# UNPRICED: two independent labs and a common evaluator

Recommendation as of 2026-11-04: retain UnpricedZ and UnpricedX, implement the four bounded
experiments in Z, then add a read-only comparison hub. Do not multiply similar labs or merge
their model code merely because either reports an attractive backtest. The brand can remain
UNPRICED, with Sector Lab, Stock Lab and Comparison Hub subtitles.

## What was actually inspected

UnpricedZ's implemented protocol, initial results and engine were reviewed. UnpricedX's README,
CLAUDE.md, methodology, data/learning documents, config, target construction, and sequential
comparison code were inspected read-only around commit
[`4b287024`](https://github.com/PrototypeVersions/UnpricedX/tree/4b28702467f2e6a35ac0c5ecb57dacd0e6c197f7).
This is an architecture comparison, not a certification of X's deployment or every implementation.
No X files, holdout experiments or automations were changed or run.

| Dimension | UnpricedZ | UnpricedX |
| --- | --- | --- |
| Main universe | Nine legacy sector ETFs | Up to 1,000 individual US stocks, selected by daily rules from available histories |
| Main output | Probability of beating SPY; variance | Within-date stock return ranks |
| Five-session target | Next open to fifth following session close | Next open to the open five intervals later |
| Initial inputs | Price/volume/context; new macro experiment | Price/volume, industries, optional SEC fundamentals/events and filing reader |
| Main score | Brier; separate QLIKE risk score | Rank IC; portfolio diagnostics |
| Model updates | Official quarterly; new monthly/quarterly comparison | Documented weekly live refits and weekly specification search |

These are complementary tasks. Their raw probabilities/ranks, IC/Brier numbers, and paper
returns cannot form a fair single leaderboard. An X rank is not a Z probability. Similar
"five-day" labels do not imply identical outcomes. X documents a present-day survivor bias
in its free historical universe; Z's ETF study does not answer the individual-stock question.

Two X mechanisms need an independent methodological review before borrowing them: repeated
weekly looks at the same holdout can leak selection information despite a weekly look cap;
the implemented decision band is an **asymptotic** confidence sequence, not a universal exact
finite-sample guarantee for dependent market observations. Non-overlapping windows remove
mechanical return overlap but do not establish independence or stationarity. Simulated error
rates under selected generators do not resolve those assumptions. These are review questions,
not a claim that the entire stock lab is invalid.

## Ordered implementation

1. **Preserve reference versions.** Leave original Unpriced untouched. Keep Z's official live
   process running. Pin the versions being compared and record all new trials separately.
2. **Finish the four Z development experiments.** Run the registered program, configure the
   vintage-data credential if absent, retain all outcomes, and investigate data/test failures
   before interpreting performance. Do not pick a winner from 2025 and call it confirmation.
3. **Exchange read-only reviews.** Ask Claude to review Z using CROSS_REVIEW_BRIEF.md. Review
   concrete failure cases, definitions and tests. Agent agreement is not evidence of skill.
4. **Agree on a comparison contract.** Exact task, universe, information cutoff, entry/exit,
   outcome vintage, score, missingness and costs must match. Keep separate scoreboards until
   there is a genuinely shared task. A stock rank cannot be converted ad hoc to a calibrated
   sector probability. A bridge model requires its own registered experiment in the owning lab.
5. **Create UnpricedHub as an independent observer.** Read immutable exports from the labs;
   store receipt time and content hash; resolve a common outcome feed; recompute scores.
   Start with operational health, coverage, separate task panels and uncertainty. A received
   artifact after entry is retrospective, even if its embedded issue time is earlier.
6. **Launch only the shortlisted shadow procedures.** Version them, freeze forecasts before
   entry, resolve matured outcomes, and compare on identical date blocks. Daily data collection
   and scoring continue; retraining cadence follows the registered procedure. No promise of
   proving a small edge in 60 or 90 days. Set an inference plan using power and dependence.
7. **Test one fixed ensemble when compatible forecasts exist.** For the same event and same
   information cutoff, start with equal-weight probabilities. For distributions use an actual
   mixture; averaging quantiles is not generally the mixture's quantile function. Score the
   ensemble as a new challenger. Report error correlation and coverage, not just its profit.
8. **Consider learned weights only after the fixed ensemble.** Fit a small constrained,
   regularized combiner on earlier out-of-fold or frozen prospective predictions with matured
   outcomes. Purge overlaps; keep entire dates together; evaluate the *whole* stacking procedure
   in later windows. Never train a combiner on component models' in-sample fits. Compare to equal
   weights and the chosen standalone baseline. Keep learned weights in a separate version.

The next concrete dependency is a common contract and an independently reviewed forecast
export, not a third forecasting engine. The hub should initially have no authority to rewrite
lab records, tune their models, promote a champion, or trade. Each lab owns its implementation;
the hub owns comparison and receipt evidence. Shared evaluation tests should also be checked
against hand-calculated fixtures so a common scorer does not spread a common bug.

## Minimum comparison export

An export must include:

- Schema version, lab/experiment/model IDs, code and model artifact hashes, input-vintage hashes.
- Exact task ID and mathematical target definition, asset/universe membership snapshot.
- Information cutoff, actual issue timestamp, intended entry and exit timestamps, timezone/calendar.
- Forecast type and units: event probability, rank, distribution quantiles, or variance; no silent conversions.
- Missing/abstained assets with reasons and the full expected universe denominator.
- Pretraining/checkpoint provenance and any unresolved historical contamination limitation.
- Stable source URL and content digest. Hub adds an independent `receivedAt` and preserves the original bytes.

The hub validates `informationCutoff <= issuedAt < entryAt <= exitAt`, receipt before entry,
unique asset/task keys, numerical ranges and exact target compatibility. It records errors;
it does not repair late forecasts into timely ones. Historical imported files remain historical.

Comparable models must share an information budget. A morning filing-aware forecast can be
useful, but it is not a controlled test of model architecture against a close-only forecast.
Use separate tracks or a registered common-cutoff adapter. Portfolio rankings additionally
require the same capital, exposure, holding convention and costs; forecast skill stays separate.

## When another lab is justified

A third forecasting lab is justified by a distinct question and data source—e.g. an options
risk lab or a documented event-response lab—not merely another prompt, algorithm or seed.
Add it after the hub can evaluate it. Several labs exposed to the same market are not several
independent samples of market history. More searches increase false discoveries as well as ideas.
