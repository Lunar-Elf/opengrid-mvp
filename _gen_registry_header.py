"""Registered data sources exposed as deterministic fetch tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from opengrid_mvp.clients.afdc import fetch_afdc_stations
from opengrid_mvp.clients.arcgis import fetch_arcgis_feature_layer
from opengrid_mvp.clients.eia import fetch_eia_power_plants
from opengrid_mvp.clients.gee import fetch_modis_landuse_tif, fetch_sentinel2_rgb_tif
from opengrid_mvp.clients.osm import fetch_osm_power_infrastructure
from opengrid_mvp.config import (
    BBox,
    EIA_POWER_PLANTS_SOURCE,
    HIFLD_SUBSTATIONS_FEATURE_LAYER_URL,
    HIFLD_SUBSTATIONS_SOURCE,
    HIFLD_SUBSTATIONS_YEAR_FIELD,
    HIFLD_SUBSTATIONS_YEAR_FILTER_KIND,
    MODIS_LANDUSE_SOURCE,
    SENTINEL2_SOURCE,
    NARN_FEATURE_LAYER_URL,
    NARN_SOURCE,
    NHS_FEATURE_LAYER_URL,
    NHS_SOURCE,
    NHS_YEAR_FIELD,
    NHS_YEAR_FILTER_KIND,
    OSM_POWER_SOURCE,
    USACE_NWN_FEATURE_LAYER_URL,
    USACE_NWN_SOURCE,
    USACE_NWN_YEAR_FIELD,
    USACE_NWN_YEAR_FILTER_KIND,
)
from opengrid_mvp.geojson_utils import merge_feature_collections, save_geojson

GeoJSON = dict[str, Any]
SourceOutput = GeoJSON | Path
Fetcher = Callable[[BBox, int | None, Path | None], SourceOutput]


@dataclass(frozen=True)
class DatasetSource:
    source_id: str
    filename: str
    source_name: str
    category: str
    description: str
    aliases: tuple[str, ...]
    fetcher: Fetcher
    output_kind: str = "geojson"
    include_in_default_all: bool = True