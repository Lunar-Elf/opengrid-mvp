# OpenGridWorks API GeoJSON MVP

This repository starts with a small Central Park data-fetching MVP. It fetches
API-based datasets and normalizes them into GeoJSON FeatureCollections.

It now also includes an early natural-language agent layer:

- geocoding: place/address text -> point + radius BBOX
- LangChain planning: user request -> relevant registered data sources
- deterministic fallback: keyword planning when `OPENAI_API_KEY` is not set

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set:

```text
AFDC_API_KEY=your_real_key_here
EIA_API_KEY=your_real_key_here
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini
BAIDU_API_KEY=your_baidu_key_here
AMAP_API_KEY=your_amap_key_here
GOOGLE_CLOUD_PROJECT=your_google_cloud_project_id_optional
```

Do not commit `.env`.

The geocoding layer uses OpenStreetMap Nominatim first for clearly global or
US place requests, then AMap and Baidu for China-oriented requests. Returned
coordinates are normalized to WGS84 before building the query BBOX.

## Fetch Central Park Data

```powershell
python scripts/fetch_afdc.py
python scripts/fetch_nhs.py
python scripts/fetch_narn.py
python scripts/fetch_hifld_substations.py
python scripts/fetch_usace_nwn.py
python scripts/fetch_eia_power_plants.py
python scripts/fetch_osm_power.py
python scripts/fetch_modis_landuse.py --year 2024
python scripts/fetch_all.py
```

Year-capable sources can be filtered with `--year`:

```powershell
python scripts/fetch_nhs.py --year 2020
python scripts/fetch_hifld_substations.py --year 2016
python scripts/fetch_usace_nwn.py --year 1997
python scripts/fetch_eia_power_plants.py --year 2020
python scripts/fetch_all.py --year 2020
```

If `--year` is omitted, year-capable sources use all available years. AFDC and
NARN do not currently expose a reliable year filter in the MVP.

MODIS land-use uses Google Earth Engine and writes a GeoTIFF instead of
GeoJSON. Authenticate Earth Engine before running it:

```powershell
D:/appdata2/anaconda3/envs/WRI_env/python.exe scripts/authenticate_gee.py --mode localhost
python scripts/fetch_modis_landuse.py --year 2024
```

If `--year` is omitted for MODIS, it uses the latest configured MCD12Q1 year.
If Earth Engine asks for a Google Cloud project, create/select one in Google
Cloud and put its project ID in `.env` as `GOOGLE_CLOUD_PROJECT=...`.

Outputs are written to `outputs/central_park/`:

- `afdc_stations.geojson`
- `national_highway_system.geojson`
- `north_american_rail.geojson`
- `hifld_electric_substations.geojson`
- `usace_national_waterway_network.geojson`
- `eia_power_plants.geojson`
- `osm_power_infrastructure.geojson`
- `modis_landuse.tif`
- `combined.geojson`

The output directory is ignored by Git because these files are generated data.

## Natural-Language Agent Query / 自然语言查询

推荐在 `WRI_env` 里运行：

```powershell
conda activate WRI_env
Set-Location "E:\实习\WRI\5.AI数据集"
python -m pip install --no-user -r requirements.txt
```

一次性查询时，直接改命令最后引号里的“目标话语”：

```powershell
python scripts/agent_query.py "获取纽约中央公园周围三公里的所有数据"
python scripts/agent_query.py "美国帝国大厦周围三公里有多少变电站的数据？"
```

进入交互模式后，可以连续输入不同目标话语：

```powershell
python scripts/chat_query.py
```

或者：

```powershell
python scripts/agent_query.py --interactive
```

只查看 agent 理解结果，不请求数据源：

```powershell
python scripts/agent_query.py "美国帝国大厦周围三公里有多少变电站的数据？" --plan-only
```

如果只想看地点、半径和数据源规划，不调用地图 API，可以跳过地理编码预览：

```powershell
python scripts/agent_query.py "美国帝国大厦周围三公里有多少变电站的数据？" --plan-only --no-geocode-preview
```

列出目前注册的数据源：

```powershell
python scripts/agent_query.py --list-sources
```

The runner plans the source list with LangChain when `OPENAI_API_KEY` is set.
Without an OpenAI key, it falls back to deterministic keyword matching so local
development and tests still work.

To force the deterministic fallback:

```powershell
python scripts/agent_query.py "美国帝国大厦周围三公里有多少变电站的数据？" --no-llm
```

Agent outputs are written under `outputs/queries/<timestamp>_<place_slug>/`
unless `--output-dir` is provided. Each run writes:

- one GeoJSON per selected source
- one GeoTIFF for selected raster sources, such as MODIS land-use
- `combined.geojson`
- `summary.json`

## Tests

```powershell
python -m unittest discover -s tests
```
