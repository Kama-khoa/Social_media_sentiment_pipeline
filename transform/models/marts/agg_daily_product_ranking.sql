{{ config(
    materialized='table',
    partition_by={
      "field": "ranking_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by=["category", "product_id"]
) }}

WITH fact_mentions AS (
    SELECT * FROM {{ ref('fact_product_mentions') }}
),
products AS (
    SELECT * FROM {{ ref('dim_products') }}
),
daily_stats AS (
    SELECT
        f.mention_date AS ranking_date,
        f.product_id,
        p.category,
        COUNT(f.mention_id) AS total_mentions,
        COUNTIF(f.sentiment_label = 'POSITIVE') AS positive_count,
        COUNTIF(f.sentiment_label = 'NEGATIVE') AS negative_count,
        COUNTIF(f.sentiment_label = 'NEUTRAL') AS neutral_count
    FROM fact_mentions f
    JOIN products p ON f.product_id = p.product_id
    GROUP BY 1, 2, 3
)

SELECT
    GENERATE_UUID() AS ranking_id,
    product_id,
    ranking_date,
    category,
    -- Simple Bayesian average placeholder
    -- formula: (C * m + sum(votes)) / (C + N)
    -- Here we do a simple ratio for demonstration: (pos - neg) / total
    SAFE_DIVIDE((positive_count - negative_count), total_mentions) AS bayesian_score,
    
    -- Controversy index placeholder: High if both pos and neg are high
    -- formula: (pos * neg) / total^2
    SAFE_DIVIDE((positive_count * negative_count), POW(total_mentions, 2)) AS controversy_index,
    
    'Unknown' AS controversy_label,
    total_mentions,
    positive_count,
    negative_count,
    neutral_count,
    CAST(NULL AS STRING) AS top_aspect,
    0.0 AS sentiment_trend,
    
    -- Rank by bayesian score descending
    RANK() OVER(PARTITION BY ranking_date, category ORDER BY SAFE_DIVIDE((positive_count - negative_count), total_mentions) DESC) AS rank_position,
    
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM daily_stats
