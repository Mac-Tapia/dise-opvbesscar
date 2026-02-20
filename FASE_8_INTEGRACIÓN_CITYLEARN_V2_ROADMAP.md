📋 PRÓXIMAS ACCIONES: FASE 8 - INTEGRACIÓN CITYLEARN V2 + RL TRAINING

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

⏰ ESTADO ACTUAL: Fase 7 (Costs HP/HFP) ✅ COMPLETADA

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

🚀 FASE 8: INTEGRACIÓN CON CITYLEARN V2 + AGENTS RL

OBJETIVO:
Entrenar agentes RL (SAC/PPO/A2C) usando datasets BESS con cálculo de costos HP/HFP integrado
para optimizar ahorros tarifarios en operación EV + Mall.

DEPENDENCIAS CUMPLIDAS:
✅ Dataset BESS: 27 columnas (EV Exclusive) con tariffs y costos
✅ Dataset BESS: 32 columnas (Arbitrage) con tariffs y costos  
✅ Tariff Constants: OSINERGMIN integrayadas en bess.py (0.45 HP / 0.28 HFP)
✅ Validation: Ambas funciones comprobadas, resultados coherentes
✅ Hour Detection: 1,825 HP + 6,935 HFP detectadas correctamente/año

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

📊 CARACTERÍSTICAS NUEVAS DISPONIBLES PARA AGENTS RL

COLUMNAS OBSERVABLES DIRENTES (Parte de estado agente):

1. tariff_period (object)
   - Valores: "HP" o "HFP"
   - Uso RL: Feature categórica = one-hot encode [is_HP, is_HFP]
   - Impacto: Cambia reward function dinámicamente per observation

2. tariff_rate_soles_kwh (float)
   - Valores: 0.28 o 0.45
   - Uso RL: Feature numérica directa, normalizada [0,1]
   - Impacto: Scaling de costos evitados en reward calculation

3. tariff_index_hp_hfp (float)
   - Valores: 1.0 (HFP) o 1.607 (HP)
   - Uso RL: Multiplicador dinámico del precio de grid
   - Impacto: Sistema de priorización automática (más agresivo en HP)

4. cost_avoided_by_bess_soles (float)
   - Valores: Costo evitado si BESS descargar (S/./kWh × cantidad)
   - Uso RL: Reward feedback directo en pesos monetarios
   - Impacto: Alignment incentivos económicos ↔ CO2

5. cost_savings_hp_soles / cost_savings_hfp_soles (float)
   - Valores: Ahorros diferenciados por periodo tarifario
   - Uso RL: Multi-objective reward (HP prioritario si factor > 1)
   - Impacto: Incentiva descarga máxima durante 18:00-22:59h

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

🎯 CONFIGURACIÓN RECOMENDADA AGENTS RL (v5.7)

REWARD FUNCTION ACTUALIZADA:

r(s,a) = w_co2 × co2_avoided           +
         w_hp × cost_savings_hp_soles  +  ← NEW: Tariff-aware (1.607x weight if HP!)
         w_hfp × cost_savings_hfp_soles +  ← NEW: Secondary reward
         w_solar × solar_utilization   +
         w_stab × -|power_ramp|        +
         w_charge × ev_charge_progress

PESO RECOMENDADOS (basados en importancia tarifaria):
  w_hp = 0.40      (Prioridad máxima peak hour optimization)
  w_hfp = 0.15     (Secundario: PV valorización)
  w_co2 = 0.25     (Objetivo primario del proyecto)
  w_solar = 0.10   (Autoconsumption)
  w_stab = 0.05    (Grid stability)
  w_charge = 0.05  (EV completion)
  ────────────────
  TOTAL = 1.00 ✓

JUSTIFICACIÓN:
  • HP tiene Mayor impacto económico (0.17 S/./kWh diferencial)
  • Arbitrage potencial 3.4x vs EV Exclusive en HP
  • CO2 y tariffs alineados (menos grid → menos CO2)

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

🔧 PASOS DE IMPLEMENTACIÓN

PASO 1: Exportar datasets con nuevas columnas
───────────────────────────────────────────────
  Código:
  ```python
  # En script de entrenamiento:
  from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_ev_exclusive
  
  # Simular con datos EV + Mall
  df_bess = simulate_bess_ev_exclusive(
      solar_generation=[...],  # 8,760 valores
      ev_demand=[...],
      mall_demand=[...],
      bess_capacity=1700,
      initial_soc=850
  )
  
  # df_bess ahora tiene 27 columnas incluyendo:
  # tariff_period, tariff_rate_soles_kwh, cost_avoided_by_bess_soles, etc.
  
  df_bess.to_csv('data/bess_training_data_v57.csv', index=False)
  ```

  Verificación:
  ```python
  assert len(df_bess) == 8760, "Dataset debe tener 8,760 horas"
  assert 'tariff_period' in df_bess.columns, "Tariff period missing"
  assert df_bess['tariff_period'].value_counts()['HP'] == 1825, "HP hours"
  assert df_bess['tariff_period'].value_counts()['HFP'] == 6935, "HFP hours"
  print("✓ Dataset validado para Phase 8")
  ```

PASO 2: Actualizar CityLearn v2 wrapper
────────────────────────────────────────
  En clase wrapper (ej: BuildingEnv):
  ```python
  def _get_observation(self):
      obs = super()._get_observation()  # Observaciones base
      
      # Agregar características tarifarias
      hour_of_day = self.time_step % 24
      is_hp = 18 <= hour_of_day < 23
      
      tariff_period = np.array([1.0, 0.0]) if is_hp else [0.0, 1.0]  # One-hot
      tariff_rate = 0.45 if is_hp else 0.28
      
      # Concatenar con observación existente
      obs = np.concatenate([obs, tariff_period, [tariff_rate]])
      
      return obs
  ```

  Impacto en observation space:
  - Original: 394 dim (CityLearn v2 default)
  - Nuevo: 394 + 2 (one-hot) + 1 (rate) = 397 dim ✓

PASO 3: Integrar reward function con costos HP/HFP
─────────────────────────────────────────────────────
  En método reward (ej: SAC agent):
  ```python
  def compute_reward(self, observations, actions, data):
      # Extraer del dataset BESS (df_bess.iloc[time_step])
      cost_savings_hp = data['cost_savings_hp_soles'].iloc[self.time_step]
      cost_savings_hfp = data['cost_savings_hfp_soles'].iloc[self.time_step]
      co2_avoided = data['co2_avoided_kg'].iloc[self.time_step]
      
      # Multi-objective reward
      reward = (
          0.40 * cost_savings_hp +      # Peak hour optimization
          0.15 * cost_savings_hfp +     # Off-peak valorization
          0.25 * co2_avoided +          # CO2 minimization
          0.10 * self.solar_util +      # Solar self-consumption
          ...
      )
      
      return reward
  ```

PASO 4: Entrenar agentes (SAC recomendado)
──────────────────────────────────────────
  ```bash
  # Script existente adaptado:
  python scripts/train/train_sac_multiobjetivo.py \
      --data "data/bess_training_data_v57.csv" \
      --hp_weight 0.40 \
      --hfp_weight 0.15 \
      --co2_weight 0.25 \
      --learning_rate 1e-4 \
      --timesteps 100000
  
  # Output esperado:
  # checkpoints/SAC/sac_model_v57_ahorros_hp_optimized.zip
  # logs/reward_breakdown_hp_hfp.csv (tracking de rewards por periodo)
  ```

PASO 5: Validar resultados post-entrenamiento
──────────────────────────────────────────────
  ```python
  from stable_baselines3 import SAC
  
  # Cargar agente entrenado
  model = SAC.load('checkpoints/SAC/sac_model_v57_ahorros_hp_optimized.zip')
  
  # Ejecutar episodio y extraer métricas
  obs = env.reset()
  total_hp_savings = 0
  total_hfp_savings = 0
  
  for step in range(8760):
      action, _ = model.predict(obs, deterministic=True)
      obs, reward, done, info = env.step(action)
      
      # Acumular ahorros diferenciados
      if env.data.iloc[step]['tariff_period'] == 'HP':
          total_hp_savings += env.data.iloc[step]['cost_savings_hp_soles']
      else:
          total_hfp_savings += env.data.iloc[step]['cost_savings_hfp_soles']
  
  # Verificar mejora vs baseline
  baseline_hp_savings = 11432  # EV Exclusive (de Phase 7)
  baseline_total = 70259       # EV Exclusive total
  
  improvement_hp = ((total_hp_savings - baseline_hp_savings) / baseline_hp_savings) * 100
  print(f"✓ Mejora HP: {improvement_hp:.1f}%")
  ```

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

📈 MÉTRICAS CLAVE A TRACKEAR

1. AHORROS DIFERENCIADOS (Costo):
   • HP savings per episode (debería ser > 11,432 S/./año vs baseline)
   • HFP savings per episode (debería ser > 58,827 S/./año vs baseline)
   • Total BESS savings (meta: > 80,000 S/./año)

2. CO2 EMISSIONS:
   • kg CO2/year (meta: < 10,200 kg vs baseline ~10,200)
   • kg CO2 per HP hour (durante peak, debe ser < 0.30 kg/h)

3. SOLAR METRICS:
   • Solar self-consumption % (meta: > 65%)
   • Solar curtailment (meta: < 5%)

4. TECHNICAL:
   • EV charge completion rate (meta: 100%)
   • BESS cycle efficiency (meta: > 94%)
   • Power ramp smoothness (σ < 10 kW)

5. CONVERGENCE:
   • Training stability (reward variance < 5% after episode 500)
   • Policy entropy (should decrease over time)

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

⚠️  CONSIDERACIONES CRITICAS

1. FEATURE SCALING:
   ├─ tariff_rate_soles_kwh: Range [0.28, 0.45]
   │  └─ Normalizar a [0, 1] antes de enviar a agentes
   ├─ cost_savings_*_soles: Range [0, ~500 S/./h]
   │  └─ Dividir por 500 o usar scaler (StableBaselines3 RewardScaler)
   └─ Action bounds: [0, 1] normalizado → multiplicar por capacity en step()

2. TEMPORAL CONSISTENCY:
   ├─ tariff_period debe cambiar EXACTAMENTE cada 24h (18→23→00)
   ├─ Verificar sincronización con gym.spaces.Discrete(8760) timesteps
   └─ Si hay desincronización, cost_savings será zero en horas equivocadas

3. DATA LEAKAGE:
   ├─ NO incluir "tariff_period" like strings directamente en obs
   │  (Agentes muy simpl podría aprender a "jugar" sistema)
   ├─ En su lugar: Usar tariff_index (1.0 o 1.607) como precio relativo
   └─ O: One-hot encode ["is_HP"], que agente aprenda implicatamente

4. BASELINE COMPARISON:
   ├─ Comparar RL vs EV Exclusive (S/. 70,259/año)
   ├─ Comparar RL vs Arbitrage (S/. 52,080/año BESS savings)
   ├─ Esperar mejora 5-15% sobre mejor baseline
   └─ Si mejora < 3%, revisar reward weights

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

📁 ARCHIVOS NECESARIOS PARA PHASE 8

✅ Datos:
   ├─ data/bess_training_data_v57.csv (27-32 columnas × 8,760 filas)
   ├─ data/solar_pv_generation_timeseries.csv (8,760 filas)
   ├─ data/chargers_ev_ano_2024_v3.csv (38 sockets)
   └─ data/mall_demand_profile.csv (hourly kWh)

✅ Código:
   ├─ src/agents/sac.py (actualizado para tariff features)
   ├─ src/agents/ppo_sb3.py (ídem)
   ├─ src/agents/a2c_sb3.py (ídem)  
   ├─ scripts/train/train_sac_multiobjetivo.py
   └─ src/utils/agent_utils.py (validate_env_spaces + reward scaling)

✅ Configuración:
   ├─ configs/default.yaml (actualizar reward weights)
   ├─ configs/agents/sac_v57_hp_optimized.yaml
   └─ configs/agents/ppo_v57_baseline.yaml

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

✅ CHECKLIST PRE-LAUNCH PHASE 8

□ Validar dataset 27-32 columnas × 8,760 rows
□ Verificar 0 NaN valores en tariff_period, cost_savings_*_soles
□ One-hot encode tariff_period o usar tariff_index como feature
□ Actualizar observation space en CityLearn wrapper
□ Implementar scaling para cost_savings (dividir por 500 o usar RewardScaler)
□ Actualizar reward function con w_hp=0.40, w_hfp=0.15
□ Crear logging para HP vs HFP savings por episodio
□ Test unitario: Verificar tariff changes cada 24h
□ Baseline run: Sin RL (uncontrolled) con nuevas columnas
□ 1-agent pilot: SAC con 10,000 timesteps para ver convergencia
□ Análisis: Histogramas ahorros HP/HFP vs baseline

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

🎬 ACCIÓN INMEDIATA

OPCIÓN A (RECOMENDADO): Validar & Preparar Datasets
  Tiempo: ~30 min
  1. Ejecutar validate_bess_dataset_v57.py
  2. Generar base data en /data/bess_training_data_v57.csv
  3. Verificar columnas y filas
  4. Crear informe de completeness (print → imagen)

OPCIÓN B: Comenzar Phase 8 Integration
  Tiempo: ~2 horas
  1. Actualizar CityLearn wrapper con tariff features
  2. Implementar scaling de costos
  3. Crear reward function v5.7
  4. Test single episode del wrapper

OPCIÓN C: Entrenar Piloto
  Tiempo: ~4 horas
  1. Ejecutar Phase A + B
  2. Entrenar SAC con 10K timesteps (5 min entrenamiento)
  3. Analizar convergencia reward
  4. Comparar vs baseline (HP savings alcanzados)

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

📞 APOYO & REFERENCIAS

Documentación:
- RESUMEN_IMPLEMENTACION_COSTOS_HP_HFP_v5.7.md (Cambios recientes)
- src/dimensionamiento/oe2/disenobess/bess.py (Código actualizado)
- validacion_costos_hp_hfp.py (Tests de validación)

Valores Clave (MEMORIZAR):
- HP: 0.45 S/./kWh, 18:00-22:59 (1,825 horas/año)
- HFP: 0.28 S/./kWh, 00:00-17:59 + 23:00-23:59 (6,935 horas/año)
- Diferencial: 0.17 S/./kWh
- EV Exclusive baseline: S/. 70,259/año
- Arbitrage baseline: S/. 52,080/año + S/. 130,260 costo evitado

═════════════════════════════════════════════════════════════════════════════════════════════════════════════

Status Completeness: FASE 7 ✅ | FASE 8 🚀 READY
Last Update: 2026-02-20
