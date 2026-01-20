#!/usr/bin/env python3
"""
ENTRENAMIENTO ROBUSTO DE AGENTES RL CON GPU
============================================
Usa datos REALES de los 128 cargadores (112 Motos + 16 Mototaxis)
Entrena SAC, PPO y A2C en secuencia con checkpoints agregables

Ejecución: python train_gpu_robusto.py

Autor: Proyecto Iquitos PV BESS EV
Fecha: 2026-01-18
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import logging
import json

# Configuración de encoding y GPU
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'  # Async para mejor rendimiento

# Configurar paths
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

def banner(msg: str, char: str = "="):
    """Imprime banner decorado."""
    print(f"\n{char * 80}")
    print(f" {msg}")
    print(f"{char * 80}\n")

def check_gpu():
    """Verifica disponibilidad de GPU y muestra información."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
            logger.info(f"GPU: {gpu_name} ({gpu_mem:.1f} GB)")
            return "cuda"
        else:
            logger.warning("CUDA no disponible, usando CPU")
            return "cpu"
    except ImportError:
        logger.error("PyTorch no instalado")
        return "cpu"

def verify_data():
    """Verifica que los datos de los 128 cargadores existan."""
    chargers_file = ROOT_DIR / "data" / "interim" / "oe2" / "chargers" / "individual_chargers.json"
    
    if not chargers_file.exists():
        logger.error(f"No existe: {chargers_file}")
        return None
    
    with open(chargers_file, 'r') as f:
        chargers = json.load(f)
    
    motos = len([c for c in chargers if c.get('playa') == 'Playa_Motos'])
    taxis = len([c for c in chargers if c.get('playa') == 'Playa_Mototaxis'])
    
    if motos != 112 or taxis != 16:
        logger.error(f"Datos incorrectos: {motos} motos, {taxis} mototaxis (esperado: 112, 16)")
        return None
    
    logger.info(f"✓ Datos verificados: {motos} Motos + {taxis} Mototaxis = {len(chargers)} cargadores")
    return chargers

def build_dataset_if_needed(cfg, rp):
    """Construye el dataset CityLearn si no existe."""
    from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
    
    dataset_name = cfg["oe3"]["dataset"]["name"]
    processed_dir = rp.processed_dir / "citylearn" / dataset_name
    schema_pv = processed_dir / "schema_pv_bess.json"
    
    if schema_pv.exists():
        logger.info(f"✓ Dataset existe: {schema_pv}")
        return processed_dir
    
    logger.info("Construyendo dataset CityLearn...")
    result = build_citylearn_dataset(
        cfg=cfg,
        raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    logger.info(f"✓ Dataset construido: {result.dataset_dir}")
    return result.dataset_dir

def apply_patches():
    """Aplica parches necesarios a CityLearn."""
    try:
        from citylearn_monkeypatch import apply_citylearn_patches
        apply_citylearn_patches()
        logger.info("✓ Parches de CityLearn aplicados")
        return True
    except ImportError:
        logger.warning("citylearn_monkeypatch no encontrado, continuando sin parches")
        return False

def train_agent(
    agent_name: str,
    schema_path: Path,
    training_dir: Path,
    carbon_intensity: float,
    seconds_per_step: int,
    device: str,
    episodes: int = 5,
    resume: bool = True,
):
    """
    Entrena un agente con la función simulate() existente.
    
    Args:
        agent_name: SAC, PPO o A2C
        schema_path: Path al schema CityLearn
        training_dir: Directorio para checkpoints
        carbon_intensity: Factor CO2 kg/kWh
        seconds_per_step: Segundos por timestep
        device: cuda o cpu
        episodes: Número de episodios a entrenar
        resume: Si continuar desde checkpoint existente
    """
    from iquitos_citylearn.oe3.simulate import simulate
    
    out_dir = training_dir / agent_name.lower()
    checkpoint_dir = out_dir / "checkpoints"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Calcular timesteps (8760 pasos por episodio = 1 año horario)
    timesteps = episodes * 8760
    
    logger.info(f"Entrenando {agent_name}: {episodes} episodios ({timesteps:,} pasos)")
    logger.info(f"  Dispositivo: {device}")
    logger.info(f"  Checkpoints: {checkpoint_dir}")
    logger.info(f"  Resume: {resume}")
    
    start_time = datetime.now()
    
    try:
        # Parámetros comunes
        common_params = {
            "schema_path": schema_path,
            "agent_name": agent_name,
            "out_dir": out_dir,
            "training_dir": checkpoint_dir,
            "carbon_intensity_kg_per_kwh": carbon_intensity,
            "seconds_per_time_step": seconds_per_step,
            "use_multi_objective": True,
            "multi_objective_priority": "balanced",
            "deterministic_eval": True,
            "seed": 42,
        }
        
        # Parámetros específicos por agente
        if agent_name.upper() == "SAC":
            result = simulate(
                **common_params,
                sac_episodes=episodes,
                sac_batch_size=256,
                sac_log_interval=500,
                sac_use_amp=True,
                sac_device=device,
                sac_checkpoint_freq_steps=1000,
                sac_resume_checkpoints=resume,
            )
        elif agent_name.upper() == "PPO":
            result = simulate(
                **common_params,
                ppo_timesteps=timesteps,
                ppo_n_steps=2048,
                ppo_batch_size=256,
                ppo_log_interval=500,
                ppo_device=device,
                ppo_checkpoint_freq_steps=1000,
                ppo_resume_checkpoints=resume,
                ppo_target_kl=0.02,
                ppo_kl_adaptive=True,
            )
        elif agent_name.upper() == "A2C":
            result = simulate(
                **common_params,
                a2c_timesteps=timesteps,
                a2c_n_steps=512,
                a2c_log_interval=500,
                a2c_learning_rate=3e-4,
                a2c_entropy_coef=0.01,
                a2c_device=device,
                a2c_checkpoint_freq_steps=1000,
                a2c_resume_checkpoints=resume,
            )
        else:
            raise ValueError(f"Agente no soportado: {agent_name}")
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✓ {agent_name} completado en {elapsed/60:.1f} minutos")
        logger.info(f"  CO2: {result.carbon_kg:.2f} kg")
        logger.info(f"  Grid neto: {result.net_grid_kwh:.2f} kWh")
        logger.info(f"  EV carga: {result.ev_charging_kwh:.2f} kWh")
        
        return {
            "agent": agent_name,
            "success": True,
            "carbon_kg": result.carbon_kg,
            "net_grid_kwh": result.net_grid_kwh,
            "ev_charging_kwh": result.ev_charging_kwh,
            "elapsed_minutes": elapsed / 60,
        }
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"✗ {agent_name} falló: {type(e).__name__}: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        
        return {
            "agent": agent_name,
            "success": False,
            "error": str(e)[:200],
            "elapsed_minutes": elapsed / 60,
        }

def main():
    """Función principal de entrenamiento."""
    banner("ENTRENAMIENTO ROBUSTO - GPU MÁXIMO", "=")
    print(f"Inicio: {datetime.now().isoformat()}")
    print(f"Directorio: {ROOT_DIR}\n")
    
    # 1. Verificar GPU
    banner("1. VERIFICACIÓN DE GPU", "-")
    device = check_gpu()
    
    # 2. Verificar datos
    banner("2. VERIFICACIÓN DE DATOS (128 CARGADORES)", "-")
    chargers = verify_data()
    if chargers is None:
        logger.error("No se pueden verificar los datos. Abortando.")
        sys.exit(1)
    
    # 3. Cargar configuración
    banner("3. CARGA DE CONFIGURACIÓN", "-")
    try:
        from scripts._common import load_all
        cfg, rp = load_all("configs/default.yaml")
        logger.info("✓ Configuración cargada")
    except Exception as e:
        logger.error(f"Error cargando configuración: {e}")
        sys.exit(1)
    
    # 4. Aplicar parches
    banner("4. APLICACIÓN DE PARCHES", "-")
    apply_patches()
    
    # 5. Verificar/construir dataset
    banner("5. VERIFICACIÓN DE DATASET", "-")
    dataset_dir = build_dataset_if_needed(cfg, rp)
    schema_pv = dataset_dir / "schema_pv_bess.json"
    
    if not schema_pv.exists():
        logger.error(f"Schema no encontrado: {schema_pv}")
        sys.exit(1)
    logger.info(f"✓ Schema: {schema_pv}")
    
    # 6. Parámetros de entrenamiento
    banner("6. CONFIGURACIÓN DE ENTRENAMIENTO", "-")
    carbon_intensity = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
    seconds_per_step = int(cfg["project"]["seconds_per_time_step"])
    
    training_dir = rp.analyses_dir / "oe3" / "training" / "gpu_robusto"
    training_dir.mkdir(parents=True, exist_ok=True)
    
    # CONFIGURACIÓN DE EPISODIOS
    EPISODES = 5  # Episodios por agente (ajustar según necesidad)
    RESUME = True  # Continuar desde checkpoints existentes
    
    logger.info(f"Episodios por agente: {EPISODES}")
    logger.info(f"Timesteps por episodio: 8,760")
    logger.info(f"Total por agente: {EPISODES * 8760:,} pasos")
    logger.info(f"Dispositivo: {device}")
    logger.info(f"Directorio: {training_dir}")
    logger.info(f"Continuar desde checkpoint: {RESUME}")
    
    # 7. Entrenar agentes
    results = {}
    agents = ["SAC", "PPO", "A2C"]
    
    for i, agent in enumerate(agents, 1):
        banner(f"7.{i}. ENTRENAMIENTO {agent} ({i}/{len(agents)})", "=")
        
        result = train_agent(
            agent_name=agent,
            schema_path=schema_pv,
            training_dir=training_dir,
            carbon_intensity=carbon_intensity,
            seconds_per_step=seconds_per_step,
            device=device,
            episodes=EPISODES,
            resume=RESUME,
        )
        results[agent] = result
    
    # 8. Resumen final
    banner("8. RESUMEN FINAL", "=")
    
    success_count = sum(1 for r in results.values() if r["success"])
    
    print(f"\n{'Agente':<8} {'Estado':<10} {'CO2 (kg)':<12} {'Tiempo (min)':<12}")
    print("-" * 50)
    
    for agent, r in results.items():
        if r["success"]:
            print(f"{agent:<8} {'✓ OK':<10} {r['carbon_kg']:<12.2f} {r['elapsed_minutes']:<12.1f}")
        else:
            print(f"{agent:<8} {'✗ FAIL':<10} {'N/A':<12} {r['elapsed_minutes']:<12.1f}")
    
    print("-" * 50)
    print(f"Éxito: {success_count}/{len(agents)} agentes\n")
    
    # Guardar resumen
    summary_file = training_dir / "TRAINING_SUMMARY.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "device": device,
            "episodes_per_agent": EPISODES,
            "resume_enabled": RESUME,
            "results": results,
        }, f, indent=2)
    
    logger.info(f"Resumen guardado: {summary_file}")
    
    print(f"\nFin: {datetime.now().isoformat()}")
    
    sys.exit(0 if success_count == len(agents) else 1)

if __name__ == "__main__":
    main()
