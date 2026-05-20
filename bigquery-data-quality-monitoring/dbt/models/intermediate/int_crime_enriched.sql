-- dbt/models/intermediate/int_crime_enriched.sql
-- ──────────────────────────────────────────────
-- Intermediate layer: adds business classifications and enrichment
-- on top of the clean staging model.

WITH staged AS (
    SELECT * FROM {{ ref('stg_chicago_crime') }}
),

enriched AS (
    SELECT
        *,

        -- Time-of-day bucket
        CASE
            WHEN incident_hour BETWEEN 6  AND 11 THEN 'morning'
            WHEN incident_hour BETWEEN 12 AND 17 THEN 'afternoon'
            WHEN incident_hour BETWEEN 18 AND 21 THEN 'evening'
            ELSE 'night'
        END AS time_of_day,

        -- Weekend flag
        incident_dow IN (1, 7) AS is_weekend,

        -- Season
        CASE
            WHEN EXTRACT(MONTH FROM incident_date) IN (12, 1, 2)  THEN 'winter'
            WHEN EXTRACT(MONTH FROM incident_date) IN (3, 4, 5)   THEN 'spring'
            WHEN EXTRACT(MONTH FROM incident_date) IN (6, 7, 8)   THEN 'summer'
            ELSE 'fall'
        END AS season,

        -- Violent crime flag (FBI UCR Part I violent crimes)
        primary_type IN (
            'HOMICIDE', 'CRIMINAL SEXUAL ASSAULT',
            'ROBBERY', 'ASSAULT', 'BATTERY'
        ) AS is_violent_crime,

        -- Property crime flag
        primary_type IN (
            'BURGLARY', 'LARCENY', 'MOTOR VEHICLE THEFT',
            'ARSON', 'THEFT'
        ) AS is_property_crime,

        -- Has coordinates flag
        (latitude IS NOT NULL AND longitude IS NOT NULL) AS has_location_data

    FROM staged
)

SELECT * FROM enriched
