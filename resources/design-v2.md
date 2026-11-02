# Design v2: long/short growth block with underlying concentration limits

Research and review: November 1, 2026. This memo proposes study policies, not the investor's personal tolerance or universally optimal percentages. Values should be recorded before comparing outcomes. Some alternatives below document design-stage proposals; implemented values are authoritative in `pipeline/config_v2.py` and `output/design.json`.

## 1. Scope and comparisons

Choose ETFs and weights for block C. Safety and inflation blocks remain outside decision variables, collateral and financing. Approved filters are 60 complete monthly returns, median daily dollar volume of USD 1 million and at least 100 observations in the prior six months. These filters use information available at the signal.

Negative weights enlarge the feasible set without imposing a minimum short position. A long-only optimum is legitimate if estimates, costs and constraints favor it; forecasts or weights must not be manipulated to manufacture shorts.

The main comparison is long-only versus long/short using the same data, auditable exposures, costs and rules. VT and 1/N remain benchmarks. Missing a benchmark margin does not automatically replace the fund's portfolio with its benchmark.

## 2. Expected returns

The earlier beta × 4% prior has little independent information and is not an alpha forecast. Jorion (1986) motivates reducing mean-estimation error, but does not prove a chosen 50/50 mixture.

Two honest options were considered:

1. Empirical mean shrinkage. DeMiguel, Garlappi and Uppal's appendix describes Bayes–Stein shrinkage toward the global minimum-variance portfolio's mean. Intensity depends on mean dispersion, covariance and sample size. Its indexed content was available, but the direct NBER PDF returned 404; complete PDF access is not claimed.
2. A disclosed fixed mixture of historical means and a market prior. A 50/50 policy would require 25/75 and 75/25 sensitivities and must not be presented as proven optimal.

Using Ledoit–Wolf covariance instead of Jorion's corrected sample matrix is an adaptation inspired by Bayes–Stein, not exact replication. Fit on only the previous 60 returns and refit inside synthetic scenarios.

Operational formula:

```
m = monthly sample mean; C = regularized monthly covariance
q = C^-1 1 / (1' C^-1 1)
m0 = q' m
phi = (N+2) / ((N+2) + T (m-m0 1)' C^-1 (m-m0 1))
m_shrunk = (1-phi) m + phi m0 1
```

`q` is an estimation device, not the recommended portfolio; it may be signed. Final optimization imposes the mandate's constraints.

## 3. Caps tied to explicit shocks

These are proposed risk budgets, not percentages optimized on the evaluation sample.

| Proposed limit | Operational rationale / shock budget |
|---|---|
| ETF weight −5% to +20% | Limits individual shorts and reliance on one vehicle; actual borrow capacity remains unverified. |
| Net exposure 100% | Keeps block C equity-oriented; it does not eliminate debt or collateral. |
| Gross exposure up to 140% | With 100% net, longs can reach 120% and shorts 20%; using all leverage is not a target. |
| Company/issuer 5% gross | An isolated 50% shock costs at most 2.5 NAV percentage points before joint shocks and costs. Wider corporate groups need separate mapping. |
| Sector 35% gross | An isolated 40% sector shock costs up to 14 NAV points; 30% and 40% sensitivities test this budget. |
| Largest country 75%, each other 25% gross | Limits geographic dependence. A 30% isolated largest-country shock could cost 22.5 NAV points; revise if incompatible with the mandate. |
| Monthly CVaR95 up to 15% | Limits average modeled worst-5% monthly loss, not cumulative drawdown or unseen maximum loss. |

Avoid decorative constraints. A fund-family cap may be removed when full company/sector/country exposures already control economic concentration, unless an operational reason is documented. A compulsory 20% global-fund floor is not needed: actual holdings should establish diversification without prescribing a ticker or wrapper.

Currency must have an auditable definition. An ETF's listing currency is not its companies' currency exposure. Underlying quotation currency is a proxy, not revenue/debt/hedging exposure. The design considered illustrative USD 85% and other-currency 35% caps only if coverage and feasibility supported them; the implemented policy applies the configured 85% per-currency cap. Neither number is established by the literature.

## 4. Look-through and missing data

For nonnegative constituent weights `h[j,i]`:

```
company j net exposure   = sum_i w_i h[j,i]
company j gross exposure = sum_i abs(w_i) h[j,i]
```

Constraints use gross exposure, while diagnostics show gross and net. Apply the same principle to sectors and countries so near-identical long and short funds cannot hide large positions through netting.

Combine share classes of one issuer, for example GOOG/GOOGL, using auditable identifiers; ADR and local listings may represent the same company. Do not claim complete corporate-group consolidation when only share classes were combined. GICS classifies at company level and propagates to securities; differing provider taxonomies require verified harmonization.

A top-ten list is not complete holdings. Keep unknown exposure, measure coverage and exclude unsupported funds. Never fill unknowns with zero or renormalize top holdings to 100%. An aggregate unknown budget is conservative but strong worst-case company certification would also allocate unknown exposure to every possible issuer.

An October 2026 snapshot was unavailable in 2019. It can support a current portfolio and a frozen retrospective test, not point-in-time validation of historical concentration. This must appear beside main results, not only in a distant footnote.

## 5. Signed accounting and financing

Let `L` be long value and `S` absolute short value as fractions of NAV. The chosen net mandate is `L-S=1`; 120/20 means 140% gross risk.

Restricted-proceeds model: short proceeds are collateral, not free capital. For collateral `K=hS`, `h>=1`:

```
D = max(L - 1 - S + K, 0)
NAV = L + K - S - D
if L-S=1, D=K and NAV=1
annual financing flow = K*rebate - D*debit_rate - S*borrow_rate
```

With `h=1` and zero rebate, annual short cost is `S*(cash_rate + debit_spread + borrow_rate)`. This is a conservative study assumption, not a particular broker account. IBKR distinguishes borrow fees and proceeds interest, varying by security and account size.

The design-stage example proposed a 1.5% debit spread and 2% borrow fee, with 1%, 3% and 5% borrow sensitivities. The implemented base uses a 1-point debit spread and 2% borrow fee, with the documented 5% sensitivity; configuration governs actual results. Historical borrow rates and availability were not observed. A candidate borrow flag is not a verified locate.

Adjusted total returns already incorporate distributions, including shorts' opposite economic effect; do not charge dividends twice. Internal fund expenses already reflected in prices must not be deducted again. Borrowing, financing, additional management and trading remain separate.

Regulation T, FINRA and house margins vary. An academic initial proxy `0.50L+0.50S` and maintenance `0.25L+0.30S` are not universal compliance. Monitor NAV against requirements; reduce exposure or record margin/liquidation events after adverse movements. Do not use blocks A/B. Borrow recall is a further sensitivity if historical availability is absent.

## 6. Optimization and execution

Expected returns, costs and risk must use consistent time units. With nonnegative `p,n`, `w=p-n`, shorts are `sum(n)` and gross is `sum(p+n)`. Costs discourage simultaneous long/short positions in the same ETF; verify no such redundant exposure remains.

For a positive Sharpe target, `numerator >= target*sigma` is convex when the numerator is linear less convex costs. Conic optimization or bisection is suitable. If SLSQP with absolute values and empirical CVaR is used instead, check feasibility and do not promise a global optimum.

Scenario CVaR uses threshold `z` and excess losses `u`:

```
u_s >= loss_s(w)-z; u_s >= 0
z + sum_s u_s / ((1-alpha)*M) <= CVaR_limit
```

At 60 observations and 95% confidence, the modeled tail has very few observations. Joint bootstrap adds scenarios, not new regimes. A universal −50% equity shock cannot coexist with a promised 15% maximum loss and net equity exposure near one without another hedge/asset. Keep such stress separate rather than silently relaxing mathematics.

Use only information through the signal and execute later. Existing positions receive returns through execution. Reducing longs and opening shorts are different operations but both incur trading cost. Fees reduce NAV through self-financing accounting. Adverse price moves can enlarge shorts and require margin control between rebalances.

## 7. Reporting and primary references

No minimum short position and no requirement to hold all 61 funds. Audit every exclusion. Compare identical estimation/risk rules with and without shorts. Keep equal weight and a global ETF as benchmarks without automatically selecting them as the recommendation.

The report addresses why the fund exists, supporting research, weight calculation, net test results and remaining validation. Show allocation, underlying concentration and active constraints before implementation detail; keep sources and the 61-candidate catalogue in collapsed appendices.

Primary evidence accessed: Jorion's Cambridge abstract (not full text); indexed DeMiguel/Garlappi/Uppal appendix (direct PDF 404); Rockafellar/Uryasev original publication records and abstracts; MSCI GICS official PDF served as April 2026 despite its older URL; FINRA Rule 4210; and official IBKR cost, financing and margin documentation. Full bibliographic records and access qualifications are in `references-v2.json`.
