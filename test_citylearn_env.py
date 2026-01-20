#!/usr/bin/env python3
"""
PRUEBA RAPIDA DEL ENTORNO CITYLEARN
Verifica que el entorno funciona antes de entrenar.
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("PRUEBA RAPIDA DEL ENTORNO CITYLEARN")
print("=" * 60)

# 1. Verificar CityLearn
print("\n[1] Importando CityLearn...")
try:
    from citylearn.citylearn import CityLearnEnv
    print("    ✓ CityLearn importado")
except ImportError as e:
    print(f"    ✗ Error: {e}")
    sys.exit(1)

# 2. Aplicar parches
print("\n[2] Aplicando parches...")
try:
    from citylearn_monkeypatch import apply_citylearn_patches
    apply_citylearn_patches()
    print("    ✓ Parches aplicados")
except Exception as e:
    print(f"    ⚠ Parches: {e}")

# 3. Cargar config
print("\n[3] Cargando configuración...")
try:
    from scripts._common import load_all
    cfg, rp = load_all("configs/default.yaml")
    print("    ✓ Configuración OK")
except Exception as e:
    print(f"    ✗ Error: {e}")
    sys.exit(1)

# 4. Verificar schema
print("\n[4] Verificando schema...")
dataset_dir = rp.processed_dir / "citylearn" / cfg["oe3"]["dataset"]["name"]
schema_pv = dataset_dir / "schema_pv_bess.json"

if not schema_pv.exists():
    print(f"    ✗ No existe: {schema_pv}")
    sys.exit(1)
print(f"    ✓ Schema: {schema_pv}")

# 5. Crear entorno
print("\n[5] Creando entorno CityLearn...")
try:
    env = CityLearnEnv(schema=str(schema_pv.resolve()), render_mode=None)
    env.render_mode = None  # Asegurar que existe
    print(f"    ✓ Entorno creado")
    print(f"    - Edificios: {len(env.buildings)}")
    print(f"    - Obs space: {env.observation_space}")
    print(f"    - Action space: {env.action_space}")
except Exception as e:
    print(f"    ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 6. Probar reset
print("\n[6] Probando env.reset()...")
try:
    start = time.time()
    obs, info = env.reset()
    elapsed = time.time() - start
    print(f"    ✓ Reset OK ({elapsed:.2f}s)")
    if isinstance(obs, list):
        print(f"    - Obs: lista de {len(obs)} elementos")
    else:
        obs_shape = getattr(obs, "shape", None)
        print(f"    - Obs shape: {obs_shape if obs_shape is not None else type(obs)}")
except Exception as e:
    print(f"    ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 7. Probar steps
print("\n[7] Probando 10 steps...")
try:
    for i in range(10):
        # Acción aleatoria
        if isinstance(env.action_space, list):
            action = [sp.sample() for sp in env.action_space]
        else:
            action = env.action_space.sample()
        
        obs, reward, terminated, truncated, info = env.step(action)
        
        if i == 0:
            print(f"    - Step 0: reward={reward}, terminated={terminated}")
        
        if terminated or truncated:
            print(f"    - Episodio terminó en step {i+1}")
            break
    
    print(f"    ✓ 10 steps OK")
except Exception as e:
    print(f"    ✗ Error en step: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 8. Probar SB3 wrapper
print("\n[8] Probando stable_baselines3...")
try:
    from stable_baselines3.common.vec_env import DummyVecEnv
    
    # Crear wrapper
    def make_env():
        e = CityLearnEnv(schema=str(schema_pv.resolve()), render_mode=None)
        e.render_mode = None
        return e
    
    print("    - Creando DummyVecEnv...")
    vec_env = DummyVecEnv([make_env])
    print(f"    ✓ VecEnv creado")
    
    # Probar reset
    obs = vec_env.reset()
    obs_shape = getattr(obs, "shape", None)
    print(f"    - Obs shape: {obs_shape if obs_shape is not None else type(obs)}")
    
except Exception as e:
    print(f"    ⚠ SB3 wrapper: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("PRUEBA COMPLETADA")
print("=" * 60 + "\n")
