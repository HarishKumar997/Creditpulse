"""Fails publish once, then the retry commits without duplicating facts."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

BATCH = "retry-demo"
ROOT = "cd /opt/airflow/project && python -m creditpulse.cli"

default_args = {
    "owner": "creditpulse",
    "retries": 1,
    "retry_delay": timedelta(seconds=15),
    "execution_timeout": timedelta(minutes=45),
}


def task(task_id: str, command: str, **kwargs) -> BashOperator:
    return BashOperator(
        task_id=task_id,
        bash_command=(
            f"{ROOT} {command} --batch-id {BATCH} "
            "--run-id {{ run_id }}-" + task_id + "-{{ ti.try_number }}"
        ),
        append_env=True,
        **kwargs,
    )


with DAG(
    dag_id="creditpulse_retry_demo",
    description="Simulates a crash before the watermark commit, then retries.",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    default_args=default_args,
    tags=["creditpulse"],
) as dag:
    generate = task("generate", "generate --seed 7 --repayments 200")
    ingest = task("ingest", "ingest")
    transform = task("transform", "transform")
    load = task("load", "load")
    dbt = task("dbt", "dbt")
    publish = task(
        "publish",
        "publish --fail-once",
        env={"CREDITPULSE_FAIL_ONCE": "1"},
        retries=1,
    )
    generate >> ingest >> transform >> load >> dbt >> publish
