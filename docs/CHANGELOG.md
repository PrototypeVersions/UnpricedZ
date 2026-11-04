# Change log

## Initial research-2.0.0

- Created an independent UNPRICED Research repository; original V1 untouched.
- Defined next-open to fifth-close targets and a separate daily-variance forecast.
- Added chronological quarterly evaluation with purged calibration, explicit baselines, raw/calibrated comparisons and fixed model complexity.
- Predeclared development and confirmation periods before inspecting results.
- Added production-path null/weak/moderate synthetic controls and seed-level results.
- Added content-addressed input archives, quarterly models, immutable live snapshots/resolutions, and actual timestamps.
- Added fixed-exit, cost-aware reference-return portfolio experiments.
- Built the responsive research interface and GitHub Pages/Actions pipelines.
- Added integrity tests for leakage, session indexing, missingness, publication windows and record immutability.

Subsequent corrections and tested specifications must be appended here.

## 2026-11-04 — Publication setup

- Enabled GitHub Pages with Actions after the initial calculation completed successfully but deployment lacked repository setup.
- Serialized site and data publication through one concurrency group. Both workflows check out current main so a retry retains records already committed by an earlier attempt.
- Attached daily deployment to the github-pages environment. Research models, thresholds, first results and live snapshots are unchanged.
