"""AFDC / DOE Alternative Fuel Stations client."""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

from opengrid_mvp.config import AFDC_SOURCE, BBox, CENTRAL_PARK_BBOX, PROJECT_ROOT
from opengrid_mvp.geojson_utils import (
    add_source_metadata,
    filter_features_to_bbox,
    ensure_feature_collection,
)

AFDC_NEAREST_GEOJSON_URL = (
    "https://developer.nlr.gov/api/alt-fuel-stations/v1/nearest.geojson"
)


def fetch_afdc_stations(
    *,
    bbox: BBox = CENTRAL_PARK_BBOX,
    api_key: str | None = None,
    radius_miles: int = 2,
    timeout: int = 30,
) -> dict[str, Any]:
    """Fetch EV charging stations near the bbox center and filter to bbox."""

    load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")
    resolved_api_key = api_key or os.getenv("AFDC_API_KEY")
    if not resolved_api_key:
        raise RuntimeError(
            "AFDC_API_KEY is missing. Create a local .env file from .env.example "
            "and set AFDC_API_KEY before running this script."
        )

    response = requests.get(
        AFDC_NEAREST_GEOJSON_URL,
        params={
            "api_key": resolved_api_key,
            "latitude": bbox.center_lat,
            "longitude": bbox.center_lon,
            "radius": radius_miles,
            "limit": "all",
            "fuel_type": "ELEC",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    raw = ensure_feature_collection(response.json())
    filtered = filter_features_to_bbox(raw, bbox)
    return add_source_metadata(filtered, source=AFDC_SOURCE, bbox=bbox)
