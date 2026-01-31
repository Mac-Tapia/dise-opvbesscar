"""
Diagnóstico: Verificar por qué CityLearn termina episodios prematuramente
y por qué no detecta vehículos cargando.
"""
from pathlib import Path
from citylearn.citylearn import CityLearnEnv

# Schema path
schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json")

print("="*80)
print("DIAGNÓSTICO CITYLEARN: Chargers y Episodios")
print("="*80)

# Create environment
try:
    env = CityLearnEnv(schema=str(schema_path))
    print(f"✓ Entorno creado correctamente")
    print(f"  Buildings: {len(env.buildings)}")

    if len(env.buildings) > 0:
        b = env.buildings[0]
        print(f"  Building 0 name: {b.name}")

        # Check for chargers
        if hasattr(b, 'chargers'):
            print(f"  Chargers en building: {len(b.chargers)}")
            if len(b.chargers) > 0:
                c = b.chargers[0]
                print(f"\n  Charger 0 attributes:")
                for attr in dir(c):
                    if not attr.startswith('_'):
                        print(f"    - {attr}")
        else:
            print("  ⚠️ Building NO tiene atributo 'chargers'")

    # Check observation space
    print(f"\n  Observation space shape: {env.observation_space}")

    # Run 1 step
    obs, info = env.reset()
    print(f"\n  Reset OK - Obs shape: {len(obs) if isinstance(obs, list) else obs.shape}")

    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    print(f"  Step 1 - terminated: {terminated}, truncated: {truncated}")

    # Run to step 100
    for i in range(99):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            print(f"  ⚠️ EPISODIO TERMINÓ EN PASO {i+2}!")
            break
    else:
        print(f"  ✓ Episodio continúa hasta paso 100")

    # Check if we can reach step 8760
    env.reset()
    step_count = 0
    max_test_steps = 8760
    for i in range(max_test_steps):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        step_count += 1
        if terminated or truncated:
            print(f"\n  ⚠️ CRÍTICO: Episodio terminó en paso {step_count} (esperado: 8760)")
            print(f"     terminated={terminated}, truncated={truncated}")
            break
    else:
        print(f"\n  ✓ EXCELENTE: Episodio completo hasta paso {step_count}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
