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

## 2026-11-04 — Isolated upgrade program and cross-lab plan

- Registered program-0.1.0 before its first computation: six macro inputs from ALFRED vintages, bounded inner chronological selection, paired monthly/quarterly refits, and a frozen pinned Chronos-2 comparison.
- Kept return, variance and drawdown tasks separate. Historical pretrained results explicitly carry an unresolved pretraining-overlap limitation.
- Added nine regression tests for temporal separation, future-label mutation, macro revisions/availability, missing inputs, drawdown paths, pretrained target alignment, and exact outcome pairing.
- Added a CPU-bounded Actions workflow that preserves all attempted reports, predictions, selection audits and dependency versions. Missing FRED credentials explicitly block macro comparisons.
- Added the two-lab strategy, a read-only Claude review brief, and links in the repository and public lab notes. UnpricedX was inspected read-only; original Unpriced was not modified.
- Updated the existing weekly research-review task to prioritize the approved four-part program and reviewed shadow-launch preparation, without automatic promotion.
- Confirmed the official algorithm SHA-256 remains `15e0549b70629e45c79ee2049a76a46b7b0f9aecf47eacecc279a43677a72f29`. No official model policy or frozen record was rewritten.

## 2026-11-04 UTC — FRED connection diagnostics

- The first credential-enabled request was rejected by FRED. Preserve that blocked attempt.
- Retain the HTTP status and provider's JSON error explanation with credentials redacted;
  omit arbitrary response bodies and credential-bearing request URLs. Added a regression test
  for reflected secrets and unexpected HTML errors. No research specification was changed.
- The provider's HTTP 400 identified the cause: the UTC runner requested November 4 while
  FRED's server still considered today November 3. The adapter now lets FRED supply its
  default real-time end on the first request, then pins that returned date across all pages
  and series. A regression test covers the overnight UTC boundary and pagination.
- The next request exposed FRED's 2,000-vintage limit for JSON. Downloads now use
  contiguous windows of at most 1,000 calendar dates and paginate within each window.
  A one-row current-date probe supplies only the server boundary; its revised value
  is discarded. Tests cover complete window coverage, pagination, absent early coverage,
  and rejection of prematurely empty pages. Earlier blocked attempts remain archived.
- FRED returns HTTP 400 for a real-time window wholly before a series first appeared in
  ALFRED. The adapter now discovers each first vintage with the vintage-date endpoint,
  starts its bounded requests there, and archives that coverage boundary. A regression
  test verifies that late archival coverage never fills earlier dates.

## 2026-11-04 UTC — Holiday handling and evidence recovery

- Let run 41757845804 finish before making the owner's requested correction. All 12
  tabular procedures and the frozen Chronos screen completed; FRED was available.
  Its evidence commit conflicted with the prior run's mutable latest-report pointer.
  The full artifact was retained and recovered without rewriting the immutable report.
- Program checkout now starts from current main after acquiring its serialized job slot,
  retaining the preceding run's evidence before computing the next report.
- `asof_series` uses the latest non-missing as-of observation. A bond-market holiday's
  missing row no longer masks a recent valid value. Age limits still use that value's
  observation date; later releases cannot fill earlier decisions; withdrawn observations
  do not regain their earlier value. Added regression tests for these cases.
- This is a data-handling correction to program-0.1.0. Preserve the prior results and
  report the rerun as a corrected development comparison, not independent confirmation.
