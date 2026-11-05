"""Offline tests for the retrospective variance CSV exporter."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

import pytest

from site_tools.export_risk_history import build_export


def prepare(tmp_path):
    (tmp_path / "risk_lab").mkdir()
    (tmp_path / "risk_lab/registry.json").write_text(json.dumps({
        "assets": {"SPY": "Market", "XLE": "Energy"},
        "historyCsvSha256": "test-input"
    }))
    rows = []
    for day, entry, exit_date in [
        ("2019-01-02", "2019-01-03", "2019-01-10"),
        ("2019-01-03", "2019-01-04", "2019-01-11")
    ]:
        for ticker in ("SPY", "XLE"):
            rows.append({"date": day, "ticker": ticker, "fitAsOf": "2019-01-02",
                         "entryDate": entry, "labelEnd": exit_date,
                         "ewma": "0.0001", "har_daily": "0.0002", "garch11": "0.0003",
                         "realizedVariance": "999", "drawdownSeverity": "0.1"})
    def save(rows):
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        raw = buf.getvalue().encode()
        (tmp_path / "source.csv.gz").write_bytes(gzip.compress(raw, mtime=0))
        return hashlib.sha256(raw).hexdigest()
    report = {"experiment": "risk-1.0.0", "status": "completed",
              "input": {"csvSha256": "test-input"},
              "predictions": {"path": "source.csv.gz", "csvSha256": save(rows), "rows": 4},
              "summary": {"rows": 4, "forecastDates": 2}}
    (tmp_path / "report.json").write_text(json.dumps(report))
    return rows, save, report


def test_export_deterministic_and_has_no_future_outcomes(tmp_path):
    prepare(tmp_path)
    one = build_export(tmp_path, Path("report.json"))
    assert one == build_export(tmp_path, Path("report.json"))
    result = list(csv.DictReader(io.StringIO(one.decode())))
    assert len(result) == 4
    assert result[0]["ticker"] == "SPY"
    assert result[-1]["ticker"] == "XLE"
    assert result[0]["garch11"] == "0.0003"
    assert "realizedVariance" not in result[0]
    assert "drawdownSeverity" not in result[0]
    assert "issuedAt" not in result[0]


def test_export_rejects_checksum_mismatch(tmp_path):
    rows, save, report = prepare(tmp_path)
    rows[0]["ewma"] = "0.4"
    save(rows)
    with pytest.raises(ValueError, match="checksum"):
        build_export(tmp_path, Path("report.json"))


def test_export_rejects_missing_asset(tmp_path):
    rows, save, report = prepare(tmp_path)
    report["predictions"]["rows"] = 3
    report["summary"]["rows"] = 3
    report["predictions"]["csvSha256"] = save(rows[:-1])
    (tmp_path / "report.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="Missing assets"):
        build_export(tmp_path, Path("report.json"))
