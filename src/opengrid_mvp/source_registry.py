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

def _fetch_afdc(
    bbox: BBox,
    query_year: int | None = None,
    output_path: Path | None = None,
) -> GeoJSON:
    return fetch_afdc_stations(bbox=bbox)


def _fetch_eia_power_plants(
    bbox: BBox,
    query_year: int | None = None,
    output_path: Path | None = None,
) -> GeoJSON:
    return fetch_eia_power_plants(bbox=bbox, query_year=query_year)


def _fetch_nhs(
    bbox: BBox,
    query_year: int | None = None,
    output_path: Path | None = None,
) -> GeoJSON:
    return fetch_arcgis_feature_layer(
        layer_url=NHS_FEATURE_LAYER_URL,
        source=NHS_SOURCE,
        bbox=bbox,
        query_year=query_year,
        year_field=NHS_YEAR_FIELD,
        year_filter_kind=NHS_YEAR_FILTER_KIND,
    )


def _fetch_narn(
    bbox: BBox,
    query_year: int | None = None,
    output_path: Path | None = None,
) -> GeoJSON:
    return fetch_arcgis_feature_layer(
        layer_url=NARN_FEATURE_LAYER_URL,
        source=NARN_SOURCE,
        bbox=bbox,
    )


def _fetch_hifld_substations(
    bbox: BBox,
    query_year: int | None = None,
    output_path: Path | None = None,
) -> GeoJSON:
    return fetch_arcgis_feature_layer(
        layer_url=HIFLD_SUBSTATIONS_FEATURE_LAYER_URL,
        source=HIFLD_SUBSTATIONS_SOURCE,
        bbox=bbox,
        query_year=query_year,
        year_field=HIFLD_SUBSTATIONS_YEAR_FIELD,
        year_filter_kind=HIFLD_SUBSTATIONS_YEAR_FILTER_KIND,
    )


def _fetch_usace_nwn(
    bbox: BBox,
    query_year: int | None = None,
    output_path: Path | None = None,
) -> GeoJSON:
    return fetch_arcgis_feature_layer(
        layer_url=USACE_NWN_FEATURE_LAYER_URL,
        source=USACE_NWN_SOURCE,
        bbox=bbox,
        query_year=query_year,
        year_field=USACE_NWN_YEAR_FIELD,
        year_filter_kind=USACE_NWN_YEAR_FILTER_KIND,
    )


def _fetch_modis_landuse(
    bbox: BBox,
    query_year: int | None = None,
    output_path: Path | None = None,
) -> Path:
    if output_path is None:
        raise RuntimeError("MODIS land-use fetcher requires an output_path.")
    return fetch_modis_landuse_tif(
        bbox=bbox,
        query_year=query_year,
        output_path=output_path,
    )


def _fetch_sentinel2(
    bbox: BBox,
    query_year: int | None = None,
    output_path: Path | None = None,
) -> Path:
    if output_path is None:
        raise RuntimeError("Sentinel-2 RGB fetcher requires an output_path.")
    return fetch_sentinel2_rgb_tif(
        bbox=bbox,
        query_year=query_year,
        output_path=output_path,
    )


def _fetch_osm_power(
    bbox: BBox,
    query_year: int | None = None,
    output_path: Path | None = None,
) -> GeoJSON:
    return fetch_osm_power_infrastructure(bbox=bbox)


REGISTERED_SOURCES: dict[str, DatasetSource] = {
    "afdc_stations": DatasetSource(
        source_id="afdc_stations",
        filename="afdc_stations.geojson",
        source_name="AFDC / DOE Alternative Fuel Stations",
        category="electric_vehicle_charging_stations",
        description="Electric vehicle charging and alternative fuel stations.",
        aliases=("afdc", "ev", "charging", "charger", "fuel", "充电", "充电桩"),
        fetcher=_fetch_afdc,
    ),
    "national_highway_system": DatasetSource(
        source_id="national_highway_system",
        filename="national_highway_system.geojson",
        source_name=NHS_SOURCE["source_name"],
        category=NHS_SOURCE["category"],
        description="National Highway System road network segments.",
        aliases=("nhs", "highway", "road", "transport", "公路", "道路", "高速"),
        fetcher=_fetch_nhs,
    ),
    "north_american_rail": DatasetSource(
        source_id="north_american_rail",
        filename="north_american_rail.geojson",
        source_name=NARN_SOURCE["source_name"],
        category=NARN_SOURCE["category"],
        description="North American rail network line features.",
        aliases=("narn", "rail", "railroad", "railway", "train", "铁路", "火车"),
        fetcher=_fetch_narn,
    ),
    "hifld_electric_substations": DatasetSource(
        source_id="hifld_electric_substations",
        filename="hifld_electric_substations.geojson",
        source_name=HIFLD_SUBSTATIONS_SOURCE["source_name"],
        category=HIFLD_SUBSTATIONS_SOURCE["category"],
        description="Electric substations from HIFLD.",
        aliases=("hifld", "substation", "substations", "grid", "变电站", "电网"),
        fetcher=_fetch_hifld_substations,
    ),
    "usace_national_waterway_network": DatasetSource(
        source_id="usace_national_waterway_network",
        filename="usace_national_waterway_network.geojson",
        source_name=USACE_NWN_SOURCE["source_name"],
        category=USACE_NWN_SOURCE["category"],
        description="Navigable waterway network line features.",
        aliases=("usace", "waterway", "river", "canal", "水路", "河流", "运河"),
        fetcher=_fetch_usace_nwn,
    ),
    "eia_power_plants": DatasetSource(
        source_id="eia_power_plants",
        filename="eia_power_plants.geojson",
        source_name=EIA_POWER_PLANTS_SOURCE["source_name"],
        category=EIA_POWER_PLANTS_SOURCE["category"],
        description="Operating generator capacity and power plant locations.",
        aliases=("eia", "power plant", "generator", "generation", "电厂", "发电厂"),
        fetcher=_fetch_eia_power_plants,
    ),
    "osm_power": DatasetSource(
        source_id="osm_power",
        filename="osm_power_infrastructure.geojson",
        source_name=OSM_POWER_SOURCE["source_name"],
        category=OSM_POWER_SOURCE["category"],
        description="Power infrastructure geometries from the OpenStreetMap power layer.",
        aliases=(
            "osm",
            "openstreetmap",
            "power",
            "power infrastructure",
            "transmission",
            "transmission line",
            "power line",
            "generator",
            "generation asset",
            "输电",
            "配电",
            "电力",
            "电力设施",
        ),
        fetcher=_fetch_osm_power,
    ),
    "modis_landuse": DatasetSource(
        source_id="modis_landuse",
        filename="modis_landuse.tif",
        source_name=MODIS_LANDUSE_SOURCE["source_name"],
        category=MODIS_LANDUSE_SOURCE["category"],
        description="MODIS MCD12Q1 annual land-use and land-cover raster.",
        aliases=(
            "modis",
            "mcd12q1",
            "landuse",
            "land use",
            "land cover",
            "lulc",
            "土地利用",
            "土地覆盖",
        ),
        fetcher=_fetch_modis_landuse,
        output_kind="tif",
    ),
    "sentinel2_rgb": DatasetSource(
        source_id="sentinel2_rgb",
        filename="sentinel2_rgb.tif",
        source_name=SENTINEL2_SOURCE["source_name"],
        category=SENTINEL2_SOURCE["category"],
        description="Cloud-masked Sentinel-2 RGB composite at 10 m resolution.",
        aliases=(
            "sentinel2",
            "sentinel",
            "sentinel-2",
            "sentinel 2",
            "satellite",
            "rgb",
            "imagery",
            "satellite imagery",
            "true color",
            "卫星影像",
            "卫星",
            "影像",
            "真彩色",
        ),
        fetcher=_fetch_sentinel2,
        output_kind="tif",
    ),
}


def source_catalog_text() -> str:
    lines_cat = []
    for source in REGISTERED_SOURCES.values():
        lines_cat.append(
            f"- {source.source_id}: {source.description} "
            f"(output: {source.output_kind}; aliases: {', '.join(source.aliases)})"
        )
    return "\n".join(lines_cat)


def default_source_ids() -> list[str]:
    return [
        source.source_id
        for source in REGISTERED_SOURCES.values()
        if source.include_in_default_all
    ]


def normalize_source_ids(source_ids: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for source_id in source_ids:
        cleaned = source_id.strip()
        if not cleaned:
            continue
        matched = match_source_id(cleaned)
        if matched not in normalized:
            normalized.append(matched)
    return normalized


def match_source_id(value: str) -> str:
    lowered = value.strip().lower()
    for source in REGISTERED_SOURCES.values():
        if lowered == source.source_id.lower():
            return source.source_id
        if lowered in {alias.lower() for alias in source.aliases}:
            return source.source_id
    raise ValueError(f"Unknown data source: {value}")


def fetch_sources(
    source_ids: Iterable[str],
    *,
    bbox: BBox,
    query_year: int | None = None,
    output_dir: Path | None = None,
) -> dict[str, SourceOutput]:
    outputs: dict[str, SourceOutput] = {}
    for source_id in normalize_source_ids(source_ids):
        source = REGISTERED_SOURCES[source_id]
        output_path = output_dir / source.filename if output_dir is not None else None
        outputs[source.filename] = source.fetcher(bbox, query_year, output_path)
    return outputs


def save_source_outputs(
    outputs: dict[str, SourceOutput],
    *,
    output_dir: Path,
    include_combined: bool = True,
) -> dict[str, Path]:
    saved: dict[str, Path] = {}
    geojson_outputs: list[GeoJSON] = []
    for filename, output in outputs.items():
        if isinstance(output, Path):
            saved[filename] = output
            continue
        saved[filename] = save_geojson(output, output_dir / filename)
        geojson_outputs.append(output)

    if include_combined and geojson_outputs:
        combined = merge_feature_collections(geojson_outputs)
        saved["combined.geojson"] = save_geojson(combined, output_dir / "combined.geojson")

    return saved
