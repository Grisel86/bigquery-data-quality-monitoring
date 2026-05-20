-- dbt/tests/singular/assert_updated_on_after_incident.sql
-- ──────────────────────────────────────────────────────────
-- Fails if updated_on is earlier than the incident date.

SELECT
    unique_key,
    incident_datetime,
    updated_on
FROM {{ ref('stg_chicago_crime') }}
WHERE
    updated_on IS NOT NULL
    AND incident_datetime IS NOT NULL
    AND updated_on < incident_datetime
