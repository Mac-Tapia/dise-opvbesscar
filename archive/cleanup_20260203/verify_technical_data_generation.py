#!/usr/bin/env python3
"""
VERIFICACIÓN DE GENERACIÓN DE DATOS TÉCNICOS
===========================================

Verifica que durante el entrenamiento de SAC y PPO se generen correctamente
los archivos técnicos: result_{agent}.json, timeseries_{agent}.csv, trace_{agent}.csv
"""

from __future__ import annotations

import json  # noqa: F401
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Any, cast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_technical_files_generation() -> None:
    """Verifica que se generen correctamente los archivos técnicos durante entrenamiento."""

    print("=" * 80)
    print("🔍 VERIFICACIÓN - GENERACIÓN ARCHIVOS TÉCNICOS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Objetivo: Asegurar que SAC y PPO generen automáticamente:")
    print("  • result_{agent}.json - Métricas completas")
    print("  • timeseries_{agent}.csv - Datos horarios 8760+ registros")
    print("  • trace_{agent}.csv - Observaciones/acciones durante entrenamiento")
    print("")

    # Directorio de simulaciones
    sims_dir = Path("outputs/oe3_simulations")

    # Agentes a verificar
    agents_to_verify = ["sac", "ppo", "a2c"]

    print("📂 Verificando directorio de simulaciones...")
    if not sims_dir.exists():
        print(f"❌ ERROR: {sims_dir} no existe")
        sims_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Creado directorio: {sims_dir}")
    else:
        print(f"✅ Directorio existe: {sims_dir}")

    print("")

    # =====================================================================
    # 1. VERIFICAR ARCHIVOS EXISTENTES
    # =====================================================================
    print("🔍 1. ESTADO ACTUAL DE ARCHIVOS TÉCNICOS")
    print("-" * 50)

    existing_files = {}

    for agent in agents_to_verify:
        print(f"📋 Agente: {agent.upper()}")

        result_file = sims_dir / f"result_{agent}.json"
        timeseries_file = sims_dir / f"timeseries_{agent}.csv"
        trace_file = sims_dir / f"trace_{agent}.csv"

        files_status = {
            "result": result_file.exists(),
            "timeseries": timeseries_file.exists(),
            "trace": trace_file.exists()
        }

        existing_files[agent] = {
            "files": files_status,
            "paths": {
                "result": result_file,
                "timeseries": timeseries_file,
                "trace": trace_file
            }
        }

        # Status por archivo
        for file_type, exists in files_status.items():
            status = "✅ Existe" if exists else "❌ Falta"
            file_path = Path(cast(str, existing_files[agent]["paths"][file_type]))  # type: ignore
            size_info = ""

            if exists:
                try:
                    size_kb = file_path.stat().st_size / 1024
                    size_info = f" ({size_kb:.1f} KB)"
                except:
                    size_info = " (sin acceso)"

            print(f"   • {file_type}.{file_path.suffix}: {status}{size_info}")

        # Resumen agente
        total_files = sum(files_status.values())
        if total_files == 3:
            print(f"   🎯 Status: ✅ COMPLETO ({total_files}/3)")
        elif total_files > 0:
            print(f"   ⚠️  Status: PARCIAL ({total_files}/3)")
        else:
            print(f"   ❌ Status: VACÍO (0/3)")
        print("")

    # =====================================================================
    # 2. VERIFICAR INTEGRIDAD DE ARCHIVOS EXISTENTES
    # =====================================================================
    print("🔬 2. VERIFICACIÓN DE INTEGRIDAD")
    print("-" * 50)

    integrity_results: Dict[str, Any] = {}

    for agent in agents_to_verify:
        print(f"📊 Verificando integridad: {agent.upper()}")

        agent_data = existing_files[agent]
        integrity = {
            "result_valid": False,
            "timeseries_valid": False,
            "trace_valid": False,
            "errors": []
        }

        # Verificar result.json
        files_data = cast(Dict[str, Any], agent_data.get("files", {}))
        paths_data = cast(Dict[str, Any], agent_data.get("paths", {}))

        if files_data.get("result", False):
            try:
                result_path = paths_data.get("result")
                if result_path:
                    with open(str(result_path), 'r', encoding='utf-8') as f:
                        result_data = json.load(f)

                    # Verificar campos críticos
                    required_fields = ['agent', 'steps', 'carbon_kg', 'pv_generation_kwh', 'ev_charging_kwh']
                    missing_fields = [f for f in required_fields if f not in result_data]

                    if not missing_fields:
                        integrity["result_valid"] = True
                        print(f"   ✅ result_{agent}.json: Válido")
                        print(f"      • Agent: {result_data.get('agent', 'N/A')}")
                        print(f"      • Steps: {result_data.get('steps', 0):,}")
                        print(f"      • Years simulated: {result_data.get('simulated_years', 0):.2f}")
                    else:
                        cast(List[str], integrity["errors"]).append(f"result_{agent}.json: campos faltantes {missing_fields}")
                        print(f"   ❌ result_{agent}.json: Campos faltantes {missing_fields}")

            except json.JSONDecodeError as e:
                cast(List[str], integrity["errors"]).append(f"result_{agent}.json: JSON inválido - {e}")
                print(f"   ❌ result_{agent}.json: JSON inválido")
            except Exception as e:
                cast(List[str], integrity["errors"]).append(f"result_{agent}.json: Error - {e}")
                print(f"   ❌ result_{agent}.json: Error leyendo archivo")
        else:
            print(f"   ⏭️  result_{agent}.json: No existe")

        # Verificar timeseries.csv
        if files_data.get("timeseries", False):
            try:
                timeseries_path = paths_data.get("timeseries")
                if timeseries_path:
                    ts_df = pd.read_csv(str(timeseries_path))

                # Verificar estructura
                required_cols = ['timestamp', 'grid_import_kwh', 'solar_generation_kw', 'ev_charging_kwh']
                missing_cols = [c for c in required_cols if c not in ts_df.columns]

                if not missing_cols and len(ts_df) > 1000:  # Al menos 1000 registros
                    integrity["timeseries_valid"] = True
                    print(f"   ✅ timeseries_{agent}.csv: Válido")
                    print(f"      • Registros: {len(ts_df):,}")
                    print(f"      • Columnas: {len(ts_df.columns)}")
                    print(f"      • Periodo: {ts_df['timestamp'].iloc[0]} a {ts_df['timestamp'].iloc[-1]}")
                else:
                    issues = []
                    if missing_cols:
                        issues.append(f"columnas faltantes {missing_cols}")
                    if len(ts_df) <= 1000:
                        issues.append(f"pocos registros ({len(ts_df)})")
                    cast(List[str], integrity["errors"]).append(f"timeseries_{agent}.csv: {', '.join(issues)}")
                    print(f"   ❌ timeseries_{agent}.csv: {', '.join(issues)}")

            except Exception as e:
                cast(List[str], integrity["errors"]).append(f"timeseries_{agent}.csv: Error - {e}")
                print(f"   ❌ timeseries_{agent}.csv: Error leyendo archivo")
        else:
            print(f"   ⏭️  timeseries_{agent}.csv: No existe")

        # Verificar trace.csv
        if files_data.get("trace", False):
            try:
                trace_path = paths_data.get("trace")
                if trace_path:
                    trace_df = pd.read_csv(str(trace_path))

                # Verificar estructura básica
                required_cols = ['step', 'reward_env']
                missing_cols = [c for c in required_cols if c not in trace_df.columns]

                if not missing_cols and len(trace_df) > 50:  # Al menos 50 registros de trace
                    integrity["trace_valid"] = True
                    print(f"   ✅ trace_{agent}.csv: Válido")
                    print(f"      • Registros: {len(trace_df):,}")
                    print(f"      • Columnas: {len(trace_df.columns)}")
                    if 'reward_total' in trace_df.columns:
                        avg_reward = trace_df['reward_total'].mean()
                        print(f"      • Reward promedio: {avg_reward:.4f}")
                else:
                    issues = []
                    if missing_cols:
                        issues.append(f"columnas faltantes {missing_cols}")
                    if len(trace_df) <= 50:
                        issues.append(f"pocos registros ({len(trace_df)})")
                    cast(List[str], integrity["errors"]).append(f"trace_{agent}.csv: {', '.join(issues)}")
                    print(f"   ❌ trace_{agent}.csv: {', '.join(issues)}")

            except Exception as e:
                cast(List[str], integrity["errors"]).append(f"trace_{agent}.csv: Error - {e}")
                print(f"   ❌ trace_{agent}.csv: Error leyendo archivo")
        else:
            print(f"   ⏭️  trace_{agent}.csv: No existe")

        integrity_results[agent] = integrity

        # Resumen de integridad por agente
        valid_count = sum([
            cast(bool, integrity["result_valid"]),
            cast(bool, integrity["timeseries_valid"]),
            cast(bool, integrity["trace_valid"])
        ])

        if valid_count == 3:
            print(f"   🎯 Integridad: ✅ PERFECTO ({valid_count}/3)")
        elif valid_count > 0:
            print(f"   ⚠️  Integridad: PARCIAL ({valid_count}/3)")
        else:
            print(f"   ❌ Integridad: FALLIDO (0/3)")

        print("")

    # =====================================================================
    # 3. VERIFICAR CONFIGURACIÓN EN SIMULATE.PY
    # =====================================================================
    print("⚙️  3. VERIFICACIÓN DE CONFIGURACIÓN SIMULATE.PY")
    print("-" * 50)

    simulate_path = Path("src/iquitos_citylearn/oe3/simulate.py")

    if not simulate_path.exists():
        print("❌ ERROR: simulate.py no encontrado")
        return

    with open(simulate_path, 'r', encoding='utf-8') as f:
        simulate_content = f.read()

    # Verificar que las mejoras estén implementadas
    checks = {
        "timestamp_generation": "timestamps = pd.date_range" in simulate_content,
        "logging_files": "[DATOS TÉCNICOS]" in simulate_content,
        "environmental_metrics": "environmental_metrics" in simulate_content,
        "trace_logging": "Trace:" in simulate_content and "registros)" in simulate_content,
        "result_enhanced": "result_data =" in simulate_content and ".copy()" in simulate_content,
    }

    print("📋 Verificaciones en simulate.py:")

    for check_name, passed in checks.items():
        status = "✅ OK" if passed else "❌ Falta"
        description = {
            "timestamp_generation": "Generación de timestamps horarios",
            "logging_files": "Logging detallado de archivos generados",
            "environmental_metrics": "Métricas ambientales en result.json",
            "trace_logging": "Logging específico de trace.csv",
            "result_enhanced": "Estructura mejorada de result.json"
        }
        print(f"   • {description[check_name]}: {status}")

    all_checks_passed = all(checks.values())
    if all_checks_passed:
        print("   🎯 Configuración: ✅ COMPLETA")
    else:
        failed_checks = [name for name, passed in checks.items() if not passed]
        print(f"   ⚠️  Configuración: FALTAN {len(failed_checks)} elementos")

    print("")

    # =====================================================================
    # 4. RECOMENDACIONES
    # =====================================================================
    print("💡 4. RECOMENDACIONES")
    print("-" * 50)

    print("🔧 Para garantizar generación correcta:")
    print("")

    # Recomendaciones por agente
    for agent in agents_to_verify:
        files_exist = existing_files[agent]["files"]
        integrity = integrity_results[agent]

        total_files = sum(cast(dict, files_exist).values())
        valid_files = sum([
            cast(bool, integrity["result_valid"]),
            cast(bool, integrity["timeseries_valid"]),
            cast(bool, integrity["trace_valid"])
        ])

        print(f"📋 {agent.upper()}:")

        if total_files == 3 and valid_files == 3:
            print("   ✅ TODO OK - Archivos completos y válidos")
        elif total_files == 0:
            print("   🚀 ENTRENAR - Ejecutar entrenamiento para generar archivos")
            print(f"      Comando: python -m scripts.run_oe3_simulate --config configs/default.yaml --agent {agent}")
        elif total_files > 0 and valid_files < total_files:
            print("   🔄 RE-GENERAR - Archivos incompletos o corruptos")
            print("      Solución 1: Eliminar archivos existentes y re-entrenar")
            print("      Solución 2: Usar scripts/generate_sac_technical_data.py (post-proceso)")
        elif valid_files < 3:
            print("   ⚠️  VERIFICAR - Algunos archivos válidos, otros problemáticos")
            for error in cast(List[str], integrity["errors"]):
                print(f"      - {error}")

        print("")

    print("🛠️  Configuración simulate.py:")
    if all_checks_passed:
        print("   ✅ Configuración completa - generación automática habilitada")
    else:
        print("   ⚠️  Faltan mejoras en simulate.py")
        print("      • Las modificaciones ya fueron aplicadas en esta sesión")
        print("      • Verificar que los cambios se guardaron correctamente")

    print("")

    # =====================================================================
    # 5. RESUMEN FINAL
    # =====================================================================
    print("=" * 80)
    print("📊 RESUMEN FINAL - GENERACIÓN ARCHIVOS TÉCNICOS")
    print("=" * 80)

    # Contar agentes con archivos completos
    complete_agents = []
    partial_agents = []
    missing_agents = []

    for agent in agents_to_verify:
        total_files = sum(cast(dict, existing_files[agent]["files"]).values())
        valid_files = sum([
            integrity_results[agent]["result_valid"],
            integrity_results[agent]["timeseries_valid"],
            integrity_results[agent]["trace_valid"]
        ])

        if total_files == 3 and valid_files == 3:
            complete_agents.append(agent)
        elif total_files > 0:
            partial_agents.append(agent)
        else:
            missing_agents.append(agent)

    print(f"✅ Agentes COMPLETOS: {len(complete_agents)}/3")
    if complete_agents:
        print(f"   • {', '.join([a.upper() for a in complete_agents])}")

    print(f"⚠️  Agentes PARCIALES: {len(partial_agents)}/3")
    if partial_agents:
        print(f"   • {', '.join([a.upper() for a in partial_agents])}")

    print(f"❌ Agentes FALTANTES: {len(missing_agents)}/3")
    if missing_agents:
        print(f"   • {', '.join([a.upper() for a in missing_agents])}")

    print("")

    if len(complete_agents) == 3:
        print("🎯 STATUS: ✅ PERFECTO - Todos los agentes tienen archivos técnicos completos")
    elif len(complete_agents) > 0:
        print("🎯 STATUS: 🔄 PARCIAL - Algunos agentes listos, otros pendientes")
    else:
        print("🎯 STATUS: 🚀 INICIAL - Listo para comenzar entrenamientos")

    print("")
    print("💡 PRÓXIMOS PASOS:")
    if missing_agents:
        next_agent = missing_agents[0]
        print(f"   1. Entrenar {next_agent.upper()}: python -m scripts.run_oe3_simulate --config configs/default.yaml --agent {next_agent}")
        print("   2. Verificar generación automática de archivos técnicos")
        print("   3. Repetir para agentes restantes")
    elif partial_agents:
        print("   1. Revisar archivos corruptos/incompletos")
        print("   2. Re-generar archivos problemáticos")
        print("   3. Validar integridad completa")
    else:
        print("   1. ✅ Archivos técnicos completos")
        print("   2. Proceder con análisis comparativo")
        print("   3. Generar reporte final de rendimiento")

    print("=" * 80)

if __name__ == "__main__":
    verify_technical_files_generation()
