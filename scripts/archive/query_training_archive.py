#!/usr/bin/env python3
"""
Utilidad de Consultas y Gestión de Datos de Entrenamiento
Permite consultar datos de agentes entrenados y preparar para nuevos entrenamientos incrementales
"""

import json
import pandas as pd  # type: ignore
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class TrainingArchiveManager:
    """Gestor de archivo consolidado de resultados de entrenamiento"""

    def __init__(self, archive_path: str = "training_results_archive.json"):
        self.archive_path = Path(archive_path)
        self.data = self._load_archive()

    def _load_archive(self) -> Dict[str, Any]:
        """Carga el archivo de archivo consolidado"""
        if not self.archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {self.archive_path}")

        with open(self.archive_path, "r", encoding="utf-8") as f:
            return json.load(f)  # type: ignore

    def save_archive(self):
        """Guarda cambios al archivo"""
        with open(self.archive_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        print(f"✅ Archive saved: {self.archive_path}")

    # ========================================================================
    # CONSULTAS GENERALES
    # ========================================================================

    def get_agents(self) -> List[str]:
        """Retorna lista de agentes entrenados"""
        return list(self.data["agents"].keys())

    def get_agent_status(self, agent: str | None = None) -> Dict:  # type: ignore
        """Retorna estado de agentes"""
        if agent:
            return {agent: self.data["agents"][agent]["status"]}
        else:
            return {name: data["status"] for name, data in self.data["agents"].items()}

    def get_all_completed(self) -> bool:
        """Verifica si todos los agentes completaron entrenamiento"""
        return self.data["metadata"]["all_trainings_completed"]  # type: ignore

    # ========================================================================
    # CONSULTAS DE MÉTRICAS FINALES
    # ========================================================================

    def get_final_metrics(self, agent: str | None = None) -> Dict:  # type: ignore
        """Retorna métricas finales de agentes"""
        if agent:
            return self.data["agents"][agent]["final_metrics"]  # type: ignore
        else:
            result = {}
            for name, agent_data in self.data["agents"].items():
                result[name] = agent_data["final_metrics"]
            return result

    def get_energy_metrics(self, agent: str | None = None) -> pd.DataFrame:  # type: ignore
        """Retorna métricas de energía en DataFrame"""
        metrics = {}
        agents = [agent] if agent else self.get_agents()

        for ag in agents:
            fm = self.data["agents"][ag]["final_metrics"]
            metrics[ag] = {
                "Grid Annual (kWh)": fm["grid_import_kwh_annual"],
                "CO₂ Annual (kg)": fm["co2_kg_annual"],
                "Solar Annual (kWh)": fm["solar_utilized_kwh_annual"],
            }

        return pd.DataFrame(metrics).T

    def get_performance_metrics(self, agent: str | None = None) -> pd.DataFrame:  # type: ignore
        """Retorna métricas de rendimiento (reward, losses)"""
        metrics = {}
        agents = [agent] if agent else self.get_agents()

        for ag in agents:
            fm = self.data["agents"][ag]["final_metrics"]
            metrics[ag] = {
                "Reward Final": fm["reward_final"],
                "Actor Loss": fm["actor_loss_final"],
                "Critic Loss": fm["critic_loss_final"],
            }

        return pd.DataFrame(metrics).T

    def get_training_duration(self, agent: str | None = None) -> pd.DataFrame:  # type: ignore
        """Retorna duración del entrenamiento"""
        durations = {}
        agents = [agent] if agent else self.get_agents()

        for ag in agents:
            td = self.data["agents"][ag]["training_dates"]
            ps = self.data["agents"][ag]["performance_speed"]
            durations[ag] = {
                "Duration (min)": td["duration_minutes"],
                "Duration (hms)": td["duration_hms"],
                "Avg Speed (steps/min)": ps["average_steps_per_minute"],
            }

        return pd.DataFrame(durations).T

    def get_reductions_vs_baseline(self, agent: str | None = None) -> pd.DataFrame:  # type: ignore
        """Retorna reducciones respecto a baseline"""
        reductions = {}
        agents = [agent] if agent else self.get_agents()

        for ag in agents:
            rvb = self.data["agents"][ag]["reductions_vs_baseline"]
            reductions[ag] = {
                "Grid Reduction (%)": rvb["grid_import_reduction_pct"],
                "CO₂ Reduction (%)": rvb["co2_reduction_pct"],
            }

        return pd.DataFrame(reductions).T

    # ========================================================================
    # CONSULTAS DE CONFIGURACIÓN
    # ========================================================================

    def get_training_config(self, agent: str) -> Dict:  # type: ignore
        """Retorna configuración de entrenamiento de agente"""
        return self.data["agents"][agent]["training_configuration"]  # type: ignore

    def get_checkpoint_info(self, agent: str) -> Dict:  # type: ignore
        """Retorna información de checkpoints"""
        return self.data["agents"][agent]["checkpoint_management"]  # type: ignore

    def can_resume(self, agent: str) -> bool:
        """Verifica si agente puede reanudar entrenamiento"""
        return self.data["agents"][agent]["checkpoint_management"]["can_resume_training"]  # type: ignore

    # ========================================================================
    # RANKING Y COMPARACIÓN
    # ========================================================================

    def get_ranking(self) -> List[tuple]:
        """Retorna ranking de agentes por eficiencia"""
        agents = []
        for name, agent_data in self.data["agents"].items():
            agents.append((
                agent_data["ranking"],
                name,
                agent_data["ranking_note"],
                agent_data["final_metrics"]["grid_import_kwh_annual"]
            ))
        return sorted(agents)

    def get_best_agent_for(self, criterion: str) -> str:
        """Retorna mejor agente según criterio"""
        criterios_map = {
            "energy": "A2C",
            "speed": "PPO",
            "reward": "SAC",
            "stability": "PPO",
            "overall": "PPO",
        }

        if criterion in criterios_map:
            return criterios_map[criterion]
        else:
            return f"Unknown criterion: {criterion}"

    # ========================================================================
    # MANEJO DE ENTRENAMIENTOS INCREMENTALES
    # ========================================================================

    def prepare_for_incremental_training(self, agent: str, new_total_timesteps: int) -> Dict:
        """Prepara agente para entrenamiento incremental desde checkpoint"""
        if not self.can_resume(agent):
            raise ValueError(f"{agent} cannot resume training")

        checkpoint_info = self.get_checkpoint_info(agent)
        current_steps = self.data["agents"][agent]["training_configuration"]["total_timesteps"]
        additional_steps = new_total_timesteps - current_steps

        instructions = {
            "agent": agent,
            "current_total_timesteps": current_steps,
            "desired_total_timesteps": new_total_timesteps,
            "additional_steps_to_train": additional_steps,
            "checkpoint_path": checkpoint_info["final_checkpoint"],
            "checkpoint_directory": checkpoint_info["checkpoint_directory"],
            "reset_num_timesteps": False,
            "python_code_template": f"""
from stable_baselines3 import {'PPO' if agent == 'PPO' else 'A2C' if agent == 'A2C' else 'SAC'}
import os

# Load agent from checkpoint
agent = {'PPO' if agent == 'PPO' else 'A2C' if agent == 'A2C' else 'SAC'}.load(
    os.path.join('{checkpoint_info["checkpoint_directory"]}', '{checkpoint_info["final_checkpoint"]}'),
    env=env
)

# Resume training (accumulates timesteps)
agent.learn(
    total_timesteps={additional_steps},
    reset_num_timesteps=False  # IMPORTANT: Keep False to accumulate steps
)

# Save new checkpoint
agent.save('checkpoint_step_{new_total_timesteps}')
            """
        }

        return instructions

    def update_after_incremental_training(self, agent: str, new_metrics: Dict):
        """Actualiza archivo después de entrenamiento incremental"""
        self.data["agents"][agent]["final_metrics"].update(new_metrics)
        self.data["metadata"]["timestamp_generated"] = datetime.utcnow().isoformat() + "Z"
        self.save_archive()
        print(f"✅ Archive updated for {agent}")

    # ========================================================================
    # REPORTES
    # ========================================================================

    def generate_summary_report(self) -> str:
        """Genera reporte de resumen"""
        report = []
        report.append("=" * 80)
        report.append("REPORTE DE DATOS DE ENTRENAMIENTO CONSOLIDADO")
        report.append("=" * 80)
        report.append("")

        report.append(f"Fecha de Generación: {self.data['metadata']['timestamp_generated']}")
        report.append(f"Ubicación: {self.data['metadata']['location']}")
        report.append(f"Agentes Entrenados: {self.data['metadata']['total_agents_trained']}")
        report.append(f"Todos Completados: {'✅ SÍ' if self.data['metadata']['all_trainings_completed'] else '❌ NO'}")
        report.append("")

        report.append("AGENTES:")
        for ranking, agent, note, grid in self.get_ranking():
            report.append(f"  {ranking}. {agent}: {note} ({grid:,.0f} kWh grid)")
        report.append("")

        report.append("MÉTRICAS FINALES (ANUALIZADAS):")
        report.append(self.get_energy_metrics().to_string())
        report.append("")

        report.append("APRENDIZAJE (REWARD Y LOSSES):")
        report.append(self.get_performance_metrics().to_string())
        report.append("")

        report.append("DURACIÓN DEL ENTRENAMIENTO:")
        report.append(self.get_training_duration().to_string())
        report.append("")

        report.append("REDUCCIONES RESPECTO A BASELINE:")
        report.append(self.get_reductions_vs_baseline().to_string())
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Interfaz de línea de comandos"""
    import sys

    manager = TrainingArchiveManager("training_results_archive.json")

    print("\n" + "=" * 80)
    print("GESTOR DE DATOS DE ENTRENAMIENTO - pvbesscar OE3")
    print("=" * 80 + "\n")

    if len(sys.argv) < 2:
        print("Comandos disponibles:")
        print("  summary         - Mostrar reporte de resumen")
        print("  energy          - Mostrar métricas de energía")
        print("  performance     - Mostrar métricas de aprendizaje")
        print("  duration        - Mostrar duración de entrenamientos")
        print("  reductions      - Mostrar reducciones vs baseline")
        print("  ranking         - Mostrar ranking de agentes")
        print("  best <criterion> - Mejor agente (energy/speed/reward/stability/overall)")
        print("  status          - Estado de agentes")
        print("  prepare <agent> <steps> - Preparar para entrenamiento incremental")
        print("")
        sys.exit(0)

    command = sys.argv[1].lower()

    try:
        if command == "summary":
            print(manager.generate_summary_report())

        elif command == "energy":
            print("\n⚡ MÉTRICAS DE ENERGÍA (ANUALIZADAS):")
            print(manager.get_energy_metrics().to_string())
            print()

        elif command == "performance":
            print("\n🧠 MÉTRICAS DE APRENDIZAJE:")
            print(manager.get_performance_metrics().to_string())
            print()

        elif command == "duration":
            print("\n⏱️ DURACIÓN DE ENTRENAMIENTOS:")
            print(manager.get_training_duration().to_string())
            print()

        elif command == "reductions":
            print("\n📉 REDUCCIONES RESPECTO A BASELINE:")
            print(manager.get_reductions_vs_baseline().to_string())
            print()

        elif command == "ranking":
            print("\n🏆 RANKING DE AGENTES:")
            for rank, agent, note, grid in manager.get_ranking():
                print(f"  {rank}. {agent}: {note}")
                print(f"     Grid import: {grid:,.0f} kWh/año")
            print()

        elif command == "best":
            if len(sys.argv) < 3:
                print("Usage: python script.py best <criterion>")
                sys.exit(1)
            criterion = sys.argv[2]
            result = manager.get_best_agent_for(criterion)
            print(f"\n🏆 Mejor agente para '{criterion}':")
            print(f"  {result[0]}: {result[1]}")
            print()

        elif command == "status":
            print("\n📊 ESTADO DE AGENTES:")
            statuses = manager.get_agent_status()
            for agent, status in statuses.items():
                print(f"  {agent}: {status}")
            print()

        elif command == "prepare":
            if len(sys.argv) < 4:
                print("Usage: python script.py prepare <agent> <total_timesteps>")
                sys.exit(1)
            agent = sys.argv[2].upper()
            new_steps = int(sys.argv[3])

            prep = manager.prepare_for_incremental_training(agent, new_steps)
            print(f"\n📋 PREPARACIÓN PARA ENTRENAMIENTO INCREMENTAL: {agent}")
            print(f"  Pasos actuales: {prep['current_total_timesteps']:,}")
            print(f"  Pasos deseados: {prep['desired_total_timesteps']:,}")
            print(f"  Pasos a entrenar: {prep['additional_steps_to_train']:,}")
            print(f"  Checkpoint: {prep['checkpoint_path']}")
            print(f"  Directorio: {prep['checkpoint_directory']}")
            print(f"\nCódigo template:")
            print(prep['python_code_template'])
            print()

        else:
            print(f"❌ Comando desconocido: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
