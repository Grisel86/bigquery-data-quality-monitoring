-- dbt/tests/singular/assert_no_future_incidents.sql
-- ────────────────────────────────────────────────────
-- Fails if any incident is dated in the future.
-- dbt singular tests: query must return 0 rows to pass.

SELECT
    unique_key,
    incident_datetime,
    CURRENT_TIMESTAMP() AS checked_at
FROM {{ ref('stg_chicago_crime') }}
WHERE incident_datetime > CURRENT_TIMESTAMP()
