from __future__ import annotations

from pathlib import Path
import sqlite3
import pandas as pd

try:
    from src.validation import validate_raw_data
except ModuleNotFoundError:  # Allows `python src/build_database.py` from repo root.
    from validation import validate_raw_data

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "processed" / "manufacturing.db"


def _build_date_dimension(min_date: str, max_date: str) -> pd.DataFrame:
    dates = pd.date_range(min_date, max_date, freq="D")
    iso = dates.isocalendar()
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "year": dates.year,
        "quarter": "Q" + dates.quarter.astype(str),
        "month": dates.strftime("%Y-%m"),
        "month_name": dates.strftime("%b"),
        "iso_week": iso["year"].astype(str).to_numpy() + "-W" + iso["week"].astype(str).str.zfill(2).to_numpy(),
        "weekday": dates.strftime("%A"),
        "weekday_number": dates.weekday + 1,
        "is_weekend": (dates.weekday >= 5).astype(int),
    })


def build_database() -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    production = pd.read_csv(RAW / "production_orders.csv")
    downtime = pd.read_csv(RAW / "downtime_events.csv")
    quality = pd.read_csv(RAW / "quality_checks.csv")
    machines = pd.read_csv(RAW / "machines.csv")
    products = pd.read_csv(RAW / "products.csv")
    validate_raw_data(production, downtime, quality, machines, products)
    dim_date = _build_date_dimension(production["date"].min(), production["date"].max())

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    machines.to_sql("dim_machine", conn, if_exists="replace", index=False)
    products.to_sql("dim_product", conn, if_exists="replace", index=False)
    dim_date.to_sql("dim_date", conn, if_exists="replace", index=False)
    production.to_sql("fact_production", conn, if_exists="replace", index=False)
    downtime.to_sql("fact_downtime", conn, if_exists="replace", index=False)
    quality.to_sql("fact_quality", conn, if_exists="replace", index=False)
    conn.executescript((ROOT / "sql" / "01_schema.sql").read_text(encoding="utf-8"))
    conn.executescript((ROOT / "sql" / "02_views.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    print(f"Database rebuilt: {DB}")


if __name__ == "__main__":
    build_database()
