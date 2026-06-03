"""EIA-860M power plant inventory client."""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv
from requests import RequestException

from opengrid_mvp.config import (
    BBox,
    CENTRAL_PARK_BBOX,
    EIA_OPERATING_GENERATOR_CAPACITY_URL,
    EIA_POWER_PLANTS_SOURCE,
    EIA_STATE_FACETS,
    PROJECT_ROOT,
)
from opengrid_mvp.geojson_utils import (
    add_source_metadata,
    empty_feature_collection,
    point_in_bbox,
)

EIA_DATA_COLUMNS = (
    "nameplate-capacity-mw",
    "net-summer-capacity-mw",
    "net-winter-capacity-mw",
    "operating-year-month",
    "planned-retirement-year-month",
    "longitude",
    "latitude",
)


def fetch_eia_power_plants(
    *,
    bbox: BBox = CENTRAL_PARK_BBOX,
    api_key: str | None = None,
    query_year: int | None = None,
    state_facets: tuple[str, ...] = EIA_STATE_FACETS,
    timeout: int = 60,
    length: int = 5000,
) -> dict[str, Any]:
    """Fetch EIA-860M generator records and filter to bbox."""

    load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")
    resolved_api_key = api_key or os.getenv("EIA_API_KEY")
    if not resolved_api_key:
        raise RuntimeError(
            "EIA_API_KEY is missing. Add EIA_API_KEY to your local .env file "
            "before running this script."
        )

    start_period, end_period = _period_bounds_for_year(query_year)
    rows = _fetch_rows(
        api_key=resolved_api_key,
        start_period=start_period,
        end_period=end_period,
        state_facets=state_facets,
        timeout=timeout,
        length=length,
    )
    collection = _rows_to_feature_collection(rows, bbox)
    return add_source_metadata(collection, source=EIA_POWER_PLANTS_SOURCE, bbox=bbox)


def _fetch_rows(
    *,
    api_key: str,
    start_period: str | None,
    end_period: str | None,
    state_facets: tuple[str, ...],
    timeout: int,
    length: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    total: int | None = None

    while total is None or offset < total:
        params = _base_params(api_key, state_facets) | {
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "sort[1][column]": "plantid",
            "sort[1][direction]": "asc",
            "offset": offset,
            "length": length,
        }
        if start_period is not None:
            params["start"] = start_period
        if end_period is not None:
            params["end"] = end_period

        response = _get_with_retry(
            EIA_OPERATING_GENERATOR_CAPACITY_URL,
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        _raise_for_eia_error(payload)

        response_data = payload.get("response", {})
        page_rows = response_data.get("data", [])
        rows.extend(page_rows)
        total = int(response_data.get("total", len(rows)))
        if not page_rows:
            break
        offset += len(page_rows)

    return rows


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


def _period_bounds_for_year(query_year: int | None) -> tuple[str | None, str | None]:
    if query_year is None:
        return None, None
    if query_year < 1800 or query_year > 2200:
        raise ValueError("query_year must be between 1800 and 2200.")
    return f"{query_year}-01", f"{query_year}-12"


def _base_params(api_key: str, state_facets: tuple[str, ...]) -> dict[str, Any]:
    params: dict[str, Any] = {
        "api_key": api_key,
        "frequency": "monthly",
    }
    for index, column in enumerate(EIA_DATA_COLUMNS):
        params[f"data[{index}]"] = column
    for index, state in enumerate(state_facets):
        params[f"facets[stateid][{index}]"] = state
    return params


def _raise_for_eia_error(payload: dict[str, Any]) -> None:
    if "error" in payload:
        raise RuntimeError(f"EIA query failed: {payload['error']}")


def _rows_to_feature_collection(rows: list[dict[str, Any]], bbox: BBox) -> dict[str, Any]:
    features = []
    for row in rows:
        lon = _parse_float(row.get("longitude"))
        lat = _parse_float(row.get("latitude"))
        if lon is None or lat is None or not point_in_bbox(lon, lat, bbox):
            continue
        features.append(
            {
                "type": "Feature",
                "properties": row,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            }
        )
    collection = empty_feature_collection()
    collection["features"] = features
    return collection


def _parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
