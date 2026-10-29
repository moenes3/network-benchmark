"""Processed -> analytics: test-weighted KPIs and rankings per country and quarter (PySpark)."""

import logging

from pyspark.sql import Column, DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from netbench.config import Settings, load_settings
from netbench.logging_setup import setup_logging
from netbench.spark import build_spark_session, s3a_path
from netbench.transform import PROCESSED_PREFIX

logger = logging.getLogger(__name__)

KPIS_PREFIX = "country_quarter_kpis/"


def _weighted_avg(column: str) -> Column:
    """Average of tile averages, weighted by each tile's number of tests."""
    return F.round(F.sum(F.col(column) * F.col("tests")) / F.sum("tests"), 2)


def country_kpis(tiles: DataFrame) -> DataFrame:
    """One row per country and quarter, with weighted averages and rankings."""
    kpis = tiles.groupBy("country_code", "year", "quarter").agg(
        F.count("*").alias("tiles"),
        F.sum("tests").alias("tests"),
        _weighted_avg("download_mbps").alias("avg_download_mbps"),
        _weighted_avg("upload_mbps").alias("avg_upload_mbps"),
        _weighted_avg("latency_ms").alias("avg_latency_ms"),
    )
    period = Window.partitionBy("year", "quarter")
    return kpis.withColumn(
        "download_rank", F.dense_rank().over(period.orderBy(F.desc("avg_download_mbps")))
    ).withColumn("latency_rank", F.dense_rank().over(period.orderBy("avg_latency_ms")))


def run(spark: SparkSession, settings: Settings) -> None:
    tiles = spark.read.parquet(s3a_path(settings.processed_bucket, PROCESSED_PREFIX))
    kpis = country_kpis(tiles).cache()  # used twice below: compute it only once

    target = s3a_path(settings.analytics_bucket, KPIS_PREFIX)
    kpis.coalesce(1).write.mode("overwrite").parquet(target)  # small table: one file
    logger.info("Wrote %d KPI rows to %s", kpis.count(), target)
    kpis.orderBy("year", "quarter", "download_rank").show(50, truncate=False)


def main() -> None:
    setup_logging()
    settings = load_settings()
    spark = build_spark_session(settings, "netbench-aggregate")
    try:
        run(spark, settings)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
