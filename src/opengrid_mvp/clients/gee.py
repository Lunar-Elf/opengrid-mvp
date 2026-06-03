"""Google Earth Engine raster clients."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from opengrid_mvp.config import (
    SENTINEL2_COLLECTION_ID,
    SENTINEL2_DEFAULT_YEAR,
    SENTINEL2_MAX_YEAR,
    SENTINEL2_MIN_YEAR,
    SENTINEL2_SCALE_METERS,
    SENTINEL2_MAX_CLOUD_COVER,
    BBox,
    CENTRAL_PARK_BBOX,
    MODIS_LANDUSE_COLLECTION_ID,
    MODIS_LANDUSE_DEFAULT_BAND,
    MODIS_LANDUSE_DEFAULT_YEAR,
    MODIS_LANDUSE_MAX_YEAR,
    MODIS_LANDUSE_MIN_YEAR,
    MODIS_LANDUSE_SCALE_METERS,
    PROJECT_ROOT,
)


def fetch_modis_landuse_tif(
    *,
    output_path: Path,
    bbox: BBox = CENTRAL_PARK_BBOX,
    query_year: int | None = None,
    band: str = MODIS_LANDUSE_DEFAULT_BAND,
    scale_meters: int = MODIS_LANDUSE_SCALE_METERS,
    timeout: int = 180,
) -> Path:
    """Download a MODIS MCD12Q1 land-use band as a GeoTIFF."""

    ee = _import_earth_engine()
    _initialize_earth_engine(ee)

    year = resolve_modis_landuse_year(query_year)
    region = ee.Geometry.Rectangle(
        [bbox.west, bbox.south, bbox.east, bbox.north],
        proj="EPSG:4326",
        geodesic=False,
    )
    image = (
        ee.ImageCollection(MODIS_LANDUSE_COLLECTION_ID)
        .filterDate(f"{year}-01-01", f"{year + 1}-01-01")
        .first()
        .select(band)
        .clip(region)
    )

    download_url = image.getDownloadURL(
        {
            "name": f"modis_landuse_{band}_{year}",
            "region": region,
            "scale": scale_meters,
            "crs": "EPSG:4326",
            "format": "GEO_TIFF",
        }
    )
    response = requests.get(download_url, timeout=timeout)
    response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path


def resolve_modis_landuse_year(query_year: int | None) -> int:
    year = query_year or MODIS_LANDUSE_DEFAULT_YEAR
    if year < MODIS_LANDUSE_MIN_YEAR or year > MODIS_LANDUSE_MAX_YEAR:
        raise ValueError(
            "MODIS MCD12Q1 query year must be between "
            f"{MODIS_LANDUSE_MIN_YEAR} and {MODIS_LANDUSE_MAX_YEAR}."
        )
    return year


def _import_earth_engine() -> Any:
    try:
        import ee
    except ImportError as exc:
        raise RuntimeError(
            "earthengine-api is not installed. Run `pip install -r requirements.txt` "
            "before using the MODIS land-use tool."
        ) from exc
    return ee


def _initialize_earth_engine(ee: Any) -> None:
    load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or None
    try:
        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()
    except Exception as exc:
        raise RuntimeError(
            "Google Earth Engine is not authenticated or initialized. Run "
            "`earthengine authenticate`, or configure application default "
            "credentials and optionally GOOGLE_CLOUD_PROJECT in .env."
        ) from exc

def fetch_sentinel2_rgb_tif(
    *,
    output_path: Path,
    bbox: BBox = CENTRAL_PARK_BBOX,
    query_year: int | None = None,
    scale_meters: int = SENTINEL2_SCALE_METERS,
    max_cloud_cover: int = SENTINEL2_MAX_CLOUD_COVER,
    timeout: int = 300,
) -> Path:
    """Download a cloud-masked Sentinel-2 RGB composite as a 3-band GeoTIFF."""

    ee = _import_earth_engine()
    _initialize_earth_engine(ee)

    year = resolve_sentinel2_year(query_year)
    region = ee.Geometry.Rectangle(
        [bbox.west, bbox.south, bbox.east, bbox.north],
        proj="EPSG:4326",
        geodesic=False,
    )

    # Helper: mask clouds using QA60 band
    def mask_s2_clouds(image):
        qa = image.select("QA60")
        # Bits 10 (opaque) and 11 (cirrus) indicate clouds
        cloud_bit_mask = (1 << 10) | (1 << 11)
        mask = qa.bitwiseAnd(cloud_bit_mask).eq(0)
        return image.updateMask(mask)

    # Composite over June--September for best cloud-free coverage
    collection = (
        ee.ImageCollection(SENTINEL2_COLLECTION_ID)
        .filterBounds(region)
        .filterDate(f"{year}-06-01", f"{year}-09-30")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_cover))
        .map(mask_s2_clouds)
        .select(["B4", "B3", "B2"], ["R", "G", "B"])
    )

    image = collection.median().clip(region)

    download_url = image.getDownloadURL(
        {
            "name": f"sentinel2_rgb_{year}",
            "region": region,
            "scale": scale_meters,
            "crs": "EPSG:4326",
            "format": "GEO_TIFF",
        }
    )
    response = requests.get(download_url, timeout=timeout)
    response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path


def resolve_sentinel2_year(query_year: int | None) -> int:
    year = query_year or SENTINEL2_DEFAULT_YEAR
    if year < SENTINEL2_MIN_YEAR or year > SENTINEL2_MAX_YEAR:
        raise ValueError(
            "Sentinel-2 query year must be between "
            f"{SENTINEL2_MIN_YEAR} and {SENTINEL2_MAX_YEAR}."
        )
    return year
