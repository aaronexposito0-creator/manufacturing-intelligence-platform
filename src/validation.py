from __future__ import annotations

import pandas as pd


class DataValidationError(ValueError):
    """Raised when a raw synthetic source violates the analytical contract."""


def _require_columns(df: pd.DataFrame, table: str, columns: set[str]) -> None:
    missing = columns.difference(df.columns)
    if missing:
        raise DataValidationError(f"{table}: missing required columns: {sorted(missing)}")


def validate_raw_data(
    production: pd.DataFrame,
    downtime: pd.DataFrame,
    quality: pd.DataFrame,
    machines: pd.DataFrame,
    products: pd.DataFrame,
) -> None:
    """Fail fast on structural, referential and reconciliation errors."""
    _require_columns(production, "fact_production", {
        "order_id", "date", "machine_id", "product_id", "planned_qty", "total_qty",
        "good_qty", "scrap_qty", "planned_minutes", "run_minutes", "production_cost_eur", "revenue_eur",
    })
    _require_columns(downtime, "fact_downtime", {"event_id", "order_id", "machine_id", "duration_min", "planned"})
    _require_columns(quality, "fact_quality", {"check_id", "order_id", "machine_id", "product_id", "defect_count"})
    _require_columns(machines, "dim_machine", {"machine_id", "target_oee"})
    _require_columns(products, "dim_product", {"product_id", "ideal_cycle_time_s", "sale_price_eur"})

    if production["order_id"].duplicated().any():
        raise DataValidationError("fact_production: order_id must be unique")
    if downtime["event_id"].duplicated().any():
        raise DataValidationError("fact_downtime: event_id must be unique")
    if quality["check_id"].duplicated().any():
        raise DataValidationError("fact_quality: check_id must be unique")

    if not (production["good_qty"] + production["scrap_qty"] == production["total_qty"]).all():
        raise DataValidationError("fact_production: good_qty + scrap_qty must equal total_qty")
    if not (production["run_minutes"] <= production["planned_minutes"] + 1e-9).all():
        raise DataValidationError("fact_production: run_minutes cannot exceed planned_minutes")

    numeric_nonnegative = [
        "planned_qty", "total_qty", "good_qty", "scrap_qty", "planned_minutes", "run_minutes",
        "production_cost_eur", "revenue_eur",
    ]
    if (production[numeric_nonnegative] < 0).any().any():
        raise DataValidationError("fact_production: negative operational/economic values found")

    order_ids = set(production["order_id"])
    machine_ids = set(machines["machine_id"])
    product_ids = set(products["product_id"])
    if not set(downtime["order_id"]).issubset(order_ids):
        raise DataValidationError("fact_downtime: orphan order_id detected")
    if not set(quality["order_id"]).issubset(order_ids):
        raise DataValidationError("fact_quality: orphan order_id detected")
    if not set(production["machine_id"]).issubset(machine_ids):
        raise DataValidationError("fact_production: unknown machine_id detected")
    if not set(production["product_id"]).issubset(product_ids):
        raise DataValidationError("fact_production: unknown product_id detected")

    expected_down = production.set_index("order_id").eval("planned_minutes - run_minutes")
    actual_down = downtime.groupby("order_id")["duration_min"].sum()
    reconciled_down = expected_down.to_frame("expected").join(actual_down.rename("actual"), how="left").fillna(0)
    if (reconciled_down["expected"] - reconciled_down["actual"]).abs().max() >= 0.08:
        raise DataValidationError("fact_downtime: event minutes do not reconcile to planned-run time loss")

    expected_scrap = production.set_index("order_id")["scrap_qty"]
    actual_defects = quality.groupby("order_id")["defect_count"].sum()
    reconciled_quality = expected_scrap.to_frame("scrap").join(actual_defects.rename("defects"), how="left").fillna(0)
    if not (reconciled_quality["scrap"] == reconciled_quality["defects"]).all():
        raise DataValidationError("fact_quality: defect counts do not reconcile to scrap_qty")
