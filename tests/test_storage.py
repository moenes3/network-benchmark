import boto3
import pytest
from moto import mock_aws

from netbench.config import load_settings
from netbench.storage import ensure_bucket, ensure_buckets

BASE_ENV = {
    "S3_ENDPOINT_URL": "http://localhost:9000",
    "S3_ACCESS_KEY": "test-access",
    "S3_SECRET_KEY": "test-secret",
}


@pytest.fixture
def s3_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


def _bucket_names(client) -> set[str]:
    return {bucket["Name"] for bucket in client.list_buckets()["Buckets"]}


def test_ensure_bucket_creates_missing_bucket(s3_client) -> None:
    assert ensure_bucket(s3_client, "raw") is True
    assert "raw" in _bucket_names(s3_client)


def test_ensure_bucket_is_idempotent(s3_client) -> None:
    ensure_bucket(s3_client, "raw")
    assert ensure_bucket(s3_client, "raw") is False
    assert _bucket_names(s3_client) == {"raw"}


def test_ensure_buckets_creates_all_layers(s3_client) -> None:
    ensure_buckets(s3_client, load_settings(BASE_ENV))
    assert _bucket_names(s3_client) == {"raw", "processed", "analytics", "reports"}
