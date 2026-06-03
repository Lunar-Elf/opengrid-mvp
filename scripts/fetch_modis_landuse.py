from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from opengrid_mvp.clients.gee import fetch_modis_landuse_tif
from opengrid_mvp.config import DEFAULT_OUTPUT_DIR


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch MODIS MCD12Q1 land-use GeoTIFF from Google Earth Engine."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="MODIS land-use year. Omit to use the latest configured year.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the GeoTIFF should be written.",
    )
    args = parser.parse_args()

    year_suffix = args.year if args.year is not None else "latest"
    output_path = args.output_dir / f"modis_landuse_{year_suffix}.tif"
    saved = fetch_modis_landuse_tif(output_path=output_path, query_year=args.year)
    print(f"Saved MODIS land-use GeoTIFF to {saved}")


if __name__ == "__main__":
    main()
