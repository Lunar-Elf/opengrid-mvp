from __future__ import annotations

import _bootstrap  # noqa: F401

from opengrid_mvp.clients.arcgis import fetch_arcgis_feature_layer
from opengrid_mvp.config import DEFAULT_OUTPUT_DIR, NARN_FEATURE_LAYER_URL, NARN_SOURCE
from opengrid_mvp.geojson_utils import save_geojson


def main() -> None:
    collection = fetch_arcgis_feature_layer(
        layer_url=NARN_FEATURE_LAYER_URL,
        source=NARN_SOURCE,
    )
    output = save_geojson(collection, DEFAULT_OUTPUT_DIR / "north_american_rail.geojson")
    print(f"Saved {len(collection['features'])} features to {output}")


if __name__ == "__main__":
    main()
