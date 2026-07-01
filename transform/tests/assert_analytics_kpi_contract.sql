SELECT *
FROM {{ ref('agg_daily_product_ranking') }}
WHERE top_aspect = 'NONE'
   OR bayesian_score < -1.0
   OR bayesian_score > 1.0
   OR controversy_index < 0.0
   OR controversy_label NOT IN ('cao', 'trung binh', 'thap')
   OR positive_count + negative_count + neutral_count != statement_count
   OR statement_count + question_count != total_mention_count
   OR total_mentions != total_mention_count
