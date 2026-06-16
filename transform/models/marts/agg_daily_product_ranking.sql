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
statement_mentions AS (
    SELECT *
    FROM valid_mentions
    WHERE sentence_type = 'statement'
),
rolling_totals AS (
    SELECT
        d.ranking_date,
        f.product_id,
        p.category,
        COUNT(*) AS total_mention_count,
        COUNTIF(f.sentence_type = 'question') AS question_count
    FROM snapshot_dates d
    JOIN valid_mentions f
      ON f.mention_date BETWEEN DATE_SUB(d.ranking_date, INTERVAL 29 DAY) AND d.ranking_date
    JOIN {{ ref('dim_products') }} p ON f.product_id = p.product_id
    GROUP BY 1, 2, 3
),
rolling_stats AS (
    SELECT
        d.ranking_date,
        f.product_id,
        p.category,
        COUNT(*) AS statement_count,
        COUNTIF(UPPER(f.sentiment_label) = 'POSITIVE') AS positive_count,
        COUNTIF(UPPER(f.sentiment_label) = 'NEGATIVE') AS negative_count,
        COUNTIF(UPPER(f.sentiment_label) = 'NEUTRAL') AS neutral_count,
        AVG(f.sentiment_score) AS mean_score,
        STDDEV_POP(f.sentiment_score) AS std_score
    FROM snapshot_dates d
    JOIN statement_mentions f
      ON f.mention_date BETWEEN DATE_SUB(d.ranking_date, INTERVAL 29 DAY) AND d.ranking_date
    JOIN {{ ref('dim_products') }} p ON f.product_id = p.product_id
    GROUP BY 1, 2, 3
),
global_stats AS (
    SELECT
        d.ranking_date,
        AVG(f.sentiment_score) AS global_mean
    FROM snapshot_dates d
    JOIN statement_mentions f
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
        t.product_id,
        t.ranking_date,
        t.category,
        COALESCE(
            SAFE_DIVIDE(50.0 * g.global_mean + s.statement_count * s.mean_score, 50.0 + s.statement_count),
            0.0
        ) AS bayesian_score,
        COALESCE(SAFE_DIVIDE(COALESCE(s.std_score, 0.0), ABS(s.mean_score) + 0.1), 0.0) AS controversy_index,
        t.total_mention_count,
        COALESCE(s.statement_count, 0) AS statement_count,
        COALESCE(t.question_count, 0) AS question_count,
        COALESCE(s.positive_count, 0) AS positive_count,
        COALESCE(s.negative_count, 0) AS negative_count,
        COALESCE(s.neutral_count, 0) AS neutral_count,
        COALESCE(n.excluded_none_count, 0) AS excluded_none_count,
        a.top_aspect,
        s.mean_score
    FROM rolling_totals t
    LEFT JOIN rolling_stats s USING (ranking_date, product_id, category)
    LEFT JOIN global_stats g USING (ranking_date)
    LEFT JOIN top_aspects a USING (ranking_date, product_id)
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
        WHEN controversy_index < 0.3 THEN 'thap'
        ELSE 'trung binh'
    END AS controversy_label,
    total_mention_count AS total_mentions,
    total_mention_count,
    statement_count,
    question_count,
    positive_count,
    negative_count,
    neutral_count,
    excluded_none_count,
    top_aspect,
    sentiment_trend,
    ROW_NUMBER() OVER (
        PARTITION BY ranking_date
        ORDER BY CASE WHEN statement_count >= 5 THEN 1 ELSE 0 END DESC, bayesian_score DESC, statement_count DESC, total_mention_count DESC, product_id ASC
    ) AS rank_position,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM trended_stats
