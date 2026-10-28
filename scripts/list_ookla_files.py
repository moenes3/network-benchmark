"""List the Ookla mobile Parquet files available in the public S3 bucket."""

import boto3
from botocore import UNSIGNED
from botocore.config import Config

SOURCE_BUCKET = "ookla-open-data"
PREFIX = "parquet/performance/type=mobile/"

client = boto3.client(
    "s3",
    region_name="us-west-2",
    config=Config(signature_version=UNSIGNED),
)

paginator = client.get_paginator("list_objects_v2")
for page in paginator.paginate(Bucket=SOURCE_BUCKET, Prefix=PREFIX):
    for obj in page.get("Contents", []):
        size_mb = obj["Size"] / 1_000_000
        print(f"{obj['Key']}  {size_mb:,.1f} MB")
