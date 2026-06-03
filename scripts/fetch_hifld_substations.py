from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from opengrid_mvp.clients.arcgis import fetch_arcgis_feature_layer
from opengrid_mvp.config import (
    DEFAULT_OUTPUT_DIR,
    HIFLD_SUBSTATIONS_FEATURE_LAYER_URL,
    HIFLD_SUBSTATIONS_SOURCE,
    HIFLD_SUBSTATIONS_YEAR_FIELD,
    HIFLD_SUBSTATIONS_YEAR_FILTER_KIND,
)
from opengrid_mvp.geojson_utils import save_geojson


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch HIFLD electric substations GeoJSON.")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Filter by HIFLD SOURCEDATE year.",
    )
    args = parser.parse_args()

    collection = fetch_arcgis_feature_layer(
        layer_url=HIFLD_SUBSTATIONS_FEATURE_LAYER_URL,
        source=HIFLD_SUBSTATIONS_SOURCE,
        query_year=args.year,
        year_field=HIFLD_SUBSTATIONS_YEAR_FIELD,
        year_filter_kind=HIFLD_SUBSTATIONS_YEAR_FILTER_KIND,
    )
    output = save_geojson(
        collection,
        DEFAULT_OUTPUT_DIR / "hifld_electric_substations.geojson",
    )
    print(f"Saved {len(collection['features'])} features to {output}")


if __name__ == "__main__":
    main()
