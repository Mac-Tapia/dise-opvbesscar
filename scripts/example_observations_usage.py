"""
Ejemplo de uso del modulo canonico de observaciones.

Demuestra como usar ObservationBuilder para construir observaciones
en lugar de tener logica duplicada en cada script de entrenamiento.
"""

from src.dataset_builder_citylearn import (
    ObservationBuilder,
    validate_observation,
    get_observation_stats,
    load_solar_data,
    load_chargers_data,
    load_mall_demand_data,
    load_bess_data,
)
import numpy as np


def example_basic_usage():
    """Ejemplo 1: Uso basico con version 156-dim (default)."""
    
    print("=" * 80)
    print("EJEMPLO 1: Uso Basico (156-dim estandar)")
    print("=" * 80)
    
    # Crear builder con version default (156-dim)
    obs_builder = ObservationBuilder()
    print(f"\n[OK] ObservationBuilder creado:")
    print(f"   - Version: {obs_builder.version}")
    print(f"   - Dimension: {obs_builder.obs_dim}")
    print(f"   - Observation space: {obs_builder.observation_space}")
    
    # Datos simulados para prueba
    data = {
        "solar_hourly": np.random.uniform(0, 1000, 8760),
        "chargers_hourly": np.random.uniform(0, 7.4, (8760, 38)),
        "mall_hourly": np.full(8760, 100.0),
        "bess_soc_hourly": np.random.uniform(20, 80, 8760),
    }
    
    # Hacer observacion para hora 0
    obs = obs_builder.make_observation(hour_idx=0, data=data)
    
    # Validar
    is_valid = validate_observation(obs, obs_builder)
    print(f"\n[OK] Observacion creada (hora 0):")
    print(f"   - Forma: {obs.shape}")
    print(f"   - Valida: {is_valid}")
    print(f"   - Primeros 5 valores: {obs[:5]}")
    
    # Estadisticas
    stats = get_observation_stats(obs, name="obs_hora_0")
    print(f"\n[GRAPH] Estadisticas:")
    print(f"   - Media: {stats['mean']:.4f}")
    print(f"   - Std: {stats['std']:.4f}")
    print(f"   - Min: {stats['min']:.4f}")
    print(f"   - Max: {stats['max']:.4f}")
    print(f"   - Has NaN: {stats['has_nan']}")


def example_multiple_versions():
    """Ejemplo 2: Usar diferentes versiones de observaciones."""
    
    print("\n" + "=" * 80)
    print("EJEMPLO 2: Multiples Versiones")
    print("=" * 80)
    
    # Datos simulados
    data = {
        "solar_hourly": np.random.uniform(0, 1000, 8760),
        "chargers_hourly": np.random.uniform(0, 7.4, (8760, 38)),
        "mall_hourly": np.full(8760, 100.0),
        "bess_soc_hourly": np.random.uniform(20, 80, 8760),
    }
    
    versions = [
        ObservationBuilder.OBS_156_STANDARD,
        ObservationBuilder.OBS_246_CASCADA,
        ObservationBuilder.OBS_66_EXPANDED,
        ObservationBuilder.OBS_50_SIMPLE,
    ]
    
    print("\nVersiones disponibles:\n")
    for version in versions:
        b = ObservationBuilder(version=version)
        obs = b.make_observation(hour_idx=0, data=data)
        stats = get_observation_stats(obs, name=f"obs_{version}")
        
        status = "[OK] ACTUAL" if version == ObservationBuilder.OBS_156_STANDARD else "[!] ALT"
        print(f"{status} {version:20s} | Dim: {b.obs_dim:3d} | Mean: {stats['mean']:7.4f}")


def example_training_integration():
    """Ejemplo 3: Integracion en un training loop."""
    
    print("\n" + "=" * 80)
    print("EJEMPLO 3: Integracion en Training Loop")
    print("=" * 80)
    
    # Crear builder
    obs_builder = ObservationBuilder(version="156_standard")
    print(f"\n[OK] Builder inicializado: {obs_builder.version}")
    
    # Datos simulados (normalmente cargados desde OE2)
    data = {
        "solar_hourly": np.random.uniform(0, 1000, 8760),
        "chargers_hourly": np.random.uniform(0, 7.4, (8760, 38)),
        "mall_hourly": np.full(8760, 100.0),
        "bess_soc_hourly": np.random.uniform(20, 80, 8760),
    }
    
    # Loop de entrenamiento simulado
    print("\nSimulando training loop (primeras 10 horas):\n")
    
    total_obs = 0
    for hour in range(10):
        obs = obs_builder.make_observation(hour_idx=hour, data=data)
        
        # Validar antes de usar en agente
        if validate_observation(obs, obs_builder):
            total_obs += 1
            print(f"  Hora {hour:2d}: obs valida, shape={obs.shape}, ' mean={obs.mean():.4f}")
        else:
            print(f"  Hora {hour:2d}: [!] INVALIDA")
    
    print(f"\n[OK] {total_obs}/10 observaciones validas")


def example_refactoring_guide():
    """Ejemplo 4: Guia de refactoring para scripts existentes."""
    
    print("\n" + "=" * 80)
    print("EJEMPLO 4: Guia de Refactoring")
    print("=" * 80)
    
    print("""
🔄 ANTES (codigo duplicado en train_ppo_multiobjetivo.py):

    class RealOE2Environment:
        OBS_DIM = 156
        
        def _make_observation(self, hour_idx):
            '''Construccion especifica aqui (150+ LOC)'''
            obs = np.zeros(156, dtype=np.float32)
            # ... logica duplicada ...
            return obs

    def reset(self):
        obs = self._make_observation(0)  # DUPLICADO en train_sac, train_a2c, etc.
        return obs, {}


🟢 DESPUES (usando ObservationBuilder):

    from src.dataset_builder_citylearn import ObservationBuilder
    
    class RealOE2Environment:
        def __init__(self):
            self.obs_builder = ObservationBuilder(version="156_standard")
            self.OBS_DIM = self.obs_builder.obs_dim
            self.observation_space = self.obs_builder.observation_space
        
        def reset(self):
            obs = self.obs_builder.make_observation(0, self.data)
            return obs, {}
        
        def step(self, action):
            # ... logica step ...
            obs = self.obs_builder.make_observation(self.step_count, self.data)
            return obs, reward, done, truncated, info


📋 BENEFICIOS DEL REFACTORING:

    [OK] Eliminacion de 150+ LOC duplicado por script
    [OK] Cambios centralizados en observations.py
    [OK] Facil agregar/cambiar versiones
    [OK] Validacion automatica de observaciones
    [OK] Versionamiento claro & historico
    [OK] Compatible backward (versiones 50, 66, 246 disponibles)
""")


if __name__ == "__main__":
    # Ejecutar ejemplos
    example_basic_usage()
    example_multiple_versions()
    example_training_integration()
    example_refactoring_guide()
    
    print("\n" + "=" * 80)
    print("[OK] TODOS LOS EJEMPLOS COMPLETADOS")
    print("=" * 80)
    print("\n🎯 Proximo paso: Refactorizar scripts de entrenamiento para usar")
    print("   ObservationBuilder en lugar de _make_observation() duplicado.")
    print("\n📚 Ver: MAPA_OBSERVACIONES_CITYLEARN_DISPERSION.md para detalles.")
