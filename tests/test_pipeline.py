import os
import shutil
import subprocess
import sys
from decimal import Decimal

import pytest

from creditpulse.pipeline import SimulatedFailure, run_batch, run_increment
from creditpulse.rules import delinquency_bucket
from creditpulse.warehouse import (
    bucket_parity,
    connect,
    ensure_schema,
    is_committed,
    reconciliation,
    reset_database,
)


def _java_ok() -> bool:
    java = shutil.which("java")
    if not java:
        return False
    try:
        completed = subprocess.run([java, "-version"], capture_output=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _postgres_ok() -> bool:
    try:
        with connect() as conn:
            conn.execute("select 1")
        return True
    except Exception:
        return False


def _spark_worker_can_start() -> bool:
    """Spark on Windows splits an unquoted interpreter path, so a home directory
    with a space cannot launch the Python worker. The pipeline container is the
    supported runtime there. GitHub Actions uses a path without spaces."""
    if os.name == "nt" and " " in sys.executable and not os.environ.get("GITHUB_ACTIONS"):
        return False
    return _java_ok()


@pytest.fixture(scope="session")
def services():
    if not _spark_worker_can_start() or not _postgres_ok():
        message = (
            "Integration tests need PostgreSQL and a JVM whose Python path has no spaces. "
            "On Windows, run: docker compose -f infra/docker-compose.yml --profile pipeline run --rm pipeline -m pytest"
        )
        if os.environ.get("GITHUB_ACTIONS"):
            pytest.fail(message)
        pytest.skip(message)
    return True


@pytest.fixture
def fresh_db(services):
    with connect() as conn:
        ensure_schema(conn)
        reset_database(conn)


def _fact_count() -> int:
    with connect() as conn:
        return int(conn.execute("select count(*) from gold.fact_repayment").fetchone()[0])


@pytest.mark.integration
def test_rerun_quarantine_and_reconciliation(tmp_path, fresh_db):
    data = tmp_path / "data"
    web = tmp_path / "web"
    manifest = run_batch(
        seed=42,
        repayments=80,
        batch_id="test-base",
        run_id="base-1",
        directory=data,
        web_dir=web,
    )
    assert manifest["rows_rejected"] == 7
    assert manifest["rows_duplicate"] == 2
    with connect() as conn:
        assert _fact_count() == 80
        reasons = dict(conn.execute("select reject_reason, count(*) from staging.quarantine group by 1").fetchall())
        assert reasons == {
            "MISSING_REQUIRED": 2,
            "INVALID_TYPE": 1,
            "NEGATIVE_AMOUNT": 1,
            "UNKNOWN_STATUS": 1,
            "ORPHAN_FK": 1,
            "BAD_DATE_ORDER": 1,
        }
        paid = conn.execute(
            "select paid_amount from gold.fact_repayment where repayment_id = 'repay-0000001'"
        ).fetchone()[0]
        assert paid != Decimal("0.01")
        versions = conn.execute("select count(*) from gold.dim_customer where customer_id = 'cust-000000'").fetchone()[
            0
        ]
        assert versions == 2
        current = conn.execute(
            """
            select customer_segment from gold.dim_customer
            where customer_id = 'cust-000000' and is_current
            """
        ).fetchone()[0]
        assert current == "premium"
        assert reconciliation(conn)["status"] == "pass"
        for days in (-1, 0, 1, 30, 31, 60, 61, 90, 91):
            assert bucket_parity(conn, days) == delinquency_bucket(days)

    run_batch(
        seed=42,
        repayments=80,
        batch_id="test-base",
        run_id="base-2",
        directory=data,
        web_dir=web,
    )
    assert _fact_count() == 80
    with connect() as conn:
        skipped = conn.execute(
            "select count(*) from ops.pipeline_run where error_summary like %s",
            ("Batch already committed%",),
        ).fetchone()[0]
        assert skipped == 1


@pytest.mark.integration
def test_failure_does_not_advance_watermark_and_retry_is_safe(tmp_path, fresh_db):
    data = tmp_path / "retry"
    web = tmp_path / "web"
    with pytest.raises(SimulatedFailure):
        run_batch(
            seed=3,
            repayments=40,
            batch_id="test-retry",
            run_id="retry-fail",
            directory=data,
            web_dir=web,
            fail_once=True,
        )
    with connect() as conn:
        assert is_committed(conn, "test-retry") is False
        assert conn.execute("select count(*) from ops.source_watermark").fetchone()[0] == 0
        failed = conn.execute(
            "select count(*) from ops.pipeline_run where batch_id = 'test-retry' and status = 'failed'"
        ).fetchone()[0]
        assert failed == 1
    before = _fact_count()
    assert before == 40
    run_batch(
        seed=3,
        repayments=40,
        batch_id="test-retry",
        run_id="retry-ok",
        directory=data,
        web_dir=web,
        fail_once=True,
    )
    assert _fact_count() == before
    with connect() as conn:
        assert is_committed(conn, "test-retry") is True
        statuses = {
            row[0]
            for row in conn.execute("select status from ops.pipeline_run where batch_id = 'test-retry'").fetchall()
        }
        assert statuses == {"failed", "success"}


@pytest.mark.integration
def test_incremental_batch_adds_only_new_repayments(tmp_path, fresh_db):
    data = tmp_path / "inc"
    web = tmp_path / "web"
    run_batch(seed=9, repayments=60, batch_id="inc-base", run_id="inc-1", directory=data, web_dir=web)
    before = _fact_count()
    assert before == 60
    run_increment(
        seed=9,
        batch_id="inc-next",
        new_repayments=5,
        loan_count=20,
        directory=data,
        web_dir=web,
        run_id="inc-2",
    )
    assert _fact_count() == before + 5
    run_increment(
        seed=9,
        batch_id="inc-next",
        new_repayments=5,
        loan_count=20,
        directory=data,
        web_dir=web,
        run_id="inc-3",
    )
    assert _fact_count() == before + 5
