from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from creditpulse.api import fetch_all_repayments, serve
from creditpulse.config import batch_id_for, dbt_dir, web_data_dir
from creditpulse.config import data_dir as default_data_dir
from creditpulse.export_demo import export_demo
from creditpulse.generate import generate, generate_increment, landing_dir
from creditpulse.spark_jobs import ingest_batch, session, stop, transform_batch
from creditpulse.warehouse import (
    commit_success,
    connect,
    ensure_schema,
    is_committed,
    load_silver,
    reconciliation,
    record_run,
)


class SimulatedFailure(RuntimeError):
    """Raised once, on purpose, before the watermark transaction commits."""


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _manifest_path(directory: Path, batch_id: str) -> Path:
    return directory / "manifests" / f"{batch_id}.json"


def _new_manifest(batch_id: str, run_id: str, as_of: str) -> dict:
    return {
        "batch_id": batch_id,
        "run_id": run_id,
        "started_at": _now(),
        "as_of": as_of,
        "rows_read": 0,
        "rows_accepted": 0,
        "rows_rejected": 0,
        "rows_duplicate": 0,
        "max_updated": {},
        "timings": {},
    }


def load_manifest(directory: Path, batch_id: str, run_id: str, as_of: str) -> dict:
    path = _manifest_path(directory, batch_id)
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("run_id") != run_id:
            manifest["started_at"] = _now()
        manifest["run_id"] = run_id
        manifest["as_of"] = as_of
        return manifest
    return _new_manifest(batch_id, run_id, as_of)


def save_manifest(directory: Path, manifest: dict) -> None:
    path = _manifest_path(directory, manifest["batch_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _fail(directory: Path, manifest: dict, run_id: str, step: str, message: str) -> None:
    save_manifest(directory, manifest)
    with connect(autocommit=True) as conn:
        record_run(conn, manifest, run_id, "failed", message[:500], step)


def _repayments_from_api(directory: Path, batch_id: str) -> list[dict]:
    source = landing_dir(directory, batch_id) / "repayments.json"
    if not source.exists():
        return []
    server = serve(source, 0)
    try:
        port = server.server_address[1]
        return fetch_all_repayments(f"http://127.0.0.1:{port}")
    finally:
        server.shutdown()
        server.server_close()


def ingest(directory: Path, batch_id: str, spark=None) -> dict:
    own = spark is None
    spark = spark or session()
    started = time.perf_counter()
    try:
        rows = _repayments_from_api(directory, batch_id)
        result = ingest_batch(spark, directory, batch_id, rows)
    finally:
        if own:
            stop(spark)
    return result | {"seconds": round(time.perf_counter() - started, 3)}


def transform(directory: Path, batch_id: str, spark=None) -> dict:
    own = spark is None
    spark = spark or session()
    started = time.perf_counter()
    try:
        result = transform_batch(spark, directory, batch_id)
    finally:
        if own:
            stop(spark)
    return result | {"seconds": round(time.perf_counter() - started, 3)}


def load(directory: Path, batch_id: str) -> float:
    started = time.perf_counter()
    with connect() as conn:
        load_silver(conn, directory, batch_id)
        conn.commit()
    return round(time.perf_counter() - started, 3)


def build_dbt(as_of: str) -> float:
    started = time.perf_counter()
    dbt = shutil.which("dbt")
    if dbt is None:
        raise RuntimeError("dbt is not on PATH. Install the project with pip install -e .[dev]")
    env = os.environ.copy()
    env["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
    subprocess.run(
        [
            dbt,
            "build",
            "--project-dir",
            str(dbt_dir()),
            "--profiles-dir",
            str(dbt_dir()),
            "--vars",
            json.dumps({"as_of_date": as_of}),
        ],
        check=True,
        env=env,
    )
    return round(time.perf_counter() - started, 3)


def publish(
    directory: Path,
    manifest: dict,
    run_id: str,
    web_dir: Path,
    *,
    fail_once: bool = False,
) -> None:
    marker = directory / "control" / f"{manifest['batch_id']}.fail_once"
    if fail_once and not marker.exists():
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(run_id, encoding="utf-8")
        _fail(
            directory,
            manifest,
            run_id,
            "publish",
            "simulated failure before watermark commit",
        )
        raise SimulatedFailure("simulated failure before watermark commit")

    with connect() as conn:
        with conn.transaction():
            check = reconciliation(conn)
            if check["status"] != "pass":
                raise RuntimeError(f"gold totals do not match staging: {check}")
            commit_success(conn, manifest, run_id)
            export_demo(conn, web_dir, manifest)


STEPS = ("generate", "ingest", "transform", "load", "dbt", "publish")


def execute_step(
    step: str,
    *,
    seed: int = 42,
    repayments: int = 2000,
    batch_id: str | None = None,
    run_id: str | None = None,
    directory: Path | None = None,
    web_dir: Path | None = None,
    as_of: str = "2024-12-31",
    generate_data: bool = True,
    fail_once: bool = False,
) -> dict:
    if step != "run" and step not in STEPS:
        raise ValueError(f"unknown step {step}")
    if step == "run":
        run_id = run_id or str(uuid.uuid4())
        manifest = None
        for name in STEPS:
            if name == "generate" and not generate_data:
                continue
            manifest = execute_step(
                name,
                seed=seed,
                repayments=repayments,
                batch_id=batch_id,
                run_id=run_id,
                directory=directory,
                web_dir=web_dir,
                as_of=as_of,
                generate_data=generate_data,
                fail_once=fail_once,
            )
        return manifest or {}

    directory = directory or default_data_dir()
    web_dir = web_dir or web_data_dir()
    batch_id = batch_id or batch_id_for(seed, repayments)
    run_id = run_id or str(uuid.uuid4())
    ensure_schema()
    manifest = load_manifest(directory, batch_id, run_id, as_of)
    manifest.setdefault("started_at", _now())
    save_manifest(directory, manifest)

    with connect() as conn:
        committed = is_committed(conn, batch_id)
    if committed and step != "generate":
        if step == "publish":
            with connect() as conn:
                with conn.transaction():
                    record_run(
                        conn,
                        manifest,
                        run_id,
                        "success",
                        "Batch already committed; skipped.",
                        "publish",
                    )
                    export_demo(conn, web_dir, manifest)
        return manifest

    try:
        if step == "generate":
            started = time.perf_counter()
            generate(seed, repayments, batch_id, directory)
            manifest["timings"]["generate_seconds"] = round(time.perf_counter() - started, 3)
        elif step == "ingest":
            ingested = ingest(directory, batch_id)
            manifest["rows_read"] = ingested["rows_read"]
            manifest["max_updated"] = ingested["max_updated"]
            manifest["timings"]["ingest_seconds"] = ingested["seconds"]
        elif step == "transform":
            transformed = transform(directory, batch_id)
            manifest["rows_accepted"] = transformed["rows_accepted"]
            manifest["rows_rejected"] = transformed["rows_rejected"]
            manifest["rows_duplicate"] = transformed["rows_duplicate"]
            manifest["max_updated"] = transformed["max_updated"]
            manifest["timings"]["transform_seconds"] = transformed["seconds"]
        elif step == "load":
            manifest["timings"]["load_seconds"] = load(directory, batch_id)
        elif step == "dbt":
            manifest["timings"]["dbt_seconds"] = build_dbt(as_of)
        elif step == "publish":
            publish(directory, manifest, run_id, web_dir, fail_once=fail_once)
        save_manifest(directory, manifest)
    except SimulatedFailure:
        raise
    except Exception as exc:
        _fail(directory, manifest, run_id, step, str(exc))
        raise
    return manifest


def run_batch(
    *,
    seed: int = 42,
    repayments: int = 2000,
    batch_id: str | None = None,
    run_id: str | None = None,
    directory: Path | None = None,
    web_dir: Path | None = None,
    as_of: str = "2024-12-31",
    generate_data: bool = True,
    fail_once: bool = False,
) -> dict:
    return execute_step(
        "run",
        seed=seed,
        repayments=repayments,
        batch_id=batch_id,
        run_id=run_id,
        directory=directory,
        web_dir=web_dir,
        as_of=as_of,
        generate_data=generate_data,
        fail_once=fail_once,
    )


def run_increment(
    *,
    seed: int,
    batch_id: str,
    new_repayments: int,
    loan_count: int,
    directory: Path | None = None,
    web_dir: Path | None = None,
    as_of: str = "2024-12-31",
    run_id: str | None = None,
) -> dict:
    directory = directory or default_data_dir()
    web_dir = web_dir or web_data_dir()
    run_id = run_id or str(uuid.uuid4())
    ensure_schema()
    generate_increment(seed, batch_id, directory, new_repayments, loan_count)
    manifest = _new_manifest(batch_id, run_id, as_of)
    save_manifest(directory, manifest)
    spark = session()
    try:
        ingested = ingest(directory, batch_id, spark)
        manifest["rows_read"] = ingested["rows_read"]
        transformed = transform(directory, batch_id, spark)
    finally:
        stop(spark)
    manifest["rows_accepted"] = transformed["rows_accepted"]
    manifest["rows_rejected"] = transformed["rows_rejected"]
    manifest["rows_duplicate"] = transformed["rows_duplicate"]
    manifest["max_updated"] = transformed["max_updated"]
    save_manifest(directory, manifest)
    manifest["timings"]["load_seconds"] = load(directory, batch_id)
    manifest["timings"]["dbt_seconds"] = build_dbt(as_of)
    publish(directory, manifest, run_id, web_dir, fail_once=False)
    return manifest
