-- dbt/macros/quality_macros.sql
-- ─────────────────────────────
-- Reusable macros for data quality checks across models.

{% macro assert_not_null(model, column) %}
    SELECT '{{ column }}' AS column_name, COUNT(*) AS null_count
    FROM {{ model }}
    WHERE {{ column }} IS NULL
    HAVING COUNT(*) > 0
{% endmacro %}


{% macro assert_unique(model, column) %}
    SELECT '{{ column }}' AS column_name, COUNT(*) - COUNT(DISTINCT {{ column }}) AS duplicate_count
    FROM {{ model }}
    HAVING COUNT(*) != COUNT(DISTINCT {{ column }})
{% endmacro %}


{% macro assert_accepted_range(model, column, min_val, max_val) %}
    SELECT '{{ column }}' AS column_name, COUNT(*) AS out_of_range_count
    FROM {{ model }}
    WHERE {{ column }} IS NOT NULL
      AND {{ column }} NOT BETWEEN {{ min_val }} AND {{ max_val }}
    HAVING COUNT(*) > 0
{% endmacro %}


{# 
   Generic test: row_count_in_range
   Asserts the model has between min_rows and max_rows rows.
   Usage in schema.yml:
     - dbt_custom.row_count_in_range:
         min_rows: 1000
#}
{% test row_count_in_range(model, min_rows=1, max_rows=none) %}
    WITH row_count AS (
        SELECT COUNT(*) AS n FROM {{ model }}
    )
    SELECT n
    FROM row_count
    WHERE n < {{ min_rows }}
    {% if max_rows is not none %}
      OR n > {{ max_rows }}
    {% endif %}
{% endtest %}


{#
   Generic test: completeness_above_threshold
   Asserts that at least `threshold_pct`% of rows are non-null for a column.
   Usage in schema.yml:
     - dbt_custom.completeness_above_threshold:
         column_name: latitude
         threshold_pct: 80
#}
{% test completeness_above_threshold(model, column_name, threshold_pct=95) %}
    WITH stats AS (
        SELECT
            COUNT(*)                              AS total,
            COUNTIF({{ column_name }} IS NOT NULL) AS non_null
        FROM {{ model }}
    )
    SELECT
        total,
        non_null,
        ROUND(non_null / total * 100, 2) AS pct_complete
    FROM stats
    WHERE ROUND(non_null / total * 100, 2) < {{ threshold_pct }}
{% endtest %}
