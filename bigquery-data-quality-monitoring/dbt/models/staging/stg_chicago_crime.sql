-- dbt/models/staging/stg_chicago_crime.sql
-- ──────────────────────────────────────────
-- Staging layer: selects from the BigQuery Public Dataset,
-- renames columns to snake_case, casts types, and adds basic derived fields.
-- No business logic here — just clean, typed, renamed source data.

WITH source AS (
    SELECT * FROM {{ source('chicago_crime_public', 'crime') }}
),

renamed AS (
    SELECT
        -- Keys
        CAST(unique_key   AS INT64)     AS unique_key,
        CAST(case_number  AS STRING)    AS case_number,

        -- Temporal
        CAST(date         AS TIMESTAMP) AS incident_datetime,
        CAST(year         AS INT64)     AS incident_year,
        DATE(date)                      AS incident_date,
        EXTRACT(HOUR FROM date)         AS incident_hour,
        EXTRACT(DAYOFWEEK FROM date)    AS incident_dow,
        CAST(updated_on  AS TIMESTAMP)  AS updated_on,

        -- Location
        CAST(block                  AS STRING)  AS block,
        CAST(location_description   AS STRING)  AS location_description,
        CAST(district               AS INT64)   AS district,
        CAST(ward                   AS INT64)   AS ward,
        CAST(community_area         AS INT64)   AS community_area,
        CAST(beat                   AS INT64)   AS beat,
        CAST(latitude               AS FLOAT64) AS latitude,
        CAST(longitude              AS FLOAT64) AS longitude,
        CAST(location               AS STRING)  AS location_str,

        -- Crime classification
        CAST(iucr          AS STRING) AS iucr_code,
        CAST(primary_type  AS STRING) AS primary_type,
        CAST(description   AS STRING) AS crime_description,
        CAST(fbi_code      AS STRING) AS fbi_code,

        -- Flags
        CAST(arrest   AS BOOL) AS is_arrest,
        CAST(domestic AS BOOL) AS is_domestic

    FROM source
),

with_validations AS (
    SELECT
        *,
        -- Derived quality flags (used by dbt singular tests)
        (latitude IS NOT NULL AND longitude IS NOT NULL)  AS has_coordinates,
        (incident_year = EXTRACT(YEAR FROM incident_datetime))
                                                          AS year_matches_date,
        (incident_datetime <= CURRENT_TIMESTAMP())        AS date_not_future
    FROM renamed
)

SELECT * FROM with_validations
