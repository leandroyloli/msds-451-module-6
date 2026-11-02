"""Filtros causais e escolha fixa de representantes equivalentes."""
from functools import lru_cache
import pandas as pd
from . import config_v2 as c

@lru_cache(maxsize=1)
def liquidity_history():
    return pd.read_csv(c.ROOT/"data/liquidity_monthly.csv",parse_dates=["date"])


def select_assets(prices, signal_date, meta, months=c.TRAIN_MONTHS):
    """61 consecutive monthly prices -> 60 returns KNOWN by the signal date."""
    history = prices.loc[:signal_date].tail(months + 1)
    if len(history) != months + 1:
        raise ValueError("Insufficient training history")
    eligible = history.columns[history.notna().all()].tolist()
    liquidity=liquidity_history()
    liq=liquidity.loc[liquidity.date.eq(signal_date)].set_index("ticker")
    valid=liq.index[(liq.median_dollar_volume_6m>=c.MIN_MEDIAN_DOLLAR_VOLUME)&
                    (liq.observations>=c.MIN_LIQUIDITY_OBSERVATIONS)]
    eligible=[t for t in eligible if t in valid]
    selected = eligible.copy()
    for family in c.EQUIVALENTS:
        alternatives = [t for t in family if t in eligible]
        for t in alternatives[1:]:
            selected.remove(t)
    # Ordering is catalogue order, never a return ranking.
    return [t for t in meta.index if t in selected], eligible


