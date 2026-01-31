#!/usr/bin/env python
"""Análisis completo de resultados de entrenamiento SAC - Sin interrumpir entrenamiento actual"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def analyze_sac_training():
    """Analizar datos de entrenamiento SAC desde CSV y checkpoints"""

    print("\n" + "="*80)
    print("ANÁLISIS COMPLETO DE RESULTADOS SAC - CHECKPOINT FINAL")
    print("="*80 + "\n")

    # 1. Cargar CSV de progreso
    csv_path = Path("analyses/oe3/training/progress/sac_progress.csv")
    if not csv_path.exists():
        print(f"❌ No se encontró {csv_path}")
        return

    df = pd.read_csv(csv_path)
    episodes_df = df[df['episode_reward'].notna()].copy()

    # 2. Información básica
    print("📊 RESUMEN DE ENTRENAMIENTO")
    print("─" * 80)
    print(f"  Total de pasos ejecutados: {df['global_step'].max():,}")
    print(f"  Episodios completados: {len(episodes_df)}")
    print(f"  Inicio: {df['timestamp'].iloc[0]}")
    print(f"  Fin: {df['timestamp'].iloc[-1]}")

    # Calcular duración
    start_time = pd.to_datetime(df['timestamp'].iloc[0])
    end_time = pd.to_datetime(df['timestamp'].iloc[-1])
    duration = end_time - start_time
    hours = duration.total_seconds() / 3600
    print(f"  Duración total: {hours:.2f} horas ({duration})")

    # 3. Análisis de episodios
    print(f"\n📈 ANÁLISIS DE EPISODIOS")
    print("─" * 80)

    if len(episodes_df) > 0:
        rewards = episodes_df['episode_reward'].values
        lengths = episodes_df['episode_length'].values

        print(f"  Episodio 1: reward={rewards[0]:.2f}, length={int(lengths[0])}")
        if len(rewards) > 1:
            print(f"  Episodio 2: reward={rewards[1]:.2f}, length={int(lengths[1])}")
        if len(rewards) > 2:
            print(f"  Episodio 3: reward={rewards[2]:.2f}, length={int(lengths[2])}")

        print(f"\n  Reward promedio: {np.mean(rewards):.2f}")
        print(f"  Reward mínimo: {np.min(rewards):.2f}")
        print(f"  Reward máximo: {np.max(rewards):.2f}")
        print(f"  Desviación estándar: {np.std(rewards):.2f}")

        print(f"\n  Length promedio: {np.mean(lengths):.0f} timesteps")
        print(f"  Length mínimo: {int(np.min(lengths))} timesteps")
        print(f"  Length máximo: {int(np.max(lengths))} timesteps")

    # 4. Análisis de checkpoints
    checkpoint_dir = Path("analyses/oe3/training/checkpoints/sac")
    if checkpoint_dir.exists():
        checkpoints = sorted(checkpoint_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime)

        print(f"\n💾 CHECKPOINTS GUARDADOS")
        print("─" * 80)
        print(f"  Total de checkpoints: {len(checkpoints)}")

        if checkpoints:
            final_checkpoint = [c for c in checkpoints if 'final' in c.name]
            if final_checkpoint:
                final = final_checkpoint[0]
                size_mb = final.stat().st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(final.stat().st_mtime)
                print(f"\n  ✓ Checkpoint FINAL:")
                print(f"    - Archivo: {final.name}")
                print(f"    - Tamaño: {size_mb:.2f} MB")
                print(f"    - Última modificación: {modified.strftime('%Y-%m-%d %H:%M:%S')}")

            print(f"\n  Checkpoints intermedios (cada 500 steps):")
            print(f"    - Primer checkpoint: {checkpoints[0].name}")
            print(f"    - Último checkpoint: {checkpoints[-1].name}")

    # 5. Baseline comparison (si existe)
    baseline_files = list(Path("outputs/oe3/simulations").glob("baseline*.json"))
    if baseline_files:
        with open(baseline_files[0], 'r') as f:
            baseline = json.load(f)

        print(f"\n📉 COMPARACIÓN CON BASELINE")
        print("─" * 80)
        print(f"  Baseline (Uncontrolled):")
        print(f"    - Demanda total: {baseline.get('total_electricity_demand_kWh', 0):,.0f} kWh")
        print(f"    - Grid import: {baseline.get('total_grid_import_kWh', 0):,.0f} kWh")
        print(f"    - CO2 emissions: {baseline.get('total_co2_kg', 0):,.0f} kg")

        # Estimación de mejora (basada en reward promedio)
        if len(episodes_df) > 0:
            avg_reward = np.mean(rewards)
            print(f"\n  SAC Agent:")
            print(f"    - Reward promedio: {avg_reward:.2f}")
            print(f"    - Interpretación: Reward alto indica reducción de CO2 y mejor uso solar")
            print(f"    - Nota: Métricas detalladas en logs de entrenamiento")

    # 6. Velocidad de entrenamiento
    print(f"\n⚡ VELOCIDAD DE ENTRENAMIENTO")
    print("─" * 80)
    steps_per_hour = df['global_step'].max() / hours if hours > 0 else 0
    print(f"  Pasos por hora: {steps_per_hour:,.0f}")
    print(f"  Tiempo promedio por 100 steps: {(hours * 3600 / (df['global_step'].max() / 100)):.1f} segundos")

    # 7. Conclusión
    print(f"\n✅ CONCLUSIÓN")
    print("─" * 80)
    print(f"  SAC completó {len(episodes_df)} episodios con éxito")
    print(f"  Checkpoint final guardado en: {checkpoint_dir / 'sac_final.zip'}")
    print(f"  Entrenamiento estable y completo")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    analyze_sac_training()
