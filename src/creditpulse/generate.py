from __future__ import annotations

import csv
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from creditpulse.config import (
    ACCOUNT_FIELDS,
    CUSTOMER_FIELDS,
    EVENT_FIELDS,
    LOAN_FIELDS,
    REPAYMENT_FIELDS,
)

REGIONS = ("R-NORTH", "R-SOUTH", "R-EAST", "R-WEST", "R-CENTRAL")
SEGMENTS = ("retail", "sme", "premium")
CUSTOMER_STATUSES = ("active", "dormant", "closed")
ACCOUNT_TYPES = ("checking", "savings", "credit")
PRODUCTS = ("PL", "HL", "AL", "CC")
LOAN_STATUSES = ("current", "delinquent", "closed", "paid_off")
PAYMENT_STATUSES = ("paid", "partial", "late", "missed", "scheduled")

EVENT_START = datetime(2024, 9, 1, tzinfo=UTC)
EVENT_END = datetime(2024, 12, 30, tzinfo=UTC)


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def landing_dir(data_dir: Path, batch_id: str) -> Path:
    return data_dir / "landing" / batch_id


def repayment_defects() -> list[dict[str, str]]:
    """Fixed bad rows. Counts do not grow with the batch size."""
    common = {
        "event_timestamp": "2024-11-15T00:00:00Z",
        "source_updated_at": "2024-11-15T00:00:00Z",
    }
    return [
        {
            "repayment_id": "bad-missing-loan",
            "loan_id": "",
            "due_amount": "100.00",
            "paid_amount": "100.00",
            "payment_status": "paid",
            "reason": "MISSING_REQUIRED",
            **common,
        },
        {
            "repayment_id": "bad-missing-due",
            "loan_id": "loan-000000",
            "due_amount": "",
            "paid_amount": "10.00",
            "payment_status": "partial",
            "reason": "MISSING_REQUIRED",
            **common,
        },
        {
            "repayment_id": "bad-invalid-paid",
            "loan_id": "loan-000000",
            "due_amount": "80.00",
            "paid_amount": "not-a-number",
            "payment_status": "partial",
            "reason": "INVALID_TYPE",
            **common,
        },
        {
            "repayment_id": "bad-negative",
            "loan_id": "loan-000000",
            "due_amount": "80.00",
            "paid_amount": "-10.00",
            "payment_status": "partial",
            "reason": "NEGATIVE_AMOUNT",
            **common,
        },
        {
            "repayment_id": "bad-status",
            "loan_id": "loan-000000",
            "due_amount": "80.00",
            "paid_amount": "80.00",
            "payment_status": "charged_off",
            "reason": "UNKNOWN_STATUS",
            **common,
        },
        {
            "repayment_id": "bad-orphan",
            "loan_id": "loan-does-not-exist",
            "due_amount": "80.00",
            "paid_amount": "80.00",
            "payment_status": "paid",
            "reason": "ORPHAN_FK",
            **common,
        },
    ]


def loan_defect() -> dict[str, str]:
    return {
        "loan_id": "bad-loan-dates",
        "account_id": "acct-000000",
        "product_code": "PL",
        "principal_amount": "1000.00",
        "annual_rate": "8.50",
        "origination_date": "2024-06-01",
        "maturity_date": "2023-06-01",
        "loan_status": "current",
        "source_updated_at": "2024-06-01T00:00:00Z",
        "reason": "BAD_DATE_ORDER",
    }


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _pick_time(rng: random.Random, start: datetime, end: datetime) -> datetime:
    span = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, max(span, 1)))


def _paid_cents(status: str, due_cents: int, rng: random.Random) -> int:
    if status == "paid":
        return due_cents
    if status == "partial":
        return max(1, due_cents // 2)
    if status == "late":
        return rng.choice((0, max(1, due_cents // 5)))
    return 0


def generate(seed: int, repayments: int, batch_id: str, data_dir: Path) -> dict[str, int]:
    if repayments < 2:
        raise ValueError("repayments must be at least 2 so duplicate fixtures have a source row")
    rng = random.Random(seed)
    n_customers = max(20, repayments // 25)
    customers: list[dict[str, str]] = []
    accounts: list[dict[str, str]] = []
    loans: list[dict[str, str]] = []
    events: list[dict[str, str]] = []

    for i in range(n_customers):
        created = datetime(2022, 1, 1, tzinfo=UTC) + timedelta(days=rng.randint(0, 600))
        segment = rng.choice(SEGMENTS)
        status = rng.choice(CUSTOMER_STATUSES)
        if i == 0:
            segment = "retail"
            status = "active"
        customer_id = f"cust-{i:06d}"
        customers.append(
            {
                "customer_id": customer_id,
                "created_at": iso(created),
                "region_code": rng.choice(REGIONS),
                "customer_segment": segment,
                "status": status,
                "source_updated_at": iso(created),
            }
        )
        opened = created + timedelta(days=rng.randint(1, 30))
        accounts.append(
            {
                "account_id": f"acct-{i:06d}",
                "customer_id": customer_id,
                "account_type": rng.choice(ACCOUNT_TYPES),
                "opened_at": opened.date().isoformat(),
                "closed_at": "",
                "status": "open",
                "source_updated_at": iso(opened),
            }
        )
        originated = opened + timedelta(days=rng.randint(0, 60))
        term_days = rng.choice((365, 730, 1095, 1825))
        principal = rng.randint(100_000, 5_000_000)
        rate_bps = rng.randint(450, 2400)
        loans.append(
            {
                "loan_id": f"loan-{i:06d}",
                "account_id": f"acct-{i:06d}",
                "product_code": rng.choice(PRODUCTS),
                "principal_amount": money(principal),
                "annual_rate": f"{rate_bps // 100}.{rate_bps % 100:02d}",
                "origination_date": originated.date().isoformat(),
                "maturity_date": (originated + timedelta(days=term_days)).date().isoformat(),
                "loan_status": rng.choice(LOAN_STATUSES),
                "source_updated_at": iso(originated),
            }
        )
        if i == 0 or rng.random() < 0.08:
            changed = datetime(2024, 6, 1, tzinfo=UTC) + timedelta(days=rng.randint(0, 20))
            new_segment = "premium" if i == 0 else rng.choice(SEGMENTS)
            payload = {
                "customer_id": customer_id,
                "region_code": customers[-1]["region_code"],
                "customer_segment": new_segment,
                "status": "active" if i == 0 else customers[-1]["status"],
            }
            events.append(
                {
                    "event_id": f"evt-{i:06d}",
                    "entity_type": "customer",
                    "operation": "update",
                    "event_timestamp": iso(changed),
                    "payload": json.dumps(payload, sort_keys=True),
                    "source_updated_at": iso(changed),
                }
            )

    payment_rows: list[dict[str, str]] = []
    for i in range(repayments):
        loan = loans[i % len(loans)]
        event_time = _pick_time(rng, EVENT_START, EVENT_END)
        status = rng.choice(PAYMENT_STATUSES)
        due_cents = rng.randint(2_500, 80_000)
        paid_cents = _paid_cents(status, due_cents, rng)
        updated = event_time + timedelta(hours=rng.randint(0, 48))
        payment_rows.append(
            {
                "repayment_id": f"repay-{i:07d}",
                "loan_id": loan["loan_id"],
                "event_timestamp": iso(event_time),
                "due_amount": money(due_cents),
                "paid_amount": money(paid_cents),
                "payment_status": status,
                "source_updated_at": iso(updated),
            }
        )

    payment_rows.append(dict(payment_rows[0]))
    stale = dict(payment_rows[1])
    stale["source_updated_at"] = "2020-01-01T00:00:00Z"
    stale["paid_amount"] = "0.01"
    payment_rows.append(stale)
    for defect in repayment_defects():
        payment_rows.append({field: defect.get(field, "") for field in REPAYMENT_FIELDS})
    loans.append({field: loan_defect().get(field, "") for field in LOAN_FIELDS})

    folder = landing_dir(data_dir, batch_id)
    _write_csv(folder / "customers.csv", CUSTOMER_FIELDS, customers)
    _write_csv(folder / "accounts.csv", ACCOUNT_FIELDS, accounts)
    _write_csv(folder / "loans.csv", LOAN_FIELDS, loans)
    _write_csv(folder / "events.csv", EVENT_FIELDS, events)
    payload = json.dumps(payment_rows, indent=2, sort_keys=True)
    (folder / "repayments.json").write_text(payload + "\n", encoding="utf-8")
    return {
        "customers": len(customers),
        "accounts": len(accounts),
        "loans": len(loans),
        "events": len(events),
        "repayments": len(payment_rows),
    }


def generate_increment(
    seed: int,
    batch_id: str,
    data_dir: Path,
    new_repayments: int,
    loan_count: int,
) -> dict[str, int]:
    """A later batch of valid repayments. Ids and timestamps do not collide with the base batch."""
    if new_repayments < 1:
        raise ValueError("new_repayments must be at least 1")
    if loan_count < 1:
        raise ValueError("loan_count must be at least 1")
    rng = random.Random(seed + 10_007)
    rows: list[dict[str, str]] = []
    start = datetime(2025, 1, 10, tzinfo=UTC)
    for i in range(new_repayments):
        event_time = start + timedelta(days=i % 10, hours=rng.randint(0, 20))
        due_cents = rng.randint(3_000, 20_000)
        rows.append(
            {
                "repayment_id": f"repay-inc-{i:05d}",
                "loan_id": f"loan-{i % loan_count:06d}",
                "event_timestamp": iso(event_time),
                "due_amount": money(due_cents),
                "paid_amount": money(due_cents),
                "payment_status": "paid",
                "source_updated_at": iso(event_time + timedelta(hours=1)),
            }
        )
    folder = landing_dir(data_dir, batch_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "repayments.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"repayments": len(rows)}
