from netbench.aggregate import country_kpis

COLUMNS = ["country_code", "year", "quarter", "download_mbps", "upload_mbps", "latency_ms", "tests"]


def test_averages_are_weighted_by_tests(spark) -> None:
    tiles = spark.createDataFrame(
        [
            ("HU", 2026, 1, 100.0, 10.0, 20.0, 1),
            ("HU", 2026, 1, 10.0, 10.0, 40.0, 9),
        ],
        COLUMNS,
    )
    row = country_kpis(tiles).collect()[0]
    # (100 * 1 + 10 * 9) / 10 = 19.0, not the plain mean (100 + 10) / 2 = 55.0
    assert row["avg_download_mbps"] == 19.0
    assert row["avg_latency_ms"] == 38.0
    assert row["tests"] == 10
    assert row["tiles"] == 2


def test_ranks_are_computed_per_quarter(spark) -> None:
    tiles = spark.createDataFrame(
        [
            ("HU", 2026, 1, 50.0, 10.0, 30.0, 1),
            ("PL", 2026, 1, 80.0, 10.0, 20.0, 1),
            ("HU", 2026, 2, 90.0, 10.0, 20.0, 1),
            ("PL", 2026, 2, 60.0, 10.0, 30.0, 1),
        ],
        COLUMNS,
    )
    ranks = {
        (row["country_code"], row["quarter"]): (row["download_rank"], row["latency_rank"])
        for row in country_kpis(tiles).collect()
    }
    assert ranks == {("PL", 1): (1, 1), ("HU", 1): (2, 2), ("HU", 2): (1, 1), ("PL", 2): (2, 2)}
