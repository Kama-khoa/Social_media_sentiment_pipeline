SELECT *
FROM {{ ref('agg_daily_product_ranking') }}
WHERE top_aspect = 'NONE'
   OR bayesian_score < -1.0
   OR bayesian_score > 1.0
   OR controversy_index < 0.0
   OR controversy_label NOT IN ('cao', 'trung bình', 'thấp')
   OR positive_count + negative_count + neutral_count != total_mentions
