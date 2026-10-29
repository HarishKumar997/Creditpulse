# Failed task retry

Publish moves the watermark only after reconciliation passes. To see the failure on purpose, from the repository root:

```powershell
docker compose -f infra/docker-compose.yml --profile pipeline run --rm pipeline -m creditpulse.cli run --seed 7 --repayments 200 --batch-id retry-demo --run-id attempt-1 --fail-once
```

The command exits non-zero. `ops.pipeline_run` has a failed row. `ops.committed_batch` does not contain `retry-demo`. Staging may already hold the upserted rows.

Run the same batch again:

```powershell
docker compose -f infra/docker-compose.yml --profile pipeline run --rm pipeline -m creditpulse.cli run --seed 7 --repayments 200 --batch-id retry-demo --run-id attempt-2 --fail-once
```

The marker file `data/generated/control/retry-demo.fail_once` tells the second attempt to commit. `fact_repayment` stays at one row per repayment id. The audit table shows both the failed attempt and the success.

The Airflow DAG `creditpulse_retry_demo` runs the same flag on the `publish` task with `retries=1`. Each try gets its own run id (`try number` is in the id), so both attempts remain queryable.

Run that demo before a large benchmark, or on a fresh database. Both seeds use the same `repay-0000001` style of id, so a later seed can upsert rows that belong to an earlier seed.

```sql
select run_id, status, error_summary
from ops.pipeline_run
where batch_id = 'retry-demo'
order by started_at;
```

If a Spark write is interrupted and the Silver directory is incomplete, delete `data/generated/silver` and run the batch again before it is committed. Do not delete a batch that is already in `ops.committed_batch` unless you intend the backfill procedure.
