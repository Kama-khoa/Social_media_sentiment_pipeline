{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_videos') }}
)

SELECT
    video_id,
    channel_id,
    title,
    description,
    keyword_matched,
    CAST(view_count AS INT64) AS view_count,
    CAST(like_count AS INT64) AS like_count,
    CAST(comment_count AS INT64) AS comment_count,
    CAST(
        CASE 
            WHEN title IS NOT NULL AND published_at IS NOT NULL THEN 1.0 
            WHEN title IS NOT NULL THEN 0.5 
            ELSE 0.1 
        END AS FLOAT64
    ) AS data_quality_score,
    CAST(published_at AS TIMESTAMP) AS published_at,
    gcs_partition_date,
    CURRENT_TIMESTAMP() AS _dbt_loaded_at
FROM source
