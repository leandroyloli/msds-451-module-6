# Holdings v2 — sources, coverage and limitations

Frozen dataset: 46 of 61 candidates have complete recovered issuer/regulator files, with 68,260 normalized positions. All 61, including unavailable candidates, remain in `data/holdings/coverage.csv`. The manifest records sources, dates and hashes. A complete source file does not imply complete classification or recursive expansion of every internal position.

## Primary sources

- Vanguard: public holdings API discovered in the issuer's JavaScript, `advisors.vanguard.com/investments/products/api/funds/{id}/holdings/latest`; September 30, 2026 snapshots retained as JSON.
- iShares/BlackRock: complete `latest-holdings.csv` endpoints and Brazilian exports; October 30, 2026 snapshots retained as CSV.
- SPY: official State Street XLSX, converted without changing source values; October 29, 2026.
- B3 funds: official September 2026 CVM CDA archive, `https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/cda_fi_202609.zip`. The ZIP and CNPJ-specific rows remain saved, including DIVO11 and other local funds. BOVA11 uses the latest recovered BlackRock snapshot.

## Transformations

Weights are fractions of net assets. Complete iShares market values reconstruct weights more precisely than rounded published percentages. No missing holdings were invented. Vanguard's duplicated fund-reserve section was removed to avoid counting the same cash twice.

Share classes are grouped by normalized issuer name. Classifications and currencies are transferred across sources only through identifiers or exact, nonconflicting security/name/country matches. The subindustry-to-sector crosswalk requires agreement in primary holdings. The original Portuguese equity label is normalized to `Equity`, avoiding false exclusion of BOVA11 from equity coverage.

Currency means the underlying security's quotation currency when identifiable, not company revenue currency or an economic FX hedge. Unknown fields remain empty and consume the unknown-exposure budget.

IVVB11 and WRLD11 underlying funds are expanded recursively using current IVV/VT snapshots. These mixed dates are explicitly qualified. NASD11 and VWRA11 still contain opaque unexpanded positions: a complete CVM file does not justify assuming complete economic coverage.

## Material limitations

Complete historical portfolios for 2019–2026 were not recovered. Applying this matrix to earlier returns is a frozen-holdings retrospective experiment, not causal certification of historical limits. SPY country coverage was not adequately recovered; industry/currency gaps remain measured by fund. Market-value weights do not replace full derivative notional/delta analysis. None of the sources establishes historical ETF borrow availability.

## Final checks

Coverage contains 61 unique rows; holdings contain 68,260 positions with numerical weights and issuer identifiers. Holdings/coverage hashes reconcile with the manifest. Final data were published atomically without changing the previous study.
