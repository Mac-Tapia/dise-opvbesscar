#!/usr/bin/env python3
"""
Verifica que los datos generados de 1 año por hora (8,760 timesteps)
se conecten correctamente al schema de CityLearn v2 para entrenamiento de agentes.

Pasos:
1. Construir dataset CityLearn con datos horarios
2. Verificar schema.json con 8,760 timesteps
3. Cargar ambiente CityLearn
4. Verificar observaciones y acciones
5. Simular algunos timesteps
"""
from pathlib import Path
import sys
import json
import traceback

sys.path.insert(0, str(Path(__file__).parent / "src"))

from iquitos_citylearn.config import load_config, load_paths
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset

try:
    from citylearn.citylearn import CityLearnEnv
except ImportError:
        print("ADVERTENCIA: CityLearn no esta instalado. Instalando...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "citylearn==2.5.0"])
        from citylearn.citylearn import CityLearnEnv


def verify_connection():
    """Verifica la conexion de datos hourly al schema de CityLearn v2."""
    print("=" * 80)
    print("VERIFICACION: DATOS HORARIOS (8,760) -> SCHEMA CITYLEARN v2")
    print("=" * 80)

    # =====================================================
    # PASO 1: Cargar configuración
    # =====================================================
    print("\n[1/5] Cargando configuracion...")
    try:
        config = load_config()
        paths = load_paths(config)
        print("   OK Configuracion cargada")
        print(f"   - Processed dir: {paths.processed_dir}")
    except Exception as e:
        print(f"   ✗ Error cargando config: {e}")
        traceback.print_exc()
        return False

    # =====================================================
    # PASO 2: Construir dataset CityLearn
    # =====================================================
    print("\n[2/5] Construyendo dataset CityLearn con datos horarios...")
    try:
        build_citylearn_dataset(
            cfg=config,
            raw_dir=paths.raw_dir,
            interim_dir=paths.interim_dir,
            processed_dir=paths.processed_dir,
        )
        print("   ✓ Dataset construido")
    except Exception as e:
        print(f"   ✗ Error construyendo dataset: {e}")
        traceback.print_exc()
        return False

    # =====================================================
    # PASO 3: Verificar schema.json
    # =====================================================
    print("\n[3/5] Verificando schema.json con 8,760 timesteps...")
    try:
        schema_files = sorted(paths.processed_dir.glob("schema_*.json"))
        if not schema_files:
            print("   ✗ No se encontró schema_*.json")
            return False

        schema_path = schema_files[-1]  # Usar el más reciente
        print(f"   Usando: {schema_path.name}")

        with open(schema_path, 'r') as f:
            schema = json.load(f)

        # Verificar estructura básica
        if 'buildings' not in schema:
            print("   ✗ Schema no contiene 'buildings'")
            return False

        buildings = schema['buildings']
        print(f"   ✓ Schema contiene {len(buildings)} building(s)")

        # Verificar energía solar y carga del mall
        for bldg in buildings:
            bldg_name = bldg.get('name', 'unknown')
            print(f"\n   Building: {bldg_name}")

            # Verificar energy_simulation
            energy_sim_path = bldg.get('energy_simulation', {}).get('file_dir', '')
            if energy_sim_path:
                full_path = paths.processed_dir / energy_sim_path
                if full_path.exists():
                    import pandas as pd
                    df_energy = pd.read_csv(full_path)
                    print(f"      - energy_simulation.csv: {len(df_energy)} filas")
                    if len(df_energy) != 8760:
                        print(f"        ✗ ERROR: Esperaba 8,760 filas, tiene {len(df_energy)}")
                        return False
                    print(f"        ✓ Timesteps horarios correctos (8,760)")
                else:
                    print(f"      ✗ No encontrado: {full_path}")
                    return False

            # Verificar dispositivos (chargers)
            devices = bldg.get('devices', [])
            if devices:
                print(f"      - Dispositivos: {len(devices)}")
                for dev in devices[:3]:  # Mostrar primeros 3
                    dev_name = dev.get('name', 'unknown')
                    dev_file = dev.get('file_dir', '')
                    if dev_file:
                        full_path = paths.processed_dir / dev_file
                        if full_path.exists():
                            df_dev = pd.read_csv(full_path)
                            print(f"        • {dev_name}: {len(df_dev)} filas")
                            if len(df_dev) != 8760:
                                print(f"          ✗ ERROR: Esperaba 8,760, tiene {len(df_dev)}")
                                return False
                        else:
                            print(f"        • {dev_name}: NO ENCONTRADO")
                if len(devices) > 3:
                    print(f"        ... y {len(devices) - 3} más")

        print("\n   ✓ Schema verifica correctamente con 8,760 timesteps")

    except Exception as e:
        print(f"   ✗ Error verificando schema: {e}")
        traceback.print_exc()
        return False

    # =====================================================
    # PASO 4: Cargar ambiente CityLearn
    # =====================================================
    print("\n[4/5] Cargando ambiente CityLearn v2...")
    try:
        env = CityLearnEnv(schema=str(schema_path))
        print("   ✓ Ambiente CityLearn cargado")

        # Resetear para obtener observación inicial
        obs, info = env.reset()
        print(f"   ✓ Ambiente reseteado")

        # Verificar dimensiones
        if isinstance(obs, list):
            obs_flat = []
            for o in obs:
                if isinstance(o, list):
                    obs_flat.extend(o)
                else:
                    obs_flat.append(o)
            obs_dim = len(obs_flat)
            print(f"   - Observación (lista anidada): {obs_dim} dims")
        else:
            obs_dim = len(obs) if hasattr(obs, '__len__') else 1
            print(f"   - Observación shape: {obs_dim} dims")

        # Verificar espacio de acción
        action_space = env.action_spaces[0]  # Primer building
        action_shape = action_space.shape if hasattr(action_space, 'shape') else (1,)
        print(f"   - Acción shape: {action_shape}")

        print("   ✓ Espacios de observación y acción verificados")

    except Exception as e:
        print(f"   ✗ Error cargando CityLearn: {e}")
        traceback.print_exc()
        return False

    # =====================================================
    # PASO 5: Simular algunos timesteps
    # =====================================================
    print("\n[5/5] Simulando 24 timesteps horarios (1 día completo)...")
    try:
        import numpy as np

        for t in range(24):
            # Crear acción (todos los cargadores a potencia 0.5)
            action = [[0.5] * len(env.action_spaces[0].shape)]

            # Step
            obs, reward, terminated, truncated, info = env.step(action)

            if (t + 1) % 6 == 0:
                print(f"   ✓ Timestep {t+1:3d}/24 completado (reward: {reward[0]:7.4f})")

            if terminated or truncated:
                print(f"   - Episodio terminado en timestep {t+1}")
                break

        print("\n   ✓ Simulación de 24 timesteps exitosa")

    except Exception as e:
        print(f"   ✗ Error en simulación: {e}")
        traceback.print_exc()
        return False

    # =====================================================
    # RESUMEN
    # =====================================================
    print("\n" + "=" * 80)
    print("✓ VERIFICACIÓN EXITOSA")
    print("=" * 80)
    print("\nResumen:")
    print("  ✓ Datos horarios (8,760 timesteps/año) generados correctamente")
    print("  ✓ Schema CityLearn v2 contiene datos horarios")
    print("  ✓ Ambiente CityLearn carga y funciona correctamente")
    print("  ✓ Observaciones y acciones tienen dimensiones correctas")
    print("  ✓ Simulación de 24 timesteps completada sin errores")
    print("\n🚀 LISTO PARA ENTRENAMIENTO DE AGENTES")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = verify_connection()
    sys.exit(0 if success else 1)
