# Independent review of implementation v2

Review resumed after a server restart. Scope: `model_v2.py`, `study_v2.py`, `execution_v2.py` and `simulation_v2.py`. This is not certification of performance or a real portfolio; final results depend on execution and frozen holdings data.

## Material findings resolved in code

1. Band projection formerly used weights after the closing return that executed the order. It now uses `old_signal`, the same earlier snapshot used by optimization.
2. Numerical weight-equality residuals could violate the stricter cash identity. Weight producers normalize residuals and recheck limits and CVaR.
3. Bands formerly omitted validation after normalization. The inspected version checks net sum, position bounds, gross exposure, `A|w|` and CVaR.
4. Insolvency must not continue trading and recover spontaneously. History liquidates, retains the deficit and freezes the strategy. Conventional metrics become undefined; losses greater than 100% are not clipped to suggest protection.

## Mathematics and accounting

- The homogeneous Sharpe transformation is coherent when a positive expected excess return exists. The earlier review compared it with independent SLSQP on ten synthetic assets: Sharpe difference approximately 6.2e−11 without violation. This records prior evidence, not a new test after restart.
- Long/short variables constrain `A(p+q)`; final validation uses `A|w|`, preventing netting from hiding concentration.
- Mean estimation is Bayes–Stein-inspired with Ledoit–Wolf covariance, not exact Jorion replication or a VT prior.
- `Account` separates holdings, cash, collateral and financing. Proceeds are not counted twice. Adjusted returns already include distributions, including on shorts.
- Current fees pass through cash/debt without hidden daily sales.
- The 23 synthetic accounting checks were repeated after restart without overwriting real results.

## Interpretation conditions

- September/October 2026 snapshots applied to 2019 are a frozen retrospective experiment; chronological prices do not resolve composition look-ahead.
- If all expected excess opportunities are nonpositive, constrained minimum variance is used. Count and disclose those decisions rather than calling every fit maximum Sharpe.
- `TC*12*turnover` annualizes the current decision's projected monthly trade cost, not an independently forecast annual turnover.
- `optimized_` trade diagnostics describe the pre-band target, not the executed portfolio's forecast.
- Final issuer coverage, classification, currency conversion and missing-data sources require stable-file audit.
- Quotation currency is a proxy, not companies' complete revenue/debt FX exposure.
- Borrowing, financing, availability and margin are assumptions, not verified historical brokerage terms.

No new mathematical blocker was identified in inspected versions. This does not replace real-output or final-HTML verification.
