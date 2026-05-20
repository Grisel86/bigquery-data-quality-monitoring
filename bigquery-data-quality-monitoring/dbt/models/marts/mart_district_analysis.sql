-- dbt/models/marts/mart_district_analysis.sql
-- ─────────────────────────────────────────────
-- District-level aggregation for operational analytics.

WITH enriched AS (
    SELECT * FROM {{ ref('int_crime_enriched') }}
    WHERE district IS NOT NULL
),

district_stats AS (
    SELECT
        district,
        incident_year                                      AS snapshot_date,
        COUNT(*)                                           AS total_incidents,
        COUNTIF(is_arrest = TRUE)                          AS total_arrests,
        COUNTIF(is_violent_crime = TRUE)                   AS violent_crimes,
        COUNTIF(is_property_crime = TRUE)                  AS property_crimes,
        COUNTIF(is_domestic = TRUE)                        AS domestic_incidents,
        COUNT(DISTINCT primary_type)                       AS distinct_crime_types,
        ROUND(COUNTIF(is_arrest = TRUE) / COUNT(*) * 100, 2)
                                                           AS arrest_rate_pct,
        ROUND(COUNTIF(is_violent_crime = TRUE) / COUNT(*) * 100, 2)
                                                           AS violent_rate_pct,
        ROUND(AVG(CAST(incident_hour AS FLOAT64)), 1)      AS avg_incident_hour,
        CURRENT_TIMESTAMP()                                AS dbt_updated_at
    FROM enriched
    GROUP BY district, incident_year
)

SELECT * FROM district_stats
ORDER BY district, snapshot_date
