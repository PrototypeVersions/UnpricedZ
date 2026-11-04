# First evaluation — 2026-11-04 UTC

The lab is operational. The initial directional models have **not demonstrated an advantage over the historical-base-rate forecast**. That is a research finding, not a reason to retune thresholds until the display looks successful.

This note records the first evaluation, generated at 00:27:29 UTC. Its [immutable report](../archive/research/2026-11-03-221e426be328.json) preserves the original data vintage and source revision. The public dashboard can show later runs; each archived report retains its own provenance.

## What the historical evaluation says

The initial run evaluated 2,720 forecast dates from January 2016 through October 27, 2026, with nine sector observations per date. They are correlated observations, not 24,480 independent experiments.

For the prespecified 2025 confirmation period (250 dates):

| Forecast | Brier loss (lower is better) | Improvement over base rate | Descriptive 95% date-block interval |
| --- | ---: | ---: | --- |
| Historical base rate | 0.249648 | 0 | Reference |
| Constant 50% | 0.250000 | -0.000352 | -0.001345 to +0.000647 |
| Momentum | 0.250473 | -0.000825 | -0.002903 to +0.000943 |
| Raw logistic | 0.252531 | -0.002882 | -0.006392 to +0.000031 |
| Calibrated logistic | 0.250449 | -0.000801 | -0.003020 to +0.001010 |
| Boosted challenger | 0.249947 | -0.000299 | -0.001772 to +0.001292 |

None of these candidates has a positive interval excluding zero. In the 2026 retrospective sample, calibrated logistic and the boosted challenger are worse than the base-rate forecast, with intervals below zero. Calibration is not a guarantee of improved performance, and the lab exposes the raw comparison for that reason.

The risk challenger has a 2025 QLIKE improvement of +0.0212 over EWMA, with interval -0.0311 to +0.0743. This also does not establish incremental skill; the development-period result favors EWMA. The residual bands' observed coverage can deteriorate: the nominal 80% band covered about 71% in the 2026 sample.

## What the synthetic controls say

The production fitting and evaluation path ran 12 fixed seeds for each condition. Detection compares calibrated logistic with the constant-50% reference, using a positive date-block interval.

| Generator | Detections | Seed-level rate interval |
| --- | ---: | --- |
| Directional null | 0 / 12 | 0%–24% |
| Weak planted signal | 1 / 12 | 1%–35% |
| Moderate planted signal | 11 / 12 | 65%–99% |

These controls show recovery of stronger planted structure and low power for weak structure in this batch. Twelve seeds cannot certify a 5% false-positive rate, and synthetic power is not market skill. The [full controls](../site/data/controls.json) retain every seed and all model results.

## Prospective record and economics

The first [live snapshot](../records/forecasts/2026-11-03.json) was published at **2026-11-04 00:27:38 UTC**, before the November 4 opening. Its target ends at the November 10 close. No outcome was mature at launch.

The initial historical paper policy selected **zero positions** and stayed at $1,000; its matched-window SPY comparator ended around $4,904.76. The first prospective plan also holds cash. These outcomes remain visible. Lowering the trading threshold after seeing them would be a new specification, not a correction.

## Verified launch behavior

- All 15 integrity tests passed in GitHub Actions, including future-price perturbation, calendar/holiday horizons, missing bars, calibration purging, late publication, immutable writes and no reranking around unavailable future returns.
- Historical research, synthetic controls, first prospective publication, strict JSON validation and frontend syntax checks completed successfully.
- Initial Pages setup failure was corrected; the subsequent [research and deployment run](https://github.com/PrototypeVersions/UnpricedZ/actions/runs/41747272969) passed.
- A separate [daily retry](https://github.com/PrototypeVersions/UnpricedZ/actions/runs/41748704510) passed tests, publication and deployment. The November 3 snapshot retained the identical Git blob hash `497a8e6afb8f82a234e9d96582a6e7fb1f48ade6` and its original issue time.
- Browser checks covered all six views, model selection, sector search, keyboard-opened forecast details, live/historical period separation, control selection, portfolio switching and provenance details. No JavaScript console errors were captured.
- Narrow-layout testing at a measured 390 CSS-pixel viewport showed no page overflow; wide forecast tables scroll within their container. Desktop layout was also inspected.

## Next research decision

Keep this specification as a documented baseline. Diagnose the stability of calibration and risk forecasts before adding complexity. Any new signal or target needs a preregistered challenger and fresh evaluation; the now-observed 2025 period is no longer an untouched test for redesigns. Timestamped event or macro data are future research directions, not features that this launch claims to implement.
