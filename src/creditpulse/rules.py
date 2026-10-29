from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from creditpulse.config import (
    VALID_ACCOUNT_STATUS,
    VALID_ACCOUNT_TYPE,
    VALID_CUSTOMER_SEGMENT,
    VALID_CUSTOMER_STATUS,
    VALID_LOAN_STATUS,
    VALID_PAYMENT_STATUS,
    VALID_PRODUCT,
)


def present(value: object) -> bool:
    return value is not None and str(value).strip() != ""


def parse_decimal(value: object) -> Decimal | None | str:
    if not present(value):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "INVALID"


def parse_timestamp(value: object) -> datetime | None | str:
    if not present(value):
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return "INVALID"


def parse_date(value: object) -> date | None | str:
    if not present(value):
        return None
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return "INVALID"


def delinquency_bucket(days_past_due: int) -> str:
    """Point-in-time bucket. Day 0 is current. Boundaries are inclusive on the right."""
    if days_past_due <= 0:
        return "current"
    if days_past_due <= 30:
        return "dpd_1_30"
    if days_past_due <= 60:
        return "dpd_31_60"
    if days_past_due <= 90:
        return "dpd_61_90"
    return "dpd_90_plus"


def completion_rate(paid: Decimal, due: Decimal) -> Decimal | None:
    """Paid divided by due. A zero due amount is undefined, not infinite."""
    if due == 0:
        return None
    return (paid / due).quantize(Decimal("0.0001"))


def next_watermark(current: str | None, seen_max: str | None) -> str | None:
    """Move the cursor forward only. A late older timestamp must not pull it backward."""
    if seen_max is None or seen_max == "":
        return current
    if current is None or current == "" or seen_max > current:
        return seen_max
    return current


def customer_reject_reason(row: dict) -> str | None:
    if not present(row.get("customer_id")) or not present(row.get("source_updated_at")):
        return "MISSING_REQUIRED"
    if not present(row.get("region_code")) or not present(row.get("created_at")):
        return "MISSING_REQUIRED"
    if parse_timestamp(row.get("created_at")) == "INVALID":
        return "INVALID_TYPE"
    if parse_timestamp(row.get("source_updated_at")) == "INVALID":
        return "INVALID_TYPE"
    segment = str(row.get("customer_segment") or "").strip().lower()
    status = str(row.get("status") or "").strip().lower()
    if segment not in VALID_CUSTOMER_SEGMENT or status not in VALID_CUSTOMER_STATUS:
        return "UNKNOWN_STATUS"
    return None


def account_reject_reason(row: dict, valid_customer_ids: set[str]) -> str | None:
    if not present(row.get("account_id")) or not present(row.get("customer_id")):
        return "MISSING_REQUIRED"
    if not present(row.get("opened_at")) or not present(row.get("source_updated_at")):
        return "MISSING_REQUIRED"
    if parse_date(row.get("opened_at")) == "INVALID":
        return "INVALID_TYPE"
    if present(row.get("closed_at")) and parse_date(row.get("closed_at")) == "INVALID":
        return "INVALID_TYPE"
    opened = parse_date(row.get("opened_at"))
    closed = parse_date(row.get("closed_at")) if present(row.get("closed_at")) else None
    if isinstance(opened, date) and isinstance(closed, date) and closed < opened:
        return "BAD_DATE_ORDER"
    account_type = str(row.get("account_type") or "").strip().lower()
    status = str(row.get("status") or "").strip().lower()
    if account_type not in VALID_ACCOUNT_TYPE or status not in VALID_ACCOUNT_STATUS:
        return "UNKNOWN_STATUS"
    if str(row["customer_id"]) not in valid_customer_ids:
        return "ORPHAN_FK"
    return None


def loan_reject_reason(row: dict, valid_account_ids: set[str]) -> str | None:
    if not present(row.get("loan_id")) or not present(row.get("account_id")):
        return "MISSING_REQUIRED"
    principal = parse_decimal(row.get("principal_amount"))
    rate = parse_decimal(row.get("annual_rate"))
    opened = parse_date(row.get("origination_date"))
    matured = parse_date(row.get("maturity_date"))
    if principal is None or rate is None or opened is None or matured is None:
        return "MISSING_REQUIRED"
    if "INVALID" in (principal, rate, opened, matured):
        return "INVALID_TYPE"
    if not present(row.get("source_updated_at")):
        return "MISSING_REQUIRED"
    if principal < 0 or rate < 0:
        return "NEGATIVE_AMOUNT"
    if isinstance(opened, date) and isinstance(matured, date) and matured < opened:
        return "BAD_DATE_ORDER"
    if str(row.get("product_code") or "") not in VALID_PRODUCT:
        return "UNKNOWN_STATUS"
    if str(row.get("loan_status") or "").strip().lower() not in VALID_LOAN_STATUS:
        return "UNKNOWN_STATUS"
    if str(row["account_id"]) not in valid_account_ids:
        return "ORPHAN_FK"
    return None


def repayment_reject_reason(row: dict, valid_loan_ids: set[str]) -> str | None:
    if not present(row.get("repayment_id")) or not present(row.get("loan_id")):
        return "MISSING_REQUIRED"
    due = parse_decimal(row.get("due_amount"))
    paid = parse_decimal(row.get("paid_amount"))
    event = parse_timestamp(row.get("event_timestamp"))
    updated = parse_timestamp(row.get("source_updated_at"))
    if due is None or paid is None or event is None or updated is None:
        return "MISSING_REQUIRED"
    if "INVALID" in (due, paid, event, updated):
        return "INVALID_TYPE"
    if due < 0 or paid < 0:
        return "NEGATIVE_AMOUNT"
    status = str(row.get("payment_status") or "").strip().lower()
    if status not in VALID_PAYMENT_STATUS:
        return "UNKNOWN_STATUS"
    if str(row["loan_id"]) not in valid_loan_ids:
        return "ORPHAN_FK"
    return None


def event_reject_reason(row: dict, valid_customer_ids: set[str]) -> str | None:
    if not present(row.get("event_id")) or not present(row.get("payload")):
        return "MISSING_REQUIRED"
    if parse_timestamp(row.get("source_updated_at")) in (None, "INVALID"):
        return "MISSING_REQUIRED" if not present(row.get("source_updated_at")) else "INVALID_TYPE"
    if str(row.get("entity_type") or "") != "customer":
        return "UNKNOWN_STATUS"
    try:
        import json

        payload = json.loads(str(row["payload"]))
    except json.JSONDecodeError:
        return "INVALID_TYPE"
    customer_id = str(payload.get("customer_id") or "")
    if not customer_id:
        return "MISSING_REQUIRED"
    if customer_id not in valid_customer_ids:
        return "ORPHAN_FK"
    return None
