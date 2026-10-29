import json

import numpy as np
import pytest
from shapely.geometry import box

from netbench.geo import bounding_box, country_of_points, load_country_shapes

SHAPES = {"AA": box(0, 0, 1, 1), "BB": box(1, 0, 2, 1)}


def test_country_of_points_assigns_each_point_once() -> None:
    lon = np.array([0.5, 1.5, 5.0])
    lat = np.array([0.5, 0.5, 5.0])
    assert list(country_of_points(lon, lat, SHAPES)) == ["AA", "BB", None]


def test_bounding_box_covers_all_shapes() -> None:
    assert bounding_box(SHAPES) == (0.0, 0.0, 2.0, 1.0)


def test_load_country_shapes_filters_and_checks_missing(tmp_path) -> None:
    features = [
        {
            "type": "Feature",
            "properties": {"ISO_A2_EH": code},
            "geometry": geometry.__geo_interface__,
        }
        for code, geometry in SHAPES.items()
    ]
    path = tmp_path / "countries.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))

    assert set(load_country_shapes(path, ("AA",))) == {"AA"}
    with pytest.raises(ValueError, match="CC"):
        load_country_shapes(path, ("AA", "CC"))
