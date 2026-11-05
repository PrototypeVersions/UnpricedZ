"""Export frozen 2019–2024 walk-forward variance forecasts without refitting.

These are retrospective research forecasts, not contemporaneously issued live signals.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = Path("risk_archive/risk-1.0.0/research/41762675368-1/report.json")
OUTPUT = Path("site/data/export/risk-v1-variance-oos-2019-2024.csv")
FIELDS = ("date", "ticker", "fitAsOf", "entryDate", "labelEnd", "ewma", "har_daily", "garch11")


def build_export(root: Path = ROOT, report_path: Path = REPORT) -> bytes:
    report = json.loads((root / report_path).read_text())
    if report.get("experiment") != "risk-1.0.0" or report.get("status") != "completed":
        raise ValueError("Expected the completed registered risk-1.0.0 research report")
    registry = json.loads((root / "risk_lab/registry.json").read_text())
    if report["input"]["csvSha256"] != registry["historyCsvSha256"]:
        raise ValueError("Registered historical input hash differs from source report")
    source = report["predictions"]
    raw = gzip.decompress((root / source["path"]).read_bytes())
    if hashlib.sha256(raw).hexdigest() != source["csvSha256"]:
        raise ValueError("Archived historical predictions checksum mismatch")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    if reader.fieldnames is None or not set(FIELDS).issubset(reader.fieldnames):
        raise ValueError("Original forecast archive is missing required fields")
    rows = list(reader)
    if len(rows) != source["rows"] or len(rows) != report["summary"]["rows"]:
        raise ValueError("Archived row count differs from registered report")
    allowed = set(registry["assets"])
    covered = defaultdict(set)
    values = []
    for row in rows:
        origin = date.fromisoformat(row["date"])
        fitted = date.fromisoformat(row["fitAsOf"])
        entry = date.fromisoformat(row["entryDate"])
        exit_date = date.fromisoformat(row["labelEnd"])
        if not date(2019, 1, 1) <= origin <= date(2024, 12, 31):
            raise ValueError("Forecast origin outside registered research years")
        if fitted > origin or not (origin < entry <= exit_date):
            raise ValueError("Invalid historical model cutoff or forecast window")
        ticker = row["ticker"]
        if ticker not in allowed or ticker in covered[row["date"]]:
            raise ValueError("Repeated or unexpected historical asset")
        covered[row["date"]].add(ticker)
        for model in ("ewma", "har_daily", "garch11"):
            if row[model]:
                x = float(row[model])
                if not math.isfinite(x) or x < 0:
                    raise ValueError("Invalid historical variance estimate")
        values.append({field: row[field] for field in FIELDS})
    if len(covered) != report["summary"]["forecastDates"]:
        raise ValueError("Historical origin-date count differs from registered report")
    if any(tickers != allowed for tickers in covered.values()):
        raise ValueError("Missing assets in a historical origin-date")
    dest = io.StringIO(newline="")
    writer = csv.DictWriter(dest, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(sorted(values, key=lambda row: (row["date"], row["ticker"])))
    return dest.getvalue().encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify existing export, write nothing")
    args = parser.parse_args()
    result = build_export()
    path = ROOT / OUTPUT
    if path.exists():
        if path.read_bytes() != result:
            raise ValueError("Existing historical export differs; refusing to overwrite")
        print(f"Verified existing historical CSV: {OUTPUT}")
    elif args.check:
        raise FileNotFoundError(f"Expected derived export: {OUTPUT}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as f:
            f.write(result)
        print(f"Created retrospective historical CSV: {OUTPUT}")
    print(f"sha256={hashlib.sha256(result).hexdigest()}; bytes={len(result)}")


if __name__ == "__main__":
    main()
