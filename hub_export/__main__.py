from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import jsonschema  # Required: never silently bypass the Hub's full schema checks.

from risk_lab.live import verify_forecast
from risk_lab.storage import ROOT, config, read, save_bytes, sha256
from vendor.unpricedhub.hub import core as hub_core

TASK_IDS = {"variance": "risk-v1-variance-5s-open-close", "drawdown": "risk-v1-drawdown-gt3pct-5s-open-close"}


def verify_pinned_contract():
    root = ROOT / "vendor/unpricedhub"
    pin = read(root / "PIN.json")
    for name, expected in pin["files"].items():
        content = (root / name).read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        if actual != expected:
            raise ValueError("Pinned Hub validator or contract was altered")
    hub_core.ROOT = root
    return pin


def build_export(snapshot, snapshot_path, snapshot_bytes, task, cfg):
    verify_forecast(snapshot)
    names = cfg["varianceModels"] if task == "variance" else cfg["drawdownModels"]
    assets = [row["ticker"] for row in snapshot["forecasts"]]
    values = {model: [row[task][model] for row in snapshot["forecasts"]] for model in names}
    for model, forecasts in values.items():
        if any(value is not None and (not math.isfinite(value) or value < 0) for value in forecasts):
            raise ValueError(f"Invalid {task} values for {model}")
    task_id = TASK_IDS[task]
    doc = {"schema": "unpriced-export/1", "lab": {"id": "unpricedz", "name": "UNPRICED Risk Lab",
        "repo": "PrototypeVersions/UnpricedZ", "experiment": snapshot["experiment"], "codeCommit": snapshot["provenance"]["codeCommit"]},
        "forecastId": f"unpricedz/{snapshot['sessionDate']}/{task_id}", "decisionSession": snapshot["sessionDate"],
        "informationCutoff": snapshot["informationCutoff"], "issuedAt": snapshot["issuedAt"],
        "entry": {"session": snapshot["entryDate"], "price": "open"}, "exit": {"session": snapshot["exitDate"], "price": "close"},
        "task": {"id": task_id, "description": snapshot["targets"][task],
            "target": {"quantity": "realized-variance" if task == "variance" else "drawdown", "entryPrice": "open", "exitPrice": "close",
                       "horizonSessions": snapshot["horizonSessions"] - 1, "relativeTo": "none"},
            "forecastType": "variance" if task == "variance" else "event-probability",
            "event": None if task == "variance" else {"operator": ">", "threshold": snapshot["targets"]["drawdownThreshold"]}},
        "universe": {"definition": "SPY plus legacy US sector ETFs XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV and XLY", "size": len(cfg["assets"])},
        "models": [{"id": model, "role": "baseline", "artifactSha256": None if model == "ewma" else snapshot["models"]["modelSha256"],
                    "trainedThrough": None if model == "ewma" else snapshot["models"]["fitAsOf"],
                    "specificationSha256": snapshot["provenance"]["registrySha256"]} for model in names],
        "forecasts": {"assets": assets, "values": values},
        "abstained": [{"asset": row["ticker"], "reason": "All models for this task abstained; see source snapshot"}
                      for row in snapshot["forecasts"] if all(row[task][name] is None for name in names)],
        "modelAbstentions": [{"asset": row["ticker"], "model": name, "reason": row["abstentions"].get(name, "Missing required input or failed fit")}
                             for row in snapshot["forecasts"] for name in names if row[task][name] is None],
        "provenance": {"snapshotPath": snapshot_path, "snapshotSha256": sha256(snapshot_bytes),
                       "inputFingerprint": {"prices": snapshot["inputVintage"]["csvSha256"], "algorithm": snapshot["provenance"]["algorithmSha256"]}},
        "limitations": ["Daily adjusted-price proxy, not intraday realized variance or intraday maximum drawdown.",
                        "Nine retrospectively selected legacy sector funds do not cover every modern sector.",
                        "Risk benchmarks only; no established forecasting edge or trading policy.",
                        "The five-observation holding window has four NYSE session-index intervals under this contract.",
                        "Issue time is when the lab froze the forecast. Hub independently determines whether receipt was timely."],
        "entryOpen": snapshot["entryOpen"], "exitClose": snapshot["exitClose"], "holdingWindowObservations": snapshot["horizonSessions"]}
    return doc


def publish_exports(cfg=None):
    cfg = cfg or config()
    pin = verify_pinned_contract()
    paths = sorted((ROOT / "risk_records" / cfg["experiment"] / "forecasts").glob("*.json"))
    if not paths:
        print("Hub export awaits the first genuine risk forecast; no placeholder published.")
        return []
    path = paths[-1]
    raw = path.read_bytes()
    snapshot = json.loads(raw)
    output = ROOT / "site/data/export"
    output.mkdir(parents=True, exist_ok=True)
    published = []
    for task, identifier in TASK_IDS.items():
        doc = build_export(snapshot, str(path.relative_to(ROOT)), raw, task, cfg)
        doc["contractRevision"] = pin["commit"]
        problems = hub_core.validate(doc)
        if problems:
            raise ValueError("Hub contract validation failed: " + "; ".join(problems))
        payload = (json.dumps(doc, indent=2, allow_nan=False) + "\n").encode()
        dated = output / f"{snapshot['sessionDate']}-{identifier}.json"
        save_bytes(dated, payload)
        latest = output / f"latest-{identifier}.json"
        if latest.exists():
            previous = json.loads(latest.read_bytes())
            if previous["forecastId"] == doc["forecastId"] and latest.read_bytes() != payload:
                raise ValueError("Refusing to change bytes for an existing Hub forecastId")
            if previous["decisionSession"] > doc["decisionSession"]:
                raise ValueError("Refusing to replace a newer export with an older session")
        latest.write_bytes(payload)
        published.append(str(latest.relative_to(ROOT)))
        print(f"Validated with pinned hub/core.py validate(): {identifier}", flush=True)
    return published


if __name__ == "__main__":
    publish_exports()
