from __future__ import annotations

import _bootstrap  # noqa: F401

from opengrid_mvp.clients.afdc import fetch_afdc_stations
from opengrid_mvp.config import DEFAULT_OUTPUT_DIR
from opengrid_mvp.geojson_utils import save_geojson


def main() -> None:
    collection = fetch_afdc_stations()
    output = save_geojson(collection, DEFAULT_OUTPUT_DIR / "afdc_stations.geojson")
    print(f"Saved {len(collection['features'])} features to {output}")


if __name__ == "__main__":
    main()
