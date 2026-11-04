from __future__ import annotations

import subprocess
import sys

import numpy as np
import pandas as pd

from research_program.reporting import block_interval
from unpriced.data import exchange_schedule
from analysis.variance_decomposition import loss_decomposition
from .core import fit_asset, make_panel, predict_asset
from .storage import ROOT, attempt_directory, load_history, now, provenance, save_predictions, write


def losses(task, outcomes, forecasts, cfg):
    if task == "drawdown":
        return (np.asarray(outcomes) - np.asarray(forecasts)) ** 2
    ratio = np.clip(np.asarray(outcomes), cfg["varianceFloor"], None) / np.clip(np.asarray(forecasts), cfg["varianceFloor"], None)
    return ratio - np.log(ratio) - 1


def score(frame, cfg):
    result = {"forecastDates": int(frame.date.nunique()), "rows": len(frame), "groups": {}}
    sessions = exchange_schedule(frame.date.min().date(), frame.date.max().date()).index
    groups = {"SPY": frame[frame.ticker == "SPY"], "sectors": frame[frame.ticker != "SPY"]}
    for group, source in groups.items():
        if source.empty:
            continue
        section = {"models": [], "comparisons": [], "expectedRows": len(source)}
        for task, target, models, baseline in [
            ("variance", "realizedVariance", cfg["varianceModels"], "ewma"),
            ("drawdown", "drawdownEvent", cfg["drawdownModels"], "base_rate")]:
            for model in models:
                valid = source.dropna(subset=[target, model])
                item = {"task": task, "model": model, "issuedRows": int(source[model].notna().sum()),
                        "scoredRows": len(valid), "dates": int(valid.date.nunique()),
                        "metric": "QLIKE" if task == "variance" else "Brier", "loss": None}
                if len(valid):
                    daily = pd.Series(losses(task, valid[target], valid[model], cfg), index=valid.date).groupby(level=0).mean()
                    item["loss"] = float(daily.mean())
                    if task == "variance":
                        item["decomposition"] = loss_decomposition(zip(valid.date, losses(task, valid[target], valid[model], cfg)))
                    if task == "drawdown":
                        p = np.clip(valid[model].to_numpy(), 1e-12, 1 - 1e-12)
                        y = valid[target].to_numpy()
                        item["logLoss"] = float(pd.Series(-y * np.log(p) - (1-y) * np.log(1-p), index=valid.date).groupby(level=0).mean().mean())
                        item["calibration"] = []
                        for lo in np.arange(0, 1, .1):
                            mask = (p >= lo) & (p < lo + .1 + (1e-10 if lo > .89 else 0))
                            if mask.any():
                                item["calibration"].append({"low": float(lo), "rows": int(mask.sum()), "predicted": float(p[mask].mean()), "observed": float(y[mask].mean())})
                section["models"].append(item)
                if model != baseline:
                    paired = source.dropna(subset=[target, model, baseline])
                    improvement = losses(task, paired[target], paired[baseline], cfg) - losses(task, paired[target], paired[model], cfg)
                    daily = pd.Series(improvement, index=paired.date).groupby(level=0).mean()
                    section["comparisons"].append({"task": task, "candidate": model, "baseline": baseline,
                        "pairedRows": len(paired), "candidateRows": int(source[model].notna().sum()),
                        "baselineRows": int(source[baseline].notna().sum()), "gain": block_interval(daily, sessions, cfg)})
        result["groups"][group] = section
    return result


def walk_forward(frame, cfg, start=None, end=None):
    start, end = start or cfg["outerStart"], end or cfg["outerEnd"]
    origins = pd.DatetimeIndex(sorted(frame.loc[frame.date.between(start, end), "date"].unique()))
    predictions, audit = [], []
    periods = origins.to_period("M")
    for period in periods.unique():
        dates = origins[periods == period]
        for ticker in cfg["assets"]:
            history = frame[frame.ticker == ticker]
            bundle = fit_asset(history, dates[0], cfg)
            predictions.append(predict_asset(bundle, history, dates, cfg))
            audit.append({"ticker": ticker, "period": str(period), **bundle["metadata"]})
        print(f"Risk benchmark month {period}: {len(dates)} origins", flush=True)
    return pd.concat(predictions, ignore_index=True), audit


def run_research(cfg):
    directory, run = attempt_directory(cfg, "research")
    report = {"experiment": cfg["experiment"], "runId": run, "generatedAt": now(), "status": "running",
              "evidence": cfg["historicalEvidence"], "provenance": provenance(), "errors": [],
              "input": {"path": cfg["historyInput"], "csvSha256": cfg["historyCsvSha256"]}}
    try:
        frame = make_panel(load_history(cfg), cfg)
        predictions, audit = walk_forward(frame, cfg)
        report["predictions"] = save_predictions(directory / "predictions.csv.gz", predictions)
        write(directory / "fit-audit.json", audit, immutable=True)
        report["summary"] = score(predictions, cfg)
        report["failedFitComponents"] = sum(len(a["errors"]) for a in audit)
        report["status"] = "completed"
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        report["archivePath"] = str((directory / "report.json").relative_to(ROOT))
        write(directory / "report.json", report, immutable=True)
        write(ROOT / "site/data/risk_research.json", report)
        (directory / "environment.txt").write_text(subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True))
    return report
