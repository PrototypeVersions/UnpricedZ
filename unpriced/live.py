from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .data import archive, exchange_schedule, market_summary
from .evaluation import summarize
from .features import FEATURES, RISK_FEATURES, panel
from .io import ROOT, digest, now, provenance, read, write
from .models import MODEL_NAMES, fit, predict


def publication_allowed(context, at):
    at = pd.Timestamp(at)
    return context["close"] + pd.Timedelta(minutes=45) <= at < context["nextOpen"]


def immutable_snapshot(path, snapshot):
    write(path, snapshot, immutable=True)


def resolve(data, cfg, vintage):
    frame = panel(data, cfg).set_index(["date", "ticker"])
    directory = ROOT / "records/resolutions"
    directory.mkdir(parents=True, exist_ok=True)
    for path in sorted((ROOT / "records/forecasts").glob("*.json")):
        snap = read(path)
        output = directory / path.name
        if output.exists():
            continue
        rows = []
        for forecast in snap["forecasts"]:
            key = (pd.Timestamp(snap["sessionDate"]), forecast["ticker"])
            if key not in frame.index:
                break
            outcome = frame.loc[key]
            if not np.isfinite(outcome.excessReturn) or not np.isfinite(outcome.realizedVariance):
                break
            # Assert exact exchange-session endpoints before recording an outcome.
            if str(outcome.entryDate.date()) != snap["entryDate"] or str(outcome.labelEnd.date()) != snap["exitDate"]:
                raise ValueError("Resolution endpoint mismatch")
            row = {**forecast, "date": snap["sessionDate"], "entryDate": snap["entryDate"],
                   "labelEnd": snap["exitDate"], "outcome": int(outcome.outcome),
                   "assetReturn": outcome.assetReturn, "spyReturn": outcome.spyReturn,
                   "excessReturn": outcome.excessReturn, "realizedVariance": outcome.realizedVariance}
            rows.append(row)
        if len(rows) == len(snap["forecasts"]):
            write(output, {"snapshotId": snap["snapshotId"], "resolvedAt": now(),
                           "inputVintage": vintage, "rows": rows}, immutable=True)


def live_paper(snapshots, resolutions, cfg):
    """Reference-return plans are frozen inside each snapshot; settled from immutable outcomes."""
    initial_plans = [s["portfolioPlan"] for s in snapshots if s.get("portfolioPlan")]
    starting_equity = initial_plans[0]["startingEquity"] if initial_plans else cfg["portfolio"]["startingEquity"]
    equity = benchmark = starting_equity
    curve, plans = [], []
    for snap in snapshots:
        plan = snap.get("portfolioPlan")
        if not plan:
            continue
        resolution = resolutions.get(snap["snapshotId"])
        item = {**plan, "signalDate": snap["sessionDate"], "entryDate": snap["entryDate"], "exitDate": snap["exitDate"], "status": "awaiting-outcome"}
        if resolution:
            outcomes = {x["ticker"]: x for x in resolution["rows"]}
            cost = plan["costPerSide"]
            gain = sum(x["weight"] * ((1 + outcomes[x["ticker"]]["assetReturn"]) * (1 - cost) / (1 + cost) - 1) for x in plan["allocations"])
            equity *= 1 + gain
            benchmark *= 1 + resolution["rows"][0]["spyReturn"]
            item.update(status="resolved", netReturn=gain, equity=equity)
            curve.append({"date": snap["exitDate"], "equity": equity, "benchmark": benchmark})
        plans.append(item)
    return {"status": "prospective-reference-simulation", "startingEquity": starting_equity,
            "settledEquity": equity, "settledBenchmark": benchmark, "curve": curve, "plans": plans,
            "note": "Plans committed before the reference entry open. Only settled cohorts change this equity; it is not a daily mark-to-market value. No broker fills are claimed. SPY comparator holds identical windows."}


def refresh_public(cfg, current=None, market=None):
    snapshots = [read(p) for p in sorted((ROOT / "records/forecasts").glob("*.json"))]
    if any(s["experiment"] != cfg["experiment"] for s in snapshots):
        raise ValueError("Different experiment versions cannot share a live ledger")
    resolutions = {r["snapshotId"]: r for r in [read(p) for p in sorted((ROOT / "records/resolutions").glob("*.json"))]}
    rows = [x for r in resolutions.values() for x in r["rows"]]
    if rows:
        frame = pd.DataFrame(rows)
        for col in ["date", "entryDate", "labelEnd"]:
            frame[col] = pd.to_datetime(frame[col])
        score = summarize(frame, cfg)
    else:
        score = {"dates": 0, "observations": 0, "models": [], "risk": [], "daily": []}
    report = {"status": "live-shadow" if snapshots else "awaiting-first-publication", "updatedAt": now(),
              "forecastDates": len(snapshots), "forecastObservations": sum(len(s["forecasts"]) for s in snapshots),
              "latest": snapshots[-1] if snapshots else None, "summary": score,
              "portfolio": live_paper(snapshots, resolutions, cfg),
              "history": [{"sessionDate": s["sessionDate"], "publishedAt": s["publishedAt"], "snapshotId": s["snapshotId"],
                           "path": f"records/forecasts/{s['sessionDate']}.json", "resolved": s["snapshotId"] in resolutions} for s in snapshots]}
    write(ROOT / "site/data/live.json", report)
    if market:
        write(ROOT / "site/data/market.json", market)
    return report


def publish(data, cfg, context):
    session = pd.Timestamp(context["session"])
    date = str(session.date())
    snapshot_path = ROOT / f"records/forecasts/{date}.json"
    # Resolve with a small complete input vintage even when the publication window was missed.
    unresolved_starts = [pd.Timestamp(read(p)["sessionDate"]) for p in (ROOT / "records/forecasts").glob("*.json")
                         if not (ROOT / "records/resolutions" / p.name).exists()]
    recent_start = min([session - pd.Timedelta(days=230)] + unresolved_starts)
    recent = data[data.date >= recent_start]
    vintage = archive(recent, "daily")
    resolve(data, cfg, vintage)
    if snapshot_path.exists():
        return refresh_public(cfg, market=market_summary(data, cfg))
    if not publication_allowed(context, pd.Timestamp.now(tz="UTC")):
        miss = ROOT / f"records/operations/{date}-missed.json"
        if not miss.exists():
            write(miss, {"at": now(), "sessionDate": date, "reason": "Publication would be after the target entry open; no forecast backfill."}, immutable=True)
        return refresh_public(cfg, market=market_summary(data, cfg))
    features = panel(data, cfg)
    quarter = str(session.to_period("Q"))
    model_path = ROOT / f"archive/models/{quarter}.joblib"
    meta_path = model_path.with_suffix(".json")
    if model_path.exists():
        model_info = read(meta_path)
        current_provenance = provenance()
        if digest(model_path) != model_info["modelSha256"]:
            raise ValueError("Frozen model artifact checksum mismatch")
        for field in ["configSha256", "algorithmSha256", "packages"]:
            if model_info[field] != current_provenance[field]:
                raise ValueError(f"{field} changed within a frozen model quarter; create an explicitly versioned transition")
        bundle = joblib.load(model_path)
    else:
        bundle = fit(features, session, cfg)
        full_vintage = archive(data, "training")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(bundle, model_path, compress=3)
        model_info = {**provenance(), "training": bundle["metadata"], "inputVintage": full_vintage,
                      "path": str(model_path.relative_to(ROOT)), "modelSha256": digest(model_path)}
        write(meta_path, model_info, immutable=True)
    current = features[features.date == session]
    prediction = predict(bundle, current)
    if set(prediction.ticker) != set(cfg["universe"]):
        raise ValueError("Incomplete current feature coverage; refusing a partial official forecast")
    intended = context["nextSessions"]
    entry_date, exit_date = intended[0], intended[cfg["horizon"] - 1]
    forecast_rows = []
    for row in prediction.to_dict("records"):
        item = {k: v for k, v in row.items() if k not in ["date", "entryDate", "labelEnd", "outcome", "assetReturn", "spyReturn", "excessReturn", "realizedVariance"]}
        item["name"] = cfg["universe"][item["ticker"]]
        forecast_rows.append(item)
    previous = [read(p) for p in sorted((ROOT / "records/forecasts").glob("*.json"))]
    active_until = max([s["exitDate"] for s in previous if s.get("portfolioPlan")], default="1900-01-01")
    plan = None
    if date >= active_until:
        rules = cfg["portfolio"]
        eligible = sorted([f for f in forecast_rows if f["p_logistic"] >= rules["minimumProbability"] and f["expectedExcess"] > rules["minimumExpectedExcess"]], key=lambda f: -f["expectedExcess"])[:rules["maxPositions"]]
        plan = {"allocations": [{"ticker": f["ticker"], "weight": rules["maxWeight"]} for f in eligible],
                "cashWeight": 1 - len(eligible) * rules["maxWeight"], "ruleVersion": cfg["experiment"],
                "startingEquity": rules["startingEquity"], "costPerSide": rules["costPerSide"]}
    published = now()
    if not publication_allowed(context, pd.Timestamp(published)):
        raise ValueError("Entry opened during fitting; refusing late publication")
    snapshot = {"schemaVersion": 1, "experiment": cfg["experiment"], "snapshotId": f"{date}-{cfg['experiment']}",
                "sessionDate": date, "publishedAt": published, "informationCutoff": context["close"].isoformat(),
                "entryDate": entry_date, "exitDate": exit_date, "entryOpen": context["nextOpen"].isoformat(),
                "horizon": cfg["horizon"], "target": "Next session adjusted open to fifth session adjusted close, relative to SPY",
                "inputVintage": vintage, "model": model_info, "provenance": provenance(), "portfolioPlan": plan,
                "features": current[["ticker"] + FEATURES + RISK_FEATURES].to_dict("records"), "forecasts": forecast_rows}
    immutable_snapshot(snapshot_path, snapshot)
    return refresh_public(cfg, current=snapshot, market=market_summary(data, cfg))
