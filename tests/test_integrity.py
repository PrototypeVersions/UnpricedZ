from __future__ import annotations

import copy
import json

import numpy as np
import pandas as pd
import pytest

from unpriced.controls import synthetic_market
from unpriced.data import market_summary, session_context, validate_bars
from unpriced.evaluation import block_interval, portfolio_simulation
from unpriced.features import FEATURES, RISK_FEATURES, panel, split_training
from unpriced.io import config
from unpriced.live import immutable_snapshot, publication_allowed
from unpriced.models import fit, predict


@pytest.fixture(scope="module")
def market():
    cfg = config()
    return cfg, synthetic_market(cfg, 7, sessions=1500)


def test_future_prices_cannot_change_earlier_features(market):
    cfg, data = market
    dates = sorted(data.date.unique())
    cutoff = pd.Timestamp(dates[-100])
    original = panel(data, cfg)
    changed = data.copy()
    mask = changed.date > cutoff
    changed.loc[mask, ["open", "high", "low", "close"]] *= 17
    altered = panel(changed, cfg)
    cols = ["date", "ticker"] + FEATURES + RISK_FEATURES
    pd.testing.assert_frame_equal(original.loc[original.date <= cutoff, cols], altered.loc[altered.date <= cutoff, cols])


def test_future_prices_cannot_change_predictions(market):
    cfg, data = market
    cutoff = pd.Timestamp(sorted(data.date.unique())[-100])
    features = panel(data, cfg)
    model = fit(features, cutoff, cfg)
    before = predict(model, features[features.date == cutoff])
    changed = data.copy()
    changed.loc[changed.date > cutoff, ["open", "high", "low", "close"]] *= 3
    altered = panel(changed, cfg)
    rebuilt = fit(altered, cutoff, cfg)
    after = predict(rebuilt, altered[altered.date == cutoff])
    columns = [c for c in before if c.startswith("p_")] + ["expectedExcess", "harVariance"]
    np.testing.assert_allclose(before[columns], after[columns], atol=1e-12)


def test_purging_and_calibration_boundaries(market):
    cfg, data = market
    frame = panel(data, cfg)
    cutoff = frame.date.max()
    training, calibration = split_training(frame, cutoff, cfg)
    assert training.labelEnd.max() < calibration.date.min()
    assert calibration.labelEnd.max() <= cutoff
    assert not set(training.date).intersection(calibration.date)
    assert training.date.nunique() >= cfg["minimumTrainingSessions"]


def test_target_endpoints_include_holidays(market):
    cfg, data = market
    frame = panel(data, cfg)
    # Friday before MLK Day: five sessions start Tuesday and end Monday.
    decision = pd.Timestamp("2013-01-18")
    row = frame[(frame.date == decision) & (frame.ticker == "XLK")].iloc[0]
    assert row.entryDate == pd.Timestamp("2013-01-22")
    assert row.labelEnd == pd.Timestamp("2013-01-28")
    prices = data[data.ticker == "XLK"].set_index("date")
    expected = prices.loc[row.labelEnd, "close"] / prices.loc[row.entryDate, "open"] - 1
    assert row.assetReturn == pytest.approx(expected)


def test_missing_observation_does_not_shorten_horizon(market):
    cfg, data = market
    missing = data[~((data.ticker == "XLK") & (data.date == pd.Timestamp("2013-01-24")))].copy()
    frame = panel(missing, cfg)
    row = frame[(frame.date == pd.Timestamp("2013-01-18")) & (frame.ticker == "XLK")].iloc[0]
    assert row.labelEnd == pd.Timestamp("2013-01-28")
    assert pd.isna(row.excessReturn)


def test_stale_symbol_fails_validation(market):
    cfg, data = market
    latest = data.date.max()
    missing = data[~((data.ticker == "XLK") & (data.date == latest))]
    with pytest.raises(ValueError, match="current-session"):
        validate_bars(missing, cfg, latest)


def test_missing_spy_does_not_remove_exchange_session(market):
    cfg, data = market
    missing = data[~((data.ticker == "SPY") & (data.date == pd.Timestamp("2013-01-24")))].copy()
    frame = panel(missing, cfg)
    row = frame[(frame.date == pd.Timestamp("2013-01-18")) & (frame.ticker == "XLK")].iloc[0]
    assert row.labelEnd == pd.Timestamp("2013-01-28")
    assert pd.isna(row.excessReturn)


def test_breadth_does_not_count_missing_as_below(market):
    cfg, data = market
    latest = data.date.max()
    missing = data[~((data.ticker == "XLK") & (data.date == latest))]
    summary = market_summary(missing, cfg)
    assert summary["breadthCoverage"] == 8
    px = missing.pivot(index="date", columns="ticker", values="close")[list(cfg["universe"])]
    valid = px.iloc[-1].notna() & px.rolling(20).mean().iloc[-1].notna()
    assert summary["breadth"] == pytest.approx((px.iloc[-1][valid] > px.rolling(20).mean().iloc[-1][valid]).mean())


def test_publication_is_before_target_open():
    context = session_context("2026-11-04T01:00:00Z")
    assert publication_allowed(context, "2026-11-04T01:00:00Z")
    assert not publication_allowed(context, context["nextOpen"])
    assert not publication_allowed(context, context["close"] + pd.Timedelta(minutes=20))


def test_immutable_forecast(tmp_path):
    path = tmp_path / "snapshot.json"
    immutable_snapshot(path, {"probability": 0.52})
    with pytest.raises(FileExistsError):
        immutable_snapshot(path, {"probability": 0.99})
    assert json.loads(path.read_text())["probability"] == 0.52


def test_probabilities_and_risk_are_finite(market):
    cfg, data = market
    frame = panel(data, cfg)
    asof = frame.date.max()
    model = fit(frame, asof, cfg)
    result = predict(model, frame[frame.date == asof])
    assert len(result) == len(cfg["universe"])
    probabilities = result[[c for c in result if c.startswith("p_")]]
    assert np.isfinite(probabilities).all().all()
    assert ((probabilities >= 0) & (probabilities <= 1)).all().all()
    assert (result.harVariance > 0).all()
    assert not model["models"]["boosted"]["estimator"].early_stopping


def test_block_intervals_require_dates():
    result = block_interval(np.zeros(10))
    assert result["status"] == "insufficient-dates"
    assert result["low"] is None
    result = block_interval(np.full(200, 0.02), repetitions=100)
    assert result["low"] == pytest.approx(0.02)
    assert result["high"] == pytest.approx(0.02)


def test_reference_simulator_costs_and_fixed_exit():
    cfg = config()
    date = pd.Timestamp("2024-01-02")
    rows = [{"date": date, "ticker": "XLK", "entryDate": pd.Timestamp("2024-01-03"),
             "labelEnd": pd.Timestamp("2024-01-09"), "p_logistic": 0.7,
             "expectedExcess": 0.01, "assetReturn": 0.0, "spyReturn": 0.0}]
    report = portfolio_simulation(pd.DataFrame(rows), cfg)
    expected = 1000 * (1 + 0.3 * ((1 - .001) / (1 + .001) - 1))
    assert report["equity"] == pytest.approx(expected)
    assert report["trades"][0]["exitDate"] == "2024-01-09"


def test_synthetic_generator_is_reproducible(market):
    cfg, _ = market
    pd.testing.assert_frame_equal(synthetic_market(cfg, 11, sessions=100), synthetic_market(cfg, 11, sessions=100))


def test_portfolio_cannot_rerank_around_unknown_future_outcome():
    cfg = config()
    rows = [{"date": pd.Timestamp("2024-01-02"), "ticker": ticker,
             "entryDate": pd.Timestamp("2024-01-03"), "labelEnd": pd.Timestamp("2024-01-09"),
             "p_logistic": .7, "expectedExcess": score, "assetReturn": ret, "spyReturn": .01}
            for ticker, score, ret in [("XLK", .03, np.nan), ("XLE", .02, .04), ("XLF", .01, .02), ("XLU", .005, .06)]]
    report = portfolio_simulation(pd.DataFrame(rows), cfg)
    assert report["equity"] == 1000
    assert report["unresolvedCohorts"][0]["selected"] == ["XLK", "XLE", "XLF"]
    assert not report["trades"]
