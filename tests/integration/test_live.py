"""Live integration tests against a real SearXNG server.

Gated on the SEARXNG_URL environment variable: without it the whole module
is skipped, so plain `uv run pytest` (and CI) never requires a server.
Run them via the docker compose profile:

    docker compose --profile integration build
    docker compose --profile integration run --rm integration
"""

import json
import os
import pty
import subprocess
import tempfile
import time

import pytest

from searxngr.constants import validate_result_url

SEARXNG_URL = os.environ.get("SEARXNG_URL", "").rstrip("/")
pytestmark = pytest.mark.skipif(not SEARXNG_URL, reason="SEARXNG_URL not set; live SearXNG server required")

READ_TIMEOUT = float(os.environ.get("SEARXNG_TIMEOUT", "90"))


def run_searxngr(*args, stdin=subprocess.DEVNULL, input=None, timeout=READ_TIMEOUT):
    """Run the installed searxngr CLI against the live server.

    Injects --searxng-url from $SEARXNG_URL (searxngr itself reads no URL env
    var) unless the caller passes an explicit --searxng-url.
    """
    if "--searxng-url" not in args and SEARXNG_URL:
        args = ("--searxng-url", SEARXNG_URL, *args)
    return subprocess.run(
        ["searxngr", *args],
        env={**os.environ, "NO_PROXY": "*", "no_proxy": "*"},
        stdin=stdin,
        input=input,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def search_json(query, *extra, attempts=4):
    """Search and return parsed JSON results.

    Retries on empty/failing searches: public upstream engines get suspended
    or CAPTCHA'd under load, which is a property of those engines, not of
    searxngr. Restarting the searxng container clears suspensions.
    """
    last = None
    for attempt in range(attempts):
        result = run_searxngr("--json", "--timeout", "45", *extra, query)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data:
                return data
            last = data
        else:
            last = result
        if attempt < attempts - 1:
            time.sleep(3)
    if isinstance(last, subprocess.CompletedProcess):
        pytest.fail(f"search failed after {attempts} attempts: {last.stderr}")
    return last


def successful_text_search(query, *extra, attempts=4):
    """Run a text-mode search until it succeeds; skip if upstream engines
    stay unavailable (suspension is upstream flakiness, not a CLI defect)."""
    for attempt in range(attempts):
        result = run_searxngr("--timeout", "45", *extra, query)
        if result.returncode == 0 and result.stdout.strip():
            return result
        if attempt < attempts - 1:
            time.sleep(3)
    pytest.skip(f"upstream engines unavailable after {attempts} attempts")


def wait_for_server(client, timeout=120):
    """Poll /search until the SearXNG instance answers."""
    import time

    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            r = client.get("/search", params={"q": "ping", "format": "json"})
            if r.status_code == 200:
                return
            last_error = f"HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001 - readiness probe
            last_error = str(exc)
        time.sleep(2)
    pytest.fail(f"SearXNG at {SEARXNG_URL} not ready after {timeout}s: {last_error}")


@pytest.fixture(scope="session")
def client():
    import httpx

    with httpx.Client(base_url=SEARXNG_URL, timeout=30, trust_env=False) as http:
        wait_for_server(http)
        yield http


# --- 010A: encoding ---------------------------------------------------------


def test_query_encoding_special_characters(client):
    results = search_json("C++ & C#")
    assert isinstance(results, list)
    assert len(results) > 0
    for item in results:
        assert "url" in item and "title" in item


def test_query_encoding_unicode(client):
    results = search_json("café naïve")
    assert isinstance(results, list)
    assert len(results) > 0


# --- 010A: JSON purity ------------------------------------------------------


def test_json_output_is_parseable_and_complete(client):
    raw = run_searxngr("--json", "--debug", "C++ & C#")
    assert raw.returncode == 0, raw.stderr
    results = json.loads(raw.stdout)  # would raise if stdout held diagnostics
    assert isinstance(results, list) and len(results) > 0


def test_diagnostics_go_to_stderr_not_stdout(client):
    result = run_searxngr("--json", "--debug", "C++ & C#")
    assert result.returncode == 0, result.stderr
    # stdout must parse as pure JSON: no Rich tables, no warnings, no prompts.
    assert isinstance(json.loads(result.stdout), list)


# --- 010A: non-interactive execution (incl. the stdout-pipe gap) ------------


def test_piped_output_does_not_hang_or_prompt(client):
    """Regression (red until the tty-guard fix lands): redirecting stdout to a
    FILE while stdin stays a TTY must not drop the user into the interactive
    loop. With the old guard (`not sys.stdin.isatty()` only) the prompt blocks
    forever in this scenario — no SIGPIPE saves it.

    A successful search is needed to reach the gate, so retry the scenario
    until the search succeeds; skip if upstream engines stay suspended.
    """
    for attempt in range(4):
        master, slave = pty.openpty()
        outfile = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as out:
                outfile = out.name
            with open(outfile, "wb") as out:
                proc = subprocess.Popen(
                    ["searxngr", "--searxng-url", SEARXNG_URL, "searxng"],
                    env={**os.environ, "NO_PROXY": "*", "no_proxy": "*"},
                    stdin=slave,
                    stdout=out,
                    stderr=subprocess.DEVNULL,
                )
                os.close(slave)
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    pytest.fail(
                        "searxngr hung in interactive mode with stdout redirected "
                        "to a file; the tty guard must also check stdout"
                    )
            output = open(outfile).read()
            if proc.returncode == 0 and output.strip():
                assert "for help" not in output, f"interactive prompt leaked into redirected output: {output!r}"
                return
        finally:
            os.close(master)
            if outfile:
                os.unlink(outfile)
        time.sleep(3)
    pytest.skip("upstream engines unavailable; could not reach the interactive gate")


def test_stdin_pipe_exits_cleanly(client):
    result = successful_text_search("searxng")
    assert "for help" not in result.stdout


def test_failed_search_exits_nonzero(client):
    result = run_searxngr("--searxng-url", "http://127.0.0.1:9", "anything")
    assert result.returncode != 0
    # No results on stdout (json mode); the error goes to stderr.
    assert not result.stdout.startswith("[")
    assert "Error" in result.stderr


# --- 010B: retries ----------------------------------------------------------


def test_retry_flag_validation(client):
    out_of_range = run_searxngr("--retries", "6", "test")
    assert out_of_range.returncode != 0
    assert "invalid choice" in out_of_range.stderr

    run_searxngr("--retries", "0", "--timeout", "45", "searxng")  # must not crash


# --- 010B/010C: metadata & removal ------------------------------------------


def test_version_reports_release(client):
    result = run_searxngr("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == "0.9.0"


def test_fallback_engines_flag_is_gone(client):
    result = run_searxngr("--fallback-engines", "google", "test")
    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr


def test_engines_selection_reaches_server(client):
    """Explicit engine choice: the request must carry engines=google (or the
    instance must report google as unresponsive, not a client-side crash)."""
    result = run_searxngr("--json", "--engines", "google", "--timeout", "45", "C++ & C#")
    assert result.returncode in (0, 1), result.stderr
    if result.returncode == 0:
        assert isinstance(json.loads(result.stdout), list)


def test_list_engines_lists_available_engines(client):
    result = run_searxngr("--list-engines")
    assert result.returncode == 0, result.stderr
    assert "google" in result.stdout.lower()


# --- 004: startup validation -------------------------------------------------


def test_invalid_url_syntax_fails_fast_before_search(client):
    """A malformed instance URL exits 1 with a specific message and no
    network work: the check is syntactic and must stay ahead of any search
    request (and any startup probe — the timing guard encodes that decision)."""
    start = time.monotonic()
    result = run_searxngr("--searxng-url", "https:/searxng.home.lan", "test")
    elapsed = time.monotonic() - start
    assert result.returncode == 1
    assert "Invalid SearXNG instance URL" in result.stdout + result.stderr
    assert elapsed < 10, "startup validation must not perform network I/O"


def test_invalid_category_fails_before_search(client):
    """An unknown category exits 1 with the supported list, before any
    search request reaches the server."""
    result = run_searxngr("-c", "genral", "test")
    assert result.returncode == 1
    assert "Invalid category 'genral'" in result.stdout + result.stderr


# --- 001: result-URL allowlist policy ---------------------------------------


def test_live_results_pass_url_allowlist(client):
    """Policy check against real engine output: every URL a live search
    returns must pass validate_result_url. If an engine ever emits a
    non-http(s) result (magnet:, ftp:, ...), the CLI would refuse to open
    it — this surfaces that as a policy decision, not a silent regression."""
    results = search_json("searxng")
    assert results, "expected at least one result"
    rejected = [r.get("url") for r in results if not validate_result_url(r.get("url", ""))]
    assert not rejected, (
        f"live search returned URLs the allowlist rejects: {rejected}; "
        "extend ALLOWED_URL_SCHEMES deliberately if these should be openable"
    )
