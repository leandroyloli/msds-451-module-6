"""Study policy for the revised long/short growth block; never personal risk estimates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
FIG = ROOT / "figures"
DATA = ROOT / "data"
START, END = "2019-07-01", "2026-09-30"
TRAIN_MONTHS = 60
LONG_MAX = .20
SHORT_MAX = .05
GROSS_MAX = 1.40
COMPANY_MAX = .05
SECTOR_MAX = .35
INDUSTRY_MAX = .20
US_MAX = .75
OTHER_COUNTRY_MAX = .25
CURRENCY_MAX = .85
UNKNOWN_MAX = .02
CVAR_LEVEL = .95
CVAR_MONTHLY_MAX = .15
MANAGEMENT = .0025
TRANSACTION = .001
BORROW = .02
FINANCING_SPREAD = .01
COLLATERAL_MULTIPLIER = 1.
COLLATERAL_REBATE = 0.
BAND = .03
SEED = 451062


def settings():
    return {k:v for k,v in globals().items() if k.isupper() and isinstance(v,(int,float,str))}

MIN_MEDIAN_DOLLAR_VOLUME = 1_000_000.
MIN_LIQUIDITY_OBSERVATIONS = 100
EQUIVALENTS = [['VOO', 'IVV', 'SPY', 'CSPX', 'VUAA', 'VUSA', 'IVVB11'], ['VTI', 'ITOT'], ['VT', 'WRLD11'], ['QQQ', 'CNDX', 'NASD11'], ['VWRD', 'VWRA', 'VWRA11'], ['BOVA11', 'BOVV11', 'BBOV11']]
