"""Funções numéricas preservadas do estudo original, sem runner v1."""
import numpy as np
import pandas as pd
SEED=45106

def asof(series, dates, tolerance=7):
    s = series.dropna().sort_index()
    table = pd.merge_asof(pd.DataFrame({"date":dates}),
                          pd.DataFrame({"date":s.index,"value":s.to_numpy(),"observed":s.index}),
                          on="date",direction="backward",tolerance=pd.Timedelta(days=tolerance))
    return pd.Series(table.value.to_numpy(),index=dates)


def metrics(r,rf,benchmark=None,years=None):
    r=pd.Series(r).astype(float)
    rf=pd.Series(rf,index=r.index).astype(float)
    wealth=np.r_[1.,np.cumprod(1+r.to_numpy())]
    dd=wealth/np.maximum.accumulate(wealth)-1
    years=years or ((r.index[-1]-r.index[0]).days/365.25+1/252)
    excess=r-rf
    s=float(excess.mean()/excess.std(ddof=1)*np.sqrt(252))
    result=dict(terminal=float(wealth[-1]),cagr=float(wealth[-1]**(1/years)-1),
                annual_mean=float(r.mean()*252),volatility=float(r.std(ddof=1)*np.sqrt(252)),
                sharpe=s,max_drawdown=float(dd.min()),worst_day=float(r.min()),
                expected_shortfall_95=float(r[r<=r.quantile(.05)].mean()),
                downside_deviation=float(np.sqrt(np.mean(np.minimum(excess,0)**2))*np.sqrt(252)))
    if benchmark is not None:
        x=(benchmark-rf).to_numpy()
        y=excess.to_numpy()
        X=np.c_[np.ones(len(x)),x]
        alpha,beta=np.linalg.lstsq(X,y,rcond=None)[0]
        active=r-benchmark
        result.update(alpha_annual=float(alpha*252),beta=float(beta),
                      tracking_error=float(active.std(ddof=1)*np.sqrt(252)),
                      downside_capture=float(r[benchmark<0].mean()/benchmark[benchmark<0].mean()),
                      upside_capture=float(r[benchmark>0].mean()/benchmark[benchmark>0].mean()))
    return result


def stationary_indices(n_obs, n_paths, horizon, mean_block=6.0, seed=SEED):
    """Draw circular stationary-bootstrap indices, shared by every input series.

    A block begins at a uniformly selected observation. With probability 1/L
    the next observation starts a fresh block; otherwise it is the next row,
    wrapping circularly at the end of the sample. L is the expected length.
    """
    if n_obs < 2 or n_paths < 1 or horizon < 1 or mean_block < 1:
        raise ValueError("Require observations >=2, paths/horizon >=1, mean block >=1")
    rng = np.random.default_rng(seed)
    indices = np.empty((n_paths, horizon), dtype=np.int32)
    indices[:, 0] = rng.integers(n_obs, size=n_paths)
    for month in range(1, horizon):
        restart = rng.random(n_paths) < 1.0 / mean_block
        fresh = rng.integers(n_obs, size=n_paths)
        indices[:, month] = np.where(restart, fresh, (indices[:, month - 1] + 1) % n_obs)
    return indices


def aggregate_monthly(frame):
    """Geometric monthly aggregation; conservatively omit partial edge months.

    The observed file supplies the valuation calendar. If its first row is
    later than the first weekday, its first month is omitted. If the last row
    predates the last weekday, its final month is omitted. This conservative
    rule can omit a complete month ending in a market holiday, but never labels
    a plainly partial edge month as a whole month.
    """
    frame = frame.sort_index()
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.has_duplicates:
        raise ValueError("Daily returns require a unique DatetimeIndex")
    if frame.empty or frame.isna().any().any():
        raise ValueError("Daily returns must be nonempty and jointly complete")
    if not np.isfinite(frame.to_numpy()).all() or (frame <= -1).any().any():
        raise ValueError("Every daily gross return must be finite and positive")
    monthly = np.expm1(np.log1p(frame).resample("ME").sum())
    first_weekday = pd.date_range(frame.index.min().to_period("M").start_time,
                                  frame.index.min().to_period("M").end_time, freq="B")[0]
    last_weekday = pd.date_range(frame.index.max().to_period("M").start_time,
                                 frame.index.max().to_period("M").end_time, freq="B")[-1]
    omitted = []
    if frame.index.min().normalize() > first_weekday.normalize():
        omitted.append(str(monthly.index[0].date()))
        monthly = monthly.iloc[1:]
    if frame.index.max().normalize() < last_weekday.normalize():
        omitted.append(str(monthly.index[-1].date()))
        monthly = monthly.iloc[:-1]
    if len(monthly) < 24:
        raise ValueError("Fewer than 24 complete monthly return vectors")
    # Independently verify the product identity on every retained month/column.
    check = (1.0 + frame).groupby(frame.index.to_period("M")).prod() - 1.0
    check.index = check.index.to_timestamp("M")
    np.testing.assert_allclose(monthly.to_numpy(), check.loc[monthly.index].to_numpy(),
                               rtol=1e-10, atol=1e-12)
    return monthly, omitted


def _metric_arrays(returns, cash, months):
    """One metric value per path; drawdown includes the initial wealth of one."""
    logs = np.cumsum(np.log1p(returns), axis=1)
    terminal = np.exp(logs[:, -1])
    # max(0, running cumulative log wealth) includes pre-investment wealth=1.
    peaks = np.maximum.accumulate(np.maximum(logs, 0.0), axis=1)
    max_drawdown = np.expm1(logs - peaks).min(axis=1)
    excess = returns - cash
    sd = np.std(excess, axis=1, ddof=1)
    sharpe = np.divide(np.mean(excess, axis=1) * np.sqrt(12.0), sd,
                       out=np.full(len(sd), np.nan), where=sd > 1e-12)
    return dict(terminal=terminal, cagr=np.expm1(logs[:, -1] * 12.0 / months),
                max_drawdown=max_drawdown, sharpe=sharpe), logs


