# MSDS 451 â€” Checkpoint B

Choose ETFs and weights for the growth block, allowing short positions and controlling the companies and sectors held inside the funds.

**[Read the English report](report/checkpoint-b.html)**

## Reproduce

All required inputs are saved here. Normal commands neither consult sibling folders nor refresh internet sources.

```powershell
cd C:/studing/msds-451-module-6
uv run --no-project --with-requirements requirements.txt python run.py --check
python -m pipeline.verify_translation
uv run --no-project --with-requirements requirements.txt python run.py --report-only
uv run --no-project --with-requirements requirements.txt python run.py
```

`--check` verifies saved data, accounting and results. `--report-only` rebuilds figures and HTML. The default command reruns seven historical cases, the temporal control, 10,000 paired 25-year scenarios and 50 reoptimized five-year paths (6,000 optimizations). A full run takes several minutes. `uv` provides isolated dependencies without changing the shared scientific environment.

## Structure

| Path | Contents |
|---|---|
| `pipeline/` | Input readers, filters, optimization, signed accounting, validation and report generation |
| `data/` | Frozen prices, FX, liquidity, cash yields and metadata |
| `data/holdings/` | Normalized holdings, coverage, manifests and original issuer/regulator files |
| `output/` | Weights, trades, wealth, metrics, simulations and verification records |
| `figures/` | English SVG and PNG charts |
| `report/` | Self-contained English HTML |
| `resources/` | Assignment, bibliography, design decisions, audits and provenance |

## What the evidence supports

- Prices end October 23, 2026; complete months end September 2026.
- The July 2019â€“September 2026 experiment includes COVID and 2022, not the 2001 or 2008 crises.
- September/October 2026 holdings are frozen retrospectively. They do not certify historical company, sector, country or currency limits.
- Share classes are grouped by issuer; wider corporate-control groups are not fully mapped.
- Underlying quotation currency is a proxy, not complete economic FX exposure.
- Borrowing, financing and margin are explicit assumptions. Historical availability and real-account terms are unverified.

## Provenance

The original study remains outside this repository in `C:/studing/msds-451-module-6-temp`. Minimal helpers replaced its earlier framework, and the complete study was rerun in this folder. Historical result fingerprints were not rewritten to imply a run that did not occur.

[Packaging provenance](resources/packaging-provenance.json) records copied inputs. [Translation provenance](resources/translation-provenance.json) records the later English-only changes and validates unchanged numerical logic and results. [Assignment instructions](resources/assignment.md) retain the Canvas source and five sections worth ten points each. [Folder relocation](resources/folder-relocation.json) records earlier locations; absolute paths in historical records describe locations at the time, not current dependencies.

The approved Portuguese report and old review screenshots are preserved outside the repository in the temporary study archive. Upstream CVM field names, legal names and Portuguese source vocabulary remain unchanged because they are original financial records, not authored documentation.

Visual verification on Windows with Edge:

```powershell
uv run --no-project --with playwright python pipeline/qa_html.py --root C:/studing/msds-451-module-6
```

Repository: [leandroyloli/msds-451-module-6](https://github.com/leandroyloli/msds-451-module-6). The study was introduced through PR #1; this translation is a separate review change. No site deployment or Canvas submission is part of the repository workflow.
