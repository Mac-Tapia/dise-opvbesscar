#!/usr/bin/env python3
"""
Entrenamiento con 5 episodios + Guardado de Checkpoints + Agregación de Series
================================================================================
- 5 episodios reales con 8,760 timesteps cada uno
- Guardado de checkpoints después de cada episodio
- Agregación de métricas (CO₂, reward, energía) por timestep
- Exportación de series para análisis
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

# Agregar src al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Importar librerías
try:
    from citylearn.citylearn import CityLearnEnv
    import torch
    print("✅ CityLearn y Torch importados exitosamente")
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    sys.exit(1)


def setup_paths():
    """Crear estructura de directorios para checkpoints y logs"""
    checkpoints_dir = ROOT / "outputs" / "checkpoints" / "training_session"
    logs_dir = ROOT / "analyses" / "training_logs"
    series_dir = ROOT / "analyses" / "time_series"

    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    series_dir.mkdir(parents=True, exist_ok=True)

    return {
        "checkpoints": checkpoints_dir,
        "logs": logs_dir,
        "series": series_dir,
    }


def train_5_episodes_with_checkpoints():
    """Entrenar 5 episodios con checkpoints y series agregadas"""

    print("\n" + "="*80)
    print("🎯 ENTRENAMIENTO: 5 EPISODIOS + CHECKPOINTS + SERIES AGREGADAS")
    print("="*80)

    # Setup
    paths = setup_paths()
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n📁 Sesión: {session_id}")
    print(f"   Checkpoints: {paths['checkpoints']}")
    print(f"   Logs:        {paths['logs']}")
    print(f"   Series:      {paths['series']}")

    # 1. Cargar dataset
    dataset_path = ROOT / "data" / "processed" / "citylearn" / "iquitos_ev_mall"
    schema_path = dataset_path / "schema.json"

    if not schema_path.exists():
        print(f"❌ Dataset no encontrado: {schema_path}")
        return False

    print(f"\n📊 Cargando dataset: {schema_path}")
    env = CityLearnEnv(str(schema_path))
    print(f"✅ Ambiente CityLearn creado")
    print(f"   • Timesteps/episodio: {env.time_steps}")
    print(f"   • Edificios: {len(env.buildings) if hasattr(env, 'buildings') else 1}")

    # 2. Verificar GPU
    gpu_available = torch.cuda.is_available()
    device = "cuda" if gpu_available else "cpu"
    print(f"\n🎮 Device: {device.upper()}")
    if gpu_available:
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        props = torch.cuda.get_device_properties(0)
        print(f"   Memory: {props.total_memory / 1e9:.1f} GB")

    # 3. Contenedores para agregación de datos
    all_episodes_data = []
    all_timestep_series = []
    all_co2_series = []
    all_reward_series = []
    all_energy_series = []

    # 4. Entrenar 5 episodios
    num_episodes = 5
    session_start = time.time()

    for episode_num in range(1, num_episodes + 1):
        print(f"\n{'='*80}")
        print(f"📈 EPISODIO {episode_num}/{num_episodes}")
        print(f"{'='*80}")

        episode_start = time.time()

        # Reset ambiente
        obs, info = env.reset()
        print(f"   Obs shape: {np.array(obs).shape if hasattr(obs, '__len__') else 'scalar'}")

        # Contenedores para este episodio
        episode_rewards = []
        episode_co2 = []
        episode_energy_in = []
        episode_energy_out = []
        episode_actions = []
        episode_timesteps = []

        done = False
        step = 0
        episode_total_reward = 0.0

        print(f"\n   Iterando {env.time_steps} timesteps...")
        step_start = time.time()

        while not done and step < env.time_steps:
            # Acción (demo: random; en producción usar SAC/PPO/A2C)
            # Las acciones en CityLearn v2 son arrays
            if hasattr(env.action_space, 'sample'):
                action = env.action_space.sample()
            else:
                # action_space puede ser una lista de espacios
                try:
                    action = [space.sample() if hasattr(space, 'sample') else 0.0
                             for space in env.action_space]
                except:
                    action = [0.0] * len(env.action_space) if isinstance(env.action_space, list) else 0.0

            episode_actions.append(action)

            # Paso del ambiente
            obs, reward, done, truncated, info = env.step(action)

            # Procesar recompensa
            if isinstance(reward, (list, np.ndarray)):
                reward_scalar = float(np.sum(reward))
            else:
                reward_scalar = float(reward)

            episode_rewards.append(reward_scalar)
            episode_total_reward += reward_scalar

            # Extraer CO₂ e energía del info (si disponible)
            co2 = info.get("co2", 0.0) if isinstance(info, dict) else 0.0
            energy_in = info.get("grid_import_kWh", 0.0) if isinstance(info, dict) else 0.0
            energy_out = info.get("solar_export_kWh", 0.0) if isinstance(info, dict) else 0.0

            episode_co2.append(float(co2))
            episode_energy_in.append(float(energy_in))
            episode_energy_out.append(float(energy_out))
            episode_timesteps.append(step)

            # Mostrar progreso
            if (step + 1) % 1000 == 0:
                elapsed = time.time() - step_start
                rate = (step + 1) / elapsed
                print(f"      [{step+1:5d}/{env.time_steps}] ({(step+1)/env.time_steps*100:5.1f}%) | "
                      f"Speed: {rate:7.0f} steps/s | Reward: {episode_total_reward:10.2f}")

            step += 1

        episode_time = time.time() - episode_start

        # 5. Agregar datos del episodio
        episode_data = {
            "episode": episode_num,
            "duration_seconds": episode_time,
            "timesteps_completed": step,
            "total_reward": float(episode_total_reward),
            "mean_reward": float(np.mean(episode_rewards)),
            "min_reward": float(np.min(episode_rewards)),
            "max_reward": float(np.max(episode_rewards)),
            "total_co2_kg": float(np.sum(episode_co2)),
            "mean_co2_per_step": float(np.mean(episode_co2)) if episode_co2 else 0.0,
            "total_energy_import_kwh": float(np.sum(episode_energy_in)),
            "total_energy_export_kwh": float(np.sum(episode_energy_out)),
        }

        all_episodes_data.append(episode_data)

        # 6. Guardar series para este episodio
        episode_series = pd.DataFrame({
            "episode": [episode_num] * len(episode_timesteps),
            "timestep": episode_timesteps,
            "reward": episode_rewards,
            "co2_kg": episode_co2,
            "energy_import_kwh": episode_energy_in,
            "energy_export_kwh": episode_energy_out,
        })

        all_timestep_series.append(episode_series)
        all_co2_series.extend(episode_co2)
        all_reward_series.extend(episode_rewards)
        all_energy_series.extend(episode_energy_in)

        # 7. Guardar checkpoint del episodio
        checkpoint_file = paths["checkpoints"] / f"episode_{episode_num:02d}_checkpoint.json"
        with open(checkpoint_file, "w") as f:
            json.dump(episode_data, f, indent=2)
        print(f"\n   ✅ Checkpoint guardado: {checkpoint_file.name}")

        # 8. Resumen del episodio
        print(f"\n   📊 RESUMEN EPISODIO {episode_num}:")
        print(f"      Duración:           {episode_time:.2f}s")
        print(f"      Timesteps:          {step:,}/{env.time_steps}")
        print(f"      Reward total:       {episode_total_reward:10.2f}")
        print(f"      Reward promedio:    {np.mean(episode_rewards):10.2f}")
        print(f"      CO₂ total:          {np.sum(episode_co2):10.2f} kg")
        print(f"      Energía importada:  {np.sum(episode_energy_in):10.2f} kWh")
        print(f"      Energía exportada:  {np.sum(episode_energy_out):10.2f} kWh")

    # 9. Agregación final
    print(f"\n{'='*80}")
    print("📦 AGREGACIÓN DE SERIES Y EXPORTACIÓN")
    print(f"{'='*80}")

    # DataFrame de episodios
    episodes_df = pd.DataFrame(all_episodes_data)

    # DataFrame de timesteps
    if all_timestep_series:
        timesteps_df = pd.concat(all_timestep_series, ignore_index=True)
    else:
        timesteps_df = pd.DataFrame()

    # Guardar CSVs
    episodes_csv = paths["logs"] / f"{session_id}_episodes_summary.csv"
    timesteps_csv = paths["series"] / f"{session_id}_timestep_series.csv"

    episodes_df.to_csv(episodes_csv, index=False)
    if not timesteps_df.empty:
        timesteps_df.to_csv(timesteps_csv, index=False)

    print(f"\n   ✅ Resumen de episodios: {episodes_csv.name}")
    print(f"   ✅ Serie de timesteps:   {timesteps_csv.name}")

    # Guardar JSON de sesión
    session_summary = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "total_episodes": num_episodes,
        "total_duration_seconds": time.time() - session_start,
        "device": device,
        "episodes": all_episodes_data,
        "statistics": {
            "mean_total_reward": float(np.mean([e["total_reward"] for e in all_episodes_data])),
            "mean_co2_kg": float(np.mean([e["total_co2_kg"] for e in all_episodes_data])),
            "mean_energy_import_kwh": float(np.mean([e["total_energy_import_kwh"] for e in all_episodes_data])),
        }
    }

    session_json = paths["logs"] / f"{session_id}_session_summary.json"
    with open(session_json, "w") as f:
        json.dump(session_summary, f, indent=2)

    print(f"   ✅ Resumen de sesión:    {session_json.name}")

    # 10. Imprimir resumen final
    print(f"\n{'='*80}")
    print("📊 RESUMEN FINAL")
    print(f"{'='*80}")
    print(f"\n   Sesión:              {session_id}")
    print(f"   Duración total:      {session_summary['total_duration_seconds']:.1f}s")
    print(f"   Episodios:           {num_episodes}")
    print(f"   Device:              {device.upper()}")
    print(f"\n   Reward promedio:     {session_summary['statistics']['mean_total_reward']:.2f}")
    print(f"   CO₂ promedio:        {session_summary['statistics']['mean_co2_kg']:.2f} kg")
    print(f"   Energía importada:   {session_summary['statistics']['mean_energy_import_kwh']:.2f} kWh")

    print(f"\n   📁 Archivos guardados:")
    print(f"      • Checkpoints:   {paths['checkpoints']}")
    print(f"      • Logs:          {paths['logs']}")
    print(f"      • Series:        {paths['series']}")

    print(f"\n✅ ENTRENAMIENTO COMPLETADO\n")

    return True


if __name__ == "__main__":
    success = train_5_episodes_with_checkpoints()
    sys.exit(0 if success else 1)
