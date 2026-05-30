{{ config(
    materialized='incremental',
    unique_key='result_id',
    on_schema_change='sync_all_columns'
) }}

WITH raw AS (
    SELECT * FROM {{ source('raw', 'raw_sentiment_results') }}
    {% if is_incremental() %}
    WHERE processed_at > (SELECT COALESCE(MAX(processed_at), TIMESTAMP('1970-01-01')) FROM {{ this }})
    {% endif %}
)

SELECT
    result_id,
    sentence_id,
    comment_id,
    video_id,
    aspect_label,
    segment_text,
    sentiment_label,
    confidence_score,
    inference_model,
    dag_run_id,
    processed_at
FROM raw
