-- Indexes for the analytical SQLite warehouse.
CREATE INDEX IF NOT EXISTS idx_prod_date ON fact_production(date);
CREATE INDEX IF NOT EXISTS idx_prod_machine ON fact_production(machine_id);
CREATE INDEX IF NOT EXISTS idx_prod_product ON fact_production(product_id);
CREATE INDEX IF NOT EXISTS idx_prod_shift ON fact_production(shift);
CREATE INDEX IF NOT EXISTS idx_down_date ON fact_downtime(date);
CREATE INDEX IF NOT EXISTS idx_down_machine ON fact_downtime(machine_id);
CREATE INDEX IF NOT EXISTS idx_down_reason ON fact_downtime(reason);
CREATE INDEX IF NOT EXISTS idx_quality_date ON fact_quality(date);
CREATE INDEX IF NOT EXISTS idx_quality_machine_product ON fact_quality(machine_id, product_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_date ON dim_date(date);
