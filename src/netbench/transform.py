"""Raw -> processed: clean Ookla tiles and assign each tile to a country (PySpark)."""

import logging
from collections.abc import Iterator, Mapping

import pandas as pd
import shapely
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from shapely.geometry.base import BaseGeometry

from netbench.config import Settings, load_settings
from netbench.geo import (
    bounding_box,
    country_of_points,
    download_countries_geojson,
    load_country_shapes,
)
from netbench.logging_setup import setup_logging
from netbench.spark import build_spark_session, s3a_path

logger = logging.getLogger(__name__)

RAW_PREFIX = "ookla/type=mobile/"
PROCESSED_PREFIX = "ookla_mobile_tiles/"

PROCESSED_SCHEMA = (
    "quadkey string, tile_x double, tile_y double, year int, quarter int, "
    "download_mbps double, upload_mbps double, latency_ms double, "
    "tests long, devices long, country_code string"
)


def clean(raw: DataFrame) -> DataFrame:
    """Keep valid measurements, convert kbps to Mbps and select the needed columns."""
    valid = (
        (F.col("tests") > 0)
        & (F.col("avg_d_kbps") >= 0)
        & (F.col("avg_u_kbps") >= 0)
        & F.col("avg_lat_ms").isNotNull()
    )
    return raw.where(valid).select(
        "quadkey",
        "tile_x",
        "tile_y",
        F.col("year").cast("int"),
        F.col("quarter").cast("int"),
        (F.col("avg_d_kbps") / 1000).alias("download_mbps"),
        (F.col("avg_u_kbps") / 1000).alias("upload_mbps"),
        F.col("avg_lat_ms").cast("double").alias("latency_ms"),
        F.col("tests").cast("long"),
        F.col("devices").cast("long"),
    )


def within_box(tiles: DataFrame, box: tuple[float, float, float, float]) -> DataFrame:
    """Cheap pre-filter: drop tiles far outside the countries before the exact polygon test."""
    min_lon, min_lat, max_lon, max_lat = box
    return tiles.where(
        F.col("tile_x").between(min_lon, max_lon) & F.col("tile_y").between(min_lat, max_lat)
    )


def assign_countries(tiles: DataFrame, shapes: Mapping[str, BaseGeometry]) -> DataFrame:
    """Add country_code with an exact point-in-polygon test; drop tiles outside all countries."""
    # Geometries travel to the workers as compact WKB bytes inside the function closure.
    wkb = {code: shapely.to_wkb(geometry) for code, geometry in shapes.items()}

    def lookup(batches: Iterator[pd.DataFrame]) -> Iterator[pd.DataFrame]:
        local_shapes = {code: shapely.from_wkb(blob) for code, blob in wkb.items()}
        for batch in batches:
            codes = country_of_points(
                batch["tile_x"].to_numpy(), batch["tile_y"].to_numpy(), local_shapes
            )
            batch["country_code"] = codes
            yield batch[batch["country_code"].notna()]

    return tiles.mapInPandas(lookup, schema=PROCESSED_SCHEMA)


def run(spark: SparkSession, settings: Settings) -> None:
    shapes = load_country_shapes(download_countries_geojson(), settings.countries)
    raw = spark.read.parquet(s3a_path(settings.raw_bucket, RAW_PREFIX))
    processed = assign_countries(within_box(clean(raw), bounding_box(shapes)), shapes)

    target = s3a_path(settings.processed_bucket, PROCESSED_PREFIX)
    processed.write.mode("overwrite").partitionBy("year", "quarter").parquet(target)
    logger.info("Wrote processed tiles to %s", target)


def main() -> None:
    setup_logging()
    settings = load_settings()
    spark = build_spark_session(settings, "netbench-transform")
    try:
        run(spark, settings)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
