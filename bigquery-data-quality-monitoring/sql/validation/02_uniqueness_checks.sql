-- =============================================================================
-- 02_uniqueness_checks.sql
-- Chicago Crime Dataset — Uniqueness Validation
-- =============================================================================

-- ── 1. unique_key must be globally unique ─────────────────────────────────────
SELECT
    'uniqueness_unique_key'                            AS check_name,
    COUNT(*) = COUNT(DISTINCT unique_key)              AS passed,
    COUNT(*) - COUNT(DISTINCT unique_key)              AS duplicate_count,
    COUNT(*)                                           AS total_count,
    ROUND(COUNT(DISTINCT unique_key) / COUNT(*) * 100, 4)
                                                       AS pct_unique
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 2. case_number must be unique ────────────────────────────────────────────
SELECT
    'uniqueness_case_number'                           AS check_name,
    COUNT(*) = COUNT(DISTINCT case_number)             AS passed,
    COUNT(*) - COUNT(DISTINCT case_number)             AS duplicate_count,
    COUNT(*)                                           AS total_count,
    ROUND(COUNT(DISTINCT case_number) / COUNT(*) * 100, 4)
                                                       AS pct_unique
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 3. Show duplicate unique_keys if any (diagnostic) ────────────────────────
SELECT
    'uniqueness_duplicates_detail'                     AS check_name,
    unique_key,
    COUNT(*)                                           AS occurrence_count
FROM `bigquery-public-data.chicago_crime.crime`
GROUP BY unique_key
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC
LIMIT 20;
