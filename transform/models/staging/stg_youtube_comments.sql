{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_comments') }}
),
deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY comment_id
            ORDER BY crawled_at DESC
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
