from __future__ import annotations

import json
import shutil
from pathlib import Path

from ashare_alpha.frontend.models import FrontendData
from ashare_alpha.frontend.renderer import render_frontend_css, render_frontend_html, render_frontend_js


def save_frontend_site(data: FrontendData, output_dir: Path, update_latest: bool = False, latest_dir: Path | None = None) -> Path:
    output_path = Path(output_dir)
    assets_dir = output_path / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (output_path / "index.html").write_text(render_frontend_html(data), encoding="utf-8")
    (assets_dir / "app.js").write_text(render_frontend_js(data), encoding="utf-8")
    (assets_dir / "style.css").write_text(render_frontend_css(), encoding="utf-8")
    (output_path / "frontend_data.json").write_text(
        json.dumps(data.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if update_latest:
        latest_path = Path(latest_dir) if latest_dir is not None else output_path.parent / "latest"
        if latest_path.resolve() != output_path.resolve():
            if latest_path.exists():
                shutil.rmtree(latest_path)
            shutil.copytree(output_path, latest_path)
    return output_path
