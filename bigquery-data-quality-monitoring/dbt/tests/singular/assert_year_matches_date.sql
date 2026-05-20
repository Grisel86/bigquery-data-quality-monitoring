-- dbt/tests/singular/assert_year_matches_date.sql
-- ──────────────────────────────────────────────────
-- Fails if the year column doesn't match the year extracted from date.

SELECT
    unique_key,
    incident_year,
    EXTRACT(YEAR FROM incident_datetime) AS date_year,
    incident_datetime
FROM {{ ref('stg_chicago_crime') }}
WHERE
    incident_datetime IS NOT NULL
    AND incident_year IS NOT NULL
    AND incident_year != EXTRACT(YEAR FROM incident_datetime)
