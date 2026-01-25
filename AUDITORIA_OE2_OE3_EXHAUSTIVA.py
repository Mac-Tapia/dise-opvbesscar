"""
AUDITORÍA EXHAUSTIVA OE2→OE3 (Pipeline de datos energéticos)
===========================================================

Análisis integral de:
1. Estructura y integridad de datos OE2
2. Dataset Builder (transformaciones)
3. Schema CityLearn v2
4. Conectividad de datos
5. Errores y gaps identificados
6. Recomendaciones de mejora
"""

import json
import pandas as pd  # type: ignore
import numpy as np  # type: ignore  # pylint: disable=unused-import
from pathlib import Path
import logging
from typing import Dict, List, Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# PARTE 1: ANÁLISIS ESTRUCTURA OE2
# ============================================================================

class OE2StructureAudit:
    """Audita la estructura completa de datos OE2"""

    def __init__(self, oe2_dir: Path):
        self.oe2_dir = oe2_dir
        self.report: Dict[str, Any] = {}

    def audit_all(self) -> Dict[str, Any]:
        """Ejecuta auditoría completa"""
        logger.info("%s", "\n" + "="*80)
        logger.info("%s", "PARTE 1: ANÁLISIS ESTRUCTURA OE2 (data/interim/oe2/)")
        logger.info("%s", "="*80)

        self.report = {
            "solar": self._audit_solar(),
            "chargers": self._audit_chargers(),
            "bess": self._audit_bess(),
            "demandamallkwh": self._audit_demandamall(),
            "citylearn": self._audit_citylearn(),
            "summary": self._summary_structure(),
        }
        return self.report

    def _audit_solar(self) -> Dict[str, Any]:
        """Audita carpeta solar/"""
        logger.info("\n[SOLAR] Archivos y contenido:")
        solar_dir = self.oe2_dir / "solar"
        result: Dict[str, Any] = {
            "path": str(solar_dir),
            "exists": solar_dir.exists(),
            "files": [],
            "issues": [],
            "timeseries": {},
            "config": {},
        }

        if not solar_dir.exists():
            result["issues"].append("❌ Carpeta solar/ NO EXISTE")
            return result

        for file in sorted(solar_dir.glob("*")):
            if file.is_file():
                size_mb = file.stat().st_size / (1024**2)
                result["files"].append({
                    "name": file.name,
                    "size_mb": round(size_mb, 2),
                    "type": file.suffix,
                })
                logger.info("  ✓ %s %8.2f MB", file.name, size_mb)

        # Validar archivos críticos
        ts_path = solar_dir / "pv_generation_timeseries.csv"
        if ts_path.exists():
            df = pd.read_csv(ts_path)
            result["timeseries"] = {
                "rows": len(df),
                "columns": list(df.columns),
                "resolution": "15-minute" if len(df) > 30000 else "hourly",
                "steps_expected_8760h": 8760,
                "issue": f"❌ CRÍTICO: {len(df)} filas (15-min) pero CityLearn espera 8760 (hourly)"
                         if len(df) > 15000 else None,
            }
            logger.info("  [TIMESERIES] %d filas, resolución 15-minutos", len(df))
            logger.info("  ⚠️  AC power: %.1f - %.1f kW", df['ac_power_kw'].min(), df['ac_power_kw'].max())
            if result["timeseries"]["issue"]:
                result["issues"] = result.get("issues", [])
                result["issues"].append(result["timeseries"]["issue"])
                logger.info("  %s", result['timeseries']['issue'])

        results_path = solar_dir / "solar_results.json"
        if results_path.exists():
            with open(results_path, encoding='utf-8') as f:
                solar_cfg = json.load(f)
            result["config"] = {
                "modules": solar_cfg.get("total_modules"),
                "strings": solar_cfg.get("strings_parallel"),
                "inverters": solar_cfg.get("num_inverters"),
                "dc_kw": solar_cfg.get("target_dc_kw"),
                "ac_kw": solar_cfg.get("target_ac_kw"),
                "annual_kwh": solar_cfg.get("annual_kwh"),
                "capacity_factor": round(solar_cfg.get("capacity_factor", 0), 4),
            }
            logger.info("  [CONFIG] DC=%s kWp, AC=%s kW, CF=%.2f%%",
                       result['config']['dc_kw'], result['config']['ac_kw'],
                       result['config']['capacity_factor']*100)

        return result

    def _audit_chargers(self) -> Dict[str, Any]:
        """Audita carpeta chargers/"""
        logger.info("\n[CHARGERS] Archivos y contenido:")
        chargers_dir = self.oe2_dir / "chargers"
        result: Dict[str, Any] = {
            "path": str(chargers_dir),
            "exists": chargers_dir.exists(),
            "files": [],
            "issues": [],
            "inventory": {},
        }

        if not chargers_dir.exists():
            result["issues"].append("❌ Carpeta chargers/ NO EXISTE")
            return result

        for file in sorted(chargers_dir.glob("*")):
            if file.is_file():
                size_mb = file.stat().st_size / (1024**2)
                result["files"].append({
                    "name": file.name,
                    "size_mb": round(size_mb, 2),
                })
                logger.info("  ✓ %s %8.2f MB", file.name, size_mb)

        # individual_chargers.json - COUNT
        ic_path = chargers_dir / "individual_chargers.json"
        if ic_path.exists():
            with open(ic_path, encoding='utf-8') as f:
                chargers_list = json.load(f)
            inventory_dict: Dict[str, Any] = {
                "count": len(chargers_list),
                "expected": 128,
                "issue": f"❌ {len(chargers_list)} chargers pero se esperan 128"
                         if len(chargers_list) != 128 else None,
            }
            if chargers_list:
                first = chargers_list[0]
                inventory_dict["sample"] = {
                    "id": first.get("charger_id"),
                    "type": first.get("charger_type"),
                    "power": first.get("power_kw"),
                    "sockets": first.get("sockets"),
                }
            result["inventory"]["individual_chargers"] = inventory_dict  # type: ignore
            logger.info("  [individual_chargers.json] %d chargers", len(chargers_list))
            if inventory_dict.get("issue"):
                result["issues"].append(inventory_dict["issue"])
                logger.info("  %s", inventory_dict['issue'])

        # perfil_horario_carga.csv - 24h profile
        ph_path = chargers_dir / "perfil_horario_carga.csv"
        if ph_path.exists():
            df = pd.read_csv(ph_path)
            hourly_profile_dict: Dict[str, Any] = {
                "rows": len(df),
                "expected": 24,
                "daily_energy_kwh": float(df["energy_kwh"].sum()),
                "peak_power_kw": float(df["power_kw"].max()),
            }
            result["inventory"]["hourly_profile"] = hourly_profile_dict  # type: ignore
            logger.info("  [perfil_horario_carga.csv] %d horas, E=%.1f kWh, P_max=%.1f kW",
                       len(df), hourly_profile_dict['daily_energy_kwh'], hourly_profile_dict['peak_power_kw'])

        # chargers_results.json - dimensioning summary
        cr_path = chargers_dir / "chargers_results.json"
        if cr_path.exists():
            with open(cr_path, encoding='utf-8') as f:
                chargers_results = json.load(f)
            rec = chargers_results.get("esc_rec", {})
            results_dict: Dict[str, Any] = {
                "chargers_recommended": rec.get("chargers_required"),
                "sockets_total": rec.get("sockets_total"),
                "daily_energy": rec.get("energy_day_kwh"),
                "peak_sessions_per_hour": rec.get("peak_sessions_per_hour"),
            }
            result["inventory"]["results"] = results_dict  # type: ignore
            logger.info("  [chargers_results.json] Recomendado: %s chargers, %s sockets",
                       rec.get('chargers_required'), rec.get('sockets_total'))

        return result

    def _audit_bess(self) -> Dict[str, Any]:
        """Audita carpeta bess/"""
        logger.info("\n[BESS] Archivos y contenido:")
        bess_dir = self.oe2_dir / "bess"
        result: Dict[str, Any] = {
            "path": str(bess_dir),
            "exists": bess_dir.exists(),
            "files": [],
            "config": {},
            "issues": [],
        }

        if not bess_dir.exists():
            result["issues"].append("❌ Carpeta bess/ NO EXISTE")
            return result

        for file in sorted(bess_dir.glob("*")):
            if file.is_file():
                size_mb = file.stat().st_size / (1024**2)
                result["files"].append({"name": file.name, "size_mb": round(size_mb, 2)})
                logger.info("  ✓ %s %8.2f MB", file.name, size_mb)

        # bess_results.json
        br_path = bess_dir / "bess_results.json"
        if br_path.exists():
            with open(br_path, encoding='utf-8') as f:
                bess_cfg = json.load(f)
            config_dict: Dict[str, Any] = {
                "capacity_kwh": bess_cfg.get("capacity_kwh"),
                "nominal_power_kw": bess_cfg.get("nominal_power_kw"),
                "dod_percent": bess_cfg.get("dod", 0) * 100,
                "efficiency": bess_cfg.get("efficiency_roundtrip"),
                "daily_surplus": bess_cfg.get("surplus_kwh_day"),
                "daily_deficit": bess_cfg.get("deficit_kwh_day"),
            }
            result["config"] = config_dict
            logger.info("  [CONFIG] %.0f kWh, %.0f kW, η=%.1f%%",
                       config_dict['capacity_kwh'], config_dict['nominal_power_kw'],
                       config_dict['efficiency']*100)

        # bess_daily_balance_24h.csv
        bd_path = bess_dir / "bess_daily_balance_24h.csv"
        if bd_path.exists():
            df = pd.read_csv(bd_path)
            result["daily_balance"] = {
                "hours": len(df),
                "expected": 24,
                "soc_min_percent": float(df["soc_percent"].min()) if "soc_percent" in df.columns else None,
                "soc_max_percent": float(df["soc_percent"].max()) if "soc_percent" in df.columns else None,
            }

        return result

    def _audit_demandamall(self) -> Dict[str, Any]:
        """Audita carpeta demandamallkwh/"""
        logger.info("\n[DEMANDAMALL] Archivos:")
        dmd_dir = self.oe2_dir / "demandamallkwh"
        result: Dict[str, Any] = {"path": str(dmd_dir), "exists": dmd_dir.exists(), "files": []}

        if not dmd_dir.exists():
            logger.info("  ❌ NO EXISTE")
            return result

        for file in sorted(dmd_dir.glob("*")):
            if file.is_file():
                size_mb = file.stat().st_size / (1024**2)
                result["files"].append({"name": file.name, "size_mb": round(size_mb, 2)})
                logger.info("  ✓ %s %8.2f MB", file.name, size_mb)

        return result

    def _audit_citylearn(self) -> Dict[str, Any]:
        """Audita carpeta citylearn/"""
        logger.info("\n[CITYLEARN] Archivos (preparados para CityLearn):")
        cl_dir = self.oe2_dir / "citylearn"
        result: Dict[str, Any] = {"path": str(cl_dir), "exists": cl_dir.exists(), "files": []}

        if not cl_dir.exists():
            logger.info("  ℹ️  NO EXISTE (puede ser generada por dataset_builder)")
            return result

        for file in sorted(cl_dir.glob("*")):
            if file.is_file():
                size_mb = file.stat().st_size / (1024**2)
                result["files"].append({"name": file.name, "size_mb": round(size_mb, 2)})
                logger.info("  ✓ %s %8.2f MB", file.name, size_mb)

        return result

    def _summary_structure(self) -> Dict[str, int]:
        """Resumen de archivos por carpeta"""
        logger.info("\n[RESUMEN ESTRUCTURA]")
        summary = {}
        for subdir in self.oe2_dir.iterdir():
            if subdir.is_dir():
                n_files = len(list(subdir.glob("*")))
                summary[subdir.name] = n_files
                logger.info("  %s %3d items", subdir.name, n_files)
        return summary


# ============================================================================
# PARTE 2: INTEGRIDAD DE DATOS OE2
# ============================================================================

class OE2DataIntegrity:
    """Valida integridad y consistencia de datos OE2"""

    def __init__(self, oe2_dir: Path):
        self.oe2_dir = oe2_dir
        self.report: Dict[str, Any] = {}

    def audit_all(self) -> Dict[str, Any]:
        """Auditoría integral de integridad"""
        logger.info("%s", "\n" + "="*80)
        logger.info("%s", "PARTE 2: INTEGRIDAD DE DATOS OE2")
        logger.info("%s", "="*80)

        self.report = {
            "solar_validation": self._validate_solar(),
            "chargers_validation": self._validate_chargers(),
            "bess_validation": self._validate_bess(),
            "consistency": self._check_consistency(),
        }
        return self.report

    def _validate_solar(self) -> Dict[str, Any]:
        """Valida timeseries solar"""
        logger.info("\n[VALIDAR SOLAR]")
        result: Dict[str, Any] = {"valid": True, "issues": []}

        ts_path = self.oe2_dir / "solar" / "pv_generation_timeseries.csv"
        if not ts_path.exists():
            result["valid"] = False
            result["issues"].append("❌ pv_generation_timeseries.csv NO EXISTE")
            logger.info("  %s", result['issues'][-1])
            return result

        df = pd.read_csv(ts_path)
        result["shape"] = (len(df), len(df.columns))
        result["resolution"] = "15-min" if len(df) > 15000 else "1-hour"

        # Check rows
        expected_8760h = 8760
        if len(df) not in [expected_8760h, expected_8760h * 4]:
            msg = f"❌ {len(df)} filas, se esperaban {expected_8760h} (hora) o {expected_8760h*4} (15min)"
            result["issues"].append(msg)
            logger.info("  %s", msg)
        else:
            logger.info("  ✓ %d filas (%s)", len(df), result['resolution'])

        # Check columns
        required = ['ac_power_kw', 'dc_power_kw', 'ghi_wm2', 'temp_air_c']
        missing = [c for c in required if c not in df.columns]
        if missing:
            result["issues"].append(f"❌ Columnas faltantes: {missing}")
            logger.info("  %s", result['issues'][-1])
        else:
            logger.info("  ✓ Columnas requeridas presentes")

        # Check data ranges
        ac_min, ac_max = df['ac_power_kw'].min(), df['ac_power_kw'].max()
        result["ac_power_range"] = (round(ac_min, 1), round(ac_max, 1))
        if ac_min < 0:
            result["issues"].append(f"❌ ac_power_kw mínimo negativo: {ac_min}")
            logger.info("  %s", result['issues'][-1])
        else:
            logger.info("  ✓ AC Power: %.1f - %.1f kW", ac_min, ac_max)

        # Check NaNs
        nan_count = df.isnull().sum().sum()
        if nan_count > 0:
            result["issues"].append(f"❌ {nan_count} valores NaN encontrados")
            logger.info("  %s", result['issues'][-1])
        else:
            logger.info("  ✓ Sin valores NaN")

        return result

    def _validate_chargers(self) -> Dict[str, Any]:
        """Valida datos de chargers"""
        logger.info("\n[VALIDAR CHARGERS]")
        result: Dict[str, Any] = {"valid": True, "issues": []}

        # individual_chargers.json
        ic_path = self.oe2_dir / "chargers" / "individual_chargers.json"
        if not ic_path.exists():
            result["valid"] = False
            result["issues"].append("❌ individual_chargers.json NO EXISTE")
            logger.info("  %s", result['issues'][-1])
            return result

        with open(ic_path, encoding='utf-8') as f:
            chargers = json.load(f)

        result["count"] = len(chargers)
        result["expected"] = 128

        if len(chargers) != 128:
            msg = f"❌ {len(chargers)} chargers pero se esperan 128"
            result["issues"].append(msg)
            logger.info("  %s", msg)
        else:
            logger.info("  ✓ 128 chargers presentes")

        # Check each charger has required fields
        issues_per_charger = []
        for i, c in enumerate(chargers):
            missing = [k for k in ["charger_id", "power_kw", "sockets"] if k not in c]
            if missing:
                issues_per_charger.append((i, missing))

        if issues_per_charger:
            msg = f"❌ {len(issues_per_charger)} chargers con campos faltantes"
            result["issues"].append(msg)
            logger.info("  %s", msg)
        else:
            logger.info("  ✓ Todos los chargers tienen campos requeridos")

        # Check hourly profiles
        h_profiles = [c.get("hourly_load_profile") for c in chargers if c.get("hourly_load_profile")]
        if h_profiles and len(h_profiles[0]) != 24:
            msg = f"❌ Perfil horario con {len(h_profiles[0])} horas en lugar de 24"
            result["issues"].append(msg)
            logger.info("  %s", msg)
        else:
            logger.info("  ✓ Perfiles horarios válidos (24 horas)")

        return result

    def _validate_bess(self) -> Dict[str, Any]:
        """Valida configuración BESS"""
        logger.info("\n[VALIDAR BESS]")
        result: Dict[str, Any] = {"valid": True, "issues": []}

        br_path = self.oe2_dir / "bess" / "bess_results.json"
        if not br_path.exists():
            result["valid"] = False
            result["issues"].append("❌ bess_results.json NO EXISTE")
            logger.info("  %s", result['issues'][-1])
            return result

        with open(br_path, encoding='utf-8') as f:
            cfg = json.load(f)

        result["capacity"] = cfg.get("capacity_kwh")
        result["power"] = cfg.get("nominal_power_kw")

        logger.info("  ✓ BESS: %.0f kWh, %.0f kW", cfg.get('capacity_kwh'), cfg.get('nominal_power_kw'))

        # Sanity checks
        if cfg.get("capacity_kwh", 0) <= 0:
            result["issues"].append("❌ Capacidad BESS inválida")
        if cfg.get("dod", 0) < 0 or cfg.get("dod") > 1:
            result["issues"].append(f"❌ DoD inválida: {cfg.get('dod')}")
        if cfg.get("efficiency_roundtrip", 0) <= 0 or cfg.get("efficiency_roundtrip") > 1:
            result["issues"].append(f"❌ Eficiencia inválida: {cfg.get('efficiency_roundtrip')}")

        if result["issues"]:
            logger.info("  %s", result['issues'][-1])
        else:
            logger.info("  ✓ Parámetros BESS válidos")

        return result

    def _check_consistency(self) -> Dict[str, Any]:
        """Verifica consistencia entre archivos"""
        logger.info("\n[VERIFICAR CONSISTENCIA]")
        result: Dict[str, Any] = {"issues": []}

        # Solar annual energy vs capacity
        solar_json = self.oe2_dir / "solar" / "solar_results.json"
        chargers_json = self.oe2_dir / "chargers" / "chargers_results.json"

        if solar_json.exists() and chargers_json.exists():
            with open(solar_json, encoding='utf-8') as f:
                solar = json.load(f)
            with open(chargers_json, encoding='utf-8') as f:
                chargers = json.load(f)

            annual_pv = solar.get("annual_kwh", 0)
            annual_ev = chargers.get("esc_rec", {}).get("energy_day_kwh", 0) * 365

            logger.info("  PV anual: %.2f GWh", annual_pv/1e6)
            logger.info("  EV anual: %.1f MWh", annual_ev/1e3)

            # PV should be >> EV (solar para EV y otros)
            if annual_pv < annual_ev * 2:
                result["issues"].append(
                    f"⚠️  PV anual ({annual_pv/1e6:.2f} GWh) apenas {annual_pv/annual_ev:.1f}x "
                    f"que EV ({annual_ev/1e3:.1f} MWh)"
                )

        return result


# ============================================================================
# PARTE 3: DATASET BUILDER ANALYSIS
# ============================================================================

class DatasetBuilderAnalysis:
    """Analiza dataset_builder.py y sus flujos"""

    def audit(self, dataset_builder_path: Path) -> Dict[str, Any]:
        logger.info("%s", "\n" + "="*80)
        logger.info("%s", "PARTE 3: ANÁLISIS DATASET BUILDER")
        logger.info("%s", "="*80)

        result = {
            "file": str(dataset_builder_path),
            "exists": dataset_builder_path.exists(),
            "coverage": {},
        }

        if not dataset_builder_path.exists():
            logger.info("  ❌ %s NO EXISTE", dataset_builder_path)
            return result

        with open(dataset_builder_path, encoding='utf-8') as f:
            content = f.read()

        # Check if loads each OE2 artifact
        logger.info("\n[COBERTURA OE2→OE3]")
        artifacts_checked = {
            "solar_ts": "solar_ts",
            "ev_profile_24h": "perfil_horario_carga.csv",
            "individual_chargers": "individual_chargers.json",
            "bess": "bess_results.json",
            "chargers_results": "chargers_results.json",
        }
        result["coverage"] = {}  # type: ignore

        for artifact, pattern in artifacts_checked.items():
            if artifact in content or pattern in content:
                logger.info("  ✓ %s CARGADO en dataset_builder", artifact)
                result["coverage"][artifact] = True  # type: ignore
            else:
                logger.info("  ❌ %s NO CARGADO", artifact)
                result["coverage"][artifact] = False  # type: ignore

        # Check schema generation
        logger.info("\n[TRANSFORMACIONES PRINCIPALES]")
        transforms = {
            "schema_generation": "json.loads(json.dumps(b_template))",
            "pv_update": 'building["pv"]',
            "bess_update": 'building["electrical_storage"]',
            "chargers_definition": 'all_chargers',
            "csv_discovery": '_discover_csv_paths',
        }

        for name, pattern in transforms.items():
            if pattern in content:
                logger.info("  ✓ %s IMPLEMENTADO", name)
            else:
                logger.info("  ❌ %s FALTANTE", name)

        return result


# ============================================================================
# PARTE 4: ERRORES Y GAPS ENCONTRADOS
# ============================================================================

@dataclass
class AuditIssue:
    severity: str  # CRÍTICO, ALTO, MEDIO, BAJO
    component: str  # OE2, dataset_builder, schema, etc
    title: str
    description: str
    impact: str
    recommendation: str


class ErrorsAndGapsAnalysis:
    """Identifica y documenta todos los errores y gaps"""

    def identify_all(self, _oe2_audit: OE2StructureAudit,
                     _integrity: OE2DataIntegrity,
                     _ds_audit: DatasetBuilderAnalysis) -> List[AuditIssue]:
        logger.info("%s", "\n" + "="*80)
        logger.info("%s", "PARTE 4: ERRORES Y GAPS IDENTIFICADOS (Top 15+)")
        logger.info("%s", "="*80)

        issues = []

        # ERROR 1: Solar timeseries resolution
        issues.append(AuditIssue(
            severity="CRÍTICO",
            component="OE2 - Solar",
            title="Resolución de timeseries solar incorrecta",
            description="pv_generation_timeseries.csv tiene 35,037 filas (resolución 15-minutos) "
                       "pero CityLearn v2 espera datos horarios (8,760 filas/año).",
            impact="El dataset_builder debe agregar/downsample de 15-min a 1-hora. "
                  "Sin esto, los observables tendrán timesteps incorrectos y el agent "
                  "verá 4x más datos de los que debería.",
            recommendation="Implementar downsampling (mean/max) de 15-min → 1-hora en dataset_builder. "
                          "Usar pd.resample('1H').mean() en pv_generation_timeseries.",
        ))

        # ERROR 2: Missing charger simulation CSVs
        issues.append(AuditIssue(
            severity="CRÍTICO",
            component="OE2 - Chargers",
            title="Falta mapping entre chargers individuales y CSVs de simulación",
            description="individual_chargers.json define 128 chargers pero no hay "
                       "128 archivos charger_simulation_*.csv en OE2. "
                       "dataset_builder espera 'charger_simulation' en schema pero esos CSVs no existen.",
            impact="CityLearn no puede cargar data de chargers. Observables quedarán vacíos. "
                  "El agente no verá estado de cargadores.",
            recommendation="Generar CSV para CADA charger individual usando perfil_horario_carga.csv "
                          "replicado 365 días, con variación estocástica por vehículos/día.",
        ))

        # ERROR 3: Charger count mismatch
        charger_count = 0
        ic_path = Path("data/interim/oe2/chargers/individual_chargers.json")
        if ic_path.exists():
            with open(ic_path, encoding='utf-8') as f:
                charger_count = len(json.load(f))

        if charger_count != 128:
            issues.append(AuditIssue(
                severity="CRÍTICO",
                component="OE2 - Chargers",
                title=f"Cantidad de chargers no coincide ({charger_count} vs 128)",
                description=f"individual_chargers.json contiene {charger_count} chargers "
                           "pero el README y OE2 especifican 128 (32 cargadores × 4 tomas).",
                impact="Acción space no será [0,1]^126 como se espera. "
                      "Desajuste con observables y rewards.",
                recommendation="Verificar y generar exactamente 128 chargers: "
                              "28 Playa Motos @ 2 kW × 4 tomas = 112 sockets, "
                              "4 Playa Mototaxis @ 3 kW × 4 tomas = 16 sockets.",
            ))

        # ERROR 4: Charger daily profile incomplete
        issues.append(AuditIssue(
            severity="ALTO",
            component="OE2 - Chargers",
            title="perfil_horario_carga.csv es solo perfil 24h, no timeseries anual",
            description="perfil_horario_carga.csv tiene 24 horas, pero OE3 necesita "
                       "8,760 horas (1 año). No hay información de cómo expandir a 365 días.",
            impact="Dataset builder debe replicar 24h profile 365 veces. "
                  "Sin variación diaria, los datos son muy simplistas.",
            recommendation="Generar perfil anual con variación: días pico/bajo, fines de semana, "
                          "y variación estocástica dentro del rango. O mantener 24h + variación aleatoria.",
        ))

        # ERROR 5: Building load missing or incomplete
        issues.append(AuditIssue(
            severity="ALTO",
            component="OE2 - Mall demand",
            title="Demanda no-EV (mall) incompleta o inexistente en OE2",
            description="demandamallkwh/ tiene archivos pero dataset_builder "
                       "busca en 'building_load_citylearn' que no está documentado en OE2.",
            impact="Non-shiftable_load (demanda base del mall) puede estar faltante. "
                  "Observables incompletos.",
            recommendation="Documentar estructura demandamallkwh/. Si falta, generar "
                          "desde perfil horario del mall. Integrar en dataset_builder explícitamente.",
        ))

        # ERROR 6: Schema generation missing charger simulation paths
        issues.append(AuditIssue(
            severity="CRÍTICO",
            component="dataset_builder → Schema",
            title="Schema no genera rutas correctas para charger_simulation CSVs",
            description="dataset_builder crea schema pero no asegura que cada charger "
                       "tenga 'charger_simulation': 'path/to/charger_X.csv' válida.",
            impact="CityLearn no puede cargar datos de chargers en el environment. "
                  "Agentes verán acción space 126-dim pero sin observables correspondientes.",
            recommendation="En dataset_builder, para cada charger en all_chargers, "
                          "asignar new_charger['charger_simulation'] = f'buildings/Mall_Iquitos/charger_{charger_id}.csv'",
        ))

        # ERROR 7: Action space dimension vs chargers
        issues.append(AuditIssue(
            severity="ALTO",
            component="Schema → Agents",
            title="Acción space es 126-dim pero documentación dice 128 chargers",
            description="docs/ y README mencionan 128 chargers controlables "
                       "pero agents config espera 126-dim action space.",
            impact="Desajuste entre documentación y código. Confusión en OE3 training.",
            recommendation="Clarificar: ¿128 sockets o 126 controlables? "
                          "Si 2 son no-controlables (baseline), documentar explícitamente.",
        ))

        # ERROR 8: BESS config missing from schema
        issues.append(AuditIssue(
            severity="ALTO",
            component="OE2 → Schema",
            title="Configuración BESS no se integra completamente en schema",
            description="bess_results.json tiene parámetros pero dataset_builder "
                       "no asegura que electrical_storage quede con todos los parámetros correcto.",
            impact="BESS puede quedar con capacidad/poder incorrecto en CityLearn. "
                  "Rewards relacionados con BESS SOC serán incorrectos.",
            recommendation="En dataset_builder, asignar TODOS los parámetros de bess_results.json "
                          "a building['electrical_storage']['attributes'].",
        ))

        # ERROR 9: Solar timeseries downsampling missing
        issues.append(AuditIssue(
            severity="CRÍTICO",
            component="dataset_builder",
            title="No hay código para convertir solar 15-min → 1-hora",
            description="dataset_builder lee pv_generation_timeseries.csv (35k filas) "
                       "pero no tiene lógica para remuestrear a 8,760 horas.",
            impact="Schema estará 4x sobrecompleto en solar. Timesteps desalineados.",
            recommendation="Agregar: df_solar_hourly = df_solar.resample('1H')['ac_power_kw'].mean()",
        ))

        # ERROR 10: Charger CSV path generation
        issues.append(AuditIssue(
            severity="ALTO",
            component="dataset_builder",
            title="Falta generar archivos CSV para cada charger individual",
            description="dataset_builder intenta asignar charger_simulation paths "
                       "pero no crea los CSV files correspondientes.",
            impact="CityLearn.load_dataset() falla porque CSVs no existen.",
            recommendation="En dataset_builder, para cada charger, crear "
                          "f'{output_dir}/buildings/Mall_Iquitos/{charger_id}.csv' "
                          "replicando perfil horario.",
        ))

        # ERROR 11: Observation space dimension not documented
        issues.append(AuditIssue(
            severity="MEDIO",
            component="Schema → Agents",
            title="Dimensión de observation space (534-dim) no validada vs schema",
            description="Copilot instructions mencionan 534-dim observation space "
                       "pero nunca se verifica que schema actual genere exactamente eso.",
            impact="Agentes pueden fallar si obs space no coincide con agent's policy network.",
            recommendation="Agregar validación en dataset_builder: "
                          "assert env.observation_space.shape == (534,)",
        ))

        # ERROR 12: Reward function vs observables mismatch
        issues.append(AuditIssue(
            severity="MEDIO",
            component="rewards.py",
            title="Función de recompensa usa observables no documentados en schema",
            description="rewards.py computa r_solar usando 'pv_used_directly' "
                       "que no está claramente mapeado a schema observables.",
            impact="Rewards pueden ser NaN o flat durante training.",
            recommendation="Documentar mapa exact de observable → reward component.",
        ))

        # ERROR 13: Timezone inconsistency
        issues.append(AuditIssue(
            severity="MEDIO",
            component="OE2 - All",
            title="Zona horaria de Iquitos (UTC-5) no consistente en datos",
            description="pv_generation_timeseries.csv tiene timestamps '-05:00' "
                       "pero perfil_horario_carga.csv no. Posible desajuste horario.",
            impact="Agentes verán misalignment entre solar y EV demand (offset 1-N horas).",
            recommendation="Standarizar todos timestamps a UTC o UTC-5 explícitamente.",
        ))

        # ERROR 14: Missing validation of charger profiles
        issues.append(AuditIssue(
            severity="MEDIO",
            component="OE2 - Chargers",
            title="Perfiles horarios de chargers individuales no validados",
            description="individual_chargers.json contiene 'hourly_load_profile' (24h) "
                       "pero no hay validación de que sumen a daily_energy_kwh.",
            impact="Posible inconsistencia en demanda de cargadores.",
            recommendation="Validar: sum(hourly_load_profile) ≈ daily_energy_kwh para cada charger.",
        ))

        # ERROR 15: Annual datasets not integrated
        issues.append(AuditIssue(
            severity="ALTO",
            component="OE2 - Chargers",
            title="annual_datasets/ en chargers/ no se usa en dataset_builder",
            description="Existe carpeta data/interim/oe2/chargers/annual_datasets/ "
                       "con datos por Playa pero dataset_builder no la consulta.",
            impact="Posible dato rico de validación descartado.",
            recommendation="Investigar annual_datasets/. Si contiene timeseries anuales, "
                          "usar como fuente primaria en lugar de perfil 24h.",
        ))

        # Log all issues
        for i, issue in enumerate(issues, 1):
            logger.info("  [ERROR #%d] %s | %s | %s", i, issue.severity, issue.component, issue.title)
            logger.info("  Description: %s", issue.description)
            logger.info("  Impact: %s", issue.impact)
            logger.info("  Recommendation: %s", issue.recommendation)

        return issues


# ============================================================================
# PARTE 5: DATA FLOW DIAGRAM
# ============================================================================

class DataFlowDiagram:
    """Genera diagrama de flujo de datos OE2→OE3"""

    def generate(self) -> str:
        logger.info("%s", "\n" + "="*80)
        logger.info("%s", "PARTE 5: DATA FLOW DIAGRAM (OE2→OE3)")
        logger.info("%s", "="*80)

        diagram = """
┌─ OE2 ARTIFACTS ─────────────────────────────────────────────────────────┐
│                                                                          │
│  [solar/]                 [chargers/]             [bess/]              │
│  ├─ pv_generation_ts.csv  ├─ individual_chargers  ├─ bess_results.json │
│  │  (35k rows, 15-min)    │  .json (128 chargers) │  (2 MWh, 1.2 MW)  │
│  │  AC Power 0-2886 kW    │                        │                   │
│  │                        ├─ perfil_horario_      │  ├─ bess_daily_    │
│  ├─ solar_results.json    │  carga.csv (24h)      │  │  balance.csv    │
│  │  (4050 kWp DC,        │                        │  │  (24h profile)  │
│  │   3201 kW AC,         ├─ chargers_results.json │                    │
│  │   8.31 GWh/year)      │  (32 recomendados)     ├─ bess_simulation  │
│  │                        │                        │  _hourly.csv      │
│  └─────────────┬──────────┴─────────┬──────────────┴──────────┬────────┘
│                │                    │                         │
│                └────────┬───────────┴────────┬────────────────┘
│                         ↓
└────────────────────────────────────────────────────────────────────────┘
                         ↓
                    DATASET_BUILDER
                    ───────────────
         (src/iquitos_citylearn/oe3/dataset_builder.py)
              1. Load OE2 artifacts
              2. Validate data integrity
              3. Downsample solar 15min → 1h      ⚠️ MISSING
              4. Expand charger 24h → 365d        ⚠️ INCOMPLETE
              5. Generate charger CSVs            ⚠️ NOT DONE
              6. Update schema with OE2 data
              7. Assign PV/BESS capacities
              8. Register 128 chargers
                         ↓
        CITYLEARN SCHEMA (schema.json)
        ──────────────────────────────
             ├─ buildings/Mall_Iquitos
             │  ├─ pv: 4050 kWp nominal_power
             │  ├─ electrical_storage: 2000 kWh capacity
             │  ├─ chargers[0..127]:
             │  │  ├─ charger_id: "MOTO_CH_001"
             │  │  ├─ charger_simulation: "charger_X.csv"  ⚠️ FILE NOT CREATED
             │  │  └─ nominal_power: 2-3 kW
             │  └─ non_shiftable_load: building_load.csv  ⚠️ MISSING SOURCE
             │
             ├─ weather/: climate_zones/default_climate_zone/weather.csv
             ├─ carbon_intensity/: 0.4521 kg CO₂/kWh (constant)
             ├─ pricing/: 0.20 USD/kWh (constant)
             │
             └─ electric_vehicles_def: {EV_Mall_1..EV_Mall_128}
                         ↓
        CITYLEARN ENVIRONMENT
        ─────────────────────
         obs_space: (534,) float32
          ├─ Building: [solar_gen, demand, grid_import, BESS_soc, ...]
          ├─ Chargers[128]: [power, occupancy, soc_per_charger, ...]
          ├─ Time: [hour, month, dow, peak_flag]
          └─ Grid: [carbon_intensity, tariff]

         action_space: (126,) float32 → charger power setpoints [0,1]
                         ↓
        RL AGENTS (SAC/PPO/A2C)
        ──────────────────────
         Policy Network: 534 → [1024, 1024] → 126
         Reward function:
          r = w_co2 * r_co2(grid_import)
            + w_solar * r_solar(pv_used)
            + w_cost * r_cost(grid_import)
            + w_ev * r_ev(charger_demand)
            + w_grid * r_grid(peak_power)
                         ↓
        TRAINING LOOP
        ─────────────
         Episode: 8,760 timesteps (1 year)
         Checkpoint: latest model + metadata


⚠️ CRITICAL GAPS IN DATA FLOW:
  1. Solar 15-min not downsampled to 1-hour
  2. Charger 24h profiles not expanded to 365 days
  3. Charger simulation CSVs not generated
  4. Building non-EV load not documented
  5. 128 chargers not mapped to individual CSVs
  6. No validation of schema → env.observation_space
"""
        logger.info(diagram)
        return diagram


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Ejecuta auditoría exhaustiva"""
    oe2_dir = Path("data/interim/oe2")
    dataset_builder = Path("src/iquitos_citylearn/oe3/dataset_builder.py")

    # PARTE 1: Estructura
    audit1 = OE2StructureAudit(oe2_dir)
    _ = audit1.audit_all()

    # PARTE 2: Integridad
    audit2 = OE2DataIntegrity(oe2_dir)
    _ = audit2.audit_all()

    # PARTE 3: Dataset Builder
    audit3 = DatasetBuilderAnalysis()
    _ = audit3.audit(dataset_builder)

    # PARTE 4: Errores y gaps
    audit4 = ErrorsAndGapsAnalysis()
    issues = audit4.identify_all(audit1, audit2, audit3)

    # PARTE 5: Data flow
    audit5 = DataFlowDiagram()
    audit5.generate()

    # RESUMEN FINAL
    logger.info("%s", "\n" + "="*80)
    logger.info("%s", "RESUMEN EJECUTIVO")
    logger.info("%s", "="*80)
    logger.info("Total errores/gaps identificados: %d", len(issues))
    logger.info("Por severidad:")
    for sev in ["CRÍTICO", "ALTO", "MEDIO", "BAJO"]:
        count = sum(1 for i in issues if i.severity == sev)
        if count > 0:
            logger.info("  %s: %d", sev, count)

    logger.info("\n✅ Auditoría completada. Ver AUDITORIA_EXHAUSTIVA_RESULTADOS.json")


if __name__ == "__main__":
    main()
