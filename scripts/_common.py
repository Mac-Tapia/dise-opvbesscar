from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import sys

from iquitos_citylearn.config import load_config, load_paths

def load_all(config_path: str) -> Tuple[Dict[str, Any], Any]:
    """
    Carga configuración y rutas del proyecto.

    IMPORTANTE: Solo Python 3.11 es soportado para OE3.
    Python 3.13 causa problemas de extracción/compilación en el entorno.
    Usa: .venv con Python 3.11 activado antes de ejecutar scripts.
    """
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError(
            f"Python 3.11 EXACTAMENTE es requerido para OE3.\n"
            f"Actual: Python {sys.version_info.major}.{sys.version_info.minor}\n"
            f"Razón: Python 3.13 causa problemas de compilación en el entorno.\n"
            f"Solución: Activa .venv con Python 3.11 antes de ejecutar scripts."
        )
    cfg = load_config(Path(config_path))
    rp = load_paths(cfg)
    return cfg, rp
