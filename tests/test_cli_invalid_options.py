"""Invalid CLI option values must exit nonzero without any network access."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "extra",
    [
        ["--safe-search", "bogus"],
        ["--time-range", "bogus"],
    ],
)
def test_invalid_option_value_exits_nonzero(tmp_path, extra):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from searxngr import main; main()",
            "--searxng-url",
            "http://127.0.0.1:9",
            "--np",
            *extra,
            "query",
        ],
        env={
            **os.environ,
            "XDG_CONFIG_HOME": str(tmp_path),
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "Invalid" in (result.stdout + result.stderr)
