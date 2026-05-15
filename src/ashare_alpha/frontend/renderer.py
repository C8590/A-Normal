from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.frontend.models import FrontendData


_TEMPLATE_DIR = Path(__file__).with_name("templates")


def render_frontend_html(data: FrontendData) -> str:
    return _read_template("index.html").replace("{{VERSION}}", data.version)


def render_frontend_js(data: FrontendData) -> str:
    payload = json.dumps(data.model_dump(mode="json"), ensure_ascii=False, indent=2)
    return _read_template("app.js").replace("__FRONTEND_DATA_JSON__", payload)


def render_frontend_css() -> str:
    return _read_template("style.css")


def _read_template(name: str) -> str:
    return (_TEMPLATE_DIR / name).read_text(encoding="utf-8")
