from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opengrid_mvp.config import AFDC_SOURCE, CENTRAL_PARK_BBOX
from opengrid_mvp.geojson_utils import (
    add_source_metadata,
    empty_feature_collection,
    filter_features_to_bbox,
    merge_feature_collections,
    save_geojson,
)
from opengrid_mvp.source_registry import save_source_outputs


class GeoJSONUtilsTest(unittest.TestCase):
    def test_bbox_point_filter(self) -> None:
        collection = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "inside"},
                    "geometry": {"type": "Point", "coordinates": [-73.97, 40.78]},
                },
                {
                    "type": "Feature",
                    "properties": {"name": "outside"},
                    "geometry": {"type": "Point", "coordinates": [-74.1, 40.78]},
                },
            ],
        }

        filtered = filter_features_to_bbox(collection, CENTRAL_PARK_BBOX)

        self.assertEqual(len(filtered["features"]), 1)
        self.assertEqual(filtered["features"][0]["properties"]["name"], "inside")

    def test_empty_feature_collection_can_be_saved(self) -> None:
        output = ROOT / "tmp" / "test_empty.geojson"
        saved = save_geojson(empty_feature_collection(), output)

        self.assertTrue(saved.exists())
        self.assertEqual(json.loads(saved.read_text(encoding="utf-8"))["features"], [])

    def test_merge_preserves_source_id(self) -> None:
        collection = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {"type": "Point", "coordinates": [-73.97, 40.78]},
                }
            ],
        }
        normalized = add_source_metadata(
            collection,
            source=AFDC_SOURCE,
            bbox=CENTRAL_PARK_BBOX,
            retrieved_at="2026-05-17T00:00:00+00:00",
        )

        merged = merge_feature_collections([normalized])

        self.assertEqual(
            merged["features"][0]["properties"]["source_id"],
            "afdc_stations",
        )

    def test_invalid_feature_collection_raises(self) -> None:
        with self.assertRaises(ValueError):
            save_geojson({"type": "Feature", "features": []}, ROOT / "tmp" / "bad.geojson")

    def test_save_source_outputs_preserves_raster_path(self) -> None:
        raster_path = ROOT / "tmp" / "mock_landuse.tif"
        raster_path.parent.mkdir(parents=True, exist_ok=True)
        raster_path.write_bytes(b"mock tif")

        saved = save_source_outputs(
            {"modis_landuse.tif": raster_path},
            output_dir=ROOT / "tmp",
        )

        self.assertEqual(saved["modis_landuse.tif"], raster_path)
        self.assertNotIn("combined.geojson", saved)


if __name__ == "__main__":
    unittest.main()
