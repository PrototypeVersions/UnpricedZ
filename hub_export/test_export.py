import copy
import json
import shutil

import pytest

pytest.importorskip("jsonschema")
from hub_export import __main__ as exporter
from risk_lab.live import persist_forecast
from risk_lab.storage import config, sha256
from unpriced.data import session_context


def fixture_snapshot(tmp_path):
    cfg = config()
    context = session_context("2026-11-04T01:00:00Z")
    snapshot = {"experiment": cfg["experiment"], "sessionDate": "2026-11-03", "informationCutoff": "2026-11-03T21:00:00Z",
        "issuedAt": "2026-11-04T01:00:00Z", "entryDate": "2026-11-04", "exitDate": "2026-11-10",
        "entryOpen": "2026-11-04T14:30:00Z", "exitClose": "2026-11-10T21:00:00Z", "horizonSessions": 5,
        "targets": {"variance": cfg["varianceTarget"], "drawdown": cfg["drawdownTarget"], "drawdownThreshold": .03},
        "provenance": {"codeCommit": "a" * 40, "algorithmSha256": "b" * 64, "registrySha256": "c" * 64},
        "models": {"modelSha256": "d" * 64, "fitAsOf": "2026-11-03"}, "inputVintage": {"csvSha256": "e" * 64},
        "forecasts": [{"ticker": ticker, "variance": {"ewma": .0001, "har_daily": .0002, "garch11": None},
                       "drawdown": {"base_rate": .12, "volatility_only": .14}, "abstentions": {"garch11": "test nonconvergence"}}
                      for ticker in cfg["assets"]]}
    path = tmp_path / "risk_records" / cfg["experiment"] / "forecasts/2026-11-03.json"
    persist_forecast(path, snapshot, context, snapshot["issuedAt"])
    return cfg, path, json.loads(path.read_bytes())


def test_exports_validate_without_changing_forecasts_or_holding_window(tmp_path):
    cfg, path, snapshot = fixture_snapshot(tmp_path)
    exporter.verify_pinned_contract()
    for task in exporter.TASK_IDS:
        doc = exporter.build_export(snapshot, str(path), path.read_bytes(), task, cfg)
        assert exporter.hub_core.validate(doc) == []
        assert doc["task"]["target"]["horizonSessions"] == 4
        assert doc["holdingWindowObservations"] == 5
        assert doc["provenance"]["snapshotSha256"] == sha256(path.read_bytes())
        assert doc["issuedAt"] == snapshot["issuedAt"]
        for model, values in doc["forecasts"]["values"].items():
            assert values == [row[task][model] for row in snapshot["forecasts"]]
        changed = copy.deepcopy(doc)
        changed["task"]["target"]["horizonSessions"] = 5
        assert any("exit is 4 sessions" in error for error in exporter.hub_core.validate(changed))
    assert len(exporter.build_export(snapshot, str(path), path.read_bytes(), "variance", cfg)["modelAbstentions"]) == 10
    doc = exporter.build_export(snapshot, str(path), path.read_bytes(), "drawdown", cfg)
    doc["forecasts"]["values"]["base_rate"][0] = 1.1
    assert any("outside [0, 1]" in error for error in exporter.hub_core.validate(doc))


def test_export_republication_is_byte_stable_and_rejects_same_id_rewrite(tmp_path, monkeypatch):
    cfg, path, snapshot = fixture_snapshot(tmp_path)
    shutil.copytree(exporter.ROOT / "vendor", tmp_path / "vendor")
    monkeypatch.setattr(exporter, "ROOT", tmp_path)
    paths = exporter.publish_exports(cfg)
    before = [(tmp_path / name).read_bytes() for name in paths]
    exporter.publish_exports(cfg)
    assert before == [(tmp_path / name).read_bytes() for name in paths]
    raw = json.loads((tmp_path / paths[0]).read_bytes())
    raw["limitations"].append("unauthorized alteration")
    (tmp_path / paths[0]).write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="existing Hub forecastId"):
        exporter.publish_exports(cfg)
