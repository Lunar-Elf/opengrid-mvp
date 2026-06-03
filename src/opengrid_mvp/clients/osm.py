"""OpenStreetMap Overpass API clients."""

from __future__ import annotations

from typing import Any

import requests
from requests import RequestException

from opengrid_mvp.config import (
    BBox,
    CENTRAL_PARK_BBOX,
    OSM_POWER_SOURCE,
    OSM_POWER_TAG_PATTERN,
    OVERPASS_API_URL,
)
from opengrid_mvp.geojson_utils import add_source_metadata, empty_feature_collection


def fetch_osm_power_infrastructure(
    *,
    bbox: BBox = CENTRAL_PARK_BBOX,
    timeout: int = 120,
) -> dict[str, Any]:
    """Fetch OSM power infrastructure from Overpass and return GeoJSON."""

    response = _post_with_retry(
        OVERPASS_API_URL,
        data={"data": build_power_query(bbox)},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    collection = overpass_to_geojson(payload)
    return add_source_metadata(collection, source=OSM_POWER_SOURCE, bbox=bbox)


def build_power_query(bbox: BBox) -> str:
    south = bbox.south
    west = bbox.west
    north = bbox.north
    east = bbox.east
    return f"""
[out:json][timeout:90];
(
  node["power"~"{OSM_POWER_TAG_PATTERN}"]({south},{west},{north},{east});
  way["power"~"{OSM_POWER_TAG_PATTERN}"]({south},{west},{north},{east});
  relation["power"~"{OSM_POWER_TAG_PATTERN}"]({south},{west},{north},{east});
);
out tags center geom;
""".strip()


def overpass_to_geojson(payload: dict[str, Any]) -> dict[str, Any]:
    features = []
    for element in payload.get("elements", []):
        feature = overpass_element_to_feature(element)
        if feature is not None:
            features.append(feature)
    collection = empty_feature_collection()
    collection["features"] = features
    return collection


def overpass_element_to_feature(element: dict[str, Any]) -> dict[str, Any] | None:
    geometry = _geometry_for_element(element)
    if geometry is None:
        return None

    properties = dict(element.get("tags") or {})
    properties.update(
        {
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
        }
    )
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": geometry,
    }


def _geometry_for_element(element: dict[str, Any]) -> dict[str, Any] | None:
    element_type = element.get("type")
    power_tag = (element.get("tags") or {}).get("power")

    if element_type == "node":
        lon = element.get("lon")
        lat = element.get("lat")
        if lon is None or lat is None:
            return None
        return {"type": "Point", "coordinates": [float(lon), float(lat)]}

    coordinates = _coordinates_from_geometry(element.get("geometry"))
    if len(coordinates) >= 2:
        if _is_closed(coordinates) and power_tag not in {"line", "minor_line"}:
            return {"type": "Polygon", "coordinates": [coordinates]}
        return {"type": "LineString", "coordinates": coordinates}

    center = element.get("center")
    if center and "lon" in center and "lat" in center:
        return {
            "type": "Point",
            "coordinates": [float(center["lon"]), float(center["lat"])],
        }

    return None


def _coordinates_from_geometry(geometry: Any) -> list[list[float]]:
    if not isinstance(geometry, list):
        return []
    coordinates = []
    for point in geometry:
        if not isinstance(point, dict) or "lon" not in point or "lat" not in point:
            continue
        coordinates.append([float(point["lon"]), float(point["lat"])])
    return coordinates


def _is_closed(coordinates: list[list[float]]) -> bool:
    return len(coordinates) >= 4 and coordinates[0] == coordinates[-1]


def _post_with_retry(
    url: str,
    *,
    data: dict[str, str],
    timeout: int,
    attempts: int = 3,
) -> requests.Response:
    last_error: RequestException | None = None
    for _ in range(attempts):
        try:
            return requests.post(
                url,
                data=data,
                headers={"User-Agent": "opengrid-mvp/0.1 (educational research)"},
                timeout=timeout,
            )
        except RequestException as exc:
            last_error = exc
    assert last_error is not None
    raise last_error
