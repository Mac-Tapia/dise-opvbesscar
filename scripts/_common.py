from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import sys

from iquitos_citylearn.config import load_config, load_paths

def load_all(config_path: str) -> Tuple[Dict[str, Any], Any]:
    """
    Carga configuración y rutas del proyecto.

    IMPORTANTE: SOLO Python 3.11 es soportado para OE3.
    NO se soportan Python 3.12, 3.13, etc. Solo 3.11 EXACTAMENTE.
    """
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError(
            f"Python 3.11 EXACTAMENTE es requerido para OE3.\n"
            f"Actual: Python {sys.version_info.major}.{sys.version_info.minor}\n"
            f"Razón: Solo Python 3.11 es soportado. No usar 3.12, 3.13, etc.\n"
            f"Solución: Instala Python 3.11 exactamente desde python.org"
        )
    cfg = load_config(Path(config_path))
    rp = load_paths(cfg)
    return cfg, rp
