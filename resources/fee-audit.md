# Fee profile audit, 1 November 2026

`data/fee_profiles.csv` is a separate descriptive metadata layer. It does not
change `universe.csv`, any frozen price, model input, or earlier SHA-256 hash.
Every one of the 61 candidates was requested through yfinance `Ticker.info`.
Raw fields, provider URL, retrieval time and request status are retained.

## Units and source hierarchy

`official_fee_pct` is an annual percentage, so a value of 0.03 means 0.03% per
year, not 3%. It is populated only from issuer material. For values already
verified during the original data audit, the issuer reference is retained.
New sources, dates and capture qualifications are in `official_source`,
`official_asof` and `official_status`.

Yahoo returned `netExpenseRatio` for a subset of the catalogue. The JSON raw
value is retained unchanged in `provider_fields_json`. Where it equals an
issuer's percentage, the per-ticker unit comparison is recorded. When no
issuer verification exists, units remain explicitly unconfirmed. A raw value
is never multiplied or divided by 100 merely because it appears plausible.

One concrete disagreement is IWQU: Yahoo returns 0.30 while BlackRock's opened
product page reports TER 0.25%. The issuer value takes precedence. This is why
the provider fields are not blindly normalized into verified fees.

## Main issuer evidence

- Vanguard September 2026 fact sheet VT, p. 1: 0.06%.
  https://institutional.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/fact-sheet/F3141.pdf
- Vanguard September 2026 VOO fact sheet, p. 1: 0.03%.
  https://workplace.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/fact-sheet/F0968.pdf
- Vanguard September 2026 VTI investment profile, p. 3: 0.03%.
  https://institutional.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/investment-profiles/0970.pdf
- Vanguard fee reductions effective 1 February 2026: VIG 0.04%, VWO 0.06%,
  VUG 0.03%, VYM 0.04%, VB 0.03%, VBR 0.05%, VTV 0.03%.
  https://corporate.vanguard.com/content/dam/corp/articles/pdf/expense_ratio_reduction_jan2026.pdf
- Vanguard September 2026 VXUS fact sheet: 0.05%; VOOG fact sheet: 0.07%.
  https://institutional.vanguard.com/assets/corp/fund_communications/pdf_publish/us-products/fact-sheet/F3369.pdf
  https://fund-docs.vanguard.com/F3341.pdf
- Invesco QQQ issuer page: current TER 0.18%.
  https://www.invesco.com/qqq-etf/en/home.html
- Avantis September 2026 AVUV fact sheet, p. 1: 0.25%.
  https://res.avantisinvestors.com/docs/avantis-us-small-cap-value-avuv-etf-fact-sheet.pdf
- Vanguard VWRD/VWRL distributing share class page: OCF/TER 0.14%. The page
  explicitly identifies the USD London VWRD line under the same ISIN. This
  current retrieved rate supersedes older issuer product lists showing 0.19%.
  https://www.vanguard.co.uk/professional/product/etf/equity/9505/ftse-all-world-ucits-etf-usd-distributing
- Vanguard VHVE page: OCF/TER 0.12%. HTML was fetched with `requests` because
  the web reader intermittently timed out; the fee and USD London line were
  present in the issuer HTML.
  https://www.vanguard.co.uk/uk-fund-directory/product/etf/equity/9675/ftse-developed-world-ucits
- BlackRock: IWDA 0.20%, ISAC 0.20%, EIMI 0.18%, IWQU 0.25%. The pages
  identify the relevant share class and listing; UK page titles may show the
  GBP ticker for the same ISIN, so the listing table was also checked.
  https://www.ishares.com/nl/particuliere-belegger/nl/producten/251882/SWDA?siteEntryPassthrough=true&switchLocale=y
  https://www.ishares.com/uk/individual/en/products/251850/ishares-msci-acwi-ucits-etf
  https://www.ishares.com/uk/individual/en/products/264659/ishares-msci-emerging-markets-imi-ucits-etf
  https://www.ishares.com/uk/professionals/en/products/270054/iwqu

VEA 0.03% is supported by a current issuer indexed record dated 28 April 2026,
but full primary page capture was limited by client-side rendering. It is
marked `issuer_indexed_record_only`, unlike the directly fetched documents.

## Interpretation and remaining work

These are current descriptive expense ratios, not a historical time series.
Some were retrieved after the study's frozen price cutoff. They were not used
to choose assets retrospectively or to optimize a historical wrapper policy.
Fund operating expenses are already embedded in observed fund performance;
deducting this table again would double count them. The portfolio's additional
management fee and trading costs are separate modeled costs.

Not all B3 and UCITS profiles publish fee fields through Yahoo. Missing values
remain unknown and require the issuer's current prospectus or product document.
No missing fee is zero. Fee profiles alone do not establish the cheapest or
tax-optimal wrapper: domicile, investor withholding, capital gains taxation,
spreads, FX costs, custody and access constraints still need separate work.

The 21 currently positive candidate positions all have an issuer-supported
rate in this supplement, including the explicitly qualified VEA indexed
record. This does not turn the candidate allocation into the preferred result
of the statistical study.
