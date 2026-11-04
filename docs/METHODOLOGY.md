# Methodology · research-2.0.0

## Purpose and universe

UNPRICED compares forecasting hypotheses against explicit baselines. The initial universe is XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV and XLY, with SPY as the reference. These legacy funds have long histories but are selected retrospectively. They do not cover every modern sector; their underlying constituents and sector classifications change. No stock-selection or survivorship-free claim is made.

QQQ, IWM, TLT, GLD, EFA and EEM are downloaded as context; the first fitted specification uses the bond and gold context alongside SPY. Additional downloaded series do not imply additional predictive features.

## The clock and target

Let t be a decision session, O the provider-adjusted opening price, C the provider-adjusted closing price, and h=5 exchange sessions. The asset return is C[t+5]/O[t+1]-1. Excess return subtracts SPY over those same endpoints. The event scored by Brier/log loss is excess return > 0. An underperformer is not necessarily a negative absolute return, and vice versa.

This means next-session open through the fifth session close. It is **not** five open-to-open intervals. Holidays come from the exchange calendar. A missing sector bar does not remove an exchange session or shorten the horizon.

The live cycle uses a completed session, with a 45-minute provider buffer. The actual issue time must precede the next session opening. If fitting finishes too late, publication is rejected. The same day's first immutable snapshot is retained on retries. Overnight publication is permitted while the entire target return window is still in the future.

## Inputs and reproducibility

The initial free adapter is Yahoo Finance via yfinance. Adjusted historical OHLC may be revised and is not a point-in-time historical publication archive. All results are labeled accordingly. Data are checked for duplicate keys, required symbols, OHLC consistency, finite positive prices, and current-session coverage. Feature calculation does not forward-fill missing observations. Missing breadth inputs are excluded with explicit coverage, not interpreted as below-average prices.

Full inputs are archived for historical research and each new quarterly live fit. Daily windows covering feature lookbacks and resolution endpoints are archived separately. Archives are compressed, content-addressed CSVs with round-trip numerical precision. Forecasts store exact feature rows, hashes, code/config revisions, actual issue time and intended endpoints. Models and Python package versions are retained.

Both resolution endpoints are taken from the **same** archived data vintage. A fixed adjusted entry from an old download is never divided into a newly adjusted exit. Resolutions are frozen once first valid; subsequent provider revisions require an additive correction if material.

## Features and fitting

Return predictors include one-session return, relative 5/20/60-session momentum, 20-session volatility and its SPY ratio, log-volume surprise, SPY trend and volatility, valid sector breadth, cross-sectional dispersion, and bond/gold trend. All use data through their decision close.

The rolling five-year development window includes a final 126 eligible forecast-date calibration segment. Training outcomes must end strictly before the first calibration feature date; calibration outcomes must end by the fit cutoff. All assets from each date share a partition. The base model is not refitted after calibration.

Models remain frozen over each calendar-quarter test block. Live launch fits on its actual launch session and then freezes through that quarter; later quarters refit at their first eligible live publication. Thus the first live quarter need not share the historical research fit date. This distinction is recorded rather than hidden.

Baselines are constant 50%, historical event frequency, and a three-feature relative-momentum logistic model. The primary candidate is unweighted-class logistic regression with standardized inputs and C=0.1. Raw and regularized-sigmoid-calibrated outputs are both scored. A histogram-boosted challenger uses fixed complexity (60 rounds, seven leaves, minimum 100 leaf rows, learning rate 0.04, L2=10) with random early stopping disabled. Calibrators use C=0.2. No automatic ensemble or performance-driven reweighting exists.

A separate Ridge model (alpha=100) predicts excess return. Its calibration residual 10th and 90th percentiles form a pooled empirical 80% band. This is not a guaranteed conditional prediction interval or a distribution-free conformal guarantee. Coverage is measured on held-out observations.

## Risk model

The risk target is the mean squared log return across the same five-session holding window: the first session's open-to-close leg followed by four close-to-close legs. It is a daily-sampled realized-variance proxy. Annualization is sqrt(252 * mean squared return).

The simple baseline combines a separate intraday squared-return EWMA with four close-to-close squared-return EWMAs (alpha=.06), matching the target window exactly. The challenger is a log-variance Ridge regression using past 5/20/60-session squared returns, recent negative-return magnitude, and SPY variance. Calibration residual smearing converts the log prediction to an arithmetic variance estimate. The model is HAR-style, not an implementation of high-frequency HAR-RV. Positive variance forecasts are compared by QLIKE; risk skill is never substituted for return skill.

## Historical evaluation

Quarterly walk-forward tests begin in 2016. Configuration fixes 2016–2024 as development, 2025 as confirmation, and 2026 onward as recent historical monitoring. The initial specification is committed before seeing any generated results. Once the 2025 results are examined, that period is no longer untouched for redesigned specifications. Historical research never appears in the LIVE record.

Brier/log loss are evaluated on identical complete rows. Paired loss differences are averaged within each forecast date. A circular moving-block bootstrap uses 20-session blocks and 1,500 resamples to describe uncertainty; at least 40 dates are required to display an interval. These are descriptive intervals, not universal guarantees, independent-observation claims, or selection-adjusted promotion tests. Rank IC across nine sectors is a noisy secondary diagnostic. Calibration bins are descriptive and retain row counts.

## Synthetic controls

Controls use production features, purged fitting, calibration and held-out scoring. Symmetric relative log-return innovations generate a directional null, while shared factors and lagged-squared-return volatility persist. A risk predictor can legitimately succeed in the directional null. Weak and moderate positives introduce lagged relative momentum with strengths .08 and .25. Fixed seeds and all outcomes are retained.

Twelve seeds per condition are an initial diagnostic. Seed-level detection uses a positive lower bound for paired Brier improvement over the known constant-50% null oracle. Beating an estimated noisy base rate alone does not establish signal. A positive lower bound of a two-sided 95% interval corresponds to a nominal one-sided 2.5% tail under ideal assumptions, not a guaranteed 5% false-positive test. Reported rate intervals are Wilson intervals across seeds. The experiment is not retuned until every weak-signal run succeeds, and is not advertised as proving a 5% false-positive rate.

## Reference portfolio

The policy begins with $1,000 and has no leverage or shorting. At a permitted cohort decision, choose up to three sectors with calibrated logistic probability >=55% and expected excess return >0.20%, ranked by expected excess. Allocate 30% to each, with the rest in cash. Hold from next open to the fifth close and deduct 10 bps each side. There is no overlapping cohort; the next decision can be made at the previous cohort's exit close.

This uses adjusted reference returns, not real order fills. Prospective plans are included in their immutable forecast snapshot before entry. Settled equity changes only after a cohort's outcome is resolved; it is not a daily mark-to-market balance. The SPY comparison holds exactly the same open-to-close windows and excludes overnight gaps between cohorts, so it is explicitly **not** continuous buy-and-hold SPY. Cash earns zero. Thresholds are fixed experimental choices, not optimized investment recommendations.
