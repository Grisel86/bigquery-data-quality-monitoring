-- dbt/models/marts/mart_daily_crime_summary.sql
-- ──────────────────────────────────────────────
-- Gold-equivalent mart: one row per day with crime KPIs.
-- Partitioned by snapshot_date for cost-efficient queries.

WITH enriched AS (
    SELECT * FROM {{ ref('int_crime_enriched') }}
),

daily AS (
    SELECT
        incident_date                                      AS snapshot_date,
        incident_year,
        COUNT(*)                                           AS total_incidents,
        COUNT(DISTINCT case_number)                        AS unique_cases,
        COUNTIF(is_arrest     = TRUE)                      AS total_arrests,
        COUNTIF(is_domestic   = TRUE)                      AS domestic_incidents,
        COUNTIF(is_violent_crime  = TRUE)                  AS violent_crimes,
        COUNTIF(is_property_crime = TRUE)                  AS property_crimes,
        COUNTIF(has_location_data = TRUE)                  AS incidents_with_coords,
        COUNT(DISTINCT district)                           AS districts_with_activity,
        COUNT(DISTINCT primary_type)                       AS distinct_crime_types,

        -- Rates
        ROUND(COUNTIF(is_arrest = TRUE) / COUNT(*) * 100, 2)
                                                           AS arrest_rate_pct,
        ROUND(COUNTIF(is_domestic = TRUE) / COUNT(*) * 100, 2)
                                                           AS domestic_rate_pct,
        ROUND(COUNTIF(is_violent_crime = TRUE) / COUNT(*) * 100, 2)
                                                           AS violent_crime_rate_pct,
        ROUND(COUNTIF(has_location_data = TRUE) / COUNT(*) * 100, 2)
                                                           AS location_completeness_pct,

        -- Time distribution
        COUNTIF(time_of_day = 'morning')                  AS morning_incidents,
        COUNTIF(time_of_day = 'afternoon')                AS afternoon_incidents,
        COUNTIF(time_of_day = 'evening')                  AS evening_incidents,
        COUNTIF(time_of_day = 'night')                    AS night_incidents,

        CURRENT_TIMESTAMP()                                AS dbt_updated_at
    FROM enriched
    GROUP BY incident_date, incident_year
)

SELECT * FROM daily
