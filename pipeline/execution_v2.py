"""Self-financing signed ETF account for the local v2 research study.

This is an explicit accounting convention, not a broker margin simulator.
Adjusted ETF total returns already include reinvested distributions: applying
them to negative holdings charges the short side for those distributions too.
Do not add a second manufactured-dividend charge to this return convention.

Normal target portfolios have sum(weights)=1. With short market value S and
collateral h*S, the separate financing debit is h*S after rebalancing. Thus
NAV = long - short + collateral - debt, not long + short-sale proceeds twice.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path

import numpy as np
import pandas as pd


class InsolventAccountError(RuntimeError):
    """A nonpositive-equity account cannot open a new research portfolio."""


@dataclass
class Account:
    """Dollar ledger; ``long``, ``short`` and ``gross`` are NAV exposure ratios.

    ``margin_required`` is dollars; ``margin_ratio`` is required dollars/NAV.
    Limits on ETF weights, look-through exposures and gross leverage belong to
    the allocation model. They are deliberately not enforced here so identical
    account arithmetic can evaluate both the model and its benchmarks.
    """

    initial_nav: float = 1.0
    collateral_haircut: float = 1.0
    management_fee: float = 0.0025
    borrow_fee: float = 0.02
    funding_spread: float = 0.01
    collateral_rebate: float = 0.0
    long_maintenance: float = 0.25
    short_maintenance: float = 0.30
    holdings: pd.Series = field(default_factory=lambda: pd.Series(dtype=float), init=False)
    cash: float = field(init=False)
    collateral: float = field(default=0.0, init=False)
    debt: float = field(default=0.0, init=False)

    def __post_init__(self):
        if not np.isfinite(self.initial_nav) or self.initial_nav <= 0:
            raise ValueError("Initial NAV must be positive and finite")
        if not np.isfinite(self.collateral_haircut) or self.collateral_haircut < 0:
            raise ValueError("Collateral multiplier must be nonnegative")
        for name in ("management_fee", "borrow_fee", "funding_spread",
                     "long_maintenance", "short_maintenance"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        self.cash = float(self.initial_nav)

    @property
    def nav(self):
        return float(self.holdings.sum() + self.cash + self.collateral - self.debt)

    @property
    def long_value(self):
        return float(self.holdings.clip(lower=0).sum())

    @property
    def short_value(self):
        return float(-self.holdings.clip(upper=0).sum())

    @property
    def long(self):
        return self.long_value / self.nav if self.nav > 0 else np.inf

    @property
    def short(self):
        return self.short_value / self.nav if self.nav > 0 else np.inf

    @property
    def gross(self):
        return (self.long_value + self.short_value) / self.nav if self.nav > 0 else np.inf

    @property
    def net(self):
        return float(self.holdings.sum() / self.nav) if self.nav > 0 else np.nan

    @property
    def weights(self):
        if self.nav <= 0:
            raise InsolventAccountError("Weights are undefined for nonpositive NAV")
        return self.holdings / self.nav

    @property
    def margin_required(self):
        """Study maintenance requirement in dollars, not certified broker terms."""
        return self.long_maintenance*self.long_value + self.short_maintenance*self.short_value

    @property
    def margin_ratio(self):
        return self.margin_required / self.nav if self.nav > 0 else np.inf

    @property
    def margin_breached(self):
        return bool(self.nav <= 0 or self.nav < self.margin_required - 1e-12)

    @property
    def bankrupt(self):
        return bool(self.nav <= 0)

    def snapshot(self):
        return dict(nav=self.nav, long_value=self.long_value, short_value=self.short_value,
                    cash=float(self.cash), collateral=float(self.collateral),
                    debt=float(self.debt), gross=self.gross, net=self.net,
                    margin_required=self.margin_required, margin_ratio=self.margin_ratio,
                    margin_breached=self.margin_breached, bankrupt=self.bankrupt)

    def _settle_cash(self):
        """Fund negative free cash; use positive free cash to repay debit first."""
        if self.cash < 0:
            self.debt -= self.cash
            self.cash = 0.0
        elif self.cash > 0 and self.debt > 0:
            repayment = min(self.cash, self.debt)
            self.cash -= repayment
            self.debt -= repayment
        if abs(self.cash) < 1e-15:
            self.cash = 0.0
        if abs(self.debt) < 1e-15:
            self.debt = 0.0

    def _mark_collateral(self):
        required = self.collateral_haircut*self.short_value
        change = required-self.collateral
        self.cash -= change
        self.collateral = required
        self._settle_cash()
        return float(change)

    def mark(self, returns):
        """Apply one holding-period total-return vector and mark collateral.

        Prices/returns must already be aligned by the caller. No missing held
        return is filled, and no asset value is changed by a fee payment here.
        """
        before = self.nav
        r = pd.Series(returns, dtype=float)
        if not r.index.is_unique:
            raise ValueError("Duplicate return tickers")
        held_returns = r.reindex(self.holdings.index)
        if held_returns.isna().any() or not np.isfinite(held_returns.to_numpy()).all():
            raise ValueError("Every held ETF needs a finite period return")
        if (held_returns < -1).any():
            raise ValueError("An unlevered ETF cannot have a simple total return below -100%")
        pnl = float((self.holdings*held_returns).sum())
        self.holdings = self.holdings*(1+held_returns)
        collateral_change = self._mark_collateral()
        after = self.nav
        np.testing.assert_allclose(after, before+pnl, rtol=1e-11, atol=1e-12)
        return dict(nav_before=before, nav_after=after, market_pnl=pnl,
                    collateral_change=collateral_change, bankrupt=self.bankrupt,
                    margin_breached=self.margin_breached)

    def accrue(self, days, rfannual, management_fee=None, borrow_fee=None,
               funding_spread=None, collateral_rebate=None, cash_rate=None):
        """Accrue simple calendar-day charges through cash/debit, not hidden sales.

        ``rfannual`` is an annual decimal yield known before the accrual period.
        Rates are annual decimals; day count is ACT/365. The baseline restricted
        collateral earns no rebate. Free unencumbered cash earns rfannual unless
        an explicit cash_rate is supplied. Financing debit pays rfannual+spread.
        """
        days = float(days)
        if not np.isfinite(days) or days < 0 or not np.isfinite(rfannual):
            raise ValueError("Finite nonnegative days and a finite annual yield required")
        rates = dict(management_fee=self.management_fee if management_fee is None else management_fee,
                     borrow_fee=self.borrow_fee if borrow_fee is None else borrow_fee,
                     funding_spread=self.funding_spread if funding_spread is None else funding_spread,
                     collateral_rebate=self.collateral_rebate if collateral_rebate is None else collateral_rebate,
                     cash_rate=rfannual if cash_rate is None else cash_rate)
        if not all(np.isfinite(float(x)) for x in rates.values()):
            raise ValueError("Every accrual rate must be finite")
        if any(float(rates[x]) < 0 for x in ("management_fee", "borrow_fee", "funding_spread")):
            raise ValueError("Management, stock-borrow fee and funding spread must be nonnegative")
        before = self.nav
        dt = days/365.0
        management = max(before, 0.0)*float(rates["management_fee"])*dt
        borrow = self.short_value*float(rates["borrow_fee"])*dt
        financing = self.debt*(float(rfannual)+float(rates["funding_spread"]))*dt
        rebate = self.collateral*float(rates["collateral_rebate"])*dt
        cash_interest = self.cash*float(rates["cash_rate"])*dt
        net_cost = management+borrow+financing-rebate-cash_interest
        self.cash -= net_cost
        self._settle_cash()
        after = self.nav
        np.testing.assert_allclose(after, before-net_cost, rtol=1e-11, atol=1e-12)
        return dict(nav_before=before, nav_after=after, days=days,
                    management_cost=float(management), borrow_cost=float(borrow),
                    financing_cost=float(financing), collateral_credit=float(rebate),
                    cash_interest=float(cash_interest), total_cost=float(net_cost),
                    bankrupt=self.bankrupt, margin_breached=self.margin_breached)

    def rebalance(self, target, cost_rate=0.001):
        """Execute signed target at current marks and pay all turnover from NAV.

        Solve N_after = NAV_before - cost_rate*sum(abs(w*N_after-v_before)).
        Rebalancing closes the old collateral/debit account and opens the new
        one, at h*S each. Financing charges already paid through debit therefore
        reduce the capital available for new holdings; they are not forgiven.
        """
        before_nav = self.nav
        if before_nav <= 0:
            raise InsolventAccountError("A nonpositive-NAV account cannot rebalance")
        w = pd.Series(target, dtype=float)
        if w.empty or not w.index.is_unique or not np.isfinite(w.to_numpy()).all():
            raise ValueError("Target weights must be finite, nonempty and uniquely indexed")
        if not np.isclose(w.sum(), 1.0, rtol=0, atol=1e-9):
            raise ValueError("Normal signed target weights must sum to one")
        if not np.isfinite(cost_rate) or cost_rate < 0:
            raise ValueError("Trading cost rate must be finite and nonnegative")
        if cost_rate*float(w.abs().sum()) >= 1:
            raise ValueError("Trading-cost fixed point requires cost_rate*gross_target < 1")
        names = list(dict.fromkeys(list(w.index)+list(self.holdings.index)))
        target_array = w.reindex(names, fill_value=0).to_numpy()
        old = self.holdings.reindex(names, fill_value=0).to_numpy()

        def fees(nav):
            return float(cost_rate*np.abs(target_array*nav-old).sum())

        if fees(0.) >= before_nav and cost_rate > 0:
            raise InsolventAccountError("Liquidation costs exhaust available NAV")
        after_nav = before_nav
        for _ in range(100):
            updated = before_nav-fees(after_nav)
            if abs(updated-after_nav) <= 1e-14*max(1., before_nav):
                after_nav = updated
                break
            after_nav = updated
        if abs(after_nav+fees(after_nav)-before_nav) > 1e-11*max(1., before_nav):
            # This should rarely be needed, but solves the same monotone budget
            # equation rather than accepting an unconverged fixed point.
            lo, hi = 0.0, before_nav
            for _ in range(100):
                mid = (lo+hi)/2
                if mid+fees(mid)>before_nav:
                    hi=mid
                else:
                    lo=mid
            after_nav=(lo+hi)/2
        after = target_array*after_nav
        delta = after-old
        buys = float(delta.clip(min=0).sum())
        sells = float(-delta.clip(max=0).sum())
        notional = buys+sells
        transaction_cost = float(cost_rate*notional)
        old_funding_net = self.cash+self.collateral-self.debt
        # Purchases/sales plus release/settlement of the old funding account
        # exactly finance the final target (the new funding account nets to 0).
        residual = old_funding_net+sells-buys-transaction_cost
        np.testing.assert_allclose(residual, 0., rtol=0, atol=2e-11*max(1., before_nav))
        self.holdings = pd.Series(after, index=names)
        self.holdings = self.holdings[self.holdings.abs()>1e-14]
        self.collateral = self.collateral_haircut*self.short_value
        self.debt = self.collateral
        self.cash = 0.0
        np.testing.assert_allclose(self.nav+transaction_cost, before_nav, rtol=1e-11, atol=1e-12)
        return dict(nav_before=before_nav, nav_after=self.nav, buys=buys,
                    sells=sells, notional=notional, tc=transaction_cost,
                    cost=transaction_cost, collateral=float(self.collateral),
                    debt=float(self.debt), funding_cashflow_residual=float(residual),
                    gross=self.gross, short=self.short, long=self.long,
                    margin_breached=self.margin_breached, bankrupt=self.bankrupt)

    def liquidate(self, cost_rate=0.001):
        """Close all positions, release collateral and settle debit at current marks.

        A remaining deficit is retained as debt with nonpositive NAV, never
        clipped to a profitable cash account. The caller decides the chronology
        of forced liquidation and whether/when normal trading may resume.
        """
        if not np.isfinite(cost_rate) or cost_rate < 0:
            raise ValueError("Trading cost rate must be finite and nonnegative")
        before = self.nav
        buys = self.short_value
        sells = self.long_value
        notional = buys+sells
        tc = float(cost_rate*notional)
        net_cash = before-tc
        self.holdings = pd.Series(dtype=float)
        self.collateral = 0.0
        self.cash = max(net_cash, 0.0)
        self.debt = max(-net_cash, 0.0)
        np.testing.assert_allclose(self.nav+tc, before, rtol=1e-11, atol=1e-12)
        return dict(nav_before=before, nav_after=self.nav, buys=float(buys),
                    sells=float(sells), notional=float(notional), tc=tc, cost=tc,
                    cash=float(self.cash), debt=float(self.debt), bankrupt=self.bankrupt,
                    margin_breached=self.margin_breached)


def self_test(output_path=None):
    """Run independent accounting examples; write an output only when requested."""
    checks = []

    def check(name, actual, expected, atol=1e-11):
        np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=atol)
        checks.append(name)

    a = Account(management_fee=0, borrow_fee=0, funding_spread=0)
    tx = a.rebalance(pd.Series({"LONG":1.2, "SHORT":-.2}), cost_rate=0)
    check("Signed entry does not create capital from short proceeds", a.nav, 1)
    check("Signed entry has 120% long and 20% short", [a.long,a.short,a.gross], [1.2,.2,1.4])
    check("Short proceeds are restricted and separately financed", [a.collateral,a.debt,a.cash], [.2,.2,0])
    a.mark(pd.Series({"LONG":0., "SHORT":.1}))
    check("A +10% short-ETF return costs 2% starting NAV", a.nav, .98)
    check("Collateral change has no independent profit/loss", [a.collateral,a.debt], [.22,.22])

    a = Account(management_fee=0, borrow_fee=0, funding_spread=0)
    a.rebalance(pd.Series({"LONG":1.2,"SHORT":-.2}),cost_rate=0)
    a.mark(pd.Series({"LONG":0.,"SHORT":-.1}))
    check("A -10% short-ETF return earns 2% starting NAV", a.nav, 1.02)
    check("Falling short releases collateral and repays debit", [a.collateral,a.debt], [.18,.18])

    a = Account()
    a.rebalance(pd.Series({"LONG":1.2,"SHORT":-.2}),cost_rate=0)
    before_holdings=a.holdings.copy()
    costs=a.accrue(days=365,rfannual=.04)
    expected=.0025+.2*.02+.2*(.04+.01)
    check("Management, borrowing and financing debits match explicit rates",costs["total_cost"],expected)
    check("Paying charges does not silently sell or resize holdings",a.holdings.to_numpy(),before_holdings.to_numpy())
    check("Charges remain in debit and reduce NAV",[a.debt,a.nav],[.2+expected,1-expected])
    tx=a.rebalance(pd.Series({"LONG":1.2,"SHORT":-.2}),cost_rate=.001)
    check("Rebalancing settles accrued debit without forgiving fees",a.nav+tx["tc"],1-expected)
    check("Rebalanced funding accounts again offset",a.collateral,a.debt)

    a=Account()
    tx=a.rebalance(pd.Series({"ETF":1.}),cost_rate=.001)
    check("Long-only initial purchase is self-financing",a.nav,1/1.001)
    check("Long-only does not create financing or stock-borrow debit",[a.debt,a.collateral],[0,0])
    costs=a.accrue(1,.04,management_fee=0)
    check("Long-only financing and stock-borrow charges are zero",[costs["borrow_cost"],costs["financing_cost"]],[0,0])

    a=Account()
    tx=a.rebalance(pd.Series({"LONG":1.2,"SHORT":-.2}),cost_rate=.001)
    check("Long-short entry costs apply to total gross notional",a.nav,1/(1+.001*1.4))
    a.mark(pd.Series({"LONG":.01,"SHORT":-.02}))
    a.accrue(3,.04)
    before=a.nav
    close=a.liquidate(.001)
    check("Liquidation conserves NAV and all closing costs",a.nav+close["tc"],before)
    check("Solvent liquidation leaves only unencumbered cash",[a.holdings.sum(),a.collateral,a.debt],[0,0,0])
    check("Solvent cash equals liquidation NAV",a.cash,a.nav)

    a=Account(management_fee=0,borrow_fee=0,funding_spread=0)
    a.rebalance(pd.Series({"LONG":1.2,"SHORT":-.2}),cost_rate=0)
    a.mark(pd.Series({"LONG":0,"SHORT":10.}))
    check("A short squeeze can create negative equity",a.nav,-1)
    assert a.bankrupt and a.margin_breached
    checks.append("Negative equity is explicitly flagged, not dropped")
    a.liquidate(0)
    check("Insolvent liquidation retains unpaid debt",[a.nav,a.cash,a.debt],[-1,0,1])

    rng=np.random.default_rng(451062)
    a=Account()
    for period in range(100):
        if period%5==0:
            shorts=rng.dirichlet(np.ones(2))*.2
            longs=rng.dirichlet(np.ones(3))*1.2
            target=pd.Series(np.r_[longs,-shorts],index=list("ABCDE"))
            before=a.nav
            tx=a.rebalance(target,.001)
            np.testing.assert_allclose(a.nav+tx["tc"],before,rtol=1e-11,atol=1e-12)
            np.testing.assert_allclose(a.weights.reindex(target.index),target,atol=1e-10)
        before=a.nav
        market=rng.normal(.0002,.01,5)
        pnl=float(a.holdings.reindex(list("ABCDE"),fill_value=0)@market)
        a.mark(pd.Series(market,index=list("ABCDE")))
        np.testing.assert_allclose(a.nav,before+pnl,rtol=1e-11,atol=1e-12)
        costs=a.accrue(1,.04)
        np.testing.assert_allclose(a.nav,costs["nav_before"]-costs["total_cost"],atol=1e-11)
    checks.append("100 random periods reconcile targets, market P&L, fees and NAV")
    result=dict(passed=True,count=len(checks),checks=checks,
                conventions="USD signed total-return notionals; ACT/365; no duplicate dividend charge",
                limitation="Study collateral and maintenance policies; not broker-certified availability or margin terms")
    if output_path is not None:
        path=Path(output_path)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.self_test:
        result=self_test(args.output)
        print(json.dumps(result,indent=2))
    else:
        parser.print_help()
