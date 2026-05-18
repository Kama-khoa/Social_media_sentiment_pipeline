{{ config(
    materialized='incremental',
    unique_key='comment_id'
) }}

WITH stg_comments AS (
    SELECT * FROM {{ ref('stg_youtube_comments') }}
    {% if is_incremental() %}
    WHERE _dbt_loaded_at > (SELECT MAX(_dbt_processed_at) FROM {{ this }})
    {% endif %}
)

SELECT
    comment_id AS sentence_id,
    comment_id,
    video_id,
    channel_id,
    1 AS sentence_index,
    text_original AS sentence_text,
    LOWER(TRIM(text_original)) AS sentence_text_normalized,
    TRUE AS is_vietnamese,
    ARRAY_LENGTH(SPLIT(text_original, ' ')) AS word_count,
    data_quality_score,
    published_at,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM stg_comments
WHERE text_original IS NOT NULL
