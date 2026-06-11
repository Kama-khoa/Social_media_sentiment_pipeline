from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'nlp_pipeline',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'sentiment_analysis_dag',
    default_args=default_args,
    description='Run NLP sentiment analysis on comment sentences',
    schedule_interval='0 20 * * *', # Run at 3:00 AM UTC+7, after extraction
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    max_active_tasks=1,
    tags=['nlp', 'daily'],
) as dag:

    prepare_comment_sentences = BashOperator(
        task_id='prepare_comment_sentences',
        bash_command=(
            'python scripts/dbt/dbt_runner.py run '
            '--select stg_youtube_comments int_comment_sentences'
        ),
        cwd='/opt/airflow',
    )

    run_nlp_inference = BashOperator(
        task_id='run_nlp_inference',
        bash_command=(
            'python -m nlp.runner '
            '--limit 5000 '
            '--dag-run-id "{{ dag_run.run_id }}"'
        ),
        cwd='/opt/airflow',
    )

    promote_nlp_results = BashOperator(
        task_id='promote_nlp_results',
        bash_command=(
            'python scripts/dbt/dbt_runner.py run '
            '--select int_sentiment_results int_video_product_mentions '
            'int_sentence_product_targets int_product_resolution_candidates'
        ),
        cwd='/opt/airflow',
    )

    resolve_product_targets = BashOperator(
        task_id='resolve_product_targets',
        bash_command='python -m nlp.product_target_resolver --limit 100 --batch-size 10',
        cwd='/opt/airflow',
    )

    rebuild_fact_product_mentions = BashOperator(
        task_id='rebuild_fact_product_mentions',
        bash_command=(
            'python scripts/dbt/dbt_runner.py run '
            '--select int_video_product_mentions int_sentence_product_targets fact_product_mentions'
        ),
        cwd='/opt/airflow',
    )

    (
        prepare_comment_sentences
        >> run_nlp_inference
        >> promote_nlp_results
        >> resolve_product_targets
        >> rebuild_fact_product_mentions
    )
