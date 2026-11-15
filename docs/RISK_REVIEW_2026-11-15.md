# Risk Lab review — 2026-11-15 UTC

This review found no defect in the running `risk-1.0.0` forecast specification or the continuing `research-2.0.0` direction record. It found one presentation defect: the Risk Lab's on-site Hub receipt summary read an obsolete Hub field, so it could report that a current receipt was not found. The proposed correction reads the Hub's published top-level forecast receipts and checks their bytes against each current Z export. It does not change research results.

## Prospective record and operations

- The public Risk Lab is current through the successful November 14 cycle. It contains nine issued risk dates, November 3 through November 13, and four resolved dates. The latest issue uses information through the November 13 close and targets the November 16 open through the November 20 close.
- Every issued snapshot passed its content hash and timestamp checks. Each holding window contains the registered five NYSE sessions. All ten assets have EWMA, daily-HAR, GARCH(1,1), event-frequency and volatility-only forecasts, with no model abstentions to date.
- The November fitted artifact remains frozen at its November 3 fit. Its file hash, the registered specification hash, the algorithm hash and every archived daily input hash matched the corresponding snapshot metadata.
- Each resolution references the exact frozen forecast hash, contains all ten assets and uses one content-addressed adjusted-price vintage. No premature or changed resolution was found.
- The early overnight attempts on November 12–14 failed closed when the provider returned invalid SPY OHLC data. Later retries succeeded before the relevant entry opens. The latest risk workflow ran 47 tests with one skipped optional test; the final export and publication steps succeeded.
- FRED access succeeded without exposing its credential: the latest archived context contains all five registered FRED series. The current macro context is marked incomplete and remains context only; it is not an input to any `risk-1.0.0` benchmark.

## Evaluation integrity

- Historical risk research retains 1,510 dates and 15,100 rows with zero failed fit components. All primary comparisons have matched candidate/baseline coverage. Date-block intervals preserve the exchange-session calendar rather than compressing gaps.
- All six registered synthetic diagnostics are present: three seeds in the constant-variance world and the same three in the persistent two-state world. These remain software diagnostics, not evidence of market skill.
- Every variance model reports its primary mean QLIKE plus forecast/date medians, the share from the worst `ceil(1% of dates)`, and the mean excluding 2020. The registered macro reports and failed attempts remain unchanged. Their extreme all-date QLIKE is correctly described as stress-period severe underprediction; excluding 2020 is diagnostic only.
- Four resolved live dates are far too few for inference, and their five-session windows overlap. Current live point estimates therefore do not justify model selection or a new hypothesis.

## Exports, independent receipt and public site

Both latest task exports contain ten assets, preserve raw forecast type and target, and use the contract's four entry-to-exit session intervals for the same five observed holding sessions. Each passed the pinned unmodified Hub `validate()` and the complete Draft 2020-12 JSON Schema with date/date-time format checks.

The Hub's current record independently shows both November 13 task files as received live at 02:59:45 ET on November 14, before the November 16 entry open. Their Hub SHA-256 values exactly match Z's published export bytes. This receipt evidence, not Z's own issue timestamp, establishes timely Hub delivery.

The proposed branch's rebuilt site produced 147 readable documents and records. An audit of all 150 generated HTML files found no repository links and no broken local links. Fifteen browser-DOM tests cover all public sections, freshness behavior, internal document links and the prohibition on repository links.

## Decision and next step

Keep the running specifications unchanged. Accumulate genuinely future resolutions, monitor missingness and provider failures, and review matched live losses only after substantially more non-independent dates have matured. No new risk hypothesis is registered in this review: the observed 2019–2026 history is not a fresh holdout, and four live dates offer no defensible basis for another model search.
