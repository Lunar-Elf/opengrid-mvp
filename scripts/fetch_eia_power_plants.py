from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from opengrid_mvp.clients.eia import fetch_eia_power_plants
from opengrid_mvp.config import DEFAULT_OUTPUT_DIR
from opengrid_mvp.geojson_utils import save_geojson


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch EIA-860M power plant GeoJSON.")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Filter by EIA monthly period year. Omit to fetch all years.",
    )
    args = parser.parse_args()

    collection = fetch_eia_power_plants(query_year=args.year)
    output = save_geojson(collection, DEFAULT_OUTPUT_DIR / "eia_power_plants.geojson")
    print(f"Saved {len(collection['features'])} features to {output}")


if __name__ == "__main__":
    main()
