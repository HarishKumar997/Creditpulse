# ADR 001 — Local first

## Status

Accepted

## Decision

The project must run from a clone with Docker and Python. Cloud accounts are optional and are not on the path that tests exercise.

PostgreSQL 16, PySpark in local mode, dbt Core, and Airflow's LocalExecutor are free local tools. The demo site reads static JSON and can be opened with `npm run dev` before any host is involved.

## Consequences

- A recruiter can rerun the batch without Databricks or Vercel credentials.
- Databricks Free Edition, if used later, is a second execution path. It is not evidence unless a real run log is attached.
- The local workload is a developer-machine benchmark, not a claim of enterprise scale.
