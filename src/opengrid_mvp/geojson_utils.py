"""Helpers for normalizing and writing GeoJSON FeatureCollections."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import BBox

GeoJSON = dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_feature_collection() -> GeoJSON:
    return {"type": "FeatureCollection", "features": []}


def ensure_feature_collection(data: GeoJSON) -> GeoJSON:
    if not isinstance(data, dict):
        raise ValueError("GeoJSON data must be a dictionary.")
    if data.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection.")
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError("FeatureCollection must contain a features list.")
    return data


def point_in_bbox(lon: float, lat: float, bbox: BBox) -> bool:
    return bbox.west <= lon <= bbox.east and bbox.south <= lat <= bbox.north


def iter_coordinates(geometry: GeoJSON | None) -> Iterable[tuple[float, float]]:
    if not geometry:
        return
    coordinates = geometry.get("coordinates")
    if coordinates is None:
        return
    yield from _iter_coordinate_pairs(coordinates)


def _iter_coordinate_pairs(value: Any) -> Iterable[tuple[float, float]]:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        yield float(value[0]), float(value[1])
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_coordinate_pairs(item)


def feature_intersects_bbox(feature: GeoJSON, bbox: BBox) -> bool:
    geometry = feature.get("geometry")
    return any(point_in_bbox(lon, lat, bbox) for lon, lat in iter_coordinates(geometry))


def filter_features_to_bbox(collection: GeoJSON, bbox: BBox) -> GeoJSON:
    ensure_feature_collection(collection)
    filtered = [
        feature
        for feature in collection["features"]
        if feature_intersects_bbox(feature, bbox)
    ]
    return {"type": "FeatureCollection", "features": filtered}


def add_source_metadata(
    collection: GeoJSON,
    *,
    source: dict[str, str],
    bbox: BBox,
    retrieved_at: str | None = None,
) -> GeoJSON:
    ensure_feature_collection(collection)
    timestamp = retrieved_at or utc_now_iso()
    normalized_features = []
    for feature in collection["features"]:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("Every item in features must be a GeoJSON Feature.")

        normalized = copy.deepcopy(feature)
        properties = normalized.get("properties") or {}
        if not isinstance(properties, dict):
            properties = {"original_properties": properties}
        properties.update(
            {
                "source_id": source["source_id"],
                "source_name": source["source_name"],
                "category": source["category"],
                "retrieved_at": timestamp,
                "bbox_query": bbox.as_dict(),
            }
        )
        normalized["properties"] = properties
        normalized_features.append(normalized)

    return {"type": "FeatureCollection", "features": normalized_features}


def merge_feature_collections(collections: Iterable[GeoJSON]) -> GeoJSON:
    features: list[GeoJSON] = []
    for collection in collections:
        ensure_feature_collection(collection)
        features.extend(copy.deepcopy(collection["features"]))
    return {"type": "FeatureCollection", "features": features}


def save_geojson(collection: GeoJSON, path: Path) -> Path:
    ensure_feature_collection(collection)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(collection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_geojson(path: Path) -> GeoJSON:
    return ensure_feature_collection(json.loads(path.read_text(encoding="utf-8")))
