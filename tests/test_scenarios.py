import pandas as pd

from src.scenarios import simulate_operational_scenario


def sample_df():
    return pd.DataFrame({
        "planned_minutes": [430.0, 430.0],
        "run_minutes": [340.0, 350.0],
        "ideal_cycle_time_s": [60.0, 60.0],
        "total_qty": [300, 315],
        "good_qty": [294, 308],
        "scrap_qty": [6, 7],
        "planned_qty": [360, 360],
        "production_cost_eur": [18000.0, 18800.0],
        "revenue_eur": [27000.0, 28200.0],
        "energy_kwh": [250.0, 260.0],
    })


def test_improvement_scenario_never_reduces_oee():
    result = simulate_operational_scenario(sample_df(), 5.0, 2.0, 0.5)
    assert result["scenario_oee"] > result["current_oee"]
    assert result["additional_good_units"] >= 0
    assert result["additional_revenue"] >= 0
    assert result["additional_gross_margin"] >= 0


def test_zero_scenario_is_close_to_current_operating_point():
    result = simulate_operational_scenario(sample_df(), 0.0, 0.0, 0.0)
    assert abs(result["scenario_oee"] - result["current_oee"]) < 1e-12
