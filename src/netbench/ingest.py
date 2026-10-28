"""Copy Ookla quarterly mobile Parquet files from the public bucket into the raw layer."""

import argparse
import logging

import boto3
from botocore import UNSIGNED
from botocore.client import BaseClient
from botocore.config import Config

from netbench.config import load_settings
from netbench.logging_setup import setup_logging
from netbench.storage import ensure_bucket, make_s3_client, object_exists

logger = logging.getLogger(__name__)

SOURCE_BUCKET = "ookla-open-data"
SOURCE_REGION = "us-west-2"
SERVICE_TYPE = "mobile"


def file_name(year: int, quarter: int) -> str:
    """Ookla names each file after the first day of its quarter."""
    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"quarter must be 1-4, got {quarter}")
    month = 3 * (quarter - 1) + 1
    return f"{year}-{month:02d}-01_performance_{SERVICE_TYPE}_tiles.parquet"


def source_key(year: int, quarter: int) -> str:
    prefix = f"parquet/performance/type={SERVICE_TYPE}/year={year}/quarter={quarter}"
    return f"{prefix}/{file_name(year, quarter)}"


def raw_key(year: int, quarter: int) -> str:
    prefix = f"ookla/type={SERVICE_TYPE}/year={year}/quarter={quarter}"
    return f"{prefix}/{file_name(year, quarter)}"


def make_source_client() -> BaseClient:
    """Anonymous client for the public Ookla bucket."""
    return boto3.client(
        "s3",
        region_name=SOURCE_REGION,
        config=Config(signature_version=UNSIGNED),
    )


def ingest_quarter(
    source: BaseClient,
    target: BaseClient,
    raw_bucket: str,
    year: int,
    quarter: int,
) -> bool:
    """Copy one quarter into the raw bucket. Return False if it was already there."""
    key = raw_key(year, quarter)
    if object_exists(target, raw_bucket, key):
        logger.info("Skipping %s: already in bucket %s", key, raw_bucket)
        return False

    src_key = source_key(year, quarter)
    logger.info("Copying s3://%s/%s", SOURCE_BUCKET, src_key)
    response = source.get_object(Bucket=SOURCE_BUCKET, Key=src_key)
    target.upload_fileobj(response["Body"], raw_bucket, key)
    logger.info("Stored s3://%s/%s", raw_bucket, key)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest one Ookla quarter into the raw bucket.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--quarter", type=int, required=True)
    args = parser.parse_args()

    setup_logging()
    settings = load_settings()
    target = make_s3_client(settings)
    ensure_bucket(target, settings.raw_bucket)
    ingest_quarter(make_source_client(), target, settings.raw_bucket, args.year, args.quarter)


if __name__ == "__main__":
    main()
