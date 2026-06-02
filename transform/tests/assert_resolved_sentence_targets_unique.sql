SELECT sentence_id, product_id, COUNT(*) AS duplicate_count
FROM {{ ref('int_sentence_product_targets') }}
WHERE resolution_status = 'resolved'
GROUP BY sentence_id, product_id
HAVING COUNT(*) > 1
