import pandas as pd
import pytest

from src.kpis import add_row_kpis, calculate_kpis, safe_div


def test_safe_div_handles_zero():
    assert safe_div(10, 0) == 0.0
    assert safe_div(10, None) == 0.0


def test_weighted_oee_is_recomputed_from_components():
    df = pd.DataFrame({
        "planned_minutes": [100.0, 300.0],
        "run_minutes": [80.0, 240.0],
        "ideal_cycle_time_s": [60.0, 30.0],
        "total_qty": [72, 432],
        "good_qty": [70, 420],
        "scrap_qty": [2, 12],
        "planned_qty": [80, 460],
        "production_cost_eur": [3500.0, 18000.0],
        "revenue_eur": [5000.0, 27000.0],
        "energy_kwh": [100.0, 300.0],
    })
    k = calculate_kpis(df)
    expected_availability = 320 / 400
    expected_performance = ((60 * 72) + (30 * 432)) / (320 * 60)
    expected_quality = 490 / 504
    assert k["availability"] == pytest.approx(expected_availability)
    assert k["performance"] == pytest.approx(expected_performance)
    assert k["quality"] == pytest.approx(expected_quality)
    assert k["oee"] == pytest.approx(expected_availability * expected_performance * expected_quality)


def test_row_kpis_add_expected_columns():
    df = pd.DataFrame({
        "planned_minutes": [100.0], "run_minutes": [80.0], "ideal_cycle_time_s": [60.0],
        "total_qty": [72], "good_qty": [70], "scrap_qty": [2],
        "production_cost_eur": [3500.0], "revenue_eur": [5000.0],
    })
    out = add_row_kpis(df)
    for col in ["availability", "performance", "quality", "oee", "scrap_rate", "unit_cost_eur", "gross_margin_eur", "gross_margin_rate"]:
        assert col in out.columns
