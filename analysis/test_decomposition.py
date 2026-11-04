import math

import pytest

from analysis.variance_decomposition import decompose, loss_decomposition


def test_tail_share_uses_dates_and_exclusion_is_origin_year():
    rows = [("2020-01-02", 50.), ("2020-01-02", 50.)]
    rows += [(f"2021-{month:02d}-{day:02d}", 1.) for month in range(1, 5) for day in range(1, 26)]
    result = loss_decomposition(rows)
    assert result["dates"] == 101 and result["rows"] == 102
    assert result["worstDateCount"] == 2
    assert result["worstDateShare"] == pytest.approx(51 / 150)
    assert result["excluding2020MeanQLIKE"] == 1
    assert result["medianForecastQLIKE"] == result["medianDateQLIKE"] == 1


def test_qlike_ratio_direction_is_realized_over_forecast():
    result = decompose([{"date": "2020-06-04", "ticker": "XLK", "outcome": .001, "prediction": .00000001}])
    worst = result["worstForecasts"][0]
    assert worst["realizedOverPredicted"] == pytest.approx(100000)
    assert result["meanQLIKE"] == pytest.approx(100000 - math.log(100000) - 1)
