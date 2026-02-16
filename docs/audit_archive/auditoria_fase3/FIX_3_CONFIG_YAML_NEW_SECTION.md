# 🔧 FIX #3 - SECCIÓN NUEVA PARA config.yaml
# Agregar estas líneas DESPUÉS de oe3 en configs/default.yaml

```yaml
oe3:
  # === CONFIGURACIÓN SAC (NUEVO) ===
  sac:
    # Hiperparámetros de entrenamiento
    episodes: 50                                # Episodios para SAC (1 episodio = 8760 horas = 1 año)
    batch_size: 256                             # Batch size para actualizaciones
    buffer_size: 100000                         # Tamaño del replay buffer
    learning_rate: 5e-5                         # Learning rate (crítico para estabilidad)
    gamma: 0.99                                 # Discount factor (fuerte descuento a largo plazo)
    tau: 0.01                                   # Soft target update rate (más agresivo que 0.005)
    
    # Entropía SAC
    ent_coef: "auto"                            # Ajuste automático de coeficiente de entropía
    ent_coef_init: 0.1                          # Inicialización conservadora (evita explosion)
    ent_coef_lr: 1e-5                           # Learning rate lento para entropía
    
    # Red neuronal
    hidden_sizes: [256, 256]                    # Arquitectura: 2 capas de 256 neuronas
    activation: "relu"                          # Función de activación
    
    # Estabilidad numérica (POST-DIVERGENCIA)
    clip_gradients: true                        # Clipear gradientes para evitar explosión
    max_grad_norm: 0.5                          # Máxima norma de gradientes
    warmup_steps: 5000                          # Steps iniciales para llenar replay buffer
    gradient_accumulation_steps: 1              # Sin acumulación (1 = update cada step)
    
    # GPU/CUDA
    device: "auto"                              # Auto-detectar GPU/CPU
    use_amp: true                               # Mixed precision (FP16 + FP32)
    pin_memory: true                            # Acelerar transferencia CPU->GPU
    
    # Límites operacionales
    peak_demand_limit_kw: 200.0                 # Límite de demanda pico (penalizar si se excede)
    
    # Logging y checkpoints
    verbose: 0                                  # Verbosidad (0=mínimo)
    log_interval: 500                           # Log cada 500 steps
    checkpoint_freq_steps: 1000                 # Guardar checkpoint cada 1000 steps
    save_final: true                            # Guardar model final al terminar
    progress_interval_episodes: 1               # Loguear progreso cada episodio
    
    # Reproducibilidad
    seed: 42                                    # Seed para reproducibilidad
    deterministic_cuda: false                   # false = más rápido, true = reproducible
    
    # Normalización (crítico para estabilidad)
    normalize_observations: true                # Normalizar observaciones (media=0, std=1)
    normalize_rewards: true                     # Normalizar rewards (escalar a [-1, 1])
    reward_scale: 0.5                           # Escala de rewards (0.5 = penalidades suaves)
    clip_obs: 5.0                               # Clipear observaciones a [-5, +5]
  
  
  # === CONFIGURACIÓN MULTIOBJETIVO (NUEVO) ===
  reward:
    # Pesos para la función de recompensa multiobjetivo
    # CRÍTICO: Deben sumar 1.0 (se normalizan automáticamente)
    weight_co2: 0.50                            # PRIMARY: Minimizar CO₂ (grid import)
    weight_solar: 0.20                          # SECONDARY: Maximizar autoconsumo solar
    weight_cost: 0.15                           # TERTIARY: Minimizar costo eléctrico
    weight_ev_satisfaction: 0.10                # EV charging satisfaction
    weight_grid_stability: 0.05                 # Minimizar picos de demanda
    
    # Baselines para normalización de rewards
    # Usados para mapear métricas reales a reward [-1, 1]
    co2_baseline_offpeak_kwh: 130.0             # Off-peak: ~130 kWh/h típico (mall + EVs)
    co2_baseline_peak_kwh: 250.0                # Peak (18-21h): target con BESS support
    cost_baseline_usd: 100.0                    # Referencia de costo para normalización
    
    # Penalizaciones dinámicas
    peak_hours: [18, 19, 20, 21]                # Horas pico donde aplica penalización extra
    peak_demand_penalty_multiplier: 4.0         # Penalidad x4 si se excede límite en pico
    
    # Bonuses
    solar_direct_bonus_weight: 0.01             # Bonus por energía solar directa a EVs
    battery_charge_bonus_weight: 0.005          # Bonus por cargar BESS en off-peak


  # === GRID / FACTORES DE EMISIÓN (ACTUALIZADO) ===
  grid:
    # Factores de emisión específicos de Iquitos (central térmica aislada)
    carbon_intensity_kg_per_kwh: 0.4521         # CO₂ del grid (central térmica)
    ev_co2_conversion_kg_per_kwh: 2.146         # Conversión directa: 50kW × 2.146 = 107.3 kg/h
    tariff_usd_per_kwh: 0.20                    # Tarifa eléctrica
    
    # Límites y objetivos
    import_limit_peak_kw: 150.0                 # Máxima importación permitida en pico
    import_limit_offpeak_kw: 100.0              # Máxima importación permitida off-peak
    solar_target_utilization_pct: 70.0          # Objetivo: utilizar 70% de PV directo


# === VERIFICACIÓN ===
# Después de agregar esta sección, verificar:
# 1. Pesos suman 1.0: 0.50 + 0.20 + 0.15 + 0.10 + 0.05 = 1.00 ✅
# 2. CO₂ factor: 0.4521 = Iquitos thermal ✅
# 3. Learning rate: 5e-5 = conservador para estabilidad ✅
# 4. Episodes: 50 = ~438,000 timesteps total ✅
```

---

## 📝 INSTRUCCIONES DE INTEGRACIÓN

### Paso 1: Ubicar sección oe3 en config.yaml
```bash
grep -n "^oe3:" configs/default.yaml
# Salida: 130:oe3:
```

### Paso 2: Estructura BEFORE (actual)
```yaml
oe3:
  dataset:
    name: oe3_simulations_v2
    template_name: ...
  grid:
    carbon_intensity_kg_per_kwh: 0.4521
    ...
```

### Paso 3: Estructura AFTER (con FIX #3)
```yaml
oe3:
  sac:                          # ✅ NUEVO
    episodes: 50
    batch_size: 256
    ...
  
  reward:                        # ✅ NUEVO
    weight_co2: 0.50
    weight_solar: 0.20
    ...
  
  grid:                          # ✅ ACTUALIZADO (agregar si no existe)
    carbon_intensity_kg_per_kwh: 0.4521
    ...
  
  dataset:
    name: oe3_simulations_v2
    ...
```

### Paso 4: Verificar sintaxis YAML
```bash
python -c "import yaml; yaml.safe_load(open('configs/default.yaml'))" && echo "✅ YAML válido"
```

### Paso 5: Verificar que SAC puede cargar config
```bash
python -c "
from iquitos_citylearn.config import load_config
cfg = load_config()
print('Episodes:', cfg['oe3']['sac']['episodes'])
print('Weight CO2:', cfg['oe3']['reward']['weight_co2'])
print('✅ Config loaded successfully')
"
```

---

## 🔗 REFERENCIAS A OTROS FIXES

- **FIX #1:** `FIX_1_LOADER_YAML_SAC.py` - Implementa `_extract_sac_config_from_yaml()`
- **FIX #2:** `FIX_2_MULTIOBJETIVO_WRAPPER_SAC.py` - Implementa `MultiObjectiveRewardWrapper`
- **FIX #3:** Este documento - Configurationn YAML
