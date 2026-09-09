from __future__ import annotations

import pandas as pd

from .kpis import calculate_kpis, machine_kpi_frame
from .scenarios import estimate_constraint_opportunity


def generate_insights(prod: pd.DataFrame, downtime: pd.DataFrame, machines: pd.DataFrame) -> list[dict]:
    """Generate management-facing insights with evidence, action and value.

    This is deliberately rules-based rather than an LLM: every statement is
    reproducible, traceable to the filtered data, and safe to demo offline.
    """
    if prod.empty:
        return [{
            "severity": "info", "title": "No data in selected scope",
            "impact": "No KPI can be calculated.", "driver": "Filters exclude all production orders.",
            "action": "Broaden the selected date, machine, product or shift filters.",
            "opportunity": "—",
        }]

    overall = calculate_kpis(prod)
    ms = machine_kpi_frame(prod, machines)
    insights: list[dict] = []

    if not ms.empty:
        worst = ms.iloc[0]
        gap_to_plant = (overall["oee"] - worst["oee"]) * 100.0
        gap_to_target = (worst["target_oee"] - worst["oee"]) * 100.0
        opp = estimate_constraint_opportunity(prod, machines)
        if gap_to_target > 2.0:
            insights.append({
                "severity": "high",
                "title": f"{worst['machine_id']} is the primary OEE constraint",
                "impact": f"OEE {worst['oee']:.1%} · {gap_to_plant:.1f} pp below plant average · {gap_to_target:.1f} pp below target.",
                "driver": "The constraint is dominated by availability loss rather than quality loss." if worst["availability"] < overall["availability"] - 0.03 else "Performance and quality losses compound the OEE gap.",
                "action": f"Prioritise root-cause work on {worst['machine_id']} before adding capacity elsewhere.",
                "opportunity": f"Target recovery scenario: ≈ +{opp['additional_good_units_month']:,.0f} good units/month and +€{opp['additional_margin_month']:,.0f} contribution/month.",
            })

        worst_scrap = ms.sort_values("scrap_rate", ascending=False).iloc[0]
        if worst_scrap["scrap_rate"] > overall["scrap_rate"] + 0.004:
            extra_scrap_pp = (worst_scrap["scrap_rate"] - overall["scrap_rate"]) * 100.0
            insights.append({
                "severity": "medium",
                "title": f"Quality loss is concentrated on {worst_scrap['machine_id']}",
                "impact": f"Scrap {worst_scrap['scrap_rate']:.1%} vs {overall['scrap_rate']:.1%} plant average (+{extra_scrap_pp:.1f} pp).",
                "driver": "Product mix and process stability should be separated before changing inspection limits.",
                "action": "Segment defects by product and defect type; validate first-off inspection and setup conditions.",
                "opportunity": "Reducing scrap to plant average directly protects material and conversion cost already incurred.",
            })

    if not downtime.empty:
        unplanned = downtime[~downtime["planned"].astype(bool)]
        if not unplanned.empty:
            by_reason = unplanned.groupby("reason", as_index=False)["duration_min"].sum().sort_values("duration_min", ascending=False)
            top = by_reason.iloc[0]
            share = float(top["duration_min"] / unplanned["duration_min"].sum())
            top_machine = (
                unplanned[unplanned["reason"] == top["reason"]]
                .groupby("machine_id")["duration_min"].sum().sort_values(ascending=False).index[0]
            )
            insights.append({
                "severity": "high" if share >= 0.15 else "medium",
                "title": f"Top downtime driver: {top['reason']}",
                "impact": f"{share:.1%} of unplanned downtime · concentrated most heavily on {top_machine}.",
                "driver": "A small number of recurring causes are consuming a disproportionate share of lost production time.",
                "action": f"Create a focused corrective-action plan for {top['reason']} and track recurrence after intervention.",
                "opportunity": "This is the highest-leverage downtime category in the current filter scope.",
            })

    # Shift comparison
    shift_rows = []
    for shift, g in prod.groupby("shift"):
        shift_rows.append((shift, calculate_kpis(g)["oee"]))
    if len(shift_rows) >= 2:
        s = pd.DataFrame(shift_rows, columns=["shift", "oee"]).sort_values("oee")
        gap = float((s.iloc[-1]["oee"] - s.iloc[0]["oee"]) * 100.0)
        if gap >= 1.0:
            insights.append({
                "severity": "medium",
                "title": f"Shift performance gap: {s.iloc[0]['shift']}",
                "impact": f"OEE {s.iloc[0]['oee']:.1%} vs {s.iloc[-1]['oee']:.1%} on {s.iloc[-1]['shift']} ({gap:.1f} pp gap).",
                "driver": "The pattern is consistent with differences in setup discipline, microstops or staffing routines.",
                "action": "Compare standard work, changeover sequence and first-hour losses between shifts.",
                "opportunity": "Replicating the stronger shift's operating standard can raise output without capital expenditure.",
            })

    # Product-level scrap concentration
    product_stats = []
    for product_id, g in prod.groupby("product_id"):
        product_stats.append((product_id, calculate_kpis(g)["scrap_rate"], int(g["scrap_qty"].sum())))
    if product_stats:
        ps = pd.DataFrame(product_stats, columns=["product_id", "scrap_rate", "scrap_qty"]).sort_values("scrap_rate", ascending=False)
        top = ps.iloc[0]
        if top["scrap_rate"] > overall["scrap_rate"] + 0.006:
            insights.append({
                "severity": "medium",
                "title": f"Product {top['product_id']} carries disproportionate quality risk",
                "impact": f"Scrap rate {top['scrap_rate']:.1%} · {int(top['scrap_qty']):,} scrap units in selected scope.",
                "driver": "The pattern can come from product sensitivity, material variation, fixture/setup or process capability.",
                "action": "Cross-filter this product by machine and defect family before selecting corrective action.",
                "opportunity": "A targeted reduction avoids broad process changes that may not address the true source of loss.",
            })

    if overall["schedule_attainment"] < 0.94:
        shortfall = int(max(overall["planned_qty"] - overall["good_qty"], 0))
        insights.append({
            "severity": "high",
            "title": "Plan attainment is below operating target",
            "impact": f"Good output is {overall['schedule_attainment']:.1%} of plan · shortfall ≈ {shortfall:,} units.",
            "driver": "The capacity loss is primarily operational; increasing plan load would amplify the gap.",
            "action": "Stabilise the constraint machine and top downtime losses before raising planned output.",
            "opportunity": "Recovering availability converts existing planned time into sellable output.",
        })

    severity_order = {"high": 0, "medium": 1, "info": 2}
    return sorted(insights, key=lambda x: severity_order.get(x["severity"], 9))[:5]
