{{ config(materialized='view') }}

WITH source AS (
    SELECT
        CAST(comment_id AS STRING) AS comment_id,
        CAST(video_id AS STRING) AS video_id,
        CAST(channel_id AS STRING) AS channel_id,
        CAST(parent_comment_id AS STRING) AS parent_comment_id,
        CAST(author_channel_id AS STRING) AS author_channel_id,
        CAST(author_display_name AS STRING) AS author_display_name,
        CAST(text_original AS STRING) AS text_original,
        CAST(text_display AS STRING) AS text_display,
        SAFE_CAST(like_count AS INT64) AS like_count,
        SAFE_CAST(reply_count AS INT64) AS reply_count,
        SAFE_CAST(is_reply AS BOOL) AS is_reply,
        CAST(crawl_type AS STRING) AS crawl_type,
        SAFE_CAST(published_at AS TIMESTAMP) AS published_at,
        SAFE_CAST(updated_at AS TIMESTAMP) AS updated_at,
        SAFE_CAST(crawled_at AS TIMESTAMP) AS crawled_at,
        CAST(gcs_partition_date AS STRING) AS gcs_partition_date,
        1 AS source_priority
    FROM {{ source('raw', 'raw_comments') }}

    UNION ALL

    SELECT
        CAST(comment_id AS STRING) AS comment_id,
        CAST(video_id AS STRING) AS video_id,
        CAST(channel_id AS STRING) AS channel_id,
        CAST(parent_comment_id AS STRING) AS parent_comment_id,
        CAST(author_channel_id AS STRING) AS author_channel_id,
        CAST(author_display_name AS STRING) AS author_display_name,
        CAST(text_original AS STRING) AS text_original,
        CAST(text_display AS STRING) AS text_display,
        SAFE_CAST(like_count AS INT64) AS like_count,
        SAFE_CAST(reply_count AS INT64) AS reply_count,
        SAFE_CAST(is_reply AS BOOL) AS is_reply,
        CAST(crawl_type AS STRING) AS crawl_type,
        SAFE_CAST(published_at AS TIMESTAMP) AS published_at,
        SAFE_CAST(updated_at AS TIMESTAMP) AS updated_at,
        SAFE_CAST(crawled_at AS TIMESTAMP) AS crawled_at,
        CAST(gcs_partition_date AS STRING) AS gcs_partition_date,
        2 AS source_priority
    FROM {{ source('raw', 'raw_comments_api') }}
),
deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY comment_id
            ORDER BY source_priority DESC, crawled_at DESC
        ) AS rn
    FROM source
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
        GREATEST(0.0,
            CASE WHEN text_original IS NULL THEN 0.0 ELSE 1.0 END
            -- Trừ 0.5 điểm nếu chứa đường dẫn URL (dấu hiệu của spam)
            - CASE WHEN REGEXP_CONTAINS(LOWER(text_original), r'(http[s]?://|www\\.)') THEN 0.5 ELSE 0.0 END
            -- Trừ 0.3 điểm nếu bình luận quá ngắn (< 5 ký tự)
            - CASE WHEN LENGTH(TRIM(text_original)) < 5 THEN 0.3 ELSE 0.0 END
            -- Trừ 0.5 điểm nếu không chứa chữ cái hoặc số (chủ yếu là emoji hoặc ký tự đặc biệt)
            - CASE WHEN NOT REGEXP_CONTAINS(text_original, r'[a-zA-Z0-9_àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]') THEN 0.5 ELSE 0.0 END
        )
    AS FLOAT64) AS data_quality_score,
    CAST(published_at AS TIMESTAMP) AS published_at,
    CURRENT_TIMESTAMP() AS _dbt_loaded_at
FROM deduped
WHERE rn = 1
