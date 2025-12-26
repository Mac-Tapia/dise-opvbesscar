from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import os

import yaml
from dotenv import load_dotenv

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding='utf-8'))

def _env_float(key: str, default: float) -> float:
    v = os.getenv(key)
    return default if v is None or str(v).strip() == '' else float(v)

@dataclass(frozen=True)
class RuntimePaths:
    raw_dir: Path
    interim_dir: Path
    processed_dir: Path
    reports_dir: Path
    outputs_dir: Path
    analyses_dir: Path

    def ensure(self) -> None:
        for p in (
            self.raw_dir,
            self.interim_dir,
            self.processed_dir,
            self.reports_dir,
            self.outputs_dir,
            self.analyses_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)

def load_config(config_path: Path | None = None) -> Dict[str, Any]:
    load_dotenv(override=False)
    if config_path is None:
        config_path = project_root() / 'configs' / 'default.yaml'
    cfg = load_yaml(Path(config_path))

    cfg['oe3']['grid']['carbon_intensity_kg_per_kwh'] = _env_float(
        'GRID_CARBON_INTENSITY_KG_PER_KWH',
        float(cfg['oe3']['grid']['carbon_intensity_kg_per_kwh'])
    )
    cfg['oe3']['grid']['tariff_usd_per_kwh'] = _env_float(
        'TARIFF_USD_PER_KWH',
        float(cfg['oe3']['grid']['tariff_usd_per_kwh'])
    )
    return cfg

def load_paths(cfg: Dict[str, Any]) -> RuntimePaths:
    root = project_root()
    paths = cfg['paths']
    rp = RuntimePaths(
        raw_dir=(root / paths['raw_dir']).resolve(),
        interim_dir=(root / paths['interim_dir']).resolve(),
        processed_dir=(root / paths['processed_dir']).resolve(),
        reports_dir=(root / paths['reports_dir']).resolve(),
        outputs_dir=(root / paths.get('outputs_dir', 'outputs')).resolve(),
        analyses_dir=(root / paths.get('analyses_dir', 'analyses')).resolve(),
    )
    rp.ensure()
    return rp
