# Historical 2019–2024 risk-variance forecasts for the Stock Lab

**Export destination:** [risk-v1-variance-oos-2019-2024.csv](../site/data/export/risk-v1-variance-oos-2019-2024.csv)

**Immutable source:** [original risk-1.0.0 historical report](../risk_archive/risk-1.0.0/research/41762675368-1/report.json) and the compressed predictions archive it identifies, from GitHub Actions run 41762675368.

This CSV is **retrospective purged walk-forward research**, not a record of predictions actually published in 2019–2024. The historical origin dates are reconstructed information cutoffs for an evaluation computed in November 2026. There are no contemporaneous historical issue timestamps or independent Hub receipts. It would be incorrect to present this data as a 2019–2024 live trading record or a fresh sealed holdout.

The export contains the original 15,100 forecast rows (1,510 decision dates for SPY and nine sector ETFs), without rerunning models or changing specifications. The columns are:

| Column | Meaning |
| --- | --- |
| date | Historical forecast origin date, **not** its original publication timestamp |
| ticker | SPY or one of nine sector ETFs |
| fitAsOf | Monthly fitting cutoff used for this prediction |
| entryDate | Next trading session; entry at adjusted open |
| labelEnd | Fifth holding session; target ends at adjusted close |
| ewma, har_daily, garch11 | Original historical forecasts of average daily-sampled variance over the five-session window, in **squared fractional log returns per session** |

Missing model values remain missing. The exporter copies the numeric strings from the original prediction archive and **omits realized outcomes and other future-dependent labels** so the file is suitable as forecast input to separately registered research.

The generator (site_tools/export_risk_history.py) checks the SHA-256 digest of the original uncompressed predictions file, the input-vintage hash against the registered configuration, the completed report, date coverage, unique ticker/date keys and row counts. It rejects attempts to silently overwrite a different CSV.

Reproduce locally with:

    python -m site_tools.export_risk_history

Verify an existing copy without modifying it with:

    python -m site_tools.export_risk_history --check

The Risk Lab workflow is set to generate and commit this derived file. **If it is not present at the link above, generation/publication has not yet completed.**

### Important restrictions on use

The original prices use the provider's adjusted OHLC data, which may contain subsequent historical adjustments. The retrospective forecast predictions are model-out-of-sample within that research design, **not** prospectively issued or newly independent evidence. The 2019–2024 period has already been inspected.

UnpricedX ranks **individual stocks** over a next-open-to-later-open window. This file predicts **ETF variance** over a next-open-to-fifth-session-close window. Before using it in an X-side portfolio A/B/C study, predeclare stock-to-sector mapping, calendar alignment, cutoffs, policy sizing/cash rules, abstention behavior, costs, and handling of overnight/cross-asset risk. The proposed comparison must include both the unchanged original X portfolio and a simple volatility-sizing baseline, and seek genuinely prospective evidence before claiming success. UnpricedZ exports only forecast data, not combined trades.
