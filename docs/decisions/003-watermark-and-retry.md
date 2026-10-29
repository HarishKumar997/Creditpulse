# ADR 003 — Batch cursor and commit-then-advance

## Status

Accepted

## Decision

A batch id is committed only after staging, dbt, reconciliation, and the success audit row are in one database transaction.

Until that commit:

- Silver upserts by business key.
- Staging uses `ON CONFLICT` and replaces a row only when the incoming `source_updated_at` is greater than or equal to the stored value.
- The watermark does not move.
- The failure is visible in `ops.pipeline_run`.

The watermark for a source is the maximum `source_updated_at` seen in a committed batch, and it never moves backward. Late rows with an older timestamp still land when their batch id has not been committed. They do not overwrite a newer stored value.

An older replay is counted in `rows_duplicate` and is not a second fact row.

## Consequences

- Rerunning a committed batch records `Batch already committed; skipped.` and does not change `fact_repayment`.
- Retrying an uncommitted batch upserts. It does not double the fact count.
- This is at-least-once processing with idempotent writes. It is not an exactly-once guarantee across Spark, Postgres, and Airflow.
