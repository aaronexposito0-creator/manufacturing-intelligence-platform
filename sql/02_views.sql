DROP VIEW IF EXISTS vw_order_kpis;
CREATE VIEW vw_order_kpis AS
SELECT
    p.*,
    CASE WHEN planned_minutes > 0 THEN run_minutes / planned_minutes END AS availability,
    CASE WHEN run_minutes > 0 THEN (ideal_cycle_time_s * total_qty) / (run_minutes * 60.0) END AS performance,
    CASE WHEN total_qty > 0 THEN good_qty * 1.0 / total_qty END AS quality,
    CASE WHEN planned_minutes > 0 AND run_minutes > 0 AND total_qty > 0
         THEN (run_minutes / planned_minutes)
            * ((ideal_cycle_time_s * total_qty) / (run_minutes * 60.0))
            * (good_qty * 1.0 / total_qty)
    END AS oee,
    CASE WHEN good_qty > 0 THEN production_cost_eur / good_qty END AS unit_cost_eur,
    CASE WHEN total_qty > 0 THEN scrap_qty * 1.0 / total_qty END AS scrap_rate,
    revenue_eur - production_cost_eur AS gross_margin_eur,
    CASE WHEN revenue_eur > 0 THEN (revenue_eur - production_cost_eur) / revenue_eur END AS gross_margin_rate
FROM fact_production p;

DROP VIEW IF EXISTS vw_daily_machine_kpis;
CREATE VIEW vw_daily_machine_kpis AS
SELECT
    p.date,
    p.machine_id,
    SUM(planned_qty) AS planned_qty,
    SUM(total_qty) AS total_qty,
    SUM(good_qty) AS good_qty,
    SUM(scrap_qty) AS scrap_qty,
    SUM(planned_minutes) AS planned_minutes,
    SUM(run_minutes) AS run_minutes,
    SUM(energy_kwh) AS energy_kwh,
    SUM(production_cost_eur) AS production_cost_eur,
    SUM(revenue_eur) AS revenue_eur,
    CASE WHEN SUM(planned_minutes) > 0 THEN SUM(run_minutes) / SUM(planned_minutes) END AS availability,
    CASE WHEN SUM(run_minutes) > 0 THEN SUM(ideal_cycle_time_s * total_qty) / (SUM(run_minutes) * 60.0) END AS performance,
    CASE WHEN SUM(total_qty) > 0 THEN SUM(good_qty) * 1.0 / SUM(total_qty) END AS quality,
    CASE WHEN SUM(planned_minutes) > 0 AND SUM(run_minutes) > 0 AND SUM(total_qty) > 0
         THEN (SUM(run_minutes) / SUM(planned_minutes))
            * (SUM(ideal_cycle_time_s * total_qty) / (SUM(run_minutes) * 60.0))
            * (SUM(good_qty) * 1.0 / SUM(total_qty))
    END AS oee,
    CASE WHEN SUM(good_qty) > 0 THEN SUM(production_cost_eur) / SUM(good_qty) END AS unit_cost_eur,
    CASE WHEN SUM(revenue_eur) > 0 THEN (SUM(revenue_eur) - SUM(production_cost_eur)) / SUM(revenue_eur) END AS gross_margin_rate
FROM fact_production p
GROUP BY p.date, p.machine_id;

DROP VIEW IF EXISTS vw_machine_health;
CREATE VIEW vw_machine_health AS
SELECT
    x.machine_id,
    m.machine_name,
    m.area,
    m.target_oee,
    x.oee,
    x.availability,
    x.performance,
    x.quality,
    x.unit_cost_eur,
    CASE
        WHEN x.oee >= m.target_oee THEN 'Healthy'
        WHEN x.oee >= m.target_oee - 0.05 THEN 'Watch'
        ELSE 'Critical'
    END AS status
FROM (
    SELECT
        machine_id,
        SUM(run_minutes) / NULLIF(SUM(planned_minutes), 0) AS availability,
        SUM(ideal_cycle_time_s * total_qty) / NULLIF(SUM(run_minutes) * 60.0, 0) AS performance,
        SUM(good_qty) * 1.0 / NULLIF(SUM(total_qty), 0) AS quality,
        (SUM(run_minutes) / NULLIF(SUM(planned_minutes), 0))
        * (SUM(ideal_cycle_time_s * total_qty) / NULLIF(SUM(run_minutes) * 60.0, 0))
        * (SUM(good_qty) * 1.0 / NULLIF(SUM(total_qty), 0)) AS oee,
        SUM(production_cost_eur) / NULLIF(SUM(good_qty), 0) AS unit_cost_eur
    FROM fact_production
    GROUP BY machine_id
) x
JOIN dim_machine m ON m.machine_id = x.machine_id;

DROP VIEW IF EXISTS vw_monthly_business_kpis;
CREATE VIEW vw_monthly_business_kpis AS
SELECT
    month,
    SUM(planned_qty) AS planned_qty,
    SUM(good_qty) AS good_qty,
    SUM(scrap_qty) AS scrap_qty,
    SUM(revenue_eur) AS revenue_eur,
    SUM(production_cost_eur) AS production_cost_eur,
    SUM(revenue_eur) - SUM(production_cost_eur) AS gross_margin_eur,
    CASE WHEN SUM(revenue_eur) > 0 THEN (SUM(revenue_eur) - SUM(production_cost_eur)) / SUM(revenue_eur) END AS gross_margin_rate,
    CASE WHEN SUM(planned_qty) > 0 THEN SUM(good_qty) * 1.0 / SUM(planned_qty) END AS plan_attainment
FROM fact_production
GROUP BY month;
