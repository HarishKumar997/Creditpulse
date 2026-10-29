from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

from creditpulse.api import make_server
from creditpulse.config import AS_OF_DEFAULT, batch_id_for, data_dir
from creditpulse.logging_utils import configure_logging
from creditpulse.pipeline import STEPS, SimulatedFailure, execute_step, run_batch, run_increment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="creditpulse")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("run", *STEPS):
        step = sub.add_parser(
            name, help=f"Run the {name} step" if name != "run" else "Generate a batch and commit Bronze through Gold"
        )
        step.add_argument("--seed", type=int, default=42)
        step.add_argument("--repayments", type=int, default=2000)
        step.add_argument("--batch-id", default=None)
        step.add_argument("--run-id", default=None)
        step.add_argument("--as-of", default=AS_OF_DEFAULT)
        step.add_argument("--fail-once", action="store_true")

    inc = sub.add_parser("increment", help="Load a later repayment batch")
    inc.add_argument("--seed", type=int, default=42)
    inc.add_argument("--batch-id", required=True)
    inc.add_argument("--new-repayments", type=int, required=True)
    inc.add_argument("--loan-count", type=int, required=True)
    inc.add_argument("--as-of", default=AS_OF_DEFAULT)
    inc.add_argument("--run-id", default=None)

    api = sub.add_parser("serve-api", help="Serve landing repayments for one batch")
    api.add_argument("--batch-id", required=True)
    api.add_argument("--port", type=int, default=8765)

    bench = sub.add_parser("benchmark", help="Time a seeded batch and write docs/benchmarks/latest.json")
    bench.add_argument("--seed", type=int, default=42)
    bench.add_argument("--repayments", type=int, default=100000)
    return parser


def _validate_as_of(value: str) -> str:
    from datetime import date

    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"as-of must be YYYY-MM-DD, got {value}") from exc
    return value


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = _parser().parse_args(argv)
    if args.command == "serve-api":
        source = data_dir() / "landing" / args.batch_id / "repayments.json"
        if not source.exists():
            print(f"missing {source}", file=sys.stderr)
            return 1
        server = make_server(source, args.port)
        print(f"serving {source} on http://127.0.0.1:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0

    if args.command == "benchmark":
        return _benchmark(args.seed, args.repayments)

    as_of = _validate_as_of(args.as_of)
    try:
        if args.command in {"run", *STEPS}:
            execute_step(
                args.command,
                seed=args.seed,
                repayments=args.repayments,
                batch_id=args.batch_id or batch_id_for(args.seed, args.repayments),
                run_id=args.run_id,
                as_of=as_of,
                fail_once=args.fail_once or _env_fail_once(),
            )
        elif args.command == "increment":
            run_increment(
                seed=args.seed,
                batch_id=args.batch_id,
                new_repayments=args.new_repayments,
                loan_count=args.loan_count,
                as_of=as_of,
                run_id=args.run_id,
            )
    except SimulatedFailure as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


def _env_fail_once() -> bool:
    return os.environ.get("CREDITPULSE_FAIL_ONCE") == "1"


def _benchmark(seed: int, repayments: int) -> int:
    started = time.perf_counter()
    manifest = run_batch(seed=seed, repayments=repayments, as_of="2024-12-31")
    elapsed = round(time.perf_counter() - started, 3)
    payload = {
        "schema_version": "1",
        "note": "Synthetic workload on one developer machine. Not an enterprise-scale claim.",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "spark_master": os.environ.get("CREDITPULSE_SPARK_MASTER", "local[2]"),
        "runtime": os.environ.get("CREDITPULSE_BENCHMARK_RUNTIME", "local"),
        "machine": os.environ.get("CREDITPULSE_BENCHMARK_HOST", platform.node()),
        "repayments_requested": repayments,
        "seed": seed,
        "batch_id": manifest["batch_id"],
        "rows_read": manifest["rows_read"],
        "rows_accepted": manifest["rows_accepted"],
        "rows_rejected": manifest["rows_rejected"],
        "rows_duplicate": manifest["rows_duplicate"],
        "elapsed_seconds": elapsed,
        "timings": manifest.get("timings"),
    }
    destination = Path(__file__).resolve().parents[2] / "docs" / "benchmarks" / "latest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
