# Data Dictionary

## `dim_machine`

| Field | Meaning |
|---|---|
| `machine_id` | Synthetic asset identifier |
| `machine_name` | Human-readable asset name |
| `area` | Manufacturing area |
| `model` | Synthetic equipment/model description |
| `commissioned_date` | Commissioning date |
| `target_availability` | Asset availability target |
| `target_oee` | Asset OEE target used by health classification |
| `energy_kw_nominal` | Nominal power used by the synthetic energy model |

## `dim_product`

| Field | Meaning |
|---|---|
| `product_id` | Synthetic product identifier |
| `product_name` | Human-readable product name |
| `family` | Product family |
| `ideal_cycle_time_s` | Ideal cycle time |
| `material_cost_eur` | Synthetic material cost per unit |
| `standard_cost_eur` | Synthetic standard variable cost per unit |
| `sale_price_eur` | Synthetic sale price per good unit |

## `fact_production`

One row per work order / shift / machine combination.

Key fields: `planned_qty`, `total_qty`, `good_qty`, `scrap_qty`, `planned_minutes`, `run_minutes`, `ideal_cycle_time_s`, `actual_cycle_time_s`, `energy_kwh`, `labor_hours`, `production_cost_eur`, `revenue_eur`.

## `fact_downtime`

One row per downtime event. `planned` distinguishes planned from unplanned loss. Event durations reconcile to the work-order time loss within rounding tolerance.

## `fact_quality`

Three synthetic quality records are generated per production order. Their `defect_count` values reconcile to work-order scrap quantity.

## `dim_date`

Calendar dimension with year, quarter, month, ISO week, weekday and weekend flag.
