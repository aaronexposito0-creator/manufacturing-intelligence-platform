-- Example 1: identify assets below their target OEE.
SELECT
    machine_id,
    machine_name,
    ROUND(oee * 100, 1) AS oee_pct,
    ROUND(target_oee * 100, 1) AS target_oee_pct,
    ROUND((oee - target_oee) * 100, 1) AS gap_pp,
    status
FROM vw_machine_health
ORDER BY gap_pp ASC;

-- Example 2: Pareto of unplanned downtime causes.
WITH losses AS (
    SELECT reason, SUM(duration_min) AS minutes
    FROM fact_downtime
    WHERE planned = 0
    GROUP BY reason
), ranked AS (
    SELECT
        reason,
        minutes,
        minutes / SUM(minutes) OVER () AS share,
        SUM(minutes) OVER (ORDER BY minutes DESC ROWS UNBOUNDED PRECEDING)
            / SUM(minutes) OVER () AS cumulative_share
    FROM losses
)
SELECT
    reason,
    ROUND(minutes / 60.0, 1) AS hours,
    ROUND(share * 100, 1) AS share_pct,
    ROUND(cumulative_share * 100, 1) AS cumulative_pct
FROM ranked
ORDER BY minutes DESC;

-- Example 3: monthly operational economics.
SELECT
    month,
    good_qty,
    planned_qty,
    ROUND(plan_attainment * 100, 1) AS plan_attainment_pct,
    ROUND(revenue_eur, 0) AS revenue_eur,
    ROUND(production_cost_eur, 0) AS production_cost_eur,
    ROUND(gross_margin_rate * 100, 1) AS gross_margin_pct
FROM vw_monthly_business_kpis
ORDER BY month;
