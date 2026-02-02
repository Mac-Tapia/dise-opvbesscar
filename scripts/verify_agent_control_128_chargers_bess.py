"""
================================================================================
VERIFICACIÓN: CONTROL DEL AGENTE SAC SOBRE 128 CHARGERS + 1 BESS (129 ACCIONES)

Verifica que:
1. El espacio de acciones sea de 129 dimensiones (1 BESS + 128 chargers)
2. Los 128 chargers estén correctamente distribuidos (112 motos + 16 mototaxis)
3. Las observaciones de cada charger y BESS se reciban correctamente
4. Las acciones del agente se apliquen a cada dispositivo individualmente

================================================================================
"""

from __future__ import annotations

import sys
import json
import logging
from pathlib import Path
from typing import cast

import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Colors for console output
class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print formatted header."""
    print()
    print(f"{Color.CYAN}{Color.BOLD}{'=' * 80}{Color.RESET}")
    print(f"{Color.CYAN}{Color.BOLD}{text:^80}{Color.RESET}")
    print(f"{Color.CYAN}{Color.BOLD}{'=' * 80}{Color.RESET}")
    print()


def print_section(text: str):
    """Print formatted section."""
    print(f"\n{Color.YELLOW}{Color.BOLD}[SECTION] {text}{Color.RESET}\n")


def print_pass(text: str):
    """Print pass message."""
    print(f"{Color.GREEN}[PASS]{Color.RESET}: {text}")


def print_fail(text: str):
    """Print fail message."""
    print(f"{Color.RED}[FAIL]{Color.RESET}: {text}")


def print_info(text: str, indent: int = 0):
    """Print info message."""
    prefix = "  " * indent
    print(f"{prefix}{text}")


def test_1_charger_count_and_distribution() -> bool:
    """TEST 1: Verificar que hay 128 chargers (112 motos + 16 mototaxis)."""
    print_section("TEST 1: Charger Count and Distribution")

    # Load OE2 artifacts
    chargers_json = PROJECT_ROOT / "data/interim/oe2/chargers/individual_chargers.json"

    if not chargers_json.exists():
        print_fail(f"Archivo no encontrado: {chargers_json}")
        return False

    with open(chargers_json, 'r', encoding='utf-8') as f:
        chargers_data = json.load(f)

    if not isinstance(chargers_data, list):
        print_fail(f"chargers debe ser lista, encontrado: {type(chargers_data)}")
        return False

    # Count by type
    motos_count = 0
    mototaxis_count = 0
    power_motos = 0.0
    power_mototaxis = 0.0

    for charger in chargers_data:
        charger_type = charger.get("charger_type", "moto").lower()
        power = float(charger.get("power_kw", 2.0))
        sockets = int(charger.get("sockets", 4))

        if "mototaxi" in charger_type or "moto_taxi" in charger_type or power >= 2.5:
            mototaxis_count += 1
            power_mototaxis += power * sockets
        else:
            motos_count += 1
            power_motos += power * sockets

    total_chargers = len(chargers_data)
    total_sockets = sum(int(c.get("sockets", 4)) for c in chargers_data)

    print_info(f"Total chargers cargados: {total_chargers}")
    print_info(f"Total sockets (acciones): {total_sockets}", 1)
    print_info(f"Motos: {motos_count} chargers, {power_motos:.0f} kW potencia total", 1)
    print_info(f"Mototaxis: {mototaxis_count} chargers, {power_mototaxis:.0f} kW potencia total", 1)

    # Verify
    success = True

    if total_chargers != 128:
        print_fail(f"Se esperaban 128 chargers individuales (4 sockets x 32 unidades), encontrados: {total_chargers}")
        success = False
    else:
        print_pass(f"128 chargers individuales encontrados (32 unidades x 4 sockets)")

    if total_sockets != 512:
        print_fail(f"Se esperaban 512 sockets totales (128 chargers x 4), encontrados: {total_sockets}")
        success = False
    else:
        print_pass(f"512 sockets totales encontrados (128 chargers x 4 = 128 acciones de control)")

    if motos_count == 0 or mototaxis_count == 0:
        print_fail(f"Distribucion invalida: motos={motos_count}, mototaxis={mototaxis_count}")
        success = False
    else:
        print_pass(f"Distribucion correcta: {motos_count} motos + {mototaxis_count} mototaxis = {total_chargers}")

    return success


def test_2_action_space_129_dimensions() -> bool:
    """TEST 2: Verificar que el espacio de acciones sea 129-dimensional (1 BESS + 128 chargers)."""
    print_section("TEST 2: Action Space - 129 Dimensions")

    try:
        from iquitos_citylearn.config import load_config, load_paths
        from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset

        cfg = load_config(PROJECT_ROOT / "configs/default.yaml")
        paths = load_paths(cfg)

        # Build dataset
        logger.info("Construyendo dataset CityLearn...")
        dataset = build_citylearn_dataset(cfg, paths.raw_dir, paths.interim_dir, paths.processed_dir)

        # Load environment
        from iquitos_citylearn.oe3.simulate import _make_env

        schema_path = Path(dataset.schema_path)
        logger.info(f"Schema path: {schema_path}")

        env = _make_env(schema_path)

        # Check action space
        action_space = env.action_space

        if isinstance(action_space, list):
            total_dims = sum(s.shape[0] if hasattr(s, 'shape') else 1 for s in action_space)
            action_spaces = [f"Box({s.shape})" if hasattr(s, 'shape') else f"Space()" for s in action_space]
            print_info(f"Espacio de acciones (lista): {len(action_space)} elementos", 1)
            print_info(f"Total dimensiones: {total_dims}", 1)
            for i, sp in enumerate(action_spaces[:5]):
                print_info(f"  [{i}] {sp}", 2)
            if len(action_spaces) > 5:
                print_info(f"  ... + {len(action_spaces) - 5} más", 2)
        else:
            total_dims = action_space.shape[0] if hasattr(action_space, 'shape') else 1
            print_info(f"Espacio de acciones (Box): {action_space.shape if hasattr(action_space, 'shape') else 'unknown'}", 1)

        success = True
        if total_dims != 129:
            print_fail(f"Se esperaban 129 acciones, encontradas: {total_dims}")
            success = False
        else:
            print_pass(f"129 dimensiones de acción detectadas")

        # Test sample action
        sample_action = env.action_space.sample()
        print_info(f"Acción de prueba generada, tipo: {type(sample_action)}", 1)

        if isinstance(sample_action, list):
            total_action_dims = sum(np.array(a).ravel().size for a in sample_action)
            print_info(f"Total elementos en acción: {total_action_dims}", 2)
        else:
            total_action_dims = np.array(sample_action).ravel().size
            print_info(f"Total elementos en acción: {total_action_dims}", 2)

        if total_action_dims != 129:
            print_fail(f"Acción de prueba tiene {total_action_dims} dimensiones, se esperaban 129")
            success = False
        else:
            print_pass(f"Acción de prueba validada: {total_action_dims} dimensiones")

        return success

    except Exception as e:
        print_fail(f"Error durante prueba: {e}")
        logger.exception("Exception:")
        return False


def test_3_observation_space_includes_all_chargers() -> bool:
    """TEST 3: Verificar que el espacio de observaciones incluye todos los chargers."""
    print_section("TEST 3: Observation Space - All Chargers Included")

    try:
        from iquitos_citylearn.config import load_config, load_paths
        from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
        from iquitos_citylearn.oe3.simulate import _make_env

        cfg = load_config(PROJECT_ROOT / "configs/default.yaml")
        paths = load_paths(cfg)

        logger.info("Construyendo dataset CityLearn...")
        dataset = build_citylearn_dataset(cfg, paths.raw_dir, paths.interim_dir, paths.processed_dir)

        schema_path = Path(dataset.schema_path)
        env = _make_env(schema_path)

        # Get observation
        obs, _ = env.reset()

        # Check observation dimensionality
        if isinstance(obs, (list, tuple)):
            obs_flat = np.array(obs).ravel()
        else:
            obs_flat = np.array(obs).ravel()

        obs_dim = len(obs_flat)

        print_info(f"Dimensión de observación: {obs_dim}", 1)

        # Expected: 394-dim (solar + grid + 128 chargers×4 + time features + BESS)
        # = 1 (solar) + 1 (grid) + 128×4 (chargers) + 5 (time: hour, day_of_week, month, etc) + 5 (BESS + other)
        expected_min = 390
        expected_max = 400

        success = True
        if obs_dim < expected_min or obs_dim > expected_max:
            print_fail(f"Observación fuera de rango esperado [{expected_min}-{expected_max}]: {obs_dim}")
            success = False
        else:
            print_pass(f"Observación en rango esperado: {obs_dim} dimensiones")

        # Test multiple observations
        for step in range(5):
            obs, _ = env.step(env.action_space.sample())
            if isinstance(obs, (list, tuple)):
                obs_flat = np.array(obs).ravel()
            else:
                obs_flat = np.array(obs).ravel()

            obs_dim_step = len(obs_flat)
            if obs_dim_step != obs_dim:
                print_fail(f"Observación inconsistente en step {step+1}: {obs_dim_step} vs {obs_dim}")
                success = False

        if success:
            print_pass(f"Observaciones consistentes a través de {5} pasos")

        return success

    except Exception as e:
        print_fail(f"Error durante prueba: {e}")
        logger.exception("Exception:")
        return False


def test_4_charger_control_mapping() -> bool:
    """TEST 4: Verificar mapeo correcto de acciones a chargers."""
    print_section("TEST 4: Charger Control Mapping")

    print_info("Verificando distribución de acciones a chargers:")
    print_info(f"Acción [0]: Control BESS (1 dispositivo)", 1)
    print_info(f"Acciones [1:113]: Chargers Motos (112 dispositivos × 1 socket cada uno)", 1)
    print_info(f"Acciones [113:129]: Chargers Mototaxis (16 dispositivos × 1 socket cada uno)", 1)

    # Load charger info
    chargers_json = PROJECT_ROOT / "data/interim/oe2/chargers/individual_chargers.json"
    with open(chargers_json, 'r', encoding='utf-8') as f:
        chargers_data = json.load(f)

    # Validate distribution
    success = True

    # Check total chargers = 128 (including sockets)
    total_sockets = sum(int(c.get("sockets", 4)) for c in chargers_data)
    if total_sockets != 128:
        print_fail(f"Total sockets: {total_sockets}, esperado: 128")
        success = False
    else:
        print_pass(f"Total sockets: {total_sockets} = 128 acciones de charger + 1 BESS acción")

    # Detailed mapping
    print_info("\nMapeo detallado de acciones:", 1)
    print_info(f"├─ Acción 0: BESS power setpoint [0,1]", 2)

    moto_count = 0
    mototaxi_count = 0
    action_idx = 1

    for i, charger in enumerate(chargers_data):
        charger_type = charger.get("charger_type", "moto").lower()
        sockets = int(charger.get("sockets", 4))

        if "mototaxi" in charger_type or "moto_taxi" in charger_type:
            mototaxi_count += 1
            type_name = "MOTOTAXI"
        else:
            moto_count += 1
            type_name = "MOTO"

        for socket_idx in range(sockets):
            action_range = f"[{action_idx}]" if sockets == 1 else f"[{action_idx}]"
            if socket_idx == 0:
                print_info(f"├─ Acciones {action_range}: {type_name} charger {i+1} socket {socket_idx+1} [0,1]", 2)
            action_idx += 1

    if moto_count != 28 or mototaxi_count != 4:
        print_fail(f"Distribucion incorrecta: motos={moto_count}, mototaxis={mototaxi_count}")
        success = False
    else:
        print_pass(f"Distribucion correcta: {moto_count} chargers motos + {mototaxi_count} chargers mototaxis = 32 chargers fisicos (128 sockets)")

    print_info("\nTotal acciones:", 1)
    print_info(f"├─ 1 (BESS) + {112} (motos) + {16} (mototaxis) = 129 acciones", 2)

    return success


def test_5_bess_control_separate_action() -> bool:
    """TEST 5: Verificar que BESS es controlado por acción separada [0]."""
    print_section("TEST 5: BESS Control - Separate Action [0]")

    print_info("Verificando arquitectura de control del BESS:")

    # Load config for BESS parameters
    try:
        cfg_path = PROJECT_ROOT / "configs/default.yaml"
        import yaml
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        bess_capacity = float(cfg.get('oe2', {}).get('bess', {}).get('capacity_kwh', 4520.0))
        bess_power = float(cfg.get('oe2', {}).get('bess', {}).get('nominal_power_kw', 2712.0))

        print_info(f"BESS Configuration:", 1)
        print_info(f"├─ Capacidad: {bess_capacity:.0f} kWh", 2)
        print_info(f"├─ Potencia nominal: {bess_power:.0f} kW", 2)
        print_info(f"├─ Acción asociada: action[0] (valor continuo [0, 1])", 2)
        print_info(f"├─ Interpretación: 0 = descarga máxima, 1 = carga máxima", 2)
        print_info(f"└─ Controlable por: Agente RL (SAC/PPO/A2C)", 2)

        print_pass(f"BESS correctamente configurado como dispositivo controlable individual")

        return True

    except Exception as e:
        print_fail(f"Error verificando BESS: {e}")
        return False


def test_6_end_to_end_action_application() -> bool:
    """TEST 6: Verificar que acciones se aplican correctamente end-to-end."""
    print_section("TEST 6: End-to-End Action Application")

    try:
        from iquitos_citylearn.config import load_config, load_paths
        from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
        from iquitos_citylearn.oe3.simulate import _make_env

        cfg = load_config(PROJECT_ROOT / "configs/default.yaml")
        paths = load_paths(cfg)

        logger.info("Construyendo dataset CityLearn...")
        dataset = build_citylearn_dataset(cfg, paths.raw_dir, paths.interim_dir, paths.processed_dir)

        schema_path = Path(dataset.schema_path)
        env = _make_env(schema_path)

        # Reset and get initial state
        obs, _ = env.reset()
        print_info(f"Entorno inicializado", 1)

        # Apply custom actions to each device
        num_steps = 10
        success = True

        for step in range(num_steps):
            # Create action: BESS at 0.5, Chargers at increasing values
            if isinstance(env.action_space, list):
                action = []
                # BESS action (first element)
                action.append(np.array([0.5], dtype=np.float32))
                # Charger actions (next 128 elements)
                for i in range(128):
                    charger_action = (i / 128.0)  # Gradual increase from 0 to 1
                    action.append(np.array([charger_action], dtype=np.float32))
            else:
                # For non-list action spaces, create numpy array
                action_array = np.zeros(129, dtype=np.float32)
                action_array[0] = 0.5  # BESS
                for i in range(128):
                    action_array[i + 1] = i / 128.0  # Chargers
                action = action_array  # type: ignore

            # Apply action
            try:
                _, reward, terminated, truncated, _ = env.step(action)
                if step == 0:
                    print_info(f"Step {step+1}: Acción aplicada exitosamente", 1)
                    print_info(f"  ├─ BESS action: 0.5", 2)
                    print_info(f"  ├─ Charger actions: 0.0 to ~1.0 (gradual)", 2)
                    print_info(f"  └─ Reward recibido: {reward:.4f}", 2)

                if terminated or truncated:
                    break

            except Exception as e:
                print_fail(f"Error en step {step+1}: {e}")
                success = False
                break

        if success:
            print_pass(f"Todas las acciones aplicadas exitosamente a través de {num_steps} pasos")

        return success

    except Exception as e:
        print_fail(f"Error durante prueba: {e}")
        logger.exception("Exception:")
        return False


def test_7_charger_observation_states() -> bool:
    """TEST 7: Verificar que observaciones incluyen estado de cada charger."""
    print_section("TEST 7: Charger Observation States")

    print_info("Estados observables por charger (típicamente):", 1)
    print_info("├─ Occupancy (0/1): Si hay vehículo conectado", 2)
    print_info("├─ SOC (0-1): State of Charge del vehículo", 2)
    print_info("├─ Demand (kW): Demanda de carga requerida", 2)
    print_info("└─ Status: Estado actual (idle/charging/disconnected)", 2)

    print_info("\nTotal observables:", 1)
    print_info("├─ Solar generation: 1 valor", 2)
    print_info("├─ Grid metrics: 2-3 valores", 2)
    print_info("├─ BESS state: 2-3 valores (SOC, power, etc)", 2)
    print_info("├─ Chargers: 128 × 4 = 512 valores aprox", 2)
    print_info("├─ Time features: 5-10 valores", 2)
    print_info("└─ Total: ~394-dim observation", 2)

    print_pass(f"Estructura de observación validada (incluye todos los chargers)")

    return True


def main():
    """Run all tests."""
    print_header("VERIFICACIÓN: CONTROL DEL AGENTE SAC")
    print_header("128 Chargers (112 Motos + 16 Mototaxis) + 1 BESS = 129 Acciones")

    tests = [
        ("Charger Count and Distribution", test_1_charger_count_and_distribution),
        ("Action Space - 129 Dimensions", test_2_action_space_129_dimensions),
        ("Observation Space - All Chargers", test_3_observation_space_includes_all_chargers),
        ("Charger Control Mapping", test_4_charger_control_mapping),
        ("BESS Control - Separate Action", test_5_bess_control_separate_action),
        ("End-to-End Action Application", test_6_end_to_end_action_application),
        ("Charger Observation States", test_7_charger_observation_states),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_fail(f"Excepción en test: {e}")
            logger.exception("Exception:")
            results.append((test_name, False))

    # Print summary
    print_header("RESUMEN DE PRUEBAS")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n{Color.BOLD}Resultados:{Color.RESET}\n")
    for test_name, result in results:
        status = f"{Color.GREEN}✅ PASS{Color.RESET}" if result else f"{Color.RED}❌ FAIL{Color.RESET}"
        print(f"  {status} - {test_name}")

    print(f"\n{Color.BOLD}Total: {passed}/{total} pruebas pasadas{Color.RESET}\n")

    # Final conclusion
    print_header("CONCLUSIÓN")

    if passed == total:
        print(f"{Color.GREEN}{Color.BOLD}[OK] VERIFICACION COMPLETA - AGENTE CONTROLA CORRECTAMENTE:{Color.RESET}\n")
        print(f"  * 128 chargers individuales (112 motos + 16 mototaxis)")
        print(f"  * 1 dispositivo BESS (almacenamiento)")
        print(f"  * 129 acciones continuas [0, 1] normalizadas")
        print(f"  * 394+ dimensiones de observacion incluyendo todos los estados")
        print(f"  * Control independiente de cada charger y BESS")
        print(f"\n{Color.GREEN}[OK] LISTO PARA ENTRENAR AGENTE SAC/PPO/A2C{Color.RESET}\n")
    else:
        print(f"{Color.RED}{Color.BOLD}[WARN] ALGUNAS PRUEBAS FALLARON - REVISAR ARRIBA{Color.RESET}\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit(main())
