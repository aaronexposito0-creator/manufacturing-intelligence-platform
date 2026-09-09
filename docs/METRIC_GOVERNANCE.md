# Metric Governance

## Principle

All non-additive metrics are calculated at query / filter context from additive components. Do not average daily, order-level or machine-level OEE values to obtain plant OEE.

## OEE

`Availability = SUM(run_minutes) / SUM(planned_minutes)`

`Performance = SUM(ideal_cycle_time_s × total_qty) / (SUM(run_minutes) × 60)`

`Quality = SUM(good_qty) / SUM(total_qty)`

`OEE = Availability × Performance × Quality`

## Plan attainment

`SUM(good_qty) / SUM(planned_qty)`

Interpretation: sellable production completed versus planned production quantity.

## Unit cost

`SUM(production_cost_eur) / SUM(good_qty)`

The denominator is good output rather than total output so scrap and poor efficiency remain visible economically.

## Gross-margin rate

`(SUM(revenue_eur) - SUM(production_cost_eur)) / SUM(revenue_eur)`

This is a synthetic operational contribution metric; it is not intended to represent audited company EBITDA or net profit.

## Machine health

Each synthetic machine has an asset-specific `target_oee`.

- **Healthy:** OEE ≥ target
- **Watch:** target − 5 pp ≤ OEE < target
- **Critical:** OEE < target − 5 pp

## Opportunity model

Constraint recovery calculates the availability required to reach the target OEE while holding Performance and Quality constant:

`Required Availability = Target OEE / (Observed Performance × Observed Quality)`

Recovered output is valued using observed gross contribution per good unit. The result is a sizing estimate, not a guaranteed savings forecast.
