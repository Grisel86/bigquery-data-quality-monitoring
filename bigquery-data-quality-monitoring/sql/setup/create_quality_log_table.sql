-- =============================================================================
-- setup/create_quality_log_table.sql
-- Creates the audit log table where Python runner writes check results.
-- Run once before the first pipeline execution.
-- Replace YOUR_PROJECT and YOUR_DATASET with your GCP project/dataset.
-- =============================================================================

CREATE TABLE IF NOT EXISTS `YOUR_PROJECT.YOUR_DATASET.dq_check_log`
(
    run_id          STRING    NOT NULL,
    run_timestamp   TIMESTAMP NOT NULL,
    layer           STRING    NOT NULL,
    check_name      STRING    NOT NULL,
    check_category  STRING,           -- completeness / uniqueness / validity / consistency
    passed          BOOL      NOT NULL,
    invalid_count   INT64,
    total_count     INT64,
    pct_valid       FLOAT64,
    critical        BOOL,
    detail          STRING,
    metadata_json   STRING,
    dataset         STRING,
    table_name      STRING,
)
PARTITION BY DATE(run_timestamp)
OPTIONS (
    description = "Data quality check audit log — Chicago Crime monitoring pipeline",
    require_partition_filter = FALSE
);
