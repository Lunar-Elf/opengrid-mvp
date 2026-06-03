from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from opengrid_mvp.clients.gee import fetch_sentinel2_rgb_tif
from opengrid_mvp.config import DEFAULT_OUTPUT_DIR


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Sentinel-2 RGB composite GeoTIFF from Google Earth Engine."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Sentinel-2 composite year. Omit to use the latest configured year.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the GeoTIFF should be written.",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=10,
        help="Output resolution in meters. Default is 10 m (native RGB).",
    )
    parser.add_argument(
        "--max-cloud-cover",
        type=int,
        default=30,
        help="Maximum cloud cover percentage per image. Default is 30.",
    )
    args = parser.parse_args()

    year_suffix = args.year if args.year is not None else "latest"
    output_path = args.output_dir / f"sentinel2_rgb_{year_suffix}.tif"
    saved = fetch_sentinel2_rgb_tif(
        output_path=output_path,
        query_year=args.year,
        scale_meters=args.scale,
        max_cloud_cover=args.max_cloud_cover,
    )
    print(f"Saved Sentinel-2 RGB GeoTIFF to {saved}")


if __name__ == "__main__":
    main()
