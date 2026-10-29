# Backfill

A committed batch is skipped. To rebuild a date range, load a new batch id. The generator's increment command writes a later repayment file that does not reuse ids from the base batch.

```powershell
docker compose -f infra/docker-compose.yml --profile pipeline run --rm pipeline -m creditpulse.cli increment --seed 42 --batch-id backfill-2025-01 --new-repayments 100 --loan-count 80
```

`loan-count` must match the number of loans in the base batch (`max(20, repayments // 25)` for the standard generator).

What this does:

1. Writes `data/generated/landing/<batch-id>/repayments.json`.
2. Merges those repayments into Silver. A newer `source_updated_at` wins. An older one does not.
3. Upserts staging, rebuilds Gold, and commits the new batch id.

To replay a batch that already committed, delete that id from `ops.committed_batch`, remove `data/generated/control/<batch-id>.fail_once` if it exists, and run the batch again. The upsert still prevents a second fact row for the same `repayment_id`.

Gold is rebuilt from all of staging, so a backfill does not leave a hole in `fact_repayment`.
