from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def clean(value):
    """Portable JSON: no NaN, Infinity, numpy scalar, or implicit timestamps."""
    import numpy as np
    import pandas as pd
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    return value


def write(path, value, immutable=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(clean(value), indent=2, allow_nan=False) + "\n"
    if immutable:
        with path.open("x") as stream:
            stream.write(encoded)
    else:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(encoded)
        os.replace(tmp, path)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def config():
    return read(ROOT / "config.json")


def provenance():
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        sha = os.environ.get("GITHUB_SHA", "local-uncommitted")
    packages = {}
    for name in ["numpy", "pandas", "scipy", "scikit-learn", "yfinance", "pandas-market-calendars", "joblib"]:
        try:
            packages[name] = version(name)
        except Exception:
            packages[name] = "unavailable"
    algorithm = hashlib.sha256()
    for path in sorted((ROOT / "unpriced").glob("*.py")) + [ROOT / "requirements.txt"]:
        algorithm.update(path.name.encode())
        algorithm.update(path.read_bytes())
    return {"codeCommit": sha, "configSha256": digest(ROOT / "config.json"), "algorithmSha256": algorithm.hexdigest(),
            "python": platform.python_version(), "packages": packages}
