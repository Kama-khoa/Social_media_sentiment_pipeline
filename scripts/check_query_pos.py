q1 = """
        SELECT * FROM `project.dataset.product_detail_change_requests`
        WHERE status = @status
        ORDER BY created_at DESC
        """

q2 = """
            SELECT * FROM `project.dataset.product_resolution_candidates`
            WHERE status=@status
            ORDER BY created_at DESC
            LIMIT @limit OFFSET @offset
        """

q3 = """
        SELECT * FROM (
            SELECT candidate_id, source_type, source_id, candidate_text, status,
                   resolved_product_id, reviewed_by, reviewed_at, created_at,
                   resolver_confidence, resolver_reason, resolution_method
            FROM `project.dataset.product_resolution_candidates`
            WHERE status='pending'
            
            UNION ALL
            
            SELECT c.candidate_id, c.source_type, c.source_id, c.candidate_text, 'pending' as status,
                   CAST(NULL AS STRING) as resolved_product_id, CAST(NULL AS STRING) as reviewed_by, 
                   CAST(NULL AS TIMESTAMP) as reviewed_at, c.created_at, 
                   CAST(NULL AS FLOAT64) as resolver_confidence, CAST(NULL AS STRING) as resolver_reason, 
                   CAST(NULL AS STRING) as resolution_method
            FROM `project.dataset_intermediate.int_product_resolution_candidates` c
            LEFT JOIN `project.dataset.product_resolution_candidates` r
              ON c.candidate_id = r.candidate_id
            WHERE r.candidate_id IS NULL
        )
        ORDER BY created_at DESC
        LIMIT @limit OFFSET @offset
        """

q4 = """
            SELECT channel_id, channel_name, channel_url, channel_handle,
                   subscriber_count, is_active, is_historically_scanned,
                   created_at, last_updated_at
            FROM `project.dataset.channel_config`
            ORDER BY is_active DESC, channel_name ASC
            """

q5 = """
        SELECT dag_run_id
        FROM `project.dataset.raw_sentiment_results`
        ORDER BY created_at DESC
        LIMIT 1
        """

for i, q in enumerate([q1, q2, q3, q4, q5], 1):
    lines = q.split('\n')
    for line_idx, line in enumerate(lines, 1):
        if 'created_at' in line:
            col = line.index('created_at') + 1
            print(f'q{i} -> line {line_idx}, char {col}')
