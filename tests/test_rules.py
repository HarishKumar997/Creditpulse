from decimal import Decimal

from creditpulse.generate import loan_defect, repayment_defects
from creditpulse.rules import (
    completion_rate,
    delinquency_bucket,
    loan_reject_reason,
    next_watermark,
    repayment_reject_reason,
)


def test_delinquency_bucket_boundaries():
    assert delinquency_bucket(-1) == "current"
    assert delinquency_bucket(0) == "current"
    assert delinquency_bucket(1) == "dpd_1_30"
    assert delinquency_bucket(30) == "dpd_1_30"
    assert delinquency_bucket(31) == "dpd_31_60"
    assert delinquency_bucket(60) == "dpd_31_60"
    assert delinquency_bucket(61) == "dpd_61_90"
    assert delinquency_bucket(90) == "dpd_61_90"
    assert delinquency_bucket(91) == "dpd_90_plus"


def test_completion_rate_zero_due_is_undefined():
    assert completion_rate(Decimal("0"), Decimal("0")) is None
    assert completion_rate(Decimal("10"), Decimal("0")) is None
    assert completion_rate(Decimal("5"), Decimal("10")) == Decimal("0.5000")


def test_watermark_does_not_move_backward():
    assert next_watermark(None, "2024-01-02T00:00:00Z") == "2024-01-02T00:00:00Z"
    assert next_watermark("2024-05-01T00:00:00Z", "2024-01-01T00:00:00Z") == "2024-05-01T00:00:00Z"
    assert next_watermark("2024-05-01T00:00:00Z", "2024-06-01T00:00:00Z") == "2024-06-01T00:00:00Z"
    assert next_watermark("2024-05-01T00:00:00Z", None) == "2024-05-01T00:00:00Z"


def test_injected_defects_have_expected_reasons():
    loans = {"loan-000000"}
    reasons = [repayment_reject_reason(row, loans) for row in repayment_defects()]
    assert reasons == [row["reason"] for row in repayment_defects()]
    assert loan_reject_reason(loan_defect(), {"acct-000000"}) == "BAD_DATE_ORDER"
