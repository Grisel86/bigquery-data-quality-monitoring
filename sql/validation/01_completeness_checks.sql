-- =============================================================================
-- 01_completeness_checks.sql
-- Chicago Crime Dataset — Completeness Validation
-- Dataset: bigquery-public-data.chicago_crime.crime
--
-- Checks that critical columns have no NULL / empty values.
-- Each query returns one row: check_name, passed, null_count, total_count, pct_valid
-- =============================================================================

-- ── 1. Critical nulls: unique_key ─────────────────────────────────────────────
SELECT
    'completeness_unique_key'                           AS check_name,
    COUNTIF(unique_key IS NULL) = 0                    AS passed,
    COUNTIF(unique_key IS NULL)                        AS null_count,
    COUNT(*)                                           AS total_count,
    ROUND(COUNTIF(unique_key IS NOT NULL) / COUNT(*) * 100, 4)
                                                       AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 2. Critical nulls: date ───────────────────────────────────────────────────
SELECT
    'completeness_date'                                AS check_name,
    COUNTIF(date IS NULL) = 0                         AS passed,
    COUNTIF(date IS NULL)                             AS null_count,
    COUNT(*)                                          AS total_count,
    ROUND(COUNTIF(date IS NOT NULL) / COUNT(*) * 100, 4)
                                                      AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 3. Critical nulls: primary_type ──────────────────────────────────────────
SELECT
    'completeness_primary_type'                        AS check_name,
    COUNTIF(primary_type IS NULL OR TRIM(primary_type) = '')
                                                       = 0 AS passed,
    COUNTIF(primary_type IS NULL OR TRIM(primary_type) = '')
                                                       AS null_count,
    COUNT(*)                                           AS total_count,
    ROUND(
        COUNTIF(primary_type IS NOT NULL AND TRIM(primary_type) != '')
        / COUNT(*) * 100, 4)                           AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 4. Non-critical nulls: latitude / longitude ───────────────────────────────
SELECT
    'completeness_coordinates'                         AS check_name,
    COUNTIF(latitude IS NULL OR longitude IS NULL) = 0 AS passed,
    COUNTIF(latitude IS NULL OR longitude IS NULL)     AS null_count,
    COUNT(*)                                           AS total_count,
    ROUND(
        COUNTIF(latitude IS NOT NULL AND longitude IS NOT NULL)
        / COUNT(*) * 100, 4)                           AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 5. Non-critical nulls: district ──────────────────────────────────────────
SELECT
    'completeness_district'                            AS check_name,
    COUNTIF(district IS NULL) = 0                     AS passed,
    COUNTIF(district IS NULL)                         AS null_count,
    COUNT(*)                                          AS total_count,
    ROUND(COUNTIF(district IS NOT NULL) / COUNT(*) * 100, 4)
                                                      AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 6. Non-critical nulls: block ─────────────────────────────────────────────
SELECT
    'completeness_block'                               AS check_name,
    COUNTIF(block IS NULL OR TRIM(block) = '')
                                                       = 0 AS passed,
    COUNTIF(block IS NULL OR TRIM(block) = '')         AS null_count,
    COUNT(*)                                           AS total_count,
    ROUND(
        COUNTIF(block IS NOT NULL AND TRIM(block) != '')
        / COUNT(*) * 100, 4)                           AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;
