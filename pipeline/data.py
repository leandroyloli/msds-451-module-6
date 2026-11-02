"""Leitura dos inputs congelados; sem dependências de pastas irmãs."""
from pathlib import Path
import hashlib
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
LAST_COMPLETE_MONTH=pd.Timestamp("2026-09-30")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_monthly(root=None):
    """Return monthly adjusted USD prices, USD/BRL series, and 61-row coverage.

    Daily FX uses the same or latest previous observation, tolerance 5 calendar
    days. Currency conversion precedes sampling; last observed monthly price
    must be no older than 7 calendar days at month end. No partial October 2026.
    """
    root = Path(root or ROOT)
    universe = pd.read_csv(root/"data"/"universe.csv")
    daily = pd.read_csv(root/"data"/"daily_prices.csv", parse_dates=["date"])
    fx = pd.read_csv(root/"data"/"fx.csv", parse_dates=["date"])
    assert not daily.duplicated(["date", "ticker"]).any()
    assert daily.date.max() <= pd.Timestamp("2026-10-23")
    assert (daily.adjusted_close > 0).all()
    rates = {}
    for symbol in ["BRL=X", "GBPUSD=X", "EURUSD=X"]:
        rates[symbol] = fx.loc[fx.symbol.eq(symbol), ["date", "close"]].sort_values("date")
    columns, coverage = {}, []
    for row in universe.to_dict("records"):
        ticker = row["ticker"]
        g = daily.loc[daily.ticker.eq(ticker)].sort_values("date").copy()
        rec = {"ticker":ticker, "symbol":row["symbol"], "quote_currency":row["quote_currency"]}
        if g.empty:
            rec.update(status="unavailable", first_date=None, last_date=None, daily_rows=0,
                       monthly_prices=0, five_year_history=False, note="No verified adjusted-price series returned; no proxy used.")
            coverage.append(rec)
            continue
        currency = str(g.quote_currency.iloc[0])
        assert g.quote_currency.nunique()==1
        if currency == "USD":
            g["usd"] = g.adjusted_close
        else:
            symbol = {"BRL":"BRL=X", "GBP":"GBPUSD=X", "EUR":"EURUSD=X"}[currency]
            paired = pd.merge_asof(g[["date", "adjusted_close"]],rates[symbol].rename(columns={"close":"fx"}),
                                   on="date", direction="backward", tolerance=pd.Timedelta(days=5))
            g["usd"] = paired.adjusted_close.to_numpy() / paired.fx.to_numpy() if currency=="BRL" else paired.adjusted_close.to_numpy()*paired.fx.to_numpy()
        # A date belongs to the local exchange day, normalized before conversion.
        g["month"] = g.date.dt.to_period("M").dt.to_timestamp("M")
        sample = g.groupby("month", sort=True).tail(1).set_index("month")
        valid = (sample.index <= LAST_COMPLETE_MONTH) & ((sample.index-sample.date).dt.days <= 7)
        sample = sample.loc[valid]
        series = sample.usd.rename(ticker)
        columns[ticker] = series
        count = series.notna().sum()
        rec.update(status="available", first_date=str(g.date.min().date()), last_date=str(g.date.max().date()),
                   daily_rows=len(g), monthly_prices=int(count), five_year_history=bool(count>=61),
                   first_month=str(series.first_valid_index().date()) if count else None,
                   last_month=str(series.last_valid_index().date()) if count else None,
                   note="Five-year flag is endpoint feasibility only; walk-forward eligibility must use history known at each date.")
        coverage.append(rec)
    panel = pd.DataFrame(columns).sort_index()
    panel = panel.reindex(pd.date_range(panel.index.min(), LAST_COMPLETE_MONTH, freq="ME"))
    usdbrl = rates["BRL=X"].copy()
    usdbrl["month"] = usdbrl.date.dt.to_period("M").dt.to_timestamp("M")
    usdbrl = usdbrl.groupby("month").tail(1).set_index("month")
    usdbrl = usdbrl.loc[(usdbrl.index<=LAST_COMPLETE_MONTH)&((usdbrl.index-usdbrl.date).dt.days<=7),"close"]
    return panel, usdbrl.rename("USDBRL"), pd.DataFrame(coverage)


def load_daily(root=None):
    """Observed adjusted USD prices on the union calendar; no price filling.

    FX is backward as-of with maximum five calendar days. The caller may apply a
    separately disclosed, bounded stale-price rule solely for daily valuation.
    Missing foreign observations stay missing here. Returns (usd_prices, USDBRL).
    """
    root = Path(root or ROOT)
    daily = pd.read_csv(root/"data"/"daily_prices.csv", parse_dates=["date"])
    fx = pd.read_csv(root/"data"/"fx.csv", parse_dates=["date"])
    out = {}
    for ticker,g in daily.groupby("ticker", sort=True):
        g = g.sort_values("date").copy()
        currency = g.quote_currency.iloc[0]
        if currency == "USD":
            values = g.adjusted_close.to_numpy()
        else:
            symbol = {"BRL":"BRL=X", "GBP":"GBPUSD=X", "EUR":"EURUSD=X"}[currency]
            rate = fx.loc[fx.symbol.eq(symbol),["date","close"]].sort_values("date").rename(columns={"close":"fx"})
            paired = pd.merge_asof(g[["date","adjusted_close"]],rate,on="date",direction="backward",tolerance=pd.Timedelta(days=5))
            values = paired.adjusted_close.to_numpy()/paired.fx.to_numpy() if currency=="BRL" else paired.adjusted_close.to_numpy()*paired.fx.to_numpy()
        out[ticker] = pd.Series(values,index=g.date,name=ticker)
    panel = pd.DataFrame(out).sort_index()
    assert not panel.index.duplicated().any()
    usdb = fx.loc[fx.symbol.eq("BRL=X")].set_index("date").close.rename("USDBRL")
    return panel, usdb


