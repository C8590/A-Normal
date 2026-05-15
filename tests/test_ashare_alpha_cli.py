from __future__ import annotations

import subprocess
import sys

from ashare_alpha.cli import main


def test_cli_help_runs_in_process(capsys) -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "does not place real orders" in captured.out


def test_module_help_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout
