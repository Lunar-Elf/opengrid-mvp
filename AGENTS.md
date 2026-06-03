# AGENTS.md

## Project Overview

spatial-data-query-agent — an AI-assisted geospatial data retrieval system. A user
describes what they want in natural language (place + data category), and the
system plans, geocodes, fetches, and returns standardized GeoJSON outputs.

## Execution Flow

The pipeline runs in this fixed order inside `run_agent_request()` in
`src/opengrid_mvp/agent.py`:

```
User natural-language query
        │
        ▼
[1] plan_request()
    Extracts structured intent: place_query, radius_km, source_ids, query_year.
    Uses LangChain + OpenAI (or a deterministic keyword fallback).
        │
        ▼
[2] geocode_place(place_query, radius_km)
    Turns the place string into a WGS84 BBox.
    Providers: AMap → Baidu → Nominatim, with a local gazetteer for known
    global landmarks (Central Park, Times Square, Empire State Building).
    Handles GCJ-02 / BD-09 → WGS84 coordinate conversion.
        │
        ▼
[3] fetch_sources(source_ids, bbox, query_year)
    Dispatches to registered API / GEE clients.
    Failures in one source do not block others.
        │
        ▼
[4] save_source_outputs(outputs)
    Saves individual GeoJSON files, a combined.geojson, and a summary.json.
    Raster outputs (.tif) are saved but excluded from combined.geojson.
```

## Four Architecture Layers

| Layer | Module(s) | Status |
|-------|-----------|--------|
| **AI Planning** | `agent.py`, `source_registry.py` | Implemented (LangChain + heuristic fallback) |
| **Geocoding** | `geocoding.py` | Implemented (AMap, Baidu, Nominatim, local gazetteer) |
| **Data Fetching** | `clients/*.py` | Implemented (9 sources across 5 API protocols) |
| **Standardized Output** | `geojson_utils.py` | Implemented (GeoJSON FeatureCollection with metadata) |

## Registered Data Sources (9 total)

| Source ID | Category | Output | Year Filter | API |
|-----------|----------|--------|:-----------:|-----|
| `afdc_stations` | EV charging | `.geojson` | No | NREL REST |
| `national_highway_system` | Transport | `.geojson` | Yes (`YEAR`, numeric) | ArcGIS FS |
| `north_american_rail` | Transport | `.geojson` | No | ArcGIS FS |
| `hifld_electric_substations` | Substations | `.geojson` | Yes (`SOURCEDATE`, date) | ArcGIS FS |
| `usace_national_waterway_network` | Transport | `.geojson` | Yes (`DATE_MOD`, string suffix) | ArcGIS FS |
| `eia_power_plants` | Power plants | `.geojson` | Yes (`period` start/end) | EIA REST v2 |
| `osm_power` | Power infra | `.geojson` | No | Overpass API |
| `modis_landuse` | Land cover | `.tif` | Yes (year filter) | Google Earth Engine |
| `sentinel2_rgb` | Satellite imagery | `.tif` | Yes (year filter) | Google Earth Engine |

Sentinel-2 RGB specifics:
- Collection: `COPERNICUS/S2_SR_HARMONIZED`
- Bands: B4 (R), B3 (G), B2 (B) at 10 m native resolution
- Composite: June–September median, cloud-masked via QA60 band
- Default year: 2025; minimum: 2015

## Repository Structure

```
src/opengrid_mvp/
├── config.py              # BBox, source metadata, API URLs, GEE constants
├── geojson_utils.py       # Validation, BBOX filter, metadata injection, merge, save/load
├── geocoding.py           # AMap, Baidu, Nominatim, local gazetteer, coordinate transforms
├── agent.py               # LangChain planner, heuristic fallback, run_agent_request()
├── source_registry.py     # DatasetSource registry, alias matching, fetch_sources()
└── clients/
    ├── afdc.py            # NREL alt-fuel stations
    ├── arcgis.py          # Generic ArcGIS FeatureServer → GeoJSON (NHS, NARN, HIFLD, USACE)
    ├── eia.py             # EIA-860M operating generator capacity
    ├── gee.py             # MODIS land-use + Sentinel-2 RGB (Google Earth Engine)
    └── osm.py             # OpenStreetMap Overpass API → power infrastructure

scripts/
├── agent_query.py         # PRIMARY ENTRY POINT: natural language → plan → geocode → fetch → save
├── fetch_all.py           # Legacy: fetch all GeoJSON sources for fixed Central Park BBox
├── fetch_afdc.py          # Single-source thin wrappers
├── fetch_nhs.py
├── fetch_narn.py
├── fetch_hifld_substations.py
├── fetch_usace_nwn.py
├── fetch_eia_power_plants.py
├── fetch_osm_power.py
├── fetch_modis_landuse.py
├── fetch_sentinel2.py
└── _bootstrap.py          # Injects src/ into sys.path for direct script execution

tests/
├── test_geojson_utils.py
├── test_clients.py
└── test_agent_geocoding.py

outputs/
├── central_park/          # Legacy fetch_all.py output
└── queries/               # Agent query output (timestamped subdirectories)
```

## Key Commands

```powershell
# Install
pip install -r requirements.txt

# Primary entry point — natural language query
python scripts/agent_query.py "Central Park EV charging stations"
python scripts/agent_query.py "Central Park satellite imagery 2024"
python scripts/agent_query.py --plan-only "Times Square substations"
python scripts/agent_query.py --no-llm "帝国大厦周围3公里变电站 2023"
python scripts/agent_query.py --interactive
python scripts/agent_query.py --list-sources

# Legacy: fetch all GeoJSON sources for fixed Central Park BBox
python scripts/fetch_all.py
python scripts/fetch_all.py --year 2023

# Single-source fetchers
python scripts/fetch_sentinel2.py --year 2024
python scripts/fetch_modis_landuse.py --year 2023

# Tests
python -m unittest discover -s tests
```

## Development Rules

- Do not commit real API keys. Keep secrets in `.env` only.
- Update `.env.example` when adding new required env vars.
- Keep generated data, caches, and large geospatial files out of Git.
- When adding a new data source:
  1. Add source metadata and API/collection constants to `config.py`.
  2. Add or reuse a client under `src/opengrid_mvp/clients/`.
  3. Register it in `source_registry.py` with a `DatasetSource` entry (include
     Chinese + English aliases for agent discoverability).
  4. Add a thin CLI script under `scripts/`.
  5. Ensure GeoJSON outputs carry `source_id`, `source_name`, `category`,
     `retrieved_at`, and `bbox_query` in every feature.
  6. Raster outputs (`.tif`) should use `output_kind="tif"` and are saved
     alongside GeoJSON but excluded from `combined.geojson`.
  7. Add or update tests for error handling and transformation logic.
- When adding year-filter support to a source, wire it through `query_year`
  consistently — the agent and registry already pass it through.
- Architecture boundaries:
  - `agent.py` owns planning and orchestration.
  - `geocoding.py` owns place → BBox conversion.
  - `source_registry.py` owns the catalog and dispatch.
  - `clients/` own API-specific request and transformation logic.
  - `geojson_utils.py` owns output normalization.
- Treat data-fetching clients as deterministic tools. The agent selects tools;
  it must not construct raw API requests when a client already exists.
