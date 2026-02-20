"""
Sistema de detección de cambios en datasets BESS, Solar y EV.
Monitorea archivos de datos y detecta si han sido modificados.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict

class DatasetInfo(TypedDict):
    """Info de un dataset para detección de cambios."""
    path: str
    timestamp: float
    file_hash: str
    file_size: int
    last_checked: str


class DatasetChangeDetector:
    """Detecta cambios en datasets BESS, Solar y EV."""
    
    DETECTOR_STATE_FILE = Path("data/processed/citylearn/.dataset_state.json")
    
    # Datos relativos a workspace root
    DATASETS = {
        "BESS": "data/oe2/bess/bess_ano_2024.csv",
        "SOLAR": "data/interim/oe2/solar/pv_generation_timeseries.csv",
        "EV_CHARGERS": "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
        "TRANSFORMED_BESS": "data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv",
    }
    
    def __init__(self, workspace_root: Path | str = None):
        """Inicializa detector con root del workspace."""
        if workspace_root is None:
            # Auto-detectar: subir desde scripts/
            workspace_root = Path(__file__).parent.parent.parent
        self.root = Path(workspace_root)
        self.detector_state_file = self.root / self.DETECTOR_STATE_FILE
    
    def _compute_file_hash(self, filepath: Path) -> str:
        """Computa hash SHA256 de un archivo."""
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except FileNotFoundError:
            return "FILE_NOT_FOUND"
    
    def get_dataset_info(self, dataset_name: str) -> DatasetInfo:
        """Obtiene info actual de un dataset."""
        if dataset_name not in self.DATASETS:
            raise ValueError(f"Dataset desconocido: {dataset_name}")
        
        rel_path = self.DATASETS[dataset_name]
        filepath = self.root / rel_path
        
        if not filepath.exists():
            return {
                "path": str(rel_path),
                "timestamp": 0,
                "file_hash": "NOT_FOUND",
                "file_size": 0,
                "last_checked": datetime.now().isoformat(),
            }
        
        stat = filepath.stat()
        return {
            "path": str(rel_path),
            "timestamp": stat.st_mtime,
            "file_hash": self._compute_file_hash(filepath),
            "file_size": stat.st_size,
            "last_checked": datetime.now().isoformat(),
        }
    
    def load_previous_state(self) -> dict[str, DatasetInfo]:
        """Carga estado anterior de datasets."""
        if not self.detector_state_file.exists():
            return {}
        
        try:
            with open(self.detector_state_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def save_current_state(self, state: dict[str, DatasetInfo]) -> None:
        """Guarda estado actual de datasets."""
        self.detector_state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.detector_state_file, "w") as f:
            json.dump(state, f, indent=2)
    
    def detect_changes(self) -> dict[str, bool]:
        """
        Detecta si algún dataset ha cambiado.
        Retorna dict con {dataset_name: has_changed}
        """
        previous = self.load_previous_state()
        current_state = {}
        changes = {}
        
        for dataset_name in self.DATASETS:
            current_info = self.get_dataset_info(dataset_name)
            current_state[dataset_name] = current_info
            
            # Detectar cambios comparando hash
            if dataset_name not in previous:
                changes[dataset_name] = True
            else:
                prev_info = previous[dataset_name]
                # Cambió si: hash diferente O archivo no encontrado cuando existía
                changes[dataset_name] = (
                    current_info["file_hash"] != prev_info["file_hash"]
                    or current_info["file_size"] != prev_info["file_size"]
                )
        
        # Guardar estado actual para próxima ejecución
        self.save_current_state(current_state)
        
        return changes
    
    def any_changed(self) -> bool:
        """Retorna True si algún dataset cambió."""
        changes = self.detect_changes()
        return any(changes.values())
    
    def get_changed_datasets(self) -> list[str]:
        """Retorna lista de datasets que cambieron."""
        changes = self.detect_changes()
        return [name for name, changed in changes.items() if changed]
    
    def reset_state(self) -> None:
        """Limpia estado guardado (fuerza regeneración completa)."""
        if self.detector_state_file.exists():
            self.detector_state_file.unlink()
        print(f"✓ Estado limpio: {self.detector_state_file}")


if __name__ == "__main__":
    detector = DatasetChangeDetector()
    
    print("=" * 80)
    print("DETECTOR DE CAMBIOS EN DATASETS")
    print("=" * 80)
    
    changed = detector.get_changed_datasets()
    print(f"\n🔍 Datasets detectados:")
    for name in detector.DATASETS:
        status = "⚠️  CAMBIO" if name in changed else "✓"
        info = detector.get_dataset_info(name)
        print(f"  {status} {name:20s} | Size: {info['file_size']:>10,} bytes")
    
    if changed:
        print(f"\n⚠️  Cambios detectados en: {', '.join(changed)}")
        print("   → Regenerar gráficas recomendado")
    else:
        print(f"\n✓ Sin cambios en datasets")
