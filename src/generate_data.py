"""Deterministic synthetic manufacturing data generator.

The dataset is intentionally engineered to contain realistic operational patterns:
- M04 is the plant constraint (availability + welding recovery losses).
- P06 has a higher intrinsic defect risk.
- Afternoon shift performs slightly worse than Morning.
- demand has mild seasonality.
- cost economics are realistic enough for margin / unit-cost analysis.

No real employer data, customer data, or confidential information is used.
"""
from __future__ import annotations

from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SUMMARY_PATH = ROOT / "data" / "DATASET_SUMMARY.json"
SEED = 20260909


MACHINES = [
    {"machine_id": "M01", "machine_name": "CNC Milling 5-Axis", "area": "Machining", "model": "DMG MORI DMU 50", "commissioned_date": "2022-04-18", "target_availability": 0.90, "target_oee": 0.79, "energy_kw_nominal": 62.0, "base_availability": 0.895, "base_performance": 0.915},
    {"machine_id": "M02", "machine_name": "CNC Turning Center", "area": "Machining", "model": "Mazak QT-250", "commissioned_date": "2021-11-06", "target_availability": 0.89, "target_oee": 0.78, "energy_kw_nominal": 48.0, "base_availability": 0.878, "base_performance": 0.900},
    {"machine_id": "M03", "machine_name": "Laser Cutting Cell", "area": "Cutting", "model": "TRUMPF TruLaser 3030", "commissioned_date": "2023-02-15", "target_availability": 0.92, "target_oee": 0.81, "energy_kw_nominal": 71.0, "base_availability": 0.910, "base_performance": 0.930},
    {"machine_id": "M04", "machine_name": "Robotic Welding Cell", "area": "Welding", "model": "KUKA KR QUANTEC", "commissioned_date": "2020-08-27", "target_availability": 0.86, "target_oee": 0.76, "energy_kw_nominal": 55.0, "base_availability": 0.755, "base_performance": 0.875},
    {"machine_id": "M05", "machine_name": "Assembly Line A", "area": "Assembly", "model": "Custom Semi-Automatic", "commissioned_date": "2022-09-14", "target_availability": 0.90, "target_oee": 0.79, "energy_kw_nominal": 38.0, "base_availability": 0.885, "base_performance": 0.905},
    {"machine_id": "M06", "machine_name": "Assembly Line B", "area": "Assembly", "model": "Custom Semi-Automatic", "commissioned_date": "2024-01-11", "target_availability": 0.93, "target_oee": 0.82, "energy_kw_nominal": 41.0, "base_availability": 0.932, "base_performance": 0.925},
]

PRODUCTS = [
    {"product_id": "P01", "product_name": "AX-100 Housing", "family": "Aluminium housing", "ideal_cycle_time_s": 62.0, "material_cost_eur": 44.0, "standard_cost_eur": 60.0, "sale_price_eur": 94.0, "base_scrap": 0.015},
    {"product_id": "P02", "product_name": "AX-220 Shaft", "family": "Steel shaft", "ideal_cycle_time_s": 74.0, "material_cost_eur": 59.0, "standard_cost_eur": 80.0, "sale_price_eur": 126.0, "base_scrap": 0.020},
    {"product_id": "P03", "product_name": "BX-410 Bracket", "family": "Structural bracket", "ideal_cycle_time_s": 38.0, "material_cost_eur": 26.0, "standard_cost_eur": 35.5, "sale_price_eur": 56.0, "base_scrap": 0.012},
    {"product_id": "P04", "product_name": "CX-500 Frame", "family": "Welded frame", "ideal_cycle_time_s": 95.0, "material_cost_eur": 99.0, "standard_cost_eur": 134.0, "sale_price_eur": 210.0, "base_scrap": 0.020},
    {"product_id": "P05", "product_name": "DX-700 Cover", "family": "Composite cover", "ideal_cycle_time_s": 52.0, "material_cost_eur": 48.0, "standard_cost_eur": 65.0, "sale_price_eur": 102.0, "base_scrap": 0.023},
    {"product_id": "P06", "product_name": "EX-900 Module", "family": "Final assembly module", "ideal_cycle_time_s": 125.0, "material_cost_eur": 139.0, "standard_cost_eur": 190.0, "sale_price_eur": 298.0, "base_scrap": 0.036},
]

COMPATIBILITY = {
    "M01": ["P01", "P02", "P03"],
    "M02": ["P01", "P02", "P05"],
    "M03": ["P01", "P03", "P05"],
    "M04": ["P03", "P04", "P06"],
    "M05": ["P01", "P04", "P05", "P06"],
    "M06": ["P01", "P04", "P05", "P06"],
}

DEFECT_TYPES = ["Dimensional", "Surface finish", "Assembly mismatch", "Weld porosity", "Material defect", "Cosmetic"]
GENERAL_UNPLANNED = [
    ("Breakdown", "Mechanical fault"),
    ("Breakdown", "Sensor fault"),
    ("Microstop", "Vision retry"),
    ("Microstop", "Material jam"),
    ("Changeover", "Tooling change"),
    ("Process", "Parameter adjustment"),
    ("Material", "Material shortage"),
]
M04_UNPLANNED = [
    ("Changeover", "Fixture setup"),
    ("Breakdown", "Robot recovery"),
    ("Process", "Weld parameter adjustment"),
    ("Microstop", "Torch cleaning"),
    ("Breakdown", "Wire feeder fault"),
]
M04_REASON_WEIGHTS = [0.50, 0.22, 0.11, 0.09, 0.08]
PLANNED_REASONS = [
    ("Planned", "Preventive maintenance"),
    ("Planned", "Calibration"),
    ("Changeover", "Planned changeover"),
]


def _seasonality(ts: pd.Timestamp) -> float:
    # Mild demand seasonality: low August / December, stronger spring and Q4.
    month_factor = {1: 0.96, 2: 1.00, 3: 1.05, 4: 1.07, 5: 1.05, 6: 1.02,
                    7: 0.98, 8: 0.84, 9: 1.03, 10: 1.08, 11: 1.10, 12: 0.90}
    return month_factor[ts.month]


def _split_downtime(rng: np.random.Generator, total: float, n: int) -> list[float]:
    if n <= 1:
        return [round(max(total, 1.0), 2)]
    weights = rng.dirichlet(np.ones(n))
    values = np.maximum(weights * total, 1.0)
    # rescale to keep exact total after the floor
    values = values / values.sum() * total
    return [round(float(v), 2) for v in values]


def generate_dataset() -> dict:
    rng = np.random.default_rng(SEED)
    RAW.mkdir(parents=True, exist_ok=True)

    machines_df = pd.DataFrame(MACHINES).drop(columns=["base_availability", "base_performance"])
    products_df = pd.DataFrame(PRODUCTS).drop(columns=["base_scrap"])
    machines_df.to_csv(RAW / "machines.csv", index=False)
    products_df.to_csv(RAW / "products.csv", index=False)

    machine_cfg = {m["machine_id"]: m for m in MACHINES}
    product_cfg = {p["product_id"]: p for p in PRODUCTS}

    orders: list[dict] = []
    downtimes: list[dict] = []
    quality_rows: list[dict] = []
    order_no = 1
    dt_no = 1
    qc_no = 1

    # Weekdays only: two production shifts per machine.
    for date in pd.bdate_range("2025-01-01", "2026-08-31"):
        for machine_id in [m["machine_id"] for m in MACHINES]:
            m = machine_cfg[machine_id]
            for shift in ["Morning", "Afternoon"]:
                # A small amount of planned idle capacity keeps the dataset realistic.
                if rng.random() < (0.025 if date.month != 8 else 0.08):
                    continue

                product_id = str(rng.choice(COMPATIBILITY[machine_id]))
                p = product_cfg[product_id]
                planned_minutes = 430.0

                shift_penalty = 0.018 if shift == "Afternoon" else 0.0
                # M04 deteriorates further in 2026 to create a clear constraint narrative.
                constraint_penalty = 0.018 if (machine_id == "M04" and date >= pd.Timestamp("2026-03-01")) else 0.0
                availability = np.clip(
                    m["base_availability"] - shift_penalty - constraint_penalty + rng.normal(0, 0.025),
                    0.58, 0.97,
                )
                performance = np.clip(
                    m["base_performance"] - (0.012 if shift == "Afternoon" else 0.0) + rng.normal(0, 0.018),
                    0.72, 0.98,
                )

                scrap_rate = p["base_scrap"]
                if machine_id == "M04":
                    scrap_rate += 0.008
                if shift == "Afternoon":
                    scrap_rate += 0.0025
                # P06 gets a modest quality drift in 2026 to make the quality analysis meaningful.
                if product_id == "P06" and date >= pd.Timestamp("2026-04-01"):
                    scrap_rate += 0.006
                scrap_rate = float(np.clip(scrap_rate + rng.normal(0, 0.004), 0.004, 0.085))

                run_minutes = planned_minutes * availability
                capacity_at_ideal = planned_minutes * 60.0 / p["ideal_cycle_time_s"]
                total_qty = max(1, int(round((run_minutes * 60.0 / p["ideal_cycle_time_s"]) * performance)))
                scrap_qty = int(round(total_qty * scrap_rate))
                scrap_qty = min(scrap_qty, total_qty - 1)
                good_qty = total_qty - scrap_qty

                demand = _seasonality(date) * (1.0 + rng.normal(0, 0.035))
                planned_qty = max(1, int(round(capacity_at_ideal * 0.88 * demand)))

                actual_cycle_time_s = (run_minutes * 60.0 / total_qty) if total_qty else p["ideal_cycle_time_s"]
                load_factor = float(np.clip(0.70 + 0.20 * performance + rng.normal(0, 0.025), 0.62, 0.98))
                energy_kwh = (run_minutes / 60.0) * m["energy_kw_nominal"] * load_factor
                labor_hours = planned_minutes / 60.0
                material_cost_total = total_qty * p["material_cost_eur"]
                maintenance_cost = float(max(12.0, rng.gamma(2.0, 20.0) + (55.0 if machine_id == "M04" else 0.0)))
                energy_cost = energy_kwh * 0.145
                fixed_shift_overhead = labor_hours * 82.0
                base_variable_cost = total_qty * p["standard_cost_eur"]
                production_cost = base_variable_cost + fixed_shift_overhead + energy_cost + maintenance_cost
                revenue = good_qty * p["sale_price_eur"]

                order_id = f"WO-{order_no:06d}"
                orders.append({
                    "order_id": order_id,
                    "date": date.date().isoformat(),
                    "month": date.strftime("%Y-%m"),
                    "iso_week": f"{date.isocalendar().year}-W{date.isocalendar().week:02d}",
                    "shift": shift,
                    "machine_id": machine_id,
                    "product_id": product_id,
                    "planned_qty": planned_qty,
                    "total_qty": total_qty,
                    "good_qty": good_qty,
                    "scrap_qty": scrap_qty,
                    "planned_minutes": round(planned_minutes, 2),
                    "run_minutes": round(float(run_minutes), 2),
                    "ideal_cycle_time_s": p["ideal_cycle_time_s"],
                    "actual_cycle_time_s": round(float(actual_cycle_time_s), 2),
                    "energy_kwh": round(float(energy_kwh), 2),
                    "labor_hours": round(float(labor_hours), 2),
                    "material_cost_eur": round(float(material_cost_total), 2),
                    "energy_cost_eur": round(float(energy_cost), 2),
                    "maintenance_cost_eur": round(float(maintenance_cost), 2),
                    "production_cost_eur": round(float(production_cost), 2),
                    "revenue_eur": round(float(revenue), 2),
                })

                # Downtime events reconcile to the order's planned - run time.
                total_downtime = max(planned_minutes - run_minutes, 0.5)
                n_events = int(np.clip(rng.poisson(1.4) + 1, 1, 5))
                durations = _split_downtime(rng, float(total_downtime), n_events)
                for duration in durations:
                    planned_event = bool(rng.random() < 0.16)
                    if planned_event:
                        category, reason = PLANNED_REASONS[int(rng.integers(0, len(PLANNED_REASONS)))]
                    else:
                        if machine_id == "M04" and rng.random() < 0.78:
                            choice = int(rng.choice(len(M04_UNPLANNED), p=M04_REASON_WEIGHTS))
                            category, reason = M04_UNPLANNED[choice]
                        else:
                            category, reason = GENERAL_UNPLANNED[int(rng.integers(0, len(GENERAL_UNPLANNED)))]
                    downtimes.append({
                        "event_id": f"DT-{dt_no:07d}",
                        "order_id": order_id,
                        "date": date.date().isoformat(),
                        "shift": shift,
                        "machine_id": machine_id,
                        "category": category,
                        "reason": reason,
                        "duration_min": duration,
                        "planned": int(planned_event),
                    })
                    dt_no += 1

                # Allocate observed scrap across three inspection records.
                selected_defects = list(rng.choice(DEFECT_TYPES, size=3, replace=False))
                if scrap_qty > 0:
                    shares = rng.multinomial(scrap_qty, [0.58, 0.27, 0.15])
                else:
                    shares = [0, 0, 0]
                # Welding-heavy products / M04 make weld porosity more likely.
                if machine_id == "M04" and "Weld porosity" not in selected_defects:
                    selected_defects[0] = "Weld porosity"
                for defect_type, defect_count in zip(selected_defects, shares):
                    quality_rows.append({
                        "check_id": f"QC-{qc_no:07d}",
                        "order_id": order_id,
                        "date": date.date().isoformat(),
                        "machine_id": machine_id,
                        "product_id": product_id,
                        "defect_type": defect_type,
                        "defect_count": int(defect_count),
                        "result": "FAIL" if defect_count > 0 else "PASS",
                    })
                    qc_no += 1

                order_no += 1

    orders_df = pd.DataFrame(orders)
    downtime_df = pd.DataFrame(downtimes)
    quality_df = pd.DataFrame(quality_rows)

    orders_df.to_csv(RAW / "production_orders.csv", index=False)
    downtime_df.to_csv(RAW / "downtime_events.csv", index=False)
    quality_df.to_csv(RAW / "quality_checks.csv", index=False)

    summary = {
        "seed": SEED,
        "production_orders": int(len(orders_df)),
        "downtime_events": int(len(downtime_df)),
        "quality_checks": int(len(quality_df)),
        "machines": int(len(machines_df)),
        "products": int(len(products_df)),
        "date_min": str(orders_df["date"].min()),
        "date_max": str(orders_df["date"].max()),
        "synthetic": True,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    result = generate_dataset()
    print(json.dumps(result, indent=2))
