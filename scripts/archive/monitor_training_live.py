#!/usr/bin/env python
"""
Monitor en vivo del entrenamiento de SAC, PPO, A2C
Muestra progreso, recompensas, CO2, tiempo estimado
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrainingMonitor:
    """Monitor en vivo del entrenamiento de agentes RL"""

    def __init__(self, output_dir: str = "outputs/oe3_simulations"):
        self.output_dir = Path(output_dir)
        self.start_time = None
        self.agents = {"SAC": "sac", "PPO": "ppo", "A2C": "a2c"}

    def read_checkpoint_summary(self, agent_name: str) -> dict[str, Any] | None:
        """Lee el archivo de resumen de checkpoints de un agente"""
        try:
            summaries = list(self.output_dir.glob(f"TRAINING_CHECKPOINTS_SUMMARY_*_{agent_name.upper()}_*.json"))
            if not summaries:
                return None
            latest = sorted(summaries)[-1]
            with open(latest) as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Error leyendo checkpoint para {agent_name}: {e}")
            return None

    def read_timeseries(self, agent_name: str) -> pd.DataFrame | None:
        """Lee la timeseries de un agente"""
        try:
            ts_file = self.output_dir / f"{agent_name.lower()}_episodes_timeseries.csv"
            if not ts_file.exists():
                return None
            return pd.read_csv(ts_file)
        except Exception as e:
            logger.debug(f"Error leyendo timeseries para {agent_name}: {e}")
            return None

    def format_time(self, seconds: float) -> str:
        """Formatea segundos a hh:mm:ss"""
        return str(timedelta(seconds=int(seconds)))

    def print_status(self) -> None:
        """Imprime el estado actual del entrenamiento"""
        print("\n" + "=" * 100)
        print(f"🕐 MONITOREO EN VIVO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)

        any_running = False

        for agent_display, agent_key in self.agents.items():
            summary = self.read_checkpoint_summary(agent_display)
            ts = self.read_timeseries(agent_display)

            if summary or ts is not None:
                any_running = True
                status = "🟢 ENTRENANDO" if summary else "✓ COMPLETADO"
                print(f"\n{agent_display:>4} {status}")
                print("-" * 100)

                if summary:
                    total_steps = summary.get("total_timesteps", 0)
                    episode = summary.get("episode", 0)
                    max_episodes = 5  # Ajustar según config
                    progress = (episode / max_episodes) * 100 if max_episodes > 0 else 0

                    print(f"  Episodio:          {episode}/{max_episodes} ({progress:.1f}%)")
                    print(f"  Total timesteps:   {total_steps:,} / 43,800 (5 episodios)")
                    print(f"  Mejor recompensa:  {summary.get('best_reward', 'N/A')}")
                    print(f"  Recompensa actual: {summary.get('last_reward', 'N/A')}")

                if ts is not None and len(ts) > 0:
                    last_row = ts.iloc[-1]
                    avg_reward = ts["reward"].mean()
                    max_reward = ts["reward"].max()
                    min_reward = ts["reward"].min()

                    print(f"  Promedio recompensa: {avg_reward:.2f}")
                    print(f"  Máximo:              {max_reward:.2f}")
                    print(f"  Mínimo:              {min_reward:.2f}")

                    if "co2_emissions" in ts.columns:
                        co2 = ts["co2_emissions"].iloc[-1]
                        print(f"  CO₂ (último):        {co2:,.0f} kg")

                    if "solar_used" in ts.columns:
                        solar = ts["solar_used"].mean()
                        print(f"  Solar (promedio):    {solar:.1f}%")
            else:
                print(f"\n{agent_display:>4} ⏳ PENDIENTE (no iniciado)")

        if not any_running:
            print("\n⏳ Ningún entrenamiento activo aún. Esperando...")

        print("\n" + "=" * 100)
        print("💡 Consejos:")
        print("  - El entrenamiento puede tardar 30-60 minutos (con GPU)")
        print("  - Checkpoints guardados en: checkpoints/{SAC,PPO,A2C}/")
        print("  - Timeseries CSV guardadas en: outputs/oe3_simulations/")
        print("=" * 100 + "\n")

    def monitor_loop(self, interval: int = 10) -> None:
        """Loop de monitoreo continuo"""
        self.start_time = time.time()
        iteration = 0

        try:
            while True:
                iteration += 1
                self.print_status()

                # Revisar si training completó (archivo de resumen final)
                summary_file = self.output_dir / "simulation_summary.json"
                if summary_file.exists():
                    print("\n✅ ENTRENAMIENTO COMPLETADO - Leyendo resultados finales...")
                    with open(summary_file) as f:
                        final = json.load(f)
                        print(json.dumps(final, indent=2))
                    break

                print(f"⏳ Próxima actualización en {interval}s (iteración {iteration})...\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            elapsed = time.time() - self.start_time
            print(f"\n\n⏹️  Monitoreo detenido después de {self.format_time(elapsed)}")


if __name__ == "__main__":
    monitor = TrainingMonitor()
    print("🚀 Iniciando monitor en vivo...")
    print("📊 Presiona Ctrl+C para detener\n")
    monitor.monitor_loop(interval=15)
