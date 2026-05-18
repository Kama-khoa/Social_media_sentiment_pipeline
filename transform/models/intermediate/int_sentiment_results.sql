{{ config(
    materialized='table'
) }}

-- TODO: Khi nlp/inference/ đã ghi kết quả vào bảng `raw_sentiment_results`
-- (dataset: sentiment_platform), thay thế model này bằng:
{#
WITH raw AS (
    SELECT * FROM {{ source('raw', 'raw_sentiment_results') }}
)
SELECT result_id, sentence_id, comment_id, video_id,
       aspect_label, segment_text, sentiment_label
FROM raw
#}
-- Bảng raw_sentiment_results chưa tồn tại — giữ LIMIT 0 để dbt compile thành công.

SELECT
    CAST(NULL AS STRING) AS result_id,
    CAST(NULL AS STRING) AS sentence_id,
    CAST(NULL AS STRING) AS comment_id,
    CAST(NULL AS STRING) AS video_id,
    CAST(NULL AS STRING) AS aspect_label,
    CAST(NULL AS STRING) AS segment_text,
    CAST(NULL AS STRING) AS sentiment_label
LIMIT 0
