from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

existing_pythonpath = os.environ.get("PYTHONPATH")
paths = [str(SRC_DIR)]
if existing_pythonpath:
    paths.append(existing_pythonpath)
os.environ["PYTHONPATH"] = os.pathsep.join(paths)
