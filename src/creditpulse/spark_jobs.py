from __future__ import annotations

import csv
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType
from pyspark.sql.window import Window

from creditpulse.config import (
    ACCOUNT_FIELDS,
    CUSTOMER_FIELDS,
    EVENT_FIELDS,
    LOAN_FIELDS,
    META_FIELDS,
    REPAYMENT_FIELDS,
    SCHEMA_VERSION,
)
from creditpulse.rules import (
    account_reject_reason,
    customer_reject_reason,
    event_reject_reason,
    loan_reject_reason,
    repayment_reject_reason,
)

SOURCE_FIELDS = {
    "customers": CUSTOMER_FIELDS,
    "accounts": ACCOUNT_FIELDS,
    "loans": LOAN_FIELDS,
    "repayments": REPAYMENT_FIELDS,
    "customer_events": EVENT_FIELDS,
}


def session() -> SparkSession:
    # The worker must be the same interpreter as the driver. A bare "python"
    # on Windows is often a stub that exits before the first Spark task.
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    memory = os.environ.get("CREDITPULSE_SPARK_MEMORY", "1g")
    spark = (
        SparkSession.builder.master(os.environ.get("CREDITPULSE_SPARK_MASTER", "local[2]"))
        .appName("creditpulse")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.driver.memory", memory)
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.RawLocalFileSystem")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def stop(spark: SparkSession) -> None:
    spark.stop()


def _schema(fields: list[str]) -> StructType:
    return StructType([StructField(name, StringType(), True) for name in fields])


def _blank(value: object) -> str:
    return "" if value is None else str(value)


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [{key: _blank(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def with_meta(rows: list[dict], source_name: str, batch_id: str, fields: list[str]) -> list[dict]:
    ingested_at = now_iso()
    prepared = []
    for row in rows:
        item = {field: _blank(row.get(field)) for field in fields}
        item.update(
            {
                "batch_id": batch_id,
                "source_name": source_name,
                "ingested_at": ingested_at,
                "schema_version": SCHEMA_VERSION,
            }
        )
        prepared.append(item)
    return prepared


def write_parquet(rows: list[dict], fields: list[str], path: Path) -> None:
    """PyArrow writes the files. Spark's Hadoop writer needs winutils on Windows."""
    if path.exists():
        shutil.rmtree(path)
    if not rows:
        return
    path.mkdir(parents=True, exist_ok=True)
    columns = {field: [_blank(row.get(field)) for row in rows] for field in fields}
    pq.write_table(pa.table(columns), path / "part-000.parquet")


def read_parquet(path: Path, fields: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = pq.read_table(path).to_pylist()
    return [{field: _blank(row.get(field)) for field in fields} for row in rows]


def bronze_path(data_dir: Path, source: str, batch_id: str) -> Path:
    return data_dir / "bronze" / source / f"batch_id={batch_id}"


def silver_path(data_dir: Path, source: str) -> Path:
    return data_dir / "silver" / source


def quarantine_path(data_dir: Path, source: str, batch_id: str) -> Path:
    return data_dir / "quarantine" / source / f"batch_id={batch_id}"


def _dedupe(
    spark: SparkSession,
    incoming: list[dict],
    existing: list[dict],
    fields: list[str],
    keys: list[str],
) -> tuple[list[dict], int]:
    """Keep the newest source_updated_at. On a tie, the row already in silver wins."""
    if not incoming and not existing:
        return [], 0
    tagged_fields = fields + ["_preference"]
    incoming_rows = [{**row, "_preference": "0"} for row in incoming]
    existing_rows = [{**{field: row.get(field, "") for field in fields}, "_preference": "1"} for row in existing]
    frame = spark.createDataFrame(
        [tuple(row.get(field, "") for field in tagged_fields) for row in incoming_rows + existing_rows],
        _schema(tagged_fields),
    )
    window = Window.partitionBy(*keys).orderBy(F.col("source_updated_at").desc(), F.col("_preference").desc())
    ranked = frame.withColumn("_rn", F.row_number().over(window))
    kept_frame = ranked.filter(F.col("_rn") == 1).drop("_rn", "_preference")
    duplicate_count = ranked.filter((F.col("_rn") > 1) & (F.col("_preference") == "0")).count()
    kept = [{field: _blank(record[field]) for field in fields} for record in kept_frame.collect()]
    return kept, int(duplicate_count)


def _split_rejects(
    rows: list[dict],
    reason_for,
    business_key,
) -> tuple[list[dict], list[dict]]:
    accepted: list[dict] = []
    rejected: list[dict] = []
    for index, row in enumerate(rows):
        reason = reason_for(row)
        if reason:
            item = dict(row)
            item["reject_reason"] = reason
            item["business_key"] = business_key(row, index)
            rejected.append(item)
        else:
            accepted.append(row)
    return accepted, rejected


def _max_updated(rows: list[dict]) -> str | None:
    values = [row.get("source_updated_at", "") for row in rows if row.get("source_updated_at")]
    return max(values) if values else None


def ingest_batch(spark: SparkSession, data_dir: Path, batch_id: str, repayment_rows: list[dict]) -> dict:
    landing = data_dir / "landing" / batch_id
    sources = {
        "customers": read_csv_rows(landing / "customers.csv"),
        "accounts": read_csv_rows(landing / "accounts.csv"),
        "loans": read_csv_rows(landing / "loans.csv"),
        "customer_events": read_csv_rows(landing / "events.csv"),
        "repayments": repayment_rows,
    }
    counts = {}
    for source, rows in sources.items():
        fields = SOURCE_FIELDS[source] + META_FIELDS
        prepared = with_meta(rows, source, batch_id, SOURCE_FIELDS[source])
        if prepared:
            write_parquet(prepared, fields, bronze_path(data_dir, source, batch_id))
        elif bronze_path(data_dir, source, batch_id).exists():
            shutil.rmtree(bronze_path(data_dir, source, batch_id))
        counts[source] = len(prepared)
    return {
        "rows_read": sum(counts.values()),
        "by_source": counts,
        "max_updated": {source: _max_updated(sources[source]) for source in sources},
    }


def _key(row: dict, keys: list[str]) -> tuple:
    return tuple(row.get(key, "") for key in keys)


def _accepted_count(accepted: list[dict], merged: list[dict], keys: list[str], batch_id: str) -> int:
    best_ts: dict[tuple, str] = {}
    for row in accepted:
        marker = _key(row, keys)
        stamp = row.get("source_updated_at", "")
        if marker not in best_ts or stamp > best_ts[marker]:
            best_ts[marker] = stamp
    kept = 0
    for row in merged:
        marker = _key(row, keys)
        if marker in best_ts and row.get("source_updated_at") == best_ts[marker] and row.get("batch_id") == batch_id:
            kept += 1
    return kept


def _merge_source(
    spark: SparkSession,
    data_dir: Path,
    batch_id: str,
    bronze_source: str,
    silver_source: str,
    fields: list[str],
    keys: list[str],
    reason_for,
    business_key,
) -> dict[str, int | str | None]:
    stored_fields = fields + META_FIELDS
    bronze = read_parquet(bronze_path(data_dir, bronze_source, batch_id), stored_fields)
    if not bronze and not silver_path(data_dir, silver_source).exists():
        return {"accepted": 0, "rejected": 0, "duplicates": 0, "max_updated": None}
    accepted, rejected = _split_rejects(bronze, reason_for, business_key)
    existing = read_parquet(silver_path(data_dir, silver_source), stored_fields)
    merged, duplicate_count = _dedupe(spark, accepted, existing, stored_fields, keys)
    if merged:
        write_parquet(merged, stored_fields, silver_path(data_dir, silver_source))
    q_fields = stored_fields + ["reject_reason", "business_key"]
    q_merged, q_dupes = _dedupe(spark, rejected, [], q_fields, ["business_key"])
    q_path = quarantine_path(data_dir, bronze_source, batch_id)
    if q_merged:
        write_parquet(q_merged, q_fields, q_path)
    elif q_path.exists():
        shutil.rmtree(q_path)
    return {
        "accepted": _accepted_count(accepted, merged, keys, batch_id),
        "rejected": len(q_merged),
        "duplicates": int(duplicate_count) + int(q_dupes),
        "max_updated": _max_updated(bronze),
    }


def _ids(rows: list[dict], field: str) -> set[str]:
    return {row[field] for row in rows if row.get(field)}


def _event_to_customer(row: dict) -> dict:
    payload = json.loads(row["payload"])
    return {
        "customer_id": str(payload["customer_id"]),
        "created_at": "",
        "region_code": str(payload.get("region_code", "")),
        "customer_segment": str(payload.get("customer_segment", "")),
        "status": str(payload.get("status", "")),
        "source_updated_at": row["source_updated_at"],
        "batch_id": row["batch_id"],
        "source_name": "customer_events",
        "ingested_at": row.get("ingested_at", ""),
        "schema_version": row.get("schema_version", "1"),
    }


def _business_key(field: str):
    def _key(row: dict, index: int) -> str:
        value = row.get(field, "")
        return value or f"missing-{row.get('batch_id', 'batch')}-{index}"

    return _key


def transform_batch(spark: SparkSession, data_dir: Path, batch_id: str) -> dict:
    customer_fields = CUSTOMER_FIELDS
    customers = _merge_source(
        spark,
        data_dir,
        batch_id,
        "customers",
        "customer_version",
        customer_fields,
        ["customer_id", "source_updated_at"],
        lambda row: customer_reject_reason(row),
        _business_key("customer_id"),
    )
    customer_rows = read_parquet(silver_path(data_dir, "customer_version"), customer_fields + META_FIELDS)
    customer_ids = _ids(customer_rows, "customer_id")

    event_fields = EVENT_FIELDS
    event_bronze = read_parquet(bronze_path(data_dir, "customer_events", batch_id), event_fields + META_FIELDS)
    event_accepted, event_rejected = _split_rejects(
        event_bronze,
        lambda row: event_reject_reason(row, customer_ids),
        _business_key("event_id"),
    )
    version_rows = [_event_to_customer(row) for row in event_accepted]
    existing_versions = read_parquet(silver_path(data_dir, "customer_version"), customer_fields + META_FIELDS)
    merged_versions, event_dupes = _dedupe(
        spark,
        version_rows,
        existing_versions,
        customer_fields + META_FIELDS,
        ["customer_id", "source_updated_at"],
    )
    if merged_versions:
        write_parquet(merged_versions, customer_fields + META_FIELDS, silver_path(data_dir, "customer_version"))
    q_fields = event_fields + META_FIELDS + ["reject_reason", "business_key"]
    q_merged, q_dupes = _dedupe(spark, event_rejected, [], q_fields, ["business_key"])
    q_path = quarantine_path(data_dir, "customer_events", batch_id)
    if q_merged:
        write_parquet(q_merged, q_fields, q_path)
    elif q_path.exists():
        shutil.rmtree(q_path)
    event_stats = {
        "accepted": _accepted_count(version_rows, merged_versions, ["customer_id", "source_updated_at"], batch_id),
        "rejected": len(q_merged),
        "duplicates": int(event_dupes) + int(q_dupes),
        "max_updated": _max_updated(event_bronze),
    }
    customer_ids = _ids(merged_versions or customer_rows, "customer_id")

    accounts = _merge_source(
        spark,
        data_dir,
        batch_id,
        "accounts",
        "account",
        ACCOUNT_FIELDS,
        ["account_id"],
        lambda row: account_reject_reason(row, customer_ids),
        _business_key("account_id"),
    )
    account_ids = _ids(
        read_parquet(silver_path(data_dir, "account"), ACCOUNT_FIELDS + META_FIELDS),
        "account_id",
    )
    loans = _merge_source(
        spark,
        data_dir,
        batch_id,
        "loans",
        "loan",
        LOAN_FIELDS,
        ["loan_id"],
        lambda row: loan_reject_reason(row, account_ids),
        _business_key("loan_id"),
    )
    loan_ids = _ids(
        read_parquet(silver_path(data_dir, "loan"), LOAN_FIELDS + META_FIELDS),
        "loan_id",
    )
    repayments = _merge_source(
        spark,
        data_dir,
        batch_id,
        "repayments",
        "repayment",
        REPAYMENT_FIELDS,
        ["repayment_id"],
        lambda row: repayment_reject_reason(row, loan_ids),
        _business_key("repayment_id"),
    )
    stats = {
        "customers": customers,
        "customer_events": event_stats,
        "accounts": accounts,
        "loans": loans,
        "repayments": repayments,
    }
    return {
        "by_source": stats,
        "rows_accepted": sum(int(item["accepted"]) for item in stats.values()),
        "rows_rejected": sum(int(item["rejected"]) for item in stats.values()),
        "rows_duplicate": sum(int(item["duplicates"]) for item in stats.values()),
        "max_updated": {name: item["max_updated"] for name, item in stats.items()},
    }
