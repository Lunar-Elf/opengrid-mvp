"""Make the src package and vendored deps importable when running scripts directly."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
VENDOR = ROOT / "_vendor"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if VENDOR.is_dir() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
