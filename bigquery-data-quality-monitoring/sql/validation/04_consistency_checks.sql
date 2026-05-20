-- =============================================================================
-- 04_consistency_checks.sql
-- Chicago Crime Dataset — Consistency & Cross-column Rules
-- =============================================================================

-- ── 1. updated_on must be >= date (update can't precede the incident) ─────────
SELECT
    'consistency_updated_after_incident'               AS check_name,
    COUNTIF(
        updated_on IS NOT NULL AND date IS NOT NULL
        AND updated_on < date
    ) = 0                                              AS passed,
    COUNTIF(
        updated_on IS NOT NULL AND date IS NOT NULL
        AND updated_on < date
    )                                                  AS invalid_count,
    COUNT(*)                                           AS total_count,
    ROUND(
        COUNTIF(
            updated_on IS NULL OR date IS NULL OR updated_on >= date
        ) / COUNT(*) * 100, 4)                         AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 2. If coordinates exist, location string should also be populated ─────────
SELECT
    'consistency_coords_with_location'                 AS check_name,
    COUNTIF(
        latitude IS NOT NULL AND longitude IS NOT NULL
        AND (location IS NULL OR TRIM(location) = '')
    ) = 0                                              AS passed,
    COUNTIF(
        latitude IS NOT NULL AND longitude IS NOT NULL
        AND (location IS NULL OR TRIM(location) = '')
    )                                                  AS invalid_count,
    COUNT(*)                                           AS total_count,
    ROUND(
        COUNTIF(
            latitude IS NULL OR longitude IS NULL
            OR (location IS NOT NULL AND TRIM(location) != '')
        ) / COUNT(*) * 100, 4)                         AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 3. Records per year — big drops may indicate data pipeline issues ─────────
SELECT
    year,
    COUNT(*)                                           AS record_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER () * 100, 2)  AS pct_of_total,
    LAG(COUNT(*)) OVER (ORDER BY year)                 AS prev_year_count,
    ROUND(
        (COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY year))
        / NULLIF(LAG(COUNT(*)) OVER (ORDER BY year), 0) * 100, 2
    )                                                  AS yoy_change_pct
FROM `bigquery-public-data.chicago_crime.crime`
GROUP BY year
ORDER BY year;

-- ── 4. Top primary_type distribution (sanity check for unexpected spikes) ─────
SELECT
    primary_type,
    COUNT(*)                                           AS record_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER () * 100, 2)  AS pct_of_total,
    COUNTIF(arrest = TRUE)                             AS arrest_count,
    ROUND(COUNTIF(arrest = TRUE) / COUNT(*) * 100, 2) AS arrest_rate_pct
FROM `bigquery-public-data.chicago_crime.crime`
GROUP BY primary_type
ORDER BY record_count DESC
LIMIT 20;
