"""SparkSession factory: local mode, with S3A configured for MinIO (or AWS S3)."""

import os
import sys

from pyspark.sql import SparkSession

from netbench.config import Settings

# Must match the Hadoop version bundled with PySpark 4.0.x (Hadoop 3.4.1).
HADOOP_AWS_PACKAGE = "org.apache.hadoop:hadoop-aws:3.4.1"
S3A_CREDENTIALS = "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider"


def s3a_path(bucket: str, prefix: str) -> str:
    """Build an s3a:// URI, the scheme Spark/Hadoop use for S3-compatible storage."""
    return f"s3a://{bucket}/{prefix}"


def build_spark_session(settings: Settings, app_name: str) -> SparkSession:
    """Create (or reuse) a local SparkSession that can read and write s3a:// paths."""
    # Make Spark's Python workers use the same interpreter (and venv) as the driver.
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    use_ssl = str(settings.s3_endpoint_url.startswith("https")).lower()

    builder = (
        SparkSession.builder.appName(app_name)
        .master(os.environ.get("SPARK_MASTER", "local[*]"))
        .config("spark.driver.memory", os.environ.get("SPARK_DRIVER_MEMORY", "4g"))
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "16")
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .config("spark.jars.packages", HADOOP_AWS_PACKAGE)
        .config("spark.hadoop.fs.s3a.endpoint", settings.s3_endpoint_url)
        .config("spark.hadoop.fs.s3a.endpoint.region", "us-east-1")
        .config("spark.hadoop.fs.s3a.access.key", settings.s3_access_key)
        .config("spark.hadoop.fs.s3a.secret.key", settings.s3_secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", use_ssl)
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", S3A_CREDENTIALS)
    )
    return builder.getOrCreate()
