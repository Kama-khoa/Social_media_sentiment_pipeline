from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

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
    start_date=datetime(2026, 6, 16),
    catchup=False,
    max_active_runs=1,
    max_active_tasks=1,
    tags=["analytics", "daily"],
) as dag:

    ensure_mart_tables = BashOperator(
        task_id="ensure_mart_tables",
        bash_command="python -m schema.layer_4_marts.init_marts_tables",
        cwd="/opt/airflow",
    )

    rebuild_analytics_marts = BashOperator(
        task_id="rebuild_analytics_marts",
        bash_command=(
            "python scripts/dbt/dbt_runner.py run "
            "--select int_sentiment_results int_sentence_product_targets "
            "fact_product_mentions dim_products agg_daily_product_ranking"
        ),
        cwd="/opt/airflow",
    )

    run_pelt_attribution = BashOperator(
        task_id="run_pelt_attribution",
        bash_command="python -m analytics.pelt_attribution",
        cwd="/opt/airflow",
    )

    ensure_mart_tables >> rebuild_analytics_marts >> run_pelt_attribution
