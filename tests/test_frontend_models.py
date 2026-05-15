from __future__ import annotations

import json
from datetime import datetime

from ashare_alpha.frontend import FrontendData


def test_frontend_data_serializable() -> None:
    data = FrontendData(
        generated_at=datetime(2026, 5, 15, 9, 0, 0),
        outputs_root="outputs",
        version="0.1.0-test",
        summary={"artifact_count": 0},
    )

    payload = data.model_dump(mode="json")

    assert json.loads(json.dumps(payload, ensure_ascii=False))["version"] == "0.1.0-test"
