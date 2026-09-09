# Case Study — From Plant Data to a Quantified Constraint Decision

## 1. Business problem

A synthetic discrete-manufacturing plant has six assets, multiple products, two shifts and fragmented operational records. Management needs a single view of production performance that can answer not only *what changed*, but *where to act first*.

## 2. Analytical design

The solution separates concerns:

- raw operational records in CSV;
- reproducible Python data generation / ETL;
- a SQLite analytical warehouse;
- reusable SQL views and Python KPI functions;
- an interactive Streamlit decision layer.

## 3. Metric design decision

OEE and other ratios are calculated from their additive components after filtering. Row-level OEE values are never averaged. This preserves correct weighting across different order sizes, cycle times and runtime durations.

## 4. Embedded operating signal

The synthetic generator creates a consistent constraint pattern on `M04` (robotic welding): lower availability, a 2026 deterioration, more fixture / robot recovery losses and an additional quality penalty.

The application therefore surfaces `M04` as the primary OEE constraint instead of relying on a manually hard-coded label.

## 5. Decision layer

The Executive Overview converts that operating signal into four fields:

- impact;
- likely driver;
- recommended action;
- estimated opportunity.

The opportunity model estimates the availability recovery required to reach the asset OEE target while holding observed performance and quality constant. It converts recovered output into observed gross contribution per good unit.

## 6. Scenario Lab

The what-if model lets a user independently change Availability, Performance and Scrap Rate for a selected asset. It recomputes expected output from planned minutes, weighted ideal cycle time and the scenario A/P/Q values.

The model is intentionally a controlled decision-support scenario, **not a demand forecast**.

## 7. Data assurance

Automated tests reconcile:

- good + scrap = total production;
- downtime-event minutes ≈ planned − run time;
- quality defect counts = scrap count;
- KPI calculations use weighted components;
- economics remain within a plausible synthetic margin range.

## 8. Result

The final product demonstrates a full analytics workflow: **operational data → model → KPI → diagnosis → quantified action → auditable evidence**.
