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
    SELECT 
        *,
        CASE 
            WHEN sentiment_label = 'POSITIVE' THEN 1.0
            WHEN sentiment_label = 'NEGATIVE' THEN -1.0
            ELSE 0.0
        END AS sentiment_score
    FROM {{ ref('fact_product_mentions') }}
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
        COUNTIF(f.sentiment_label = 'NEUTRAL') AS neutral_count,
        AVG(f.sentiment_score) AS mean_score,
        STDDEV_SAMP(f.sentiment_score) AS std_score
    FROM fact_mentions f
    JOIN products p ON f.product_id = p.product_id
    GROUP BY 1, 2, 3
),
scored_stats AS (
    SELECT
        product_id,
        ranking_date,
        category,
        -- Bayesian average: (C * global_mean + n * local_mean) / (C + n), C=50
        SAFE_DIVIDE(
            50.0 * COALESCE(AVG(mean_score) OVER (), 0.0) + total_mentions * mean_score,
            50.0 + total_mentions
        ) AS bayesian_score,
        
        -- Controversy index: Std(score) / (|Mean(score)| + 0.1)
        SAFE_DIVIDE(COALESCE(std_score, 0), ABS(mean_score) + 0.1) AS controversy_index,
        
        CASE
            WHEN SAFE_DIVIDE(COALESCE(std_score, 0), ABS(mean_score) + 0.1) > 0.6 THEN 'cao'
            WHEN SAFE_DIVIDE(COALESCE(std_score, 0), ABS(mean_score) + 0.1) < 0.3 THEN 'thấp'
            ELSE 'trung bình'
        END AS controversy_label,
        
        total_mentions,
        positive_count,
        negative_count,
        neutral_count,
        CAST(NULL AS STRING) AS top_aspect,
        0.0 AS sentiment_trend
    FROM daily_stats
)

SELECT
    TO_HEX(MD5(CONCAT(CAST(ranking_date AS STRING), '-', product_id))) AS ranking_id,
    *,
    -- Rank by bayesian score descending
    RANK() OVER(PARTITION BY ranking_date, category ORDER BY bayesian_score DESC) AS rank_position,
    
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM scored_stats
