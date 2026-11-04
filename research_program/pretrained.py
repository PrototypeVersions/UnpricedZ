"""Pinned frozen Chronos challenger. Historical evidence is contamination-uncertain."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .panel import TARGETS, resolved_history


def probability_above(quantiles, levels, threshold):
    # Duplicate quantiles represent atoms: use the rightmost CDF value at the atom.
    values = np.maximum.accumulate(np.asarray(quantiles, dtype=float))
    unique = np.unique(values)
    cdf = np.array([max(np.asarray(levels)[values == value]) for value in unique])
    return float(1 - np.interp(threshold, unique, cdf, left=levels[0], right=levels[-1]))


def quantile_mean(values, levels):
    """Finite-tail approximation; the package's point output is not assumed a mean."""
    return float(np.trapezoid(np.r_[values[0], values, values[-1]], np.r_[0, levels, 1]))


def load_pipeline(spec):
    import torch
    from chronos import Chronos2Pipeline
    torch.set_num_threads(2)
    return Chronos2Pipeline.from_pretrained(spec["model"], revision=spec["revision"],
                                           device_map="cpu", torch_dtype=torch.float32)


def predict_date(pipeline, frame, asof, cfg, registry):
    spec = registry["pretrained"]
    requests, identifiers, skipped = [], [], []
    current = frame[frame.date == pd.Timestamp(asof)].set_index("ticker")
    for task in registry["tasks"]:
        for ticker in cfg["universe"]:
            context = resolved_history(frame, ticker, task, asof, spec["contextSessions"])
            if np.isfinite(context).sum() < spec["minimumObservedContext"]:
                skipped.append({"date": str(pd.Timestamp(asof).date()), "ticker": ticker, "task": task, "reason": "insufficient-context"})
                continue
            requests.append(context.astype(np.float32).reshape(1, -1))
            identifiers.append((task, ticker))
    if not requests:
        return pd.DataFrame(), skipped
    quantiles, _ = pipeline.predict_quantiles(requests, prediction_length=cfg["horizon"],
                                              quantile_levels=spec["quantiles"],
                                              context_length=spec["contextSessions"], cross_learning=False)
    rows = []
    for (task, ticker), tensor in zip(identifiers, quantiles):
        q = tensor.detach().cpu().numpy()[0, cfg["horizon"] - 1, :]
        if not np.isfinite(q).all():
            raise ValueError("Nonfinite Chronos output")
        repaired = bool((np.diff(q) < 0).any())
        q = np.maximum.accumulate(q)
        source = current.loc[ticker]
        if task == "variance":
            q = np.exp(np.clip(q, -25, 5))
            value = quantile_mean(q, spec["quantiles"])
        elif task == "drawdown":
            q = np.clip(q, 0, 1)
            # Continuous-model approximation at 3%; the endpoint convention is documented.
            value = probability_above(q, spec["quantiles"], registry["drawdownThreshold"])
        else:
            value = probability_above(q, spec["quantiles"], 0)
        rows.append({"date": pd.Timestamp(asof), "ticker": ticker, "entryDate": source.entryDate,
                     "labelEnd": source.labelEnd, "task": task, "outcome": source[TARGETS[task]],
                     "prediction": value, "quantileMonotonicityRepaired": repaired,
                     **{f"q{i+1}": float(v) for i, v in enumerate(q)}})
    if len(rows) != len(requests):
        raise ValueError("Chronos output count differs from requested series count")
    return pd.DataFrame(rows), skipped


def historical_screen(frame, cfg, registry):
    pipeline = load_pipeline(registry["pretrained"])
    dates = pd.DatetimeIndex(sorted(frame[(frame.date >= registry["outerStart"]) &
                                         (frame.date <= registry["outerEnd"])].date.unique()))
    results, skipped = [], []
    for period in dates.to_period("M").unique():
        date = dates[dates.to_period("M") == period][0]
        result, missing = predict_date(pipeline, frame, date, cfg, registry)
        results.append(result)
        skipped.extend(missing)
        print(f"Chronos monthly development origin {date.date()}", flush=True)
    return pd.concat(results, ignore_index=True), skipped
