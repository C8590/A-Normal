from __future__ import annotations


class ConfigError(Exception):
    """Base class for ashare-alpha-lab configuration errors."""


class ConfigFileNotFoundError(ConfigError):
    """Raised when a required configuration file is missing."""


class ConfigYamlError(ConfigError):
    """Raised when a YAML file cannot be parsed as a mapping."""


class ConfigValidationError(ConfigError):
    """Raised when configuration content fails schema validation."""
