from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor

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
    tags=['nlp', 'daily'],
) as dag:

    # Wait for the daily extraction DAG to complete
    wait_for_extraction = ExternalTaskSensor(
        task_id='wait_for_extraction',
        external_dag_id='youtube_daily_extraction_dag',
        external_task_id='dbt_run',
        allowed_states=['success'],
        failed_states=['failed', 'skipped'],
    )

    run_nlp_inference = BashOperator(
        task_id='run_nlp_inference',
        bash_command=(
            'cd /opt/airflow && '
            'python -m nlp.runner '
            '--limit 500 '
            '--dag-run-id "{{ dag_run.run_id }}"'
        ),
    )

    promote_nlp_results = BashOperator(
        task_id='promote_nlp_results',
        bash_command=(
            'cd /opt/airflow/transform && '
            'dbt run --profiles-dir . --select int_sentiment_results int_video_product_mentions int_sentence_product_targets int_product_resolution_candidates && '
            'cd /opt/airflow && python -m nlp.product_target_resolver --limit 100 && '
            'cd /opt/airflow/transform && dbt run --profiles-dir . --select int_video_product_mentions int_sentence_product_targets fact_product_mentions'
        ),
    )

    wait_for_extraction >> run_nlp_inference >> promote_nlp_results
