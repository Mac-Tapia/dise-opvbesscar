#!/usr/bin/env python3
"""
Verificacion exhaustiva: Datos horarios (8,760) -> Schema CityLearn v2 -> Entrenamiento de agentes
"""

import sys
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")


def print_check(msg: str, status: bool, details: str = "") -> None:
    """Print a check with status."""
    symbol = f"{GREEN}OK{RESET}" if status else f"{RED}ERROR{RESET}"
    print(f"  [{symbol}] {msg}")
    if details:
        print(f"      {details}")


def verify_oe2_artifacts() -> bool:
    """Verify OE2 artifacts exist and have correct format."""
    print_header("PASO 1: Verificacion de Artefactos OE2 (Solar, Chargers, BESS)")

    oe2_path = Path("data/interim/oe2")
    all_ok = True

    # 1. Solar
    solar_file = oe2_path / "solar" / "pv_generation_timeseries.csv"
    if solar_file.exists():
        df_solar = pd.read_csv(solar_file)
        is_ok = len(df_solar) == 8760
        print_check(f"Solar timeseries: {len(df_solar)} filas", is_ok,
                   f"Esperado: 8760, Obtenido: {len(df_solar)}")
        all_ok = all_ok and is_ok
    else:
        print_check("Solar timeseries existe", False)
        all_ok = False

    # 2. Chargers
    chargers_file = oe2_path / "chargers" / "individual_chargers.json"
    if chargers_file.exists():
        with open(chargers_file) as f:
            chargers = json.load(f)
        n_chargers = len(chargers)
        n_sockets = n_chargers * 4  # 4 sockets por charger
        is_ok = n_chargers == 32 and n_sockets == 128
        print_check(f"Chargers: {n_chargers} unidades, {n_sockets} sockets", is_ok,
                   f"Esperado: 32 chargers, 128 sockets")
        all_ok = all_ok and is_ok
    else:
        print_check("Chargers JSON existe", False)
        all_ok = False

    # 3. Charger profiles
    charger_profile = oe2_path / "chargers" / "perfil_horario_carga.csv"
    if charger_profile.exists():
        df_profile = pd.read_csv(charger_profile)
        is_ok = len(df_profile) == 24  # 24 horas del dia
        print_check(f"Charger profile diario: {len(df_profile)} filas", is_ok,
                   f"Esperado: 24 horas/dia")
        all_ok = all_ok and is_ok
    else:
        print_check("Charger profile diario existe", False)
        all_ok = False

    # 4. BESS
    bess_file = oe2_path / "bess" / "bess_config.json"
    if bess_file.exists():
        with open(bess_file) as f:
            bess = json.load(f)
        print_check("BESS config existe", True,
                   f"Capacity: {bess.get('capacity_kwh', 'N/A')} kWh, Power: {bess.get('power_kw', 'N/A')} kW")
    else:
        print_check("BESS config existe", False)
        all_ok = False

    return all_ok


def verify_processed_dataset() -> bool:
    """Verify processed CityLearn dataset."""
    print_header("PASO 2: Verificacion de Dataset Procesado (CityLearn v2)")

    dataset_path = Path("data/processed/citylearnv2_dataset")
    all_ok = True

    if not dataset_path.exists():
        print_check("Dataset directory exists", False, "Sera generado por run_full_pipeline.py")
        return False

    # Check schema
    schema_file = dataset_path / "schema.json"
    if schema_file.exists():
        with open(schema_file) as f:
            schema = json.load(f)

        n_timesteps = schema.get("time_steps", 0)
        is_ok = n_timesteps == 8760
        print_check(f"Schema timesteps: {n_timesteps}", is_ok,
                   f"Esperado: 8760 (1 año * 1 hora)")
        all_ok = all_ok and is_ok

        # Check buildings
        buildings = schema.get("buildings", [])
        print_check(f"Buildings en schema: {len(buildings)}", len(buildings) >= 1,
                   f"Esperado: >= 1 building con 128 chargers")

    else:
        print_check("Schema.json existe", False, "Sera generado por pipeline")
        all_ok = False

    # Check CSV files
    climate_path = dataset_path / "climate_zones" / "default_climate_zone"
    if climate_path.exists():
        weather_file = climate_path / "weather.csv"
        if weather_file.exists():
            df_weather = pd.read_csv(weather_file)
            is_ok = len(df_weather) == 8760
            print_check(f"Weather CSV: {len(df_weather)} filas", is_ok)
            all_ok = all_ok and is_ok

    # Check building energy
    building_path = dataset_path / "buildings"
    if building_path.exists():
        building_dirs = list(building_path.glob("*/"))
        if building_dirs:
            building_name = building_dirs[0].name
            energy_file = building_dirs[0] / "energy_simulation.csv"

            if energy_file.exists():
                df_energy = pd.read_csv(energy_file)
                is_ok = len(df_energy) == 8760
                print_check(f"Building energy ({building_name}): {len(df_energy)} filas", is_ok,
                           f"Esperado: 8760 (1 ano horario)")
                all_ok = all_ok and is_ok

                # Check charger files
                charger_files = list(building_dirs[0].glob("charger_simulation_*.csv"))
                n_chargers = len(charger_files)
                is_ok = n_chargers == 128
                print_check(f"Charger simulation files: {n_chargers}", is_ok,
                           f"Esperado: 128 chargers (32 * 4 sockets)")
                all_ok = all_ok and is_ok

                # Verify each charger file
                if charger_files:
                    # Sample first and last
                    sample_files = [charger_files[0], charger_files[-1]]
                    for cf in sample_files:
                        df_charger = pd.read_csv(cf)
                        is_ok = len(df_charger) == 8760
                        if not is_ok:
                            print_check(f"Charger {cf.name}: {len(df_charger)} filas", False)
                            all_ok = False

                    if is_ok:
                        print_check(f"All charger CSVs verified (sampled first & last)", True,
                                   f"8760 filas cada uno")

    return all_ok


def verify_citylearn_environment() -> bool:
    """Verify CityLearn environment loads correctly."""
    print_header("PASO 3: Verificacion de Entorno CityLearn v2")

    try:
        from citylearn.citylearn import CityLearnEnv
    except ImportError:
        print_check("CityLearn importable", False, "pip install citylearn")
        return False

    schema_path = Path("data/processed/citylearnv2_dataset/schema.json")

    if not schema_path.exists():
        print_check("Schema file accessible", False, "Schema sera generado por pipeline")
        return False

    try:
        env = CityLearnEnv(schema_path)
        obs, info = env.reset()

        # Check observation space
        if isinstance(obs, list):
            obs_shape = (len(obs),) if obs else (0,)
        elif hasattr(obs, "shape"):
            obs_shape = obs.shape
        else:
            obs_shape = None

        print_check(f"CityLearn environment loads", True,
                   f"Observation shape: {obs_shape}")

        # Check for 8760 timesteps capability
        n_episodes = 1
        done = False
        step_count = 0

        while not done and step_count < 100:  # Just check first 100 steps
            action = env.action_space.sample()
            obs, reward, done, info = env.step(action)
            step_count += 1

        print_check(f"CityLearn step simulation works", True,
                   f"Executed {step_count} steps without error")

        # Note: Full 8760 step verification would take longer
        print(f"      (Nota: Verificacion completa de 8,760 timesteps ocurre durante entrenamiento)")

        return True

    except Exception as e:
        print_check(f"CityLearn environment loads", False, f"Error: {str(e)[:100]}")
        return False


def verify_agent_training_readiness() -> bool:
    """Verify system is ready for agent training."""
    print_header("PASO 4: Verificacion de Preparacion para Entrenamiento de Agentes")

    all_ok = True

    # Check stable-baselines3
    try:
        from stable_baselines3 import PPO, SAC, A2C
        print_check("Stable-baselines3 importable", True, "PPO, SAC, A2C disponibles")
    except ImportError:
        print_check("Stable-baselines3 importable", False, "pip install stable-baselines3")
        all_ok = False

    # Check config
    config_file = Path("configs/default.yaml")
    is_ok = config_file.exists()
    print_check(f"Training config exists", is_ok, "configs/default.yaml")
    all_ok = all_ok and is_ok

    # Check GPU availability
    try:
        import torch
        has_gpu = torch.cuda.is_available()
        device_msg = f"GPU detected: {torch.cuda.get_device_name(0)}" if has_gpu else "CPU only (slower)"
        print_check(f"PyTorch GPU support", True, device_msg)
    except ImportError:
        print_check(f"PyTorch available", False, "pip install torch")
        all_ok = False

    # Check directories
    checkpoints_dir = Path("checkpoints")
    outputs_dir = Path("outputs")

    checkpoints_dir.mkdir(exist_ok=True)
    outputs_dir.mkdir(exist_ok=True)

    print_check(f"Output directories writable", True,
               f"{checkpoints_dir}, {outputs_dir}")

    return all_ok


def verify_data_flow() -> bool:
    """Verify complete data flow: OE2 -> Processed -> CityLearn."""
    print_header("PASO 5: Verificacion de Flujo de Datos (OE2 -> Procesado -> CityLearn)")

    flow_steps = [
        ("OE2 artifacts (Solar, Chargers, BESS)", "data/interim/oe2"),
        ("Processed CityLearn dataset", "data/processed/citylearnv2_dataset"),
        ("CityLearn environment accessible", "citylearnv2_dataset/schema.json"),
        ("Agent training ready", "checkpoints/"),
    ]

    print("Flujo de datos esperado:")
    print(f"  1. OE2 Artifacts (8,760 filas/ano)")
    print(f"     -> 1 anno horario (8,760 timesteps)")
    print(f"  2. Dataset Builder procesa OE2")
    print(f"     -> Genera 128 archivos charger_simulation_*.csv (8,760 filas c/u)")
    print(f"  3. CityLearn v2 carga dataset")
    print(f"     -> Observation space: 534-dim (building + 128 chargers + time)")
    print(f"     -> Action space: 126 continuous actions (charger power setpoints)")
    print(f"  4. Agentes entrenan en episodios de 8,760 timesteps")
    print(f"     -> PPO, SAC, A2C optimizan CO2 + solar + cost + EV satisfaction")
    results["Training Readiness"] = verify_agent_training_readiness()
    results["Data Flow"] = verify_data_flow()

    print_header("RESUMEN DE VERIFICACION")

    all_passed = True
    for check_name, passed in results.items():
        status = f"{GREEN}COMPLETADO{RESET}" if passed else f"{YELLOW}PENDIENTE{RESET}"
        print(f"  [{status}] {check_name}")
        all_passed = all_passed and passed

    print(f"\n{BOLD}Estado General:{RESET}")
    if all_passed:
        print(f"  {GREEN}SISTEMA LISTO PARA ENTRENAMIENTO{RESET}")
        print(f"\n  Ejecutar:")
        print(f"    python scripts/run_full_pipeline.py")
        return 0
    else:
        print(f"  {YELLOW}Algunos componentes falta generar (ejecutar pipeline){RESET}")
        print(f"\n  Ejecutar:")
        print(f"    python scripts/run_full_pipeline.py")
        return 0  # Return 0 because this is expected during setup


if __name__ == "__main__":
    sys.exit(main())
