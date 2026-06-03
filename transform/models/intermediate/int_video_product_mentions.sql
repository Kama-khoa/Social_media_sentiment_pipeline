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
aliases AS (
    SELECT product_id, alias_text, LOWER(TRIM(alias_text)) AS normalized_alias
    FROM {{ source('raw', 'product_aliases') }}
    WHERE is_active = TRUE AND LENGTH(TRIM(alias_text)) >= 3
      AND LOWER(TRIM(alias_text)) NOT IN (
          'ear',
          'macbook air',
          'macbook pro',
          'airpods',
          'airpods pro'
      )
),
overridden_videos AS (
    SELECT DISTINCT video_id
    FROM {{ source('raw', 'video_product_overrides') }}
    WHERE is_active = TRUE
),
alias_matches AS (
    SELECT DISTINCT
        v.video_id,
        a.product_id,
        CASE
            WHEN STRPOS(LOWER(v.title), LOWER(a.alias_text)) > 0 THEN 'title'
            ELSE 'description'
        END AS match_source,
        CASE
            WHEN STRPOS(LOWER(v.title), LOWER(a.alias_text)) > 0 THEN 0.95
            ELSE 0.80
        END AS confidence_score
    FROM videos v
    JOIN aliases a
      ON STRPOS(v.text_blob, a.normalized_alias) > 0
    LEFT JOIN overridden_videos o USING (video_id)
    WHERE o.video_id IS NULL
),
contextual_matches AS (
    SELECT DISTINCT
        v.video_id,
        'apple-airpods-pro-1' AS product_id,
        'title_context' AS match_source,
        0.90 AS confidence_score
    FROM videos v
    LEFT JOIN overridden_videos o USING (video_id)
    WHERE o.video_id IS NULL
      AND v.published_at < TIMESTAMP('2022-09-07')
      AND REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])airpods pro([^a-z0-9]|$)')
      AND NOT REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])airpods pro\s*(2|3)([^a-z0-9]|$)')

    UNION ALL

    SELECT DISTINCT
        v.video_id,
        'apple-airpods-1' AS product_id,
        'title_context' AS match_source,
        0.90 AS confidence_score
    FROM videos v
    LEFT JOIN overridden_videos o USING (video_id)
    WHERE o.video_id IS NULL
      AND v.published_at < TIMESTAMP('2019-03-20')
      AND REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])airpods([^a-z0-9]|$)')
      AND NOT REGEXP_CONTAINS(v.text_blob, r'(^|[^a-z0-9])airpods\s*(2|3|4|max|pro)([^a-z0-9]|$)')
),
matches AS (
    SELECT * FROM alias_matches
    UNION ALL
    SELECT * FROM contextual_matches
),
deduplicated AS (
    SELECT *
    FROM matches
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY video_id, product_id
        ORDER BY confidence_score DESC
    ) = 1
),
video_counts AS (
    SELECT video_id, COUNT(*) AS product_count
    FROM deduplicated
    GROUP BY video_id
)

SELECT
    d.video_id,
    d.product_id,
    CASE WHEN c.product_count = 1 THEN 'primary' ELSE 'secondary' END AS role,
    d.match_source,
    d.confidence_score,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM deduplicated d
JOIN video_counts c USING (video_id)

UNION ALL

SELECT
    video_id,
    product_id,
    role,
    'admin_override' AS match_source,
    1.0 AS confidence_score,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM {{ source('raw', 'video_product_overrides') }}
WHERE is_active = TRUE
