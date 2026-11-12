# A reader’s guide to UNPRICED

This is **UnpricedZ, the Market & Sector Risk Lab**. UNPRICED studies market forecasts, tests their accuracy, and asks whether they can support useful trading decisions. Risk is one part of that larger question.

## Three components, different jobs

| Component | Job | What it does not do |
| --- | --- | --- |
| Stock Forecasting Lab — UnpricedX | Ranks individual stocks and runs its own stock paper portfolio. | Its ranking score alone does not establish trading profitability. |
| Market & Sector Risk Lab — UnpricedZ | Forecasts five-session variance and drawdown for SPY and nine sector ETFs. Its earlier sector-direction study and sector-ETF paper portfolio continue separately. | The new risk forecasts do not currently control that portfolio. |
| Independent Results Hub — UnpricedHub | Stores its own copies of exported forecasts, records receipt times and scores outcomes using its own price download. | It does not trade, combine forecasts, promote models, or audit portfolio profit. |

X and Z distinguish the two forecasting labs. The [Stock Forecasting Lab](https://prototypeversions.github.io/UnpricedX/) and [Independent Results Hub](https://prototypeversions.github.io/UnpricedHub/) have separate websites. This site explains its own methods and records in full.

## What is running?

- **risk-1.0.0:** the risk experiment, with monthly model fits and daily volatility-state updates and forecasts.
- **research-2.0.0:** the continuing sector-direction experiment, with quarterly fits, daily forecasts, and fixed rules for a $1,000 simulated sector portfolio.
- **program-0.1.0:** a completed historical research program. Its reports, including the negative macro result, remain recorded as originally produced. It is not an automatically promoted live model.
- **A combined risk-aware stock portfolio:** proposed research only. It has no live trading record on this site. See the [proposed sequence](TRADING_RESEARCH_PLAN.md).

## What do the forecasts mean?

**Variance** measures the size of price movements without predicting their direction. Here the target is the average of five squared log returns: the first session’s opening-to-closing move and four following close-to-close moves. This is a daily-sampled proxy, not a measure built from intraday observations.

**Volatility** is the square root of variance. For readability the site displays `sqrt(252 × forecast variance)` as annualized volatility. A displayed 20% is neither an expected 20% five-day move nor a promise that prices stay inside a particular interval. The models forecast variance; annualization changes display units only.

**Drawdown** is a decline from a running peak. The event here is a decline **strictly greater than 3%**, using the entry opening price and five session closes. Intraday lows are excluded. For example, a price path of 100 → 106 → 102 ends above entry but falls about 3.77% from its peak, so the event occurs. An exact 3% decline does not pass a “greater than 3%” threshold.

**Relative return or excess return** compares an asset with SPY. A sector losing 2% while SPY loses 5% outperforms by 3 percentage points. A correct relative forecast can therefore lead to an absolute loss when traded.

**A probability** is a frequency claim about repeated comparable forecasts, not a certainty about this occasion. A 20% drawdown forecast can be reasonable whether or not a drawdown happens on one date.

## How are forecasts graded?

| Measure | Calculation and interpretation |
| --- | --- |
| QLIKE | With `r = realized variance / forecast variance`, loss is `r − ln(r) − 1`. Zero is a perfect match; lower average loss is better. The implementation retains its registered numerical floor. |
| Brier score | For forecast probability `p` and event `y` (0 or 1), loss is `(p − y)²`. Lower is better. |
| Log loss | `−[y ln(p) + (1−y) ln(1−p)]`, with the declared probability clipping. It penalizes confident errors strongly. The direction study reports it alongside Brier. |
| Rank correlation / rank IC | Spearman correlation between predicted and observed orderings. +1 means identical order, −1 reversed order, and 0 no measured rank association in that sample. It is not portfolio return. |
| Calibration | Compares predicted probabilities with observed event frequencies in groups of forecasts. Counts matter: a small group can look poorly or perfectly calibrated by chance. |

For QLIKE, realized variance twice the forecast gives about **0.307**; realized variance half the forecast gives about **0.193**. For Brier, a 20% prediction scores **0.04** if the event does not happen and **0.64** if it does. Predicting 50% always scores 0.25, but a rare-event forecast should also be compared with the historical frequency of that event.

The variance baselines and challengers are **EWMA** (exponentially weighted moving average), **HAR** (heterogeneous autoregressive model using daily price moves), and **GARCH(1,1)** (generalized autoregressive conditional heteroskedasticity). Drawdown models are historical event frequency and a calibrated logistic model using volatility alone. Definitions and exact settings appear in the [risk protocol](RISK_PROTOCOL.md) and [risk registry](../risk_lab/registry.json).

Risk score comparisons are paired on common assets and dates. Windows overlap and sectors move together, so many rows do not mean many independent trials. The registered comparison uses a 20-session block bootstrap with 1,500 resamples. Its intervals are descriptive and do not correct for every research idea tried.

## What does “learning” mean here?

**Training** estimates model parameters from earlier observations. **Calibration** uses a later, separate segment to adjust predictions. **Evaluation** tests those predictions on dates after the fit. **Purging** removes examples whose outcome windows would overlap the next segment. These chronological boundaries avoid training on outcomes that were not yet available.

Risk supervised models use a trailing five-year window, at least 504 fitting dates, and a final 126-date calibration segment. Parameters are fitted monthly. Daily observations still update the volatility state and produce new predictions. The direction study refits quarterly. The portfolio’s trading rules remain fixed.

**Historical / retrospective** means tested on past data. **Prospective / live forecast** means a prediction issued before its target began. “Live” does not mean money was traded. An inspected historical period is no longer a fresh holdout for a redesigned model. Updating models with new observations does not guarantee that performance improves.

**Synthetic controls** are simulated worlds used to test whether a method responds to known structure or invents patterns in noise. A good synthetic result does not establish a real-market edge. Agreement between AI reviewers is not evidence of forecasting skill either.

## Timing and provenance

| Term | Meaning |
| --- | --- |
| Information cutoff | Latest information the forecast is allowed to use. |
| Issue time | When the lab recorded the forecast. It can be later than the information cutoff. |
| Entry / exit | Exact start and end of the target window. For risk, next exchange-session open through the fifth session close. |
| Session | A trading day on the New York Stock Exchange calendar, not an arbitrary weekday. Holidays and early closes matter. |
| Frozen record | A saved forecast or outcome that must not be silently replaced. Corrections and new versions require their own history. |
| SHA-256 hash / fingerprint | A digest identifying exact file bytes. It detects changes; by itself it does not prove when a file existed. |
| Input vintage | The particular downloaded dataset used for a calculation. Historical adjusted prices can later be revised by the provider. |
| Hub receipt | The Hub’s separately recorded arrival time and copy. A file first seen after entry is late, even if the lab’s stated issue time is earlier. |
| Registered version | Questions, rules and settings recorded before evaluation. This is not regulatory registration or certification of skill. |
| Abstention | No forecast from a model because required inputs, fits or checks are unavailable. Missing estimates are not zero predictions. |

The Hub uses its own price download from the same public provider, so it offers a separate check while still sharing possible provider errors. Scores require a completed window, valid data, and a successful scoring run. Several forecasts issued on one date or for overlapping windows are not independent evidence.

## Reading the $1,000 experiment

The sector portfolio uses the calibrated logistic direction model. To qualify, a sector needs at least **55% probability of outperforming SPY** and expected excess return **greater than 0.20%**. Up to three qualifying sectors are selected by expected excess return, at **30% allocation each**. Remaining capital stays in cash. The experiment models **0.10% cost on each side** and holds from the next session open to the fifth session close. Cohorts do not overlap. See the [exact configuration](../config.json).

The latest plan’s explanation uses the frozen forecasts that actually created it. A newer daily forecast may exist while the earlier portfolio window is still open. Holding all cash is permitted; the next decision still follows the declared cohort cycle.

**Settled equity** changes after a whole holding window resolves. It is not a daily valuation of open positions. The chart cannot describe intraperiod drawdown. The **SPY reference** uses the same holding windows and excludes gaps between cohorts; it is not continuous buy-and-hold. The policy includes modeled costs, whereas this SPY reference is before trading costs. Cash earns zero. Exposure differences also affect the comparison.

These are simulations using adjusted reference prices, with no verified broker fills. Forecast scores, allocation quality, and portfolio profit answer different questions. None should stand in for the other two.

## Original evidence and later diagnostics

The registered macro outcome remains in its [original review](PROGRAM_MACRO_REVIEW_2026-11-04.md) and [original report](../archive/program/program-0.1.0/41759065718-1/report.json). The [variance decomposition](MACRO_VARIANCE_DECOMPOSITION.md) reports median QLIKE, the share of loss from the worst 1% of dates, and results excluding 2020 for every variance model. Excluding 2020 diagnoses sensitivity; it does not replace the registered result.

Read the [direction methodology](METHODOLOGY.md), [risk protocol](RISK_PROTOCOL.md), and [research program](RESEARCH_PROGRAM.md) for the full specifications and limits.
