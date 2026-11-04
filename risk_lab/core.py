from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from unpriced.data import exchange_schedule


def strict_ewma(values, alpha, minimum):
    state, count, output = np.nan, 0, []
    for value in values:
        if not np.isfinite(value):
            state, count = np.nan, 0
        else:
            state = value if count == 0 else alpha * value + (1 - alpha) * state
            count += 1
        output.append(state if count >= minimum else np.nan)
    return np.asarray(output)


def make_panel(data, cfg):
    """Keep the exchange clock, including future endpoint slots and missing bars."""
    start, end = data.date.min(), data.date.max()
    sessions = exchange_schedule(start.date(), (end + pd.Timedelta(days=25)).date()).index
    close = data.pivot(index="date", columns="ticker", values="close").reindex(sessions)
    opens = data.pivot(index="date", columns="ticker", values="open").reindex(sessions)
    dates = pd.Series(sessions, index=sessions)
    horizon, floor = cfg["horizon"], cfg["varianceFloor"]
    output = []
    for ticker in cfg["assets"]:
        c, o = close[ticker], opens[ticker]
        cc, intraday = np.log(c / c.shift(1)), np.log(c / o)
        f = pd.DataFrame({"date": sessions, "ticker": ticker, "closeReturn": cc.to_numpy(),
                          "intradayReturn": intraday.to_numpy()}, index=sessions)
        for lag in cfg["harLags"]:
            f[f"logVar{lag}"] = np.log(cc.pow(2).rolling(lag, min_periods=lag).mean().clip(lower=floor))
        daily_ewma = strict_ewma(cc.pow(2), cfg["ewmaAlpha"], cfg["ewmaMinimumSessions"])
        intra_ewma = strict_ewma(intraday.pow(2), cfg["ewmaAlpha"], cfg["ewmaMinimumSessions"])
        f["ewma"] = (intra_ewma + (horizon - 1) * daily_ewma) / horizon
        f["logEwmaVariance"] = np.log(f.ewma.clip(lower=floor))
        f["entryDate"], f["labelEnd"] = dates.shift(-1), dates.shift(-horizon)
        legs = [intraday.shift(-1).pow(2)] + [cc.shift(-j).pow(2) for j in range(2, horizon + 1)]
        f["realizedVariance"] = pd.concat(legs, axis=1).sum(axis=1, min_count=horizon) / horizon
        entry = o.shift(-1)
        values = np.column_stack([np.ones(len(sessions))] + [(c.shift(-j) / entry).to_numpy() for j in range(1, horizon + 1)])
        f["drawdownSeverity"] = np.max(1 - values / np.maximum.accumulate(values, axis=1), axis=1)
        f["drawdownEvent"] = (f.drawdownSeverity > cfg["drawdownThreshold"]).where(f.drawdownSeverity.notna()).astype(float)
        output.append(f[f.date <= end].reset_index(drop=True))
    return pd.concat(output, ignore_index=True).replace([np.inf, -np.inf], np.nan).sort_values(["date", "ticker"]).reset_index(drop=True)


def split_supervised(frame, asof, cfg):
    features = [f"logVar{n}" for n in cfg["harLags"]] + cfg["drawdownFeatures"]
    eligible = frame[(frame.date < asof) & (frame.labelEnd <= asof) &
                     (frame.date >= asof - pd.DateOffset(years=cfg["trainingYears"]))]
    eligible = eligible.dropna(subset=features + ["realizedVariance", "drawdownEvent"])
    dates = sorted(eligible.date.unique())
    if len(dates) < cfg["minimumFitDates"] + cfg["calibrationSessions"] + cfg["horizon"]:
        raise ValueError("Insufficient matured, purged fitting and calibration dates")
    first_calibration = pd.Timestamp(dates[-cfg["calibrationSessions"]])
    train = eligible[eligible.labelEnd < first_calibration].copy()
    calibration = eligible[eligible.date >= first_calibration].copy()
    if train.date.nunique() < cfg["minimumFitDates"]:
        raise ValueError("Insufficient fitting dates after purging")
    assert train.labelEnd.max() < calibration.date.min()
    assert calibration.labelEnd.max() <= asof
    return train, calibration


def logit(probabilities):
    p = np.clip(np.asarray(probabilities), 1e-8, 1 - 1e-8)
    return np.log(p / (1 - p)).reshape(-1, 1)


def probability(model, values):
    return np.full(len(values), model) if isinstance(model, float) else model.predict_proba(values)[:, 1]


def fit_garch(frame, field, asof, cfg):
    from arch import arch_model
    raw = frame[(frame.date <= asof) & (frame.date >= asof - pd.DateOffset(years=cfg["trainingYears"]))]
    # The first available close has no preceding close. This structural leading
    # slot is not an internal missing exchange session.
    if field == "closeReturn" and len(raw) and raw.date.iloc[0] == frame.date.min() and pd.isna(raw[field].iloc[0]):
        raw = raw.iloc[1:]
    values = raw[field].to_numpy(dtype=float)
    if len(values) < cfg["minimumFitDates"] or not np.isfinite(values).all():
        raise ValueError("GARCH requires complete chronological return observations")
    spec = cfg["garch"]
    model = arch_model(spec["returnScale"] * values, mean=spec["mean"], vol=spec["vol"],
                       p=spec["p"], q=spec["q"], dist=spec["dist"], rescale=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = model.fit(disp="off", show_warning=False, options={"maxiter": spec["maxIterations"]})
    omega, alpha, beta = [float(result.params[name]) for name in ["omega", "alpha[1]", "beta[1]"]]
    variance = float(np.asarray(result.conditional_volatility)[-1] ** 2)
    if result.convergence_flag != 0 or not np.isfinite([omega, alpha, beta, variance]).all():
        raise ValueError("GARCH optimizer did not converge to finite parameters")
    if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta > 1 + 1e-7 or variance <= 0:
        raise ValueError("GARCH parameters violate the declared variance constraints")
    return {"omega": omega, "alpha": alpha, "beta": beta, "variance": variance,
            "lastReturn": float(spec["returnScale"] * values[-1]), "asof": asof,
            "scale": spec["returnScale"], "returnDates": len(raw), "firstReturnDate": str(raw.date.min().date()),
            "convergenceFlag": int(result.convergence_flag)}


def garch_horizons(state, history, field, dates, horizon):
    """Frozen parameters; filter only returns observed by each forecast origin."""
    requested = pd.DatetimeIndex(dates)
    if requested.min() < state["asof"]:
        raise ValueError("Cannot forecast before the model fit cutoff")
    path = history[(history.date >= state["asof"]) & (history.date <= requested.max())].sort_values("date")
    if path.empty or path.iloc[0].date != state["asof"]:
        raise ValueError("GARCH filter anchor is absent from the current input")
    omega, alpha, beta = (state[k] for k in ["omega", "alpha", "beta"])
    variance, previous = state["variance"], state["lastReturn"]
    predictions, valid = {}, True
    for row in path.itertuples(index=False):
        if row.date > state["asof"]:
            variance = omega + alpha * previous ** 2 + beta * variance
            previous = getattr(row, field) * state["scale"]
            valid = valid and np.isfinite(previous) and np.isfinite(variance) and variance > 0
        if row.date in requested:
            if not valid:
                predictions[row.date] = np.full(horizon, np.nan)
                continue
            following = omega + alpha * previous ** 2 + beta * variance
            values = [following]
            for _ in range(1, horizon):
                following = omega + (alpha + beta) * following
                values.append(following)
            predictions[row.date] = np.asarray(values) / state["scale"] ** 2
    return np.asarray([predictions.get(day, np.full(horizon, np.nan)) for day in requested])


def fit_asset(frame, asof, cfg):
    asof = pd.Timestamp(asof)
    bundle = {"asof": asof, "har": None, "smear": None, "drawdown": None, "calibrator": None,
              "baseRate": None, "garch": {}, "errors": {}, "metadata": {"fitAsOf": str(asof.date())}}
    features = [f"logVar{n}" for n in cfg["harLags"]]
    try:
        train, calibration = split_supervised(frame, asof, cfg)
        bundle["metadata"].update(fitStart=str(train.date.min().date()), fitLastOutcome=str(train.labelEnd.max().date()),
            calibrationStart=str(calibration.date.min().date()), calibrationLastOutcome=str(calibration.labelEnd.max().date()),
            fittingDates=len(train), calibrationDates=len(calibration))
        estimator = LinearRegression().fit(train[features], np.log(train.realizedVariance.clip(lower=cfg["varianceFloor"])))
        residual = np.log(calibration.realizedVariance.clip(lower=cfg["varianceFloor"])) - estimator.predict(calibration[features])
        smear = float(np.exp(residual).mean())
        if np.isfinite(smear) and smear > 0:
            bundle["har"], bundle["smear"] = estimator, smear
        else:
            bundle["errors"]["har_daily"] = "Non-finite residual-smearing calibration"
        y = train.drawdownEvent.astype(int)
        if y.nunique() < 2:
            classifier = float((y.sum() + .5) / (len(y) + 1))
        else:
            classifier = make_pipeline(StandardScaler(), LogisticRegression(C=cfg["drawdownC"], max_iter=2000))
            classifier.fit(train[cfg["drawdownFeatures"]], y)
        raw = probability(classifier, calibration[cfg["drawdownFeatures"]])
        cy = calibration.drawdownEvent.astype(int)
        if cy.nunique() < 2:
            calibrator = float((cy.sum() + .5) / (len(cy) + 1))
        else:
            calibrator = LogisticRegression(C=cfg["calibrationC"], max_iter=2000).fit(logit(raw), cy)
        bundle["drawdown"], bundle["calibrator"] = classifier, calibrator
        bundle["baseRate"] = float((y.sum() + cy.sum() + .5) / (len(y) + len(cy) + 1))
    except ValueError as exc:
        bundle["errors"]["supervised"] = str(exc)
    for field in ["intradayReturn", "closeReturn"]:
        try:
            bundle["garch"][field] = fit_garch(frame, field, asof, cfg)
        except (ValueError, ArithmeticError) as exc:
            bundle["errors"][f"garch_{field}"] = str(exc)
    bundle["metadata"]["errors"] = bundle["errors"]
    bundle["metadata"]["garch"] = bundle["garch"]
    return bundle


def predict_asset(bundle, history, dates, cfg):
    rows = history[history.date.isin(dates)].sort_values("date").copy()
    output = rows[["date", "ticker", "entryDate", "labelEnd", "realizedVariance", "drawdownSeverity", "drawdownEvent", "ewma"]].copy()
    output["fitAsOf"] = bundle["asof"]
    output["har_daily"], output["garch11"], output["volatility_only"] = np.nan, np.nan, np.nan
    output["base_rate"] = bundle["baseRate"] if bundle["baseRate"] is not None else np.nan
    features = [f"logVar{n}" for n in cfg["harLags"]]
    valid = rows[features].notna().all(axis=1)
    if bundle["har"] is not None and valid.any():
        values = np.exp(bundle["har"].predict(rows.loc[valid, features])) * bundle["smear"]
        output.loc[valid, "har_daily"] = np.where(np.isfinite(values) & (values > 0), values, np.nan)
    valid = rows[cfg["drawdownFeatures"]].notna().all(axis=1)
    if bundle["drawdown"] is not None and valid.any():
        raw = probability(bundle["drawdown"], rows.loc[valid, cfg["drawdownFeatures"]])
        output.loc[valid, "volatility_only"] = probability(bundle["calibrator"], logit(raw))
    if len(bundle["garch"]) == 2:
        intra = garch_horizons(bundle["garch"]["intradayReturn"], history, "intradayReturn", rows.date, cfg["horizon"])
        cc = garch_horizons(bundle["garch"]["closeReturn"], history, "closeReturn", rows.date, cfg["horizon"])
        output["garch11"] = (intra[:, 0] + cc[:, 1:].sum(axis=1)) / cfg["horizon"]
    return output
