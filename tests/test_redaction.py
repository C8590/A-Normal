from __future__ import annotations

import pytest

from ashare_alpha.security import redact_mapping, redact_secret, safe_env_status


def test_redact_secret_masks_short_strings() -> None:
    assert redact_secret("abc") == "****"


def test_redact_secret_keeps_small_edges_for_long_strings() -> None:
    assert redact_secret("abcdefgh") == "a****h"
    assert redact_secret("abcdefghijkl") == "abc****jkl"


def test_redact_mapping_recursively_redacts_sensitive_keys() -> None:
    data = {
        "token": "abcdefghijkl",
        "nested": {"api_key": "1234567890", "password": "abcd"},
        "safe": "visible",
    }

    redacted = redact_mapping(data)

    assert redacted["token"] == "abc****jkl"
    assert redacted["nested"]["api_key"] == "123****890"
    assert redacted["nested"]["password"] == "****"
    assert redacted["safe"] == "visible"


def test_safe_env_status_only_outputs_redacted_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASHARE_ALPHA_TEST_TOKEN", "secret-token-value")

    status = safe_env_status("ASHARE_ALPHA_TEST_TOKEN")

    assert status["is_set"] is True
    assert status["redacted_value"] == "sec****lue"
    assert status["redacted_value"] != "secret-token-value"
