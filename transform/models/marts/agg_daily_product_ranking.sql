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
            WHEN UPPER(sentiment_label) = 'POSITIVE' THEN 1.0
            WHEN UPPER(sentiment_label) = 'NEGATIVE' THEN -1.0
            ELSE 0.0
        END AS sentiment_score
    FROM {{ ref('fact_product_mentions') }}
),
snapshot_dates AS (
    SELECT DISTINCT mention_date AS ranking_date
    FROM fact_mentions
),
valid_mentions AS (
    SELECT *
    FROM fact_mentions
    WHERE aspect_label != 'NONE'
),
rolling_stats AS (
    SELECT
        d.ranking_date,
        f.product_id,
        p.category,
        COUNT(*) AS total_mentions,
        COUNTIF(UPPER(f.sentiment_label) = 'POSITIVE') AS positive_count,
        COUNTIF(UPPER(f.sentiment_label) = 'NEGATIVE') AS negative_count,
        COUNTIF(UPPER(f.sentiment_label) = 'NEUTRAL') AS neutral_count,
        AVG(f.sentiment_score) AS mean_score,
        STDDEV_POP(f.sentiment_score) AS std_score
    FROM snapshot_dates d
    JOIN valid_mentions f
      ON f.mention_date BETWEEN DATE_SUB(d.ranking_date, INTERVAL 29 DAY) AND d.ranking_date
    JOIN {{ ref('dim_products') }} p ON f.product_id = p.product_id
    GROUP BY 1, 2, 3
),
global_stats AS (
    SELECT
        d.ranking_date,
        AVG(f.sentiment_score) AS global_mean
    FROM snapshot_dates d
    JOIN valid_mentions f
      ON f.mention_date BETWEEN DATE_SUB(d.ranking_date, INTERVAL 29 DAY) AND d.ranking_date
    GROUP BY 1
),
none_stats AS (
    SELECT
        d.ranking_date,
        f.product_id,
        COUNT(*) AS excluded_none_count
    FROM snapshot_dates d
    JOIN fact_mentions f
      ON f.mention_date BETWEEN DATE_SUB(d.ranking_date, INTERVAL 29 DAY) AND d.ranking_date
     AND f.aspect_label = 'NONE'
    GROUP BY 1, 2
),
aspect_counts AS (
    SELECT
        d.ranking_date,
        f.product_id,
        f.aspect_label,
        COUNT(*) AS aspect_mentions
    FROM snapshot_dates d
    JOIN valid_mentions f
      ON f.mention_date BETWEEN DATE_SUB(d.ranking_date, INTERVAL 29 DAY) AND d.ranking_date
    GROUP BY 1, 2, 3
),
top_aspects AS (
    SELECT ranking_date, product_id, aspect_label AS top_aspect
    FROM aspect_counts
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY ranking_date, product_id
        ORDER BY aspect_mentions DESC, aspect_label ASC
    ) = 1
),
scored_stats AS (
    SELECT
        s.product_id,
        s.ranking_date,
        s.category,
        SAFE_DIVIDE(50.0 * g.global_mean + s.total_mentions * s.mean_score, 50.0 + s.total_mentions) AS bayesian_score,
        SAFE_DIVIDE(COALESCE(s.std_score, 0.0), ABS(s.mean_score) + 0.1) AS controversy_index,
        s.total_mentions,
        s.positive_count,
        s.negative_count,
        s.neutral_count,
        COALESCE(n.excluded_none_count, 0) AS excluded_none_count,
        a.top_aspect,
        s.mean_score
    FROM rolling_stats s
    JOIN global_stats g USING (ranking_date)
    JOIN top_aspects a USING (ranking_date, product_id)
    LEFT JOIN none_stats n USING (ranking_date, product_id)
),
trended_stats AS (
    SELECT
        *,
        mean_score - COALESCE(
            LAG(mean_score) OVER (PARTITION BY product_id ORDER BY ranking_date),
            mean_score
        ) AS sentiment_trend
    FROM scored_stats
)

SELECT
    TO_HEX(MD5(CONCAT(CAST(ranking_date AS STRING), '-', product_id))) AS ranking_id,
    product_id,
    ranking_date,
    category,
    bayesian_score,
    controversy_index,
    CASE
        WHEN controversy_index > 0.6 THEN 'cao'
        WHEN controversy_index < 0.3 THEN 'thấp'
        ELSE 'trung bình'
    END AS controversy_label,
    total_mentions,
    positive_count,
    negative_count,
    neutral_count,
    excluded_none_count,
    top_aspect,
    sentiment_trend,
    RANK() OVER (PARTITION BY ranking_date, category ORDER BY bayesian_score DESC) AS rank_position,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM trended_stats
