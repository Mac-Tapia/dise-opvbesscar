from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import sys

from iquitos_citylearn.config import load_config, load_paths

def load_all(config_path: str) -> Tuple[Dict[str, Any], Any]:
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError("Python 3.11 is required. Activate the .venv before running scripts.")
    cfg = load_config(Path(config_path))
    rp = load_paths(cfg)
    return cfg, rp
