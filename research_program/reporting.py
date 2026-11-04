from __future__ import annotations

import numpy as np
import pandas as pd

from .selection import loss


def block_interval(daily, sessions, registry):
    """Keep calendar gaps in blocks; don't compress missing dates into adjacency."""
    values = daily.reindex(sessions).to_numpy(dtype=float)
    observed = int(np.isfinite(values).sum())
    result = {"mean": float(np.nanmean(values)) if observed else None, "dates": observed,
              "calendarSessions": len(values), "low": None, "high": None,
              "interpretation": "descriptive interval, no selection-adjusted significance or promotion"}
    block = registry["bootstrapBlockSessions"]
    if observed < max(40, 2 * block):
        return result
    rng = np.random.default_rng(registry["seed"])
    count = int(np.ceil(len(values) / block))
    starts = rng.integers(0, len(values), (registry["bootstrapReplications"], count))
    indices = ((starts[:, :, None] + np.arange(block)) % len(values)).reshape(len(starts), -1)[:, :len(values)]
    sampled = values[indices]
    valid = np.isfinite(sampled).sum(axis=1)
    means = np.nansum(sampled, axis=1)[valid > 0] / valid[valid > 0]
    result.update(low=float(np.quantile(means, .025)), high=float(np.quantile(means, .975)))
    return result


def summary(predictions, task, sessions, registry):
    scored = predictions.dropna(subset=["outcome", "prediction", "baseline"]).copy()
    result = {"issuedRows": len(predictions), "scoredRows": len(scored), "dates": int(scored.date.nunique())}
    if scored.empty:
        return result
    candidate = loss(task, scored.outcome, scored.prediction)
    baseline = loss(task, scored.outcome, scored.baseline)
    date_mean = lambda x: pd.Series(np.asarray(x), index=scored.date).groupby(level=0).mean()
    result.update(metric="QLIKE" if task == "variance" else "Brier",
                  modelLoss=float(date_mean(candidate).mean()), baselineLoss=float(date_mean(baseline).mean()),
                  gain=block_interval(date_mean(baseline - candidate), sessions, registry))
    if task != "variance":
        p = np.clip(scored.prediction.to_numpy(), 1e-7, 1 - 1e-7)
        y = scored.outcome.to_numpy()
        result["logLoss"] = float(date_mean(-y * np.log(p) - (1 - y) * np.log(1 - p)).mean())
        result["calibration"] = []
        for lo in np.arange(0, 1, .1):
            mask = (p >= lo) & (p < lo + .1 + (1e-10 if lo > .89 else 0))
            if mask.any():
                result["calibration"].append({"low": float(lo), "rows": int(mask.sum()),
                                              "predicted": float(p[mask].mean()), "observed": float(y[mask].mean())})
    elif all(f"q{i+1}" in scored for i in range(9)):
        q = scored[[f"q{i+1}" for i in range(9)]].to_numpy()
        error = scored.outcome.to_numpy()[:, None] - q
        levels = np.asarray(registry["pretrained"]["quantiles"])
        result["meanQuantileLoss"] = float(date_mean(np.maximum(levels * error, (levels - 1) * error).mean(axis=1)).mean())
    return result


def paired(a, b, task, sessions, registry):
    keys = ["date", "ticker", "entryDate", "labelEnd"]
    joined = a[keys + ["outcome", "prediction"]].merge(b[keys + ["outcome", "prediction"]],
             on=keys, suffixes=("_a", "_b"), validate="one_to_one")
    scored = joined.dropna(subset=["outcome_a", "outcome_b", "prediction_a", "prediction_b"])
    if not np.allclose(scored.outcome_a, scored.outcome_b):
        raise ValueError("Paired predictions disagree on the outcome vintage or task")
    difference = loss(task, scored.outcome_b, scored.prediction_b) - loss(task, scored.outcome_a, scored.prediction_a)
    daily = pd.Series(difference, index=scored.date).groupby(level=0).mean()
    return {"meaning": "positive means first model has lower loss", "firstRows": len(a), "secondRows": len(b),
            "pairedRows": len(scored), "gain": block_interval(daily, sessions, registry)}
