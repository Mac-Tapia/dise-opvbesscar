from __future__ import annotations

import json
import time
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TrainingMonitor:
    """Monitor de entrenamiento en tiempo real con gráficas"""

    def __init__(self, output_dir: Path, update_interval: int = 30):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.update_interval = update_interval
        self.sac_progress_file = Path("analyses/oe3/training/progress/sac_progress.csv")
        self.ppo_progress_file = Path("analyses/oe3/training/progress/ppo_progress.csv")

    def load_progress(self, agent: str) -> pd.DataFrame | None:
        """Carga el archivo de progreso del agente"""
        progress_file = self.sac_progress_file if agent.lower() == "sac" else self.ppo_progress_file

        if not progress_file.exists():
            return None

        try:
            df = pd.read_csv(progress_file)
            return df
        except Exception as e:
            logger.error(f"Error cargando progreso de {agent}: {e}")
            return None

    def plot_training_metrics(self, agent: str):
        """Crea gráficas de entrenamiento para un agente"""
        df = self.load_progress(agent)

        if df is None or len(df) == 0:
            print(f"⚠️  Sin datos de progreso para {agent}")
            return

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'{agent} - Métricas de Entrenamiento', fontsize=16, fontweight='bold')

        # Subplot 1: Reward promedio
        if 'episode_reward_mean' in df.columns:
            axes[0, 0].plot(df.index, df['episode_reward_mean'], 'b-', linewidth=2, label='Reward Mean')
            axes[0, 0].fill_between(df.index, df['episode_reward_mean'], alpha=0.3)
            axes[0, 0].set_title('Reward Promedio por Episodio', fontweight='bold')
            axes[0, 0].set_xlabel('Episodio')
            axes[0, 0].set_ylabel('Reward')
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].legend()

        # Subplot 2: Loss (Actor y Critic)
        if 'actor_loss' in df.columns and 'critic_loss' in df.columns:
            ax2 = axes[0, 1]
            ax2.plot(df.index, df['actor_loss'], 'r-', linewidth=2, label='Actor Loss', alpha=0.7)
            ax2.plot(df.index, df['critic_loss'], 'g-', linewidth=2, label='Critic Loss', alpha=0.7)
            ax2.set_title('Loss del Actor y Crítico', fontweight='bold')
            ax2.set_xlabel('Episodio')
            ax2.set_ylabel('Loss')
            ax2.grid(True, alpha=0.3)
            ax2.legend()

        # Subplot 3: Métricas de CO2 y Solar
        if 'total_co2_kg' in df.columns and 'total_solar_kwh' in df.columns:
            ax3 = axes[1, 0]
            ax3_twin = ax3.twinx()

            line1 = ax3.plot(df.index, df['total_co2_kg'], 'r-', linewidth=2, label='CO2 (kg)')
            line2 = ax3_twin.plot(df.index, df['total_solar_kwh'], 'y-', linewidth=2, label='Solar (kWh)')

            ax3.set_title('CO2 vs Solar Self-Consumption', fontweight='bold')
            ax3.set_xlabel('Episodio')
            ax3.set_ylabel('CO2 (kg)', color='r')
            ax3_twin.set_ylabel('Solar (kWh)', color='y')
            ax3.tick_params(axis='y', labelcolor='r')
            ax3_twin.tick_params(axis='y', labelcolor='y')
            ax3.grid(True, alpha=0.3)

            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            ax3.legend(lines, labels, loc='upper left')

        # Subplot 4: Steps/Timesteps acumulados
        if 'total_timesteps' in df.columns:
            axes[1, 1].plot(df.index, df['total_timesteps'], 'purple', linewidth=2, marker='o', markersize=4)
            axes[1, 1].set_title('Timesteps Acumulados', fontweight='bold')
            axes[1, 1].set_xlabel('Episodio')
            axes[1, 1].set_ylabel('Timesteps')
            axes[1, 1].grid(True, alpha=0.3)

            # Anotación del último valor
            last_ts = df['total_timesteps'].iloc[-1]
            axes[1, 1].text(0.98, 0.05, f'Total: {last_ts:,.0f} steps',
                           transform=axes[1, 1].transAxes,
                           horizontalalignment='right', verticalalignment='bottom',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()

        # Guardar figura
        output_file = self.output_dir / f"{agent.lower()}_training_metrics.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"✓ Gráfica guardada: {output_file}")
        plt.close()

    def plot_comparison(self):
        """Compara métricas de SAC vs PPO"""
        sac_df = self.load_progress("SAC")
        ppo_df = self.load_progress("PPO")

        if sac_df is None or ppo_df is None:
            print("⚠️  No hay suficientes datos para comparación")
            return

        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        fig.suptitle('SAC vs PPO - Comparación de Entrenamiento', fontsize=16, fontweight='bold')

        # Comparación de Reward
        if 'episode_reward_mean' in sac_df.columns and 'episode_reward_mean' in ppo_df.columns:
            axes[0].plot(sac_df.index, sac_df['episode_reward_mean'], 'b-', linewidth=2, label='SAC', marker='o')
            axes[0].plot(ppo_df.index, ppo_df['episode_reward_mean'], 'g-', linewidth=2, label='PPO', marker='s')
            axes[0].set_title('Reward Promedio', fontweight='bold')
            axes[0].set_xlabel('Episodio')
            axes[0].set_ylabel('Reward')
            axes[0].grid(True, alpha=0.3)
            axes[0].legend()

        # Comparación de CO2
        if 'total_co2_kg' in sac_df.columns and 'total_co2_kg' in ppo_df.columns:
            axes[1].plot(sac_df.index, sac_df['total_co2_kg'], 'b-', linewidth=2, label='SAC', marker='o')
            axes[1].plot(ppo_df.index, ppo_df['total_co2_kg'], 'g-', linewidth=2, label='PPO', marker='s')
            axes[1].set_title('Emisiones CO2 por Episodio', fontweight='bold')
            axes[1].set_xlabel('Episodio')
            axes[1].set_ylabel('CO2 (kg)')
            axes[1].grid(True, alpha=0.3)
            axes[1].legend()

        plt.tight_layout()

        output_file = self.output_dir / "sac_vs_ppo_comparison.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"✓ Gráfica de comparación guardada: {output_file}")
        plt.close()

    def print_summary(self, agent: str):
        """Imprime resumen de métricas del agente"""
        df = self.load_progress(agent)

        if df is None or len(df) == 0:
            return

        print(f"\n{'='*80}")
        print(f"📊 RESUMEN {agent.upper()}")
        print(f"{'='*80}")
        print(f"Episodios completados: {len(df)}")

        if 'episode_reward_mean' in df.columns:
            print(f"Reward Promedio (actual): {df['episode_reward_mean'].iloc[-1]:.4f}")
            print(f"Reward Máximo: {df['episode_reward_mean'].max():.4f}")
            print(f"Reward Mínimo: {df['episode_reward_mean'].min():.4f}")

        if 'total_co2_kg' in df.columns:
            print(f"\nCO2 (actual): {df['total_co2_kg'].iloc[-1]:.2f} kg")
            print(f"CO2 Mínimo: {df['total_co2_kg'].min():.2f} kg")
            print(f"Reducción CO2: {((df['total_co2_kg'].iloc[0] - df['total_co2_kg'].iloc[-1]) / df['total_co2_kg'].iloc[0] * 100):.1f}%")

        if 'total_solar_kwh' in df.columns:
            print(f"\nSolar Self-Consumption (actual): {df['total_solar_kwh'].iloc[-1]:.2f} kWh")
            print(f"Solar Máximo: {df['total_solar_kwh'].max():.2f} kWh")

        if 'total_timesteps' in df.columns:
            print(f"\nTimesteps totales: {df['total_timesteps'].iloc[-1]:,.0f}")

        print(f"{'='*80}\n")


def main():
    """Script principal de monitoreo"""
    import argparse

    ap = argparse.ArgumentParser(description="Monitor de entrenamiento SAC/PPO")
    ap.add_argument("--output", default="outputs/oe3/training_monitoring", help="Directorio de salida")
    ap.add_argument("--agents", nargs="+", default=["sac", "ppo"], help="Agentes a monitorear")
    args = ap.parse_args()

    monitor = TrainingMonitor(Path(args.output))

    print("\n🎯 Monitor de Entrenamiento Iniciado")
    print(f"📁 Salida: {monitor.output_dir}")
    print(f"🤖 Agentes monitoreados: {', '.join(args.agents)}\n")

    # Generar gráficas iniciales
    for agent in args.agents:
        print(f"\n📊 Generando gráficas para {agent.upper()}...")
        monitor.plot_training_metrics(agent.upper())
        monitor.print_summary(agent.upper())

    # Comparación
    if len(args.agents) >= 2:
        print("\n📊 Generando gráfica de comparación...")
        monitor.plot_comparison()

    print("\n✅ Monitoreo completado")


if __name__ == "__main__":
    main()
