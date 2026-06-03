# OpenGrid MVP

> AI-assisted geospatial data retrieval — natural language in, GeoJSON out.

Describe a place and data category in plain language, and the system plans, geocodes, fetches, and returns standardized geospatial outputs.

## Pipeline

```
User Query (English / 中文)
        │
        ▼
[1] Plan — LLM extracts structured intent: place, radius, sources, year
        │
        ▼
[2] Geocode — Google Maps → AMap / Baidu (for addresses inside China)
        │
        ▼
[3] Fetch — dispatch to API / Google Earth Engine clients
        │
        ▼
[4] Save — per-source GeoJSON, combined.geojson, summary.json
```

## Architecture

| Layer | Module | Description |
|-------|--------|-------------|
| AI Planning | `agent.py` | LangChain with OpenAI or DeepSeek; deterministic keyword fallback |
| Source Catalog | `source_registry.py` | 9 registered sources with English + Chinese aliases |
| Geocoding | `geocoding.py` | Google → AMap → Baidu; GCJ-02 / BD-09 → WGS84 conversion |
| Data Fetching | `clients/*.py` | 5 client modules covering REST, ArcGIS FS, EIA, Overpass, GEE |
| Output | `geojson_utils.py` | Validation, BBox filtering, merging, metadata injection |

## Registered Data Sources (9)

| Source ID | Category | Format | Year Filter | API |
|-----------|----------|:------:|:-----------:|-----|
| `afdc_stations` | EV charging | GeoJSON | — | NREL REST |
| `national_highway_system` | Transport | GeoJSON | ✅ (`YEAR`) | ArcGIS FeatureServer |
| `north_american_rail` | Transport | GeoJSON | — | ArcGIS FeatureServer |
| `hifld_electric_substations` | Substations | GeoJSON | ✅ (`SOURCEDATE`) | ArcGIS FeatureServer |
| `usace_national_waterway_network` | Transport | GeoJSON | ✅ (`DATE_MOD`) | ArcGIS FeatureServer |
| `eia_power_plants` | Power plants | GeoJSON | ✅ (`period`) | EIA REST v2 |
| `osm_power` | Power infrastructure | GeoJSON | — | Overpass API |
| `modis_landuse` | Land cover | GeoTIFF | ✅ (year of MCD12Q1) | Google Earth Engine |
| `sentinel2_rgb` | Satellite imagery | GeoTIFF | ✅ (June–Sep median) | Google Earth Engine |

Sentinel-2 RGB uses `COPERNICUS/S2_SR_HARMONIZED` with bands B4 (R), B3 (G), B2 (B) at 10 m resolution, cloud-masked via QA60.

## Quick Start

```powershell
git clone https://github.com/Lunar-Elf/opengrid-mvp.git
cd opengrid-mvp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure API keys
copy .env.example .env
# Edit .env with your keys
```

### Environment Variables

```text
# LLM Planner (optional; falls back to keyword matching if keys are missing)
LLM_PROVIDER=deepseek          # or openai
OPENAI_API_KEY=your_key        # for OpenAI
DEEPSEEK_API_KEY=your_key      # for DeepSeek

# Geocoding
GOOGLE_GEOCODE_API_KEY=your_key    # Primary geocoder for all addresses
AMAP_API_KEY=your_key              # Override for China addresses
BAIDU_API_KEY=your_key             # Fallback for China addresses

# Data Sources
AFDC_API_KEY=your_key              # NREL alt-fuel stations
EIA_API_KEY=your_key               # EIA power plants
GOOGLE_CLOUD_PROJECT=your_id       # Google Earth Engine
```

## Usage

### Natural Language Query

```powershell
# English
python scripts/agent_query.py "EV charging stations within 3 km of Central Park"
python scripts/agent_query.py "satellite imagery of Times Square 2024"
python scripts/agent_query.py "power plants near Empire State Building"

# 中文
python scripts/agent_query.py "帝国大厦周围3公里变电站 2023"
python scripts/agent_query.py "中央公园电动汽车充电站"
python scripts/agent_query.py "获取纽约中央公园周围三公里的所有数据"

# Plan only — see what was understood without fetching
python scripts/agent_query.py --plan-only "Times Square substations"
python scripts/agent_query.py --plan-only --no-geocode-preview "Times Square substations"

# Deterministic keyword fallback (no LLM)
python scripts/agent_query.py --no-llm "帝国大厦周围3公里变电站 2023"

# Interactive mode
python scripts/agent_query.py --interactive

# List all registered sources
python scripts/agent_query.py --list-sources
```

### Single-Source Fetching

```powershell
python scripts/fetch_afdc.py
python scripts/fetch_nhs.py --year 2023
python scripts/fetch_hifld_substations.py --year 2020
python scripts/fetch_usace_nwn.py --year 2020
python scripts/fetch_eia_power_plants.py --year 2020
python scripts/fetch_osm_power.py
python scripts/fetch_sentinel2.py --year 2024
python scripts/fetch_modis_landuse.py --year 2023
python scripts/fetch_all.py --year 2023
```

### Output Structure

```
outputs/
└── queries/
    └── 20260603_120000_central_park/
        ├── afdc_stations.geojson
        ├── national_highway_system.geojson
        ├── ...                          # one per source
        ├── combined.geojson             # all vector features merged
        ├── summary.json                 # run metadata
        └── modis_landuse.tif            # raster outputs excluded from combined
```

## Geocoding

The geocoding pipeline resolves place names to WGS84 bounding boxes:

1. **Google Maps** — primary geocoder, best global coverage
2. **AMap (高德)** — used when Google result falls inside China, for more accurate local coordinates
3. **Baidu (百度)** — fallback if AMap is unavailable or fails

Chinese coordinate systems (GCJ-02 from AMap, BD-09 from Baidu) are automatically converted to WGS84. No Nominatim is used.

## Tests

```powershell
python -m unittest discover -s tests
```

## Repository Structure

```
src/opengrid_mvp/
├── agent.py               # LLM planner, heuristic fallback, run_agent_request()
├── source_registry.py     # DatasetSource catalog, alias matching, dispatch
├── geocoding.py           # Google / AMap / Baidu geocoding, coordinate transforms
├── geojson_utils.py       # Validation, BBox filter, metadata, merge, save
├── config.py              # BBox, source metadata, API URLs, GEE constants
└── clients/
    ├── afdc.py            # NREL alternative fuel stations
    ├── arcgis.py          # ArcGIS FeatureServer → GeoJSON
    ├── eia.py             # EIA-860M operating generator capacity
    ├── gee.py             # MODIS land use + Sentinel-2 RGB
    └── osm.py             # OpenStreetMap Overpass → power infrastructure

scripts/
├── agent_query.py         # PRIMARY ENTRY POINT
├── fetch_all.py           # Fetch all vector sources for a fixed BBox
├── fetch_*.py             # Single-source thin wrappers (9 scripts)
└── _bootstrap.py          # sys.path injection for direct script execution

tests/
├── test_geojson_utils.py
├── test_clients.py
└── test_agent_geocoding.py
```

## License

MIT
