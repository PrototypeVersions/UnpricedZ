from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .models import MODEL_NAMES, fit, predict


def block_interval(values, block=20, repetitions=1500, seed=20261104):
    """Circular moving-block bootstrap of paired date means, NOT individual stocks."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    n = len(values)
    if n < max(2 * block, 40):
        return {"mean": float(values.mean()) if n else None, "low": None, "high": None,
                "dates": n, "blockSessions": block, "status": "insufficient-dates"}
    rng = np.random.default_rng(seed)
    count = int(np.ceil(n / block))
    starts = rng.integers(0, n, (repetitions, count))
    indices = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    means = values[indices.reshape(repetitions, -1)[:, :n]].mean(axis=1)
    return {"mean": float(values.mean()), "low": float(np.quantile(means, 0.025)),
            "high": float(np.quantile(means, 0.975)), "dates": n,
            "blockSessions": block, "status": "descriptive-95-percent-interval"}


def quarter_folds(frame, cfg):
    dates = pd.DatetimeIndex(sorted(frame[frame.date >= pd.Timestamp(cfg["researchStart"])].date.unique()))
    # Every model is frozen during a calendar quarter. The first date is its fitting cutoff.
    for quarter in dates.to_period("Q").unique():
        selected = dates[dates.to_period("Q") == quarter]
        yield selected[0], selected[-1], str(quarter)


def walk_forward(frame, cfg, include_boosted=True):
    results, folds = [], []
    for start, end, identifier in quarter_folds(frame, cfg):
        # Predict from current features first. Future missingness must not select candidates.
        test = frame[(frame.date >= start) & (frame.date <= end)]
        if test.empty:
            continue
        try:
            bundle = fit(frame, start, cfg, include_boosted=include_boosted)
        except ValueError as exc:
            if "Insufficient" in str(exc):
                continue
            raise
        prediction = predict(bundle, test)
        prediction["fold"] = identifier
        prediction["fitAsOf"] = start
        results.append(prediction)
        folds.append({"id": identifier, "testStart": str(start.date()), "testEnd": str(test.date.max().date()),
                      "testDates": test.date.nunique(), **bundle["metadata"]})
        print(f"Evaluated {identifier}: {test.date.nunique()} forecast dates", flush=True)
    if not results:
        raise ValueError("No eligible out-of-sample folds")
    return pd.concat(results, ignore_index=True), folds


def calibration_bins(p, y):
    result = []
    for lo in np.arange(0, 1, 0.1):
        mask = (p >= lo) & (p < lo + 0.1 + (1e-10 if lo > 0.89 else 0))
        if mask.any():
            result.append({"low": round(float(lo), 1), "high": round(float(lo + 0.1), 1),
                           "count": int(mask.sum()), "predicted": float(p[mask].mean()), "observed": float(y[mask].mean())})
    return result


def summarize(predictions, cfg):
    d = predictions.dropna(subset=["outcome", "realizedVariance"]).copy()
    if d.empty:
        return {"dates": 0, "observations": 0, "models": [], "risk": [], "daily": [], "folds": []}
    y = d.outcome.to_numpy()
    def date_mean(values):
        return float(pd.Series(np.asarray(values), index=d.date).groupby(level=0).mean().mean())
    base = (d.p_base_rate.to_numpy() - y) ** 2
    models, daily = [], pd.DataFrame({"date": sorted(d.date.unique())}).set_index("date")
    for key, label in MODEL_NAMES.items():
        if f"p_{key}" not in d:
            continue
        p = np.clip(d[f"p_{key}"].to_numpy(), 1e-7, 1 - 1e-7)
        loss = (p - y) ** 2
        # Positive improvement means the challenger has lower loss than the baseline.
        gains = pd.Series(base - loss, index=d.date).groupby(level=0).mean().sort_index()
        daily[key] = gains
        interval = block_interval(gains, cfg["bootstrapBlockSessions"], cfg["bootstrapReplications"])
        models.append({"id": key, "name": label, "brier": date_mean(loss),
                       "logLoss": date_mean(-(y * np.log(p) + (1 - y) * np.log(1 - p))),
                       "improvement": interval, "calibration": calibration_bins(p, y),
                       "forecastMin": float(p.min()), "forecastMax": float(p.max()),
                       "status": "baseline" if key == "base_rate" else "research-only"})
    ic = []
    for date, group in d.groupby("date"):
        if len(group) >= 6 and group.expectedExcess.nunique() > 1 and group.excessReturn.nunique() > 1:
            ic.append({"date": date, "ic": float(spearmanr(group.expectedExcess, group.excessReturn).statistic)})
    variance = d.realizedVariance.to_numpy().clip(min=1e-10)
    ewma = d.ewmaVariance.to_numpy().clip(min=1e-10)
    har = d.harVariance.to_numpy().clip(min=1e-10)
    q = lambda pred: variance / pred - np.log(variance / pred) - 1
    risk_gain = pd.Series(q(ewma) - q(har), index=d.date).groupby(level=0).mean().sort_index()
    coverage = date_mean((d.excessReturn >= d.lower80) & (d.excessReturn <= d.upper80))
    annual = []
    for year, group in d.groupby(d.date.dt.year):
        annual.append({"year": int(year), "dates": group.date.nunique(),
                       "brierBaseline": float(((group.p_base_rate - group.outcome) ** 2).mean()),
                       "brierLogistic": float(((group.p_logistic - group.outcome) ** 2).mean()),
                       "meanExcess": float(group.excessReturn.mean())})
    return {"dates": d.date.nunique(), "observations": len(d), "start": str(d.date.min().date()),
            "end": str(d.date.max().date()), "models": models,
            "risk": [{"id": "ewma", "name": "EWMA baseline", "qlike": date_mean(q(ewma))},
                     {"id": "har", "name": "Daily-variance HAR-style model", "qlike": date_mean(q(har)),
                      "improvement": block_interval(risk_gain, cfg["bootstrapBlockSessions"], cfg["bootstrapReplications"])}],
            "rankIC": block_interval([x["ic"] for x in ic], cfg["bootstrapBlockSessions"], cfg["bootstrapReplications"]),
            "intervalCoverage80": float(coverage), "annual": annual,
            "daily": [{"date": str(date.date()), **{k: float(v) for k, v in row.items()}} for date, row in daily.iterrows()],
            "inferenceNote": "Paired date-level moving-block bootstrap; descriptive intervals, not selection-adjusted proof or promotion permission."}


def portfolio_simulation(predictions, cfg):
    """Non-overlapping, ex-ante plans; provider-adjusted reference returns, no broker fills."""
    p = cfg["portfolio"]
    equity = benchmark = p["startingEquity"]
    curve, trades, unresolved = [], [], []
    next_date = pd.Timestamp.min
    for date, group in predictions.sort_values(["date", "ticker"]).groupby("date"):
        if date < next_date:
            continue
        eligible = group[(group.p_logistic >= p["minimumProbability"]) &
                         (group.expectedExcess > p["minimumExpectedExcess"])].sort_values("expectedExcess", ascending=False).head(p["maxPositions"])
        if group.labelEnd.isna().any() or group.spyReturn.isna().any() or eligible.assetReturn.isna().any():
            unresolved.append({"signalDate": str(date.date()), "selected": list(eligible.ticker),
                               "reason": "Selected cohort or benchmark outcome is unavailable; equity series stops here without reranking."})
            break
        gain = sum(p["maxWeight"] * ((1 + row.assetReturn) * (1 - p["costPerSide"]) / (1 + p["costPerSide"]) - 1)
                   for row in eligible.itertuples())
        equity *= 1 + gain
        benchmark *= 1 + float(group.spyReturn.iloc[0])
        exit_date = group.labelEnd.iloc[0]
        next_date = exit_date  # Next decision at this close; next position starts next open.
        curve.append({"date": str(exit_date.date()), "equity": equity, "benchmark": benchmark, "positions": len(eligible)})
        trades += [{"signalDate": str(date.date()), "entryDate": str(row.entryDate.date()),
                    "exitDate": str(row.labelEnd.date()), "ticker": row.ticker,
                    "return": row.assetReturn, "weight": p["maxWeight"]} for row in eligible.itertuples()]
    # Comparator deliberately shares open-to-close windows; excludes between-window overnight gaps.
    return {"status": "historical-reference-simulation", "startingEquity": p["startingEquity"],
            "equity": equity, "benchmark": benchmark, "positionCount": len(trades), "curve": curve,
            "trades": trades, "unresolvedCohorts": unresolved, "benchmarkLabel": "SPY over identical holding windows",
            "note": "Predeclared policy, 10 bps per side, fixed five-session holds; adjusted reference returns, not executable fills. No overnight exposure between cohorts. Cash earns zero. Thresholds have not been optimized."}
