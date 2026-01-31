#!/usr/bin/env python3
"""
VALIDACIÓN INTEGRAL: Sistema de Entrenamientos Incrementales
Verificación sistemática de preparación para producción
"""

import json
import zipfile
from pathlib import Path
from datetime import datetime
# Typing imports removed (not used in this script)

class ValidationSystem:
    """Sistema completo de validación de entrenamientos incrementales"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "PENDING",
            "checks": {},
            "summary": {}
        }
        self.checkpoint_base = Path("analyses/oe3/training/checkpoints")
        self.archive_file = Path("training_results_archive.json")

    # ========================================================================
    # CHECK 1: INTEGRIDAD DEL ARCHIVO JSON
    # ========================================================================

    def check_archive_integrity(self) -> bool:
        """Valida estructura y contenido de training_results_archive.json"""

        print("\n" + "=" * 80)
        print("CHECK 1: INTEGRIDAD DEL ARCHIVO JSON")
        print("=" * 80)

        checks = {}

        # 1a. Existencia
        checks["file_exists"] = self.archive_file.exists()
        print(f"{'✅' if checks['file_exists'] else '❌'} Archivo existe: {self.archive_file}")

        if not checks["file_exists"]:
            self.results["checks"]["archive_integrity"] = checks
            return False

        # 1b. Lectura y parsing
        try:
            with open(self.archive_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            checks["valid_json"] = True
            print(f"✅ JSON válido y parseable")
        except json.JSONDecodeError as e:
            checks["valid_json"] = False
            print(f"❌ Error JSON: {e}")
            self.results["checks"]["archive_integrity"] = checks
            return False

        # 1c. Estructura esperada
        required_keys = ["metadata", "baseline", "agents", "comparison_summary"]
        checks["required_keys"] = all(k in self.data for k in required_keys)
        print(f"{'✅' if checks['required_keys'] else '❌'} Claves requeridas: {required_keys}")

        # 1d. Agentes
        agents = self.data.get("agents", {})
        expected_agents = {"SAC", "PPO", "A2C"}
        checks["agents_present"] = set(agents.keys()) == expected_agents
        print(f"{'✅' if checks['agents_present'] else '❌'} Agentes presentes: {list(agents.keys())}")

        # 1e. Todos los agentes completados
        all_completed = all(
            agents[a].get("status") == "COMPLETED"
            for a in agents
        )
        checks["all_completed"] = all_completed
        print(f"{'✅' if all_completed else '❌'} Todos agentes COMPLETED")

        # 1f. Validar estructura por agente
        agent_structure_ok = True
        required_agent_keys = [
            "status", "training_dates", "training_configuration",
            "final_metrics", "checkpoint_management"
        ]

        for agent_name, agent_data in agents.items():
            has_keys = all(k in agent_data for k in required_agent_keys)
            if not has_keys:
                agent_structure_ok = False
                print(f"❌ {agent_name}: Faltan claves - {set(required_agent_keys) - set(agent_data.keys())}")

        if agent_structure_ok:
            print(f"✅ Estructura de agentes válida")

        checks["agent_structure"] = agent_structure_ok

        # 1g. Validar métricas
        metrics_ok = True
        for agent_name, agent_data in agents.items():
            fm = agent_data.get("final_metrics", {})
            required_metrics = [
                "reward_final", "actor_loss_final", "critic_loss_final",
                "grid_import_kwh_annual", "co2_kg_annual"
            ]
            if not all(m in fm for m in required_metrics):
                metrics_ok = False
                print(f"❌ {agent_name}: Faltan métricas")

        if metrics_ok:
            print(f"✅ Todas las métricas presentes")

        checks["metrics_complete"] = metrics_ok

        self.results["checks"]["archive_integrity"] = checks
        return all(checks.values())

    # ========================================================================
    # CHECK 2: CHECKPOINTS FUNCIONALES
    # ========================================================================

    def check_checkpoints(self) -> bool:
        """Valida existencia y funcionalidad de checkpoints"""

        print("\n" + "=" * 80)
        print("CHECK 2: CHECKPOINTS FUNCIONALES")
        print("=" * 80)

        checks = {}
        agents = self.data.get("agents", {})

        all_ok = True

        for agent_name in ["SAC", "PPO", "A2C"]:
            agent_data = agents.get(agent_name, {})
            cm = agent_data.get("checkpoint_management", {})

            checkpoint_dir = Path(cm.get("checkpoint_directory", ""))
            final_checkpoint = cm.get("final_checkpoint", "")
            final_path = checkpoint_dir / final_checkpoint

            # 2a. Directorio existe
            dir_exists = checkpoint_dir.exists()
            print(f"\n🔹 {agent_name}:")
            print(f"  {'✅' if dir_exists else '❌'} Directorio: {checkpoint_dir}")

            if not dir_exists:
                all_ok = False
                continue

            # 2b. Checkpoint final existe
            final_exists = final_path.exists()
            print(f"  {'✅' if final_exists else '❌'} Checkpoint final: {final_checkpoint}")

            if not final_exists:
                all_ok = False
                continue

            # 2c. Integridad de archivo ZIP
            try:
                with zipfile.ZipFile(final_path, 'r') as zf:
                    is_valid_zip = zf.testzip() is None
                    files_count = len(zf.namelist())
                print(f"  {'✅' if is_valid_zip else '❌'} ZIP válido (archivos: {files_count})")
            except Exception as e:
                print(f"  ❌ Error ZIP: {e}")
                all_ok = False
                continue

            # 2d. Conteo de checkpoints intermedios
            checkpoint_files = list(checkpoint_dir.glob(f"{agent_name.lower()}_step_*.zip"))
            # expected_count = cm.get("checkpoints_saved", 0)  # Not used
            actual_count = len(checkpoint_files)
            count_ok = actual_count > 0  # Al menos algunos intermedios
            print(f"  {'✅' if count_ok else '❌'} Checkpoints intermedios: {actual_count} encontrados")

            # 2e. Tamaño de archivos
            total_size = sum(p.stat().st_size for p in checkpoint_dir.glob("*.zip"))
            total_mb = total_size / (1024 * 1024)
            print(f"  ✅ Tamaño total: {total_mb:.1f} MB")

            # 2f. Capacidad de resumir
            can_resume = cm.get("can_resume_training", False)
            print(f"  {'✅' if can_resume else '❌'} Resumible: {can_resume}")

            checks[agent_name] = {
                "dir_exists": dir_exists,
                "final_exists": final_exists,
                "zip_valid": is_valid_zip if final_exists else False,
                "intermediates_ok": count_ok,
                "can_resume": can_resume
            }

        self.results["checks"]["checkpoints"] = checks
        return all_ok

    # ========================================================================
    # CHECK 3: CONFIGURACIÓN DE ENTRENAMIENTOS
    # ========================================================================

    def check_training_config(self) -> bool:
        """Valida configuración de entrenamientos"""

        print("\n" + "=" * 80)
        print("CHECK 3: CONFIGURACIÓN DE ENTRENAMIENTOS")
        print("=" * 80)

        checks = {}
        agents = self.data.get("agents", {})

        all_ok = True

        for agent_name in ["SAC", "PPO", "A2C"]:
            agent_data = agents.get(agent_name, {})
            config = agent_data.get("training_configuration", {})

            print(f"\n🔹 {agent_name}:")

            # 3a. Parámetros básicos
            required_params = ["episodes", "timesteps_per_episode", "total_timesteps", "device"]
            has_params = all(p in config for p in required_params)
            print(f"  {'✅' if has_params else '❌'} Parámetros básicos: {has_params}")

            # 3b. Valores coherentes
            episodes = config.get("episodes", 0)
            tps = config.get("timesteps_per_episode", 0)
            total = config.get("total_timesteps", 0)

            coherent = (episodes * tps == total)
            print(f"  {'✅' if coherent else '❌'} Coherencia: {episodes} × {tps} = {total}")

            # 3c. Observation/Action spaces
            obs_space = config.get("observation_space_dims", 0)
            act_space = config.get("action_space_dims", 0)

            obs_ok = obs_space == 534
            act_ok = act_space == 126

            print(f"  {'✅' if obs_ok else '❌'} Obs space: {obs_space} dims (esperado 534)")
            print(f"  {'✅' if act_ok else '❌'} Action space: {act_space} dims (esperado 126)")

            # 3d. Device
            device = config.get("device", "")
            print(f"  ℹ️  Device: {device}")

            # 3e. Learning rate válido
            lr = config.get("learning_rate", 0)
            lr_ok = 1e-6 < lr < 1e-3 if lr else False
            print(f"  {'✅' if lr_ok else '⚠️ '} Learning rate: {lr}")

            checks[agent_name] = {
                "has_params": has_params,
                "values_coherent": coherent,
                "obs_space_ok": obs_ok,
                "action_space_ok": act_ok,
                "config_complete": all([has_params, coherent, obs_ok, act_ok])
            }

            if not checks[agent_name]["config_complete"]:
                all_ok = False

        self.results["checks"]["training_config"] = checks
        return all_ok

    # ========================================================================
    # CHECK 4: MÉTRICAS Y CONVERGENCIA
    # ========================================================================

    def check_metrics(self) -> bool:
        """Valida métricas finales y convergencia"""

        print("\n" + "=" * 80)
        print("CHECK 4: MÉTRICAS Y CONVERGENCIA")
        print("=" * 80)

        checks = {}
        agents = self.data.get("agents", {})

        all_ok = True

        for agent_name in ["SAC", "PPO", "A2C"]:
            agent_data = agents.get(agent_name, {})
            fm = agent_data.get("final_metrics", {})

            print(f"\n🔹 {agent_name}:")

            # 4a. Reward válido
            reward = fm.get("reward_final", 0)
            reward_ok = isinstance(reward, (int, float)) and reward != 0
            print(f"  {'✅' if reward_ok else '❌'} Reward final: {reward}")

            # 4b. Losses válidos
            actor_loss = fm.get("actor_loss_final", 0)
            critic_loss = fm.get("critic_loss_final", 0)

            # Para SAC/PPO, actor loss es negativo; A2C es positivo
            if agent_name == "A2C":
                actor_ok = isinstance(actor_loss, (int, float)) and actor_loss >= 0
            else:
                actor_ok = isinstance(actor_loss, (int, float)) and actor_loss < 0

            critic_ok = isinstance(critic_loss, (int, float)) and 0 <= critic_loss < 1

            print(f"  {'✅' if actor_ok else '❌'} Actor loss: {actor_loss}")
            print(f"  {'✅' if critic_ok else '❌'} Critic loss: {critic_loss}")

            # 4c. Energía coherente
            grid = fm.get("grid_import_kwh_annual", 0)
            co2 = fm.get("co2_kg_annual", 0)
            solar = fm.get("solar_utilized_kwh_annual", 0)

            # Grid y CO2 deben ser coherentes (ratio ~0.45 kg CO2/kWh)
            ratio = co2 / grid if grid > 0 else 0
            ratio_ok = 0.4 < ratio < 0.5

            energy_ok = all([grid > 0, co2 > 0, solar > 0])

            print(f"  {'✅' if energy_ok else '❌'} Grid: {grid:,.0f} kWh, CO₂: {co2:,.0f} kg, Solar: {solar:,.0f} kWh")
            print(f"  {'✅' if ratio_ok else '❌'} Ratio CO₂/Grid: {ratio:.4f} (esperado ~0.45)")

            # 4d. Reducciones válidas
            reductions = agent_data.get("reductions_vs_baseline", {})
            grid_red = reductions.get("grid_import_reduction_pct", 0)
            co2_red = reductions.get("co2_reduction_pct", 0)

            # Deben estar entre 99-100%
            red_ok = all([99 < grid_red <= 100, 99 < co2_red <= 100])

            print(f"  {'✅' if red_ok else '❌'} Reducciones: Grid {grid_red:.2f}%, CO₂ {co2_red:.2f}%")

            checks[agent_name] = {
                "reward_valid": reward_ok,
                "actor_loss_valid": actor_ok,
                "critic_loss_valid": critic_ok,
                "energy_coherent": energy_ok,
                "ratio_ok": ratio_ok,
                "reductions_ok": red_ok,
                "all_valid": all([reward_ok, actor_ok, critic_ok, energy_ok, ratio_ok, red_ok])
            }

            if not checks[agent_name]["all_valid"]:
                all_ok = False

        self.results["checks"]["metrics"] = checks
        return all_ok

    # ========================================================================
    # CHECK 5: SCRIPTS Y UTILIDADES
    # ========================================================================

    def check_utilities(self) -> bool:
        """Valida scripts de consulta y utilidades"""

        print("\n" + "=" * 80)
        print("CHECK 5: SCRIPTS Y UTILIDADES")
        print("=" * 80)

        checks = {}

        # 5a. Script de consultas
        query_script = Path("scripts/query_training_archive.py")
        query_exists = query_script.exists()
        print(f"{'✅' if query_exists else '❌'} Script consultas: {query_script}")
        checks["query_script"] = query_exists

        # 5b. Documentación
        guide_file = Path("GUIA_CONSULTAS_Y_ENTRENAMIENTOS_INCREMENTALES.md")
        guide_exists = guide_file.exists()
        print(f"{'✅' if guide_exists else '❌'} Guía: {guide_file}")
        checks["guide"] = guide_exists

        # 5c. Tabla comparativa
        table_file = Path("TABLA_COMPARATIVA_FINAL_CORREGIDA.md")
        table_exists = table_file.exists()
        print(f"{'✅' if table_exists else '❌'} Tabla comparativa: {table_file}")
        checks["comparison_table"] = table_exists

        # 5d. Cierre/consolidación
        closure_file = Path("CIERRE_CONSOLIDACION_DATOS_ENTRENAMIENTO.md")
        closure_exists = closure_file.exists()
        print(f"{'✅' if closure_exists else '❌'} Cierre: {closure_file}")
        checks["closure"] = closure_exists

        # 5e. Ejemplo incremental
        example_file = Path("ejemplo_entrenamiento_incremental.py")
        example_exists = example_file.exists()
        print(f"{'✅' if example_exists else '❌'} Ejemplo incremental: {example_file}")
        checks["example"] = example_exists

        self.results["checks"]["utilities"] = checks
        return all(checks.values())

    # ========================================================================
    # CHECK 6: READINESS PARA PRODUCCIÓN
    # ========================================================================

    def check_production_readiness(self) -> bool:
        """Valida preparación para producción"""

        print("\n" + "=" * 80)
        print("CHECK 6: READINESS PARA PRODUCCIÓN")
        print("=" * 80)

        checks = {}
        agents = self.data.get("agents", {})

        # 6a. Todos agentes completados
        all_completed = all(
            agents[a].get("status") == "COMPLETED"
            for a in ["SAC", "PPO", "A2C"]
        )
        print(f"{'✅' if all_completed else '❌'} Todos agentes completados")
        checks["all_completed"] = all_completed

        # 6b. Todos resumibles
        all_resumable = all(
            agents[a].get("checkpoint_management", {}).get("can_resume_training")
            for a in ["SAC", "PPO", "A2C"]
        )
        print(f"{'✅' if all_resumable else '❌'} Todos resumibles")
        checks["all_resumable"] = all_resumable

        # 6c. Baseline presente
        baseline = self.data.get("baseline", {})
        baseline_ok = all(
            baseline.get(k) for k in [
                "annual_grid_import_kwh", "annual_co2_kg", "grid_carbon_intensity_kg_co2_per_kwh"
            ]
        )
        print(f"{'✅' if baseline_ok else '❌'} Baseline configurado")
        checks["baseline_ok"] = baseline_ok

        # 6d. Comparativa presente
        comparison = self.data.get("comparison_summary", {})
        comparison_ok = len(comparison) > 0
        print(f"{'✅' if comparison_ok else '❌'} Comparativa de agentes")
        checks["comparison_ok"] = comparison_ok

        # 6e. Metadata correcta
        metadata = self.data.get("metadata", {})
        metadata_ok = all([
            metadata.get("all_trainings_completed"),
            metadata.get("total_agents_trained") == 3
        ])
        print(f"{'✅' if metadata_ok else '❌'} Metadata válida")
        checks["metadata_ok"] = metadata_ok

        # 6f. Instrucciones para resumir presentes
        resume_instr = self.data.get("resume_training_instructions")
        resume_ok = resume_instr is not None
        print(f"{'✅' if resume_ok else '❌'} Instrucciones para resumir")
        checks["resume_instructions"] = resume_ok

        production_ready = all(checks.values())

        self.results["checks"]["production_readiness"] = checks
        return production_ready

    # ========================================================================
    # GENERAR REPORTE FINAL
    # ========================================================================

    def generate_report(self) -> str:
        """Genera reporte final de validación"""

        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("REPORTE FINAL DE VALIDACIÓN")
        lines.append("=" * 80 + "\n")

        # Resumen de checks
        lines.append("📊 RESUMEN DE CHECKS:\n")

        check_results = []
        for check_name, check_data in self.results["checks"].items():
            if isinstance(check_data, dict):
                if "all_valid" in check_data:
                    # Métrica por agente
                    all_ok = all(
                        check_data[a].get("all_valid", False)
                        for a in check_data if isinstance(check_data[a], dict)
                    )
                else:
                    all_ok = all(check_data.values()) if isinstance(check_data, dict) else check_data
            else:
                all_ok = check_data

            status = "✅ OK" if all_ok else "❌ FALLÓ"
            check_results.append((check_name, all_ok))
            lines.append(f"  {status} - {check_name}")

        # Status general
        all_passed = all(status for _, status in check_results)

        lines.append("\n" + "=" * 80)
        if all_passed:
            lines.append("🟢 SISTEMA LISTO PARA PRODUCCIÓN")
            lines.append("Estado: READY FOR INCREMENTAL TRAINING")
        else:
            lines.append("🔴 PROBLEMAS DETECTADOS")
            lines.append("Estado: REQUIERE REVISIÓN")
        lines.append("=" * 80 + "\n")

        # Recomendaciones
        lines.append("💡 PRÓXIMOS PASOS:\n")

        if all_passed:
            lines.append("1. Sistema validado y listo para producción")
            lines.append("2. Entrenamientos incrementales habilitados")
            lines.append("3. Comandos disponibles:")
            lines.append("   - python scripts/query_training_archive.py summary")
            lines.append("   - python scripts/query_training_archive.py ranking")
            lines.append("   - python scripts/query_training_archive.py prepare <AGENT> <STEPS>")
            lines.append("4. Ver GUIA_CONSULTAS_Y_ENTRENAMIENTOS_INCREMENTALES.md")
        else:
            lines.append("1. Revisar checks fallidos arriba")
            lines.append("2. Restaurar archivos de backup si es necesario")
            lines.append("3. Re-ejecutar validación después de correcciones")

        lines.append("\n")

        return "\n".join(lines)

    # ========================================================================
    # EJECUTAR VALIDACIÓN COMPLETA
    # ========================================================================

    def run_full_validation(self) -> bool:
        """Ejecuta todas las validaciones"""

        print("\n" + "=" * 80)
        print("🚀 INICIANDO VALIDACIÓN INTEGRAL DEL SISTEMA")
        print("=" * 80)

        try:
            # Ejecutar checks en orden
            check1 = self.check_archive_integrity()
            if not check1:
                print("\n⚠️ Abortando validación - Archive inválido")
                self.results["status"] = "FAILED_ARCHIVE"
                return False

            check2 = self.check_checkpoints()
            check3 = self.check_training_config()
            check4 = self.check_metrics()
            check5 = self.check_utilities()
            check6 = self.check_production_readiness()

            # Determinar status general
            all_passed = all([check1, check2, check3, check4, check5, check6])
            self.results["status"] = "PASSED" if all_passed else "FAILED"

            # Generar reporte
            report = self.generate_report()
            print(report)

            # Guardar resultados
            self.save_results()

            return all_passed

        except Exception as e:
            print(f"\n❌ Error durante validación: {e}")
            self.results["status"] = "ERROR"
            self.results["error"] = str(e)
            self.save_results()
            return False

    def save_results(self):
        """Guarda resultados de validación"""

        output_file = Path("validation_results.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\n📄 Resultados guardados: {output_file}")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":

    validator = ValidationSystem()
    success = validator.run_full_validation()

    # Exit code
    exit(0 if success else 1)
