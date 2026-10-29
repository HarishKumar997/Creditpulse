from pathlib import Path


def test_sample_customer_header():
    header = Path("data/samples/customers.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header == "customer_id,created_at,region_code,customer_segment,status,source_updated_at"


def test_airflow_dags_declare_dependencies_and_retries():
    daily = Path("orchestration/airflow/dags/creditpulse_daily.py").read_text(encoding="utf-8")
    retry = Path("orchestration/airflow/dags/creditpulse_retry_demo.py").read_text(encoding="utf-8")
    for name in ("generate", "ingest", "transform", "load", "dbt", "publish"):
        assert f'task("{name}"' in daily or f'task("{name}"' in daily
    assert '"retries": 2' in daily
    assert "execution_timeout" in daily
    assert "generate >> ingest >> transform >> load >> dbt >> publish" in daily
    assert "--fail-once" in retry
    assert "CREDITPULSE_FAIL_ONCE" in retry
    assert "retries=1" in retry
    assert "generate >> ingest >> transform >> load >> dbt >> publish" in retry
