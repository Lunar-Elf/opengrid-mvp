"""Shared configuration for the Central Park MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BBox:
    """A WGS84 bounding box in west/south/east/north order."""

    west: float
    south: float
    east: float
    north: float

    @property
    def center_lat(self) -> float:
        return (self.south + self.north) / 2

    @property
    def center_lon(self) -> float:
        return (self.west + self.east) / 2

    def as_arcgis_geometry(self) -> str:
        return f"{self.west},{self.south},{self.east},{self.north}"

    def as_dict(self) -> dict[str, float]:
        return {
            "west": self.west,
            "south": self.south,
            "east": self.east,
            "north": self.north,
        }


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "central_park"
AGENT_OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "queries"

CENTRAL_PARK_BBOX = BBox(
    west=-73.9819,
    south=40.7644,
    east=-73.9493,
    north=40.8007,
)

AFDC_SOURCE = {
    "source_id": "afdc_stations",
    "source_name": "AFDC / DOE Alternative Fuel Stations",
    "category": "electric_vehicle_charging_stations",
}

NHS_SOURCE = {
    "source_id": "national_highway_system",
    "source_name": "FHWA / BTS National Highway System",
    "category": "transportation_network",
}

NARN_SOURCE = {
    "source_id": "north_american_rail",
    "source_name": "FRA / BTS North American Rail Network",
    "category": "transportation_network",
}

HIFLD_SUBSTATIONS_SOURCE = {
    "source_id": "hifld_electric_substations",
    "source_name": "HIFLD Electric Substations",
    "category": "electric_substations",
}

USACE_NWN_SOURCE = {
    "source_id": "usace_national_waterway_network",
    "source_name": "USACE National Waterway Network",
    "category": "transportation_network",
}

EIA_POWER_PLANTS_SOURCE = {
    "source_id": "eia_power_plants",
    "source_name": "EIA Power Plant Attributes and Capacity (EIA-860M)",
    "category": "power_plants",
}

MODIS_LANDUSE_SOURCE = {
    "source_id": "modis_landuse",
    "source_name": "MODIS MCD12Q1 Land Cover Type",
    "category": "land_use_land_cover",
}

OSM_POWER_SOURCE = {
    "source_id": "osm_power",
    "source_name": "OpenStreetMap Power Infrastructure",
    "category": "power_infrastructure",
}

NHS_FEATURE_LAYER_URL = (
    "https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/"
    "NTAD_National_Highway_System/FeatureServer/0"
)
NHS_YEAR_FIELD = "YEAR"
NHS_YEAR_FILTER_KIND = "numeric"

NARN_FEATURE_LAYER_URL = (
    "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/"
    "NTAD_North_American_Rail_Network_Lines/FeatureServer/0"
)

HIFLD_SUBSTATIONS_FEATURE_LAYER_URL = (
    "https://services5.arcgis.com/caWDr9qv9f34KIAZ/arcgis/rest/services/"
    "ElectricSubstations/FeatureServer/9"
)
HIFLD_SUBSTATIONS_YEAR_FIELD = "SOURCEDATE"
HIFLD_SUBSTATIONS_YEAR_FILTER_KIND = "date"

USACE_NWN_FEATURE_LAYER_URL = (
    "https://services7.arcgis.com/n1YM8pTrFmm7L4hs/ArcGIS/rest/services/"
    "Waterway_Networks/FeatureServer/1"
)
USACE_NWN_YEAR_FIELD = "DATE_MOD"
USACE_NWN_YEAR_FILTER_KIND = "string_suffix"

EIA_OPERATING_GENERATOR_CAPACITY_URL = (
    "https://api.eia.gov/v2/electricity/operating-generator-capacity/data/"
)

EIA_STATE_FACETS = ("NY",)

MODIS_LANDUSE_COLLECTION_ID = "MODIS/061/MCD12Q1"
MODIS_LANDUSE_DEFAULT_BAND = "LC_Type1"
MODIS_LANDUSE_MIN_YEAR = 2001
MODIS_LANDUSE_MAX_YEAR = 2024
MODIS_LANDUSE_DEFAULT_YEAR = MODIS_LANDUSE_MAX_YEAR
MODIS_LANDUSE_SCALE_METERS = 500

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
OSM_POWER_TAG_PATTERN = "^(substation|line|minor_line|plant|generator)$"

# ---- Sentinel-2 Surface Reflectance (RGB) -----------------------------------

SENTINEL2_SOURCE = {
    "source_id": "sentinel2_rgb",
    "source_name": "Sentinel-2 MSI Surface Reflectance (RGB)",
    "category": "satellite_imagery",
}

SENTINEL2_COLLECTION_ID = "COPERNICUS/S2_SR_HARMONIZED"
SENTINEL2_RGB_BANDS = ("B4", "B3", "B2")  # Red, Green, Blue -- 10 m native
SENTINEL2_MIN_YEAR = 2015  # Sentinel-2A launch
SENTINEL2_MAX_YEAR = 2025  # Updated yearly
SENTINEL2_DEFAULT_YEAR = SENTINEL2_MAX_YEAR
SENTINEL2_SCALE_METERS = 10  # Native resolution of RGB bands
SENTINEL2_MAX_CLOUD_COVER = 30  # Percent, applied per-image before compositing
# ---- LLM Provider Configuration ---------------------------------------------

# Supported providers: "openai", "deepseek"
# DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
# DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"  # DeepSeek-V3
# OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
