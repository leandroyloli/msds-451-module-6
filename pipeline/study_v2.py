"""Current-look-through research experiment, explicitly retrospective in history."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import numpy as np
import pandas as pd

from . import config_v2 as c, data, eligibility as model
from .utilities import asof, metrics
from .execution_v2 import Account
from .model_v2 import Optimizer,closest_band


UNKNOWN={"","UNKNOWN","NAN","NONE","-","UNCLASSIFIED","NOT CLASSIFIED","N/A"}


class ExposureBook:
    def __init__(self):
        path=c.DATA/"holdings/holdings.csv"
        self.source_hash=hashlib.sha256(path.read_bytes()).hexdigest()
        self.holdings=pd.read_csv(path,keep_default_na=False)
        self.coverage=pd.read_csv(c.DATA/"holdings/coverage.csv").set_index("etf")
        self.names=sorted(self.holdings.etf.unique())
        self.matrices={}
        self.unknown={}
        for kind,column in [("company","issuer_id"),("sector","sector"),("industry","industry"),("country","country"),("currency","currency")]:
            rows=[]
            for ticker,g in self.holdings.groupby("etf"):
                # Company/industry/country exposure applies to equities; cash
                # is not falsely treated as an unidentified operating company.
                if kind in {"company","industry","country"}:
                    relevant=g.loc[g.asset_class.astype(str).str.lower().isin(["equity","stock","stocks","equities"])].copy()
                else: relevant=g.copy()
                relevant["absolute_weight"]=pd.to_numeric(relevant.weight,errors="raise").abs()
                unknown=relevant[column].astype(str).str.upper().isin(UNKNOWN)
                missing=max(1-float(pd.to_numeric(g.weight).sum()),0.)
                unk=float(relevant.loc[unknown,"absolute_weight"].sum())+missing
                self.unknown[(kind,ticker)]=unk
                for label,group in relevant.loc[~unknown].groupby(column):
                    if kind=="company" and str(label).lower().startswith(("cash", "currency")):continue
                    rows.append(dict(label=str(label),etf=ticker,value=float(group.absolute_weight.sum())))
            frame=pd.DataFrame(rows)
            matrix=frame.pivot(index="label",columns="etf",values="value").fillna(0) if len(frame) else pd.DataFrame(columns=self.names)
            self.matrices[kind]=matrix.reindex(columns=self.names,fill_value=0)
        # Require an actual complete-file source. Rounded weights and metadata
        # gaps remain conservatively budgeted in the unknown-exposure rows.
        self.complete=[]
        for ticker,row in self.coverage.iterrows():
            status=str(row.status)
            if ticker in self.names and ("complete" in status or "derived" in status) and float(row.equity_weight)>=.90:
                self.complete.append(ticker)

    def select(self,names):
        rows=[];bounds=[];labels=[]
        for kind,frame in self.matrices.items():
            subset=frame.reindex(columns=names,fill_value=0)
            for label,row in subset.iterrows():
                if not row.any():continue
                bound={"company":c.COMPANY_MAX,"sector":c.SECTOR_MAX,"industry":c.INDUSTRY_MAX,
                       "country":c.US_MAX if label=="United States" else c.OTHER_COUNTRY_MAX,
                       "currency":c.CURRENCY_MAX}[kind]
                rows.append(row.to_numpy());bounds.append(bound);labels.append(kind+":"+label)
            unknown=np.array([self.unknown.get((kind,t),1.) for t in names])
            rows.append(unknown);bounds.append(c.UNKNOWN_MAX);labels.append("unknown:"+kind)
        return np.array(rows,float),np.array(bounds,float),labels

    def portfolio(self,weights):
        weights=pd.Series(weights)
        output=[]
        for kind,frame in self.matrices.items():
            panel=frame.reindex(columns=weights.index,fill_value=0)
            gross=panel@weights.abs();net=panel@weights
            for name in gross.index:
                if gross[name]>1e-6:
                    output.append(dict(kind=kind,name=name,gross=float(gross[name]),net=float(net[name])))
            unknown=sum(self.unknown.get((kind,t),1.)*abs(v) for t,v in weights.items())
            output.append(dict(kind=kind,name="Unidentified / rounding",gross=float(unknown),net=np.nan))
        return pd.DataFrame(output)


@dataclass
class Study:
    monthly:pd.DataFrame
    fx_monthly:pd.Series
    meta:pd.DataFrame
    exposures:ExposureBook
    prices:pd.DataFrame
    fx:pd.Series
    yields:pd.Series
    quote_age:pd.DataFrame

    def select(self,signal):
        # Apply composition availability BEFORE equivalent-wrapper preference:
        # a missing preferred wrapper must not exclude a recovered substitute.
        columns=[t for t in self.meta.index if t in self.exposures.complete]
        subset=self.monthly.reindex(columns=columns)
        return model.select_assets(subset,signal,self.meta.loc[columns])


def valuation_v2():
    raw=pd.read_csv(c.ROOT/"data/daily_prices.csv",parse_dates=["date"])
    fx=pd.read_csv(c.ROOT/"data/fx.csv",parse_dates=["date"])
    calendar=pd.DatetimeIndex(sorted(raw.loc[raw.ticker.eq("VT"),"date"].unique()))
    calendar=calendar[(calendar>=c.START)&(calendar<=c.END)]
    columns={};ages={}
    for ticker,g in raw.groupby("ticker"):
        g=g.sort_values("date")
        paired=pd.merge_asof(pd.DataFrame({"date":calendar}),g[["date","adjusted_close"]].assign(observed=g.date),
                             on="date",direction="backward",tolerance=pd.Timedelta(days=14))
        px=pd.Series(paired.adjusted_close.to_numpy(),index=calendar)
        ages[ticker]=pd.Series((paired.date-paired.observed).dt.days.to_numpy(),index=calendar)
        currency=g.quote_currency.iloc[0]
        if currency!="USD":
            symbol={"BRL":"BRL=X","GBP":"GBPUSD=X","EUR":"EURUSD=X"}[currency]
            rate=asof(fx.loc[fx.symbol.eq(symbol)].set_index("date").close,calendar,5)
            px=px/rate if currency=="BRL" else px*rate
        columns[ticker]=px
    usdb=asof(fx.loc[fx.symbol.eq("BRL=X")].set_index("date").close,calendar,5)
    return pd.DataFrame(columns),usdb,pd.DataFrame(ages)


def prepare():
    monthly,fxm,_=data.load_monthly()
    meta=pd.read_csv(c.ROOT/"data/universe.csv").set_index("ticker")
    prices,fx,ages=valuation_v2()
    raw=pd.read_csv(c.ROOT/"data/risk_free.csv")
    rates=pd.Series(pd.to_numeric(raw.iloc[:,1],errors="coerce").to_numpy(),index=pd.to_datetime(raw.iloc[:,0])).dropna()/100
    return Study(monthly,fxm,meta,ExposureBook(),prices,fx,rates,ages)


def annual_yield(study,date):
    known=study.yields.loc[:pd.Timestamp(date)-pd.Timedelta(days=1)]
    if not len(known):raise ValueError("Missing lagged cash yield")
    return max(float(known.iloc[-1]),0.)


def run_history(study,label,long_only=False,sector_limit=None,borrow=c.BORROW,benchmark=None,temporal_control=False):
    calendar=study.prices.index
    scheduled={}
    for signal in pd.date_range("2019-06-30","2026-08-31",freq="ME"):
        idx=calendar.searchsorted(signal,side="right")
        if idx<len(calendar):scheduled[calendar[idx]]=signal
    account=Account(management_fee=0 if benchmark else c.MANAGEMENT,borrow_fee=borrow,
                    funding_spread=c.FINANCING_SPREAD,collateral_haircut=c.COLLATERAL_MULTIPLIER)
    cache={};pending={};records=[];weights=[];daily=[];margin_pending=False;bankrupt=False
    prior_date=None;prior_price=None;waiting_signal=None;waiting_weights=None
    for date in calendar:
        before=account.nav
        if bankrupt:
            # Insolvency ends this strategy. Retain the debt/deficit unchanged;
            # do not recover by continuing to mark old securities or add money.
            daily.append(dict(date=date,strategy=label,net_return=0.,trading_cost=0.,
                              management_cost=0.,borrow_cost=0.,financing_cost=0.,
                              **account.snapshot(),forced_liquidation=False,
                              unpaid_deficit=max(-account.nav,0.)))
            continue
        if prior_date is not None:
            if len(account.holdings):
                held=account.holdings.index
                quote=study.prices.loc[date,held]
                if quote.isna().any():raise ValueError(f"Missing held valuation: {date} {quote[quote.isna()].index.tolist()}")
                account.mark(quote/prior_price.reindex(held)-1)
        days=0 if prior_date is None else (date-prior_date).days
        rf=annual_yield(study,date)
        charges=account.accrue(days,rf)
        transaction=0.;forced=False
        if margin_pending and not bankrupt:
            tx=account.liquidate(c.TRANSACTION)
            transaction+=tx["tc"];forced=True; margin_pending=False
            records.append(dict(strategy=label,date=date,event="forced_liquidation",**tx))
        if account.bankrupt:
            account.liquidate(c.TRANSACTION)
            bankrupt=True
        if date in scheduled:
            waiting_signal=scheduled[date]
            waiting_weights=pending.get("old_signal",pd.Series(dtype=float)).copy()
        if waiting_signal is not None and not bankrupt and not forced:
            signal=waiting_signal
            if temporal_control:
                names,eligible=model.select_assets(study.monthly,signal,study.meta)
            else:
                names,eligible=study.select(signal)
            traded_names=list(dict.fromkeys(names+list(account.holdings.index)))
            recent=study.quote_age.loc[date,traded_names]
            if recent.isna().any() or (recent>0).any():
                # Stale marks may value an existing holding, never execute a
                # new order. Keep signal-time weights fixed while waiting.
                names=[]
            else:
                waiting_signal=None
            if not names:
                nav=account.nav
                daily.append(dict(date=date,strategy=label,net_return=nav/before-1,trading_cost=0.,
                                  **{**charges,**account.snapshot()},forced_liquidation=False,
                                  unpaid_deficit=max(-nav,0.)))
                prior_date=date;prior_price=study.prices.loc[date,account.holdings.index]
                continue
            old=waiting_weights.reindex(names,fill_value=0)
            history=study.monthly.loc[:signal].tail(61)
            R=history[names].pct_change(fill_method=None).iloc[1:].to_numpy()
            if benchmark=="VT":target=pd.Series({"VT":1.});diag={}
            elif benchmark=="equal":target=pd.Series(1/len(names),index=names);diag={}
            else:
                key=(tuple(names),long_only,sector_limit,borrow)
                if temporal_control:
                    # This separate control never uses the 2026 composition in
                    # admission or constraints. It cannot certify look-through.
                    A=np.ones((1,len(names)));b=np.array([c.GROSS_MAX]);labels=["temporal_control:gross_only"]
                else:
                    A,b,labels=study.exposures.select(names)
                if key not in cache:cache[key]=Optimizer(names,A,b,labels,long_only,sector_limit,borrow)
                opt=cache[key]
                target,diag=opt.fit(R,annual_yield(study,signal+pd.Timedelta(days=1)),old.to_numpy())
                # Bands permit holding past weights only if the FULL budget,
                # concentration, empirical tail and funding rules remain feasible.
                if len(account.holdings):
                    # The band decision uses the last signal-time snapshot,
                    # never the closing return that also executes this order.
                    target=closest_band(old,target,opt.A,opt.b,R,annual_yield(study,signal+pd.Timedelta(days=1)),long_only,borrow)
            if benchmark=="VT" and len(account.holdings):
                tx={"tc":0.,"buys":0.,"sells":0.,"notional":0.,"nav_before":account.nav,"nav_after":account.nav}
            else:tx=account.rebalance(target,c.TRANSACTION)
            transaction+=tx["tc"]
            records.append(dict(strategy=label,date=date,signal_date=signal,event="monthly",execution_delay_days=(date-signal).days,representatives=len(names),eligible=len(eligible),**{**tx,**{"optimized_"+k:v for k,v in diag.items()}}))
            for ticker in study.meta.index:
                weights.append(dict(strategy=label,date=date,signal_date=signal,ticker=ticker,
                                    weight=float(account.weights.get(ticker,0.)),target=float(target.get(ticker,0.))))
        nav=account.nav
        if nav<=0:
            if len(account.holdings):account.liquidate(c.TRANSACTION)
            nav=account.nav
            bankrupt=True
        if account.margin_breached and not bankrupt:margin_pending=True
        net=nav/before-1 if before>0 else 0.
        daily.append(dict(date=date,strategy=label,net_return=net,trading_cost=transaction,
                          **{**charges,**account.snapshot()},forced_liquidation=forced,
                          unpaid_deficit=max(-nav,0.)))
        # Store a decision-time weight snapshot BEFORE the next execution day's
        # price move; this is the optimizer's only turnover forecast input.
        if not bankrupt:pending["old_signal"]=account.weights.copy()
        prior_date=date
        prior_price=study.prices.loc[date,account.holdings.index]
    return pd.DataFrame(daily),pd.DataFrame(records),pd.DataFrame(weights),account


def run_temporal_control(study=None):
    study=study or prepare()
    d,t,w,a=run_history(study,"Controle temporal sem look-through",temporal_control=True)
    d.to_csv(c.OUT/"temporal_control_accounting.csv",index=False)
    t.to_csv(c.OUT/"temporal_control_trades.csv",index=False)
    w.to_csv(c.OUT/"temporal_control_weights.csv",index=False)
    dates=pd.DatetimeIndex(d.date)
    r=pd.Series(d.net_return.to_numpy(),index=dates)
    gaps=np.r_[0.,np.diff(dates.values).astype("timedelta64[D]").astype(float)]
    rf=pd.Series([annual_yield(study,date)*gap/365 for date,gap in zip(dates,gaps)],index=dates)
    result=metrics(r,rf)
    result.update(interpretation="Operationally time-ordered price/liquidity control; no current composition used; surviving universe still retrospective. Does NOT validate historical look-through limits.",
                  current_composition_used=False,margin_calls=int(d.forced_liquidation.sum()),
                  bankrupt=bool(d.bankrupt.any()))
    (c.OUT/"temporal_control_summary.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("Temporal price-only control complete",flush=True)
    return result


def run():
    study=prepare()
    variants=[("Long-short",False,None,c.BORROW,None),
              ("Long only",True,None,c.BORROW,None),
              ("Equal weight",True,None,c.BORROW,"equal"),
              ("VT",True,None,c.BORROW,"VT"),
              ("Sector cap 30%",False,.30,c.BORROW,None),
              ("Sector cap 40%",False,.40,c.BORROW,None),
              ("Borrow fee 5%",False,None,.05,None)]
    ds=[];ts=[];ws=[];accounts={}
    for label,lo,sector,borrow,benchmark in variants:
        print("v2 backtest:",label,flush=True)
        d,t,w,a=run_history(study,label,lo,sector,borrow,benchmark)
        ds.append(d);ts.append(t);ws.append(w);accounts[label]=a
    daily=pd.concat(ds,ignore_index=True)
    trades=pd.concat(ts,ignore_index=True)
    weights=pd.concat(ws,ignore_index=True)
    returns=daily.pivot(index="date",columns="strategy",values="net_return")
    dates=returns.index
    gaps=np.r_[0.,np.diff(dates.values).astype("timedelta64[D]").astype(float)]
    returns["RF"]=[annual_yield(study,d)*gap/365 for d,gap in zip(dates,gaps)]
    returns["FX"]=study.fx.reindex(dates).pct_change(fill_method=None).fillna(0)
    returns.to_csv(c.OUT/"daily_returns.csv",index_label="date")
    daily.to_csv(c.OUT/"accounting.csv",index=False)
    trades.to_csv(c.OUT/"trades.csv",index=False)
    weights.to_csv(c.OUT/"weights.csv",index=False)
    summaries=[]
    for label,*_ in variants:
        ledger=daily.loc[daily.strategy.eq(label)]
        if ledger.bankrupt.any():
            m=dict(cagr=np.nan,sharpe=np.nan,volatility=np.nan,max_drawdown=np.nan,
                   terminal=float(ledger.nav.iloc[-1]),bankrupt=True)
        else:
            m=metrics(returns[label],returns.RF,returns.VT)
            m["bankrupt"]=False
        m.update(strategy=label,margin_calls=int(ledger.forced_liquidation.sum()),
                 max_gross=float(ledger.gross.replace(np.inf,np.nan).max()),
                 fees_borrow=float(ledger.borrow_cost.sum()),fees_funding=float(ledger.financing_cost.sum()),
                 fees_management=float(ledger.management_cost.sum()),fees_trading=float(ledger.trading_cost.sum()))
        summaries.append(m)
    result=pd.DataFrame(summaries).set_index("strategy")
    result.to_csv(c.OUT/"metrics.csv")
    # Latest inception allocation has no invented existing personal holdings.
    signal=pd.Timestamp(c.END)
    names,eligible=study.select(signal)
    R=study.monthly.loc[:signal,names].tail(61).pct_change(fill_method=None).iloc[1:].to_numpy()
    A,b,labels=study.exposures.select(names)
    opt=Optimizer(names,A,b,labels)
    latest,diag=opt.fit(R,annual_yield(study,signal+pd.Timedelta(days=1)),np.zeros(len(names)))
    allocation=study.meta.copy()
    allocation["weight"]=latest.reindex(allocation.index,fill_value=0)
    allocation["eligible"]=allocation.index.isin(eligible)
    allocation["representative"]=allocation.index.isin(names)
    allocation.to_csv(c.OUT/"allocation.csv",index_label="ticker")
    study.exposures.portfolio(latest).to_csv(c.OUT/"lookthrough.csv",index=False)
    feasibility=pd.DataFrame({"constraint":labels,"gross_exposure":A@np.abs(latest.to_numpy()),"limit":b})
    feasibility.to_csv(c.OUT/"limits.csv",index=False)
    design=c.settings()
    design.update(holdings_sha256=study.exposures.source_hash,holdings_asof_dates=sorted(study.exposures.holdings.as_of.unique()),
                  lookthrough_history="CURRENT SNAPSHOT FROZEN RETROSPECTIVELY; NOT HISTORICAL HOLDINGS; NO CAUSAL CERTIFICATION",
                  historical_start=c.START,historical_end=c.END,
                  complete_composition_tickers=len(study.exposures.complete),eligible_latest=len(eligible),representatives_latest=len(names),
                  recommended_allocation="optimized_multi_ETF_candidate",forecast=diag,
                  mean_model="data-driven common-mean shrinkage inspired by Bayes-Stein; not a VT beta prior",
                  short_availability="assumed for study; historical borrow availability and broker execution unverified")
    (c.OUT/"design.json").write_text(json.dumps(design,indent=2),encoding="utf-8")
    print(result[["cagr","volatility","sharpe","max_drawdown","fees_borrow","fees_funding"]].round(4).to_string(),flush=True)
    return study
