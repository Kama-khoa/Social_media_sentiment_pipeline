{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_comments') }}
)

SELECT
    comment_id,
    video_id,
    channel_id,
    parent_comment_id,
    author_channel_id,
    author_display_name,
    text_original,
    CAST(like_count AS INT64) AS like_count,
    CAST(reply_count AS INT64) AS reply_count,
    CAST(is_reply AS BOOL) AS is_reply,
    crawl_type,
    CAST(
        CASE 
            WHEN text_original IS NOT NULL AND author_display_name IS NOT NULL THEN 1.0 
            WHEN text_original IS NOT NULL THEN 0.8
            ELSE 0.1 
        END AS FLOAT64
    ) AS data_quality_score,
    CAST(published_at AS TIMESTAMP) AS published_at,
    CURRENT_TIMESTAMP() AS _dbt_loaded_at
FROM source
