from __future__ import annotations

import pytest

from ashare_alpha.security import EnvSecretProvider, MissingSecretError


def test_get_secret_reads_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASHARE_ALPHA_TEST_TOKEN", "test-secret")

    assert EnvSecretProvider().get_secret("ASHARE_ALPHA_TEST_TOKEN") == "test-secret"


def test_require_secret_missing_raises_missing_secret_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASHARE_ALPHA_MISSING_TOKEN", raising=False)

    with pytest.raises(MissingSecretError, match="ASHARE_ALPHA_MISSING_TOKEN"):
        EnvSecretProvider().require_secret("ASHARE_ALPHA_MISSING_TOKEN")


def test_missing_secret_error_does_not_contain_secret_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASHARE_ALPHA_OTHER_TOKEN", "real-secret-value")

    with pytest.raises(MissingSecretError) as exc_info:
        EnvSecretProvider().require_secret("ASHARE_ALPHA_MISSING_TOKEN")

    assert "real-secret-value" not in str(exc_info.value)
