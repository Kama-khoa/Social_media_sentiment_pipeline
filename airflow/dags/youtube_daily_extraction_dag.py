from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'elt_pipeline',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'youtube_daily_extraction_dag',
    default_args=default_args,
    description='Daily ELT extraction and dbt transformation',
    schedule_interval='0 19 * * *', # 2:00 AM UTC+7 (19:00 UTC)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['elt', 'daily'],
) as dag:

    extract_videos = BashOperator(
        task_id='extract_videos',
        bash_command='python -m elt.main --mode videos --date {{ ds }} --run-id {{ run_id }}',
        cwd='/opt/airflow',
    )

    extract_comments = BashOperator(
        task_id='extract_comments',
        bash_command='python -m elt.main --mode comments --date {{ ds }} --run-id {{ run_id }}',
        cwd='/opt/airflow',
    )

    dbt_run = BashOperator(
        task_id='dbt_run',
        # Assuming dbt is installed and profiles.yml is configured in the environment
        bash_command='cd /opt/airflow/transform && dbt run',
        # Note: Need to update the cd path to match the actual deployment path in production
    )

    extract_videos >> extract_comments >> dbt_run
