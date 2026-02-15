# 📋 GUÍA DE IMPLEMENTACIÓN: SAC v6.0 Sistema de Comunicación
**Versión**: 6.0  
**Fecha**: 2026-02-14  
**Estado**: 🟢 READY FOR IMPLEMENTATION  
**Estimación**: 2-3 semanas  

---

## ÍNDICE

1. [Resumen Ejecución](#resumen)
2. [Fase 1: Stack Base (3-4 días)](#fase-1)
3. [Fase 2: Integración Datos (2-3 días)](#fase-2)
4. [Fase 3: Entrenamiento (5-7 días)](#fase-3)
5. [Fase 4: Validación (2-3 días)](#fase-4)
6. [Checklist Detallado](#checklist)

---

## RESUMEN EJECUCIÓN

### Objetivo Final

```
Entrenar SAC con observación 246-dim que incluye:
  ✅ SOC individual por socket [156-193]
  ✅ Tiempo restante por socket [194-231]
  ✅ Comunicación BESS↔EVs [232-233]
  ✅ Comunicación Solar↔EVs [234-235]
  ✅ Comunicación Grid↔EVs [236-237]
  ✅ Señales de prioridad/urgencia/capacidad [238-245]

Resultado esperado:
  +130-160 vehículos/día (vs 150 actual)
  -13% grid import
  +300-800 kg CO2 indirecto evitado
  2x convergencia más rápida
```

### Timeline

| Fase | Tarea | Duración | Responsable |
|------|-------|----------|-------------|
| 1 | Extender environment a 246-dim | 1 día | Engineer |
| 1 | Implementar VehicleSOCTracker v2 | 1 día | Engineer |
| 1 | Recompensa v6.0 (w_vehicles) | 1 día | Engineer |
| 2 | Cargar datos reales OE2 | 1 día | Data |
| 2 | Validación cascada | 1 día | Engineer |
| 3 | Configure SAC + training loop | 1 día | Engineer |
| 3 | Train SAC (15 episodios) | 7 días | GPU |
| 4 | Validar resultados | 1 día | Engineer |
| 4 | Comparativas v5.3 vs v6.0 | 1 día | Data Science |
| 4 | Documentación final | 1 día | Engineer |
| **TOTAL** | | **14-16 días** | |

---

## FASE 1: Stack Base (Código)

### Tarea 1.1: Extender RealOE2Environment a 246-dim

**File**: `scripts/train/train_sac_multiobjetivo.py` (Extensión)

**Pseudocódigo**:

```python
class RealOE2Environment(Env):
    
    OBS_DIM_V53: int = 156  # Actual (ya implementado)
    OBS_DIM_COMMUNICATION_V6: int = 90  # NUEVO
    OBS_DIM: int = 246  # NUEVO TOTAL
    
    def __init__(self, ...):
        # (Anterior code)
        # OBS DIM ya era 156, ahora +90 = 246
        self.observation_space = spaces.Box(
            low=-1e6, high=1e6,
            shape=(246,),  # ⭐ Cambiar de 156 a 246
            dtype=np.float32
        )
```

**Paso a Paso**:

1. **[156-193] Socket SOC tracking**
   ```python
   # En _make_observation():
   
   for i in range(self.NUM_CHARGERS):
       state = self.socket_states[i]
       if state is not None and state.is_connected:
           soc_normalized = state.current_soc / 100.0
       else:
           soc_normalized = 0.0
       
       obs[156 + i] = np.clip(soc_normalized, 0.0, 1.0)
   ```
   
   **Tests**:
   - [ ] obs[156:194].shape == (38,)
   - [ ] obs[156:194] range ∈ [0, 1]
   - [ ] obs value cambia cuando SOC cambia ✓

2. **[194-231] Socket time remaining**
   ```python
   for i in range(self.NUM_CHARGERS):
       state = self.socket_states[i]
       if state is not None and state.is_connected:
           # Tiempo estimado = (100 - SOC) / 20% por hora
           remaining_soc = 100.0 - state.current_soc
           hours_to_charge = remaining_soc / 20.0  # ~5 horas típico
           time_normalized = np.clip(hours_to_charge / 8.0, 0.0, 1.0)
       else:
           time_normalized = 0.0
       
       obs[194 + i] = time_normalized
   ```
   
   **Tests**:
   - [ ] obs[194:232].shape == (38,)
   - [ ] obs[194:232] range ∈ [0, 1]
   - [ ] Cuando SOC=10%, time ≈ 0.5 (4h/8h)
   - [ ] Cuando SOC=95%, time ≈ 0.06 (0.5h/8h)

3. **[232-233] BESS dispatch signals**
   ```python
   bess_available_power_kw = (bess_soc_percent / 100.0) * BESS_CAPACITY_KWH / 10.0
   obs[232] = np.clip(bess_available_power_kw / BESS_MAX_POWER_KW, 0.0, 1.0)
   obs[233] = np.clip(bess_available_power_kw / BESS_MAX_POWER_KW, 0.0, 1.0)
   ```
   
   **Tests**:
   - [ ] obs[232], obs[233] ∈ [0, 1]
   - [ ] Cuando BESS SOC=100%, obs[232,233]=1.0
   - [ ] Cuando BESS SOC=0%, obs[232,233]=0.0

4. **[234-235] Solar bypass signals**
   ```python
   obs[234] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)
   obs[235] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)
   ```
   
   **Tests**:
   - [ ] obs[234,235] track solar_kw
   - [ ] Mediodía (solar=2800): obs ≈ 0.68
   - [ ] Noche (solar=0): obs = 0.0

5. **[236-237] Grid import signals**
   ```python
   total_ev_demand = np.sum(socket_demands)
   grid_import_needed = max(0.0, total_ev_demand - solar_kw - bess_available)
   
   obs[236] = np.clip(grid_import_needed / 500.0, 0.0, 1.0)  # Motos
   obs[237] = np.clip(grid_import_needed / 500.0, 0.0, 1.0)  # Taxis
   ```
   
   **Tests**:
   - [ ] obs[236,237] = 0 cuando solar+BESS suficientes
   - [ ] obs[236,237] > 0 cuando hay grid import

6. **[238-245] Agregados críticos**
   ```python
   # Prioridad actual cargando
   priority_motos = sum(s.get_priority_weight() for s in states if moto) / 30
   priority_taxis = sum(s.get_priority_weight() for s in states if taxi) / 8
   obs[238] = priority_motos
   obs[239] = priority_taxis
   
   # Urgencia de completar
   motos_not_charged = 270 - self.soc_tracker.total_motos_charged_100
   taxis_not_charged = 39 - self.soc_tracker.total_mototaxis_charged_100
   obs[240] = np.clip(motos_not_charged / 270.0, 0.0, 1.0)
   obs[241] = np.clip(taxis_not_charged / 39.0, 0.0, 1.0)
   
   # Capacidad disponible
   motos_free = 30 - motos_connected
   taxis_free = 8 - taxis_connected
   obs[242] = motos_free / 30.0
   obs[243] = taxis_free / 8.0
   
   # Correlación solar-demanda
   total_demand = total_ev_demand + mall_kw
   obs[244] = np.clip(solar_kw / max(total_demand, 1.0), 0.0, 2.0) / 2.0
   
   # BESS SOC redundante pero crítico
   obs[245] = bess_soc_percent / 100.0
   ```
   
   **Tests**:
   - [ ] obs[238:246].shape == (8,)
   - [ ] obs[238:246] range ∈ [0, 1] (except [244] mediodía)

**Total Work**: 1 día
**Deliverable**: RealOE2Environment with OBS_DIM=246 ✓

---

### Tarea 1.2: Implementar VehicleSOCTracker v2

**File**: `scripts/train/train_sac_multiobjetivo.py` (Extender clase)

**Cambios**:

```python
class VehicleSOCTracker:
    """Tracker mejorado con siguientes capacidades:
    
    1. Estado detallado por socket (actual: solo agregados)
    2. Priorización por SOC (100% > 80% > ... > 10%)
    3. Contadores de vehículos 100% completados
    4. Métricas de scarcity decisions
    """
    
    def update_vehicle_soc(self, socket_id: int, soc_increment_pct: float):
        """Actualiza SOC del vehículo en socket."""
        state = self.vehicle_states[socket_id]
        if state is None:
            return
        
        state.current_soc = min(100.0, state.current_soc + soc_increment_pct)
        
        # Si llegó a 100%, marcar como completado
        if state.current_soc >= 99.9 and not state.was_completed:
            if state.vehicle_type == 'moto':
                self.total_motos_charged_100 += 1
            else:
                self.total_mototaxis_charged_100 += 1
            state.was_completed = True
            state.is_connected = False  # Desconectar automáticamente
    
    def get_socket_metrics(self, socket_id: int) -> Dict:
        """Retorna métricas de socket individual."""
        state = self.vehicle_states[socket_id]
        if state is None:
            return {'connected': False}
        
        return {
            'connected': state.is_connected,
            'soc_pct': state.current_soc,
            'type': state.vehicle_type,
            'priority_weight': state.get_priority_weight(),
            'time_remaining_hours': (100 - state.current_soc) / 20.0,
            'is_100_percent': state.current_soc >= 99.9,
        }
```

**Tests**:
- [ ] Vehículo cargado incrementa SOC
- [ ] Al 100% SOC, se marca completado + desconecta
- [ ] total_motos_charged_100 crece cuando moto llega 100%
- [ ] Prioridad sigue orden: 100%>80%>70%>50%>30%>20%>10%

**Total Work**: 1 día
**Deliverable**: VehicleSOCTracker v2 con tracking granular ✓

---

### Tarea 1.3: Recompensa v6.0 (añadir w_vehicles)

**File**: `scripts/train/train_sac_multiobjetivo.py` (Extender reward)

**Cambios**:

```python
# PESOS NUEVOS v6.0:
REWARD_WEIGHTS_V6 = {
    'co2': 0.45,              # (reducido de 0.50)
    'solar': 0.15,            # (igual)
    'vehicles_charged': 0.25, # ⭐ NUEVO, reemplaza EV_satisfaction
    'grid_stable': 0.05,      # (igual)
    'bess_efficiency': 0.05,  # (igual)
    'prioritization': 0.05,   # (igual)
}  # Total = 1.00 ✓

def _compute_reward(self, action, ...):
    """Recompensa v6.0 con w_vehicles."""
    
    # [1] CO2 Reduction (45%)
    r_co2 = -grid_import_kwh * CO2_FACTOR_IQUITOS * 0.001
    reward += 0.45 * r_co2
    
    # [2] Solar Utilization (15%)
    r_solar = solar_used_to_ev / max(total_ev_demand, 1.0)
    reward += 0.15 * r_solar
    
    # [3] VEHICLES CHARGED ⭐ NUEVO (25%)
    vehicles_completed_this_hour = count(
        self.soc_tracker.vehicle_states[i].current_soc >= 99.9
        for i in range(NUM_CHARGERS)
    )
    r_vehicles = vehicles_completed_this_hour / NUM_CHARGERS
    reward += 0.25 * r_vehicles
    self.episode_vehicles_charged += vehicles_completed_this_hour
    
    # [4] Grid Stability (5%)
    r_stability = 1.0 - min(1.0, grid_import_kw / 500.0)
    reward += 0.05 * r_stability
    
    # [5] BESS Efficiency (5%)
    bess_cycles = (charge_kwh + discharge_kwh) / (2 * BESS_CAPACITY)
    r_bess = 1.0 - min(1.0, bess_cycles / 0.5)
    reward += 0.05 * r_bess
    
    return reward
```

**Tests**:
- [ ] Sum(weights) = 1.00 ✓
- [ ] Reward positivo cuando hay vehículos charged > 0
- [ ] Reward crece con más vehículos completados
- [ ] CO2 aún penaliza grid import (no sacrificado)

**Total Work**: 1 día
**Deliverable**: Recompensa v6.0 implementada ✓

---

## FASE 2: Integración Datos (Data Pipeline)

### Tarea 2.1: Cargar datos reales OE2

**File**: `scripts/train/train_sac_sistema_comunicacion_v6.py` (ya existe)

O extender `scripts/train/train_sac_multiobjetivo.py`:

```python
def load_real_oe2_data():
    """Carga datos reales de OE2 Iquitos v5.3."""
    
    # 1. Solar
    solar_df = pd.read_csv('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
    solar_kw = solar_df['potencia_kw'].values.astype(np.float32)
    assert len(solar_kw) == 8760, f"Solar debe tener 8760 rows, tiene {len(solar_kw)}"
    
    # 2. Chargers (38 sockets)
    chargers_df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    socket_cols = [col for col in chargers_df.columns if 'socket_' in col and 'power' in col]
    chargers_kw = chargers_df[socket_cols[:38]].values.astype(np.float32)  # Exactamente 38
    assert chargers_kw.shape == (8760, 38), f"Chargers shape {chargers_kw.shape} != (8760, 38)"
    
    # 3. BESS
    bess_df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
    bess_soc = bess_df['soc_percent'].values.astype(np.float32)
    assert len(bess_soc) == 8760, f"BESS debe tener 8760 rows"
    
    # 4. Mall demand
    mall_df = pd.read_csv('data/oe2/demandamallkwh/demandamallhorakwh.csv', sep=';')
    mall_kw = mall_df['demanda'].values.astype(np.float32) / 1000.0  # Convert to kW if needed
    assert len(mall_kw) == 8760, f"Mall debe tener 8760 rows"
    
    print(f"✅ Loaded OE2 Data:")
    print(f"  Solar: {len(solar_kw)} hrs, max {solar_kw.max():.1f} kW")
    print(f"  Chargers: {chargers_kw.shape}")
    print(f"  BESS: {len(bess_soc)} hrs, range {bess_soc.min():.1f}%-{bess_soc.max():.1f}%")
    print(f"  Mall: {len(mall_kw)} hrs, max {mall_kw.max():.1f} kW")
    
    return solar_kw, chargers_kw, mall_kw, bess_soc
```

**Tests**:
- [ ] solar_kw.shape == (8760,)
- [ ] chargers_kw.shape == (8760, 38)
- [ ] mall_kw.shape == (8760,)
- [ ] bess_soc.shape == (8760,)
- [ ] All ranges reasonable (solar 0-4000, BESS 20-100%, etc.)

**Total Work**: 1 día
**Deliverable**: Data loader con validación ✓

---

### Tarea 2.2: Validación Cascada

**File**: `docs/VALIDACION_CASCADA_OE2.md` (crear)

**Script de validación**:

```python
def validate_cascada_oe2():
    """Valida que cascada solar suma correctamente."""
    
    bess_df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
    
    # Columnas cascada (ya están en el archivo)
    pv_total = bess_df['pv_generation'].sum()  # Total solar anual
    pv_to_bess = bess_df['pv_to_bess_kwh'].sum()
    pv_to_ev = bess_df['pv_to_ev_kwh'].sum()
    pv_to_mall = bess_df['pv_to_mall_kwh'].sum()
    pv_curtailed = bess_df['pv_curtailed_kwh'].sum()
    
    cascada_total = pv_to_bess + pv_to_ev + pv_to_mall + pv_curtailed
    
    diff = abs(pv_total - cascada_total)
    percentage_diff = (diff / pv_total) * 100 if pv_total > 0 else 0
    
    print(f"Cascada Validation:")
    print(f"  PV Total:       {pv_total:>12,.0f} kWh")
    print(f"  PV→BESS:        {pv_to_bess:>12,.0f} kWh ({pv_to_bess/pv_total*100:.1f}%)")
    print(f"  PV→EVs:         {pv_to_ev:>12,.0f} kWh ({pv_to_ev/pv_total*100:.1f}%)")
    print(f"  PV→Mall:        {pv_to_mall:>12,.0f} kWh ({pv_to_mall/pv_total*100:.1f}%)")
    print(f"  PV→Curtailed:   {pv_curtailed:>12,.0f} kWh ({pv_curtailed/pv_total*100:.1f}%)")
    print(f"  ─────────────────────────────────────")
    print(f"  Cascada Sum:    {cascada_total:>12,.0f} kWh")
    print(f"  Difference:     {diff:>12,.0f} kWh ({percentage_diff:.3f}%)")
    
    if diff < 1000:  # Menos de 1 MWh
        print(f"  ✅ CASCADA VÁLIDA (diff < 1 MWh)")
        return True
    else:
        print(f"  ❌ CASCADA INVÁLIDA (diff >= 1 MWh)")
        return False
```

**Tests**:
- [ ] pv_to_bess + pv_to_ev + pv_to_mall + pv_curtailed ≈ pv_total
- [ ] Diferencia < 1 MWh/año (< 0.01%)
- [ ] Reporte guardado en `docs/cascada_validation_report.csv`

**Total Work**: 1 día
**Deliverable**: Cascada validada ✓

---

## FASE 3: Entrenamiento (RL Training)

### Tarea 3.1: Configurar SAC + Training Loop

**File**: Crear `scripts/train/train_sac_v6.py` (copia mejorada)

```python
#!/usr/bin/env python3
"""Training SAC v6.0 con sistema de comunicación."""

from stable_baselines3 import SAC

def main():
    # Load data
    solar_kw, chargers_kw, mall_kw, bess_soc = load_real_oe2_data()
    
    # Create environment (v6.0)
    env = RealOE2Environment(
        solar_kw=solar_kw,
        chargers_kw=chargers_kw,
        mall_kw=mall_kw,
        bess_soc=bess_soc,
        reward_weights=REWARD_WEIGHTS_V6,
    )
    
    # SAC Config (optimizado)
    model = SAC(
        'MlpPolicy',
        env,
        learning_rate=1e-4,
        buffer_size=1_000_000,
        learning_starts=10_000,
        batch_size=256,
        train_freq=(1, 'step'),
        gradient_steps=2,
        gamma=0.99,
        tau=0.005,
        ent_coef=0.2,
        device='cuda',  # O 'cpu' si no hay GPU
        verbose=1,
    )
    
    # Callbacks
    callbacks = [
        CheckpointCallback(
            save_freq=1000,
            save_path='checkpoints/SAC/',
            name_prefix='sac_v6_'
        ),
    ]
    
    # Training
    print("Training SAC v6.0...")
    model.learn(
        total_timesteps=131_400,  # 15 episodes × 8,760 hours
        callback=callbacks,
        log_interval=100,
    )
    
    # Save final model
    model.save('checkpoints/SAC/sac_v6_final.zip')
    print("✅ Training completed!")

if __name__ == '__main__':
    main()
```

**Configuration**:
- Learning rate: 1e-4 (estable)
- Buffer: 1M (GPU memory)
- Batch: 256
- Total timesteps: 131,400 (15 episodios)

**Tests**:
- [ ] Environment loads without errors
- [ ] Model trains first 10 steps without NaN
- [ ] Checkpoints saved every 1000 steps
- [ ] GPU memory OK (<8GB RTX 4060)

**Total Work**: 1 día
**Deliverable**: Training script ready ✓

---

### Tarea 3.2: Monitor Training Progress

**File**: `scripts/train/monitor_training.py` (crear)

```python
def monitor_training(model, env, checkpoint_dir='checkpoints/SAC/'):
    """Monitor training progress every N steps."""
    
    import os
    
    checkpoints = sorted([f for f in os.listdir(checkpoint_dir) if f.endswith('.zip')])
    
    metrics = []
    for cp in checkpoints:
        model = SAC.load(os.path.join(checkpoint_dir, cp))
        
        # Evaluate
        obs, info = env.reset()
        episode_return = 0.0
        vehicles_charged = 0
        for step in range(8760):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = env.step(action)
            episode_return += reward
            vehicles_charged += info.get('vehicles_charged', 0)
            if done:
                break
        
        metrics.append({
            'checkpoint': cp,
            'episode_return': episode_return,
            'vehicles_charged': vehicles_charged,
        })
    
    # Report
    df_metrics = pd.DataFrame(metrics)
    df_metrics.to_csv('outputs/training_metrics.csv', index=False)
    print(df_metrics)
```

**Monitoring KPIs**:
- Episode return trend (debe crecer)
- Vehicles charged trend (debe alcanzar 280+)
- CO2 avoided (debe mantenerse > 7500)
- Grid import (debe bajar)

**Total Work**: Concurrent with training
**Deliverable**: Monitoring dashboard ✓

---

### Tarea 3.3: Training Execution

**GPU Hardware** (Requerido):
- RTX 4060 8GB VRAM (suficiente)
- O CPU (40 horas de entrenamiento)

**Expected Duration**:
- GPU: 6-8 horas (converge en 15 episodios)
- CPU: 40-48 horas

**Commands**:

```bash
# En terminal
cd d:\diseñopvbesscar

# Opción 1: GPU (recomendado)
python scripts/train/train_sac_v6.py --device cuda

# Opción 2: CPU (lento)
python scripts/train/train_sac_v6.py --device cpu

# Monitor (en otra terminal)
watch -n 30 "python scripts/train/monitor_training.py"
```

**Total Work**: 1 semana (GPU en background)
**Deliverable**: Trained model + logs ✓

---

## FASE 4: Validación (Resultados)

### Tarea 4.1: Validar Resultados

**File**: `scripts/validation/validate_sac_v6.py` (crear)

```python
def validate_sac_v6():
    """Valida que SAC v6.0 cumple objetivos."""
    
    model = SAC.load('checkpoints/SAC/sac_v6_final.zip')
    env = RealOE2Environment(...)
    
    # Run 1 full episode
    obs, _ = env.reset()
    metrics = {
        'episode_return': 0.0,
        'vehicles_charged': 0,
        'co2_avoided_kg': 0.0,
        'grid_import_kwh': 0.0,
    }
    
    for step in range(8760):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, truncated, info = env.step(action)
        
        metrics['episode_return'] += reward
        metrics['vehicles_charged'] += info.get('vehicles_charged', 0)
        metrics['co2_avoided_kg'] += info.get('co2_avoided_kg', 0)
        metrics['grid_import_kwh'] += info.get('grid_import_kwh', 0)
    
    # Validate thresholds
    print("\n" + "="*60)
    print("SAC v6.0 VALIDATION RESULTS")
    print("="*60)
    
    results = {}
    
    # Vehículos cargados
    results['vehicles_charged'] = {
        'value': metrics['vehicles_charged'],
        'threshold': 250,
        'pass': metrics['vehicles_charged'] >= 250,
    }
    
    # CO2 evitado
    results['co2_avoided'] = {
        'value': metrics['co2_avoided_kg'],
        'threshold': 7500,
        'pass': metrics['co2_avoided_kg'] >= 7500,
    }
    
    # Grid import (vs baseline)
    grid_import_percentage = metrics['grid_import_kwh'] / 12000.0 * 100  # 12k baseline
    results['grid_import'] = {
        'value': f"{grid_import_percentage:.1f}%",
        'threshold': "< 15%",
        'pass': grid_import_percentage < 15,  # Reduc del 12% baseline
    }
    
    # Reward
    results['episode_return'] = {
        'value': metrics['episode_return'],
        'threshold': 400,
        'pass': metrics['episode_return'] >= 400,
    }
    
    # Print report
    for metric, res in results.items():
        status = "✅" if res['pass'] else "❌"
        print(f"{status} {metric:25s}: {str(res['value']):>15s} (threshold: {res['threshold']})")
    
    # Overall pass
    all_pass = all(r['pass'] for r in results.values())
    print("="*60)
    print(f"Overall: {'✅ PASSED' if all_pass else '❌ FAILED'}")
    print("="*60)
    
    return all_pass
```

**Validation Checklist**:
- [ ] vehicles_charged >= 250 (goal 280-309)
- [ ] co2_avoided_kg >= 7500 (goal 7500-8000+)
- [ ] grid_import < 15% of baseline (vs 25% actual)
- [ ] episode_return >= 400 (vs 100-150 actual)
- [ ] Agent uses obs[156:194] (SOC per socket)
- [ ] Agent uses obs[194:232] (time per socket)
- [ ] Agent uses obs[232:235] (BESS/Solar signals)

**Total Work**: 1 día
**Deliverable**: Validation report ✓

---

### Tarea 4.2: Comparativas v5.3 vs v6.0

**File**: `reports/comparison_v53_vs_v6.md` (crear)

```python
def compare_v53_vs_v6():
    """Compara resultados SAC v5.3 vs v6.0."""
    
    # Load both models
    model_v53 = SAC.load('checkpoints/SAC/sac_v53_final.zip')
    model_v6 = SAC.load('checkpoints/SAC/sac_v6_final.zip')
    
    # Evaluate both (episodios múltiples)
    results = {'v5.3': [], 'v6.0': []}
    
    for model_name, model in [('v5.3', model_v53), ('v6.0', model_v6)]:
        for episode in range(3):  # 3 episodios averaged
            obs, _ = env.reset()
            metrics = {...}  # Misma estructura que valida_sac_v6()
            # Run episode, collect metrics
            results[model_name].append(metrics)
    
    # Create comparison table
    comparison = {
        'Metric': [
            'Vehicles Charged',
            'CO2 Avoided (kg)',
            'Grid Import (%)',
            'Episode Return',
            'Solar Utilization (%)',
            'BESS Efficiency (cycles/h)',
        ],
        'v5.3 Mean': [
            np.mean([r['vehicles_charged'] for r in results['v5.3']]),
            np.mean([r['co2_avoided_kg'] for r in results['v5.3']]),
            # ...
        ],
        'v6.0 Mean': [
            np.mean([r['vehicles_charged'] for r in results['v6.0']]),
            np.mean([r['co2_avoided_kg'] for r in results['v6.0']]),
            # ...
        ],
        'Improvement': [
            # Calculate % improvement
            # ...
        ],
    }
    
    df_comparison = pd.DataFrame(comparison)
    df_comparison.to_csv('reports/comparison_v53_v6.csv', index=False)
    print(df_comparison)
```

**Expected Improvements**:
| Métrica | v5.3 | v6.0 | Mejora |
|---------|------|------|--------|
| Vehículos/día | ~150 | ~280-309 | +85-107% |
| CO2 evitado | ~7,200 | ~7,500+ | +4-11% |
| Grid import | 25% | 12% | -13% |
| Episode return | ~100-200 | ~400-600 | +2-4x |
| Convergencia | >100 ep | 10-15 ep | 7-10x ⬇ |

**Total Work**: 1 día
**Deliverable**: Comparison report ✓

---

## CHECKLIST DETALLADO

### Pre-Implementation

- [ ] Read all documentation:
  - [ ] ARQUITECTURA_SAC_v6_COMUNICACION_SISTEMAS.md
  - [ ] RESUMEN_EJECUTIVO_v6_COMUNICACION.md
  - [ ] DIAGRAMAS_COMUNICACION_v6.md
- [ ] Backup actual code (v5.3)
- [ ] Create feature branch: `feature/sac-v6-communication`

### Fase 1: Stack Base

#### Tarea 1.1
- [ ] Extend RealOE2Environment OBS_DIM: 156 → 246
- [ ] Implement [156-193]: Socket SOC tracking
  - [ ] Test: obs[156:194].shape == (38,)
  - [ ] Test: Values range [0, 1]
  - [ ] Test: Update when SOC changes
- [ ] Implement [194-231]: Time remaining per socket
  - [ ] Test: obs[194:232].shape == (38,)
  - [ ] Test: Quando SOC=10%, time ≈ 0.5 (4h/8h input)
  - [ ] Test: Quando SOC=95%, time ≈ 0.06 (0.5h/8h)
- [ ] Implement [232-233]: BESS dispatch signals
  - [ ] Test: Track BESS SOC%
  - [ ] Test: obs[232]=1.0 quando BESS=100%
- [ ] Implement [234-235]: Solar bypass signals
  - [ ] Test: Track solar_kw
- [ ] Implement [236-237]: Grid import signals
  - [ ] Test: 0 cuando no necesita grid
- [ ] Implement [238-245]: Agregados críticos
  - [ ] Test: All values range [0, 1]
- [ ] **Code review**: OBS_DIM=246, all ranges validated

#### Tarea 1.2
- [ ] Extend VehicleSOCTracker class
  - [ ] Implement: update_vehicle_soc()
  - [ ] Implement: get_socket_metrics()
  - [ ] Implement: get_priority_weight()
- [ ] Add VehicleSOCState dataclass
  - [ ] Fields: socket_id, vehicle_type, current_soc, ...
- [ ] Update step() function
  - [ ] Call tracker.update_vehicle_soc() for each socket
  - [ ] Track vehicles completed (SOC >= 99.9%)
- [ ] Tests:
  - [ ] SOC increments correctly based on power
  - [ ] Vehicles marked complete at 100%
  - [ ] total_motos_charged_100 increments
  - [ ] Proper disconnection at completion

#### Tarea 1.3
- [ ] Update reward function (REWARD_WEIGHTS_V6)
  - [ ] w_co2 = 0.45 (was 0.50)
  - [ ] w_solar = 0.15 (same)
  - [ ] w_vehicles_charged = 0.25 ⭐ NEW
  - [ ] w_grid_stable = 0.05 (same)
  - [ ] w_bess_efficiency = 0.05 (same)
  - [ ] w_prioritization = 0.05 (same)
- [ ] Implement r_vehicles calculation:
  - [ ] Count vehicles with SOC >= 99.9% this hour
  - [ ] r_vehicles = count / NUM_CHARGERS
  - [ ] Accum self.episode_vehicles_charged
- [ ] Tests:
  - [ ] sum(weights) = 1.00 ✓
  - [ ] Reward > 0 cuando vehicles_charged > 0
  - [ ] CO2 still penalized if grid import

### Fase 2: Data Integration

#### Tarea 2.1
- [ ] Create data loader function:
  - [ ] Load solar CSV (8,760 rows)
  - [ ] Load chargers CSV (8,760 × 38)
  - [ ] Load BESS CSV (8,760 rows)
  - [ ] Load mall CSV (8,760 rows)
- [ ] Validate shapes:
  - [ ] solar_kw.shape == (8760,)
  - [ ] chargers_kw.shape == (8760, 38)
  - [ ] bess_soc.shape == (8760,)
  - [ ] mall_kw.shape == (8760,)
- [ ] Validate ranges:
  - [ ] sol: [0, 4100] kW ✓
  - [ ] chargers: [0, 281.2] kW ✓
  - [ ] BESS: [20, 100] % ✓
  - [ ] mall: [0, 150] kW ✓
- [ ] Create train_sac_v6.py with data loading

#### Tarea 2.2
- [ ] Load BESS cascada columns:
  - [ ] pv_generation, pv_to_bess, pv_to_ev, pv_to_mall, pv_curtailed
- [ ] Validate cascada:
  - [ ] sum(pv_to_*) == pv_generation with <1% error
- [ ] Generate cascada report:
  - [ ] pv_to_bess %
  - [ ] pv_to_ev %
  - [ ] pv_to_mall %
  - [ ] pv_curtailed %

### Fase 3: Training

#### Tarea 3.1
- [ ] Create train_sac_v6.py
- [ ] Configure SAC:
  - [ ] learning_rate=1e-4
  - [ ] buffer_size=1M
  - [ ] batch_size=256
  - [ ] gradient_steps=2
- [ ] Setup checkpoints:
  - [ ] Directory: checkpoints/SAC/
  - [ ] Frequency: every 1000 steps
- [ ] Training parameters:
  - [ ] total_timesteps=131,400 (15 episodes)
  - [ ] log_interval=100

#### Tarea 3.2
- [ ] Implement monitoring script
- [ ] Track KPIs:
  - [ ] Episode return trend
  - [ ] Vehicles charged trend
  - [ ] CO2 avoided
  - [ ] Grid import
- [ ] Generate plots:
  - [ ] Reward curve
  - [ ] Vehicle count curve
  - [ ] Energy flows

#### Tarea 3.3
- [ ] Run training:
  ```bash
  python scripts/train/train_sac_v6.py --device cuda  # 6-8 hrs
  ```
- [ ] Monitor progress:
  ```bash
  python scripts/train/monitor_training.py  # In otra terminal
  ```
- [ ] Expected final model: `checkpoints/SAC/sac_v6_final.zip`

### Fase 4: Validation

#### Tarea 4.1
- [ ] Validate results:
  - [ ] vehicles_charged >= 250 ✓
  - [ ] co2_avoided_kg >= 7500 ✓
  - [ ] grid_import < 15% ✓
  - [ ] episode_return >= 400 ✓
- [ ] Create validation report
- [ ] Save metrics to CSV

#### Tarea 4.2
- [ ] Compare v5.3 vs v6.0:
  - [ ] Vehicles charged: 150 → 280-309 (+85%)
  - [ ] CO2 avoided: 7200 → 7500+ (+4%)
  - [ ] Grid import: 25% → 12% (-13%)
  - [ ] Convergence: >100 ep → 10-15 ep (7-10x faster)
- [ ] Generate comparison table
- [ ] Document findings

### Deliverables

- [ ] Code:
  - [ ] `scripts/train/train_sac_v6.py` (main training script)
  - [ ] Extended `RealOE2Environment` (OBS_DIM=246)
  - [ ] Updated reward logic (w_vehicles=0.25)
  - [ ] VehicleSOCTracker v2
- [ ] Data:
  - [ ] `data/oe2/` (loaded and validated)
  - [ ] Cascada validation report
- [ ] Trained model:
  - [ ] `checkpoints/SAC/sac_v6_final.zip` (trained SAC)
  - [ ] Training logs + metrics CSV
- [ ] Documentation:
  - [ ] `reports/comparison_v53_v6.md`
  - [ ] Validation report
  - [ ] Implementation summary

---

## COMANDOS RÁPIDOS

```bash
# Setup environment
cd d:\diseñopvbesscar
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-training.txt

# Validar datos
python -c "from scripts.train.train_sac_v6 import load_real_oe2_data; load_real_oe2_data()"

# Entrenar (GPU)
python scripts/train/train_sac_v6.py --device cuda --total_timesteps 131400

# Monitor
python scripts/train/monitor_training.py

# Validar resultados
python scripts/validation/validate_sac_v6.py

# Comparar v5.3 vs v6.0
python scripts/validation/compare_versions.py
```

---

## NOTAS IMPORTANTES

1. **GPU Requerido**: La entrenamiento de SAC optimizado necesita GPU. RTX 4060 8GB es suficiente.
2. **Backup**: Guardar código v5.3 antes de empezar.
3. **Dependencias**: Asegurar stable-baselines3 >= 2.0, gymnasium >= 0.27
4. **Data**: Todos los archivos CSV en `data/oe2/` deben estar presentes (ya existen)
5. **Paciencia**: GPU toma 6-8 horas, CPU toma 40+ horas. Entrenar de noche.

---

## SOPORTE

Si necesitas ayuda:
1. Revisar documentación en `docs/`
2. Ejecutar validation scripts para diagnosticar
3. Verificar logs en `outputs/`

**Estimated Timeline**: 14-16 days (2-3 weeks)
**Success Criteria**: +130 vehicles/day, -13% grid import, 2x convergence speed
