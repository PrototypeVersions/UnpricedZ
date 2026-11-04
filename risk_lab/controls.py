from __future__ import annotations

import numpy as np
import pandas as pd

from unpriced.data import exchange_schedule
from .core import make_panel
from .evaluate import losses, score, walk_forward
from .storage import ROOT, attempt_directory, now, save_predictions, write


def synthetic_market(cfg, seed, persistent):
    spec, horizon = cfg["controls"], cfg["horizon"]
    rng = np.random.default_rng(seed)
    count = spec["sessions"] + horizon  # Extra prices only resolve the final origins.
    dates = exchange_schedule("2010-01-01", "2020-01-01").index[:count]
    state, previous, records, oracle = 0, 100., [], {}
    low, high = spec["lowIntradaySigma"] ** 2, spec["highIntradaySigma"] ** 2
    average = (low + high) / 2
    for day in dates:
        if persistent and rng.random() < spec["switchProbability"]:
            state = 1 - state
        sigma = (spec["highIntradaySigma"] if state else spec["lowIntradaySigma"]) if persistent else spec["constantIntradaySigma"]
        opening = previous * np.exp(rng.normal(0, sigma * spec["overnightSigmaFraction"]))
        close = opening * np.exp(rng.normal(0, sigma))
        records.append({"date": day, "ticker": "SPY", "open": opening, "close": close,
                        "high": max(opening, close) * 1.001, "low": min(opening, close) * .999, "volume": 100000.})
        expected = [average + (sigma ** 2 - average) * (1 - 2 * spec["switchProbability"]) ** j
                    if persistent else sigma ** 2 for j in range(1, horizon + 1)]
        oracle[day] = (expected[0] + (1 + spec["overnightSigmaFraction"] ** 2) * sum(expected[1:])) / horizon
        previous = close
    return pd.DataFrame(records), oracle


def run_controls(cfg):
    directory, run = attempt_directory(cfg, "controls")
    report = {"experiment": cfg["experiment"], "runId": run, "generatedAt": now(), "status": "running", "runs": [],
              "interpretation": "Six production-path diagnostics. The oracle knows the synthetic latent state; model forecasts do not. No market-skill or false-positive-rate certification."}
    try:
        for persistent in [False, True]:
            for seed in cfg["controls"]["seeds"]:
                local = {**cfg, "assets": {"SPY": "Synthetic SPY"}}
                data, oracle = synthetic_market(local, seed, persistent)
                frame = make_panel(data, local)
                dates = sorted(frame.date.unique())
                start = pd.Timestamp(dates[-cfg["horizon"] - cfg["controls"]["evaluationSessions"]])
                end = pd.Timestamp(dates[-cfg["horizon"] - 1])
                predictions, audit = walk_forward(frame, local, start, end)
                predictions["oracle"] = predictions.date.map(oracle)
                name = f"{'persistent' if persistent else 'constant'}-{seed}"
                result = {"scenario": "persistent two-state variance" if persistent else "constant variance", "seed": seed,
                          "summary": score(predictions, local), "oracleQLIKE": float(np.mean(losses("variance", predictions.realizedVariance, predictions.oracle, cfg))),
                          "predictions": save_predictions(directory / f"{name}.csv.gz", predictions)}
                write(directory / f"{name}-fits.json", audit, immutable=True)
                report["runs"].append(result)
        report["status"] = "completed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report["archivePath"] = str((directory / "report.json").relative_to(ROOT))
        write(directory / "report.json", report, immutable=True)
        write(ROOT / "site/data/risk_controls.json", report)
    return report
