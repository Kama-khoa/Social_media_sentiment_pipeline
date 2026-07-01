{{ config(
    materialized='table'
) }}

WITH products AS (
    SELECT * FROM {{ source('raw', 'product_config') }}
)

SELECT
    product_id,
    product_name,
    COALESCE(brand, 'unknown') AS brand,
    COALESCE(category, 'unknown') AS category,
    release_year,
    is_active,
    created_at
FROM products
WHERE product_name IS NOT NULL AND product_name != ''
QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY created_at DESC) = 1
