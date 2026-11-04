from __future__ import annotations

import copy
import math

import numpy as np
import pandas as pd

from .data import exchange_schedule
from .evaluation import block_interval, summarize, walk_forward
from .features import panel
from .io import ROOT, now, provenance, write


def synthetic_market(cfg, seed, strength=0.0, sessions=1800):
    """Directional null has symmetric conditional relative log returns.

    Shared factors and predictable conditional volatility remain present. A risk
    model is therefore allowed to succeed even in the directional-null world.
    Positive controls inject lagged relative momentum, a production feature.
    """
    rng = np.random.default_rng(seed)
    symbols = [cfg["benchmark"]] + list(cfg["universe"]) + cfg["context"]
    dates = exchange_schedule("2010-01-01", "2020-12-31").index[:sessions]
    n = len(symbols)
    returns = np.zeros((sessions, n))
    variance = 0.0001
    sector_indices = [symbols.index(s) for s in cfg["universe"]]
    for t in range(sessions):
        previous = returns[t - 1, 0] if t else 0
        variance = 0.000003 + 0.08 * previous ** 2 + 0.89 * variance
        scale = np.sqrt(variance)
        market, sector = rng.normal(size=2)
        returns[t, 0] = scale * market
        for j in range(1, n):
            mean = 0.0
            if t >= 60 and j in sector_indices:
                past = returns[t - 20:t, j] - returns[t - 20:t, 0]
                score = past.sum() / max(past.std() * np.sqrt(20), 1e-7)
                mean = strength * scale * np.tanh(score)
            returns[t, j] = scale * market + scale * (0.35 * sector + 0.8 * rng.normal()) + mean
    prices = 100 * np.exp(np.cumsum(returns, axis=0))
    prev = np.vstack([np.full(n, 100.0), prices[:-1]])
    opens = prev * np.exp(0.25 * returns)
    rows = []
    for j, symbol in enumerate(symbols):
        rows.append(pd.DataFrame({"date": dates, "ticker": symbol,
            "open": opens[:, j], "close": prices[:, j],
            "high": np.maximum(opens[:, j], prices[:, j]) * 1.003,
            "low": np.minimum(opens[:, j], prices[:, j]) * 0.997,
            "volume": rng.lognormal(16, 0.4, sessions)}))
    return pd.concat(rows, ignore_index=True)


def wilson(successes, total):
    if not total:
        return [None, None]
    z, p = 1.96, successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z / denominator * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return [max(0.0, center - radius), min(1.0, center + radius)]


def run_controls(cfg, seed_count=None):
    seed_count = cfg["controlsSeeds"] if seed_count is None else seed_count
    rows = []
    for strength in [0.0, cfg["controlsSignalStrength"], 0.25]:
        for seed in range(seed_count):
            local = copy.deepcopy(cfg)
            data = synthetic_market(cfg, cfg["modelSeed"] + seed, strength)
            dates = sorted(data.date.unique())
            local["researchStart"] = str(pd.Timestamp(dates[-252]).date())
            local["bootstrapReplications"] = 500
            predictions, folds = walk_forward(panel(data, local), local)
            metrics = summarize(predictions, local)
            model = next(m for m in metrics["models"] if m["id"] == "logistic")
            # The null oracle is 0.5. Beating a noisy estimated base rate is NOT proof of signal.
            def oracle_gain(name):
                losses = .25 - (predictions[f"p_{name}"] - predictions.outcome) ** 2
                daily = pd.Series(losses.to_numpy(), index=predictions.date).groupby(level=0).mean().sort_index()
                return block_interval(daily, local["bootstrapBlockSessions"], local["bootstrapReplications"])
            gain = oracle_gain("logistic")
            rows.append({"seed": cfg["modelSeed"] + seed, "strength": strength,
                         "dates": metrics["dates"], "brier": model["brier"],
                         "improvement": gain, "positiveDetection": gain["low"] is not None and gain["low"] > 0,
                         "models": [{"id": m["id"], "brier": m["brier"], "improvement": oracle_gain(m["id"])} for m in metrics["models"]]})
            print(f"Control strength={strength} seed={seed}: gain={gain['mean']:.6f}", flush=True)
    groups = []
    for strength in sorted(set(x["strength"] for x in rows)):
        items = [x for x in rows if x["strength"] == strength]
        found = sum(x["positiveDetection"] for x in items)
        groups.append({"strength": strength, "name": "No directional signal" if strength == 0 else "Weak planted signal" if strength < 0.2 else "Moderate planted signal",
                       "runs": len(items), "detections": found, "detectionRate": found / len(items),
                       "rateInterval95": wilson(found, len(items)),
                       "meanImprovement": float(np.mean([x["improvement"]["mean"] for x in items]))})
    report = {"status": "completed-diagnostic", "generatedAt": now(), "provenance": provenance(),
              "primaryModel": "logistic", "comparison": "Known constant-50% directional-null oracle", "sessionsPerRun": 1800, "evaluationSessions": 252,
              "groups": groups, "runs": rows,
              "note": "Independent synthetic seeds; each run exercises production features, purged quarterly fitting, calibration and date-block evaluation. Twelve seeds provide a diagnostic, not a precise false-positive guarantee. Failed or weak detection remains visible. No model is promoted by this report."}
    write(ROOT / "site/data/controls.json", report)
    return report
