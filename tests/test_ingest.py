import boto3
import pytest
from moto import mock_aws

from netbench.ingest import SOURCE_BUCKET, file_name, ingest_quarter, raw_key, source_key

FAKE_CONTENT = b"fake parquet bytes"


def test_file_name_uses_first_month_of_quarter() -> None:
    assert file_name(2026, 3) == "2026-07-01_performance_mobile_tiles.parquet"


def test_invalid_quarter_raises() -> None:
    with pytest.raises(ValueError, match="quarter must be 1-4"):
        file_name(2026, 5)


def test_keys_use_hive_style_partitions() -> None:
    expected_source = (
        "parquet/performance/type=mobile/year=2025/quarter=4/"
        "2025-10-01_performance_mobile_tiles.parquet"
    )
    assert source_key(2025, 4) == expected_source
    assert raw_key(2025, 4).startswith("ookla/type=mobile/year=2025/quarter=4/")


@pytest.fixture
def s3(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=SOURCE_BUCKET)
        client.create_bucket(Bucket="raw")
        client.put_object(Bucket=SOURCE_BUCKET, Key=source_key(2026, 1), Body=FAKE_CONTENT)
        yield client


def test_ingest_copies_file_to_raw(s3) -> None:
    assert ingest_quarter(s3, s3, "raw", 2026, 1) is True
    stored = s3.get_object(Bucket="raw", Key=raw_key(2026, 1))["Body"].read()
    assert stored == FAKE_CONTENT


def test_ingest_is_idempotent(s3) -> None:
    ingest_quarter(s3, s3, "raw", 2026, 1)
    assert ingest_quarter(s3, s3, "raw", 2026, 1) is False
