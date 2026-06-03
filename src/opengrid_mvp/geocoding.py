"""Geocoding helpers for turning place requests into WGS84 BBOXes."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv
from requests import RequestException

from opengrid_mvp.config import BBox, PROJECT_ROOT

EARTH_RADIUS_KM = 6371.0088
DEFAULT_RADIUS_KM = 3.0
AMAP_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
BAIDU_GEOCODE_URL = "https://api.map.baidu.com/geocoding/v3/"
GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
MAP_API_TIMEOUT = 30
X_PI = math.pi * 3000.0 / 180.0
EE = 0.00669342162296594323
A = 6378245.0

@dataclass(frozen=True)
class PlaceAOI:
    """A geocoded area of interest."""

    place_query: str
    label: str
    latitude: float
    longitude: float
    radius_km: float
    bbox: BBox
    provider: str = ""
    location_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "place_query": self.place_query,
            "label": self.label,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius_km": self.radius_km,
            "bbox": self.bbox.as_dict(),
            "provider": self.provider,
            "location_type": self.location_type,
        }


@dataclass(frozen=True)
class GeocodeCandidate:
    label: str
    latitude: float
    longitude: float
    provider: str
    location_type: str | None = None




def bbox_from_point_radius(
    *,
    latitude: float,
    longitude: float,
    radius_km: float = DEFAULT_RADIUS_KM,
) -> BBox:
    """Build an approximate WGS84 bbox around a point and radius."""

    if radius_km <= 0:
        raise ValueError("radius_km must be greater than zero.")
    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180.")

    lat_delta = math.degrees(radius_km / EARTH_RADIUS_KM)
    cos_lat = math.cos(math.radians(latitude))
    if abs(cos_lat) < 1e-12:
        lon_delta = 180.0
    else:
        lon_delta = math.degrees(radius_km / (EARTH_RADIUS_KM * cos_lat))

    return BBox(
        west=max(-180.0, longitude - lon_delta),
        south=max(-90.0, latitude - lat_delta),
        east=min(180.0, longitude + lon_delta),
        north=min(90.0, latitude + lat_delta),
    )


def geocode_place(
    place_query: str,
    *,
    radius_km: float = DEFAULT_RADIUS_KM,
    timeout: int = 30,
) -> PlaceAOI:
    """Geocode a semantic place string via Nominatim, then AMap, then Baidu."""

    cleaned_query = place_query.strip()
    if not cleaned_query:
        raise ValueError("place_query cannot be empty.")

    candidate = geocode_with_map_providers(cleaned_query, timeout=timeout)
    if candidate is None:
        raise RuntimeError(f"Could not geocode place: {cleaned_query}")

    bbox = bbox_from_point_radius(
        latitude=candidate.latitude,
        longitude=candidate.longitude,
        radius_km=radius_km,
    )
    return PlaceAOI(
        place_query=cleaned_query,
        label=candidate.label,
        latitude=candidate.latitude,
        longitude=candidate.longitude,
        radius_km=radius_km,
        bbox=bbox,
        provider=candidate.provider,
        location_type=candidate.location_type,
    )


def geocode_with_map_providers(
    address: str,
    *,
    timeout: int = MAP_API_TIMEOUT,
) -> GeocodeCandidate | None:
    """Try geocoding providers: Google first, switch to AMap/Baidu if in China."""

    load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")

    # 1) Google -- best global coverage, fast and reliable
    google_key = os.getenv("GOOGLE_GEOCODE_API_KEY", "").strip()
    google_candidate = None
    if google_key:
        google_candidate = google_geocode(address, api_key=google_key, timeout=timeout)

    if google_candidate is not None:
        # For addresses inside China, AMap/Baidu have more accurate local coordinates
        if not out_of_china(google_candidate.longitude, google_candidate.latitude):
            amap_key = os.getenv("AMAP_API_KEY", "").strip()
            if amap_key:
                cn_candidate = amap_geocode(address, api_key=amap_key, timeout=timeout)
                if cn_candidate is not None:
                    return cn_candidate
            baidu_key = os.getenv("BAIDU_API_KEY", "").strip()
            if baidu_key:
                cn_candidate = baidu_geocode(address, api_key=baidu_key, timeout=timeout)
                if cn_candidate is not None:
                    return cn_candidate
        return google_candidate

    # 2) AMap -- fallback for Chinese addresses when Google is unavailable
    amap_key = os.getenv("AMAP_API_KEY", "").strip()
    if amap_key:
        candidate = amap_geocode(address, api_key=amap_key, timeout=timeout)
        if candidate is not None:
            return candidate

    # 3) Baidu -- last resort for Chinese addresses
    baidu_key = os.getenv("BAIDU_API_KEY", "").strip()
    if baidu_key:
        candidate = baidu_geocode(address, api_key=baidu_key, timeout=timeout)
        if candidate is not None:
            return candidate

    if not google_key and not amap_key and not baidu_key:
        raise RuntimeError(
            "All geocoding providers failed. Set GOOGLE_GEOCODE_API_KEY, "
            "AMAP_API_KEY, or BAIDU_API_KEY in .env."
        )
    return None


def google_geocode(
    address: str,
    *,
    api_key: str,
    timeout: int = MAP_API_TIMEOUT,
) -> GeocodeCandidate | None:
    """Use Google Geocoding API and return a WGS84 candidate."""

    response = requests.get(
        GOOGLE_GEOCODE_URL,
        params={"address": address, "key": api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "OK" or not data.get("results"):
        return None

    result = data["results"][0]
    location = result.get("geometry", {}).get("location", {})
    lat = location.get("lat")
    lng = location.get("lng")
    if lat is None or lng is None:
        return None

    label = result.get("formatted_address") or address
    location_type = result.get("geometry", {}).get("location_type")
    return GeocodeCandidate(
        label=f"{label} (Google)",
        latitude=float(lat),
        longitude=float(lng),
        provider="google",
        location_type=location_type,
    )


def amap_geocode(
    address: str,
    *,
    api_key: str,
    timeout: int = MAP_API_TIMEOUT,
) -> GeocodeCandidate | None:
    """Use AMap geocoding and return a WGS84 candidate."""

    response = requests.get(
        AMAP_GEOCODE_URL,
        params={"address": address, "key": api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "1" or not data.get("geocodes"):
        return None

    geocode = data["geocodes"][0]
    location = geocode.get("location")
    if not location:
        return None

    gcj_lon, gcj_lat = map(float, location.split(","))
    wgs_lon, wgs_lat = gcj02_to_wgs84(gcj_lon, gcj_lat)
    label = geocode.get("formatted_address") or address
    return GeocodeCandidate(
        label=f"{label} (AMap)",
        latitude=wgs_lat,
        longitude=wgs_lon,
        provider="amap",
    )


def baidu_geocode(
    address: str,
    *,
    api_key: str,
    timeout: int = MAP_API_TIMEOUT,
) -> GeocodeCandidate | None:
    """Use Baidu geocoding and return a WGS84 candidate."""

    response = requests.get(
        BAIDU_GEOCODE_URL,
        params={"address": address, "output": "json", "ak": api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != 0:
        return None

    location = data.get("result", {}).get("location") or {}
    bd_lon = float(location["lng"])
    bd_lat = float(location["lat"])
    gcj_lon, gcj_lat = bd09_to_gcj02(bd_lon, bd_lat)
    wgs_lon, wgs_lat = gcj02_to_wgs84(gcj_lon, gcj_lat)
    confidence = data.get("result", {}).get("confidence")
    suffix = f"Baidu, confidence={confidence}" if confidence is not None else "Baidu"
    return GeocodeCandidate(
        label=f"{address} ({suffix})",
        latitude=wgs_lat,
        longitude=wgs_lon,
        provider="baidu",
    )


def bd09_to_gcj02(lon: float, lat: float) -> tuple[float, float]:
    x = lon - 0.0065
    y = lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * X_PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * X_PI)
    return z * math.cos(theta), z * math.sin(theta)


def gcj02_to_wgs84(lon: float, lat: float) -> tuple[float, float]:
    if out_of_china(lon, lat):
        return lon, lat

    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlon = _transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((A * (1 - EE)) / (magic * sqrt_magic) * math.pi)
    dlon = (dlon * 180.0) / (A / sqrt_magic * math.cos(radlat) * math.pi)
    mg_lat = lat + dlat
    mg_lon = lon + dlon
    return lon * 2 - mg_lon, lat * 2 - mg_lat


def out_of_china(lon: float, lat: float) -> bool:
    return not (73.66 < lon < 135.05 and 3.86 < lat < 53.55)


def _transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y
    ret += 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lon(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x
    ret += 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret
