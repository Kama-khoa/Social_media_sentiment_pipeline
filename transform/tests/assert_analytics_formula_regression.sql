WITH fixture AS (
    SELECT 50.0 AS prior_strength, 0.2 AS global_mean, 10 AS total_mentions, 0.8 AS local_mean, 0.5 AS std_score
),
calculated AS (
    SELECT
        SAFE_DIVIDE(prior_strength * global_mean + total_mentions * local_mean, prior_strength + total_mentions) AS bayesian_score,
        SAFE_DIVIDE(std_score, ABS(local_mean) + 0.1) AS controversy_index
    FROM fixture
)
SELECT *
FROM calculated
WHERE ABS(bayesian_score - 0.3) > 0.000001
   OR ABS(controversy_index - 0.5555555556) > 0.000001
