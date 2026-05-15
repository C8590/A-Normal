from __future__ import annotations

from pathlib import Path

from ashare_alpha.frontend import collect_frontend_data, render_frontend_css, render_frontend_html, render_frontend_js
from dashboard_helpers import write_dashboard_fixture


def test_render_frontend_html_nonempty(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)
    data = collect_frontend_data(paths["outputs"])

    html = render_frontend_html(data)

    assert "ashare-alpha-lab Research Frontend" in html
    assert "assets/app.js" in html


def test_render_frontend_js_contains_embedded_data(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)
    data = collect_frontend_data(paths["outputs"])

    js = render_frontend_js(data)

    assert "const FRONTEND_DATA" in js
    assert '"artifacts"' in js
    assert "fetch(" not in js


def test_render_frontend_css_nonempty() -> None:
    css = render_frontend_css()

    assert "body" in css
    assert "http://" not in css
    assert "https://" not in css
