# Long/short portfolio accounting — v2

`pipeline/execution_v2.py` adds signed accounting. Allocation constraints belong to the calling model; the account handles money and does not alter the earlier study's prices or results.

## API

- `Account(initial_nav=1)` starts with one cash unit and no positions.
- `holdings` contains USD values, positive for longs and negative for shorts.
- `cash`, `collateral` and `debt` are separate USD balances.
- `nav = sum(holdings) + cash + collateral - debt`.
- `long_value` and `short_value` are absolute USD values; `long`, `short`, `gross` and `net` divide exposures by NAV.
- `margin_required` is the policy's USD maintenance requirement; `margin_ratio` divides it by NAV.
- `rebalance(target, cost_rate=.001)` trades weights whose net sum is one.
- `mark(returns)` applies one period's total returns and remarks collateral.
- `accrue(days, rfannual, ...)` charges interest and fees through cash/debt.
- `liquidate(cost_rate=.001)` closes positions, releases collateral and repays debt only as far as wealth permits. An unpaid deficit remains recorded; insolvency never becomes positive cash.

## Short sales do not create wealth

With net weights summing to 100%, a 120% long / 20% short portfolio still has 100% wealth and 140% gross exposure. The conservative study assumption restricts all short proceeds as unremunerated collateral. For short value `S` and multiplier `h`, collateral is `h*S`; separate financing is also `h*S` after rebalancing.

For `h=1`:

| Balance | Value per unit of wealth |
|---|---:|
| Long ETFs | 1.20 |
| Short ETF obligation | −0.20 |
| Restricted collateral | +0.20 |
| Financing | −0.20 |
| Net wealth | 1.00 |

This avoids double-counting proceeds. A short-price increase raises required collateral, financed by debt; a decrease releases collateral and reduces debt first. Collateral transfers create no profit or loss. Only asset movements and charges change NAV.

## Costs

Defaults, explicitly overridable by the caller:

- Additional management: 0.25% annually on positive wealth.
- Borrowing: 2% annually on short value.
- Financing: supplied lagged annual USD cash rate plus one percentage point, charged on recorded debt.
- Collateral rebate: zero.
- Free cash: supplied USD cash rate unless configured otherwise.
- Trading: 0.10% of all bought/sold value, including initial entry and opening/closing shorts.

Charges use calendar days/365 and pass through cash or financing. Positions are not silently sold or rescaled daily to pay fees. Accrued debt reduces NAV and is economically settled at the next trade or liquidation.

Adjusted returns already include distributions. A negative weight reverses total return, including distributions; charging the short dividend again would duplicate cost. This is a total-return-unit representation, not a share/distribution ledger with individual payment dates.

## Self-financing rebalancing

For old signed values `v`, target weights `w`, proportional cost `c` and old wealth `N`, solve:

`N_after = N - c * sum(abs(w * N_after - v))`.

New positions are `w*N_after`. New collateral and debt offset; accrued interest is not forgiven. An independent cash identity reconciles buys, sells and repayment of old financing.

## Margin and failure

Maintenance is the academic USD proxy `0.25*long_value + 0.30*short_value`, not certification of any broker, market or ETF margin rules. Borrow availability, changing fees, recalls and product differences require operational data; account-specific brokerage terms are not invented.

`margin_breached` flags insufficiency. The account does not sell using the same quote that revealed the breach; the temporal engine must schedule a later executable action. Insolvency remains an event and no failed Monte Carlo path is removed.

## Verification

`self_test()` returns checks without writing by default. Explicit output:

```powershell
uv run --no-project --with-requirements requirements.txt python -m pipeline.execution_v2 --self-test --output output/execution_v2_checks.json
```

Tests cover entry, short gains/losses, collateral without fictitious profit, costs, no hidden daily trading, solvent/insolvent closure and 100 periods of random movements.
