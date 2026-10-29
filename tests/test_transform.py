import pytest
from shapely.geometry import box

from netbench.transform import assign_countries, clean, within_box

RAW_COLUMNS = [
    "quadkey",
    "tile_x",
    "tile_y",
    "avg_d_kbps",
    "avg_u_kbps",
    "avg_lat_ms",
    "tests",
    "devices",
    "year",
    "quarter",
]


@pytest.fixture
def raw(spark):
    rows = [
        ("q1", 0.5, 0.5, 50_000, 10_000, 20, 4, 2, 2026, 1),  # inside AA
        ("q2", 1.5, 0.5, 80_000, 20_000, 30, 1, 1, 2026, 1),  # inside BB
        ("q3", 9.0, 9.0, 90_000, 30_000, 25, 2, 1, 2026, 1),  # outside every country
        ("q4", 0.5, 0.5, 70_000, 10_000, 20, 0, 0, 2026, 1),  # 0 tests: invalid
    ]
    return spark.createDataFrame(rows, RAW_COLUMNS)


def test_clean_converts_units_and_drops_invalid_rows(raw) -> None:
    rows = {row["quadkey"]: row for row in clean(raw).collect()}
    assert set(rows) == {"q1", "q2", "q3"}
    assert rows["q1"]["download_mbps"] == 50.0
    assert rows["q1"]["upload_mbps"] == 10.0


def test_within_box_drops_far_away_tiles(raw) -> None:
    kept = within_box(clean(raw), (0.0, 0.0, 2.0, 1.0))
    assert {row["quadkey"] for row in kept.collect()} == {"q1", "q2"}


def test_assign_countries_uses_exact_polygons(raw) -> None:
    shapes = {"AA": box(0, 0, 1, 1), "BB": box(1, 0, 2, 1)}
    result = assign_countries(clean(raw), shapes)
    assert {row["quadkey"]: row["country_code"] for row in result.collect()} == {
        "q1": "AA",
        "q2": "BB",
    }
