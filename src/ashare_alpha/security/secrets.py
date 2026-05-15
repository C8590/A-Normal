from __future__ import annotations

import os


class MissingSecretError(RuntimeError):
    """Raised when a required environment variable secret is missing."""


class SecretPolicyError(RuntimeError):
    """Raised when a secret access violates the configured policy."""


class EnvSecretProvider:
    def get_secret(self, env_var_name: str) -> str | None:
        return os.environ.get(env_var_name)

    def require_secret(self, env_var_name: str) -> str:
        value = self.get_secret(env_var_name)
        if value is None or value == "":
            raise MissingSecretError(f"缺少必需的环境变量密钥：{env_var_name}")
        return value
