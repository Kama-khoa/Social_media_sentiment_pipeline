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

    # Placeholder for the actual NLP pipeline execution
    run_nlp_inference = BashOperator(
        task_id='run_nlp_inference',
        bash_command='echo "Running NLP inference pipeline..." && sleep 5',
    )

    wait_for_extraction >> run_nlp_inference
