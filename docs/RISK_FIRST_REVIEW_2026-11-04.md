# Risk Lab first evaluation — 2026-11-04 UTC

The independent risk-1.0.0 experiment is published. This date is November 3 in the owner's
America/Chicago timezone. The [protocol](RISK_PROTOCOL.md) was registered at commit
`7198a83bbf0f8fb47a6bf66f27abdb743a541436`, before the implementation and evaluation at
`3c76f435c1dda2b8f6a80cb7bdc92a11bf1cc59a`.

[Actual workflow](https://github.com/PrototypeVersions/UnpricedZ/actions/runs/41762675368):
**40 tests passed**, 12 warnings; all six synthetic runs and the registered historical study
completed. The historical fit audit reports **zero failed fit components**. Both genuine live
exports passed the exact pinned Hub `hub/core.py validate()` with jsonschema installed.
Frontend syntax passed, Pages deployment succeeded, and the published Risk Lab page,
separate live scorecard and provenance dialog were inspected in the browser.

## Historical development evidence

Origins are 2019–2024: 1,510 dates, 15,100 rows across SPY and the nine sectors. This history
was already observed. It is neither fresh confirmation nor a live track record. Lower loss
is better; no baseline is automatically promoted.

| Group | Benchmark | Metric | Mean loss | Scored rows |
| --- | --- | --- | ---: | ---: |
| SPY | ewma | QLIKE | 0.48940 | 1,510 |
| SPY | har_daily | QLIKE | 0.48206 | 1,510 |
| SPY | garch11 | QLIKE | 0.43085 | 1,510 |
| SPY | base_rate | Brier | 0.12443 | 1,510 |
| SPY | volatility_only | Brier | 0.12782 | 1,510 |
| sectors | ewma | QLIKE | 0.41370 | 13,590 |
| sectors | har_daily | QLIKE | 0.44699 | 13,590 |
| sectors | garch11 | QLIKE | 0.38268 | 13,590 |
| sectors | base_rate | Brier | 0.15461 | 13,590 |
| sectors | volatility_only | Brier | 0.15654 | 13,590 |

Positive paired gain favors the candidate. Intervals are descriptive 95% date-block
intervals, unadjusted for six comparisons or repeated inspection.

| Group | Paired comparison | Mean gain | Interval |
| --- | --- | ---: | --- |
| SPY | har_daily vs ewma | +0.00734 | -0.02296 to +0.04025 |
| SPY | garch11 vs ewma | +0.05855 | +0.00961 to +0.11265 |
| SPY | volatility_only vs base_rate | -0.00339 | -0.01615 to +0.01048 |
| sectors | har_daily vs ewma | -0.03329 | -0.08947 to +0.00315 |
| sectors | garch11 vs ewma | +0.03102 | +0.00057 to +0.06744 |
| sectors | volatility_only vs base_rate | -0.00192 | -0.01110 to +0.00785 |

GARCH had lower historical variance loss than EWMA in both groups. HAR did not establish
consistent improvement. The volatility-only drawdown model had slightly worse Brier loss
than event frequency in both groups. All of these results remain in the record. They do
not establish a prospective edge, a tradable policy, or a reason to add another model now.

Every variance benchmark includes median QLIKE, worst-1%-of-dates concentration and the
mean excluding 2020 in the [immutable report](../risk_archive/risk-1.0.0/research/41762675368-1/report.json).
The registered all-date mean remains primary. Complete predictions, fit audits and the
package environment are archived alongside it.

## Synthetic diagnostics

All six prespecified runs completed with 252 evaluated dates each. GARCH and HAR beat EWMA
in point estimates in the persistent-state worlds; the uncertainty is wide. In the constant
world, smoothing toward constant variance can also beat a reactive EWMA: this is not a
false directional signal or proof of market information. The volatility-only drawdown
model lost to frequency in all three constant worlds and improved in point estimate in
all three persistent worlds. Keep every seed and the latent-state oracle comparison in
[the control report](../risk_archive/risk-1.0.0/controls/41762675368-1/report.json).

## First prospective publication

- Information cutoff: `2026-11-03T21:00:00+00:00`.
- Actual issue time: `2026-11-04T02:46:06.847826+00:00` (November 3, 9:46 p.m. EST / 8:46 p.m. CST).
- Entry: `2026-11-04T14:30:00+00:00`; exit: `2026-11-10T21:00:00+00:00`.
- All ten assets have all three variance and both drawdown forecasts; zero abstentions.
- One issued date and zero resolved dates at launch. The first outcome matures November 10.
- FRED dated context is available, but is not a benchmark model input.

The [snapshot](../risk_records/risk-1.0.0/forecasts/2026-11-03.json) is separate from the original
ledger. Daily state updates and monthly frozen parameter fits follow the registered protocol.
Daily exports use the raw variance and drawdown probability, unchanged entry/exit prices,
actual information/issue times and content/model/code hashes. Hub's four session-index
intervals describe this same five-observation window. Hub receipt timeliness is independent
and requires its own successful collection before the entry open.

## Preservation and next step

The corrected program-0.1.0 macro report remains exactly unchanged, Git blob
`7cbfbe3b6ccd28af1fc83e793059c8e68e4eb0fd`. Its [additive decomposition](MACRO_VARIANCE_DECOMPOSITION.md)
keeps the negative registered results and explains stress-period concentration.

The original research-2.0.0 algorithm SHA-256 remains
`15e0549b70629e45c79ee2049a76a46b7b0f9aecf47eacecc279a43677a72f29`.
Its first forecast remains Git blob `497a8e6afb8f82a234e9d96582a6e7fb1f48ade6`.
The original direction engine, configuration, model artifacts and schedule were not changed.
Neither Unpriced nor UnpricedX was modified.

The immediate next step is to accumulate genuinely future risk forecasts and have the Hub
receive them independently. The weekly review now prioritizes risk integrity, coverage,
calibration and contract compatibility. A macro residual hypothesis or new calibration
method needs a new registration; neither has been retrofitted into this result.
