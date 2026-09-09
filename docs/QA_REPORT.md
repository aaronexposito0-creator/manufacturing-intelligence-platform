# QA Report — Portfolio Release 2.0

## Automated checks

`pytest -q` → **9 passed** during release build.

Coverage includes:

- weighted OEE calculation;
- scenario monotonicity;
- `good_qty + scrap_qty = total_qty`;
- run time never exceeds planned time;
- downtime-event minutes reconcile to work-order lost time within rounding tolerance;
- quality defect counts reconcile to work-order scrap;
- positive production economics;
- synthetic plant gross-margin rate remains inside the intended plausible range.

## Reproducibility

The synthetic generator uses fixed seed `20260909`. A release audit regenerated the CSV files twice and compared SHA-256 hashes; the generated datasets were identical.

## Default six-month analytical signal

The default window is expected to show:

- plant OEE in the mid-70% range;
- `M04` as **Critical** against its asset OEE target;
- `Fixture setup` as the leading unplanned downtime cause;
- plant gross-margin rate around one third;
- a positive recovery opportunity for `M04`;
- Morning shift outperforming Afternoon.

These are synthetic signals intentionally embedded by the deterministic generator. They are not real company results.

## Release checks performed

- Python sources compile successfully.
- Analytical database rebuild completes successfully.
- All SQL views return rows.
- Example analytical SQL executes against the generated database.
- Dataset generator produces identical output across repeated runs.
