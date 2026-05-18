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
-- We need to join with products. Since int_sentiment_results doesn't have product_id natively in the schema,
-- the aspect_label or another field from NLP needs to map to product_id.
-- Assuming NLP tags aspect_label or segment_text with the keyword_id (product_id), 
-- OR assuming we do a text match.
-- For the sake of the structural pipeline, we'll assume NLP outputs `aspect_label` as product_name or we do a text match.
-- We will use a basic CROSS JOIN with LIKE for baseline if NLP doesn't output product_id directly, 
-- but normally NLP gives aspect_label as the entity. We'll join where aspect_label = product_name for now.
JOIN products p ON LOWER(sr.aspect_label) = LOWER(p.product_name)
