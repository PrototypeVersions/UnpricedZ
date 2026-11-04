from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from unpriced.io import ROOT, clean, config, write

from .macro import MacroUnavailable, download_vintages, macro_panel
from .panel import columns, make_panel
from .reporting import paired, summary
from .selection import InsufficientHistory, walk_forward


def digest(value):
    return hashlib.sha256(value).hexdigest()


def load_input(registry):
    compressed = (ROOT / registry["historyInput"]).read_bytes()
    csv = gzip.decompress(compressed)
    if digest(csv) != registry["historyCsvSha256"]:
        raise ValueError("Pinned input archive hash does not match registry")
    from io import BytesIO
    return pd.read_csv(BytesIO(csv), parse_dates=["date"])


def save_csv(path, frame):
    csv = frame.to_csv(index=False, float_format="%.17g").encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(csv, mtime=0))
    return {"path": str(path.relative_to(ROOT)), "csvSha256": digest(csv), "rows": len(frame)}


def execute(include_pretrained=False):
    registry_path = ROOT / "research_program/registry.json"
    registry = json.loads(registry_path.read_text())
    cfg = config()
    now = datetime.now(timezone.utc)
    run_id = os.environ.get("GITHUB_RUN_ID", now.strftime("%Y%m%dT%H%M%S%fZ")) + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    output = ROOT / "archive/program" / registry["program"] / run_id
    output.mkdir(parents=True, exist_ok=False)
    report = {"program": registry["program"], "runId": run_id, "generatedAt": now.isoformat(),
              "evidence": registry["historicalEvidence"], "registrySha256": digest(registry_path.read_bytes()),
              "codeCommit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "input": {"path": registry["historyInput"], "csvSha256": registry["historyCsvSha256"]},
              "status": "running", "tasks": {}, "comparisons": {}, "errors": [],
              "pretrained": {"status": "not-requested"}, "macro": {"status": "pending"},
              "interpretation": "Exploratory only; all attempts retained. No live forecasts or automatic selection/promotion."}
    write(output / "attempt.json", {"runId": run_id, "startedAt": now.isoformat(),
          "codeCommit": report["codeCommit"], "registrySha256": report["registrySha256"],
          "registry": registry, "includePretrained": include_pretrained}, immutable=True)
    audit, predictions = {}, {}
    try:
        data = load_input(registry)
        frame = make_panel(data, cfg, registry)
        sessions = pd.DatetimeIndex(sorted(frame.date.unique()))
        evaluation_sessions = sessions[(sessions >= registry["outerStart"]) & (sessions <= registry["outerEnd"])]
        expected = frame.date.between(registry["outerStart"], registry["outerEnd"]).sum()
        try:
            vintages = download_vintages(registry["macro"])
            encoded = json.dumps(vintages, sort_keys=True).encode()
            with (output / "macro-vintages.json.gz").open("xb") as stream:
                stream.write(gzip.compress(encoded, mtime=0))
            macro = macro_panel(vintages, sessions, registry["macro"])
            frame = make_panel(data, cfg, registry, macro)
            report["macro"] = {"status": "available", "jsonSha256": digest(encoded),
                               "inputPath": str((output / "macro-vintages.json.gz").relative_to(ROOT)),
                               "availabilityRule": registry["macro"]["vintageAvailability"],
                               "completeDates": int(macro.dropna().date.nunique())}
        except MacroUnavailable as exc:
            report["macro"] = {"status": "blocked", "reason": str(exc)}
            print(str(exc), flush=True)
        for feature_set in registry["featureSets"]:
            for cadence in registry["cadences"]:
                for task in registry["tasks"]:
                    identifier = f"{feature_set}-{cadence}-{task}"
                    if feature_set == "macro" and report["macro"]["status"] != "available":
                        report["tasks"][identifier] = {"status": "blocked-macro-data", "expectedRows": int(expected)}
                        continue
                    try:
                        result, folds = walk_forward(frame, columns(task, feature_set, cfg, registry), task, cadence, registry)
                    except InsufficientHistory as exc:
                        report["tasks"][identifier] = {"status": "insufficient-history", "reason": str(exc), "expectedRows": int(expected)}
                        continue
                    predictions[identifier], audit[identifier] = result, folds
                    report["tasks"][identifier] = {"status": "completed", "expectedRows": int(expected),
                                                  **summary(result, task, evaluation_sessions, registry),
                                                  "archive": save_csv(output / f"{identifier}.csv.gz", result)}
                    write(output / "selection-progress.json", audit)
                    print(f"Completed {identifier}: {len(result)} forecasts", flush=True)
        for task in registry["tasks"]:
            pairs = [(f"market-M-{task}", f"market-Q-{task}")]
            pairs += [(f"macro-{c}-{task}", f"market-{c}-{task}") for c in registry["cadences"]]
            for a, b in pairs:
                if a in predictions and b in predictions:
                    report["comparisons"][f"{a} versus {b}"] = paired(predictions[a], predictions[b], task, evaluation_sessions, registry)
        if include_pretrained:
            from .pretrained import historical_screen
            report["pretrained"] = {"status": "running", **registry["pretrained"]}
            chronos, skipped = historical_screen(frame, cfg, registry)
            audit["chronos-skipped"] = skipped
            for task in registry["tasks"]:
                candidate = chronos[chronos.task == task].copy()
                baseline = predictions.get(f"market-M-{task}")
                if baseline is None:
                    report["tasks"][f"chronos-{task}"] = {"status": "missing-matched-baseline"}
                    continue
                candidate = candidate.merge(baseline[["date", "ticker", "baseline"]], on=["date", "ticker"], how="left", validate="one_to_one")
                report["tasks"][f"chronos-{task}"] = {"status": "completed-exploratory-pretraining-overlap-unknown",
                    **summary(candidate, task, evaluation_sessions, registry),
                    "archive": save_csv(output / f"chronos-{task}.csv.gz", candidate)}
                report["comparisons"][f"chronos-{task} versus market-M-{task}"] = paired(candidate, baseline, task, evaluation_sessions, registry)
            report["pretrained"]["status"] = "completed-exploratory-pretraining-overlap-unknown"
        report["status"] = "completed-with-blocked-macro" if report["macro"]["status"] == "blocked" else "completed"
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append({"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        write(output / "selection-audit.json", audit, immutable=True)
        try:
            environment = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
        except subprocess.SubprocessError:
            environment = "Unable to record pip freeze; see workflow installation log.\n"
        (output / "environment.txt").write_text(environment)
        report["auditPath"] = str((output / "selection-audit.json").relative_to(ROOT))
        report["archivePath"] = str((output / "report.json").relative_to(ROOT))
        write(output / "report.json", report, immutable=True)
        write(ROOT / "site/data/program.json", report)
        print(json.dumps(clean({"status": report["status"], "macro": report["macro"]["status"], "archive": report["archivePath"]})), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the registered, isolated development program")
    parser.add_argument("--pretrained", action="store_true", help="Include pinned Chronos CPU inference on monthly origins")
    args = parser.parse_args()
    execute(args.pretrained)
