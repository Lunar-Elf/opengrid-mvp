"""Generic ArcGIS FeatureServer GeoJSON client."""

from __future__ import annotations

from typing import Any

import requests
from requests import RequestException

from opengrid_mvp.config import BBox, CENTRAL_PARK_BBOX
from opengrid_mvp.geojson_utils import add_source_metadata, ensure_feature_collection


def fetch_arcgis_feature_layer(
    *,
    layer_url: str,
    source: dict[str, str],
    bbox: BBox = CENTRAL_PARK_BBOX,
    query_year: int | None = None,
    year_field: str | None = None,
    year_filter_kind: str | None = None,
    timeout: int = 30,
    result_record_count: int = 2000,
) -> dict[str, Any]:
    """Fetch features intersecting a WGS84 bbox from an ArcGIS Feature Layer."""

    where = build_where_clause(
        query_year=query_year,
        year_field=year_field,
        year_filter_kind=year_filter_kind,
    )
    response = _get_with_retry(
        f"{layer_url.rstrip('/')}/query",
        params={
            "where": where,
            "outFields": "*",
            "returnGeometry": "true",
            "geometryType": "esriGeometryEnvelope",
            "geometry": bbox.as_arcgis_geometry(),
            "inSR": 4326,
            "outSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "f": "geojson",
            "resultRecordCount": result_record_count,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and "error" in data:
        message = data["error"].get("message", "ArcGIS query failed")
        details = data["error"].get("details") or []
        raise RuntimeError(f"{message}: {details}")

    collection = ensure_feature_collection(data)
    return add_source_metadata(collection, source=source, bbox=bbox)


def _get_with_retry(
    url: str,
    *,
    params: dict[str, Any],
    timeout: int,
    attempts: int = 3,
) -> requests.Response:
    last_error: RequestException | None = None
    for _ in range(attempts):
        try:
            return requests.get(url, params=params, timeout=timeout)
        except RequestException as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def build_where_clause(
    *,
    query_year: int | None,
    year_field: str | None,
    year_filter_kind: str | None,
) -> str:
    """Build an ArcGIS where clause, optionally constrained to one year."""

    if query_year is None:
        return "1=1"
    if not year_field or not year_filter_kind:
        raise ValueError("year_field and year_filter_kind are required with query_year.")
    if query_year < 1800 or query_year > 2200:
        raise ValueError("query_year must be between 1800 and 2200.")

    if year_filter_kind == "numeric":
        return f"{year_field} = {query_year}"
    if year_filter_kind == "date":
        next_year = query_year + 1
        return (
            f"{year_field} >= timestamp '{query_year}-01-01 00:00:00' "
            f"AND {year_field} < timestamp '{next_year}-01-01 00:00:00'"
        )
    if year_filter_kind == "string_suffix":
        return f"{year_field} LIKE '%{query_year}'"

    raise ValueError(f"Unsupported ArcGIS year_filter_kind: {year_filter_kind}")
