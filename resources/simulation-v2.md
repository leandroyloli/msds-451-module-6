# Monte Carlo for the long/short study

`pipeline/simulation_v2.py` writes to `output/`. The original study remains preserved outside this repository.

## Experiment 1: uncertainty in the net process

- Saved daily net returns are compounded geometrically into complete months. Embedded costs are not deducted again.
- Circular paired stationary bootstrap gives strategies, cash and FX the same sampled index each month. Expected block length is six months, with a fixed seed.
- 10,000 paths span 300 months (25 years). Percentiles are conditional scenarios, not calibrated future probabilities.
- Historical-horizon confidence intervals use 2,000 resamples separately with expected block lengths 3, 6 and 12 months; the most favorable block is not selected afterward.
- Monthly Sharpe annualizes by square root of 12. Drawdown is observed at month-end and may miss larger intramonth losses. BRL conversion is reported without a BRL Sharpe referenced to USD cash.

Replay measures variability of the observed net process; it does not refit the optimizer at each synthetic step.

## Experiment 2: synthetic returns with new decisions

- Fix the June 2019 history/liquidity-eligible universe, intersected with current complete holdings coverage.
- Use jointly available ETF, cash and FX vectors. The reservoir starts July 2014, includes COVID and ends September 2026, subject to complete common coverage.
- Generate 50 paths, each with 60 training and 60 testing months.
- Refit expected returns, covariance and both long/short and long-only portfolios each month: 6,000 fits absent insolvencies.
- A holding-period return never enters its own training window. Monthly cash return is approximated from the latest DGS3MO yield known before the source month.
- Use the same constraints, bands, trading, management, borrowing and financing rules.
- Separate signed holdings, cash, collateral and debt. Adjusted returns already include distributions; shorts do not pay them twice.
- Margin breaches detected at the previous close are liquidated at the next monthly execution. This is an approximation, not a daily broker simulation. Insolvent paths retain deficits and are never discarded; undefined metrics remain missing with explicit counts.
- Record path-level outcomes and a verification trace. Model and accounting hashes must remain unchanged during simulation.

## Mandatory visible limitation

The company/sector/country/currency matrix is a current issuer snapshot. Freezing it over earlier prices creates a retrospective scenario, not causal validation of historical concentration.

Chronological prices and training do not remove future information in the frozen matrix or current universe coverage. Faithful historical execution requires complete holdings known at each decision. With 50 dynamic paths, frequencies have two-percentage-point resolution and maximum Monte Carlo standard error about 7.1 points, in addition to uncertainty in data, returns, borrowing and future regimes.

## Outputs

Paired outputs include `mc_summary.json`, monthly returns, percentile paths, terminal samples, intervals and verification. Dynamic outputs include `mc_dynamic_summary.json`, path metrics, reservoir, cash-source record, trace and verification. Later translation changes are separately documented; they do not imply a new simulation execution.
