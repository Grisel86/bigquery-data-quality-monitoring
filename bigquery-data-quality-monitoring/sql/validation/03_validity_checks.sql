-- =============================================================================
-- 03_validity_checks.sql
-- Chicago Crime Dataset — Validity & Domain Rules
-- =============================================================================

-- ── 1. Year must be between 2001 and current year ────────────────────────────
SELECT
    'validity_year_range'                              AS check_name,
    COUNTIF(year NOT BETWEEN 2001 AND EXTRACT(YEAR FROM CURRENT_DATE())) = 0
                                                       AS passed,
    COUNTIF(year NOT BETWEEN 2001 AND EXTRACT(YEAR FROM CURRENT_DATE()))
                                                       AS invalid_count,
    COUNT(*)                                           AS total_count,
    ROUND(
        COUNTIF(year BETWEEN 2001 AND EXTRACT(YEAR FROM CURRENT_DATE()))
        / COUNT(*) * 100, 4)                           AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 2. Coordinates must be in Chicago bounding box ───────────────────────────
-- Chicago approx bbox: lat 41.64–42.02, lon -87.94– -87.52
SELECT
    'validity_coordinates_chicago_bbox'                AS check_name,
    COUNTIF(
        latitude  IS NOT NULL AND longitude IS NOT NULL AND
        NOT (latitude  BETWEEN 41.64 AND 42.02
             AND longitude BETWEEN -87.94 AND -87.52)
    ) = 0                                              AS passed,
    COUNTIF(
        latitude  IS NOT NULL AND longitude IS NOT NULL AND
        NOT (latitude  BETWEEN 41.64 AND 42.02
             AND longitude BETWEEN -87.94 AND -87.52)
    )                                                  AS invalid_count,
    COUNT(*)                                           AS total_count,
    ROUND(
        COUNTIF(
            latitude IS NULL OR longitude IS NULL OR
            (latitude  BETWEEN 41.64 AND 42.02
             AND longitude BETWEEN -87.94 AND -87.52)
        ) / COUNT(*) * 100, 4)                         AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 3. District must be between 1 and 31 (Chicago PD districts) ──────────────
SELECT
    'validity_district_range'                          AS check_name,
    COUNTIF(district IS NOT NULL AND district NOT BETWEEN 1 AND 31)
                                                       = 0 AS passed,
    COUNTIF(district IS NOT NULL AND district NOT BETWEEN 1 AND 31)
                                                       AS invalid_count,
    COUNT(*)                                           AS total_count,
    ROUND(
        COUNTIF(district IS NULL OR district BETWEEN 1 AND 31)
        / COUNT(*) * 100, 4)                           AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 4. date must not be in the future ────────────────────────────────────────
SELECT
    'validity_date_not_future'                         AS check_name,
    COUNTIF(date > CURRENT_TIMESTAMP()) = 0            AS passed,
    COUNTIF(date > CURRENT_TIMESTAMP())                AS invalid_count,
    COUNT(*)                                           AS total_count,
    ROUND(COUNTIF(date <= CURRENT_TIMESTAMP()) / COUNT(*) * 100, 4)
                                                       AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 5. arrest and domestic must be boolean (not null in typed schema) ─────────
SELECT
    'validity_boolean_fields_not_null'                 AS check_name,
    COUNTIF(arrest IS NULL OR domestic IS NULL) = 0    AS passed,
    COUNTIF(arrest IS NULL OR domestic IS NULL)        AS invalid_count,
    COUNT(*)                                           AS total_count,
    ROUND(
        COUNTIF(arrest IS NOT NULL AND domestic IS NOT NULL)
        / COUNT(*) * 100, 4)                           AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`;

-- ── 6. year must match EXTRACT(YEAR FROM date) ───────────────────────────────
SELECT
    'validity_year_matches_date'                       AS check_name,
    COUNTIF(year != EXTRACT(YEAR FROM date)) = 0       AS passed,
    COUNTIF(year != EXTRACT(YEAR FROM date))           AS invalid_count,
    COUNT(*)                                           AS total_count,
    ROUND(
        COUNTIF(year = EXTRACT(YEAR FROM date))
        / COUNT(*) * 100, 4)                           AS pct_valid
FROM `bigquery-public-data.chicago_crime.crime`
WHERE date IS NOT NULL AND year IS NOT NULL;
