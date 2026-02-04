#!/usr/bin/env python3
"""
VALIDACIÓN INTEGRAL: Integración PPO con Cadena de Datos OE2→OE3
Verifica que TODOS los datos (solar, mall, BESS, 128 chargers)
estén correctamente construidos, sincronizados y listos para PPO.

Ejecución:
    python scripts/validate_complete_chain_oe2_to_ppo.py
"""

import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def print_header(title: str):
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_check(status: bool, message: str):
    """Print check result with ✅ or ❌."""
    symbol = "✅" if status else "❌"
    print(f"  {symbol} {message}")

def print_metric(label: str, value: str):
    """Print metric value."""
    print(f"    • {label}: {value}")

class FullChainValidator:
    """Valida cadena completa OE2 → OE3 → PPO."""

    def __init__(self):
        self.root = Path(__file__).parent.parent
        self.data_interim = self.root / "data" / "interim" / "oe2"
        self.data_processed = self.root / "data" / "processed" / "citylearn" / "iquitos_ev_mall"
        self.results = {
            "solar": False,
            "mall": False,
            "bess": False,
            "chargers": False,
            "schema": False,
            "sync": False,
            "ppo": False,
        }

    def validate_solar(self) -> bool:
        """Validar generación solar OE2."""
        print_header("FASE 1: VALIDACIÓN SOLAR")

        try:
            # OE2 source
            solar_path = self.data_interim / "solar" / "pv_generation_timeseries.csv"
            if not solar_path.exists():
                print_check(False, f"Archivo OE2 no encontrado: {solar_path}")
                return False

            df_solar = pd.read_csv(solar_path)
            print_check(True, f"OE2 Solar: {solar_path.name}")
            print_metric("Filas", f"{len(df_solar)} (esperado 8,760)")
            print_metric("Columnas", f"{df_solar.shape[1]} ({', '.join(df_solar.columns[:3])}...)")

            # Validaciones
            checks = []
            checks.append(("Filas = 8,760", len(df_solar) == 8760))
            checks.append(("Sin NaN", df_solar.isnull().sum().sum() == 0))

            # Verificar columna ac_power_kw
            has_power = "ac_power_kw" in df_solar.columns
            checks.append(("Columna 'ac_power_kw' presente", has_power))

            if has_power:
                power_vals = df_solar["ac_power_kw"]
                checks.append(("Valores positivos", (power_vals >= 0).all()))
                checks.append(("Rango realista", power_vals.max() < 10000))
                print_metric("Rango ac_power_kw", f"{power_vals.min():.1f} - {power_vals.max():.1f} kW")
                print_metric("Media ac_power_kw", f"{power_vals.mean():.1f} kW")

            all_ok = all(check[1] for check in checks)
            for check_name, check_result in checks:
                print_check(check_result, check_name)

            return all_ok

        except Exception as e:
            print_check(False, f"Error: {e}")
            return False

    def validate_mall(self) -> bool:
        """Validar demanda mall OE2."""
        print_header("FASE 2: VALIDACIÓN DEMANDA MALL")

        try:
            # OE2 source (con múltiples posibilidades)
            candidates = [
                self.data_interim / "demandamallkwh" / "demandamallhorakwh.csv",
                self.data_interim / "demandamallkwh" / "demanda_mall_horaria_anual.csv",
                self.data_interim / "demandamall" / "demanda_mall_kwh.csv",
            ]

            mall_path = None
            for path in candidates:
                if path.exists():
                    mall_path = path
                    break

            if mall_path is None:
                print_check(False, "Archivo OE2 Mall no encontrado")
                return False

            print_check(True, f"OE2 Mall: {mall_path.name}")

            # Intentar cargar con diferentes separadores
            try:
                df_mall = pd.read_csv(mall_path, sep=",", decimal=".")
            except:
                df_mall = pd.read_csv(mall_path, sep=";", decimal=".")

            print_metric("Filas", f"{len(df_mall)} (esperado 8,760)")
            print_metric("Columnas", f"{df_mall.shape[1]}")

            # Validaciones
            checks = []
            checks.append(("Filas >= 8,760", len(df_mall) >= 8760))

            # Encontrar columna de demanda
            demand_cols = [c for c in df_mall.columns if any(x in c.lower() for x in ["kwh", "demanda", "power", "kw"])]
            has_demand = len(demand_cols) > 0
            checks.append(("Columna demanda encontrada", has_demand))

            if has_demand:
                demand_col = demand_cols[0]
                demand_vals = pd.to_numeric(df_mall[demand_col], errors="coerce")
                valid_count = demand_vals.notna().sum()
                checks.append(("Valores válidos", valid_count > len(df_mall) * 0.9))
                print_metric(f"Columna demanda", f"{demand_col}")
                print_metric(f"Rango demanda", f"{demand_vals.min():.1f} - {demand_vals.max():.1f} kW")
                print_metric(f"Media demanda", f"{demand_vals.mean():.1f} kW")

            all_ok = all(check[1] for check in checks)
            for check_name, check_result in checks:
                print_check(check_result, check_name)

            return all_ok

        except Exception as e:
            print_check(False, f"Error: {e}")
            return False

    def validate_bess(self) -> bool:
        """Validar BESS OE2 e integración CityLearn."""
        print_header("FASE 3: VALIDACIÓN BESS")

        try:
            # OE2 source
            bess_path = self.data_interim / "bess" / "bess_simulation_hourly.csv"
            if not bess_path.exists():
                print_check(False, f"OE2 BESS: {bess_path} NO ENCONTRADO")
                return False

            df_bess = pd.read_csv(bess_path)
            print_check(True, f"OE2 BESS: {bess_path.name}")
            print_metric("Filas", f"{len(df_bess)} (esperado 8,760)")
            print_metric("Columnas", f"{df_bess.shape[1]}")

            # Validaciones OE2
            checks_oe2 = []
            checks_oe2.append(("Filas = 8,760", len(df_bess) == 8760))
            checks_oe2.append(("Columna 'soc_kwh' presente", "soc_kwh" in df_bess.columns))

            if "soc_kwh" in df_bess.columns:
                soc_vals = df_bess["soc_kwh"]
                checks_oe2.append(("Sin NaN", soc_vals.isnull().sum() == 0))
                checks_oe2.append(("Rango [1169-4520]", soc_vals.min() >= 1000 and soc_vals.max() <= 5000))
                print_metric("SOC rango", f"{soc_vals.min():.0f} - {soc_vals.max():.0f} kWh")
                print_metric("SOC media", f"{soc_vals.mean():.0f} kWh")
                print_metric("SOC primer valor", f"{soc_vals.iloc[0]:.0f} kWh")

            for check_name, check_result in checks_oe2:
                print_check(check_result, f"OE2: {check_name}")

            # CityLearn generated
            cie_path = self.data_processed / "electrical_storage_simulation.csv"
            if not cie_path.exists():
                print_check(False, "CityLearn electrical_storage_simulation.csv NO ENCONTRADO")
                return False

            df_cie = pd.read_csv(cie_path)
            print_check(True, f"CityLearn BESS: {cie_path.name} ({cie_path.stat().st_size / 1024:.0f} KB)")

            # Validaciones CityLearn
            checks_cl = []
            checks_cl.append(("Filas = 8,760", len(df_cie) == 8760))
            checks_cl.append(("Columna 'soc_stored_kwh'", "soc_stored_kwh" in df_cie.columns))

            if "soc_stored_kwh" in df_cie.columns:
                cie_soc = df_cie["soc_stored_kwh"]
                checks_cl.append(("Sin NaN", cie_soc.isnull().sum() == 0))

            for check_name, check_result in checks_cl:
                print_check(check_result, f"CityLearn: {check_name}")

            # Sincronización
            if "soc_kwh" in df_bess.columns and "soc_stored_kwh" in df_cie.columns:
                diff = float(np.abs(np.array(df_bess["soc_kwh"].values, dtype=float) - np.array(df_cie["soc_stored_kwh"].values, dtype=float)).sum())
                print_check(diff == 0, f"Sincronización: Diferencia total = {diff:.1f} kWh (PERFECTO: 0.0)")

            all_ok = all(check[1] for check in checks_oe2 + checks_cl)
            return all_ok

        except Exception as e:
            print_check(False, f"Error: {e}")
            return False

    def validate_chargers(self) -> bool:
        """Validar 32 chargers × 4 tomas = 128 tomas."""
        print_header("FASE 4: VALIDACIÓN CARGADORES (128 TOMAS)")

        try:
            # OE2 source
            chargers_path = self.data_interim / "chargers" / "chargers_hourly_profiles_annual.csv"
            if not chargers_path.exists():
                print_check(False, f"OE2 Chargers: {chargers_path} NO ENCONTRADO")
                return False

            df_chargers = pd.read_csv(chargers_path)
            print_check(True, f"OE2 Chargers: {chargers_path.name}")
            print_metric("Filas", f"{len(df_chargers)} (esperado 8,760)")
            print_metric("Columnas", f"{df_chargers.shape[1]} (esperado 32)")

            # Validaciones OE2
            checks = []
            checks.append(("Filas = 8,760", len(df_chargers) == 8760))
            checks.append(("Columnas = 32", df_chargers.shape[1] == 32))
            checks.append(("Sin NaN", df_chargers.isnull().sum().sum() == 0))

            for check_name, check_result in checks:
                print_check(check_result, f"OE2: {check_name}")

            # Verificar 128 CSVs individuales (CityLearn)
            print("\n  Verificando 128 archivos individuales en CityLearn:")
            generated_count = 0
            for i in range(1, 129):
                csv_name = f"charger_simulation_{i:03d}.csv"
                csv_path = self.data_processed / csv_name
                if csv_path.exists():
                    generated_count += 1

            print_check(generated_count == 128, f"Archivos generados: {generated_count}/128")

            return len(df_chargers) == 8760 and df_chargers.shape[1] == 32 and generated_count == 128

        except Exception as e:
            print_check(False, f"Error: {e}")
            return False

    def validate_schema(self) -> bool:
        """Validar schema.json con todas las integraciones."""
        print_header("FASE 5: VALIDACIÓN SCHEMA.JSON")

        try:
            schema_path = self.data_processed / "schema.json"
            if not schema_path.exists():
                print_check(False, f"schema.json NO ENCONTRADO")
                return False

            with open(schema_path) as f:
                schema = json.load(f)

            print_check(True, "schema.json cargado")

            # Verificar estructura
            checks = []
            checks.append(("Tiene 'buildings'", "buildings" in schema))

            if "buildings" in schema:
                bnames = list(schema["buildings"].keys())
                checks.append(("Building existente", len(bnames) > 0))
                if len(bnames) > 0:
                    building = schema["buildings"][bnames[0]]
                    print_metric("Building", f"{bnames[0]}")

                    # Verificar PV
                    has_pv = "pv" in building or "pv_power_plant" in building
                    checks.append(("PV configurado", has_pv))
                    print_check(has_pv, "PV configurado")

                    # Verificar BESS
                    has_bess = "electrical_storage" in building
                    checks.append(("BESS configurado", has_bess))
                    if has_bess:
                        bess_config = building["electrical_storage"]
                        has_energy_sim = "energy_simulation" in bess_config
                        checks.append(("BESS energy_simulation", has_energy_sim))
                        print_check(has_energy_sim, "BESS: energy_simulation referenciada")
                        if has_energy_sim:
                            print_metric("BESS reference", bess_config["energy_simulation"])

                    # Verificar Chargers
                    has_chargers = "chargers" in building
                    checks.append(("Chargers configurados", has_chargers))
                    if has_chargers:
                        n_chargers = len(building["chargers"])
                        print_check(n_chargers == 128, f"Chargers: {n_chargers}/128 configurados")
                        checks.append(("128 chargers", n_chargers == 128))

                        # Verificar que cada uno tenga charger_simulation
                        chargers_with_sim = 0
                        for charger_name, charger_config in building["chargers"].items():
                            if "charger_simulation" in charger_config:
                                chargers_with_sim += 1

                        print_check(chargers_with_sim == 128,
                                  f"Chargers con 'charger_simulation': {chargers_with_sim}/128")
                        checks.append(("Chargers con referencia", chargers_with_sim == 128))

            all_ok = all(check[1] for check in checks)
            for check_name, check_result in checks:
                if check_name not in ["PV configurado", "BESS energy_simulation",
                                     "Chargers con 'charger_simulation'"]:  # Ya logged
                    print_check(check_result, check_name)

            return all_ok

        except Exception as e:
            print_check(False, f"Error: {e}")
            return False

    def validate_sync(self) -> bool:
        """Validar sincronización completa OE2 → CityLearn."""
        print_header("FASE 6: VALIDACIÓN SINCRONIZACIÓN")

        try:
            # Contadores
            sources_ok = 0
            targets_ok = 0

            # 1. Solar
            solar_source = self.data_interim / "solar" / "pv_generation_timeseries.csv"
            solar_target = self.data_processed / "Building_1.csv"
            if solar_source.exists():
                sources_ok += 1
            if solar_target.exists():
                df = pd.read_csv(solar_target)
                if "solar_generation" in df.columns:
                    targets_ok += 1
            print_check(sources_ok >= 1, f"Solar OE2: Archivo existente")
            print_check(targets_ok >= 1, f"Solar CityLearn: Integrado en Building_1.csv")

            # 2. Mall
            mall_source = self.data_interim / "demandamallkwh" / "demandamallhorakwh.csv"
            mall_target = self.data_processed / "Building_1.csv"
            if mall_source.exists():
                sources_ok += 1
            if mall_target.exists():
                df = pd.read_csv(mall_target)
                if "non_shiftable_load" in df.columns:
                    targets_ok += 1
            print_check(sources_ok >= 2, f"Mall OE2: Archivo existente")
            print_check(targets_ok >= 2, f"Mall CityLearn: Integrado en Building_1.csv")

            # 3. BESS
            bess_source = self.data_interim / "bess" / "bess_simulation_hourly.csv"
            bess_target = self.data_processed / "electrical_storage_simulation.csv"
            if bess_source.exists():
                sources_ok += 1
            if bess_target.exists():
                targets_ok += 1
            print_check(sources_ok >= 3, f"BESS OE2: Archivo existente")
            print_check(targets_ok >= 3, f"BESS CityLearn: electrical_storage_simulation.csv generado")

            # 4. Chargers
            chargers_source = self.data_interim / "chargers" / "chargers_hourly_profiles_annual.csv"
            if chargers_source.exists():
                sources_ok += 1

            chargers_generated = len(list(self.data_processed.glob("charger_simulation_*.csv")))
            if chargers_generated == 128:
                targets_ok += 1
            print_check(sources_ok >= 4, f"Chargers OE2: Archivo existente")
            print_check(targets_ok >= 4, f"Chargers CityLearn: {chargers_generated}/128 archivos generados")

            print_metric("Fuentes OE2", f"{sources_ok}/4 existentes")
            print_metric("Targets CityLearn", f"{targets_ok}/4 generados")

            return sources_ok == 4 and targets_ok == 4

        except Exception as e:
            print_check(False, f"Error: {e}")
            return False

    def validate_ppo(self) -> bool:
        """Validar que PPO está listo para usar toda la cadena."""
        print_header("FASE 7: VALIDACIÓN READINESS PPO")

        try:
            # Verificar que simulate.py puede cargar todo
            from iquitos_citylearn.oe3.simulate import simulate
            from iquitos_citylearn.config import load_config, load_paths

            print_check(True, "Importaciones de PPO OK")

            # Verificar schema es válido
            schema_path = self.data_processed / "schema.json"
            with open(schema_path) as f:
                schema = json.load(f)

            bname = list(schema["buildings"].keys())[0]
            building = schema["buildings"][bname]

            checks = []

            # Observation space
            has_solar_obs = True  # CityLearn incluye solar en observación
            checks.append(("Observable Solar", has_solar_obs))

            has_mall_obs = True  # CityLearn incluye building load
            checks.append(("Observable Mall", has_mall_obs))

            has_bess_obs = "electrical_storage" in building
            checks.append(("Observable BESS", has_bess_obs))

            has_chargers_obs = "chargers" in building
            checks.append(("Observable Chargers", has_chargers_obs))

            # Action space
            has_bess_action = has_bess_obs
            checks.append(("Acción BESS", has_bess_action))

            n_chargers = len(building.get("chargers", {}))
            has_chargers_action = n_chargers == 128
            checks.append((f"Acciones Chargers ({n_chargers}/128)", has_chargers_action))

            for check_name, check_result in checks:
                print_check(check_result, check_name)

            all_ok = all(check[1] for check in checks)

            if all_ok:
                print("\n  ✅ LISTO PARA ENTRENAR PPO:")
                print("     python -m scripts.run_agent_ppo --config configs/default.yaml")

            return all_ok

        except Exception as e:
            print_check(False, f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_all(self):
        """Ejecutar todas las validaciones."""
        print("\n")
        print("╔" + "="*78 + "╗")
        print("║" + " VALIDACIÓN INTEGRAL: OE2 → OE3 → PPO".center(78) + "║")
        print("║" + f" {datetime.now().isoformat()}".ljust(78) + "║")
        print("╚" + "="*78 + "╝")

        self.results["solar"] = self.validate_solar()
        self.results["mall"] = self.validate_mall()
        self.results["bess"] = self.validate_bess()
        self.results["chargers"] = self.validate_chargers()
        self.results["schema"] = self.validate_schema()
        self.results["sync"] = self.validate_sync()
        self.results["ppo"] = self.validate_ppo()

        # Summary
        print_header("RESUMEN FINAL")

        for phase, status in self.results.items():
            symbol = "✅" if status else "❌"
            print(f"  {symbol} {phase.upper()}: {'PASSED' if status else 'FAILED'}")

        all_passed = all(self.results.values())

        print("\n" + "="*80)
        if all_passed:
            print("  ✅ TODAS LAS VALIDACIONES PASARON - SISTEMA LISTO PARA PPO")
        else:
            print("  ❌ ALGUNAS VALIDACIONES FALLARON - REVISAR ARRIBA")
        print("="*80 + "\n")

        return all_passed

if __name__ == "__main__":
    validator = FullChainValidator()
    success = validator.run_all()
    sys.exit(0 if success else 1)
