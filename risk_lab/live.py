from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd

from unpriced.data import download, exchange_schedule, session_context
from research_program.macro import MacroUnavailable, download_vintages, macro_panel
from .core import fit_asset, make_panel, predict_asset
from .evaluate import score
from .storage import ROOT, archive_macro, archive_prices, clean, now, provenance, read, sha256, write


def publication_allowed(context, at):
    at = pd.Timestamp(at)
    if at.tzinfo is None:
        raise ValueError("Publication timestamp must have a timezone")
    return context["close"] + pd.Timedelta(minutes=45) <= at < context["nextOpen"]


def persist_forecast(path, snapshot, context, at):
    if not publication_allowed(context, at):
        raise ValueError("Risk publication is outside its pre-entry window")
    if pd.Timestamp(snapshot["issuedAt"]) != pd.Timestamp(at):
        raise ValueError("Issue timestamp must equal the final publication check")
    payload = json.dumps(clean(snapshot), sort_keys=True, separators=(",", ":")).encode()
    snapshot = {**snapshot, "payloadSha256": sha256(payload)}
    write(path, snapshot, immutable=True)
    return snapshot


def verify_forecast(snapshot):
    payload = {k: v for k, v in snapshot.items() if k != "payloadSha256"}
    if sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()) != snapshot["payloadSha256"]:
        raise ValueError("Risk forecast content hash mismatch")
    if not pd.Timestamp(snapshot["informationCutoff"]) <= pd.Timestamp(snapshot["issuedAt"]) < pd.Timestamp(snapshot["entryOpen"]) < pd.Timestamp(snapshot["exitClose"]):
        raise ValueError("Risk forecast timestamps are inconsistent")


def record_directory(cfg):
    return ROOT / "risk_records" / cfg["experiment"]


def resolve(frame, cfg, vintage):
    lookup = frame.set_index(["date", "ticker"])
    directory = record_directory(cfg)
    for path in sorted((directory / "forecasts").glob("*.json")):
        output = directory / "resolutions" / path.name
        if output.exists():
            continue
        snapshot = read(path)
        verify_forecast(snapshot)
        rows = []
        for forecast in snapshot["forecasts"]:
            key = (pd.Timestamp(snapshot["sessionDate"]), forecast["ticker"])
            if key not in lookup.index:
                break
            actual = lookup.loc[key]
            if not np.isfinite(actual.realizedVariance) or not np.isfinite(actual.drawdownSeverity):
                break
            if str(actual.entryDate.date()) != snapshot["entryDate"] or str(actual.labelEnd.date()) != snapshot["exitDate"]:
                raise ValueError("Risk resolution endpoints differ from the issued target")
            rows.append({"date": snapshot["sessionDate"], "ticker": forecast["ticker"],
                         "entryDate": snapshot["entryDate"], "labelEnd": snapshot["exitDate"],
                         "realizedVariance": actual.realizedVariance, "drawdownSeverity": actual.drawdownSeverity,
                         "drawdownEvent": actual.drawdownEvent, **forecast["variance"], **forecast["drawdown"]})
        if len(rows) == len(snapshot["forecasts"]):
            write(output, {"experiment": cfg["experiment"], "forecastId": snapshot["forecastId"], "resolvedAt": now(),
                           "forecastFileSha256": sha256(path.read_bytes()), "inputVintage": vintage, "rows": rows}, immutable=True)


def refresh_public(cfg):
    directory = record_directory(cfg)
    paths = sorted((directory / "forecasts").glob("*.json"))
    snapshots = [read(p) for p in paths]
    for snapshot in snapshots:
        verify_forecast(snapshot)
        if snapshot["experiment"] != cfg["experiment"]:
            raise ValueError("Different risk versions cannot share a ledger")
    resolutions = {p.stem: read(p) for p in (directory / "resolutions").glob("*.json")}
    rows = [row for resolution in resolutions.values() for row in resolution["rows"]]
    summary = {"forecastDates": 0, "rows": 0, "groups": {}}
    if rows:
        frame = pd.DataFrame(rows)
        for col in ["date", "entryDate", "labelEnd"]:
            frame[col] = pd.to_datetime(frame[col])
        summary = score(frame, cfg)
    report = {"experiment": cfg["experiment"], "status": "live-shadow" if snapshots else "awaiting-first-publication",
              "updatedAt": now(), "forecastDates": len(snapshots), "resolvedDates": len(resolutions),
              "latest": snapshots[-1] if snapshots else None, "summary": summary,
              "history": [{"sessionDate": s["sessionDate"], "issuedAt": s["issuedAt"], "entryOpen": s["entryOpen"],
                           "exitClose": s["exitClose"], "path": str(p.relative_to(ROOT)), "fileSha256": sha256(p.read_bytes()),
                           "resolved": p.stem in resolutions} for s, p in zip(snapshots, paths)]}
    write(ROOT / "site/data/risk.json", report)
    return report


def frozen_models(frame, data, session, cfg):
    month = str(session.to_period("M"))
    path = ROOT / "risk_archive" / cfg["experiment"] / "models" / f"{month}.joblib"
    meta_path = path.with_suffix(".json")
    current = provenance()
    if path.exists():
        metadata = read(meta_path)
        if sha256(path.read_bytes()) != metadata["modelSha256"]:
            raise ValueError("Frozen risk model artifact checksum mismatch")
        for field in ["algorithmSha256", "registrySha256", "packages"]:
            if current[field] != metadata["provenance"][field]:
                raise ValueError(f"Frozen risk {field} changed; use a new registered version")
        return joblib.load(path), metadata
    bundles = {ticker: fit_asset(frame[frame.ticker == ticker], session, cfg) for ticker in cfg["assets"]}
    training = data[data.date >= session - pd.DateOffset(years=cfg["trainingYears"]) - pd.Timedelta(days=40)]
    vintage = archive_prices(training, "training")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        joblib.dump(bundles, stream, compress=3)
    metadata = {"experiment": cfg["experiment"], "fitAsOf": str(session.date()), "path": str(path.relative_to(ROOT)),
                "modelSha256": sha256(path.read_bytes()), "provenance": current, "inputVintage": vintage,
                "assets": {ticker: bundle["metadata"] for ticker, bundle in bundles.items()}}
    write(meta_path, metadata, immutable=True)
    return bundles, metadata


def macro_context(frame, session):
    spec = read(ROOT / "research_program/registry.json")["macro"]
    try:
        payload = download_vintages(spec, str((session - pd.DateOffset(years=2)).date()))
        vintage = archive_macro(payload)
        dates = pd.DatetimeIndex(sorted(frame.date.unique()))
        row = macro_panel(payload, dates, spec).set_index("date").loc[session]
        return {"status": "available" if row.notna().all() else "incomplete", "inputVintage": vintage,
                "features": row.to_dict(), "use": "Dated context only; not a model input in risk-1.0.0",
                "availabilityRule": spec["vintageAvailability"]}
    except MacroUnavailable as exc:
        return {"status": "blocked", "reason": str(exc), "use": "Risk benchmarks use price inputs only"}


def publish(data, frame, cfg, context):
    session = pd.Timestamp(context["session"])
    date = str(session.date())
    directory = record_directory(cfg)
    path = directory / "forecasts" / f"{date}.json"
    pending = [pd.Timestamp(p.stem) for p in (directory / "forecasts").glob("*.json")
               if not (directory / "resolutions" / p.name).exists()]
    first = min([session - pd.Timedelta(days=450)] + pending)
    vintage = archive_prices(data[data.date >= first], "daily")
    resolve(frame, cfg, vintage)
    if path.exists():
        return refresh_public(cfg)
    if not publication_allowed(context, pd.Timestamp.now(tz="UTC")):
        miss = directory / "operations" / f"{date}-missed.json"
        if not miss.exists():
            write(miss, {"at": now(), "sessionDate": date, "reason": "Missed pre-entry publication window; no live backfill"}, immutable=True)
        return refresh_public(cfg)
    bundles, metadata = frozen_models(frame, data, session, cfg)
    rows = []
    for ticker, bundle in bundles.items():
        history = frame[frame.ticker == ticker]
        current = history[history.date == session]
        result = predict_asset(bundle, history, [session], cfg).iloc[0]
        rows.append({"ticker": ticker, "name": cfg["assets"][ticker],
                     "variance": {name: result[name] for name in cfg["varianceModels"]},
                     "drawdown": {name: result[name] for name in cfg["drawdownModels"]},
                     "features": current[[f"logVar{n}" for n in cfg["harLags"]] + cfg["drawdownFeatures"]].iloc[0].to_dict(),
                     "abstentions": {name: bundle["errors"].get("supervised", "Missing required input or failed fit; inspect model metadata")
                                     for name in cfg["varianceModels"] + cfg["drawdownModels"] if not np.isfinite(result[name])}})
    macro = macro_context(frame, session)
    entry, exit_date = context["nextSessions"][0], context["nextSessions"][cfg["horizon"] - 1]
    exit_close = exchange_schedule(exit_date, exit_date).iloc[0].market_close.isoformat()
    issued = now()
    snapshot = {"schemaVersion": 1, "experiment": cfg["experiment"], "forecastId": f"{cfg['experiment']}:{date}",
                "sessionDate": date, "issuedAt": issued, "informationCutoff": context["close"].isoformat(),
                "entryDate": entry, "exitDate": exit_date, "entryOpen": context["nextOpen"].isoformat(), "exitClose": exit_close,
                "horizonSessions": cfg["horizon"], "targets": {"variance": cfg["varianceTarget"], "drawdown": cfg["drawdownTarget"],
                    "drawdownThreshold": cfg["drawdownThreshold"], "varianceUnits": "squared fractional log return per session"},
                "inputVintage": vintage, "models": metadata, "provenance": provenance(), "macroContext": macro, "forecasts": rows}
    persist_forecast(path, snapshot, context, issued)
    return refresh_public(cfg)


def run_daily(cfg):
    context = session_context()
    prices = {"benchmark": "SPY", "universe": {k:v for k,v in cfg["assets"].items() if k != "SPY"},
              "context": [], "historyStart": cfg["historyStart"]}
    data = download(prices, context["session"])
    return publish(data, make_panel(data, cfg), cfg, context)
