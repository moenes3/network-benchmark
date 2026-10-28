import pytest

from netbench.config import DEFAULT_COUNTRIES, ConfigError, load_settings

BASE_ENV = {
    "S3_ENDPOINT_URL": "http://localhost:9000",
    "S3_ACCESS_KEY": "test-access",
    "S3_SECRET_KEY": "test-secret",
}


def test_loads_required_values_and_defaults() -> None:
    settings = load_settings(BASE_ENV)
    assert settings.s3_endpoint_url == "http://localhost:9000"
    assert settings.raw_bucket == "raw"
    assert settings.countries == DEFAULT_COUNTRIES


def test_missing_required_variable_raises() -> None:
    env = {key: value for key, value in BASE_ENV.items() if key != "S3_SECRET_KEY"}
    with pytest.raises(ConfigError, match="S3_SECRET_KEY"):
        load_settings(env)


def test_countries_are_parsed_and_normalised() -> None:
    settings = load_settings({**BASE_ENV, "COUNTRIES": " hu, pl ,CZ "})
    assert settings.countries == ("HU", "PL", "CZ")


def test_invalid_country_code_raises() -> None:
    with pytest.raises(ConfigError):
        load_settings({**BASE_ENV, "COUNTRIES": "HU,POL"})


def test_secrets_are_hidden_from_repr() -> None:
    text = repr(load_settings(BASE_ENV))
    assert "test-secret" not in text
    assert "test-access" not in text
