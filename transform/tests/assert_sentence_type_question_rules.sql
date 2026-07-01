WITH samples AS (
    SELECT 'pin ok' AS sentence_text, 'statement' AS expected_type UNION ALL
    SELECT 'ngon ko kém', 'statement' UNION ALL
    SELECT 'pin có nóng ko', 'question' UNION ALL
    SELECT 'giá tốt không?', 'question' UNION ALL
    SELECT 'nên mua không', 'question'
),
classified AS (
    SELECT
        sentence_text,
        expected_type,
        CASE
            WHEN REGEXP_CONTAINS(LOWER(TRIM(sentence_text)), r'\?\s*$') THEN 'question'
            WHEN REGEXP_CONTAINS(LOWER(TRIM(sentence_text)), r'(^|\s)(bao nhiêu|mấy|sao|tại sao|khi nào|ở đâu)(\s|$)') THEN 'question'
            WHEN REGEXP_CONTAINS(LOWER(TRIM(sentence_text)), r'(^|\s)(có|nên)(\s|[^.!?\n]){1,80}\s(không|ko|k)\s*\??$') THEN 'question'
            WHEN REGEXP_CONTAINS(LOWER(TRIM(sentence_text)), r'(^|\s)(được|tốt|ổn|ngon)\s+(không|ko|k)\s*\??$') THEN 'question'
            ELSE 'statement'
        END AS actual_type
    FROM samples
)
SELECT *
FROM classified
WHERE actual_type != expected_type
