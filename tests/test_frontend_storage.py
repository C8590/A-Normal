from __future__ import annotations

from pathlib import Path

from ashare_alpha.frontend import collect_frontend_data, save_frontend_site
from dashboard_helpers import write_dashboard_fixture


def test_save_frontend_site_outputs_files(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)
    data = collect_frontend_data(paths["outputs"])
    output_dir = tmp_path / "site"

    save_frontend_site(data, output_dir)

    assert (output_dir / "index.html").exists()
    assert (output_dir / "assets" / "app.js").exists()
    assert (output_dir / "assets" / "style.css").exists()
    assert (output_dir / "frontend_data.json").exists()


def test_save_frontend_site_update_latest(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)
    data = collect_frontend_data(paths["outputs"])
    output_dir = tmp_path / "frontend" / "frontend_20260515_090000"

    save_frontend_site(data, output_dir, update_latest=True)

    assert (tmp_path / "frontend" / "latest" / "index.html").exists()
