from __future__ import annotations

import os
import sys
import unittest
from inspect import signature
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opengrid_mvp.clients.afdc import fetch_afdc_stations
from opengrid_mvp.clients.arcgis import build_where_clause, fetch_arcgis_feature_layer
from opengrid_mvp.clients.eia import fetch_eia_power_plants
from opengrid_mvp.clients.gee import resolve_modis_landuse_year
from opengrid_mvp.clients.osm import build_power_query, overpass_to_geojson
from opengrid_mvp.config import CENTRAL_PARK_BBOX, NHS_FEATURE_LAYER_URL, NHS_SOURCE
from opengrid_mvp.source_registry import REGISTERED_SOURCES


class ClientTest(unittest.TestCase):
    def test_afdc_missing_api_key_raises_clear_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch(
            "opengrid_mvp.clients.afdc.load_dotenv"
        ):
            with self.assertRaisesRegex(RuntimeError, "AFDC_API_KEY is missing"):
                fetch_afdc_stations()

    def test_arcgis_error_response_raises(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "error": {
                "message": "Invalid query",
                "details": ["Bad geometry"],
            }
        }

        with patch("opengrid_mvp.clients.arcgis.requests.get", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "Invalid query"):
                fetch_arcgis_feature_layer(
                    layer_url=NHS_FEATURE_LAYER_URL,
                    source=NHS_SOURCE,
                    bbox=CENTRAL_PARK_BBOX,
                )

    def test_eia_missing_api_key_raises_clear_error(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch(
            "opengrid_mvp.clients.eia.load_dotenv"
        ):
            with self.assertRaisesRegex(RuntimeError, "EIA_API_KEY is missing"):
                fetch_eia_power_plants()

    def test_eia_api_error_response_raises(self) -> None:
        first_response = Mock()
        first_response.raise_for_status.return_value = None
        first_response.json.return_value = {"error": "bad key"}

        with patch("opengrid_mvp.clients.eia.requests.get", return_value=first_response):
            with self.assertRaisesRegex(RuntimeError, "EIA query failed"):
                fetch_eia_power_plants(api_key="test-key")

    def test_registry_fetchers_accept_bbox_argument(self) -> None:
        for source in REGISTERED_SOURCES.values():
            with self.subTest(source=source.source_id):
                parameters = list(signature(source.fetcher).parameters)
                self.assertEqual(parameters, ["bbox", "query_year", "output_path"])

    def test_arcgis_year_where_clauses(self) -> None:
        self.assertEqual(
            build_where_clause(
                query_year=2020,
                year_field="YEAR",
                year_filter_kind="numeric",
            ),
            "YEAR = 2020",
        )
        self.assertEqual(
            build_where_clause(
                query_year=1997,
                year_field="DATE_MOD",
                year_filter_kind="string_suffix",
            ),
            "DATE_MOD LIKE '%1997'",
        )
        self.assertIn(
            "SOURCEDATE >= timestamp '2016-01-01 00:00:00'",
            build_where_clause(
                query_year=2016,
                year_field="SOURCEDATE",
                year_filter_kind="date",
            ),
        )

    def test_modis_year_defaults_and_bounds(self) -> None:
        self.assertEqual(resolve_modis_landuse_year(None), 2024)
        self.assertEqual(resolve_modis_landuse_year(2020), 2020)
        with self.assertRaises(ValueError):
            resolve_modis_landuse_year(1999)

    def test_osm_power_query_uses_bbox_and_power_tags(self) -> None:
        query = build_power_query(CENTRAL_PARK_BBOX)

        self.assertIn('["power"~', query)
        self.assertIn("40.7644,-73.9819,40.8007,-73.9493", query)

    def test_overpass_to_geojson_converts_node_and_way(self) -> None:
        collection = overpass_to_geojson(
            {
                "elements": [
                    {
                        "type": "node",
                        "id": 1,
                        "lat": 40.78,
                        "lon": -73.97,
                        "tags": {"power": "substation", "name": "Test"},
                    },
                    {
                        "type": "way",
                        "id": 2,
                        "tags": {"power": "line"},
                        "geometry": [
                            {"lat": 40.78, "lon": -73.97},
                            {"lat": 40.79, "lon": -73.96},
                        ],
                    },
                ]
            }
        )

        self.assertEqual(len(collection["features"]), 2)
        self.assertEqual(collection["features"][0]["geometry"]["type"], "Point")
        self.assertEqual(collection["features"][1]["geometry"]["type"], "LineString")


if __name__ == "__main__":
    unittest.main()
