"""Auditoría exhaustiva del ambiente OE2/OE3 para entrenamiento de agentes RL."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Resultado de una auditoría individual."""

    check_name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    """Reporte completo de auditoría."""

    results: list[AuditResult] = field(default_factory=list)
    total_checks: int = 0
    passed_checks: int = 0

    def add_result(self, result: AuditResult) -> None:
        """Agrega un resultado a la auditoría."""
        self.results.append(result)
        self.total_checks += 1
        if result.passed:
            self.passed_checks += 1

    def summary(self) -> str:
        """Genera un resumen de la auditoría."""
        if self.total_checks == 0:
            return "Auditoría: 0/0 checks (0.0%)"
        passed_pct = (self.passed_checks / self.total_checks) * 100
        return f"Auditoría: {self.passed_checks}/{self.total_checks} checks ({passed_pct:.1f}%)"


class EnvironmentAuditor:
    """Auditor del ambiente para entrenamiento OE3."""

    def __init__(self, config_path: str | None = None) -> None:
        """Inicializa el auditor.

        Args:
            config_path: Ruta al archivo de configuración YAML (opcional)
        """
        self.config_path: Path = Path(config_path) if config_path else Path("configs/default.yaml")
        self.report: AuditReport = AuditReport()
        self.workspace_root: Path = Path(__file__).parent.parent.parent.parent

    def audit_all(self) -> AuditReport:
        """Ejecuta todas las auditorías."""
        logger.info("Iniciando auditoría exhaustiva del ambiente OE3...")

        self._audit_imports()
        self._audit_file_structure()
        self._audit_config()
        self._audit_gpu()
        self._audit_dataset()

        logger.info(self.report.summary())
        return self.report

    def _audit_imports(self) -> None:
        """Audita disponibilidad de dependencias críticas."""
        critical_packages: list[str] = ["pandas", "numpy", "gymnasium", "stable_baselines3"]
        optional_packages: list[str] = ["torch", "tensorflow"]

        for package in critical_packages:
            try:
                __import__(package)
                self.report.add_result(
                    AuditResult(
                        check_name=f"Import {package}",
                        passed=True,
                        message=f"✓ {package} disponible",
                    )
                )
            except ImportError as e:
                self.report.add_result(
                    AuditResult(
                        check_name=f"Import {package}",
                        passed=False,
                        message=f"✗ {package} no disponible: {str(e)}",
                    )
                )

        for package in optional_packages:
            try:
                __import__(package)
                self.report.add_result(
                    AuditResult(
                        check_name=f"Import {package}",
                        passed=True,
                        message=f"✓ {package} disponible (opcional)",
                        details={"optional": True},
                    )
                )
            except ImportError:
                logger.debug("Paquete opcional %s no disponible", package)

    def _audit_file_structure(self) -> None:
        """Audita estructura de archivos OE2."""
        required_paths: dict[str, str] = {
            "Solar PV Timeseries": "data/interim/oe2/solar/pv_generation_timeseries.csv",
            "Charger Profiles": "data/interim/oe2/chargers/perfil_horario_carga.csv",
            "Charger Config": "data/interim/oe2/chargers/individual_chargers.json",
            "BESS Config": "data/interim/oe2/bess/bess_config.json",
        }

        for check_name, relative_path in required_paths.items():
            full_path: Path = self.workspace_root / relative_path
            if full_path.exists():
                file_size_mb: float = full_path.stat().st_size / (1024 * 1024)
                self.report.add_result(
                    AuditResult(
                        check_name=check_name,
                        passed=True,
                        message=f"✓ {relative_path} existe",
                        details={"path": str(full_path), "size_mb": round(file_size_mb, 2)},
                    )
                )
            else:
                self.report.add_result(
                    AuditResult(
                        check_name=check_name,
                        passed=False,
                        message=f"✗ {relative_path} no encontrado",
                        details={"path": str(full_path)},
                    )
                )

    def _audit_config(self) -> None:
        """Audita archivo de configuración."""
        if not self.config_path.exists():
            self.report.add_result(
                AuditResult(
                    check_name="Config File",
                    passed=False,
                    message=f"✗ {self.config_path} no encontrado",
                )
            )
            return

        try:
            import yaml  # type: ignore[import]

            with open(self.config_path, "r", encoding="utf-8") as f:
                config: Any = yaml.safe_load(f)

            if isinstance(config, dict) and "oe3" in config:
                config_keys: list[str] = list(config.keys())
                self.report.add_result(
                    AuditResult(
                        check_name="Config File",
                        passed=True,
                        message=f"✓ {self.config_path} válido",
                        details={"sections": config_keys},
                    )
                )
            else:
                self.report.add_result(
                    AuditResult(
                        check_name="Config File",
                        passed=False,
                        message=f"✗ {self.config_path} no contiene sección 'oe3'",
                    )
                )
        except OSError as e:
            self.report.add_result(
                AuditResult(
                    check_name="Config File",
                    passed=False,
                    message=f"✗ Error al parsear {self.config_path}: {str(e)}",
                )
            )

    def _audit_gpu(self) -> None:
        """Audita disponibilidad de GPU para entrenamiento."""
        try:
            import torch  # type: ignore[import]

            if torch.cuda.is_available():
                device_count: int = torch.cuda.device_count()
                device_name: str = torch.cuda.get_device_name(0)
                device_props: Any = torch.cuda.get_device_properties(0)
                total_memory_gb: float = device_props.total_memory / (1024 ** 3)
                cuda_version: str = str(torch.version.cuda)

                self.report.add_result(
                    AuditResult(
                        check_name="GPU/CUDA",
                        passed=True,
                        message=f"✓ GPU CUDA disponible: {device_name}",
                        details={
                            "device_count": device_count,
                            "total_memory_gb": round(total_memory_gb, 2),
                            "cuda_version": cuda_version,
                        },
                    )
                )
            else:
                self.report.add_result(
                    AuditResult(
                        check_name="GPU/CUDA",
                        passed=False,
                        message="✗ No hay GPU CUDA disponible (entrenamiento será en CPU)",
                    )
                )
        except ImportError:
            self.report.add_result(
                AuditResult(
                    check_name="GPU/CUDA",
                    passed=False,
                    message="✗ PyTorch no instalado; no se puede detectar GPU",
                )
            )

    def _audit_dataset(self) -> None:
        """Audita estructura del dataset CityLearn."""
        dataset_path: Path = self.workspace_root / "data/processed/citylearnv2_dataset"

        if not dataset_path.exists():
            self.report.add_result(
                AuditResult(
                    check_name="CityLearn Dataset",
                    passed=False,
                    message=f"✗ Dataset no encontrado en {dataset_path}",
                )
            )
            return

        schema_path: Path = dataset_path / "schema.json"
        if schema_path.exists():
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema: dict[str, Any] = json.load(f)

                buildings: Any = schema.get("buildings", [])
                buildings_count: int = len(buildings) if isinstance(buildings, (list, tuple)) else 0
                self.report.add_result(
                    AuditResult(
                        check_name="CityLearn Dataset",
                        passed=True,
                        message=f"✓ Schema válido con {buildings_count} building(s)",
                        details={
                            "schema_path": str(schema_path),
                            "buildings": buildings_count,
                        },
                    )
                )
            except json.JSONDecodeError as e:
                self.report.add_result(
                    AuditResult(
                        check_name="CityLearn Dataset",
                        passed=False,
                        message=f"✗ Schema JSON inválido: {str(e)}",
                    )
                )
        else:
            self.report.add_result(
                AuditResult(
                    check_name="CityLearn Dataset",
                    passed=False,
                    message=f"✗ Schema no encontrado en {schema_path}",
                )
            )


def main() -> int:
    """Función principal de auditoría."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    auditor: EnvironmentAuditor = EnvironmentAuditor(config_path="configs/default.yaml")
    report: AuditReport = auditor.audit_all()

    # Imprimir resultados
    print("\n" + "=" * 80)
    print(report.summary())
    print("=" * 80)

    for result in report.results:
        status: str = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"{status}: {result.check_name}")
        print(f"        {result.message}")
        if result.details:
            for key, value in result.details.items():
                print(f"        - {key}: {value}")

    print("=" * 80)

    # Retorna código de salida basado en si todos los checks pasaron
    return 0 if report.passed_checks == report.total_checks else 1


if __name__ == "__main__":
    sys.exit(main())
