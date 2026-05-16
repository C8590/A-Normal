from __future__ import annotations

from pathlib import Path


def test_ashare_alpha_does_not_import_forbidden_network_or_legacy_packages() -> None:
    forbidden = ("import a_normal", "from a_normal", "import requests", "import httpx", "import tushare", "import akshare")
    for path in Path("src/ashare_alpha").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert pattern not in text, f"{pattern} found in {path}"
