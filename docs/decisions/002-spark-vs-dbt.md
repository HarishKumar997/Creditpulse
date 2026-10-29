# ADR 002 — Spark prepares files, dbt owns Gold

## Status

Accepted

## Decision

PySpark deduplicates on the business key. PyArrow writes the Parquet files. dbt builds and tests the dimensional model in PostgreSQL.

The same metric is not implemented in both places. Delinquency buckets exist once as `refdata.delinquency_bucket`, and the Python tests compare that function with `rules.delinquency_bucket` on the boundary days.

## Why not one engine for everything

Spark is the right tool to show file-level medallion handling and a business-key merge. The warehouse tests, grain, and metric definitions are easier to read as SQL. Splitting them makes the interview explanation specific: what was deduplicated, and what was aggregated.

Pandas is not the pipeline engine.

## Consequences

- Gold is rebuilt from staging after each committed batch. That is a full refresh of a small warehouse, not a Spark streaming aggregate.
- A change to a metric belongs in a dbt model and a dictionary entry, plus a test.
