# Risk Lab review — 2026-11-22 UTC

This review found no reproducible defect in the running `risk-1.0.0` forecast
specification or the continuing `research-2.0.0` direction record. The one
material presentation defect found on November 15 remains reproducible on the
public site: its on-site Hub table says the latest receipts were not found even
though the Hub recorded both files before entry. Draft PR 7 contains the tested
compatibility correction. This review updates the evidence; it does not change
models, targets, fitted artifacts, schedules, ledgers, exports or trading rules.

## Prospective record and operations

- The live risk record contains every expected NYSE decision session from
  November 3 through November 20: 14 forecast dates, with nine matured and
  resolved dates. All ten assets have all five registered model forecasts and
  there have been no abstentions.
- The latest snapshot used information through the November 20 close, was
  frozen at `2026-11-21T02:37:43.336610+00:00`, and targets the November 23 open
  through the November 30 close. Its publication and the Hub's independent
  receipt both occurred before the entry open.
- Every snapshot's canonical payload hash, archived uncompressed input hash and
  model artifact hash verified. Every resolution points to the exact frozen
  forecast file, contains all ten assets and uses one content-addressed
  adjusted-price vintage.
- The November model remains the November 3 monthly fit. The model, algorithm
  and registry hashes are unchanged across all 14 issues. No model was refit or
  promoted in this review.
- The latest risk workflow completed successfully with 47 tests passed and one
  optional test skipped, rebuilt the unchanged historical export, ran the daily
  record, validated both Hub exports and preserved the resulting evidence. The
  latest Pages workflow then built and verified the public deployment.
- One early direction workflow on November 20 failed closed on invalid provider
  OHLC values for EEM. A later scheduled retry succeeded. This did not justify a
  code, schedule, data-quality or direction-model change.
- FRED access is evidenced by a successful archived response containing all five
  registered series, without exposing the credential. The latest dated context
  is marked incomplete because one derived context value is unavailable. Macro
  data remain context only and do not enter the `risk-1.0.0` forecasts.

## Evaluation integrity

- Historical risk research remains the registered 1,510 dates and 15,100 rows,
  with zero failed fit components. Every primary comparison uses the matched
  candidate/baseline intersection. The reported uncertainty reindexes losses to
  the NYSE calendar before sampling date blocks, so missing dates are retained as
  gaps rather than compressed into artificial adjacency.
- All six registered synthetic diagnostics remain present: three fixed seeds in
  a constant-variance world and the same three in a persistent two-state world.
  They test recoverability and implementation behavior, not market skill.
- Every risk variance model reports mean and median QLIKE, worst-`ceil(1%)` date
  concentration and the mean excluding 2020. The registered macro report and its
  prior failed attempts remain unchanged; the corrected report retains Git blob
  `7cbfbe3b6ccd28af1fc83e793059c8e68e4eb0fd`. Its extreme variance QLIKE remains
  correctly described as severe stress-period underprediction. Excluding 2020 is
  an additive diagnostic, not a replacement result.
- The nine live outcomes have overlapping five-session windows. Point estimates
  currently favor HAR and GARCH over EWMA for variance and favor event frequency
  over the volatility-only drawdown model, but this is far too little dependent
  evidence for model selection, promotion or a new hypothesis.

## Exports, independent receipt and public site

The latest variance and drawdown files preserve their raw forecast types,
targets, information cutoff, issue time, open entry, close exit and hashes. The
contract's four session-index intervals correctly represent the five observed
holding sessions. Both files passed the pinned, unmodified Hub `validate()` and
the full Draft 2020-12 JSON Schema with date and date-time format checking.

The Hub independently recorded both November 20 exports as `live` at
`2026-11-21T03:45:17-05:00`, 3,224 minutes before the November 23 entry open.
Their Hub SHA-256 values exactly match Z's current export bytes. This receipt,
not the lab's issue timestamp, establishes timely delivery.

The current public site exactly matches the successful November 21 deployment
for its HTML, scripts, risk data, status and both exports. Its primary and on-site
reference pages contain no repository links. A rebuilt local bundle contains 198
HTML pages, 2,648 links, zero repository links and zero broken local links. The
remaining public error is the Hub receipt display described above; the underlying
forecast and Hub records are correct.

## Decision and next step

Keep both running specifications unchanged. Merge the isolated presentation fix
only after review, then let the normal site publication rebuild its on-site Hub
receipt table. Continue accumulating genuinely future resolutions and monitoring
delivery, abstentions, missingness and matched coverage. No new risk hypothesis is
registered: observed 2019–2026 history is not a fresh holdout, and nine overlapping
live dates do not support another model search.
