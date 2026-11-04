from __future__ import annotations

import gzip
import hashlib
import json
import os
import platform
import subprocess
from importlib.metadata import version

import pandas as pd

from unpriced.io import ROOT, clean, now, read, write


def config():
    return read(ROOT / "risk_lab/registry.json")


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def provenance():
    files = [p for p in sorted((ROOT / "risk_lab").glob("*.py")) if not p.name.startswith("test_")]
    files += [ROOT / p for p in ["risk_lab/registry.json", "risk_lab/requirements.txt", "requirements.txt",
              "unpriced/data.py", "unpriced/io.py", "research_program/macro.py", "research_program/reporting.py", "analysis/variance_decomposition.py"]]
    content = hashlib.sha256()
    for path in files:
        content.update(str(path.relative_to(ROOT)).encode())
        content.update(path.read_bytes())
    packages = {}
    for package in ["numpy", "pandas", "scipy", "scikit-learn", "arch", "statsmodels", "joblib", "yfinance", "pandas-market-calendars"]:
        try:
            packages[package] = version(package)
        except Exception:
            packages[package] = "unavailable"
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        commit = os.environ.get("GITHUB_SHA", "local-uncommitted")
    return {"codeCommit": commit, "algorithmSha256": content.hexdigest(),
            "registrySha256": sha256((ROOT / "risk_lab/registry.json").read_bytes()),
            "python": platform.python_version(), "packages": packages}


def save_bytes(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("Immutable archive already exists with different content")
    else:
        with path.open("xb") as stream:
            stream.write(payload)


def archive_prices(data, kind):
    frame = data.sort_values(["date", "ticker"]).copy()
    frame["date"] = frame.date.dt.strftime("%Y-%m-%d")
    payload = frame.to_csv(index=False, float_format="%.17g").encode()
    digest = sha256(payload)
    path = ROOT / "risk_archive/inputs" / f"{kind}-{digest[:16]}.csv.gz"
    save_bytes(path, gzip.compress(payload, mtime=0))
    return {"path": str(path.relative_to(ROOT)), "csvSha256": digest, "retrievedAt": now(),
            "start": frame.date.min(), "end": frame.date.max(), "rows": len(frame),
            "adjustment": "Provider-adjusted OHLC; outcomes use a single vintage"}


def archive_macro(payload):
    encoded = json.dumps(clean(payload), sort_keys=True).encode()
    digest = sha256(encoded)
    path = ROOT / "risk_archive/inputs" / f"macro-{digest[:16]}.json.gz"
    save_bytes(path, gzip.compress(encoded, mtime=0))
    return {"path": str(path.relative_to(ROOT)), "jsonSha256": digest, "retrievedAt": payload["retrievedAt"]}


def load_history(cfg):
    from io import BytesIO
    payload = gzip.decompress((ROOT / cfg["historyInput"]).read_bytes())
    if sha256(payload) != cfg["historyCsvSha256"]:
        raise ValueError("Registered historical price input hash mismatch")
    return pd.read_csv(BytesIO(payload), parse_dates=["date"], float_precision="round_trip")


def attempt_directory(cfg, mode):
    run = os.environ.get("GITHUB_RUN_ID", now().replace(":", "").replace("+", "_")) + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    path = ROOT / "risk_archive" / cfg["experiment"] / mode / run
    path.mkdir(parents=True, exist_ok=False)
    write(path / "attempt.json", {"startedAt": now(), "mode": mode, "registry": cfg, "provenance": provenance()}, immutable=True)
    return path, run


def save_predictions(path, frame):
    payload = frame.to_csv(index=False, float_format="%.17g").encode()
    save_bytes(path, gzip.compress(payload, mtime=0))
    return {"path": str(path.relative_to(ROOT)), "csvSha256": sha256(payload), "rows": len(frame)}
