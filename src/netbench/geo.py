"""Country boundaries (Natural Earth) and point-in-polygon lookup for tile centres."""

import json
import logging
import shutil
import ssl
import urllib.request
from collections.abc import Mapping
from pathlib import Path

import certifi
import numpy as np
import shapely
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)

NATURAL_EARTH_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_10m_admin_0_countries.geojson"
)
DEFAULT_CACHE_DIR = Path("data/geo")
GEOJSON_NAME = "ne_10m_admin_0_countries.geojson"


def download_countries_geojson(cache_dir: Path = DEFAULT_CACHE_DIR) -> Path:
    """Download the Natural Earth country boundaries once and reuse the local copy."""
    target = cache_dir / GEOJSON_NAME
    if target.exists():
        return target
    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading country boundaries from %s", NATURAL_EARTH_URL)
    partial = target.with_suffix(".part")
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(NATURAL_EARTH_URL, context=context, timeout=120) as response:
        with partial.open("wb") as file:
            shutil.copyfileobj(response, file)
    partial.rename(target)  # rename is atomic: a half-downloaded file is never used
    return target


def load_country_shapes(geojson_path: Path, countries: tuple[str, ...]) -> dict[str, BaseGeometry]:
    """Return {ISO alpha-2 code: polygon} for the requested countries."""
    with geojson_path.open(encoding="utf-8") as file:
        features = json.load(file)["features"]

    shapes: dict[str, BaseGeometry] = {}
    for feature in features:
        properties = feature["properties"]
        code = properties.get("ISO_A2_EH") or properties.get("ISO_A2")
        if code in countries:
            shapes[code] = shape(feature["geometry"])

    missing = sorted(set(countries) - shapes.keys())
    if missing:
        raise ValueError(f"No boundary found for countries: {missing}")
    return shapes


def bounding_box(shapes: Mapping[str, BaseGeometry]) -> tuple[float, float, float, float]:
    """Smallest (min_lon, min_lat, max_lon, max_lat) box containing all the shapes."""
    bounds = np.array([geometry.bounds for geometry in shapes.values()])
    return (
        float(bounds[:, 0].min()),
        float(bounds[:, 1].min()),
        float(bounds[:, 2].max()),
        float(bounds[:, 3].max()),
    )


def country_of_points(
    lon: np.ndarray, lat: np.ndarray, shapes: Mapping[str, BaseGeometry]
) -> np.ndarray:
    """ISO code of the country containing each point, or None when outside all of them."""
    result = np.full(len(lon), None, dtype=object)
    unassigned = np.ones(len(lon), dtype=bool)
    for code, geometry in shapes.items():
        shapely.prepare(geometry)  # builds a spatial index once, makes contains_xy fast
        inside = shapely.contains_xy(geometry, lon, lat) & unassigned
        result[inside] = code
        unassigned &= ~inside
    return result
