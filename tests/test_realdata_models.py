from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.realdata import RealDataOfflineDrillSpec, RealDataOfflineDrillStep


def test_realdata_offline_drill_spec_loads() -> None:
    spec = RealDataOfflineDrillSpec.model_validate(
        {
            "drill_name": "tushare_like_offline_drill",
            "source_profile": "configs/ashare_alpha/source_profiles/tushare_like_offline.yaml",
            "source_name": "tushare_like_offline",
            "data_version": "v0_3_drill",
            "target_date": "2026-03-20",
            "output_root_dir": "outputs/realdata",
            "experiment_registry_dir": "outputs/experiments",
        }
    )

    assert spec.source_name == "tushare_like_offline"
    assert spec.target_date.isoformat() == "2026-03-20"
    assert spec.run_pipeline is True


def test_realdata_offline_drill_spec_requires_source_profile() -> None:
    with pytest.raises(ValidationError):
        RealDataOfflineDrillSpec.model_validate(
            {
                "drill_name": "bad_drill",
                "source_name": "tushare_like_offline",
                "data_version": "v0_3_drill",
                "target_date": "2026-03-20",
                "output_root_dir": "outputs/realdata",
                "experiment_registry_dir": "outputs/experiments",
            }
        )


def test_failed_step_requires_error_message() -> None:
    with pytest.raises(ValidationError):
        RealDataOfflineDrillStep(
            name="cache_source_fixture",
            status="FAILED",
            started_at=datetime.now(),
            finished_at=datetime.now(),
            duration_seconds=0.1,
        )
