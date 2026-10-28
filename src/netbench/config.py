"""Application settings, read from environment variables."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_COUNTRIES = ("HU", "PL", "CZ", "SK", "RO", "BG", "SI", "HR", "EE", "LV", "LT")


class ConfigError(Exception):
    """Raised when a required setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    s3_endpoint_url: str
    s3_access_key: str = field(repr=False)
    s3_secret_key: str = field(repr=False)
    raw_bucket: str = "raw"
    processed_bucket: str = "processed"
    analytics_bucket: str = "analytics"
    reports_bucket: str = "reports"
    countries: tuple[str, ...] = DEFAULT_COUNTRIES


def _require(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _parse_countries(raw: str) -> tuple[str, ...]:
    codes = tuple(code.strip().upper() for code in raw.split(",") if code.strip())
    invalid = [code for code in codes if len(code) != 2 or not code.isalpha()]
    if not codes or invalid:
        raise ConfigError(f"Invalid COUNTRIES value: {raw!r}")
    return codes


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build Settings from environment variables (or from a given mapping, for tests)."""
    env = os.environ if env is None else env
    countries_raw = env.get("COUNTRIES")
    return Settings(
        s3_endpoint_url=_require(env, "S3_ENDPOINT_URL"),
        s3_access_key=_require(env, "S3_ACCESS_KEY"),
        s3_secret_key=_require(env, "S3_SECRET_KEY"),
        raw_bucket=env.get("RAW_BUCKET", "raw"),
        processed_bucket=env.get("PROCESSED_BUCKET", "processed"),
        analytics_bucket=env.get("ANALYTICS_BUCKET", "analytics"),
        reports_bucket=env.get("REPORTS_BUCKET", "reports"),
        countries=_parse_countries(countries_raw) if countries_raw else DEFAULT_COUNTRIES,
    )
