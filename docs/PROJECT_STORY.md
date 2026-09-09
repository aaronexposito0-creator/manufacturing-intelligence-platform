# Project Story

## Positioning

Manufacturing Intelligence Platform is designed around the intersection of **engineering, process improvement, automation and analytics**.

The objective was to avoid a generic dashboard portfolio piece and instead build a compact product that resembles the way an industrial analyst or process engineer would work: verify the data, govern the metric, identify the constraint, investigate losses and quantify a response.

## Fictional plant

The dataset represents a six-asset discrete manufacturing facility with machining, cutting, welding and assembly operations. It contains production orders, downtime events and quality checks across January 2025 to August 2026.

## Deliberate analytical patterns

The generator contains business logic rather than independent random values:

- lower availability on the robotic welding asset;
- a persistent afternoon-shift penalty;
- a higher defect propensity on one final-assembly product;
- machine-specific downtime cause distributions;
- seasonal production demand;
- realistic manufacturing contribution economics.

These patterns make the analytics explainable and testable.

## Design philosophy

1. **Traceability over decoration.** Every KPI can be traced to source rows.
2. **Weighted metrics over convenience.** OEE is recomputed from components.
3. **Action over observation.** Insights include a next step and economic reason.
4. **Honest uncertainty.** Scenario outputs are labelled as sizing estimates, not forecasts.
5. **Reproducibility.** A fixed random seed, database rebuild script, automated tests and CI make the project repeatable.
