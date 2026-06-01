from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor

default_args = {
    "owner": "analytics_pipeline",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "analytics_dag",
    default_args=default_args,
    description="Run Bayesian ranking, controversy index, and PELT attribution after NLP phase",
    schedule_interval="0 22 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["analytics", "daily"],
) as dag:

    wait_for_nlp = ExternalTaskSensor(
        task_id="wait_for_nlp",
        external_dag_id="sentiment_analysis_dag",
        external_task_id="promote_nlp_results",
        allowed_states=["success"],
        failed_states=["failed", "skipped"],
        poke_interval=300,
        timeout=7200,
        mode="poke",
    )

    run_bayesian_ranking = BashOperator(
        task_id="run_bayesian_ranking",
        bash_command="cd /opt/airflow && python -m analytics.bayesian_ranking",
    )

    run_controversy_index = BashOperator(
        task_id="run_controversy_index",
        bash_command="cd /opt/airflow && python -m analytics.controversy_index",
    )

    run_pelt_attribution = BashOperator(
        task_id="run_pelt_attribution",
        bash_command=(
            "cd /opt/airflow && "
            "python -m analytics.pelt_attribution "
            '--dag-run-id "{{ dag_run.run_id }}"'
        ),
    )

    wait_for_nlp >> run_bayesian_ranking >> run_controversy_index >> run_pelt_attribution
