# Registered macro results — 2026-11-04 UTC

FRED access is verified. The corrected program completed with **31 tests passed**, all five
series archived, and all six macro procedures scored on **1,510 dates / 13,590 sector rows**
from 2019–2024. These are development results, not fresh confirmation or live performance.

- [Corrected run](https://github.com/PrototypeVersions/UnpricedZ/actions/runs/41759065718)
- [Immutable corrected report](../archive/program/program-0.1.0/41759065718-1/report.json)
- [Prior completed computation](../archive/program/program-0.1.0/41757845804-1/report.json)
- [Evidence recovery run](https://github.com/PrototypeVersions/UnpricedZ/actions/runs/41758878602)

## Results as registered

Lower loss is better. Gain is market-only loss minus macro loss, so positive favors macro.
Intervals use the predeclared date-block procedure and are descriptive, not adjusted for
multiple comparisons. Every row uses identical forecasts' assets, endpoints and outcomes.

| Task | Refit | Macro loss | Market-only loss | Macro gain | Descriptive 95% interval |
| --- | --- | ---: | ---: | ---: | --- |
| Relative-return event · Brier | Monthly | 0.25226 | 0.25096 | -0.00130 | -0.00273 to +0.00009 |
| Relative-return event · Brier | Quarterly | 0.25363 | 0.25066 | -0.00297 | -0.00721 to -0.00013 |
| Variance · QLIKE | Monthly | 5.18726 | 0.49280 | -4.69445 | -13.27862 to -0.21025 |
| Variance · QLIKE | Quarterly | 25.12044 | 0.50112 | -24.61932 | -67.15671 to -0.32394 |
| Drawdown event · Brier | Monthly | 0.15388 | 0.14398 | -0.00990 | -0.02008 to -0.00249 |
| Drawdown event · Brier | Quarterly | 0.15476 | 0.14792 | -0.00684 | -0.01407 to -0.00100 |

The macro addition lost to the corresponding market-only model in every comparison's point
estimate. Both macro variance procedures lost badly to the endpoint-matched EWMA baseline
(QLIKE **0.41370**). Their extreme losses remain in the report. The drawdown models' modest
advantage over unconditional event frequency did not establish an advantage over market-only
features. No model is promoted and no thresholds, features or hyperparameters were retuned.
Market-only and frozen Chronos results are unchanged from the earlier report.

## Corrections and coverage

The connection adapter now obtains the server's date, requests bounded vintage-date windows,
and discovers each series' first archival date. T10Y2Y and BAA10Y first appear in ALFRED on
2014-01-27; their earlier historical values are not backfilled as information known then.
All input vintages and selection audits are preserved, including blocked earlier attempts.

The owner requested a fix after run 41757845804 finished. A newly missing holiday observation
now falls back to the most recent still-valid observation, subject to its own age limit.
Explicitly withdrawn values stay withdrawn and future releases cannot enter earlier decisions.
The correction increases complete input dates across the full input span from 3,072 to 3,073;
outer evaluation coverage was already complete. Changed training inputs slightly alter fitted
forecasts. The corrected result is not an independent replication or a new holdout.

The original computation finished, but its evidence commit conflicted in the mutable latest
report. Its exact artifact was recovered with SHA-256
`6457498a14e77afe7bd2aa5b5f1afe29e12806db4dc121b8291c6a0f42bc5422`.
The recovery preserves the old report verbatim. Subsequent serialized runs check out current
main so that preceding evidence commits are included.

## Research decision

UnpricedZ becomes the Risk Lab. Preserve the official research-2.0.0 direction record and stop
adding sector-direction complexity. Register a separate risk benchmark version for SPY and
nine sectors, with EWMA, daily-data HAR and GARCH(1,1), plus a volatility-only drawdown baseline.
Future macro hypotheses must demonstrate incremental value against these stronger controls.
Reviewer agreement is not forecasting evidence.
