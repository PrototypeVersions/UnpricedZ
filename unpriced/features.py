from __future__ import annotations

import numpy as np
import pandas as pd

from .data import exchange_schedule

FEATURES = ["ret1", "rel5", "rel20", "rel60", "vol20", "volRatio", "volumeZ",
            "spy20", "spyVol", "breadth", "dispersion", "bond20", "gold20"]
RISK_FEATURES = ["logVar5", "logVar20", "logVar60", "negative20", "spyLogVar20"]


def panel(data, cfg):
    """No imputation. Missing observations invalidate affected features/targets."""
    c = data.pivot(index="date", columns="ticker", values="close").sort_index()
    o = data.pivot(index="date", columns="ticker", values="open").reindex(c.index)
    volume = data.pivot(index="date", columns="ticker", values="volume").reindex(c.index)
    # A missing benchmark bar must not remove an exchange session from the target clock.
    sessions = exchange_schedule(c.index.min().date(), c.index.max().date()).index
    c, o, volume = c.reindex(sessions), o.reindex(sessions), volume.reindex(sessions)
    dates = pd.Series(sessions, index=sessions)
    r = c.pct_change(fill_method=None)
    log_r = np.log(c / c.shift(1))
    spy = cfg["benchmark"]
    h = cfg["horizon"]
    sector = c[list(cfg["universe"])]
    ma = sector.rolling(20, min_periods=20).mean()
    valid = sector.notna() & ma.notna()
    breadth = (sector > ma).where(valid).mean(axis=1)
    dispersion = r[list(cfg["universe"])].std(axis=1).rolling(20).mean()
    spy_fwd = c[spy].shift(-h) / o[spy].shift(-1) - 1
    out = []
    for ticker in cfg["universe"]:
        f = pd.DataFrame(index=c.index)
        f["ticker"] = ticker
        f["ret1"] = r[ticker]
        for n in [5, 20, 60]:
            f[f"rel{n}"] = c[ticker].pct_change(n, fill_method=None) - c[spy].pct_change(n, fill_method=None)
            f[f"logVar{n}"] = np.log(log_r[ticker].pow(2).rolling(n, min_periods=n).mean().clip(lower=1e-10))
        f["vol20"] = r[ticker].rolling(20).std() * np.sqrt(252)
        f["spyVol"] = r[spy].rolling(20).std() * np.sqrt(252)
        f["volRatio"] = f.vol20 / f.spyVol.replace(0, np.nan)
        lv = np.log(volume[ticker].replace(0, np.nan))
        f["volumeZ"] = (lv - lv.rolling(20).mean()) / lv.rolling(20).std().replace(0, np.nan)
        f["spy20"] = c[spy].pct_change(20, fill_method=None)
        f["breadth"], f["dispersion"] = breadth, dispersion
        f["bond20"] = c["TLT"].pct_change(20, fill_method=None)
        f["gold20"] = c["GLD"].pct_change(20, fill_method=None)
        f["negative20"] = r[ticker].clip(upper=0).pow(2).rolling(20).mean()
        f["spyLogVar20"] = np.log(log_r[spy].pow(2).rolling(20).mean().clip(lower=1e-10))
        daily_ewma = log_r[ticker].pow(2).ewm(alpha=0.06, adjust=False, min_periods=60).mean()
        intraday_ewma = np.log(c[ticker] / o[ticker]).pow(2).ewm(alpha=0.06, adjust=False, min_periods=60).mean()
        f["ewmaVariance"] = (intraday_ewma + (h - 1) * daily_ewma) / h
        f["entryDate"] = dates.shift(-1)
        f["labelEnd"] = dates.shift(-h)
        f["assetReturn"] = c[ticker].shift(-h) / o[ticker].shift(-1) - 1
        f["spyReturn"] = spy_fwd
        f["excessReturn"] = f.assetReturn - f.spyReturn
        f["outcome"] = (f.excessReturn > 0).where(f.excessReturn.notna()).astype(float)
        # First open-to-close leg, then h-1 close-to-close legs: exactly the target window.
        components = [np.log(c[ticker].shift(-1) / o[ticker].shift(-1)).pow(2)]
        components += [log_r[ticker].shift(-j).pow(2) for j in range(2, h + 1)]
        f["realizedVariance"] = pd.concat(components, axis=1).sum(axis=1, min_count=h) / h
        # Any missing price within a holding period invalidates its return too.
        complete = pd.concat([c[ticker].shift(-j).notna() & c[spy].shift(-j).notna() for j in range(1, h + 1)], axis=1).all(axis=1)
        f.loc[~complete, ["assetReturn", "spyReturn", "excessReturn", "outcome", "realizedVariance"]] = np.nan
        f["date"] = f.index
        out.append(f.reset_index(drop=True))
    result = pd.concat(out, ignore_index=True).replace([np.inf, -np.inf], np.nan)
    return result.sort_values(["date", "ticker"]).reset_index(drop=True)


def split_training(frame, asof, cfg):
    """All labels mature by asof; fit labels end strictly before calibration starts."""
    asof = pd.Timestamp(asof)
    eligible = frame[(frame.date < asof) & (frame.labelEnd <= asof)].dropna(
        subset=FEATURES + RISK_FEATURES + ["outcome", "excessReturn", "realizedVariance"])
    eligible = eligible[eligible.date >= asof - pd.DateOffset(years=cfg["trainingYears"])]
    dates = sorted(eligible.date.unique())
    if len(dates) < cfg["minimumTrainingSessions"] + cfg["calibrationSessions"]:
        raise ValueError("Insufficient chronological fitting and calibration history")
    cal_start = pd.Timestamp(dates[-cfg["calibrationSessions"]])
    fit = eligible[eligible.labelEnd < cal_start].copy()
    calibration = eligible[eligible.date >= cal_start].copy()
    if fit.date.nunique() < cfg["minimumTrainingSessions"] or calibration.date.nunique() < cfg["minimumCalibrationSessions"]:
        raise ValueError("Insufficient purged training/calibration dates")
    assert fit.labelEnd.max() < calibration.date.min()
    assert calibration.labelEnd.max() <= asof
    return fit, calibration
