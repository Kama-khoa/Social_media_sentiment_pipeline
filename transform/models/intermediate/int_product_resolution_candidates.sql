{{ config(materialized='table') }}

WITH videos AS (
    SELECT video_id, title
    FROM {{ ref('stg_youtube_videos') }}
),
mapped_videos AS (
    SELECT DISTINCT video_id
    FROM {{ ref('int_video_product_mentions') }}
),
ambiguous_sentences AS (
    SELECT sentence_id, video_id
    FROM {{ ref('int_sentence_product_targets') }}
    WHERE resolution_status = 'needs_llm'
    GROUP BY sentence_id, video_id
)

SELECT
    TO_HEX(MD5(CONCAT('video-', v.video_id))) AS candidate_id,
    'video' AS source_type,
    v.video_id AS source_id,
    v.title AS candidate_text,
    'pending' AS status,
    CAST(NULL AS STRING) AS resolved_product_id,
    CURRENT_TIMESTAMP() AS created_at
FROM videos v
LEFT JOIN mapped_videos m USING (video_id)
WHERE m.video_id IS NULL

UNION ALL

SELECT
    TO_HEX(MD5(CONCAT('sentence-', s.sentence_id))) AS candidate_id,
    'sentence' AS source_type,
    s.sentence_id AS source_id,
    s.sentence_text AS candidate_text,
    'pending' AS status,
    CAST(NULL AS STRING) AS resolved_product_id,
    CURRENT_TIMESTAMP() AS created_at
FROM ambiguous_sentences a
JOIN {{ ref('int_comment_sentences') }} s USING (sentence_id, video_id)
