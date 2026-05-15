from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from scripts import dev_check, smoke_test


def test_dev_check_json_runs(capsys) -> None:
    code = dev_check.main(["--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["python_executable"]
    assert any(result["name"] == "src_package" for result in payload["results"])


def test_smoke_test_json_quick_uses_mocked_subprocess(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(smoke_test, "REPORT_DIR", tmp_path / "dev")

    def fake_run(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout=f"ok: {' '.join(command)}", stderr="")

    monkeypatch.setattr(smoke_test.subprocess, "run", fake_run)

    code = smoke_test.main(["--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["mode"] == "quick"
    assert payload["failed_count"] == 0
    assert (tmp_path / "dev" / "smoke_test_report.json").exists()
    assert (tmp_path / "dev" / "smoke_test_report.md").exists()


def test_readme_contains_editable_install_instruction() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "py -3.12 -m pip install -e ." in text
    assert "py -3.12 scripts/dev_check.py" in text


def test_development_setup_exists() -> None:
    text = Path("docs/DEVELOPMENT_SETUP.md").read_text(encoding="utf-8")

    assert "Editable Install" in text
    assert "PYTHONPATH" in text
