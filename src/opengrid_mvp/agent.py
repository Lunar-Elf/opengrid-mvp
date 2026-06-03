"""LangChain planning layer for geospatial data requests."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from opengrid_mvp.config import AGENT_OUTPUT_ROOT, BBox, PROJECT_ROOT
from opengrid_mvp.geocoding import DEFAULT_RADIUS_KM, PlaceAOI, geocode_place
from opengrid_mvp.geojson_utils import merge_feature_collections
from opengrid_mvp.source_registry import (
    REGISTERED_SOURCES,
    SourceOutput,
    default_source_ids,
    normalize_source_ids,
    save_source_outputs,
    source_catalog_text,
)


@dataclass(frozen=True)
class RequestPlan:
    place_query: str
    radius_km: float
    source_ids: tuple[str, ...]
    query_year: int | None
    reasoning: str

    @property
    def fetch_all(self) -> bool:
        return set(self.source_ids) == set(default_source_ids())

    def as_dict(self) -> dict[str, Any]:
        return {
            "place_query": self.place_query,
            "radius_km": self.radius_km,
            "source_ids": list(self.source_ids),
            "query_year": self.query_year,
            "reasoning": self.reasoning,
            "fetch_all": self.fetch_all,
        }


@dataclass(frozen=True)
class AgentRunResult:
    query: str
    plan: RequestPlan
    aoi: PlaceAOI
    output_dir: Path
    saved_files: dict[str, Path]
    feature_counts: dict[str, int]
    errors: dict[str, str]

    def as_summary_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "plan": self.plan.as_dict(),
            "aoi": self.aoi.as_dict(),
            "output_dir": str(self.output_dir),
            "saved_files": {
                filename: str(path)
                for filename, path in self.saved_files.items()
            },
            "feature_counts": self.feature_counts,
            "errors": self.errors,
        }


def _resolve_llm_provider() -> tuple[str, str, str | None, str | None]:
    """Return (provider, api_key, model, base_url) from environment."""
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        model_env = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        base_url = "https://api.deepseek.com/v1"
    else:
        provider = "openai"
        api_key = os.getenv("OPENAI_API_KEY", "")
        model_env = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        base_url = None  # use langchain-openai default
    return provider, api_key, model_env, base_url


def plan_request(
    query: str,
    *,
    model: str | None = None,
    use_llm: bool = True,
) -> RequestPlan:
    """Plan place, radius, and data sources for a user request."""

    load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")
    if use_llm:
        _provider, api_key, _model_env, _base_url = _resolve_llm_provider()
        if api_key:
            try:
                return _plan_request_with_langchain(query, model=model)
            except Exception:
                # Keep the CLI usable during early MVP work even if model setup fails.
                return heuristic_plan_request(query)
    return heuristic_plan_request(query)


def run_agent_request(
    query: str,
    *,
    output_dir: Path | None = None,
    model: str | None = None,
    use_llm: bool = True,
) -> AgentRunResult:
    """Plan, geocode, fetch selected sources, and save GeoJSON outputs."""

    load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")
    plan = plan_request(query, model=model, use_llm=use_llm)
    aoi = geocode_place(plan.place_query, radius_km=plan.radius_km)
    resolved_output_dir = output_dir or default_query_output_dir(plan.place_query)
    outputs, errors = fetch_sources_for_agent(
        plan.source_ids,
        bbox=aoi.bbox,
        query_year=plan.query_year,
        output_dir=resolved_output_dir,
    )
    saved_files = save_source_outputs(outputs, output_dir=resolved_output_dir)

    geojson_outputs = _geojson_outputs(outputs)
    if "combined.geojson" not in outputs and geojson_outputs:
        combined = merge_feature_collections(geojson_outputs.values())
        feature_counts = {
            filename: len(collection["features"])
            for filename, collection in geojson_outputs.items()
        }
        feature_counts["combined.geojson"] = len(combined["features"])
    else:
        feature_counts = {
            filename: len(collection["features"])
            for filename, collection in geojson_outputs.items()
        }

    result = AgentRunResult(
        query=query,
        plan=plan,
        aoi=aoi,
        output_dir=resolved_output_dir,
        saved_files=saved_files,
        feature_counts=feature_counts,
        errors=errors,
    )
    save_run_summary(result)
    return result


def preview_agent_request(
    query: str,
    *,
    model: str | None = None,
    use_llm: bool = True,
) -> tuple[RequestPlan, PlaceAOI]:
    """Plan and geocode a request without fetching dataset APIs."""

    plan = plan_request(query, model=model, use_llm=use_llm)
    aoi = geocode_place(plan.place_query, radius_km=plan.radius_km)
    return plan, aoi


def save_run_summary(result: AgentRunResult) -> Path:
    path = result.output_dir / "summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    result.saved_files["summary.json"] = path
    path.write_text(
        json.dumps(result.as_summary_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def default_query_output_dir(place_query: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return AGENT_OUTPUT_ROOT / f"{timestamp}_{slugify(place_query)}"


def format_plan_preview(plan: RequestPlan, aoi: PlaceAOI | None = None) -> str:
    lines = [
        f"Place query: {plan.place_query}",
        f"Radius km: {plan.radius_km}",
        f"Sources: {', '.join(plan.source_ids)}",
        f"Query year: {plan.query_year if plan.query_year is not None else 'all years'}",
        f"Reasoning: {plan.reasoning}",
    ]
    if aoi is not None:
        provider_line = f"Geocoded by: {aoi.provider}"
        if aoi.location_type:
            provider_line += f" (location_type: {aoi.location_type})"
        lines.extend(
            [
                f"Geocoded label: {aoi.label}",
                provider_line,
                f"BBOX: {aoi.bbox.as_dict()}",
            ]
        )
    return "\n".join(lines)


def format_run_result(result: AgentRunResult) -> str:
    provider_line = f"Geocoded by: {result.aoi.provider}"
    if result.aoi.location_type:
        provider_line += f" (location_type: {result.aoi.location_type})"
    lines = [
        f"Place: {result.aoi.label}",
        provider_line,
        f"BBOX: {result.aoi.bbox.as_dict()}",
        f"Sources: {', '.join(result.plan.source_ids)}",
        f"Query year: {result.plan.query_year if result.plan.query_year is not None else 'all years'}",
        f"Output directory: {result.output_dir}",
    ]
    for filename, path in result.saved_files.items():
        if filename == "summary.json":
            lines.append(f"Saved summary to {path}")
            continue
        if filename.lower().endswith((".tif", ".tiff")):
            lines.append(f"Saved raster to {path}")
            continue
        count = result.feature_counts.get(filename, 0)
        lines.append(f"Saved {count} features to {path}")
    for source_id, message in result.errors.items():
        lines.append(f"Failed {source_id}: {message}")
    return "\n".join(lines)


def fetch_sources_for_agent(
    source_ids: tuple[str, ...],
    *,
    bbox: BBox,
    query_year: int | None,
    output_dir: Path,
) -> tuple[dict[str, SourceOutput], dict[str, str]]:
    outputs: dict[str, SourceOutput] = {}
    errors: dict[str, str] = {}
    for source_id in normalize_source_ids(source_ids):
        source = REGISTERED_SOURCES[source_id]
        output_path = output_dir / source.filename
        try:
            outputs[source.filename] = source.fetcher(bbox, query_year, output_path)
        except Exception as exc:
            errors[source_id] = str(exc)
    return outputs, errors


def _plan_request_with_langchain(query: str, *, model: str | None) -> RequestPlan:
    from pydantic import BaseModel, Field

    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    provider, api_key, model_env, base_url = _resolve_llm_provider()
    resolved_model = model or model_env

    llm_kwargs: dict = {
        "model": resolved_model,
        "temperature": 0,
        "api_key": api_key,
    }
    if base_url is not None:
        llm_kwargs["base_url"] = base_url
    llm = ChatOpenAI(**llm_kwargs)

    # DeepSeek does not support structured output (response_format).
    # Fall back to prompting for JSON and parsing manually.
    _USE_STRUCTURED = provider == "openai"

    if _USE_STRUCTURED:
        class PlanSchema(BaseModel):
            place_query: str = Field(
                description="The semantic place/address to geocode, without radius words."
            )
            radius_km: float = Field(
                default=DEFAULT_RADIUS_KM,
                description="Search radius in kilometers. Use 3 if absent.",
            )
            source_ids: list[str] = Field(
                description="Relevant source_id values from the registered catalog."
            )
            query_year: int | None = Field(
                default=None,
                description="Four-digit year if the user asks for a specific year; otherwise null.",
            )
            reasoning: str = Field(description="Brief reason for the selected sources.")

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You plan geospatial data retrieval. Extract the place/address, "
                    "radius in km, optional four-digit query year, and source IDs to fetch. If the user asks for all "
                    "data or broad infrastructure data, include every registered source, "
                    "including raster outputs such as modis_landuse. "
                    "Return only registered source IDs.\n\nRegistered sources:\n{catalog}",
                ),
                ("human", "{query}"),
            ]
        )
        chain = prompt | llm.with_structured_output(PlanSchema)
        raw_plan = chain.invoke({"query": query, "catalog": source_catalog_text()})
    else:
        json_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You plan geospatial data retrieval. Extract the place/address, "
                    "radius in km, optional four-digit query year, and source IDs to fetch. If the user asks for all "
                    "data or broad infrastructure data, include every registered source, "
                    "including raster outputs such as modis_landuse. "
                    "Return only registered source IDs.\n\n"
                    "You MUST respond with ONLY a valid JSON object, no extra text. "
                    "Format: {{\"place_query\": \"...\", \"radius_km\": 3.0, \"source_ids\": [...], \"query_year\": null, \"reasoning\": \"...\"}}\n\n"
                    "Registered sources:\n{catalog}",
                ),
                ("human", "{query}"),
            ]
        )
        chain = json_prompt | llm
        response = chain.invoke({"query": query, "catalog": source_catalog_text()})
        raw_text = response.content if hasattr(response, "content") else str(response)
        # Strip markdown fences if present
        import re as _re
        _match = _re.search(r"\{[\s\S]*\}", raw_text)
        if _match:
            raw_text = _match.group(0)
        raw_plan = json.loads(raw_text)

    source_ids = normalize_source_ids(raw_plan["source_ids"] if isinstance(raw_plan, dict) else raw_plan.source_ids)
    if _asks_for_all_data(query):
        source_ids = list(REGISTERED_SOURCES)
    if not source_ids:
        source_ids = default_source_ids()

    if isinstance(raw_plan, dict):
        query_year = raw_plan.get("query_year")
        radius_km_val = raw_plan.get("radius_km") or DEFAULT_RADIUS_KM
        place_query_val = raw_plan.get("place_query", "").strip()
        reasoning_val = raw_plan.get("reasoning", "").strip()
    else:
        query_year = raw_plan.query_year
        radius_km_val = raw_plan.radius_km
        place_query_val = raw_plan.place_query
        reasoning_val = raw_plan.reasoning

    if query_year is None:
        query_year = extract_query_year(query)

    return RequestPlan(
        place_query=place_query_val,
        radius_km=float(radius_km_val),
        source_ids=tuple(source_ids),
        query_year=query_year,
        reasoning=reasoning_val,
    )


def heuristic_plan_request(query: str) -> RequestPlan:
    """Small deterministic fallback for local development and tests."""

    radius_km = extract_radius_km(query) or DEFAULT_RADIUS_KM
    query_year = extract_query_year(query)
    source_ids = _heuristic_source_ids(query)
    place_query = _heuristic_place_query(query)
    return RequestPlan(
        place_query=place_query,
        radius_km=radius_km,
        source_ids=tuple(source_ids),
        query_year=query_year,
        reasoning="Heuristic fallback matched request keywords to registered sources.",
    )


def extract_radius_km(query: str) -> float | None:
    patterns = (
        r"(\d+(?:\.\d+)?)\s*(?:km|kilometer|kilometers|公里|千米)",
        r"([一二两三四五六七八九十]+)\s*(?:公里|千米)",
    )
    for pattern in patterns:
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(1)
        if re.fullmatch(r"\d+(?:\.\d+)?", value):
            return float(value)
        return float(_chinese_number_to_int(value))
    return None


def extract_query_year(query: str) -> int | None:
    match = re.search(r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})(?!\d)", query)
    if not match:
        return None
    return int(match.group(1))


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "_", value).strip("_").lower()
    return slug or "query"


def _heuristic_source_ids(query: str) -> list[str]:
    lowered = query.lower()
    if _asks_for_all_data(query):
        return list(REGISTERED_SOURCES)

    matched: list[str] = []
    for source in REGISTERED_SOURCES.values():
        if any(alias.lower() in lowered for alias in source.aliases):
            matched.append(source.source_id)

    return matched or default_source_ids()


def _asks_for_all_data(query: str) -> bool:
    lowered = query.lower()
    return any(token in lowered for token in ("all", "所有", "全部", "综合", "基础设施"))


def _geojson_outputs(outputs: dict[str, SourceOutput]) -> dict[str, dict[str, Any]]:
    return {
        filename: output
        for filename, output in outputs.items()
        if isinstance(output, dict)
    }


def _heuristic_place_query(query: str) -> str:
    cleaned = query.strip()
    cleaned = re.sub(
        r"获取|有多少|多少|的所有数据|所有数据|全部数据|的数据|数据|所有|全部|周围|附近|fetch|get|all\s+data|data|around|near",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\d+(?:\.\d+)?\s*(?:km|kilometer|kilometers|公里|千米)", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})(?!\d)\s*年?", " ", cleaned)
    cleaned = re.sub(r"[一二两三四五六七八九十]+\s*(?:公里|千米)", " ", cleaned)
    cleaned = re.sub(r"\b(?:in|for|of)\s*$", " ", cleaned, flags=re.IGNORECASE)
    for source in REGISTERED_SOURCES.values():
        for alias in sorted(source.aliases, key=len, reverse=True):
            cleaned = re.sub(re.escape(alias), " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,，?？。")
    return cleaned or query.strip()


def _chinese_number_to_int(value: str) -> int:
    digits = {
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    if value == "十":
        return 10
    if "十" in value:
        left, _, right = value.partition("十")
        tens = digits.get(left, 1) if left else 1
        ones = digits.get(right, 0) if right else 0
        return tens * 10 + ones
    return digits[value]
