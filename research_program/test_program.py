from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from unpriced.controls import synthetic_market
from unpriced.io import config

from research_program.macro import MacroUnavailable, asof_series, download_vintages
from research_program.panel import columns, make_panel, resolved_history
from research_program.pretrained import probability_above
from research_program.reporting import paired
from research_program.selection import fit_selected, partitions, predict_selected


@pytest.fixture(scope="module")
def sample():
    registry = json.loads((Path(__file__).parent / "registry.json").read_text())
    cfg = config()
    data = synthetic_market(cfg, 37, sessions=1500)
    return cfg, registry, data, make_panel(data, cfg, registry)


def test_nested_selection_and_calibration_are_purged_by_date(sample):
    cfg, registry, _, frame = sample
    features = columns("excess", "market", cfg, registry)
    asof = frame.date.max()
    train, calibration, folds = partitions(frame, asof, features, "excess", registry)
    assert train.labelEnd.max() < calibration.date.min()
    assert calibration.labelEnd.max() <= asof
    for fitting, validation in folds:
        assert fitting.labelEnd.max() < validation.date.min()
        assert validation.labelEnd.max() < calibration.date.min()
        assert set(fitting.date).isdisjoint(validation.date)
        assert validation.groupby("date").ticker.nunique().min() == len(cfg["universe"])


def test_future_outcomes_cannot_change_selection_or_forecast(sample):
    cfg, registry, _, frame = sample
    asof = sorted(frame.date.unique())[-100]
    features = columns("excess", "market", cfg, registry)
    first = fit_selected(frame, asof, features, "excess", registry)
    altered = frame.copy()
    altered.loc[altered.labelEnd > asof, "outcome"] = 1 - altered.loc[altered.labelEnd > asof, "outcome"]
    second = fit_selected(altered, asof, features, "excess", registry)
    assert first["metadata"] == second["metadata"]
    np.testing.assert_allclose(predict_selected(first, frame[frame.date == asof]).prediction,
                               predict_selected(second, altered[altered.date == asof]).prediction)
    # Unresolved or unavailable future outcomes must not suppress a forecast.
    current = frame[frame.date == asof].copy()
    current["outcome"] = np.nan
    assert len(predict_selected(first, current)) == len(cfg["universe"])


def test_vintages_wait_until_next_session_and_old_revisions_do_not_replace_latest():
    sessions = pd.DatetimeIndex(["2020-02-03", "2020-02-04", "2020-02-05", "2020-02-06"])
    rows = [{"date": "2020-01-01", "realtime_start": "2020-02-03", "value": "1"},
            {"date": "2020-02-01", "realtime_start": "2020-02-04", "value": "2"},
            {"date": "2020-01-01", "realtime_start": "2020-02-05", "value": "999"}]
    values = asof_series(rows, sessions, 100)
    assert pd.isna(values.loc["2020-02-03", "value"])
    assert values.loc["2020-02-04", "value"] == 1
    assert values.loc["2020-02-05", "value"] == 2
    assert values.loc["2020-02-06", "value"] == 2
    future = rows + [{"date": "2020-02-01", "realtime_start": "2020-02-06", "value": "1000"}]
    pd.testing.assert_frame_equal(values, asof_series(future, sessions, 100))


def test_macro_missing_and_stale_values_are_not_filled(monkeypatch, sample):
    _, registry, _, _ = sample
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(MacroUnavailable, match="absent"):
        download_vintages(registry["macro"])
    rows = [{"date": "2020-01-01", "realtime_start": "2020-01-01", "value": "1"},
            {"date": "2020-01-01", "realtime_start": "2020-01-03", "value": "."}]
    dates = pd.DatetimeIndex(["2020-01-02", "2020-01-06", "2020-02-01"])
    values = asof_series(rows, dates, 10)
    assert values.iloc[0].value == 1
    assert values.iloc[1:].value.isna().all()


def test_drawdown_is_path_dependent_and_missing_path_abstains(sample):
    cfg, registry, data, frame = sample
    date = pd.Timestamp("2013-01-18")
    source = frame[(frame.date == date) & (frame.ticker == "XLK")].iloc[0]
    future = sorted(frame.loc[(frame.date >= source.entryDate) & (frame.date <= source.labelEnd), "date"].unique())
    changed = data.copy()
    changed.loc[(changed.ticker == "XLK") & (changed.date == source.entryDate), "open"] = 100
    for day, value in zip(future, [110, 100, 99, 100, 105]):
        changed.loc[(changed.ticker == "XLK") & (changed.date == day), "close"] = value
    rebuilt = make_panel(changed, cfg, registry)
    value = rebuilt[(rebuilt.date == date) & (rebuilt.ticker == "XLK")].iloc[0]
    assert value.drawdownSeverity == pytest.approx(.1)
    assert value.drawdownEvent == 1
    changed = changed[~((changed.ticker == "XLK") & (changed.date == future[2]))]
    rebuilt = make_panel(changed, cfg, registry)
    assert pd.isna(rebuilt[(rebuilt.date == date) & (rebuilt.ticker == "XLK")].iloc[0].drawdownSeverity)


def test_pretrained_context_uses_matured_targets_and_keeps_session_slots(sample):
    _, _, _, frame = sample
    asof = pd.Timestamp(sorted(frame.date.unique())[-100])
    before = resolved_history(frame, "XLK", "excess", asof, 512)
    altered = frame.copy()
    altered.loc[altered.labelEnd > asof, "excessReturn"] = 999
    after = resolved_history(altered, "XLK", "excess", asof, 512)
    np.testing.assert_allclose(before, after, equal_nan=True)
    known = altered[(altered.ticker == "XLK") & (altered.labelEnd == asof)].index
    altered.loc[known, "excessReturn"] = np.nan
    missing = resolved_history(altered, "XLK", "excess", asof, 512)
    assert len(missing) == 512
    assert np.isnan(missing[-1])
    np.testing.assert_allclose(before[:-1], missing[:-1], equal_nan=True)


def test_fifth_pretrained_step_matches_the_declared_holding_window(sample):
    _, _, _, frame = sample
    asof = pd.Timestamp("2013-01-18")
    source = frame[(frame.date == asof) & (frame.ticker == "XLK")].iloc[0]
    for task, field in [("excess", "excessReturn"), ("drawdown", "drawdownSeverity")]:
        # Once the fifth following exchange session ends, its completed-target
        # series contains exactly this decision's outcome at the final slot.
        historical = resolved_history(frame, "XLK", task, source.labelEnd, 512)
        assert historical[-1] == pytest.approx(source[field])
    assert source.labelEnd == pd.Timestamp("2013-01-28")


def test_pairing_rejects_inconsistent_outcomes_and_reports_intersection(sample):
    _, registry, _, _ = sample
    a = pd.DataFrame({"date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                      "ticker": ["XLK", "XLE"], "entryDate": pd.to_datetime(["2024-01-03", "2024-01-04"]),
                      "labelEnd": pd.to_datetime(["2024-01-09", "2024-01-10"]),
                      "outcome": [1., 0.], "prediction": [.5, .5]})
    b = a.iloc[:1].copy()
    score = paired(a, b, "excess", pd.DatetimeIndex(a.date), registry)
    assert score["pairedRows"] == 1
    b["outcome"] = 0
    with pytest.raises(ValueError, match="disagree"):
        paired(a, b, "excess", pd.DatetimeIndex(a.date), registry)


def test_quantile_probability_uses_right_continuous_atom():
    assert probability_above([0, 0, 1], [.1, .5, .9], 0) == pytest.approx(.5)
    assert probability_above([-1, 0, 1], [.1, .5, .9], 0) == pytest.approx(.5)
