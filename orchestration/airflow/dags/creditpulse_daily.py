"""Daily batch. Tasks call the same Python entrypoints as the local CLI."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

BATCH = "daily-demo"
ROOT = "cd /opt/airflow/project && python -m creditpulse.cli"

default_args = {
    "owner": "creditpulse",
    "retries": 2,
    "retry_delay": timedelta(seconds=30),
    "execution_timeout": timedelta(minutes=45),
}


def task(task_id: str, command: str) -> BashOperator:
    return BashOperator(
        task_id=task_id,
        bash_command=(
            f"{ROOT} {command} --batch-id {BATCH} "
            "--run-id {{ run_id }}-" + task_id + "-{{ ti.try_number }}"
        ),
        append_env=True,
    )


with DAG(
    dag_id="creditpulse_daily",
    description="Synthetic credit portfolio batch. Safe to rerun.",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    default_args=default_args,
    tags=["creditpulse"],
) as dag:
    generate = task("generate", "generate --seed 42 --repayments 2000")
    ingest = task("ingest", "ingest")
    transform = task("transform", "transform")
    load = task("load", "load")
    dbt = task("dbt", "dbt")
    publish = task("publish", "publish")
    generate >> ingest >> transform >> load >> dbt >> publish
