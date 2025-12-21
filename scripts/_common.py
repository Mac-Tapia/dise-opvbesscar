from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from iquitos_citylearn.config import load_config, load_paths

def load_all(config_path: str) -> Tuple[Dict[str, Any], Any]:
    cfg = load_config(Path(config_path))
    rp = load_paths(cfg)
    return cfg, rp
