# OpenGrid MVP

> AI-assisted geospatial data retrieval — describe a place and data category in natural language, get standardized GeoJSON outputs.

## What It Does

You type something like *"EV charging stations within 3 km of Central Park"* and the system:

1. **Plans** — extracts structured intent via LLM (or deterministic keyword fallback)
2. **Geocodes** — resolves place names to WGS84 bounding boxes using multiple providers
3. **Fetches** — dispatches requests to 9 registered API / Google Earth Engine clients
4. **Saves** — writes per-source GeoJSON, a combined GeoJSON, and a summary

## Architecture

| Layer | Module(s) | Description |
|-------|-----------|-------------|
| AI Planning | `agent.py`, `source_registry.py` | LangChain + heuristic fallback |
| Geocoding | `geocoding.py` | AMap → Baidu → Nominatim, GCJ-02/BD-09 → WGS84 |
| Data Fetching | `clients/*.py` | 9 sources across 5 API protocols |
| Output | `geojson_utils.py` | GeoJSON FeatureCollection with metadata |

## Registered Data Sources

| Source | Category | Format | Year Filter | API |
|--------|----------|:------:|:-----------:|-----|
| AFDC Stations | EV charging | GeoJSON | No | NREL REST |
| National Highway System | Transport | GeoJSON | Yes | ArcGIS FS |
| North American Rail | Transport | GeoJSON | No | ArcGIS FS |
| HIFLD Substations | Substations | GeoJSON | Yes | ArcGIS FS |
| USACE Waterway Network | Transport | GeoJSON | Yes | ArcGIS FS |
| EIA Power Plants | Power plants | GeoJSON | Yes | EIA REST v2 |
| OSM Power Infrastructure | Power | GeoJSON | No | Overpass API |
| MODIS Land Use | Land cover | GeoTIFF | Yes | Google Earth Engine |
| Sentinel-2 RGB | Satellite imagery | GeoTIFF | Yes | Google Earth Engine |

## Quick Start

```powershell
# Clone & install
git clone https://github.com/Lunar-Elf/opengrid-mvp.git
cd opengrid-mvp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure API keys
copy .env.example .env
# Fill in your keys in .env
```

### Required Environment Variables

```text
# Core
OPENAI_API_KEY=your_openai_key_here        # LLM planner (optional; falls back to keywords)
DEEPSEEK_API_KEY=your_deepseek_key_here    # Alternative LLM provider
LLM_PROVIDER=deepseek                      # or openai

# Geocoding
AMAP_API_KEY=your_amap_key_here            # AMap (Gaode) geocoding
BAIDU_API_KEY=your_baidu_key_here          # Baidu geocoding

# Data Sources
AFDC_API_KEY=your_key_here                 # NREL alt-fuel stations
EIA_API_KEY=your_key_here                  # EIA power plants
GOOGLE_CLOUD_PROJECT=your_project_id       # Google Earth Engine (MODIS, Sentinel-2)
```

## Usage

### Natural Language Query (primary entry point)

```powershell
python scripts/agent_query.py "Central Park EV charging stations"
python scripts/agent_query.py "Times Square substations within 3 km"
python scripts/agent_query.py "Central Park satellite imagery 2024"

# Plan only — see what the agent understood without fetching
python scripts/agent_query.py --plan-only "Times Square substations"

# Interactive mode — keep asking queries in a session
python scripts/agent_query.py --interactive

# Chat interface
python scripts/chat_query.py

# Deterministic keyword fallback (no LLM needed)
python scripts/agent_query.py --no-llm "帝国大厦周围3公里变电站 2023"

# List all registered sources
python scripts/agent_query.py --list-sources
```

### Single-Source Fetching

```powershell
python scripts/fetch_afdc.py
python scripts/fetch_nhs.py --year 2023
python scripts/fetch_sentinel2.py --year 2024
python scripts/fetch_modis_landuse.py --year 2023
python scripts/fetch_eia_power_plants.py --year 2020
python scripts/fetch_osm_power.py
python scripts/fetch_all.py --year 2023
```

### Output Structure

```
outputs/
├── central_park/           # Legacy fetch_all.py output
└── queries/
    └── 20260603_120000_central_park/
        ├── afdc_stations.geojson
        ├── national_highway_system.geojson
        ├── ...              # one file per source
        ├── combined.geojson  # all vector features merged
        └── summary.json      # metadata about the run
```

## Geocoding

The system tries providers in order: **AMap → Baidu → Nominatim**. A local gazetteer handles well-known global landmarks. Chinese coordinate systems (GCJ-02, BD-09) are automatically converted to WGS84.

## Tests

```powershell
python -m unittest discover -s tests
```

## Repository Structure

```
src/opengrid_mvp/
├── agent.py               # LLM planner & main orchestration
├── source_registry.py     # Data source catalog & dispatch
├── geocoding.py           # Multi-provider geocoding & coordinate transforms
├── geojson_utils.py       # Validation, merging, metadata injection
├── config.py              # Shared BBox, API URLs, GEE constants
└── clients/
    ├── afdc.py            # NREL alt-fuel stations
    ├── arcgis.py          # ArcGIS FeatureServer → GeoJSON
    ├── eia.py             # EIA power plant data
    ├── gee.py             # MODIS land use + Sentinel-2 RGB
    └── osm.py             # OpenStreetMap Overpass API
```

## Development

- Never commit `.env` — secrets stay local
- Update `.env.example` when adding new environment variables
- Generated outputs, caches, and large geospatial files stay out of Git
- New data sources follow the [AGENTS.md](AGENTS.md) checklist

## License

MIT
