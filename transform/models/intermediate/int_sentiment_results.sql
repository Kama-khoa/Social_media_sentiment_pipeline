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
),
deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY result_id
            ORDER BY processed_at DESC, confidence_score DESC, dag_run_id DESC
        ) AS result_rank
    FROM raw
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
FROM deduplicated
WHERE result_rank = 1
