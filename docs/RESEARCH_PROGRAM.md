# Research program 0.1.0 — registered 2026-11-04

The user approved four upgrades: point-in-time macro inputs, stronger model selection,
monthly-versus-quarterly refits, and a pretrained challenger. This implements an isolated
development program. It does not replace research-2.0.0, its fitted artifacts, forecasts,
portfolio policy or score history. The official engine's source and requirements remain unchanged.

The executable declaration is [`research_program/registry.json`](../research_program/registry.json).
Every run retains its predictions, inner-selection audit, environment and report under
`archive/program/program-0.1.0/`. Failed attempts are retained too. The newest report is
`site/data/program.json`; it is exploratory research, never a live-score input.

## 1. Economically motivated information

Use ALFRED vintages for DGS10 (rates), T10Y2Y (yield curve), BAA10Y (credit spread),
CPIAUCSL (inflation) and UNRATE (employment). Six fixed predictors comprise the three market
rates/spreads, 12-month inflation, unemployment level and its three-month change. Fixed sector
indicators and macro-by-sector interactions let sectors respond differently. Market controls
also receive those sector indicators, so the comparison isolates the macro addition.

The adapter replays observation revisions in availability order. It derives inflation and
changes using the entire snapshot available then, not today's revised denominator. Because
ALFRED provides dates rather than exact publication times, a vintage becomes usable only at
the close of the first NYSE session strictly after its vintage date. This is a conservative
availability convention, not proof of an exact historical feed timestamp. Series with late
archival coverage remain missing before coverage begins. Stale inputs abstain.

A free FRED API key must be configured as the repository Actions secret `FRED_API_KEY`.
Follow the illustrated [FRED setup instructions](FRED_SETUP.md).
Without it, the macro experiment explicitly reports **blocked**. No revised-data fallback,
secret in the repository, paid data purchase or external model API is involved.

Economic motivation is a hypothesis, not evidence these inputs predict five-session sector
returns. Low-frequency releases may help risk more than short-horizon direction. A later
earnings/filings experiment belongs primarily in the individual-stock lab.

## 2. Limited chronological model selection

The 12 tabular procedures are 2 feature sets × 2 refit cadences × 3 tasks. Each procedure has
exactly three candidate regularization values. No automated neighborhood search runs here.
At each outer fit cutoff, use a trailing five-year window of labels already resolved. Reserve
the final 126 eligible dates for probability calibration or variance residual calibration.
Within the preceding data, evaluate candidates on two sequential 63-date validation blocks,
purging any training label whose endpoint reaches that block. Select by date-mean Brier
(events) or QLIKE (variance), then refit the selected estimator on data strictly before the
calibration block. Do not refit it on the calibration block afterward.

Outer evaluation is 2019–2024, a subset of already observed development history. All assets
on a date stay together. Preprocessing is fit only on fitting data. All candidate losses and
selected values are recorded. Later outer fits may legitimately learn from earlier outer
outcomes once resolved. **Neither observed 2025 nor observed 2026 is called a fresh holdout.**

## 3. Monthly versus quarterly

Run the identical selection procedure with calendar-month and calendar-quarter freezes.
Compare paired forecasts on the same assets and dates, retaining coverage and failed folds.
Do not infer that the faster cadence is better simply because it updates more often.
Every new refit is from historical examples, not a continuation of old optimizer weights.

## 4. Pretrained challenger

Use frozen Amazon Chronos-2, pinned to Hugging Face revision
`29ec3766d36d6f73f0696f85560a422f50e8498c`, with a separate pinned dependency environment.
The initial CPU screen uses the first exchange session of each month in 2019–2024 and 512
past session slots. It runs each series independently (no cross-learning or future covariates).

Forecast histories contain **already completed holding-window targets**, indexed by their
ending session. Predicting five steps ahead then matches the lab's next-open-to-fifth-close
target. This avoids comparing a next-close price forecast with a different return definition.
Missing sessions keep their slots; targets that have not finished cannot enter the context.

Three tasks are scored separately:

| Task | Outcome | Primary score / baseline |
| --- | --- | --- |
| Relative return event | Sector return exceeds SPY over identical endpoints | Brier / earlier-data event frequency |
| Variance | Mean squared log holding-period legs | QLIKE / endpoint-matched EWMA; quantile loss also reported |
| Drawdown event | More than 3% peak-to-trough loss along entry and subsequent daily closes | Brier / earlier-data event frequency |

Drawdown is a daily-close path proxy, not the worst intraday low. It can occur even if the
terminal return is positive. The pretrained variance series is log-transformed; the other
two use completed excess returns and completed drawdown severity. Probabilities come from a
fixed interpolation of predicted quantiles, with 0.1/0.9 tail clipping and a right-continuous
CDF at atoms. They are uncalibrated approximations. Any quantile crossings are repaired by
cumulative maxima and counted. The variance mean is a trapezoidal quantile integral with
flat outer tails, not an assumption that the package's point output is an arithmetic mean.

Chronos was pretrained on real and synthetic data. Overlap with these financial histories
has not been excluded; **historical pretrained results are contamination-uncertain diagnostics**.
A pinned checkpoint forecasting genuinely future outcomes is the decisive comparison.
Fine-tuning is deliberately deferred: first test the frozen checkpoint, then register a
small training-only adaptation with chronological validation and a compute budget. More
optimization is not evidence of more predictive information.

## Reading the results

All pairwise comparisons use exact shared keys and verify identical outcomes. Date-level
moving-block intervals retain calendar gaps; they are descriptive, not adjusted proof after
trying several hypotheses. Macro coverage must be reported with its paired market control.
Chronos comparisons use its same monthly origins, not all daily market predictions. This
small monthly screen has low power and cannot establish a winner.

The result is a shortlist for a separately reviewed prospective shadow launch. Nothing here
automatically promotes a model or changes a live trading rule. A future version needs a new
artifact namespace, immutable issue times before entry and its own resolved live evidence.

## Running

The **Registered research program** Actions workflow runs tests and these comparisons on a
program-code push; it can also be run manually. It has a bounded CPU runtime and no recurring
expensive search. The weekly review checks its status and takes the next registered step.

Local equivalent (Python 3.11):

```sh
pip install -r requirements.txt
python -m pytest -q
python -m research_program
# Optional CPU pretrained comparison:
pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r research_program/requirements-pretrained.txt
python -m research_program --pretrained
```

The pinned archived price input must be present. It remains retrospective provider-adjusted
data, not an as-published price history. Failed or interrupted workflows remain visible;
a green run with missing macro credentials does not mean the macro comparison completed.

## Primary documentation

- [FRED observations and vintage options](https://fred.stlouisfed.org/docs/api/fred/series_observations.html)
- [ALFRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)
- [Chronos model card and training sources](https://huggingface.co/amazon/chronos-2)
- [Pinned Chronos implementation](https://github.com/amazon-science/chronos-forecasting/tree/v2.2.0)
