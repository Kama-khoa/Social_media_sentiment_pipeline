from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'elt_pipeline',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'seed_sync_dag',
    default_args=default_args,
    description='Sync channels and keywords to BigQuery configs',
    schedule_interval=None, # Run manually
    start_date=datetime(2026, 6, 16),
    catchup=False,
    tags=['elt', 'seed'],
) as dag:

    # Assuming the airflow worker runs in an environment where the project root is in PYTHONPATH
    # or the elt module is installed. Using BashOperator to run the script.
    run_seed_sync = BashOperator(
        task_id='run_seed_sync',
        bash_command='python -m elt.seed_data.seed_loader',
        cwd='/opt/airflow',
    )

    run_seed_sync
