from __future__ import annotations

import numpy as np
import pandas as pd

from unpriced.features import FEATURES, RISK_FEATURES, panel


def make_panel(data, cfg, registry, macro=None):
    frame = panel(data, cfg)
    sessions = pd.DatetimeIndex(sorted(frame.date.unique()))
    closes = data.pivot(index="date", columns="ticker", values="close").reindex(sessions)
    opens = data.pivot(index="date", columns="ticker", values="open").reindex(sessions)
    targets = []
    for ticker in cfg["universe"]:
        entry = opens[ticker].shift(-1)
        legs = [closes[ticker].shift(-j) / entry for j in range(1, cfg["horizon"] + 1)]
        values = np.column_stack([np.ones(len(sessions))] + [s.to_numpy() for s in legs])
        peaks = np.maximum.accumulate(values, axis=1)
        severity = np.max(1 - values / peaks, axis=1)
        severity[entry.isna()] = np.nan
        targets.append(pd.DataFrame({"date": sessions, "ticker": ticker, "drawdownSeverity": severity}))
    frame = frame.merge(pd.concat(targets), on=["date", "ticker"], validate="one_to_one")
    frame["drawdownEvent"] = (frame.drawdownSeverity > registry["drawdownThreshold"]).where(frame.drawdownSeverity.notna()).astype(float)
    for ticker in cfg["universe"]:
        frame[f"sector_{ticker}"] = (frame.ticker == ticker).astype(float)
    if macro is not None:
        frame = frame.merge(macro, on="date", how="left", validate="many_to_one")
        for col in registry["macro"]["features"]:
            for ticker in cfg["universe"]:
                frame[f"{col}_x_{ticker}"] = frame[col] * frame[f"sector_{ticker}"]
    return frame.sort_values(["date", "ticker"]).reset_index(drop=True)


def columns(task, feature_set, cfg, registry):
    base = RISK_FEATURES if task == "variance" else list(dict.fromkeys(FEATURES + RISK_FEATURES)) if task == "drawdown" else FEATURES
    result = list(base) + [f"sector_{t}" for t in cfg["universe"]]
    if feature_set == "macro":
        result += registry["macro"]["features"]
        result += [f"{m}_x_{t}" for m in registry["macro"]["features"] for t in cfg["universe"]]
    return result


TARGETS = {"excess": "outcome", "variance": "realizedVariance", "drawdown": "drawdownEvent"}


def resolved_history(frame, ticker, task, asof, context_length):
    """Chronos sees only targets that have already finished, indexed by their end.

    The value at t+5 is exactly the target for a decision at t. Missing exchange
    sessions retain their slots; dropping NaNs would change what five steps means.
    """
    asof = pd.Timestamp(asof)
    field = {"excess": "excessReturn", "variance": "realizedVariance", "drawdown": "drawdownSeverity"}[task]
    sessions = pd.DatetimeIndex(sorted(frame.loc[frame.date <= asof, "date"].unique()))[-context_length:]
    known = frame[(frame.ticker == ticker) & (frame.date < asof) & (frame.labelEnd <= asof)]
    values = known.set_index("labelEnd")[field].reindex(sessions).to_numpy(dtype=float)
    if task == "variance":
        values = np.log(np.clip(values, 1e-10, None))
    return values
