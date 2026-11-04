from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf

from .io import ROOT, now, write


def exchange_schedule(start, end):
    return mcal.get_calendar("NYSE").schedule(start_date=start, end_date=end)


def session_context(at=None):
    at = pd.Timestamp.now(tz="UTC") if at is None else pd.Timestamp(at)
    if at.tzinfo is None:
        raise ValueError("An explicit timezone is required")
    local = at.tz_convert("America/New_York")
    sched = exchange_schedule((local - pd.Timedelta(days=14)).date(), (local + pd.Timedelta(days=20)).date())
    completed = sched[sched.market_close + pd.Timedelta(minutes=45) <= at]
    if completed.empty:
        raise ValueError("No completed trading session")
    session = completed.index[-1]
    following = sched[sched.index > session]
    return {"session": session, "close": completed.iloc[-1].market_close,
            "nextOpen": following.iloc[0].market_open,
            "nextSessions": [d.date().isoformat() for d in following.index],
            "today": local.date().isoformat(), "at": at}


def validate_bars(data, cfg, expected=None):
    required = [cfg["benchmark"]] + list(cfg["universe"]) + cfg["context"]
    needed = {"date", "ticker", "open", "high", "low", "close", "volume"}
    if not needed.issubset(data.columns):
        raise ValueError("OHLCV columns are missing")
    if data.duplicated(["date", "ticker"]).any():
        raise ValueError("Duplicate symbol/date bars")
    if not set(required).issubset(set(data.ticker)):
        raise ValueError("Required symbols missing: " + str(set(required) - set(data.ticker)))
    for symbol, bars in data.groupby("ticker"):
        if len(bars) < 160:
            raise ValueError(f"Insufficient history: {symbol}")
        values = bars[["open", "high", "low", "close"]].to_numpy()
        if not np.isfinite(values).all() or (values <= 0).any():
            raise ValueError(f"Invalid OHLC values: {symbol}")
        if (bars.high < bars[["open", "close", "low"]].max(axis=1) - 1e-5).any():
            raise ValueError(f"Inconsistent high: {symbol}")
        if (bars.low > bars[["open", "close", "high"]].min(axis=1) + 1e-5).any():
            raise ValueError(f"Inconsistent low: {symbol}")
        if not np.isfinite(bars.volume).all() or (bars.volume < 0).any():
            raise ValueError(f"Invalid volume: {symbol}")
        if expected is not None:
            date = pd.Timestamp(expected).normalize()
            current = bars[bars.date == date]
            if len(current) != 1:
                raise ValueError(f"Missing required current-session bar: {symbol} / {date.date()}")
    return data.sort_values(["date", "ticker"]).reset_index(drop=True)


def download(cfg, expected):
    symbols = [cfg["benchmark"]] + list(cfg["universe"]) + cfg["context"]
    end = (pd.Timestamp(expected) + pd.Timedelta(days=1)).date().isoformat()
    raw = yf.download(symbols, start=cfg["historyStart"], end=end, interval="1d",
                      auto_adjust=True, actions=False, group_by="ticker", threads=False,
                      progress=False, timeout=30)
    if raw.empty:
        raise RuntimeError("The provider returned no market data")
    records = []
    for symbol in symbols:
        frame = raw[symbol].copy() if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
        frame = frame.dropna(how="all")
        frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
        frame = frame.rename(columns=str.lower)
        frame["ticker"] = symbol
        frame["date"] = frame.index
        records.append(frame[["date", "ticker", "open", "high", "low", "close", "volume"]])
    data = pd.concat(records, ignore_index=True)
    data = data[data.date <= pd.Timestamp(expected)]
    return validate_bars(data, cfg, expected)


def archive(data, kind):
    """Archive a compressed, content-addressed input vintage; never overwrite it."""
    normalized = data.sort_values(["date", "ticker"]).copy()
    normalized["date"] = pd.to_datetime(normalized.date).dt.strftime("%Y-%m-%d")
    text = normalized.to_csv(index=False, float_format="%.17g")
    sha = hashlib.sha256(text.encode()).hexdigest()
    date = normalized.date.max()
    path = ROOT / "archive" / "inputs" / f"{date}-{kind}-{sha[:16]}.csv.gz"
    if not path.exists():
        import gzip
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as target:
            target.write(gzip.compress(text.encode(), mtime=0))
    meta = {"path": str(path.relative_to(ROOT)), "csvSha256": sha,
            "rows": len(data), "retrievedAt": now(), "start": normalized.date.min(),
            "end": date, "adjustment": "Provider-adjusted OHLC; both return endpoints use this same vintage"}
    return meta


def load_archive(path):
    return pd.read_csv(path, parse_dates=["date"], float_precision="round_trip")


def market_summary(data, cfg):
    close = data.pivot(index="date", columns="ticker", values="close").sort_index()
    universe = list(cfg["universe"])
    px = close[universe]
    ma = px.rolling(20, min_periods=20).mean()
    valid = px.iloc[-1].notna() & ma.iloc[-1].notna()
    breadth = float((px.iloc[-1][valid] > ma.iloc[-1][valid]).mean()) if valid.any() else None
    returns = close.pct_change(fill_method=None)
    spy = close[cfg["benchmark"]]
    return {"asOf": close.index[-1].date().isoformat(), "breadth": breadth,
            "breadthCoverage": int(valid.sum()), "breadthDenominator": len(universe),
            "spy20d": float(spy.pct_change(20, fill_method=None).iloc[-1]),
            "annualizedVol": float(returns[cfg["benchmark"]].tail(20).std() * np.sqrt(252)),
            "crossSectionalDispersion": float(returns[universe].std(axis=1).tail(20).mean()),
            "sectors": [{"ticker": s, "name": cfg["universe"][s],
                         "return20d": float(close[s].pct_change(20, fill_method=None).iloc[-1]),
                         "relative20d": float(close[s].pct_change(20, fill_method=None).iloc[-1] - spy.pct_change(20, fill_method=None).iloc[-1])}
                        for s in universe],
            "history": [{"date": d.date().isoformat(), "spy": float(v)} for d, v in spy.tail(252).items()]}
