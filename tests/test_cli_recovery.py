"""End-to-end fault injection through real local HTTP and a CLI subprocess."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import shlex
import subprocess
import sys
import threading
from urllib.parse import parse_qs, urlsplit

import pytest


@pytest.mark.parametrize(
    "responses,expected_exit",
    [
        (
            [(503, {}), (200, {"results": [{"url": "https://example.com/recovered", "title": "Recovered"}]})],
            0,
        ),
        ([(503, {}), (503, {}), (503, {})], 1),
    ],
)
def test_cli_recovers_or_fails_cleanly(tmp_path, responses, expected_exit):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(parse_qs(urlsplit(self.path).query))
            status, payload = responses[min(len(requests) - 1, len(responses) - 1)]
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from searxngr import main; main()",
                    "--searxng-url",
                    f"http://127.0.0.1:{server.server_port}",
                    "--json",
                    "--retries",
                    "2",
                    "--timeout",
                    "1",
                    "--url-handler",
                    shlex.quote(sys.executable),
                    "C++ & C#",
                ],
                env={
                    **os.environ,
                    "XDG_CONFIG_HOME": str(tmp_path),
                    "NO_PROXY": "127.0.0.1",
                },
                capture_output=True,
                text=True,
                timeout=10,
            )
        finally:
            server.shutdown()
            thread.join(timeout=2)
    assert result.returncode == expected_exit, result.stderr
    assert len(requests) == len(responses)
    assert all(request["q"] == ["C++ & C#"] for request in requests)
    if expected_exit == 0:
        assert json.loads(result.stdout)[0]["url"] == "https://example.com/recovered"
        assert "retry" in result.stderr
    else:
        assert result.stdout == ""
        assert "Error:" in result.stderr
