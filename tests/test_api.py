import json
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from creditpulse.api import fetch_all_repayments, make_server, paginate


def test_paginate_cursor_and_limit():
    rows = [{"repayment_id": str(i)} for i in range(5)]
    first = paginate(rows, None, 2)
    assert [row["repayment_id"] for row in first["data"]] == ["0", "1"]
    assert first["next_cursor"] == "2"
    second = paginate(rows, first["next_cursor"], 2)
    assert second["next_cursor"] == "4"
    last = paginate(rows, "4", 2)
    assert last["next_cursor"] is None
    assert last["data"] == [{"repayment_id": "4"}]


def test_bad_cursor_is_rejected():
    with pytest.raises(ValueError, match="cursor"):
        paginate([{"repayment_id": "1"}], "abc", 10)


def test_http_pages_match_the_file(tmp_path):
    rows = [{"repayment_id": f"r-{i}", "loan_id": "loan-000000"} for i in range(7)]
    path = tmp_path / "repayments.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    server = make_server(path, 0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        fetched = fetch_all_repayments(f"http://127.0.0.1:{port}", limit=3)
        assert fetched == rows
        with pytest.raises(HTTPError) as caught:
            urlopen(f"http://127.0.0.1:{port}/repayments?cursor=nope")
        assert caught.value.code == 400
        assert "cursor" in json.load(caught.value)["error"]
    finally:
        server.shutdown()
        server.server_close()
