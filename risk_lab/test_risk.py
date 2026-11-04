import copy
import json

import numpy as np
import pandas as pd
import pytest

from risk_lab.core import make_panel, strict_ewma, split_supervised, fit_asset, predict_asset, fit_garch, garch_horizons
from risk_lab.controls import synthetic_market
from risk_lab.live import persist_forecast, publication_allowed, verify_forecast
from risk_lab.storage import config
from unpriced.data import session_context


@pytest.fixture(scope="module")
def market():
    cfg = {**config(), "assets": {"SPY": "Synthetic"}}
    data, _ = synthetic_market(cfg, 73, True)
    return cfg, data


def test_risk_targets_follow_exchange_clock_and_price_legs(market):
    cfg, data = market
    row = make_panel(data, cfg).iloc[100]
    prices = data.set_index("date")
    window = prices.loc[row.entryDate:row.labelEnd]
    assert len(window) == 5
    legs = np.r_[np.log(window.close.iloc[0] / window.open.iloc[0]), np.diff(np.log(window.close))]
    assert row.realizedVariance == pytest.approx(np.mean(legs ** 2))
    path = np.r_[window.open.iloc[0], window.close]
    severity = np.max(1 - path / np.maximum.accumulate(path))
    assert row.drawdownSeverity == pytest.approx(severity)
    assert row.drawdownEvent == float(severity > .03)
    missing = data[data.date != window.index[2]]
    altered = make_panel(missing, cfg).set_index("date").loc[row.date]
    assert altered.entryDate == row.entryDate and altered.labelEnd == row.labelEnd
    assert pd.isna(altered.realizedVariance) and pd.isna(altered.drawdownSeverity)


def test_risk_ewma_missing_slot_requires_fresh_consecutive_history():
    actual = strict_ewma([1., 2., 3., np.nan, 7., 8., 9.], .5, 3)
    np.testing.assert_allclose(actual, [np.nan, np.nan, 2.25, np.nan, np.nan, np.nan, 8.25], equal_nan=True)


def test_risk_purging_and_future_mutation(market):
    pytest.importorskip("arch")
    cfg, data = market
    cutoff = data.date.iloc[900]
    frame = make_panel(data, cfg)
    training, calibration = split_supervised(frame, cutoff, cfg)
    assert training.labelEnd.max() < calibration.date.min()
    assert calibration.labelEnd.max() <= cutoff
    assert len(calibration) == cfg["calibrationSessions"]
    before_model = fit_asset(frame, cutoff, cfg)
    assert not before_model["errors"]
    before = predict_asset(before_model, frame, [cutoff], cfg)
    changed = data.copy()
    changed.loc[changed.date > cutoff, ["open", "close", "high", "low"]] *= 4
    altered = make_panel(changed, cfg)
    after_model = fit_asset(altered, cutoff, cfg)
    after = predict_asset(after_model, altered, [cutoff], cfg)
    names = cfg["varianceModels"] + cfg["drawdownModels"]
    np.testing.assert_allclose(before[names], after[names], atol=1e-12)
    assert before_model["metadata"] == after_model["metadata"]


def test_garch_matches_arch_analytic_forecast_and_filters_observed_returns(market):
    arch = pytest.importorskip("arch")
    cfg, data = market
    frame = make_panel(data, cfg)
    cutoff = frame.date.iloc[800]
    state = fit_garch(frame, "intradayReturn", cutoff, cfg)
    values = frame.loc[frame.date <= cutoff, "intradayReturn"].to_numpy() * 100
    reference = arch.arch_model(values, mean="Zero", vol="GARCH", p=1, q=1, dist="normal", rescale=False).fit(
        disp="off", show_warning=False, options={"maxiter": 300})
    actual = garch_horizons(state, frame, "intradayReturn", [cutoff], 5)[0]
    expected = reference.forecast(horizon=5, reindex=False).variance.iloc[-1].to_numpy() / 10000
    np.testing.assert_allclose(actual, expected, rtol=1e-9)
    tomorrow = frame.date.iloc[801]
    update = garch_horizons(state, frame, "intradayReturn", [tomorrow], 5)[0]
    next_variance = state["omega"] + state["alpha"] * state["lastReturn"] ** 2 + state["beta"] * state["variance"]
    current_return = frame.intradayReturn.iloc[801] * 100
    assert update[0] == pytest.approx((state["omega"] + state["alpha"] * current_return ** 2 + state["beta"] * next_variance) / 10000)
    changed = frame.copy()
    changed.loc[changed.date > tomorrow, "intradayReturn"] = 1000
    np.testing.assert_allclose(garch_horizons(state, changed, "intradayReturn", [tomorrow], 5)[0], update)
    changed.loc[changed.date == tomorrow, "intradayReturn"] = np.nan
    assert np.isnan(garch_horizons(state, changed, "intradayReturn", [frame.date.iloc[802]], 5)).all()
    with pytest.raises(ValueError, match="complete chronological"):
        fit_garch(changed, "intradayReturn", frame.date.iloc[802], cfg)


def test_risk_publication_deadline_immutability_and_hash(tmp_path):
    context = session_context("2026-11-04T01:00:00Z")
    assert publication_allowed(context, "2026-11-04T01:00:00Z")
    assert not publication_allowed(context, context["nextOpen"])
    assert not publication_allowed(context, context["close"] + pd.Timedelta(minutes=44))
    snapshot = {"informationCutoff": context["close"].isoformat(), "issuedAt": "2026-11-04T01:00:00Z",
                "entryOpen": context["nextOpen"].isoformat(), "exitClose": "2026-11-10T21:00:00Z", "probability": .1}
    path = tmp_path / "forecast.json"
    persist_forecast(path, snapshot, context, snapshot["issuedAt"])
    saved = json.loads(path.read_text())
    verify_forecast(saved)
    with pytest.raises(FileExistsError):
        persist_forecast(path, snapshot, context, snapshot["issuedAt"])
    saved["probability"] = .9
    with pytest.raises(ValueError, match="content hash"):
        verify_forecast(saved)
    late = copy.deepcopy(snapshot)
    late["issuedAt"] = context["nextOpen"].isoformat()
    with pytest.raises(ValueError, match="outside"):
        persist_forecast(tmp_path / "late.json", late, context, late["issuedAt"])
    assert not (tmp_path / "late.json").exists()
