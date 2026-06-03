from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opengrid_mvp.agent import (
    AgentRunResult,
    RequestPlan,
    default_query_output_dir,
    extract_radius_km,
    extract_query_year,
    fetch_sources_for_agent,
    format_plan_preview,
    heuristic_plan_request,
    save_run_summary,
    slugify,
)
from opengrid_mvp.geocoding import (
    PlaceAOI,
    amap_geocode,
    baidu_geocode,
    bbox_from_point_radius,
    geocode_with_map_providers,
    nominatim_geocode,
)


class AgentGeocodingTest(unittest.TestCase):
    def test_bbox_from_point_radius_contains_center(self) -> None:
        bbox = bbox_from_point_radius(
            latitude=40.7484,
            longitude=-73.9857,
            radius_km=3,
        )

        self.assertLess(bbox.west, -73.9857)
        self.assertGreater(bbox.east, -73.9857)
        self.assertLess(bbox.south, 40.7484)
        self.assertGreater(bbox.north, 40.7484)

    def test_amap_geocode_parses_success_response(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "status": "1",
            "geocodes": [
                {
                    "formatted_address": "北京市朝阳区",
                    "location": "116.481488,39.990464",
                }
            ],
        }

        with patch("opengrid_mvp.geocoding.requests.get", return_value=response):
            candidate = amap_geocode("北京朝阳区", api_key="test-key")

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.provider, "amap")
        self.assertIn("AMap", candidate.label)

    def test_baidu_geocode_parses_success_response(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "status": 0,
            "result": {
                "confidence": 80,
                "location": {"lng": 116.403963, "lat": 39.915119},
            },
        }

        with patch("opengrid_mvp.geocoding.requests.get", return_value=response):
            candidate = baidu_geocode("天安门", api_key="test-key")

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.provider, "baidu")
        self.assertIn("Baidu", candidate.label)

    def test_nominatim_geocode_parses_success_response(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {
                "display_name": "Times Square, New York, United States",
                "lat": "40.7570095",
                "lon": "-73.9859724",
            }
        ]

        with patch("opengrid_mvp.geocoding.requests.get", return_value=response):
            candidate = nominatim_geocode("USA, New York, Times Square")

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.provider, "nominatim")
        self.assertAlmostEqual(candidate.latitude, 40.7570095)
        self.assertAlmostEqual(candidate.longitude, -73.9859724)

    def test_global_places_use_nominatim_before_china_map_providers(self) -> None:
        candidate = Mock(provider="nominatim")

        with patch.dict(
            "os.environ",
            {"AMAP_API_KEY": "amap-key", "BAIDU_API_KEY": "baidu-key"},
            clear=False,
        ), patch("opengrid_mvp.geocoding.load_dotenv"), patch(
            "opengrid_mvp.geocoding.nominatim_geocode",
            return_value=candidate,
        ) as nominatim, patch(
            "opengrid_mvp.geocoding.amap_geocode",
        ) as amap, patch(
            "opengrid_mvp.geocoding.baidu_geocode",
        ) as baidu:
            result = geocode_with_map_providers("USA, New York, Bryant Park")

        self.assertEqual(result.provider, "nominatim")
        nominatim.assert_called_once()
        amap.assert_not_called()
        baidu.assert_not_called()

    def test_map_provider_falls_back_to_baidu(self) -> None:
        with patch.dict(
            "os.environ",
            {"AMAP_API_KEY": "amap-key", "BAIDU_API_KEY": "baidu-key"},
            clear=False,
        ), patch("opengrid_mvp.geocoding.load_dotenv"), patch(
            "opengrid_mvp.geocoding.amap_geocode",
            return_value=None,
        ), patch(
            "opengrid_mvp.geocoding.baidu_geocode",
            return_value=Mock(provider="baidu"),
        ) as baidu:
            candidate = geocode_with_map_providers("test")

        self.assertEqual(candidate.provider, "baidu")
        baidu.assert_called_once()

    def test_extract_radius_supports_chinese_kilometers(self) -> None:
        self.assertEqual(extract_radius_km("美国帝国大厦周围三公里有多少变电站的数据？"), 3.0)

    def test_extract_query_year(self) -> None:
        self.assertEqual(extract_query_year("fetch EIA data for 2020"), 2020)
        self.assertEqual(extract_query_year("2023年，USA，New York，Times Square"), 2023)
        self.assertIsNone(extract_query_year("fetch all years"))

    def test_heuristic_plan_selects_substations(self) -> None:
        plan = heuristic_plan_request("美国帝国大厦周围三公里有多少变电站的数据？")

        self.assertEqual(plan.radius_km, 3.0)
        self.assertIsNone(plan.query_year)
        self.assertEqual(plan.source_ids, ("hifld_electric_substations",))
        self.assertIn("美国帝国大厦", plan.place_query)

    def test_heuristic_plan_all_sources_for_all_data(self) -> None:
        plan = heuristic_plan_request("获取纽约中央公园周围三公里的所有数据")

        self.assertGreater(len(plan.source_ids), 1)
        self.assertIn("modis_landuse", plan.source_ids)
        self.assertEqual(plan.radius_km, 3.0)
        self.assertIn("纽约中央公园", plan.place_query)
        self.assertNotIn("所有", plan.place_query)

    def test_heuristic_plan_strips_chinese_year_marker(self) -> None:
        plan = heuristic_plan_request("2023年，USA， New York ，Times Square, 周围3km的所有数据")

        self.assertEqual(plan.query_year, 2023)
        self.assertEqual(plan.radius_km, 3.0)
        self.assertIn("modis_landuse", plan.source_ids)
        self.assertEqual(plan.place_query, "USA， New York ，Times Square")

    def test_heuristic_plan_selects_modis_landuse(self) -> None:
        plan = heuristic_plan_request("Central Park 2024 land cover")

        self.assertEqual(plan.source_ids, ("modis_landuse",))
        self.assertEqual(plan.query_year, 2024)

    def test_heuristic_plan_selects_osm_power(self) -> None:
        plan = heuristic_plan_request("Central Park OSM power infrastructure")

        self.assertEqual(plan.source_ids, ("osm_power",))

    def test_slugify_keeps_chinese_place_names(self) -> None:
        self.assertEqual(slugify("纽约 中央公园"), "纽约_中央公园")

    def test_default_query_output_dir_uses_queries_root(self) -> None:
        output_dir = default_query_output_dir("纽约 中央公园")

        self.assertIn("outputs", output_dir.parts)
        self.assertIn("queries", output_dir.parts)
        self.assertTrue(output_dir.name.endswith("_纽约_中央公园"))

    def test_format_plan_preview_can_skip_geocoding(self) -> None:
        plan = heuristic_plan_request("美国帝国大厦周围三公里有多少变电站的数据？")

        preview = format_plan_preview(plan)

        self.assertIn("Place query: 美国帝国大厦", preview)
        self.assertIn("hifld_electric_substations", preview)

    def test_save_run_summary_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = RequestPlan(
                place_query="Test Place",
                radius_km=3,
                source_ids=("hifld_electric_substations",),
                query_year=None,
                reasoning="test",
            )
            aoi = PlaceAOI(
                place_query="Test Place",
                label="Test Place",
                latitude=40,
                longitude=-73,
                radius_km=3,
                bbox=bbox_from_point_radius(latitude=40, longitude=-73, radius_km=3),
            )
            result = AgentRunResult(
                query="test query",
                plan=plan,
                aoi=aoi,
                output_dir=Path(temp_dir),
                saved_files={},
                feature_counts={"combined.geojson": 0},
                errors={},
            )

            summary_path = save_run_summary(result)

            self.assertTrue(summary_path.exists())
            self.assertIn("summary.json", result.saved_files)

    def test_agent_fetch_continues_when_one_source_fails(self) -> None:
        bbox = bbox_from_point_radius(latitude=40, longitude=-73, radius_km=3)
        successful_output = {"type": "FeatureCollection", "features": []}

        with patch("opengrid_mvp.agent.REGISTERED_SOURCES") as registry:
            registry.__getitem__.side_effect = lambda key: {
                "afdc_stations": Mock(
                    filename="afdc_stations.geojson",
                    fetcher=Mock(side_effect=RuntimeError("bad key")),
                ),
                "osm_power": Mock(
                    filename="osm_power_infrastructure.geojson",
                    fetcher=Mock(return_value=successful_output),
                ),
            }[key]

            outputs, errors = fetch_sources_for_agent(
                ("afdc_stations", "osm_power"),
                bbox=bbox,
                query_year=None,
                output_dir=Path("outputs"),
            )

        self.assertIn("afdc_stations", errors)
        self.assertEqual(outputs["osm_power_infrastructure.geojson"], successful_output)


if __name__ == "__main__":
    unittest.main()
