"""evidence.jsonl must hold the same requests the engine detected on.

Runs a real browser against a local server, on both S3 paths.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from consent_engine.models.scan_result import ScanResult
from consent_engine.tools.tool_03_browser_scanner import _scan_s3

PLAIN_BODY = "<h1>Plain</h1>"
BANNER_BODY = """
<script>window.OneTrust = {};</script>
<div id="onetrust-banner-sdk" style="display:block;width:300px;height:100px">Cookies</div>
<h1>Banner</h1>
"""


def _serve(body: str) -> Iterator[str]:
    loads = {"count": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                loads["count"] += 1
                page = f'{body}<img src="/px.gif?load={loads["count"]}">'
                payload, content_type = page.encode(), "text/html"
            else:
                payload, content_type = b"", "image/gif"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()


@pytest.fixture
def plain_site() -> Iterator[str]:
    yield from _serve(PLAIN_BODY)


@pytest.fixture
def banner_site() -> Iterator[str]:
    yield from _serve(BANNER_BODY)


def _detected(scan: ScanResult) -> list[str]:
    return sorted(u for u in scan.network_requests if not u.startswith("__js_consent_mode__"))


def _logged(scan: ScanResult) -> list[str]:
    return sorted(entry.url for entry in scan.request_log)


async def test_injection_path_log_drops_the_first_load(plain_site: str):
    scan = await _scan_s3(plain_site)
    assert scan.cmp_interaction_method == "cookie_injection"
    assert not any("load=1" in url for url in _logged(scan))
    assert _logged(scan) == _detected(scan)


async def test_second_session_requests_reach_the_log(banner_site: str):
    scan = await _scan_s3(banner_site)
    assert scan.cmp_interaction_method != "cookie_injection"
    assert _detected(scan)
    assert _logged(scan) == _detected(scan)
