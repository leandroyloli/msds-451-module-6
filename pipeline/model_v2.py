"""Exact conic maximum net Sharpe with signed ETF positions and empirical CVaR."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache

import cvxpy as cp
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from . import config_v2 as c


def cvar(returns, weights, monthly_cost=0., level=c.CVAR_LEVEL):
    loss=-np.asarray(returns)@np.asarray(weights)+monthly_cost
    # Exact empirical CVaR, including fractional tail mass if required.
    count=(1-level)*len(loss)
    order=np.sort(loss)[::-1]
    n=int(np.floor(count+1e-10))
    fraction=count-n
    return float((order[:n].sum()+(fraction*order[n] if fraction>1e-10 else 0))/count)


def estimate(returns):
    """Data-driven common-mean shrinkage inspired by Bayes–Stein, not exact Jorion."""
    R=np.asarray(returns,float)
    T,N=R.shape
    fit=LedoitWolf().fit(R)
    cov=fit.covariance_
    inverse=np.linalg.inv(cov)
    one=np.ones(N)
    gmv=inverse@one/(one@inverse@one)
    means=R.mean(axis=0)
    center=float(gmv@means)
    delta=means-center
    strength=float((N+2)/(N+2+T*max(delta@inverse@delta,0)))
    mu=((1-strength)*means+strength*center)*12
    annual=cov*12
    eigen,vec=np.linalg.eigh(annual)
    root=(vec*np.sqrt(np.maximum(eigen,1e-12)))@vec.T
    return mu,annual,root,dict(mean_shrinkage=strength,cov_shrinkage=float(fit.shrinkage_),center_annual=center*12)


class Optimizer:
    def __init__(self,names,A,b,labels,long_only=False,sector_limit=None,borrow=c.BORROW):
        self.names=list(names)
        self.n=len(names)
        self.labels=list(labels)
        self.A=np.asarray(A,float)
        self.b=np.asarray(b,float).copy()
        if sector_limit is not None:
            for i,label in enumerate(labels):
                if label.startswith("sector:"):self.b[i]=sector_limit
        self.long_only=long_only
        self.borrow=borrow
        # Rows that cannot bind under the gross ceiling may be omitted from the
        # solve, but are still independently checked on every final solution.
        keep=self.A.max(axis=1)*c.GROSS_MAX>self.b-1e-10
        active_A,active_b=self.A[keep],self.b[keep]
        n=self.n
        p=cp.Variable(n,nonneg=True)
        q=cp.Variable(n,nonneg=True)
        scale=cp.Variable(nonneg=True)
        eta=cp.Variable()
        slack=cp.Variable(c.TRAIN_MONTHS,nonneg=True)
        traded=cp.Variable(n,nonneg=True)
        self.mu=cp.Parameter(n)
        self.root=cp.Parameter((n,n))
        self.history=cp.Parameter((c.TRAIN_MONTHS,n))
        self.rf=cp.Parameter(nonneg=True)
        self.short_cost=cp.Parameter(nonneg=True)
        self.old=cp.Parameter(n)
        y=p-q
        cost_month=c.MANAGEMENT/12*scale+self.short_cost/12*cp.sum(q)+c.TRANSACTION*cp.sum(traded)
        constraints=[cp.sum(y)==scale,
                     p<=c.LONG_MAX*scale,
                     q<=(0. if long_only else c.SHORT_MAX)*scale,
                     cp.sum(p+q)<=(1. if long_only else c.GROSS_MAX)*scale,
                     active_A@(p+q)<=active_b*scale,
                     traded>=y-cp.multiply(self.old,scale),
                     traded>=-y+cp.multiply(self.old,scale),
                     slack>=-self.history@y+cost_month-eta,
                     eta+cp.sum(slack)/((1-c.CVAR_LEVEL)*c.TRAIN_MONTHS)<=c.CVAR_MONTHLY_MAX*scale,
                     cp.norm(self.root@y,2)<=1]
        # Homogeneous (Schaible) transform: divide y by scale after solving.
        numerator=self.mu@y-(self.rf+c.MANAGEMENT)*scale-self.short_cost*cp.sum(q)-12*c.TRANSACTION*cp.sum(traded)
        self.problem=cp.Problem(cp.Maximize(numerator),constraints)
        self.variables=(p,q,scale)

    def fit(self,returns,rfannual,old=None):
        R=np.asarray(returns,float)
        if R.shape!=(c.TRAIN_MONTHS,self.n):raise ValueError("Need exactly 60 preceding monthly returns")
        mu,cov,root,diag=estimate(R)
        old=np.zeros(self.n) if old is None else np.asarray(old,float)
        self.mu.value=mu
        self.root.value=root
        self.history.value=R
        self.rf.value=max(float(rfannual),0.)
        self.short_cost.value=max(float(rfannual),0.)+c.FINANCING_SPREAD+self.borrow
        self.old.value=old
        self.problem.solve(solver="CLARABEL",warm_start=True,tol_gap_abs=1e-8,tol_feas=1e-8,tol_gap_rel=1e-8,max_iter=200)
        if self.problem.status not in {"optimal","optimal_inaccurate"}:
            raise ValueError("Conic allocation failed: "+self.problem.status)
        p,q,scale=self.variables
        if scale.value is None or scale.value<1e-7 or self.problem.value<1e-8:
            # If all expected excess opportunities are negative, the homogeneous
            # maximum is zero. Use a disclosed mandate-constrained min-risk rule.
            return self._minimum_risk(R,rfannual,old,mu,cov,diag)
        w=(p.value-q.value)/scale.value
        w[np.abs(w)<1e-9]=0
        return self._finish(w,R,rfannual,old,mu,cov,diag,"maximum_net_sharpe")

    def _minimum_risk(self,R,rf,old,mu,cov,diag):
        n=self.n
        p=cp.Variable(n,nonneg=True);q=cp.Variable(n,nonneg=True)
        w=p-q;eta=cp.Variable();z=cp.Variable(len(R),nonneg=True)
        monthly=c.MANAGEMENT/12+(rf+c.FINANCING_SPREAD+self.borrow)/12*cp.sum(q)+c.TRANSACTION*cp.norm1(w-old)
        cons=[cp.sum(w)==1,p<=c.LONG_MAX,q<=(0. if self.long_only else c.SHORT_MAX),
              cp.sum(p+q)<=(1 if self.long_only else c.GROSS_MAX),self.A@(p+q)<=self.b,
              z>=-R@w+monthly-eta,eta+cp.sum(z)/((1-c.CVAR_LEVEL)*len(R))<=c.CVAR_MONTHLY_MAX]
        problem=cp.Problem(cp.Minimize(cp.quad_form(w,cp.psd_wrap(cov))+1e-5*cp.sum(p+q)),cons)
        problem.solve(solver="CLARABEL",tol_feas=1e-8,tol_gap_abs=1e-8,tol_gap_rel=1e-8)
        if problem.status not in {"optimal","optimal_inaccurate"}:raise ValueError("Minimum-risk safeguard infeasible: "+problem.status)
        return self._finish(np.asarray(w.value).ravel(),R,rf,old,mu,cov,diag,"negative_expected_excess_minimum_risk")

    def _finish(self,w,R,rf,old,mu,cov,diag,method):
        # Conic solvers allow tiny equality residuals; close the accounting
        # identity before independently rechecking every economic constraint.
        w=np.asarray(w,float)/np.sum(w)
        S=float(np.maximum(-w,0).sum())
        trade=float(np.abs(w-old).sum())
        forecast_cost=c.MANAGEMENT+(rf+c.FINANCING_SPREAD+self.borrow)*S+12*c.TRANSACTION*trade
        monthly_cost=forecast_cost/12
        violations=dict(net=abs(w.sum()-1),long=max(w.max()-c.LONG_MAX,0),
                        short=max(-w.min()-(0 if self.long_only else c.SHORT_MAX),0),
                        gross=max(np.abs(w).sum()-(1 if self.long_only else c.GROSS_MAX),0),
                        exposure=max(float(np.max(self.A@np.abs(w)-self.b)),0),
                        cvar=max(cvar(R,w,monthly_cost)-c.CVAR_MONTHLY_MAX,0))
        if max(violations.values())>2e-6:raise AssertionError("Target constraint violation: "+str(violations))
        vol=float(np.sqrt(w@cov@w))
        diag.update(expected_return=float(mu@w),expected_volatility=vol,
                    expected_net_sharpe=float((mu@w-rf-forecast_cost)/vol),
                    expected_annual_cost=forecast_cost,cvar_95_month=cvar(R,w,monthly_cost),
                    gross=float(np.abs(w).sum()),short=S,turnover_forecast=trade,
                    solve_method=method,max_violation=max(violations.values()))
        return pd.Series(w,index=self.names),diag


def closest_band(current,target,A,b,R,rf,long_only=False,borrow=c.BORROW,band=c.BAND):
    """LP minimum trading within bands and the same gross/exposure/CVaR policy."""
    names=list(target.index)
    old=current.reindex(names,fill_value=0).to_numpy()
    goal=target.to_numpy()
    n=len(names)
    A=np.asarray(A,float);b=np.asarray(b,float)
    keep=A.max(axis=1)*(1. if long_only else c.GROSS_MAX)>b-1e-10
    reduced_A,reduced_b=A[keep],b[keep]
    w=cp.Variable(n)
    absw=cp.Variable(n,nonneg=True)
    eta=cp.Variable();z=cp.Variable(len(R),nonneg=True)
    transaction=cp.norm1(w-old)
    short=cp.sum(cp.pos(-w))
    monthly_cost=c.MANAGEMENT/12+(max(rf,0)+c.FINANCING_SPREAD+borrow)/12*short+c.TRANSACTION*transaction
    constraints=[cp.sum(w)==1,w>=np.maximum(goal-band,0 if long_only else -c.SHORT_MAX),
                 w<=np.minimum(goal+band,c.LONG_MAX),absw>=w,absw>=-w,
                 cp.sum(absw)<=(1 if long_only else c.GROSS_MAX),reduced_A@absw<=reduced_b,
                 z>=-np.asarray(R)@w+monthly_cost-eta,
                 eta+cp.sum(z)/((1-c.CVAR_LEVEL)*len(R))<=c.CVAR_MONTHLY_MAX]
    prob=cp.Problem(cp.Minimize(transaction),constraints)
    prob.solve(solver="CLARABEL",tol_feas=1e-8,tol_gap_abs=1e-8,tol_gap_rel=1e-8)
    if prob.status not in {"optimal","optimal_inaccurate"}:raise ValueError("Band LP infeasible: "+prob.status)
    answer=np.asarray(w.value).ravel()
    answer=answer/answer.sum()
    short_value=float(np.maximum(-answer,0).sum())
    cost=c.MANAGEMENT/12+(max(rf,0)+c.FINANCING_SPREAD+borrow)/12*short_value+c.TRANSACTION*np.abs(answer-old).sum()
    violations=[abs(answer.sum()-1),answer.max()-c.LONG_MAX,
                -answer.min()-(0 if long_only else c.SHORT_MAX),
                np.abs(answer).sum()-(1 if long_only else c.GROSS_MAX),
                np.max(A@np.abs(answer)-b),cvar(R,answer,cost)-c.CVAR_MONTHLY_MAX]
    if max(violations)>2e-6:raise AssertionError("Band constraint violation: "+str(violations))
    return pd.Series(answer,index=names)
