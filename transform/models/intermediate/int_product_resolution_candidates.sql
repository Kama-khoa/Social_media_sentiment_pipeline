{{ config(materialized='table') }}

WITH videos AS (
    SELECT
        video_id,
        title,
        description,
        published_at,
        LOWER(CONCAT(COALESCE(title, ''), ' ', COALESCE(description, ''))) AS text_blob
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
),
generic_video_mentions AS (
    SELECT DISTINCT
        v.video_id,
        'macbook_air' AS generic_term,
        CONCAT('[generic: MacBook Air] ', v.title) AS candidate_text
    FROM videos v
    WHERE REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])macbook air([^a-z0-9]|$)')
      AND NOT REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])macbook air[^a-z0-9]*(m1|m2|m3|m4|m5|13|15|2020|2021|2022|2023|2024|2025|2026)([^a-z0-9]|$)')

    UNION ALL

    SELECT DISTINCT
        v.video_id,
        'macbook_pro' AS generic_term,
        CONCAT('[generic: MacBook Pro] ', v.title) AS candidate_text
    FROM videos v
    WHERE REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])macbook pro([^a-z0-9]|$)')
      AND NOT REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])macbook pro[^a-z0-9]*(m1|m2|m3|m4|m5|13|14|16|2020|2021|2022|2023|2024|2025|2026)([^a-z0-9]|$)')

    UNION ALL

    SELECT DISTINCT
        v.video_id,
        'airpods_pro' AS generic_term,
        CONCAT('[generic: AirPods Pro] ', v.title) AS candidate_text
    FROM videos v
    WHERE (v.published_at IS NULL OR v.published_at >= TIMESTAMP('2022-09-07'))
      AND REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])airpods pro([^a-z0-9]|$)')
      AND NOT REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])airpods pro\s*(1|2|3|gen|first|1st)([^a-z0-9]|$)')

    UNION ALL

    SELECT DISTINCT
        v.video_id,
        'airpods' AS generic_term,
        CONCAT('[generic: AirPods] ', v.title) AS candidate_text
    FROM videos v
    WHERE (v.published_at IS NULL OR v.published_at >= TIMESTAMP('2019-03-20'))
      AND REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])airpods([^a-z0-9]|$)')
      AND NOT REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])airpods\s*(1|2|3|4|max|pro|gen|first|1st)([^a-z0-9]|$)')
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
    TO_HEX(MD5(CONCAT('generic-video-', g.generic_term, '-', g.video_id))) AS candidate_id,
    'video' AS source_type,
    g.video_id AS source_id,
    g.candidate_text,
    'pending' AS status,
    CAST(NULL AS STRING) AS resolved_product_id,
    CURRENT_TIMESTAMP() AS created_at
FROM generic_video_mentions g

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
