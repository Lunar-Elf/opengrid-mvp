from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from opengrid_mvp.clients.arcgis import fetch_arcgis_feature_layer
from opengrid_mvp.config import (
    DEFAULT_OUTPUT_DIR,
    NHS_FEATURE_LAYER_URL,
    NHS_SOURCE,
    NHS_YEAR_FIELD,
    NHS_YEAR_FILTER_KIND,
)
from opengrid_mvp.geojson_utils import save_geojson


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch National Highway System GeoJSON.")
    parser.add_argument("--year", type=int, default=None, help="Filter by NHS YEAR.")
    args = parser.parse_args()

    collection = fetch_arcgis_feature_layer(
        layer_url=NHS_FEATURE_LAYER_URL,
        source=NHS_SOURCE,
        query_year=args.year,
        year_field=NHS_YEAR_FIELD,
        year_filter_kind=NHS_YEAR_FILTER_KIND,
    )
    output = save_geojson(
        collection,
        DEFAULT_OUTPUT_DIR / "national_highway_system.geojson",
    )
    print(f"Saved {len(collection['features'])} features to {output}")


if __name__ == "__main__":
    main()
