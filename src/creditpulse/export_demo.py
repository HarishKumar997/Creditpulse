from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg

DISCLAIMER = (
    "Synthetic demonstration data only. CreditPulse does not make lending decisions " "and is not a credit bureau."
)

BUCKET_LABELS = {
    "current": "Current",
    "dpd_1_30": "1–30 days past due",
    "dpd_31_60": "31–60 days past due",
    "dpd_61_90": "61–90 days past due",
    "dpd_90_plus": "90+ days past due",
}


def _money(value) -> str | None:
    if value is None:
        return None
    return f"{Decimal(value):.2f}"


def _rate(value) -> str | None:
    if value is None:
        return None
    return f"{Decimal(value):.4f}"


def _write(directory: Path, name: str, payload: dict | list) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def export_demo(conn: psycopg.Connection, web_dir: Path, manifest: dict) -> None:
    as_of = manifest.get("as_of")
    totals = conn.execute(
        """
        select
            (select count(*) from gold.fact_loan_snapshot),
            (select count(*) from gold.dim_customer where is_current),
            (select coalesce(sum(outstanding_balance_proxy), 0) from gold.fact_loan_snapshot),
            (select sum(paid_amount) / nullif(sum(due_amount), 0) from gold.fact_repayment),
            (
                select count(*) filter (where delinquency_bucket <> 'current')::numeric
                    / nullif(count(*), 0)
                from gold.fact_loan_snapshot
            )
        """
    ).fetchone()
    buckets = conn.execute(
        """
        select delinquency_bucket, count(*)
        from gold.fact_loan_snapshot
        group by 1
        order by 1
        """
    ).fetchall()
    products = conn.execute(
        """
        select
            product_code,
            count(*) as loans,
            coalesce(sum(outstanding_balance_proxy), 0) as outstanding_balance_proxy,
            count(*) filter (where delinquency_bucket <> 'current') as delinquent_loans
        from gold.fact_loan_snapshot
        group by 1
        order by 1
        """
    ).fetchall()
    reasons = conn.execute(
        """
        select reject_reason, count(*)
        from staging.quarantine
        where batch_id = %s
        group by 1
        order by 1
        """,
        (manifest["batch_id"],),
    ).fetchall()
    runs = conn.execute(
        """
        select run_id, batch_id, status, started_at, finished_at, rows_read, rows_accepted,
               rows_rejected, rows_duplicate, error_summary, step
        from ops.pipeline_run
        order by started_at desc
        limit 20
        """
    ).fetchall()
    daily = conn.execute(
        """
        select report_date, product_code, repayment_count, loan_count, due_amount, paid_amount,
               repayment_completion_rate, delinquent_event_count
        from gold.agg_portfolio_daily
        order by report_date, product_code
        """
    ).fetchall()
    from creditpulse.warehouse import reconciliation

    check = reconciliation(conn)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = {
        "schema_version": "1",
        "disclaimer": DISCLAIMER,
        "as_of_date": as_of,
        "generated_at": generated_at,
        "batch_id": manifest["batch_id"],
        "loans": int(totals[0]),
        "customers": int(totals[1]),
        "outstanding_balance_proxy": _money(totals[2]),
        "repayment_completion_rate": _rate(totals[3]),
        "delinquency_rate": _rate(totals[4]),
        "accepted": int(manifest.get("rows_accepted") or 0),
        "rejected": int(manifest.get("rows_rejected") or 0),
        "duplicates": int(manifest.get("rows_duplicate") or 0),
        "buckets": [
            {
                "id": bucket,
                "label": BUCKET_LABELS.get(bucket, bucket),
                "loans": int(count),
            }
            for bucket, count in buckets
        ],
        "products": [
            {
                "product_code": code,
                "loans": int(loans),
                "outstanding_balance_proxy": _money(outstanding),
                "delinquent_loans": int(delinquent),
            }
            for code, loans, outstanding, delinquent in products
        ],
    }
    quality = {
        "schema_version": "1",
        "disclaimer": DISCLAIMER,
        "batch_id": manifest["batch_id"],
        "generated_at": generated_at,
        "rejected_by_reason": [{"reason": reason, "rows": int(count)} for reason, count in reasons],
        "reconciliation": {
            "status": check["status"],
            "due_amount": _money(check["gold_due"]),
            "paid_amount": _money(check["gold_paid"]),
            "rows": int(check["gold_rows"]),
        },
    }
    run_payload = {
        "schema_version": "1",
        "disclaimer": DISCLAIMER,
        "runs": [
            {
                "run_id": item[0],
                "batch_id": item[1],
                "status": item[2],
                "started_at": item[3].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "finished_at": None if item[4] is None else item[4].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "rows_read": item[5],
                "rows_accepted": item[6],
                "rows_rejected": item[7],
                "rows_duplicate": item[8],
                "error_summary": item[9],
                "step": item[10],
            }
            for item in runs
        ],
    }
    portfolio = {
        "schema_version": "1",
        "disclaimer": DISCLAIMER,
        "rows": [
            {
                "report_date": item[0].isoformat(),
                "product_code": item[1],
                "repayment_count": int(item[2]),
                "loan_count": int(item[3]),
                "due_amount": _money(item[4]),
                "paid_amount": _money(item[5]),
                "repayment_completion_rate": _rate(item[6]),
                "delinquent_event_count": int(item[7]),
            }
            for item in daily
        ],
    }
    _write(web_dir, "summary.json", summary)
    _write(web_dir, "quality.json", quality)
    _write(web_dir, "runs.json", run_payload)
    _write(web_dir, "portfolio_daily.json", portfolio)
