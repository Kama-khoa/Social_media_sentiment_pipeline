SELECT product_id, product_name
FROM {{ ref('dim_products') }}
WHERE LOWER(product_name) IN (
    'review', 'so sánh', 'đánh giá', 'pin test', 'samsung', 'iphone', '_uncategorized'
)
