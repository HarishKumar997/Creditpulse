from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen


def paginate(rows: list[dict], cursor: str | None, limit: int) -> dict:
    if limit < 1 or limit > 5000:
        raise ValueError("limit must be between 1 and 5000")
    if cursor in (None, ""):
        start = 0
    else:
        if not str(cursor).isdigit():
            raise ValueError("cursor must be a non-negative integer")
        start = int(cursor)
    chunk = rows[start : start + limit]
    next_cursor = None if start + limit >= len(rows) else str(start + limit)
    return {"schema_version": "1", "data": chunk, "next_cursor": next_cursor}


def load_repayments(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def make_handler(repayments_file: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def _send(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send(200, {"status": "ok", "schema_version": "1"})
                return
            if parsed.path != "/repayments":
                self._send(404, {"error": "not found"})
                return
            query = parse_qs(parsed.query)
            cursor = query.get("cursor", [None])[0]
            limit_raw = query.get("limit", ["500"])[0]
            try:
                limit = int(limit_raw)
                page = paginate(load_repayments(repayments_file), cursor, limit)
            except ValueError as exc:
                self._send(400, {"error": str(exc)})
                return
            self._send(200, page)

    return Handler


def make_server(repayments_file: Path, port: int = 0) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(repayments_file))


def serve(repayments_file: Path, port: int = 8765) -> ThreadingHTTPServer:
    server = make_server(repayments_file, port)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def fetch_all_repayments(base_url: str, limit: int = 500) -> list[dict]:
    rows: list[dict] = []
    cursor: str | None = None
    while True:
        query = f"?limit={limit}"
        if cursor is not None:
            query += f"&cursor={cursor}"
        with urlopen(f"{base_url}/repayments{query}", timeout=30) as response:
            page = json.load(response)
        if response.status >= 400:
            raise HTTPError(base_url, response.status, "api error", hdrs=None, fp=None)
        rows.extend(page["data"])
        cursor = page.get("next_cursor")
        if not cursor:
            return rows
