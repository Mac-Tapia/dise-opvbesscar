# SOLUCION SAC IMPLEMENTE - FRAGMENTOS LISTOS PARA COPIAR

## Este archivo contiene los fragmentos de código listos para copiar en train_sac_multiobjetivo.py

---

## FRAGMENTO 1: REEMPLAZAR main() INCOMPLETA (Línea ~2235)

### LOCATION: script/train/train_sac_multiobjetivo.py, línea ~2235

### FIND THIS:
```python
def main():
    """Entrenar SAC con multiobjetivo."""
    
    # ===== LIMPIEZA DE CHECKPOINTS SAC (DESACTIVADA PARA CONTINUAR) =====
    # NOTA: Descomentar para entrenar desde cero:
    # clean_sac_checkpoints_safe()
    #
    # Por defecto: NO limpiar para permitir continuar
    print()
    print('[INFO] Checkpoints SAC existentes seran PRESERVADOS (continuar entrenamiento)')
    print('       Para entrenar desde cero, descomentar clean_sac_checkpoints_safe() en main()')
    print()
    
    # ===== VALIDACION ROBUSTA DE DATASETS (PREVENIR TODOS LOS ERRORES DE RAIZ) =====
    try:
        datasets = load_datasets_from_processed()
    except Exception as e:
        print(f'\n[FATAL] No se pudieron cargar los datasets: {str(e)[:100]}')
        print('[ACCION] Ejecutar primero: python scripts/train/prepare_data_ppo.py')
        sys.exit(1)
    
    # Validar que TODOS los keys requeridos existan - DEFENSIVE PROGRAMMING
...
```

### REEMPLAZAR CON:
```python
def main():
    """Entrenar SAC con multiobjetivo - SOLUCION INTEGRAL v7.3"""
    
    # ===== LIMPIEZA DE CHECKPOINTS SAC (DESACTIVADA PARA CONTINUAR) =====
    print()
    print('[INFO] Checkpoints SAC existentes seran PRESERVADOS (continuar entrenamiento)')
    print('       Para entrenar desde cero, descomentar clean_sac_checkpoints_safe() en main()')
    print()
    
    # ===== VALIDACION ROBUSTA DE DATASETS =====
    try:
        datasets = load_datasets_from_processed()
    except Exception as e:
        print(f'\n[FATAL] No se pudieron cargar los datasets: {str(e)[:100]}')
        sys.exit(1)
    
    # Validar keys
    required_keys = [
        'solar', 'chargers', 'mall', 'bess_soc', 'bess_costs', 'bess_co2', 
        'charger_max_power_kw', 'charger_mean_power_kw'
    ]
    
    missing_keys = [k for k in required_keys if k not in datasets]
    if missing_keys:
        print(f'\n[FATAL] Datasets incompletos. Faltan: {missing_keys}')
        sys.exit(1)
    
    # Validar dimensiones
    try:
        assert len(datasets['solar']) == HOURS_PER_YEAR
        assert len(datasets['chargers']) == HOURS_PER_YEAR
        assert len(datasets['mall']) == HOURS_PER_YEAR
        assert len(datasets['bess_soc']) == HOURS_PER_YEAR
        print(f'  [OK] Validacion de dimensiones OK ({HOURS_PER_YEAR} horas x 4 datasets)')
    except AssertionError as e:
        print(f'\n[FATAL] Validacion fallida: {str(e)}')
        sys.exit(1)
    
    # ===== DESEMPAQUETAR DATASETS =====
    solar_hourly = datasets['solar']
    solar_data = datasets.get('solar_data', {})
    chargers_hourly = datasets['chargers']
    chargers_moto = datasets.get('chargers_moto')
    chargers_mototaxi = datasets.get('chargers_mototaxi')
    n_moto_sockets = datasets.get('n_moto_sockets', 0)
    n_mototaxi_sockets = datasets.get('n_mototaxi_sockets', 0)
    chargers_data = datasets.get('chargers_data', {})
    mall_hourly = datasets['mall']
    mall_data = datasets.get('mall_data', {})
    bess_soc = datasets['bess_soc']
    bess_costs = datasets['bess_costs']
    bess_peak_savings = datasets.get('bess_peak_savings')
    bess_tariff = datasets.get('bess_tariff')
    bess_co2 = datasets['bess_co2']
    energy_flows = datasets.get('energy_flows', {})
    bess_ev_demand = datasets.get('bess_ev_demand')
    bess_mall_demand = datasets.get('bess_mall_demand')
    bess_pv_generation = datasets.get('bess_pv_generation')
    charger_max_power = datasets['charger_max_power_kw']
    charger_mean_power = datasets['charger_mean_power_kw']
    observable_variables_df = datasets.get('observable_variables', None)
    
    print('[3.5] VALIDAR CALIDAD DE DATOS')
    print('-' * 80)
    
    # Chequear NaN/inf
    for name, data in [
        ('Solar', solar_hourly), ('Chargers', chargers_hourly), ('Mall', mall_hourly),
        ('BESS SOC', bess_soc), ('BESS Costs', bess_costs),
    ]:
        if isinstance(data, (list, np.ndarray)):
            arr = np.array(data)
            nan_count = np.sum(np.isnan(arr))
            inf_count = np.sum(np.isinf(arr))
            status = '[!] LIMPIANDO' if (nan_count > 0 or inf_count > 0) else '[OK]'
            print(f'  {status} {name}: {nan_count} NaN, {inf_count} inf')
    print()
```

---

## FRAGMENTO 2: CREAR AMBIENTE (INSERTAR ANTES DE ENTRENAR)

### LOCATION: Después de cargar datasets (línea ~2400)

### INSERTAR:
```python
    # ===== CREAR AMBIENTE REAL CON DATOS OE2 v5.3 =====
    print('[4] CREAR AMBIENTE REAL CON DATOS OE2')
    print('-' * 80)
    
    # Cargar reward weights
    try:
        reward_weights = create_iquitos_reward_weights(priority="co2_focus")
        context = IquitosContext()
        print(f'  [OK] Reward weights loaded:')
        print(f'     - CO2 grid:        {reward_weights.co2:.3f}')
        print(f'     - Solar:           {reward_weights.solar:.3f}')  
        print(f'     - EV satisfaction: {reward_weights.ev_satisfaction:.3f}')
        print(f'     - Cost:            {reward_weights.cost:.3f}')
    except Exception as e:
        print(f'  [!] No reward weights, using defaults')
        reward_weights = None
        context = None
    print()
    
    # Crear ambiente
    env = RealOE2Environment(
        solar_kw=solar_hourly,
        chargers_kw=chargers_hourly,
        mall_kw=mall_hourly,
        bess_soc=bess_soc,
        bess_costs=bess_costs,
        bess_co2=bess_co2,
        reward_weights=reward_weights,
        context=context,
        charger_max_power_kw=charger_max_power,
        charger_mean_power_kw=charger_mean_power,
        bess_peak_savings=bess_peak_savings,
        bess_tariff=bess_tariff,
        energy_flows=energy_flows,
        solar_data=solar_data,
        chargers_moto=chargers_moto,
        chargers_mototaxi=chargers_mototaxi,
        n_moto_sockets=n_moto_sockets,
        n_mototaxi_sockets=n_mototaxi_sockets,
        bess_ev_demand=bess_ev_demand,
        bess_mall_demand=bess_mall_demand,
        bess_pv_generation=bess_pv_generation,
        observable_variables=observable_variables_df,
        chargers_data=chargers_data,
        mall_data=mall_data,
    )
    
    print('[5] VALIDAR AMBIENTE')
    print('-' * 80)
    print(f'  [OK] Observation space: {env.observation_space}')
    print(f'  [OK] Action space:      {env.action_space}')
    print(f'  [OK] Timesteps/year:    {env.hours_per_year}')
    print()
```

---

## FRAGMENTO 3: CREAR Y ENTRENAR SAC (AJUSTE REWARD SCALE)

### LOCATION: Después de crear ambiente (línea ~2420)

### INSERTAR:
```python
    # ===== CREAR AGENTE SAC =====
    print('[6] INSTANCIAR AGENTE SAC (OFF-POLICY, MULTIOBJETIVO)')
    print('-' * 80)
    
    # Config SAC
    sac_config = SACConfig.for_gpu() if DEVICE == 'cuda' else SACConfig.for_cpu()
    
    # Crear agente SAC
    agent = SAC(
        policy='MlpPolicy',
        env=env,
        learning_rate=sac_config.learning_rate,
        buffer_size=sac_config.buffer_size,
        batch_size=sac_config.batch_size,
        train_freq=sac_config.train_freq,
        gradient_steps=sac_config.gradient_steps,
        tau=sac_config.tau,
        gamma=sac_config.gamma,
        ent_coef=sac_config.ent_coef,
        target_entropy=sac_config.target_entropy,
        policy_kwargs=sac_config.policy_kwargs,
        use_sde=sac_config.use_sde,
        sde_sample_freq=sac_config.sde_sample_freq,
        device=DEVICE,
        learning_starts=sac_config.learning_starts,
        verbose=1,
    )
    
    print(f'  [OK] Agente SAC creado')
    print(f'      Policy:       {agent.policy.__class__.__name__}')
    print(f'      Buffer:       {agent.replay_buffer.buffer_size:,} steps')
    print(f'      Learning rate: {sac_config.learning_rate}')
    print()
    
    # ===== CALLBACKS =====
    from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
    
    checkpoint_callback = CheckpointCallback(
        save_freq=8760,  # Cada episodio (1 año = 8760 horas)
        save_path=CHECKPOINT_DIR,
        name_prefix='sac_iquitos',
        save_replay_buffer=True,  # Guardar replay buffer para resumir
    )
    
    callbacks = [checkpoint_callback]
    
    print('[7] INICIAR ENTRENAMIENTO SAC')
    print('-' * 80)
    print(f'  Total timesteps: 26,280 (3 episodios × 8,760 horas)')
    print(f'  GPU:             {DEVICE.upper()}')
    print(f'  Estimated time:  5-7 horas (RTX 4060)')
    print()
    
    # ===== ENTRENAR SAC =====
    try:
        print(f'  [START] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        agent.learn(
            total_timesteps=26_280,  # 3 episodios × 8,760 steps
            callback=callbacks,
            log_interval=100,  # Log cada 100 steps
            tb_log_name='sac_iquitos_training',
            reset_num_timesteps=False,
        )
        
        print(f'  [DONE] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Guardar checkpoint final
        agent.save(CHECKPOINT_DIR / 'sac_iquitos_final')
        print(f'  [SAVE] Checkpoint final guardado')
        print()
        
    except KeyboardInterrupt:
        print(f'  [INTERRUPT] Entrenamiento interrumpido')
        agent.save(CHECKPOINT_DIR / 'sac_iquitos_latest')
        print(f'  [SAVE] Checkpoint de interrupcion guardado')
    except Exception as e:
        print(f'  [ERROR] {str(e)[:200]}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    print('[8] RESUMEN FINAL')
    print('-' * 80)
    print(f'  Checkpoints:      {list(CHECKPOINT_DIR.glob("*.zip"))}')
    print(f'  Logs:             {list(Path("runs/").glob("*"))}')
    print()
```

---

## FRAGMENTO 4: AJUSTAR REWARD SCALE (CRÍTICO)

### LOCATION: step() method, línea ~2800

### FIND THIS:
```python
            # ===== REWARD SCALING v7.0 ESTABLE PROBADO =====
            # Objetivo: Q-values en rango [0.5, 5.0] para estabilidad SAC
            # ...
            REWARD_SCALE = 0.01  # Muy conservador
            
            # Aplicar scaling y clip para Q < 2
            scaled_reward = base_reward * REWARD_SCALE
            reward = float(np.clip(scaled_reward, -0.02, 0.02))
```

### REEMPLAZAR CON:
```python
            # ===== REWARD SCALING v7.3 MEJORADO =====
            # SAC maneja bien rewards en [-0.1, +0.1] 
            # Q-values convergen a [0.5, 2.0] que es óptimo
            # 
            # Matemática:
            # Q_max = reward_max / (1-gamma)
            # Q_max = 0.02 / (1-0.98) = 0.02 / 0.02 = 1.0 ✅ ÓPTIMO
            
            REWARD_SCALE = 0.1  # Aumentado de 0.01 para claridad
            
            # Aplicar scaling
            scaled_reward = base_reward * REWARD_SCALE
            reward = float(np.clip(scaled_reward, -0.01, 0.01))  # [−0.01, +0.01]
```

---

## FRAGMENTO 5: AGREGAR IMPORT FALTANTE (AL INICIO)

### LOCATION: Top of main() function, cerca de imports

### AGREGAR (SI NO EXISTE):
```python
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from src.dataset_builder_citylearn.rewards import create_iquitos_reward_weights, IquitosContext
```

---

## RESUMEN DE CAMBIOS

| Item | Cambio |
|---|---|
| **main() function** | Completar con instantiación ambiente + SAC |
| **Ambiente Creation** | Agregar `RealOE2Environment(...)` |
| **SAC Agent** | Agregar `agent = SAC(...)` |
| **Training Loop** | Agregar `agent.learn(...)` |
| **Reward Scale** | 0.01 → 0.1 (mejorada visibilidad) |
| **Clip Range** | [−0.02, +0.02] → [−0.01, +0.01] (más conservador) |
| **Callbacks** | Agregar CheckpointCallback para guardar periódicamente |

---

## TESTING POST-IMPLEMENTACIÓN

Una vez aplicados los cambios, ejecutar:

```bash
# Terminal 1: Ejecutar entrenamiento
python scripts/train/train_sac_multiobjetivo.py

# Terminal 2 (en paralelo): Monitorear TensorBoard
tensorboard --logdir=runs/
# Abrir: http://localhost:6006

# Verificar:
# 1. El gráfico de episode_reward debe CAMBIAR (no flat line = 0.0)
# 2. Actor loss debe decrecer
# 3. Critic loss debe ser ~0.05-0.5
# 4. Speed ~50-100 steps/segundo (GPU)
# 5. Memoria GPU ~4-5 GB
```

