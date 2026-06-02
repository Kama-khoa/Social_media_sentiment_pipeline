{{ config(
    materialized='table',
    partition_by={
      "field": "mention_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by=["product_id", "aspect_label", "sentiment_label"]
) }}

WITH sentiment_results AS (
    SELECT * FROM {{ ref('int_sentiment_results') }}
),
sentences AS (
    SELECT * FROM {{ ref('int_comment_sentences') }}
),
targets AS (
    SELECT * FROM {{ ref('int_sentence_product_targets') }}
    WHERE resolution_status = 'resolved'
),
products AS (
    SELECT * FROM {{ ref('dim_products') }}
)

SELECT
    TO_HEX(MD5(CONCAT(sr.result_id, '-', p.product_id))) AS mention_id,
    p.product_id,
    sr.result_id,
    s.video_id,
    s.channel_id,
    s.comment_id,
    sr.sentence_id,
    sr.aspect_label,
    COALESCE(t.target_sentiment_label, sr.sentiment_label) AS sentiment_label,
    sr.confidence_score,
    t.target_source,
    t.target_confidence,
    CAST(s.published_at AS DATE) AS mention_date,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM sentiment_results sr
JOIN sentences s ON sr.sentence_id = s.sentence_id
JOIN targets t ON sr.sentence_id = t.sentence_id
JOIN products p ON t.product_id = p.product_id
