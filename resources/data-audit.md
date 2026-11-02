# Checkpoint B: source and data audit

Prepared 1 November 2026. This note documents the data; it is not a claim of
out-of-sample investment performance or complete product due diligence.

## Catalogue and collection

- Exactly the 61 tickers in `msds-451-module-4/report/06-next-steps.md` are
  catalogued in `data/universe.csv`: 27 US listings, 15 London listings, two
  Xetra listings and 17 B3 listings. No candidate was silently dropped.
- All 61 supplied a positive adjusted daily price series. The frozen combined
  file has 221,045 ETF observations, with no duplicate ticker/date pair, no
  nonpositive adjusted price and no infinite value.
- New requests use Yahoo Finance through yfinance 1.7.0, start 2000-01-01,
  end 2026-10-24 exclusive. The final possible observation is 23 October 2026.
- The nine previously downloaded ETFs (the PA2 eight plus AUVP11) preserve
  their exact PA2 source rows. They were downloaded on 25 October 2026. The
  other 52 ETFs and EUR/USD were collected on 1 November 2026. This is an
  explicitly mixed retrieval snapshot, not an unrecorded blend within series.
- `data/sources.json` records each source, row count, observed first/last date,
  quote currency, retrieval time, source URL and SHA-256 hashes. Historical
  vendor corrections remain possible. First observed price is not asserted to
  equal the issuer's legal inception or first exchange trading day.

## Price and currency contract

- `daily_prices.csv`: date, ticker, Yahoo symbol, quote currency, close,
  adjusted close, distributions and splits. Dividends are retained for audit,
  never added a second time to adjusted-price returns.
- `fx.csv`: date, symbol, close. BRL=X means BRL per USD, GBPUSD=X means USD
  per GBP, EURUSD=X means USD per EUR.
- Brazilian quotes convert by dividing by BRL per USD. GBP and EUR quotes
  convert by multiplying by the relevant USD cross. Conversion occurs before
  calculating USD returns or aggregating monthly prices.
- Yahoo history metadata confirms all quote currencies. VHYL.L and VUSA.L
  are GBP; ZPRV.DE and AVWS.DE are EUR. The other selected London lines are
  USD. Fund base currency and economic exposure are separate concepts.
- If Yahoo returns GBp/GBX, the collector divides close, adjusted close and
  distributions by 100 and records this unit normalization. None of the final
  61-series collection required that normalization.
- Daily conversion uses the same-day or latest earlier FX quote, never a
  later quote, with a maximum five-calendar-day tolerance. Market closing
  times differ across London, New York and B3: date alignment is not a claim
  of simultaneous executable quotes.

## Monthly and daily functions

`pipeline.data.load_monthly(root=None)` returns:

1. USD adjusted price DataFrame with month-end datetime index and ticker columns;
2. month-end USD/BRL Series;
3. a 61-row coverage DataFrame.

The panel spans January 2000 through September 2026. It uses last observed
local-exchange prices, converted with backward FX, provided the source quote is
no older than seven calendar days at month end. October 2026 is incomplete at
the frozen cutoff and is excluded. Prices are missing before each ETF exists;
no historical index, sister share class or another ETF fills that history.
There are no missing months inside an individual fund's observed monthly span.

56 candidates have at least 61 monthly endpoints at the cutoff (enough to form
60 monthly returns). The five that do not are AVWS (24 prices), AUVP11 (13),
BEST11 (12), WRLD11 (60) and VWRA11 (13). This is only endpoint coverage.
Actual walk-forward admission must test the history available at each decision
date, not use this final flag for earlier years.

`pipeline.data.load_daily(root=None)` returns observed adjusted USD prices on
the union calendar plus observed USD/BRL. It does not forward-fill ETF prices.
Any bounded stale-price convention for daily portfolio valuation belongs to the
backtest and must be disclosed independently of observed market prices.

## Gaps and liquidity

The complete list of gaps longer than seven calendar days is saved as
`data/price_gaps_over_7days.csv`. After July 2019 only one qualifies: CNDX's
price on 5 January 2026 follows the 24 December 2025 quote, a 12-day interval.
GOVE11's earlier 8–16-day intervals end before July 2019. The absence of a
Yahoo quote is not automatically proof that an exchange was closed.

`data/daily_liquidity.csv` contains separately refreshed reported volume and
quote close for every ETF. `dollar_volume_usd` is quote close times reported
volume times the relevant FX conversion. It is a turnover proxy, not an
executable spread or market-depth estimate. The liquidity refresh never
replaces frozen prices. `data/liquidity_sources.json` records source status
and hashes.

`data/liquidity_monthly.csv` uses only observations known by each month end:
trailing six-calendar-month median dollar volume, observation count and share
of reported zero-volume days. A model may use this for a causal liquidity
screen. Zero reported volume is left visible, not silently replaced. A price
gap filter must also use only gaps completed before that historical decision.

Large observed daily USD movements occur in crises. The largest absolute
one-observation USD return in the unfilled panel is about 21.44%, PIBB11 on
13 October 2008; GOVE11 reaches about 20.30% on 12 March 2020. They were not
winsorized or deleted because doing so would erase relevant tail observations.

## Product metadata and corrections

- The A catalogue incorrectly described WRLD11 as IT Now MSCI World. The
  issuer identifies it as Investo's B3 feeder of VT, FTSE Global All Cap.
  Opened source: https://www.investoetf.com/etf/wrld11/ (1 November 2026).
- BEST11 is Investo's MarketVector Brazil BESST Quality exposure, not a
  generic broad-market fund. Source: https://www.investoetf.com/como-investir/.
- The groups in `exposure_group` are research classifications. Similar
  economic exposures are not necessarily exact index, domicile or tax
  substitutes. For example, VWO, IEMG and EIMI have different benchmark details;
  VYM and global VHYL are deliberately different groups.
- `country_US` and `country_BR` contain only structurally known 0/1 values.
  Global funds' country fractions remain missing. They are not fabricated
  current holdings or point-in-time country allocations. Current holdings
  obtained later must not be backfilled into historical portfolio decisions.
- Fees verified from opened issuer sources are supplied for 11 ETFs. The
  other 50 values remain explicitly unknown, not zero. Fees are current
  descriptive metadata and are not used to reconstruct historical cost rates.
  All fund operating expenses already reflected in market-price performance
  must not be deducted twice.

Verified fee sources:

- iShares US product list dated 1 September 2026, pp. 1–2 and 5:
  IVV 0.03%, ITOT 0.03%, DGRO 0.08%, IEMG 0.09%, DVY 0.38%, QUAL 0.15%,
  MTUM 0.15%, USMV 0.15%.
  https://www.ishares.com/us/literature/brochure/ishares-product-list-en-us.pdf
- Vanguard's VT product page reports 0.06% expense ratio; retrieved issuer
  search record dates it 27 February 2026. The direct client-rendered page had
  no readable body in the web fetch; therefore this is less directly captured
  than the iShares PDF and should be rechecked before actual implementation.
  https://advisors.vanguard.com/investments/products/vt/vanguard-total-world-stock-etf
- Vanguard VHYL product page: OCF/TER 0.29%, GBP market quote and Irish domicile.
  https://www.vanguard.co.uk/professional/product/etf/equity/9506/ftse-all-world-high-dividend-yield-ucits
- State Street ZPRV product page: TER 0.30%, Xetra EUR line ZPRV.DE, Irish
  domicile; this is US small-cap value exposure despite its EUR quote.
  https://www.ssga.com/at/en_gb/institutional/etfs/state-street-spdr-msci-usa-small-cap-value-weighted-ucits-etf-zprv-gy

## Remaining limits

This is a preselected survivor catalogue inherited from Checkpoint A, not a
point-in-time census containing delisted ETFs. Historical membership and fund
closures are not reconstructed. Vendor-adjusted returns are an approximation
to reinvested market returns, before each investor's taxes, execution prices,
currency conversion spread and additional management charges. The catalogue
does not yet establish the tax-optimal wrapper for a Brazilian resident, or
complete historical issuer/sector/security-level look-through. Those limits
must stay visible in any recommended portfolio.
