# Risk Lab — risk-1.0.0

Registered on 2026-11-04 UTC before this version's evaluation or live publication.
The executable declaration is [risk_lab/registry.json](../risk_lab/registry.json).

## Mandate and boundaries

Claude leads the overall UNPRICED project. UnpricedX is the Stock Lab, UnpricedZ is the
Risk Lab, and UnpricedHub is the read-only scorekeeper. Work here changes only UnpricedZ.
The official research-2.0.0 sector-direction forecast ledger, model artifacts, source and
daily operation remain unchanged. It continues collecting outcomes without new directional
complexity. Reviewer agreement is not evidence of forecasting skill.

The registered macro program's [negative results](PROGRAM_MACRO_REVIEW_2026-11-04.md) remain
visible. This new version establishes stronger risk benchmarks. Macro observations are
archived as dated context, but do not enter these initial benchmark forecasts. A future
macro candidate needs a separately declared incremental comparison against these controls.

## Targets and universe

SPY and nine legacy sector ETFs: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY.
Both tasks run from the next NYSE session's adjusted open through the fifth session's
adjusted close. Calendar slots are never compressed when data are missing.

- **Variance:** the mean of five squared log-return legs: the first open-to-close leg,
  followed by four close-to-close legs. This is a daily-sampled realized-variance proxy,
  not high-frequency realized variance. Its units are squared fractional log returns
  per session. A display may show `sqrt(252 * variance)` as annualized volatility; raw
  variance remains the scored and exported forecast.
- **Drawdown:** probability of a decline strictly greater than 3% from a running peak
  along the entry price and subsequent five daily closes. Intraday lows are not observed
  by this target. A positive terminal return does not imply that no drawdown occurred.

## Fixed benchmarks

Every fitted model is per asset. There is no sector-direction prediction, class balancing,
adaptive ensemble, hyperparameter search, or performance-based selection in this version.

| Task | Model | Fixed definition |
| --- | --- | --- |
| Variance | EWMA | Alpha .06, at least 60 consecutive valid sessions. Separate intraday and close-to-close states, combined as `(intraday + 4 * close-to-close) / 5`. |
| Variance | HAR on daily data | Direct five-session log-variance OLS using log mean daily squared close-to-close returns over 1, 5 and 22 sessions. A separate final 126-date segment estimates residual smearing. This is a daily proxy HAR, not high-frequency HAR-RV. |
| Variance | GARCH(1,1) | Gaussian, zero mean, separate intraday and close-to-close fits. Forecast the first intraday leg plus close-to-close horizons 2–5, then divide by five. Fit percent log returns and convert squared units back exactly. No endpoint substitution. |
| Drawdown | Event frequency | Smoothed frequency `(events + .5)/(n + 1)` from matured fitting/calibration outcomes. |
| Drawdown | Volatility-only logistic | One feature: log endpoint-matched EWMA variance. Standardize on fitting data, C=.1; regularized sigmoid calibration C=.2 on a separate final 126-date segment. Single-class partitions use their smoothed frequency. |

Training uses a trailing five-year window. At least 504 distinct fitting dates are required.
For HAR and drawdown, all training labels finish strictly before calibration starts and all
calibration labels finish by the fit cutoff. Fitting never reuses calibration examples.
GARCH estimates parameters from past raw returns through the fitting session; it does not
use forward target labels. Failed convergence, invalid parameters or missing input sessions
cause that GARCH forecast to abstain for the month, with the reason retained.

Models refit monthly, frozen within each calendar month. The live launch month's fit uses
its actual first eligible issue session. EWMA and GARCH variance states update from each
newly observed session using the frozen parameters. This is daily state updating with
monthly parameter fitting, not daily hyperparameter optimization.

## Evidence and scoring

Historical forecast origins are 2019–2024 on the pinned price archive in the registry.
This is already observed development history. Neither 2025 nor 2026 is a fresh holdout.
Archive every attempt, prediction, failed fit, audit and dependency environment. No result
is removed or a specification retuned because a benchmark loses.

Three comparisons are primary: HAR versus EWMA, GARCH versus EWMA, and volatility-only
drawdown versus event frequency. Report each for SPY and for the equally weighted nine
sectors. Sector losses are averaged within date before inference; ten correlated assets
do not count as ten independent dates. Match exact origins, assets, endpoints and outcomes.
Report model and paired coverage, including abstentions.

Use QLIKE for variance and Brier for drawdown, with log loss and calibration as secondary
probability diagnostics. The numerical variance floor is 1e-12. Descriptive 95% date-block
intervals use 20-session blocks and 1,500 resamples, retaining gaps. They are not adjusted
proof after six comparisons or repeated inspection. A 60- or 90-day win does not promote
a model. Only genuinely future issued forecasts establish this version's prospective record.

Synthetic diagnostics use three fixed seeds in each of a constant-variance and a persistent
two-state variance world, 1,000 sessions with the last 252 evaluated. The state changes with
probability .02; intraday sigmas are .005/.025 and overnight sigma is half the intraday sigma.
The constant world uses intraday sigma .008. Generate coherent open/close paths and use the
production monthly fitting, prediction and scoring path. The known conditional variance
oracle is recorded for both worlds. These six runs are diagnostics, not a certified false-
positive rate or evidence that market risk has been solved. Preserve all seeds.

## Independent live record

Use `risk_records/risk-1.0.0/` for forecasts, resolutions and operational events, and
`risk_archive/` for inputs, model artifacts and research attempts. The original `records/`
and `archive/models/` are not reused. Publish after the session close plus 45 minutes and
before the next opening, checking again after fitting. Never backfill a missed live issue.
Keep exact information cutoff, issue time, entry open, exit close, target definitions,
feature values, source/registry/model hashes and input vintages.

Resolve each holding window from one archived price vintage. Once valid, resolutions are
immutable. Later corrections must be additive. There is no risk trading policy or automatic
replacement of the continuing direction experiment.

## Hub integration

UnpricedHub/docs/CONTRACT.md was not published when this version was registered. Do not invent
a compatible schema or convert ranks to probabilities, direction to risk, or one holding
window to another. Once the contract is published, pin its revision and add a tested daily
export in UnpricedZ only. Preserve the task, information cutoff, issue time, endpoints,
units and hashes. The Hub remains responsible for independent receipt and scoring.

Integration update, before this version's first evaluation: contract commit
`5bdee50d25f57dac6b85630523f9cdfeb0a5352d` is now pinned, with its unmodified schema and
`hub/core.py` validator vendored under `vendor/unpricedhub/`. Exports are validated with
`validate()` and mandatory jsonschema support. Daily outputs are
`site/data/export/latest-risk-v1-variance-5s-open-close.json` and
`site/data/export/latest-risk-v1-drawdown-gt3pct-5s-open-close.json`, with immutable dated
copies. Hub's horizon convention counts entry-to-exit session-index intervals: four for
our five observed sessions. Prices, forecast values, units and actual endpoints do not change.
The owner authorized new coordination notes in Hub's `notes/to-claude/` only; no other Hub
files may be modified.

Supplementary diagnostics for every variance benchmark include forecast-level and date-level
median QLIKE, the share of total date-mean loss from the worst `ceil(.01 * date count)` dates,
and the mean excluding forecast origins in 2020. Always retain the primary all-date mean.
These decompositions do not select models or create another untouched holdout.

## Primary references

- [arch GARCH forecast equations and horizon indexing](https://arch.readthedocs.io/en/latest/univariate/forecasting.html)
- [arch package and pinned release](https://pypi.org/project/arch/8.0.0/)
- [ALFRED vintage semantics](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)
