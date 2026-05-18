{{ config(
    materialized='table'
) }}

WITH keywords AS (
    SELECT * FROM {{ source('raw', 'keyword_config') }}
)

SELECT
    keyword_id AS product_id,
    keyword_text AS product_name,
    keyword_text AS brand,
    COALESCE(search_cluster, 'unknown') AS category,
    CAST(NULL AS INT64) AS release_year,
    is_active,
    created_at
FROM keywords
WHERE keyword_text IS NOT NULL AND keyword_text != ''
