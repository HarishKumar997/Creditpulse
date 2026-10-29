# Databricks Free Edition

This path was not executed in the environment that built the repository. There is no screenshot and no cluster id to show. The local Parquet and PostgreSQL pipeline is the source of truth.

Free Edition is optional, $0, and limited. Treat the limits on the Databricks pricing page as current only after you check them. Do not describe a Free Edition run as production or as enterprise scale.

If you have a workspace:

1. Upload the batch landing files, or regenerate them with the same seed.
2. Create a notebook or job that runs the same Bronze, Silver, and quarantine rules. Prefer Delta tables for those three layers.
3. Keep dbt, or a SQL warehouse task, pointed at the same metric definitions in this repository. Do not invent a second completion-rate formula.
4. Use a job cluster that stops when the job ends.
5. Paste the real driver log, the Delta history for one table, and the reconciliation query result into this runbook. Replace this paragraph only with that evidence.

Differences to expect versus local:

- Local files are Parquet directories. Delta adds a transaction log and a real `MERGE`.
- Local orchestration is Airflow on one machine. A Databricks job is the scheduler for that workspace only.
- The Next.js demo still reads the exported JSON. Do not point a Vercel function at the Databricks job.

If Free Edition is not available, stop here. The clone instructions in `docs/runbooks/local-setup.md` remain the demo.
