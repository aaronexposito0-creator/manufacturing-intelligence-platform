from __future__ import annotations

from dataclasses import dataclass
import math
import pandas as pd


def safe_div(num: float, den: float) -> float:
    if den is None or den == 0 or (isinstance(den, float) and math.isnan(den)):
        return 0.0
    return float(num / den)


def calculate_kpis(df: pd.DataFrame) -> dict[str, float]:
    """Calculate weighted manufacturing KPIs from production-order rows.

    Ratios are always recomputed from their additive components. This deliberately
    avoids the common BI error of averaging row-level percentages.
    """
    empty = {
        "availability": 0.0,
        "performance": 0.0,
        "quality": 0.0,
        "oee": 0.0,
        "scrap_rate": 0.0,
        "unit_cost": 0.0,
        "gross_margin": 0.0,
        "gross_margin_rate": 0.0,
        "schedule_attainment": 0.0,
        "energy_per_good_unit": 0.0,
        "revenue": 0.0,
        "production_cost": 0.0,
        "good_qty": 0.0,
        "planned_qty": 0.0,
        "total_qty": 0.0,
        "planned_minutes": 0.0,
        "run_minutes": 0.0,
    }
    if df.empty:
        return empty

    planned_minutes = float(df["planned_minutes"].sum())
    run_minutes = float(df["run_minutes"].sum())
    total_qty = float(df["total_qty"].sum())
    good_qty = float(df["good_qty"].sum())
    scrap_qty = float(df["scrap_qty"].sum())
    planned_qty = float(df["planned_qty"].sum())
    revenue = float(df["revenue_eur"].sum())
    production_cost = float(df["production_cost_eur"].sum())

    availability = safe_div(run_minutes, planned_minutes)
    performance = safe_div(float((df["ideal_cycle_time_s"] * df["total_qty"]).sum()), run_minutes * 60.0)
    quality = safe_div(good_qty, total_qty)
    oee = availability * performance * quality
    gross_margin = revenue - production_cost

    return {
        "availability": availability,
        "performance": performance,
        "quality": quality,
        "oee": oee,
        "scrap_rate": safe_div(scrap_qty, total_qty),
        "unit_cost": safe_div(production_cost, good_qty),
        "gross_margin": gross_margin,
        "gross_margin_rate": safe_div(gross_margin, revenue),
        "schedule_attainment": safe_div(good_qty, planned_qty),
        "energy_per_good_unit": safe_div(float(df["energy_kwh"].sum()), good_qty),
        "revenue": revenue,
        "production_cost": production_cost,
        "good_qty": good_qty,
        "planned_qty": planned_qty,
        "total_qty": total_qty,
        "planned_minutes": planned_minutes,
        "run_minutes": run_minutes,
    }


def add_row_kpis(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["availability"] = out["run_minutes"] / out["planned_minutes"].replace(0, pd.NA)
    out["performance"] = (out["ideal_cycle_time_s"] * out["total_qty"]) / (out["run_minutes"].replace(0, pd.NA) * 60.0)
    out["quality"] = out["good_qty"] / out["total_qty"].replace(0, pd.NA)
    out["oee"] = out["availability"] * out["performance"] * out["quality"]
    out["scrap_rate"] = out["scrap_qty"] / out["total_qty"].replace(0, pd.NA)
    out["unit_cost_eur"] = out["production_cost_eur"] / out["good_qty"].replace(0, pd.NA)
    out["gross_margin_eur"] = out["revenue_eur"] - out["production_cost_eur"]
    out["gross_margin_rate"] = out["gross_margin_eur"] / out["revenue_eur"].replace(0, pd.NA)
    return out


def metric_delta(current: float, previous: float, kind: str = "pp") -> float | None:
    """Return a comparable delta for Streamlit cards.

    kind='pp' -> percentage-point delta (0.01 = +1.0 pp)
    kind='pct' -> relative percent change (0.01 = +1.0%)
    kind='abs' -> absolute difference
    """
    if previous is None or (isinstance(previous, float) and math.isnan(previous)):
        return None
    if kind == "pp":
        return current - previous
    if kind == "pct":
        return safe_div(current - previous, abs(previous)) if previous != 0 else None
    return current - previous


def machine_kpi_frame(prod: pd.DataFrame, machines: pd.DataFrame | None = None) -> pd.DataFrame:
    rows: list[dict] = []
    if prod.empty:
        return pd.DataFrame(columns=["machine_id", "oee", "availability", "performance", "quality", "scrap_rate", "unit_cost", "good_qty"])

    target_map = {}
    if machines is not None and not machines.empty and "target_oee" in machines.columns:
        target_map = machines.set_index("machine_id")["target_oee"].to_dict()

    for machine_id, g in prod.groupby("machine_id"):
        k = calculate_kpis(g)
        target = float(target_map.get(machine_id, 0.80))
        gap = k["oee"] - target
        if gap >= 0:
            status = "Healthy"
        elif gap >= -0.05:
            status = "Watch"
        else:
            status = "Critical"
        rows.append({
            "machine_id": machine_id,
            "oee": k["oee"],
            "availability": k["availability"],
            "performance": k["performance"],
            "quality": k["quality"],
            "scrap_rate": k["scrap_rate"],
            "unit_cost": k["unit_cost"],
            "good_qty": k["good_qty"],
            "target_oee": target,
            "oee_gap": gap,
            "status": status,
        })
    return pd.DataFrame(rows).sort_values("oee")
