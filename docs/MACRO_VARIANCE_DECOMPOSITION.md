# Variance loss decomposition — additive diagnostic

Source: the unchanged [registered macro report](../archive/program/program-0.1.0/41759065718-1/report.json).
Every archived CSV checksum was verified and every reconstructed mean matches its registered
loss within 1e-9. [Machine-readable decomposition](../analysis/program-0.1.0/41759065718-1/variance-decomposition.json)
and [reproducible script](../analysis/variance_decomposition.py).

## All variance procedures and matched EWMA baselines

Lower QLIKE is better. The registered mean weights forecast dates equally after averaging
within date. Both forecast-level and date-level medians are shown to remove ambiguity.
Worst-date share uses the largest `ceil(1% × date count)` daily mean losses: 16 of 1,510 dates,
or one of 72 dates for the sparse Chronos screen. The latter is 1.39%, not exactly 1%.

| Model | Dates | Registered mean | Forecast median | Date median | Worst-date share | Mean excluding 2020 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| market-M-variance | 1510 | 0.49280 | 0.18205 | 0.28704 | 16.1% (16 dates) | 0.33600 |
| ewma-daily | 1510 | 0.41370 | 0.16866 | 0.27499 | 15.2% (16 dates) | 0.33504 |
| market-Q-variance | 1510 | 0.50112 | 0.18352 | 0.28574 | 15.9% (16 dates) | 0.33564 |
| macro-M-variance | 1510 | 5.18726 | 0.22081 | 0.32037 | 80.0% (16 dates) | 0.36174 |
| macro-Q-variance | 1510 | 25.12044 | 0.23451 | 0.32577 | 80.9% (16 dates) | 0.36601 |
| chronos-variance | 72 | 0.39867 | 0.11966 | 0.22797 | 13.8% (1 dates) | 0.32769 |
| ewma-chronos-matched | 72 | 0.41523 | 0.13080 | 0.20985 | 15.5% (1 dates) | 0.32622 |

## What the extremes mean

The extreme macro losses are concentrated in 2020, but the worst observations severely
**underpredict** variance. For example, quarterly macro on 2020-06-04 / XLK
predicted `1.55847099995e-08` against realized `0.000833299301294`:
realized variance was **53,469 times** the forecast. Its QLIKE was
53,457.1. Reversing that ratio would incorrectly describe overprediction.

QLIKE is `r - log(r) - 1`, with `r = realized / predicted`: severe underprediction enters
approximately linearly in this ratio; severe overprediction is penalized logarithmically.
Both directions of extrapolation occur: the quoted 99th/99.9th percentiles of predicted/realized variance reproduce (monthly about 850 / 42,117; quarterly about 957 / 29,605). Those upper overprediction quantiles are valid, but they do not identify the forecasts with the largest QLIKE. The CSVs verify the direction and concentration of the largest losses. These patterns are consistent
with a log-linear model extrapolating badly during a new regime; the output decomposition
alone does not establish which individual input or coefficient caused the failure.

A median predicted/realized ratio above one is not by itself evidence that smearing is biased.
A conditional-mean variance forecast can exceed the median noisy realized variance. Assess
mean-forecast calibration and proper loss on held-out dates before changing that estimator.
The JSON retains each model's median ratio as a diagnostic, not a proof of miscalibration.

Excluding 2020 is a post hoc stress-period decomposition, not a revised headline result,
an improved backtest, or evidence from an untouched holdout. It does not erase the large
registered losses or establish that macro data have no predictive information in general.
These particular macro procedures did not improve on their market controls. Any proposal to
model a residual relative to EWMA, restrict extrapolation, or change calibration belongs in a
new registered experiment; none has been retrofitted into this result.
