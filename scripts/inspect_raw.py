"""Print the schema, size and first rows of one raw Ookla Parquet file in MinIO."""

from urllib.parse import urlparse

import pyarrow.parquet as pq
from pyarrow import fs

from netbench.config import load_settings
from netbench.ingest import raw_key

settings = load_settings()
endpoint = urlparse(settings.s3_endpoint_url)

s3 = fs.S3FileSystem(
    access_key=settings.s3_access_key,
    secret_key=settings.s3_secret_key,
    endpoint_override=endpoint.netloc,
    scheme=endpoint.scheme,
    region="us-east-1",
)

path = f"{settings.raw_bucket}/{raw_key(2026, 3)}"
parquet_file = pq.ParquetFile(path, filesystem=s3)

print("=== Schema ===")
print(parquet_file.schema_arrow)
print(f"\nRows: {parquet_file.metadata.num_rows:,}")
print(f"Row groups: {parquet_file.metadata.num_row_groups}")

print("\n=== First 5 rows ===")
first_rows = parquet_file.read_row_group(0).slice(0, 5).to_pandas()
print(first_rows.to_string())
