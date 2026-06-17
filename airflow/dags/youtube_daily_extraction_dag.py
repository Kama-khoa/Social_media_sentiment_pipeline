import os
import pendulum
from datetime import datetime, timedelta
from pathlib import Path
from airflow import DAG
from airflow.operators.bash import BashOperator

# Thư mục gốc dự án (hoạt động tốt cả trên local và Docker)
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
local_tz = pendulum.timezone("Asia/Ho_Chi_Minh")

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
    schedule_interval='0 2 * * *', # 2:00 AM local time (Asia/Ho_Chi_Minh)
    start_date=datetime(2025, 1, 1, tzinfo=local_tz),
    catchup=False,
    max_active_runs=1,
    max_active_tasks=1,
    tags=['elt', 'daily'],
) as dag:

    run_youtube_elt = BashOperator(
        task_id='run_youtube_elt',
        bash_command=(
            'python -m elt.main --mode full --date {{ ds }} --run-id "{{ dag_run.run_id }}" '
            '--manual-channel-id "{{ dag_run.conf.get(\'channel_id\', \'\') }}" '
            '--lookback-days "{{ dag_run.conf.get(\'lookback_days\', 30) }}" '
            '--crawl-mode "{{ dag_run.conf.get(\'crawl_mode\', \'api_or_ytdlp\') }}"'
        ),
        cwd=PROJECT_ROOT,
    )

    prepare_downstream_models = BashOperator(
        task_id='prepare_downstream_models',
        bash_command=(
            'python scripts/dbt/dbt_runner.py run '
            '--select stg_youtube_videos stg_youtube_comments '
            'int_video_product_mentions int_comment_sentences'
        ),
        cwd=PROJECT_ROOT,
    )

    run_youtube_elt >> prepare_downstream_models
