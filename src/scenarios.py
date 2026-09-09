from __future__ import annotations

import math
import pandas as pd

from .kpis import calculate_kpis, safe_div


def _weighted_ideal_cycle_seconds(df: pd.DataFrame) -> float:
    total = float(df["total_qty"].sum())
    return safe_div(float((df["ideal_cycle_time_s"] * df["total_qty"]).sum()), total)


def simulate_operational_scenario(
    prod: pd.DataFrame,
    availability_delta_pp: float = 0.0,
    performance_delta_pp: float = 0.0,
    scrap_reduction_pp: float = 0.0,
) -> dict[str, float]:
    """Deterministic what-if scenario for a fixed production plan.

    The scenario does not forecast demand. It asks: if the same planned production
    minutes and product mix were run with better A/P/Q, what output and contribution
    could the selected scope plausibly produce?
    """
    if prod.empty:
        return {
            "current_oee": 0.0, "scenario_oee": 0.0, "additional_good_units": 0.0,
            "additional_revenue": 0.0, "additional_gross_margin": 0.0,
            "scenario_availability": 0.0, "scenario_performance": 0.0,
            "scenario_quality": 0.0,
        }

    k = calculate_kpis(prod)
    availability = min(max(k["availability"] + availability_delta_pp / 100.0, 0.0), 0.995)
    performance = min(max(k["performance"] + performance_delta_pp / 100.0, 0.0), 0.995)
    new_scrap = min(max(k["scrap_rate"] - scrap_reduction_pp / 100.0, 0.0), 0.20)
    quality = 1.0 - new_scrap
    scenario_oee = availability * performance * quality

    ideal_s = _weighted_ideal_cycle_seconds(prod)
    theoretical_total = safe_div(k["planned_minutes"] * 60.0, ideal_s)
    scenario_total = theoretical_total * availability * performance
    scenario_good = scenario_total * quality
    additional_good = max(0.0, scenario_good - k["good_qty"])

    avg_revenue_per_good = safe_div(k["revenue"], k["good_qty"])
    current_margin_per_good = safe_div(k["gross_margin"], k["good_qty"])

    return {
        "current_oee": k["oee"],
        "scenario_oee": scenario_oee,
        "additional_good_units": additional_good,
        "additional_revenue": additional_good * avg_revenue_per_good,
        # Conservative: use observed contribution/good unit instead of assuming all revenue is profit.
        "additional_gross_margin": additional_good * current_margin_per_good,
        "scenario_availability": availability,
        "scenario_performance": performance,
        "scenario_quality": quality,
    }


def estimate_constraint_opportunity(prod: pd.DataFrame, machines: pd.DataFrame) -> dict[str, float | str]:
    """Estimate the value of bringing the worst machine back to its OEE target.

    The target is converted into the availability needed while holding observed
    performance and quality constant. Opportunity is normalised to a 30.4-day month.
    """
    if prod.empty:
        return {"machine_id": "—", "additional_good_units_month": 0.0, "additional_margin_month": 0.0, "target_oee": 0.0, "current_oee": 0.0, "availability_delta_pp": 0.0}

    machine_rows = []
    target_map = machines.set_index("machine_id")["target_oee"].to_dict() if "target_oee" in machines.columns else {}
    for machine_id, g in prod.groupby("machine_id"):
        k = calculate_kpis(g)
        target = float(target_map.get(machine_id, 0.80))
        machine_rows.append((machine_id, k["oee"], target, g))
    machine_id, current_oee, target_oee, g = sorted(machine_rows, key=lambda x: x[1] - x[2])[0]
    k = calculate_kpis(g)

    required_availability = min(0.98, safe_div(target_oee, k["performance"] * k["quality"]))
    availability_delta_pp = max(0.0, (required_availability - k["availability"]) * 100.0)
    scenario = simulate_operational_scenario(g, availability_delta_pp=availability_delta_pp)

    days = max(1, int((pd.to_datetime(g["date"]).max() - pd.to_datetime(g["date"]).min()).days) + 1)
    month_factor = 30.4 / days

    return {
        "machine_id": machine_id,
        "current_oee": current_oee,
        "target_oee": target_oee,
        "availability_delta_pp": availability_delta_pp,
        "additional_good_units_month": scenario["additional_good_units"] * month_factor,
        "additional_margin_month": scenario["additional_gross_margin"] * month_factor,
    }
