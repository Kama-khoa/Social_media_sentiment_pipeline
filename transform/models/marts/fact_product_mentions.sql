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
video_state AS (
    SELECT * FROM {{ source('raw', 'video_crawl_state') }}
),
products AS (
    SELECT * FROM {{ ref('dim_products') }}
)

SELECT
    TO_HEX(MD5(CONCAT(sr.sentence_id, '-', p.product_id))) AS mention_id,
    p.product_id,
    sr.result_id,
    s.video_id,
    s.channel_id,
    s.comment_id,
    sr.sentence_id,
    sr.aspect_label,
    sr.sentiment_label,
    1.0 AS confidence_score, -- Placeholder for NLP confidence score
    CAST(s.published_at AS DATE) AS mention_date,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM sentiment_results sr
JOIN sentences s ON sr.sentence_id = s.sentence_id
-- Kết nối qua bảng video_crawl_state để lấy keyword_id (tương ứng product_id) của video
JOIN video_state vcs ON s.video_id = vcs.video_id
-- Kết nối để lấy các trường chi tiết của product
JOIN products p ON vcs.keyword_id = p.product_id
