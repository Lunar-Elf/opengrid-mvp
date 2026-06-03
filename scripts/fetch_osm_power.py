from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from opengrid_mvp.clients.osm import fetch_osm_power_infrastructure
from opengrid_mvp.config import DEFAULT_OUTPUT_DIR
from opengrid_mvp.geojson_utils import save_geojson


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch OpenStreetMap power infrastructure GeoJSON via Overpass."
    )
    parser.parse_args()

    collection = fetch_osm_power_infrastructure()
    output = save_geojson(collection, DEFAULT_OUTPUT_DIR / "osm_power_infrastructure.geojson")
    print(f"Saved {len(collection['features'])} features to {output}")


if __name__ == "__main__":
    main()
