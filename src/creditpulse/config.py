from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "1"
AS_OF_DEFAULT = "2024-12-31"
OPEN_ENDED = "9999-12-31T00:00:00Z"

VALID_PAYMENT_STATUS = frozenset({"paid", "partial", "late", "missed", "scheduled"})
VALID_CUSTOMER_SEGMENT = frozenset({"retail", "sme", "premium"})
VALID_CUSTOMER_STATUS = frozenset({"active", "dormant", "closed"})
VALID_ACCOUNT_TYPE = frozenset({"checking", "savings", "credit"})
VALID_ACCOUNT_STATUS = frozenset({"open", "closed"})
VALID_LOAN_STATUS = frozenset({"current", "delinquent", "closed", "paid_off"})
VALID_PRODUCT = frozenset({"PL", "HL", "AL", "CC"})

CUSTOMER_FIELDS = [
    "customer_id",
    "created_at",
    "region_code",
    "customer_segment",
    "status",
    "source_updated_at",
]
ACCOUNT_FIELDS = [
    "account_id",
    "customer_id",
    "account_type",
    "opened_at",
    "closed_at",
    "status",
    "source_updated_at",
]
LOAN_FIELDS = [
    "loan_id",
    "account_id",
    "product_code",
    "principal_amount",
    "annual_rate",
    "origination_date",
    "maturity_date",
    "loan_status",
    "source_updated_at",
]
REPAYMENT_FIELDS = [
    "repayment_id",
    "loan_id",
    "event_timestamp",
    "due_amount",
    "paid_amount",
    "payment_status",
    "source_updated_at",
]
EVENT_FIELDS = [
    "event_id",
    "entity_type",
    "operation",
    "event_timestamp",
    "payload",
    "source_updated_at",
]
META_FIELDS = ["batch_id", "source_name", "ingested_at", "schema_version"]


def data_dir() -> Path:
    raw = os.environ.get("CREDITPULSE_DATA_DIR")
    path = Path(raw) if raw else ROOT / "data" / "generated"
    return path if path.is_absolute() else ROOT / path


def web_data_dir() -> Path:
    return ROOT / "web" / "data"


def dbt_dir() -> Path:
    return ROOT / "transformations" / "dbt"


def postgres_dsn() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "creditpulse")
    password = os.environ.get("POSTGRES_PASSWORD", "creditpulse")
    dbname = os.environ.get("POSTGRES_DB", "creditpulse")
    return f"host={host} port={port} dbname={dbname} user={user} " f"password={password} application_name=creditpulse"


def batch_id_for(seed: int, repayments: int) -> str:
    return f"seed-{seed}-n-{repayments}"
