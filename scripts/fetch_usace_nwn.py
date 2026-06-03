from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from opengrid_mvp.clients.arcgis import fetch_arcgis_feature_layer
from opengrid_mvp.config import (
    DEFAULT_OUTPUT_DIR,
    USACE_NWN_FEATURE_LAYER_URL,
    USACE_NWN_SOURCE,
    USACE_NWN_YEAR_FIELD,
    USACE_NWN_YEAR_FILTER_KIND,
)
from opengrid_mvp.geojson_utils import save_geojson


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch USACE National Waterway Network GeoJSON.")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Filter by USACE DATE_MOD year.",
    )
    args = parser.parse_args()

    collection = fetch_arcgis_feature_layer(
        layer_url=USACE_NWN_FEATURE_LAYER_URL,
        source=USACE_NWN_SOURCE,
        query_year=args.year,
        year_field=USACE_NWN_YEAR_FIELD,
        year_filter_kind=USACE_NWN_YEAR_FILTER_KIND,
    )
    output = save_geojson(
        collection,
        DEFAULT_OUTPUT_DIR / "usace_national_waterway_network.geojson",
    )
    print(f"Saved {len(collection['features'])} features to {output}")


if __name__ == "__main__":
    main()
