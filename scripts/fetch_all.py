from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from opengrid_mvp.clients.afdc import fetch_afdc_stations
from opengrid_mvp.clients.arcgis import fetch_arcgis_feature_layer
from opengrid_mvp.clients.eia import fetch_eia_power_plants
from opengrid_mvp.clients.osm import fetch_osm_power_infrastructure
from opengrid_mvp.config import (
    DEFAULT_OUTPUT_DIR,
    HIFLD_SUBSTATIONS_FEATURE_LAYER_URL,
    HIFLD_SUBSTATIONS_SOURCE,
    HIFLD_SUBSTATIONS_YEAR_FIELD,
    HIFLD_SUBSTATIONS_YEAR_FILTER_KIND,
    NARN_FEATURE_LAYER_URL,
    NARN_SOURCE,
    NHS_FEATURE_LAYER_URL,
    NHS_SOURCE,
    NHS_YEAR_FIELD,
    NHS_YEAR_FILTER_KIND,
    USACE_NWN_FEATURE_LAYER_URL,
    USACE_NWN_SOURCE,
    USACE_NWN_YEAR_FIELD,
    USACE_NWN_YEAR_FILTER_KIND,
)
from opengrid_mvp.geojson_utils import merge_feature_collections, save_geojson


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch all Central Park API GeoJSON outputs.")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help=(
            "Filter year-capable sources. AFDC and NARN do not currently support "
            "year filtering."
        ),
    )
    args = parser.parse_args()

    datasets = {
        "afdc_stations.geojson": fetch_afdc_stations(),
        "national_highway_system.geojson": fetch_arcgis_feature_layer(
            layer_url=NHS_FEATURE_LAYER_URL,
            source=NHS_SOURCE,
            query_year=args.year,
            year_field=NHS_YEAR_FIELD,
            year_filter_kind=NHS_YEAR_FILTER_KIND,
        ),
        "north_american_rail.geojson": fetch_arcgis_feature_layer(
            layer_url=NARN_FEATURE_LAYER_URL,
            source=NARN_SOURCE,
        ),
        "hifld_electric_substations.geojson": fetch_arcgis_feature_layer(
            layer_url=HIFLD_SUBSTATIONS_FEATURE_LAYER_URL,
            source=HIFLD_SUBSTATIONS_SOURCE,
            query_year=args.year,
            year_field=HIFLD_SUBSTATIONS_YEAR_FIELD,
            year_filter_kind=HIFLD_SUBSTATIONS_YEAR_FILTER_KIND,
        ),
        "usace_national_waterway_network.geojson": fetch_arcgis_feature_layer(
            layer_url=USACE_NWN_FEATURE_LAYER_URL,
            source=USACE_NWN_SOURCE,
            query_year=args.year,
            year_field=USACE_NWN_YEAR_FIELD,
            year_filter_kind=USACE_NWN_YEAR_FILTER_KIND,
        ),
        "eia_power_plants.geojson": fetch_eia_power_plants(query_year=args.year),
        "osm_power_infrastructure.geojson": fetch_osm_power_infrastructure(),
    }

    for filename, collection in datasets.items():
        output = save_geojson(collection, DEFAULT_OUTPUT_DIR / filename)
        print(f"Saved {len(collection['features'])} features to {output}")

    combined = merge_feature_collections(datasets.values())
    output = save_geojson(combined, DEFAULT_OUTPUT_DIR / "combined.geojson")
    print(f"Saved {len(combined['features'])} combined features to {output}")


if __name__ == "__main__":
    main()
