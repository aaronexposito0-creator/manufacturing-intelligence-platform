from pathlib import Path
import sqlite3
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "manufacturing.db"


def load_tables():
    conn = sqlite3.connect(DB)
    prod = pd.read_sql("SELECT * FROM fact_production", conn)
    down = pd.read_sql("SELECT * FROM fact_downtime", conn)
    qual = pd.read_sql("SELECT * FROM fact_quality", conn)
    conn.close()
    return prod, down, qual


def test_production_conservation_and_bounds():
    prod, _, _ = load_tables()
    assert (prod["good_qty"] + prod["scrap_qty"] == prod["total_qty"]).all()
    assert (prod["run_minutes"] <= prod["planned_minutes"] + 1e-9).all()
    assert (prod["good_qty"] > 0).all()
    assert (prod["revenue_eur"] > 0).all()
    assert (prod["production_cost_eur"] > 0).all()


def test_downtime_reconciles_to_time_loss():
    prod, down, _ = load_tables()
    expected = prod.set_index("order_id").eval("planned_minutes - run_minutes")
    actual = down.groupby("order_id")["duration_min"].sum()
    aligned = expected.to_frame("expected").join(actual.rename("actual"), how="left").fillna(0)
    # Event-level rounding can create a few hundredths of a minute difference.
    assert (aligned["expected"] - aligned["actual"]).abs().max() < 0.08


def test_quality_defect_counts_reconcile_to_scrap():
    prod, _, qual = load_tables()
    expected = prod.set_index("order_id")["scrap_qty"]
    actual = qual.groupby("order_id")["defect_count"].sum()
    aligned = expected.to_frame("scrap").join(actual.rename("defects"), how="left").fillna(0)
    assert (aligned["scrap"] == aligned["defects"]).all()


def test_factory_margin_is_plausible_for_demo_dataset():
    prod, _, _ = load_tables()
    revenue = prod["revenue_eur"].sum()
    margin_rate = (revenue - prod["production_cost_eur"].sum()) / revenue
    assert 0.20 < margin_rate < 0.45
