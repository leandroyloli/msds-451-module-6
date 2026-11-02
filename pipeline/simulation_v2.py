"""Paired and re-estimated Monte Carlo experiments for the revised growth fund.

The v2 exposure matrix is a CURRENT issuer snapshot. Applying that matrix to
earlier market returns is a frozen-composition retrospective experiment, not a
point-in-time historical validation of company/sector/country/currency limits.
No experiment here upgrades that data limitation into a causal result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import config_v2 as c
from .utilities import aggregate_monthly, stationary_indices, _metric_arrays


PAIRED_PATHS = 10_000
PAIRED_HORIZON_MONTHS = 300
INTERVAL_PATHS = 2_000
MEAN_BLOCK_MONTHS = 6.
DYNAMIC_PATHS = 50
DYNAMIC_TEST_MONTHS = 60
BURN_IN = 60
STRATEGIES = ["Long-short", "Long only", "Equal weight", "VT"]
REQUIRED = STRATEGIES + ["RF", "FX"]
EXPOSURE_CAVEAT = (
    "Current ETF holdings are frozen: scenarios are retrospective and do not "
    "causally validate historical company/sector/country/currency limits."
)


def _clean(value):
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_clean(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _write(path, value):
    Path(path).write_text(json.dumps(_clean(value), indent=2, ensure_ascii=False,
                                    allow_nan=False), encoding="utf-8")


def _q(values):
    values = np.asarray(values, float)
    defined = values[np.isfinite(values)]
    if not len(defined):
        return dict(p05=None, p50=None, p95=None, defined_paths=0)
    quantiles = np.quantile(defined, [.05, .5, .95])
    return dict(p05=float(quantiles[0]), p50=float(quantiles[1]),
                p95=float(quantiles[2]), defined_paths=int(len(defined)))


def paired(root=None, paths=PAIRED_PATHS, horizon_months=PAIRED_HORIZON_MONTHS,
           interval_paths=INTERVAL_PATHS):
    """Replay the jointly sampled NET monthly process; no second fee deduction."""
    root = Path(root or c.ROOT)
    out = root / "output"
    daily = pd.read_csv(out / "daily_returns.csv", index_col=0, parse_dates=True)
    missing = set(REQUIRED) - set(daily.columns)
    if missing:
        raise ValueError(f"Missing v2 daily return columns: {sorted(missing)}")
    monthly, omitted = aggregate_monthly(daily[REQUIRED].astype(float))
    monthly.to_csv(out / "mc_monthly_returns.csv", index_label="date")
    data = monthly.to_numpy()
    names = list(monthly.columns)
    n_obs = len(monthly)
    seed = c.SEED + 1
    draws = stationary_indices(n_obs, paths, horizon_months, MEAN_BLOCK_MONTHS, seed)
    cash = data[draws, names.index("RF")]
    fx = data[draws, names.index("FX")]
    summaries, percentiles, terminals, measured = [], [], [], {}
    periods = sorted(set([0, horizon_months] + list(range(12, horizon_months + 1, 12))))
    for strategy in STRATEGIES:
        returns = data[draws, names.index(strategy)]
        usd, log_wealth = _metric_arrays(returns, cash, horizon_months)
        measured[strategy] = usd
        converted = (1 + returns) * (1 + fx) - 1
        brl, brl_logs = _metric_arrays(converted, (1 + cash) * (1 + fx) - 1,
                                      horizon_months)
        for currency, stats, logs in [("USD", usd, log_wealth), ("BRL", brl, brl_logs)]:
            summaries.append(dict(strategy=strategy, currency=currency,
                                  terminal_wealth=_q(stats["terminal"]),
                                  cagr=_q(stats["cagr"]),
                                  max_drawdown=_q(stats["max_drawdown"]),
                                  sharpe=_q(stats["sharpe"]) if currency == "USD" else None,
                                  probability_terminal_below_initial=float(np.mean(stats["terminal"] < 1)),
                                  probability_drawdown_below_minus_30=float(np.mean(stats["max_drawdown"] < -.30)),
                                  probability_drawdown_below_minus_50=float(np.mean(stats["max_drawdown"] < -.50))))
            for month in periods:
                wealth = np.ones(paths) if month == 0 else np.exp(logs[:, month-1])
                percentiles.append(dict(strategy=strategy, currency=currency,
                                        month=month, year=month/12, **_q(wealth)))
            for path in range(min(500, paths)):
                terminals.append(dict(path=path, strategy=strategy, currency=currency,
                                      terminal_wealth=stats["terminal"][path],
                                      cagr=stats["cagr"][path],
                                      max_drawdown=stats["max_drawdown"][path]))
    comparisons = []
    for reference in ["Long only", "Equal weight", "VT"]:
        delta = measured["Long-short"]["sharpe"] - measured[reference]["sharpe"]
        comparisons.append(dict(reference=reference, delta_sharpe=_q(delta),
                                delta_cagr=_q(measured["Long-short"]["cagr"] - measured[reference]["cagr"]),
                                probability_sharpe_above=float(np.mean(delta > 0)),
                                probability_sharpe_gain_point_one=float(np.mean(delta >= .1)),
                                probability_terminal_above=float(np.mean(
                                    measured["Long-short"]["terminal"] > measured[reference]["terminal"]))))
    joint = ((measured["Long-short"]["sharpe"] - measured["Equal weight"]["sharpe"] >= .1)
             & (measured["Long-short"]["sharpe"] - measured["VT"]["sharpe"] >= .1))
    interval_rows = []
    for block in [3, 6, 12]:
        idx = stationary_indices(n_obs, interval_paths, n_obs, block, seed + block)
        sample_cash = data[idx, names.index("RF")]
        stats = {name: _metric_arrays(data[idx, names.index(name)], sample_cash, n_obs)[0]
                 for name in STRATEGIES}
        gate = np.ones(interval_paths, bool)
        for reference in ["Long only", "Equal weight", "VT"]:
            for metric in ["sharpe", "cagr"]:
                delta = stats["Long-short"][metric] - stats[reference][metric]
                low, median, high = np.quantile(delta, [.025, .5, .975])
                interval_rows.append(dict(mean_block_months=block, reference=reference,
                                          metric=metric, p025=low, median=median, p975=high,
                                          probability_above_zero=float(np.mean(delta > 0)),
                                          probability_above_point_one=float(np.mean(delta >= .1)) if metric == "sharpe" else np.nan,
                                          resamples=interval_paths, horizon_months=n_obs, seed=seed+block))
            if reference in {"Equal weight", "VT"}:
                gate &= stats["Long-short"]["sharpe"] - stats[reference]["sharpe"] >= .1
        interval_rows.append(dict(mean_block_months=block, reference="Both benchmarks",
                                  metric="joint_sharpe_gate", p025=np.nan, median=np.nan,
                                  p975=np.nan, probability_above_zero=np.nan,
                                  probability_above_point_one=float(gate.mean()),
                                  resamples=interval_paths, horizon_months=n_obs, seed=seed+block))
    summary = dict(method="Paired stationary bootstrap of the net monthly process",
                   paths=paths, horizon_months=horizon_months, horizon_years=horizon_months/12,
                   historical_months=n_obs, first_month=str(monthly.index.min().date()),
                   last_month=str(monthly.index.max().date()), omitted_edge_months=omitted,
                   mean_block_months=MEAN_BLOCK_MONTHS, seed=seed,
                   exposure_information=EXPOSURE_CAVEAT,
                   costs="Already included in net returns; not charged again",
                   interpretation="Sample-conditional scenarios; not calibrated future probabilities",
                   sharpe="Monthly USD excess returns, annualized by square root of 12",
                   drawdown="Month-end observations only; intramonth losses may be larger",
                   strategies=summaries, comparisons=comparisons,
                   probability_sharpe_gain_point_one_over_both=float(joint.mean()),
                   limitations=[EXPOSURE_CAVEAT,
                                "Replay of the observed algorithm without within-path reoptimization",
                                f"Short sample repeated over {horizon_months/12:g} years; does not create new regimes",
                                "Survivor universe and previously explored history",
                                "Nominal BRL; no BRL Sharpe using a USD cash benchmark"])
    _write(out / "mc_summary.json", summary)
    pd.DataFrame(percentiles).to_csv(out / "mc_percentiles.csv", index=False)
    pd.DataFrame(terminals).to_csv(out / "mc_terminal_samples.csv", index=False)
    pd.DataFrame(interval_rows).to_csv(out / "mc_intervals.csv", index=False)
    same = data[draws[:20], names.index("VT")]
    a, _ = _metric_arrays(same, cash[:20], horizon_months)
    b, _ = _metric_arrays(same.copy(), cash[:20], horizon_months)
    np.testing.assert_array_equal(a["terminal"], b["terminal"])
    np.testing.assert_array_equal(a["sharpe"], b["sharpe"])
    np.testing.assert_allclose(np.prod((1+same)*(1+fx[:20]),axis=1),
                               np.prod(1+same,axis=1)*np.prod(1+fx[:20],axis=1),rtol=1e-10)
    np.testing.assert_array_equal(stationary_indices(11,20,30,6,123),
                                  stationary_indices(11,20,30,6,123))
    continuation = np.mean(draws[:,1:] == (draws[:,:-1]+1) % n_obs)
    expected = 1-1/MEAN_BLOCK_MONTHS+1/(MEAN_BLOCK_MONTHS*n_obs)
    assert abs(continuation-expected) < .01
    _write(out / "mc_verification.json", dict(passed=True,
        checks=["Monthly geometric compounding independently checked",
                "Identical indices for strategies, cash and FX",
                "Reproducible seed and geometric continuation frequency",
                "Identical pairs produce identical metrics",
                "BRL wealth equals USD wealth times compounded FX",
                "Drawdown inclui o patrimônio inicial",
                "Net costs are not deducted twice"],
        continuation_fraction=continuation, expected_continuation_fraction=expected))
    print(f"Paired MC v2: {paths:,} paths × {horizon_months} months; sample {n_obs} months.", flush=True)
    return summary


def _cash_source(root, index):
    path = root / "data/dynamic_rf_source.csv"
    if not path.exists():
        raise FileNotFoundError("Archived FRED source is required; no network fallback is used")
    raw = pd.read_csv(path)
    values = pd.Series(pd.to_numeric(raw.iloc[:,1], errors="coerce").to_numpy(),
                       index=pd.to_datetime(raw.iloc[:,0])).dropna().sort_index()
    rows = []
    for month in index:
        cutoff = month.to_period("M").start_time
        known = values.loc[values.index < cutoff]
        if known.empty or (cutoff-known.index[-1]).days > 10:
            raise ValueError(f"Missing pre-month cash proxy at {month}")
        rows.append(float(known.iloc[-1])/100/12)
    return pd.Series(rows,index=index,name="RF"),dict(
        source="FRED DGS3MO archive inherited from the first study",
        path=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        convention="Last yield observed before source month /100 /12; approximate cash return")


def _path_metrics(nav_values, returns, cash, insolvent):
    wealth = np.r_[1.,np.asarray(nav_values,float)]
    dd = wealth/np.maximum.accumulate(wealth)-1
    terminal = float(wealth[-1])
    result = dict(terminal_wealth=terminal,max_drawdown=float(dd.min()),
                  insolvent=bool(insolvent),cagr=None,sharpe=None,volatility=None)
    if not insolvent and terminal>0:
        r=np.asarray(returns,float)
        excess=r-np.asarray(cash,float)
        result.update(cagr=float(terminal**(12/len(r))-1),
                      sharpe=float(excess.mean()/excess.std(ddof=1)*np.sqrt(12)),
                      volatility=float(r.std(ddof=1)*np.sqrt(12)))
    return result


def dynamic(root=None, paths=DYNAMIC_PATHS, test_months=DYNAMIC_TEST_MONTHS,
            use_bands=True, study=None):
    """Refit both v2 optimizers on preceding synthetic returns, with real ledger.

    The seasoned source asset list is fixed with June 2019 price/liquidity
    information, intersected with CURRENT complete holdings coverage. Therefore
    this is explicitly retrospective and does not certify historical exposures.
    """
    from . import data
    from .execution_v2 import Account
    from .model_v2 import Optimizer, closest_band
    if study is None:
        from .study_v2 import prepare
        study=prepare()
    root=Path(root or c.ROOT)
    out=root/"output"
    started=time.monotonic()
    fingerprints={name:hashlib.sha256((root/"pipeline"/name).read_bytes()).hexdigest()
                  for name in ["model_v2.py","execution_v2.py","config_v2.py",
                               "study_v2.py","data.py","eligibility.py","utilities.py"]
                  if (root/"pipeline"/name).exists()}
    exposure_hash=getattr(study.exposures,"source_hash",None)
    signal=pd.Timestamp("2019-06-30")
    selection=study.select(signal)
    names=list(selection[0] if isinstance(selection,tuple) else selection)
    if len(names)<5:
        raise ValueError("Fewer than five current-holdings-covered seasoned ETFs")
    panel_names=names+([] if "VT" in names else ["VT"])
    observed=study.monthly[panel_names].pct_change(fill_method=None).loc["2014-07-31":c.END].dropna()
    if len(observed)<BURN_IN+12:
        raise ValueError("Not enough jointly complete monthly source rows")
    observed["RF"],rf_source=_cash_source(root,observed.index)
    _,fx,_=data.load_monthly(root)
    observed["FX"]=fx.pct_change(fill_method=None).reindex(observed.index)
    if observed.isna().any().any() or not np.isfinite(observed.to_numpy()).all() or (observed<=-1).any().any():
        raise ValueError("Incomplete/invalid dynamic sampling reservoir")
    observed.to_csv(out/"mc_dynamic_reservoir.csv",index_label="date")
    _write(out/"mc_dynamic_rf_source.json",rf_source)
    A,b,labels=study.exposures.select(names)
    optimizers={"Long-short":Optimizer(names,A,b,labels,long_only=False),
                "Long only":Optimizer(names,A,b,labels,long_only=True)}
    values=observed.to_numpy()
    columns=list(observed.columns)
    ix=[columns.index(name) for name in names]
    vt_ix=columns.index("VT");rf_ix=columns.index("RF");fx_ix=columns.index("FX")
    seed=c.SEED+2
    draws=stationary_indices(len(observed),paths,BURN_IN+test_months,MEAN_BLOCK_MONTHS,seed)
    results,trace=[],[]
    refits=0
    max_violation=0.
    margins=0
    safeguard_fits=0
    for path in range(paths):
        sampled=values[draws[path]]
        accounts={name:Account(management_fee=c.MANAGEMENT if name in optimizers else 0.,
                               borrow_fee=c.BORROW,funding_spread=c.FINANCING_SPREAD,
                               collateral_haircut=c.COLLATERAL_MULTIPLIER,
                               collateral_rebate=c.COLLATERAL_REBATE) for name in STRATEGIES}
        returns={name:[] for name in STRATEGIES}
        navs={name:[] for name in STRATEGIES}
        totals={name:dict(trading=0.,borrow=0.,financing=0.,management=0.,sales_turnover=0.,margin_calls=0,insolvent=False)
                for name in STRATEGIES}
        for month in range(test_months):
            end=BURN_IN+month
            training=sampled[end-BURN_IN:end][:,ix]
            rfannual=max(float(sampled[end,rf_ix])*12,0.)
            current_returns=pd.Series(sampled[end,ix],index=names)
            for strategy in STRATEGIES:
                account=accounts[strategy]
                before=account.nav
                tx_cost=0.
                if account.bankrupt:
                    # Retain the failed path and its financing deficit, never
                    # reset or replace it with a successful sample.
                    if len(account.holdings):
                        liquidation=account.liquidate(c.TRANSACTION)
                        totals[strategy]["trading"]+=liquidation["tc"]
                    cost=account.accrue(365/12,rfannual)
                    returns[strategy].append(np.nan)
                    navs[strategy].append(account.nav)
                    totals[strategy]["financing"]+=cost["financing_cost"]
                    totals[strategy]["insolvent"]=True
                    continue
                if account.margin_breached:
                    # A prior monthly close's breach is acted on only at the
                    # next monthly execution. This is a coarse monthly proxy.
                    liquidation=account.liquidate(c.TRANSACTION)
                    tx_cost+=liquidation["tc"]
                    totals[strategy]["margin_calls"]+=1
                    margins+=1
                    if account.bankrupt:
                        totals[strategy]["trading"]+=tx_cost
                        totals[strategy]["insolvent"]=True
                        returns[strategy].append(account.nav/before-1)
                        navs[strategy].append(account.nav)
                        continue
                diag={}
                if strategy in optimizers:
                    old=account.weights.reindex(names,fill_value=0).to_numpy()
                    target,diag=optimizers[strategy].fit(training,rfannual,old)
                    refits+=1
                    safeguard_fits+=int(diag.get("solve_method")!="maximum_net_sharpe")
                    max_violation=max(max_violation,diag["max_violation"])
                    if month and use_bands:
                        target=closest_band(account.weights,target,A,b,training,rfannual,
                                             long_only=strategy=="Long only")
                    tx=account.rebalance(target,c.TRANSACTION)
                elif strategy=="Equal weight":
                    tx=account.rebalance(pd.Series(1/len(names),index=names),c.TRANSACTION)
                elif month==0 or not len(account.holdings):
                    tx=account.rebalance(pd.Series({"VT":1.}),c.TRANSACTION)
                else:
                    tx=dict(tc=0.,sells=0.)
                tx_cost+=tx["tc"]
                totals[strategy]["trading"]+=tx_cost
                if month:
                    totals[strategy]["sales_turnover"]+=tx["sells"]/before
                holding_returns=current_returns if strategy!="VT" else pd.Series({"VT":sampled[end,vt_ix]})
                account.mark(holding_returns)
                cost=account.accrue(365/12,rfannual)
                for metric,key in [("borrow","borrow_cost"),("financing","financing_cost"),("management","management_cost")]:
                    totals[strategy][metric]+=cost[key]
                totals[strategy]["insolvent"] |= account.bankrupt
                returns[strategy].append(account.nav/before-1)
                navs[strategy].append(account.nav)
                if path<10:
                    trace.append(dict(path=path,month=month+1,strategy=strategy,
                                      net_return=returns[strategy][-1],nav=account.nav,
                                      training_last=end-1,holding_index=end,
                                      gross=account.gross,short=account.short,
                                      collateral=account.collateral,debt=account.debt,
                                      trading_cost=tx_cost,borrow_cost=cost["borrow_cost"],
                                      financing_cost=cost["financing_cost"],management_cost=cost["management_cost"],
                                      max_target_violation=diag.get("max_violation",0.)))
        cash=sampled[BURN_IN:,rf_ix]
        fx_returns=sampled[BURN_IN:,fx_ix]
        for strategy in STRATEGIES:
            result=_path_metrics(navs[strategy],returns[strategy],cash,totals[strategy]["insolvent"])
            result.update(path=path,strategy=strategy,
                          annual_sales_turnover=totals[strategy]["sales_turnover"]/(test_months/12),
                          paid_trading=totals[strategy]["trading"],paid_borrow=totals[strategy]["borrow"],
                          paid_financing=totals[strategy]["financing"],paid_management=totals[strategy]["management"],
                          margin_calls=totals[strategy]["margin_calls"],
                          terminal_wealth_brl=float(navs[strategy][-1]*np.prod(1+fx_returns)))
            results.append(result)
        if (path+1)%5==0:
            print(f"MC v2 dinâmico: {path+1}/{paths}; {time.monotonic()-started:.1f}s",flush=True)
    table=pd.DataFrame(results)
    assert len(table)==paths*len(STRATEGIES)
    stats=[]
    for strategy in STRATEGIES:
        z=table.loc[table.strategy.eq(strategy)]
        stats.append(dict(strategy=strategy,paths=len(z),insolvent_paths=int(z.insolvent.sum()),
                          margin_calls=int(z.margin_calls.sum()),
                          probability_terminal_below_initial=float(np.mean(z.terminal_wealth<1)),
                          **{metric:_q(z[metric]) for metric in ["terminal_wealth","cagr","sharpe","volatility","max_drawdown",
                                                               "annual_sales_turnover","paid_trading","paid_borrow","paid_financing","paid_management","terminal_wealth_brl"]}))
    sr=table.pivot(index="path",columns="strategy",values="sharpe")
    wealth=table.pivot(index="path",columns="strategy",values="terminal_wealth")
    comparisons=[]
    for reference in ["Long only","Equal weight","VT"]:
        delta=sr["Long-short"]-sr[reference]
        comparisons.append(dict(reference=reference,delta_sharpe=_q(delta),
                                defined_sharpe_pairs=int(delta.notna().sum()),
                                probability_terminal_above=float(np.mean(wealth["Long-short"]>wealth[reference])),
                                probability_sharpe_above=float((delta>0).sum()/paths),
                                probability_sharpe_gain_point_one=float((delta>=.1).sum()/paths)))
    gate=((sr["Long-short"]-sr["Equal weight"]>=.1)&(sr["Long-short"]-sr.VT>=.1))
    summary=dict(method="Monthly walk-forward on synthetic vectors with long/short and long-only reoptimization",
                 paths=paths,test_months=test_months,test_years=test_months/12,
                 burn_in_months=BURN_IN,mean_block_months=MEAN_BLOCK_MONTHS,seed=seed,
                 universe_date=str(signal.date()),assets=names,asset_count=len(names),
                 reservoir_first=str(observed.index.min().date()),reservoir_last=str(observed.index.max().date()),
                 reservoir_months=len(observed),optimizer_fits=refits,expected_fits_without_insolvency=paths*test_months*2,
                 solver_failures=0,solver_failure_policy="Execution stops on solver failure; no path is discarded",
                 max_target_constraint_violation=max_violation,margin_calls=margins,
                 minimum_risk_safeguard_fits=safeguard_fits,
                 exposure_information=EXPOSURE_CAVEAT,holdings_matrix_frozen=True,
                 holdings_sha256=exposure_hash,
                 historical_exposures_point_in_time=False,monthly_bands=use_bands,
                 execution="Signal follows 60 prior returns; execution precedes the next synthetic return; monthly approximation",
                 costs=dict(transaction=c.TRANSACTION,management=c.MANAGEMENT,borrow=c.BORROW,
                            financing_spread=c.FINANCING_SPREAD,collateral_multiplier=c.COLLATERAL_MULTIPLIER,
                            collateral_rebate=c.COLLATERAL_REBATE),
                 probabilities_are_forecasts=False,strategies=stats,comparisons=comparisons,
                 probability_sharpe_gain_point_one_over_both=float(gate.mean()),
                 fingerprints=fingerprints,elapsed_seconds=time.monotonic()-started,
                 limitations=[EXPOSURE_CAVEAT,
                              "Fixed universe of seasoned ETFs, without future admission of all 61 candidates",
                              "Monthly approximation does not measure intramonth losses or margin calls",
                              "Borrowing and financing are assumptions; historical borrow availability is unverified",
                              "Retrospectively known reservoir without prospective validation",
                              "Losses/insolvencies remain recorded without replacing paths; undefined CAGR/Sharpe values are counted",
                              "Frequencies from 50 paths have substantial Monte Carlo error; they are not future probabilities"])
    for name,digest in fingerprints.items():
        if hashlib.sha256((root/"pipeline"/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError(f"{name} changed during simulation; rerun")
    exposure_path=root/"data/holdings/holdings.csv"
    if exposure_hash is not None and exposure_path.exists():
        if hashlib.sha256(exposure_path.read_bytes()).hexdigest()!=exposure_hash:
            raise RuntimeError("Holdings snapshot changed during simulation; rerun")
    _write(out/"mc_dynamic_summary.json",summary)
    table.to_csv(out/"mc_dynamic_paths.csv",index=False)
    trace_table=pd.DataFrame(trace)
    trace_table.to_csv(out/"mc_dynamic_trace.csv",index=False)
    assert (trace_table.training_last<trace_table.holding_index).all()
    np.testing.assert_array_equal(draws[:,:20],stationary_indices(len(observed),paths,20,MEAN_BLOCK_MONTHS,seed))
    _write(out/"mc_dynamic_verification.json",dict(passed=True,paths=paths,optimizer_fits=refits,
        max_target_constraint_violation=max_violation,
        checks=["60 synthetic returns precede each decision",
                "The same vector is sampled for ETFs, cash and FX",
                "Two optimizations per month: long/short and long only",
                "Account separates cash, collateral and debt",
                "Borrowing/financing costs charged without duplicating distributions",
                "Current frozen matrix explicitly identified as retrospective",
                "Insolvent paths are neither removed nor restarted",
                "Model and accounting sources did not change during execution",
                "Seed and training before the holding period verified"] ))
    print(f"Dynamic MC v2 completed: {paths} paths, {refits} reoptimizations in {summary['elapsed_seconds']:.1f}s.",flush=True)
    return summary


def run(root=None, paired_only=False, dynamic_only=False, paths=DYNAMIC_PATHS,
        test_months=DYNAMIC_TEST_MONTHS):
    result={}
    if not dynamic_only:result["paired"]=paired(root)
    if not paired_only:result["dynamic"]=dynamic(root,paths=paths,test_months=test_months)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--paired-only",action="store_true")
    parser.add_argument("--dynamic-only",action="store_true")
    parser.add_argument("--paths",type=int,default=DYNAMIC_PATHS)
    parser.add_argument("--test-months",type=int,default=DYNAMIC_TEST_MONTHS)
    args=parser.parse_args()
    run(paired_only=args.paired_only,dynamic_only=args.dynamic_only,
        paths=args.paths,test_months=args.test_months)
