"""Additive diagnostics from frozen predictions; never refit or rewrite a report."""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path


def loss_decomposition(dated_losses):
    grouped = collections.defaultdict(list)
    all_losses = []
    for date, value in dated_losses:
        grouped[str(date)[:10]].append(float(value))
        all_losses.append(float(value))
    if not all_losses:
        return None
    daily = {date: statistics.fmean(values) for date, values in grouped.items()}
    count = max(1, math.ceil(.01 * len(daily)))
    worst = sorted(daily.items(), key=lambda pair: (-pair[1], pair[0]))[:count]
    total = math.fsum(daily.values())
    excluded = [value for date, value in daily.items() if not date.startswith("2020-")]
    return {"rows": len(all_losses), "dates": len(daily), "meanQLIKE": statistics.fmean(daily.values()),
            "medianForecastQLIKE": statistics.median(all_losses), "medianDateQLIKE": statistics.median(daily.values()),
            "worstDateCount": count, "worstDateFraction": count / len(daily),
            "worstDateShare": math.fsum(value for _, value in worst) / total if total else 0.,
            "excluding2020MeanQLIKE": statistics.fmean(excluded) if excluded else None,
            "excluding2020Dates": len(excluded), "worstDates": [{"date": date, "meanQLIKE": value} for date, value in worst]}


def decompose(rows, column="prediction"):
    dated, extremes, ratios = [], [], []
    for row in rows:
        y, forecast = float(row["outcome"]), float(row[column])
        if not math.isfinite(y) or not math.isfinite(forecast):
            continue
        y, forecast = max(y, 1e-10), max(forecast, 1e-10)  # Exact program-0.1.0 scoring floor.
        ratio = y / forecast
        loss = ratio - math.log(ratio) - 1
        dated.append((row["date"], loss))
        ratios.append(forecast / y)
        extremes.append({"date": row["date"], "ticker": row["ticker"], "qlike": loss,
                         "realizedVariance": y, "predictedVariance": forecast,
                         "realizedOverPredicted": ratio, "predictedOverRealized": forecast / y})
    result = loss_decomposition(dated)
    result["medianPredictedOverRealized"] = statistics.median(ratios)
    result["worstForecasts"] = sorted(extremes, key=lambda row: -row["qlike"])[:10]
    return result


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "archive/program/program-0.1.0/41759065718-1/report.json"
    report = json.loads(source.read_text())
    results = {}
    candidates = ["market-M-variance", "market-Q-variance", "macro-M-variance", "macro-Q-variance", "chronos-variance"]
    for name in candidates:
        info = report["tasks"][name]
        raw = gzip.decompress((root / info["archive"]["path"]).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == info["archive"]["csvSha256"]
        rows = list(csv.DictReader(raw.decode().splitlines()))
        result = decompose(rows)
        assert abs(result["meanQLIKE"] - info["modelLoss"]) < 1e-9
        result["source"] = info["archive"]
        results[name] = result
        if name in ["market-M-variance", "chronos-variance"]:
            baseline = decompose(rows, "baseline")
            assert abs(baseline["meanQLIKE"] - info["baselineLoss"]) < 1e-9
            baseline["source"] = {**info["archive"], "column": "baseline"}
            results["ewma-daily" if name == "market-M-variance" else "ewma-chronos-matched"] = baseline
    analysis = {"sourceReport": str(source.relative_to(root)), "sourceReportSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "operation": "Frozen forecast decomposition; no refitting, model changes, or report replacement",
                "formula": "r - log(r) - 1, r = max(realized, 1e-10) / max(predicted, 1e-10)",
                "dateRule": "Average losses across assets within forecast origin; worst 1% uses ceil(.01 * dates). Exclude 2020 by forecast-origin year.",
                "models": results}
    destination = root / "analysis/program-0.1.0/41759065718-1"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "variance-decomposition.json").write_text(json.dumps(analysis, indent=2) + "\n")
    table = []
    for name, result in results.items():
        table.append(f"| {name} | {result['dates']} | {result['meanQLIKE']:.5f} | {result['medianForecastQLIKE']:.5f} | {result['medianDateQLIKE']:.5f} | {result['worstDateShare']:.1%} ({result['worstDateCount']} dates) | {result['excluding2020MeanQLIKE']:.5f} |")
    worst = results["macro-Q-variance"]["worstForecasts"][0]
    text = """# Variance loss decomposition — additive diagnostic

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
""" + "\n".join(table) + f"""

## What the extremes mean

The extreme macro losses are concentrated in 2020, but the worst observations severely
**underpredict** variance. For example, quarterly macro on {worst['date']} / {worst['ticker']}
predicted `{worst['predictedVariance']:.12g}` against realized `{worst['realizedVariance']:.12g}`:
realized variance was **{worst['realizedOverPredicted']:,.0f} times** the forecast. Its QLIKE was
{worst['qlike']:,.1f}. Reversing that ratio would incorrectly describe overprediction.

QLIKE is `r - log(r) - 1`, with `r = realized / predicted`: severe underprediction enters
approximately linearly in this ratio; severe overprediction is penalized logarithmically.
The CSVs verify the direction and concentration of the errors. These patterns are consistent
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
"""
    (root / "docs/MACRO_VARIANCE_DECOMPOSITION.md").write_text(text)
    print(json.dumps({name: {k: result[k] for k in ["meanQLIKE", "medianForecastQLIKE", "medianDateQLIKE", "worstDateShare", "excluding2020MeanQLIKE"]} for name, result in results.items()}, indent=2))
    print("Worst quarterly macro forecast:", json.dumps(worst))


if __name__ == "__main__":
    main()
