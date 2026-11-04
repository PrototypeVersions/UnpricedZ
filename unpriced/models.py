from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURES, RISK_FEATURES, split_training

MODEL_NAMES = {"coin_flip": "Constant 50%", "base_rate": "Historical base rate", "momentum": "Momentum baseline",
               "raw_logistic": "Logistic before calibration",
               "logistic": "Regularized logistic", "boosted": "Boosted challenger"}


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)


def fit(frame, asof, cfg, include_boosted=True):
    training, calibration = split_training(frame, asof, cfg)
    models = {
        "momentum": (make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500)), ["rel5", "rel20", "rel60"]),
        "logistic": (make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500)), FEATURES)
    }
    if include_boosted:
        models["boosted"] = (HistGradientBoostingClassifier(max_iter=60, max_leaf_nodes=7,
            min_samples_leaf=100, learning_rate=0.04, l2_regularization=10,
            early_stopping=False, random_state=cfg["modelSeed"]), FEATURES)
    fitted = {}
    for name, (estimator, features) in models.items():
        estimator.fit(training[features], training.outcome.astype(int))
        raw = estimator.predict_proba(calibration[features])[:, 1]
        calibrator = LogisticRegression(C=0.2, max_iter=400)
        calibrator.fit(logit(raw), calibration.outcome.astype(int))
        fitted[name] = {"estimator": estimator, "features": features, "calibrator": calibrator}
    regressor = make_pipeline(StandardScaler(), Ridge(alpha=100))
    regressor.fit(training[FEATURES], training.excessReturn)
    residual = calibration.excessReturn.to_numpy() - regressor.predict(calibration[FEATURES])
    # Empirical residual band; no exchangeability/conditional-coverage guarantee is claimed.
    band = np.quantile(residual, [0.1, 0.9])
    risk = make_pipeline(StandardScaler(), Ridge(alpha=100))
    risk.fit(training[RISK_FEATURES], np.log(training.realizedVariance.clip(lower=1e-10)))
    risk_residual = np.log(calibration.realizedVariance.clip(lower=1e-10)) - risk.predict(calibration[RISK_FEATURES])
    # Smearing correction estimates the arithmetic variance mean from a log model.
    smear = float(np.exp(np.clip(risk_residual, -8, 8)).mean())
    return {"models": fitted, "regressor": regressor, "band": band, "risk": risk,
            "smear": smear, "baseRate": float(pd.concat([training, calibration]).outcome.mean()),
            "metadata": {"asOf": str(pd.Timestamp(asof).date()),
                         "fitStart": str(training.date.min().date()), "fitEnd": str(training.date.max().date()),
                         "fitLabelEnd": str(training.labelEnd.max().date()),
                         "calibrationStart": str(calibration.date.min().date()),
                         "calibrationEnd": str(calibration.date.max().date()),
                         "lastKnownOutcome": str(calibration.labelEnd.max().date()),
                         "fitDates": training.date.nunique(), "calibrationDates": calibration.date.nunique(),
                         "fitRows": len(training), "refitPolicy": cfg["refitPolicy"],
                         "weighting": "Separate models; no adaptive ensemble or automatic promotion"}}


def predict(bundle, frame):
    rows = frame.dropna(subset=FEATURES + RISK_FEATURES + ["ewmaVariance"]).copy()
    if rows.empty:
        raise ValueError("No complete feature rows available")
    out = rows[["date", "ticker", "entryDate", "labelEnd", "outcome", "assetReturn", "spyReturn", "excessReturn", "realizedVariance", "ewmaVariance"]].copy()
    out["p_base_rate"] = bundle["baseRate"]
    out["p_coin_flip"] = 0.5
    for name, model in bundle["models"].items():
        raw = model["estimator"].predict_proba(rows[model["features"]])[:, 1]
        if name == "logistic":
            out["p_raw_logistic"] = raw
        out[f"p_{name}"] = model["calibrator"].predict_proba(logit(raw))[:, 1]
    out["expectedExcess"] = bundle["regressor"].predict(rows[FEATURES])
    out["lower80"] = out.expectedExcess + bundle["band"][0]
    out["upper80"] = out.expectedExcess + bundle["band"][1]
    out["harVariance"] = np.exp(np.clip(bundle["risk"].predict(rows[RISK_FEATURES]), -20, 0)) * bundle["smear"]
    return out
