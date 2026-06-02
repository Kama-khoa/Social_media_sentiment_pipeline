{{ config(materialized='table') }}

WITH sentences AS (
    SELECT sentence_id, video_id, sentence_text_normalized
    FROM {{ ref('int_comment_sentences') }}
),
aliases AS (
    SELECT product_id, alias_text
    FROM {{ source('raw', 'product_aliases') }}
    WHERE is_active = TRUE AND LENGTH(TRIM(alias_text)) >= 3
),
overridden_sentences AS (
    SELECT DISTINCT sentence_id
    FROM {{ source('raw', 'sentence_product_target_overrides') }}
),
explicit_matches AS (
    SELECT DISTINCT s.sentence_id, s.video_id, a.product_id
    FROM sentences s
    JOIN aliases a
      ON STRPOS(LOWER(s.sentence_text_normalized), LOWER(a.alias_text)) > 0
    LEFT JOIN overridden_sentences o USING (sentence_id)
    WHERE o.sentence_id IS NULL
),
explicit_counts AS (
    SELECT sentence_id, COUNT(*) AS product_count
    FROM explicit_matches
    GROUP BY sentence_id
),
video_primary AS (
    SELECT video_id, product_id, confidence_score
    FROM {{ ref('int_video_product_mentions') }}
    WHERE role = 'primary'
)

SELECT
    e.sentence_id,
    e.video_id,
    e.product_id,
    'explicit_comment' AS target_source,
    0.95 AS target_confidence,
    CAST(NULL AS STRING) AS target_sentiment_label,
    CASE WHEN c.product_count = 1 THEN 'resolved' ELSE 'needs_llm' END AS resolution_status,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM explicit_matches e
JOIN explicit_counts c USING (sentence_id)

UNION ALL

SELECT
    s.sentence_id,
    s.video_id,
    p.product_id,
    'inherited_video_primary' AS target_source,
    p.confidence_score AS target_confidence,
    CAST(NULL AS STRING) AS target_sentiment_label,
    'resolved' AS resolution_status,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM sentences s
JOIN video_primary p USING (video_id)
LEFT JOIN explicit_counts c USING (sentence_id)
WHERE c.sentence_id IS NULL

UNION ALL

SELECT
    o.sentence_id,
    s.video_id,
    o.product_id,
    o.target_source,
    o.target_confidence,
    o.sentiment_label AS target_sentiment_label,
    'resolved' AS resolution_status,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM {{ source('raw', 'sentence_product_target_overrides') }} o
JOIN sentences s USING (sentence_id)
