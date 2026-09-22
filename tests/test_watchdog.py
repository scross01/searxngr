"""Exercise the opt-in local watchdog without touching a real service."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.skipif(
    shutil.which("sh") is None, reason="watchdog requires a POSIX shell"
)
@pytest.mark.parametrize(
    "statuses,restart_status,expected_exit,expected_restarts",
    [
        ([0], 0, 0, 0),
        ([1, 0], 0, 0, 0),
        ([1, 1, 0], 0, 0, 1),
        ([1] * 7, 0, 1, 1),
        ([1, 1], 1, 1, 1),
    ],
)
def test_watchdog_recovery(
    tmp_path, statuses, restart_status, expected_exit, expected_restarts
):
    script = Path(__file__).resolve().parents[1] / "contrib/systemd/check-health.sh"
    calls = tmp_path / "calls.json"
    calls.write_text(json.dumps({"curl": 0, "systemctl": 0}))
    helper = f"""#!{sys.executable}
import json, pathlib, sys
calls = pathlib.Path({str(calls)!r})
state = json.loads(calls.read_text())
command = pathlib.Path(sys.argv[0]).name
if command == 'sleep':
    sys.exit(0)
state[command] += 1
calls.write_text(json.dumps(state))
if command == 'curl':
    assert sys.argv[-1] == 'http://127.0.0.1:8080/healthz'
    assert '--max-time' in sys.argv and '--noproxy' in sys.argv
    sys.exit({statuses!r}[state['curl'] - 1])
assert sys.argv[1:] == ['--user', 'restart', 'searxng.service']
sys.exit({restart_status})
"""
    for name in ("curl", "systemctl", "sleep"):
        command = tmp_path / name
        command.write_text(helper)
        command.chmod(0o755)
    env = {**os.environ, "PATH": str(tmp_path)}
    result = subprocess.run(
        [shutil.which("sh"), str(script)], env=env, capture_output=True, timeout=10
    )
    assert result.returncode == expected_exit, result.stderr
    state = json.loads(calls.read_text())
    assert state["curl"] == len(statuses)
    assert state["systemctl"] == expected_restarts
