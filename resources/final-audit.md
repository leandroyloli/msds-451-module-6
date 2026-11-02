# Final review and independent rerun

## Evidence before separating folders

A read-only independent review of the original study found:

- Maximum independently reconstructed wealth error approximately 1.33e−15 per initial capital unit.
- Compounded returns, volatilities and signed limits reconciled for all seven cases at every monthly decision.
- Execution one to five days after signals, with observed quotes for every nonzero traded position.
- BRL conversion and Monte Carlo fingerprints reconciled.
- Long/short regression alpha approximately 0.5306 percentage points/year and beta 0.8520; long-only alpha 0.6115 and beta 0.8502.
- Nine current long positions, although shorts were permitted. No short was forced to change the result.

These observations document origin, not a replacement for this folder's rerun.

## Evidence in this folder

Path separation changed helper source files. Results were therefore rerun instead of rewriting old fingerprints. Authoritative execution records are `../output/verification.json`, `../output/mc_dynamic_verification.json`, `../output/artifact_manifest.json` and `../output/environment.json`. Independent checks reconstruct P&L without the backtest's accounting class.

The subsequent English translation is recorded separately in `translation-provenance.json`: it changes descriptions/identifiers, not simulated observations or numerical calculations, and does not claim a fresh simulation run.

Numerical checks do not resolve the main scientific limitation: 2026 holdings are frozen retrospectively. Historical company/sector compliance is not certified against then-current holdings.
