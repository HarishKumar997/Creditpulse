# Data dictionary

All rows are synthetic. None of these fields are a credit-bureau attribute, and none of the metrics are a lending decision.

Currency amounts are synthetic units with two decimal places. `annual_rate` is a percent (12.50 means 12.50%). It is stored for context and is not used in the balance proxy.

## Sources

| Entity | Business key | Notes |
| --- | --- | --- |
| customers | `customer_id` | Versions are kept. The initial row uses `created_at` as `source_updated_at`. |
| accounts | `account_id` | Type 1. Latest `source_updated_at` wins. |
| loans | `loan_id` | `loan_status` is the source label. It is not the delinquency bucket. |
| repayments | `repayment_id` | Delivered by the mock API. |
| customer events | `event_id` | Payload is a customer attribute change. |

## Reject reasons

| Reason | When it is used |
| --- | --- |
| `MISSING_REQUIRED` | A required identifier, amount, or timestamp is blank. |
| `INVALID_TYPE` | A number or timestamp cannot be parsed. |
| `NEGATIVE_AMOUNT` | An amount or rate is below zero. |
| `UNKNOWN_STATUS` | A status, segment, or product code is outside the allowed list. |
| `ORPHAN_FK` | The parent id is not in the accepted parent set. |
| `BAD_DATE_ORDER` | Maturity is before origination, or an account close date is before open. |

The generator always appends six bad repayments, one bad loan, one exact repayment duplicate, and one older replay of `repay-0000001` with `paid_amount` 0.01. Those counts do not grow with the batch size.

`rows_duplicate` counts extra copies in the batch and stale replays that lost the business-key comparison. It does not count a row that was already stored and is still the winner.

## Gold grain

| Table | Grain |
| --- | --- |
| `dim_customer` | One row per customer version. `is_current` marks the latest. |
| `dim_customer_current` | One row per customer, current version only. |
| `dim_account` | One row per account. |
| `dim_loan` | One row per accepted loan. |
| `dim_date` | One row per calendar day from 2022-01-01 through 2026-12-31. |
| `fact_repayment` | One row per accepted repayment event. |
| `fact_loan_snapshot` | One row per loan on the pipeline as-of date (default 2024-12-31). |
| `agg_portfolio_daily` | One row per repayment event date and product code. |

Delinquency is a stock. Daily payments are a flow. They are not stored on the same row, because summing the snapshot across dates would double-count loans.

## Metrics

### Repayment completion rate

`sum(paid_amount) / sum(due_amount)` over the rows in scope.

Exclusions: if the due total is zero, the rate is null. It is not treated as zero or infinity. A single repayment with a zero due amount is allowed only when the value parses; the generator's clean rows use a positive due amount.

### Days past due and delinquency bucket

On the snapshot date, a loan is current when it has no accepted repayment with `paid_amount < due_amount` on or before that date.

Otherwise `days_past_due` is the snapshot date minus the earliest such unpaid event date.

| Days | Bucket |
| --- | --- |
| 0 or less | `current` |
| 1–30 | `dpd_1_30` |
| 31–60 | `dpd_31_60` |
| 61–90 | `dpd_61_90` |
| 91 or more | `dpd_90_plus` |

The portfolio delinquency rate is the count of snapshot loans outside `current`, divided by the loan count. If there are no loans, the rate is null.

### Outstanding balance proxy

`max(principal_amount - paid_to_date, 0)` on the snapshot date.

Assumption: this subtracts payments received from principal. It does not accrue interest, fees, or a servicing-system balance. `annual_rate` is not an input. A source `loan_status` of `paid_off` does not zero the proxy by itself.

### Batch counts

`rows_read` is every landed row in the batch, including rejects and extra copies. `rows_accepted` is the number of business keys whose winning row came from this batch. `rows_rejected` is the quarantined row count. `rows_duplicate` is defined above.

## Reconciliation

`sum(due_amount)`, `sum(paid_amount)`, and the row count of `gold.fact_repayment` must equal `staging.repayment`. The join to loan and account must not drop an accepted repayment. `dbt build` runs this check, and publish refuses to move the watermark if it fails.
