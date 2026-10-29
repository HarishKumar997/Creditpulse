from __future__ import annotations

import json
from pathlib import Path

import psycopg
import pyarrow.parquet as pq

from creditpulse.config import ROOT, postgres_dsn
from creditpulse.rules import next_watermark

SCHEMA_PATH = ROOT / "warehouse" / "sql" / "001_creditpulse.sql"


def connect(*, autocommit: bool = False) -> psycopg.Connection:
    return psycopg.connect(postgres_dsn(), autocommit=autocommit)


def statements(sql: str) -> list[str]:
    parts: list[str] = []
    buffer: list[str] = []
    in_dollar = False
    for line in sql.splitlines():
        if line.strip().startswith("--") and not in_dollar:
            continue
        buffer.append(line)
        if "$$" in line:
            if line.count("$$") % 2 == 1:
                in_dollar = not in_dollar
        if not in_dollar and line.rstrip().endswith(";"):
            text = "\n".join(buffer).strip()
            if text:
                parts.append(text)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        parts.append(tail)
    return parts


def ensure_schema(conn: psycopg.Connection | None = None) -> None:
    own = conn is None
    if conn is None:
        conn = connect(autocommit=True)
    try:
        for statement in statements(SCHEMA_PATH.read_text(encoding="utf-8")):
            conn.execute(statement)
        if not own:
            conn.commit()
    finally:
        if own:
            conn.close()


def reset_database(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        truncate table
            staging.repayment,
            staging.loan,
            staging.account,
            staging.customer_version,
            staging.quarantine,
            ops.pipeline_run,
            ops.source_watermark,
            ops.committed_batch
        """
    )
    conn.commit()


def _read_parquet(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return pq.read_table(path).to_pylist()


def _copy_and_merge(
    conn: psycopg.Connection, create_sql: str, copy_sql: str, merge_sql: str, rows: list[tuple]
) -> None:
    if not rows:
        return
    with conn.cursor() as cur:
        cur.execute(create_sql)
        with cur.copy(copy_sql) as copy:
            for row in rows:
                copy.write_row(row)
        cur.execute(merge_sql)


def load_silver(conn: psycopg.Connection, data_dir: Path, batch_id: str) -> None:
    customers = _read_parquet(data_dir / "silver" / "customer_version")
    accounts = _read_parquet(data_dir / "silver" / "account")
    loans = _read_parquet(data_dir / "silver" / "loan")
    repayments = _read_parquet(data_dir / "silver" / "repayment")
    quarantine: list[dict] = []
    q_root = data_dir / "quarantine"
    if q_root.exists():
        for source_dir in q_root.iterdir():
            batch_dir = source_dir / f"batch_id={batch_id}"
            quarantine.extend(_read_parquet(batch_dir))

    _copy_and_merge(
        conn,
        """
        create temp table incoming_customer (
            customer_id text, created_at text, region_code text, customer_segment text,
            status text, source_updated_at text, batch_id text
        ) on commit drop
        """,
        "copy incoming_customer from stdin",
        """
        insert into staging.customer_version (
            customer_id, created_at, region_code, customer_segment, status, source_updated_at, batch_id
        )
        select * from incoming_customer
        on conflict (customer_id, source_updated_at) do nothing
        """,
        [
            (
                row["customer_id"],
                row.get("created_at") or None,
                row.get("region_code"),
                row.get("customer_segment"),
                row.get("status"),
                row["source_updated_at"],
                row["batch_id"],
            )
            for row in customers
        ],
    )
    _copy_and_merge(
        conn,
        """
        create temp table incoming_account (
            account_id text, customer_id text, account_type text, opened_at text,
            closed_at text, status text, source_updated_at text, batch_id text
        ) on commit drop
        """,
        "copy incoming_account from stdin",
        """
        insert into staging.account (
            account_id, customer_id, account_type, opened_at, closed_at, status, source_updated_at, batch_id
        )
        select * from incoming_account
        on conflict (account_id) do update set
            customer_id = excluded.customer_id,
            account_type = excluded.account_type,
            opened_at = excluded.opened_at,
            closed_at = excluded.closed_at,
            status = excluded.status,
            source_updated_at = excluded.source_updated_at,
            batch_id = excluded.batch_id
        where excluded.source_updated_at >= staging.account.source_updated_at
        """,
        [
            (
                row["account_id"],
                row["customer_id"],
                row.get("account_type"),
                row.get("opened_at"),
                row.get("closed_at") or None,
                row.get("status"),
                row["source_updated_at"],
                row["batch_id"],
            )
            for row in accounts
        ],
    )
    _copy_and_merge(
        conn,
        """
        create temp table incoming_loan (
            loan_id text, account_id text, product_code text, principal_amount text,
            annual_rate text, origination_date text, maturity_date text, loan_status text,
            source_updated_at text, batch_id text
        ) on commit drop
        """,
        "copy incoming_loan from stdin",
        """
        insert into staging.loan (
            loan_id, account_id, product_code, principal_amount, annual_rate,
            origination_date, maturity_date, loan_status, source_updated_at, batch_id
        )
        select
            loan_id, account_id, product_code, principal_amount::numeric, annual_rate::numeric,
            origination_date::date, maturity_date::date, loan_status, source_updated_at, batch_id
        from incoming_loan
        on conflict (loan_id) do update set
            account_id = excluded.account_id,
            product_code = excluded.product_code,
            principal_amount = excluded.principal_amount,
            annual_rate = excluded.annual_rate,
            origination_date = excluded.origination_date,
            maturity_date = excluded.maturity_date,
            loan_status = excluded.loan_status,
            source_updated_at = excluded.source_updated_at,
            batch_id = excluded.batch_id
        where excluded.source_updated_at >= staging.loan.source_updated_at
        """,
        [
            (
                row["loan_id"],
                row["account_id"],
                row["product_code"],
                row["principal_amount"],
                row["annual_rate"],
                row["origination_date"],
                row["maturity_date"],
                row["loan_status"],
                row["source_updated_at"],
                row["batch_id"],
            )
            for row in loans
        ],
    )
    _copy_and_merge(
        conn,
        """
        create temp table incoming_repayment (
            repayment_id text, loan_id text, event_timestamp text, due_amount text,
            paid_amount text, payment_status text, source_updated_at text, batch_id text
        ) on commit drop
        """,
        "copy incoming_repayment from stdin",
        """
        insert into staging.repayment (
            repayment_id, loan_id, event_timestamp, due_amount, paid_amount,
            payment_status, source_updated_at, batch_id
        )
        select
            repayment_id, loan_id, event_timestamp::timestamptz, due_amount::numeric,
            paid_amount::numeric, payment_status, source_updated_at, batch_id
        from incoming_repayment
        on conflict (repayment_id) do update set
            loan_id = excluded.loan_id,
            event_timestamp = excluded.event_timestamp,
            due_amount = excluded.due_amount,
            paid_amount = excluded.paid_amount,
            payment_status = excluded.payment_status,
            source_updated_at = excluded.source_updated_at,
            batch_id = excluded.batch_id
        where excluded.source_updated_at >= staging.repayment.source_updated_at
        """,
        [
            (
                row["repayment_id"],
                row["loan_id"],
                row["event_timestamp"],
                row["due_amount"],
                row["paid_amount"],
                row["payment_status"],
                row["source_updated_at"],
                row["batch_id"],
            )
            for row in repayments
        ],
    )
    _copy_and_merge(
        conn,
        """
        create temp table incoming_quarantine (
            source_name text, business_key text, reject_reason text, batch_id text, payload text
        ) on commit drop
        """,
        "copy incoming_quarantine from stdin",
        """
        insert into staging.quarantine (source_name, business_key, reject_reason, batch_id, payload)
        select source_name, business_key, reject_reason, batch_id, payload::jsonb
        from incoming_quarantine
        on conflict (source_name, business_key, batch_id) do nothing
        """,
        [
            (
                row.get("source_name") or "",
                row["business_key"],
                row["reject_reason"],
                row["batch_id"],
                json.dumps({key: value for key, value in row.items() if key != "business_key"}),
            )
            for row in quarantine
        ],
    )


def is_committed(conn: psycopg.Connection, batch_id: str) -> bool:
    row = conn.execute(
        "select 1 from ops.committed_batch where batch_id = %s",
        (batch_id,),
    ).fetchone()
    return row is not None


def commit_success(conn: psycopg.Connection, manifest: dict, run_id: str) -> None:
    """Advance cursors only after staging, dbt, and this audit row commit together."""
    for source, seen in (manifest.get("max_updated") or {}).items():
        current = conn.execute(
            "select last_source_updated_at from ops.source_watermark where source_name = %s",
            (source,),
        ).fetchone()
        updated = next_watermark(current[0] if current else None, seen)
        conn.execute(
            """
            insert into ops.source_watermark (source_name, last_source_updated_at, last_success_run_id, updated_at)
            values (%s, %s, %s, now())
            on conflict (source_name) do update set
                last_source_updated_at = excluded.last_source_updated_at,
                last_success_run_id = excluded.last_success_run_id,
                updated_at = now()
            """,
            (source, updated, run_id),
        )
    conn.execute(
        """
        insert into ops.committed_batch (batch_id, run_id) values (%s, %s)
        on conflict (batch_id) do nothing
        """,
        (manifest["batch_id"], run_id),
    )
    _insert_run(conn, manifest, run_id, "success", None)


def record_run(
    conn: psycopg.Connection,
    manifest: dict,
    run_id: str,
    status: str,
    error_summary: str | None,
    step: str | None = None,
) -> None:
    _insert_run(conn, manifest, run_id, status, error_summary, step)


def _insert_run(conn, manifest, run_id, status, error_summary, step=None) -> None:
    conn.execute(
        """
        insert into ops.pipeline_run (
            run_id, batch_id, status, started_at, finished_at, rows_read, rows_accepted,
            rows_rejected, rows_duplicate, error_summary, step, timings
        ) values (
            %s, %s, %s, %s, now(), %s, %s, %s, %s, %s, %s, %s::jsonb
        )
        """,
        (
            run_id,
            manifest["batch_id"],
            status,
            manifest["started_at"],
            int(manifest.get("rows_read") or 0),
            int(manifest.get("rows_accepted") or 0),
            int(manifest.get("rows_rejected") or 0),
            int(manifest.get("rows_duplicate") or 0),
            error_summary,
            step,
            json.dumps(manifest.get("timings") or {}),
        ),
    )


def reconciliation(conn: psycopg.Connection) -> dict:
    row = conn.execute(
        """
        select
            (select coalesce(sum(due_amount), 0) from staging.repayment),
            (select coalesce(sum(due_amount), 0) from gold.fact_repayment),
            (select coalesce(sum(paid_amount), 0) from staging.repayment),
            (select coalesce(sum(paid_amount), 0) from gold.fact_repayment),
            (select count(*) from staging.repayment),
            (select count(*) from gold.fact_repayment)
        """
    ).fetchone()
    due_ok = row[0] == row[1]
    paid_ok = row[2] == row[3]
    count_ok = row[4] == row[5]
    return {
        "status": "pass" if due_ok and paid_ok and count_ok else "fail",
        "staging_due": row[0],
        "gold_due": row[1],
        "staging_paid": row[2],
        "gold_paid": row[3],
        "staging_rows": row[4],
        "gold_rows": row[5],
    }


def bucket_parity(conn: psycopg.Connection, days: int) -> str:
    row = conn.execute("select refdata.delinquency_bucket(%s)", (days,)).fetchone()
    return row[0]
