"""Build disposable display context from immutable records; never fit or score models."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def build(root: Path, now=None, calendar=None):
    now = now or datetime.now(timezone.utc)
    report = read(root / "site/data/risk.json")
    latest = report.get("latest") or {}
    start = (now - timedelta(days=90)).date().isoformat()
    end = (now + timedelta(days=45)).date().isoformat()
    if calendar is None:
        import pandas_market_calendars as mcal
        schedule = mcal.get_calendar("NYSE").schedule(start_date=start, end_date=end)
        calendar = [{"date": str(day.date()), "open": row.market_open.isoformat(),
                     "close": row.market_close.isoformat()} for day, row in schedule.iterrows()]
    history = []
    for entry in report.get("history", [])[-60:]:
        relative = Path(entry["path"])
        expected = Path("risk_records") / report["experiment"] / "forecasts"
        if relative.parent != expected or relative.name != entry["sessionDate"] + ".json":
            raise ValueError("Unexpected forecast path in public history")
        path = root / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["fileSha256"]:
            raise ValueError("Frozen forecast file differs from public hash")
        snap = read(path)
        item = {key: snap[key] for key in ["sessionDate", "issuedAt", "entryDate", "exitDate", "forecasts"]}
        item["path"] = entry["path"]
        resolution = path.parent.parent / "resolutions" / path.name
        if entry["resolved"]:
            resolved = read(resolution)
            if resolved["forecastFileSha256"] != entry["fileSha256"] or resolved["forecastId"] != snap["forecastId"]:
                raise ValueError("Resolution references a different frozen forecast")
            item["outcomes"] = [{k: row[k] for k in ["ticker", "realizedVariance", "drawdownSeverity", "drawdownEvent"]}
                                for row in resolved["rows"]]
        history.append(item)
    return {"schemaVersion": 1, "builtAt": now.isoformat(), "forecastId": latest.get("forecastId"),
            "riskUpdatedAt": report.get("updatedAt"), "history": history,
            "calendar": {"source": "pandas-market-calendars NYSE", "validFrom": start + "T00:00:00Z",
                         "validUntil": end + "T00:00:00Z", "sessions": calendar}}


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    output = root / "site/data/presentation.json"
    output.write_text(json.dumps(build(root), separators=(",", ":"), allow_nan=False) + "\n")
    print("Built calendar and recent forecast display context; research records unchanged.")
