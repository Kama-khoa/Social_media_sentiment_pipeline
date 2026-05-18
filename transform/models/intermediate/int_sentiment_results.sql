{{ config(
    materialized='table'
) }}

-- This is a placeholder table for compilation purposes.
-- The actual sentiment results will be populated by the NLP Python pipeline into `raw_sentiment_results`.
-- If the NLP pipeline directly writes to `int_sentiment_results`, then this dbt model can just be an empty table
-- initialization or select from the raw NLP output table.

SELECT
    CAST(NULL AS STRING) AS result_id,
    CAST(NULL AS STRING) AS sentence_id,
    CAST(NULL AS STRING) AS comment_id,
    CAST(NULL AS STRING) AS video_id,
    CAST(NULL AS STRING) AS aspect_label,
    CAST(NULL AS STRING) AS segment_text,
    CAST(NULL AS STRING) AS sentiment_label
LIMIT 0
