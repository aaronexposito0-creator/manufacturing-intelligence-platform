# Power BI Companion Guide

The Streamlit application is the public interactive demo. A Power BI companion version can reuse the same logical model.

## Recommended model

Dimensions:
- `dim_date`
- `dim_machine`
- `dim_product`

Facts:
- `fact_production`
- `fact_downtime`
- `fact_quality`

Use one-to-many relationships from dimensions into facts. Avoid joining fact tables directly.

## Core DAX measures

```DAX
Planned Minutes = SUM(fact_production[planned_minutes])
Run Minutes = SUM(fact_production[run_minutes])
Total Qty = SUM(fact_production[total_qty])
Good Qty = SUM(fact_production[good_qty])
Scrap Qty = SUM(fact_production[scrap_qty])
Planned Qty = SUM(fact_production[planned_qty])

Availability = DIVIDE([Run Minutes], [Planned Minutes])

Ideal Production Seconds =
SUMX(
    fact_production,
    fact_production[ideal_cycle_time_s] * fact_production[total_qty]
)

Performance = DIVIDE([Ideal Production Seconds], [Run Minutes] * 60)
Quality = DIVIDE([Good Qty], [Total Qty])
OEE = [Availability] * [Performance] * [Quality]
Scrap Rate = DIVIDE([Scrap Qty], [Total Qty])
Plan Attainment = DIVIDE([Good Qty], [Planned Qty])

Revenue = SUM(fact_production[revenue_eur])
Production Cost = SUM(fact_production[production_cost_eur])
Gross Margin = [Revenue] - [Production Cost]
Gross Margin % = DIVIDE([Gross Margin], [Revenue])
Unit Cost = DIVIDE([Production Cost], [Good Qty])
```

## Suggested pages

1. **Executive** — KPI cards, OEE by asset, plan trend, top insight callouts.
2. **Production** — throughput, plan attainment, product and shift comparisons.
3. **Quality** — Pareto, scrap trend, machine × product matrix.
4. **Downtime** — unplanned hours, Pareto and asset composition.
5. **Economics** — unit cost, gross margin and OEE vs cost.

## Important modelling point

Do not create `AVERAGE(fact_production[oee])`. OEE must be calculated from aggregated components in the current filter context.
