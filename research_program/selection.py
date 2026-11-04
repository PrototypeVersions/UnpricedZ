"""Small nested chronological selection, followed by untouched calibration."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .panel import TARGETS


class InsufficientHistory(ValueError):
    pass


def logit(p):
    p = np.clip(np.asarray(p), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)


def fit_classifier(x, y, strength):
    if len(np.unique(y)) < 2:
        return float((np.sum(y) + 0.5) / (len(y) + 1))
    model = make_pipeline(StandardScaler(), LogisticRegression(C=strength, max_iter=1000))
    model.fit(x, y)
    return model


def probability(model, x):
    return np.full(len(x), model) if isinstance(model, float) else model.predict_proba(x)[:, 1]


def loss(task, y, prediction):
    if task != "variance":
        return (np.asarray(y) - np.asarray(prediction)) ** 2
    ratio = np.clip(np.asarray(y), 1e-10, None) / np.clip(np.asarray(prediction), 1e-10, None)
    return ratio - np.log(ratio) - 1


def date_loss(task, frame, prediction):
    values = loss(task, frame[TARGETS[task]], prediction)
    return pd.Series(values, index=frame.date).groupby(level=0).mean()


def partitions(frame, asof, features, task, registry):
    asof = pd.Timestamp(asof)
    eligible = frame[(frame.date < asof) & (frame.labelEnd <= asof) &
                     (frame.date >= asof - pd.DateOffset(years=registry["trainingYears"]))]
    eligible = eligible.dropna(subset=features + [TARGETS[task]])
    dates = pd.DatetimeIndex(sorted(eligible.date.unique()))
    required = registry["calibrationSessions"] + registry["innerBlocks"] * registry["innerBlockSessions"] + registry["minimumFitDates"] + 15
    if len(dates) < required:
        raise InsufficientHistory("Not enough distinct dates for purged inner selection and calibration")
    cal_start = dates[-registry["calibrationSessions"]]
    train = eligible[eligible.labelEnd < cal_start].copy()
    calibration = eligible[eligible.date >= cal_start].copy()
    train_dates = pd.DatetimeIndex(sorted(train.date.unique()))
    inner_dates = train_dates[-registry["innerBlocks"] * registry["innerBlockSessions"]:]
    folds = []
    for offset in range(0, len(inner_dates), registry["innerBlockSessions"]):
        selected = inner_dates[offset:offset + registry["innerBlockSessions"]]
        inner_train = train[train.labelEnd < selected[0]].copy()
        validation = train[train.date.isin(selected)].copy()
        if inner_train.date.nunique() < registry["minimumFitDates"]:
            raise InsufficientHistory("Inner training window is too short")
        assert inner_train.labelEnd.max() < validation.date.min()
        assert validation.labelEnd.max() < calibration.date.min()
        folds.append((inner_train, validation))
    assert train.labelEnd.max() < calibration.date.min()
    assert calibration.labelEnd.max() <= asof
    return train, calibration, folds


def fit_estimator(frame, features, task, strength):
    if task == "variance":
        estimator = make_pipeline(StandardScaler(), Ridge(alpha=strength))
        target = np.log(frame.realizedVariance.clip(lower=1e-10))
        estimator.fit(frame[features], target)
        smear = float(np.exp(np.clip(target - estimator.predict(frame[features]), -8, 8)).mean())
        return estimator, smear
    return fit_classifier(frame[features], frame[TARGETS[task]].astype(int), strength), None


def point_estimate(estimator, smear, frame, features, task):
    if task == "variance":
        return np.exp(np.clip(estimator.predict(frame[features]), -25, 5)) * smear
    return probability(estimator, frame[features])


def fit_selected(frame, asof, features, task, registry):
    training, calibration, folds = partitions(frame, asof, features, task, registry)
    strengths = registry["varianceAlpha"] if task == "variance" else registry["classificationC"]
    trials = []
    for strength in strengths:
        values = []
        for train, validation in folds:
            estimator, smear = fit_estimator(train, features, task, strength)
            estimates = point_estimate(estimator, smear, validation, features, task)
            values.extend(date_loss(task, validation, estimates).tolist())
        trials.append({"strength": strength, "innerLoss": float(np.mean(values)), "validationDates": len(values)})
    # Predeclared order favors stronger regularization on an exact tie.
    selected = min(trials, key=lambda t: t["innerLoss"])["strength"]
    estimator, smear = fit_estimator(training, features, task, selected)
    calibrator, residual_quantiles = None, None
    if task == "variance":
        residual = np.log(calibration.realizedVariance.clip(lower=1e-10)) - estimator.predict(calibration[features])
        smear = float(np.exp(np.clip(residual, -8, 8)).mean())
        residual_quantiles = np.quantile(residual, registry["pretrained"]["quantiles"])
    else:
        raw = probability(estimator, calibration[features])
        # Preserve the initial lab's sigmoid scaling; do not standardize logits.
        if calibration[TARGETS[task]].nunique() < 2:
            calibrator = float((calibration[TARGETS[task]].sum() + 0.5) / (len(calibration) + 1))
        else:
            calibrator = LogisticRegression(C=registry["calibrationC"], max_iter=1000)
            calibrator.fit(logit(raw), calibration[TARGETS[task]].astype(int))
    metadata = {
        "fitAsOf": str(pd.Timestamp(asof).date()), "selectedStrength": selected, "trials": trials,
        "fitStart": str(training.date.min().date()), "fitLabelEnd": str(training.labelEnd.max().date()),
        "calibrationStart": str(calibration.date.min().date()), "calibrationLastOutcome": str(calibration.labelEnd.max().date()),
        "innerFolds": [{"fitLabelEnd": str(a.labelEnd.max().date()), "validationStart": str(b.date.min().date()),
                        "validationLabelEnd": str(b.labelEnd.max().date())} for a, b in folds]}
    return {"estimator": estimator, "smear": smear, "calibrator": calibrator, "features": features,
            "task": task, "residualQuantiles": residual_quantiles,
            "baseRate": float((pd.concat([training, calibration])[TARGETS[task]].sum() + 0.5) /
                              (len(training) + len(calibration) + 1)) if task != "variance" else None,
            "metadata": metadata}


def predict_selected(bundle, frame):
    task, features = bundle["task"], bundle["features"]
    # Eligibility is determined by present features, never future outcomes.
    rows = frame.dropna(subset=features).copy()
    output = rows[["date", "ticker", "entryDate", "labelEnd", TARGETS[task]]].copy()
    output = output.rename(columns={TARGETS[task]: "outcome"})
    if rows.empty:
        return output.assign(prediction=[], baseline=[])
    raw = point_estimate(bundle["estimator"], bundle["smear"], rows, features, task)
    if task == "variance":
        output["prediction"] = raw
        output["baseline"] = rows.ewmaVariance
        q = np.exp(np.clip(bundle["estimator"].predict(rows[features])[:, None] + bundle["residualQuantiles"], -25, 5))
        for j in range(q.shape[1]):
            output[f"q{j+1}"] = q[:, j]
    else:
        output["prediction"] = probability(bundle["calibrator"], logit(raw))
        output["baseline"] = bundle["baseRate"]
    return output


def walk_forward(frame, features, task, cadence, registry):
    dates = pd.DatetimeIndex(sorted(frame[(frame.date >= registry["outerStart"]) &
                                         (frame.date <= registry["outerEnd"])].date.unique()))
    results, audit = [], []
    periods = dates.to_period(cadence)
    for period in periods.unique():
        selected = dates[periods == period]
        test = frame[frame.date.isin(selected)]
        try:
            bundle = fit_selected(frame, selected[0], features, task, registry)
        except InsufficientHistory as exc:
            audit.append({"period": str(period), "status": "insufficient-history", "reason": str(exc), "expectedRows": len(test)})
            continue
        prediction = predict_selected(bundle, test)
        prediction["fitAsOf"] = selected[0]
        results.append(prediction)
        audit.append({"period": str(period), "status": "completed", "expectedRows": len(test),
                      "forecastRows": len(prediction), **bundle["metadata"]})
    if not results:
        raise InsufficientHistory("No outer fold has sufficient point-in-time training history")
    return pd.concat(results, ignore_index=True), audit
