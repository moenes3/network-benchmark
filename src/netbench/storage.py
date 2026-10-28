"""Helpers for S3-compatible object storage (MinIO locally, AWS S3 in the cloud)."""

import logging

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from netbench.config import Settings, load_settings
from netbench.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def make_s3_client(settings: Settings) -> BaseClient:
    """Create a boto3 S3 client pointed at the configured endpoint."""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}),
    )


def ensure_bucket(client: BaseClient, name: str) -> bool:
    """Create the bucket if it does not exist. Return True if it was created."""
    try:
        client.head_bucket(Bucket=name)
        logger.info("Bucket %s already exists", name)
        return False
    except ClientError as error:
        if error.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
            raise
    client.create_bucket(Bucket=name)
    logger.info("Created bucket %s", name)
    return True


def ensure_buckets(client: BaseClient, settings: Settings) -> None:
    """Make sure every data-layer bucket exists."""
    for name in (
        settings.raw_bucket,
        settings.processed_bucket,
        settings.analytics_bucket,
        settings.reports_bucket,
    ):
        ensure_bucket(client, name)


def main() -> None:
    setup_logging()
    settings = load_settings()
    ensure_buckets(make_s3_client(settings), settings)


if __name__ == "__main__":
    main()
