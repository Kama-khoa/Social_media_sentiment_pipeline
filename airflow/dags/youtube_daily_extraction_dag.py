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

    run_youtube_elt = BashOperator(
        task_id='run_youtube_elt',
        bash_command='python -m elt.main --mode full --date {{ ds }} --run-id "{{ dag_run.run_id }}"',
        cwd='/opt/airflow',
    )

    prepare_downstream_models = BashOperator(
        task_id='prepare_downstream_models',
        bash_command=(
            'python scripts/dbt/dbt_runner.py run '
            '--select stg_youtube_videos stg_youtube_comments '
            'int_video_product_mentions int_comment_sentences'
        ),
        cwd='/opt/airflow',
    )

    run_youtube_elt >> prepare_downstream_models
