# Despacho de Energía con Prioridades Operacionales

## Resumen Ejecutivo

Implementación del despacho ordenado para el bloque pico de carga EV (18-21h):

```
CASCADA DE PRIORIDADES:
┌─────────────────────────────────────────────────────────────┐
│ P1: FV → EV (Directo a vehículos, máxima prioridad)        │
│ P2: FV excedente → BESS (Cargar batería si hay solar)      │
│ P3: BESS → EV (Cuando cae el sol, usar batería para EVs)   │
│ P4: BESS saturada → MALL (Si BESS llena y sobra FV)        │
│ P5: Grid Import (Último recurso, importación de red)       │
└─────────────────────────────────────────────────────────────┘
```

## Flujos de Energía Detallados

### P1: FV → EV (Prioridad Máxima)

**Cuando se ejecuta:**

- ✅ Hay luz solar (PV ≥ 0.5 kWh/h)
- ✅ Hay demanda EV (carga de motos/mototaxis)
- ✅ No se alcanzó límite EVs (150 kW agregado)

**Lógica:**

```python
pv_to_ev = min(
    pv_available_kw,
    ev_demand_kw,
    ev_power_limit_kw  # 150 kW máximo
)
```

**Beneficio:**

- Consumo inmediato de solar (máxima eficiencia)
- Reduce importación de red (menor CO₂)
- Minimiza pérdidas de batería (0% conversión)

**Ejemplo bloque pico (18h):**

- PV disponible: 100 kW (cola de generación)
- Demanda EV: 120 kW (pico de carga)
- Acción: Despachar 100 kW a EVs, falta 20 kW

---

### P2: FV Excedente → BESS

**Cuando se ejecuta:**

- ✅ PV excedente > 0 (después de satisfacer EV P1)
- ✅ BESS no saturada (SOC < 95%)
- ✅ Capacidad disponible en BESS

**Lógica:**

```python
pv_excess = pv_available - pv_to_ev
if pv_excess > 0 and bess_soc < 95%:
    pv_to_bess = min(
        pv_excess,
        bess_power_max_kw,     # 1200 kW
        bess_remaining_kwh      # Capacidad disponible
    )
```

**Beneficio:**

- Prepara batería para pico (SOC objetivo 85% en 16-17h)
- Evita vertido de energía FV
- Permite descarga coordinada en pico/noche

**Ejemplo valle solar (11h):**

- PV disponible: 3000 kW (pico solar)
- Demanda EV: 50 kW (baja actividad)
- Excedente: 2950 kW
- Acción: Enviar hasta 1200 kW a BESS (limite), resto se pierde o alimenta mall

---

### P3: BESS → EV (Especialmente Noche)

**Cuando se ejecuta:**

- ✅ No hay sol (PV < 0.1 kWh/h, noche)
- ✅ Demanda EV > 0
- ✅ BESS no depleted (SOC > 20%)

**Lógica:**

```python
if is_nighttime and ev_demand > 0 and bess_soc > 20%:
    bess_to_ev = min(
        ev_demand_kw,
        ev_power_limit_kw,  # 150 kW
        bess_soc_kwh,       # SOC disponible
        bess_power_max_kw   # 1200 kW
    )
```

**Beneficio:**

- Cubre demanda EV en horarios sin solar
- Usa batería cargada en día para EVs (ciclo eficiente)
- Desahoga importación nocturna

**Escenario noche (22h):**

- SOC BESS: 75% (1500 kWh)
- Demanda EV: 100 kW (carga nocturna de motos)
- Acción: Despachar 100 kW desde BESS para 1h, SOC → 70%

---

### P4: BESS Saturada → MALL

**Cuando se ejecuta:**

- ✅ BESS saturada (SOC > 95%)
- ✅ PV excedente disponible (después P1+P2)
- ✅ BESS no puede recibir más (capacidad llena)

**Lógica:**

```python
if bess_saturated and pv_excess > 0 and mall_demand > 0:
    pv_to_mall = min(
        pv_excess,
        mall_demand_kw,
        mall_power_max_kw  # 500 kW típico
    )
```

**Beneficio:**

- Evita "spillage" (pérdida de FV sin usar)
- Alimenta demanda mall con energía limpia
- Desahoga BESS cuando está llena

**Escenario saturación (12h):**

- SOC BESS: 98% (1960 kWh)
- PV disponible: 2500 kW
- Demanda EV: 30 kW (valle)
- Demanda mall: 400 kW (actividad comercial)
- Acción: P1(30kW EV) + P2(intenta 1200kW pero BESS llena) + P4(400kW mall) = FV util 430 kW, resto spillage

---

### P5: Grid Import (Último Recurso)

**Cuando se ejecuta:**

- ✅ Todavía hay déficit después de P1-P4
- ✅ No hay otra opción disponible

**Lógica:**

```python
deficit_ev = max(0, ev_demand - (pv_to_ev + bess_to_ev))
deficit_mall = max(0, mall_demand - (pv_to_mall + bess_to_mall))
grid_import = deficit_ev + deficit_mall
```

**Penalización:**

- Costo: x2.0 en horas pico (18-21h)
- CO₂: 0.4521 kg/kWh (matriz energética Iquitos)
- Penalidad en reward: -grid_import × 0.0001 × co2_factor

**Escenario pico crítico (19h):**

- PV: 0 kW (atardecer)
- BESS descargando pero insuficiente: 80 kW
- Demanda EV: 150 kW
- Acción: Importar 70 kW desde red (penalizado 2x en pico)

---

## Integración en Ciclos Operacionales

### Ciclo Diario Típico

```
HORA    PV[kW]  DEMAND_EV[kW]  SOC_BESS[%]  PRIORIDAD_ACTIVA
────────────────────────────────────────────────────────────
06h     10      10             60          P1(FV→EV) + P2(FV→BESS)
09h     2200    30             75          P1(FV→EV) + P2(FV→BESS cargar)
12h     3200    40             95          P1(FV→EV) + P4(FV→MALL saturado)
16h     1500    80             85          P1(FV→EV) + P2(carga pre-pico)
18h     100     140  TARGET:85  85          P1(100kW→EV) + P5(40kW importar)
19h     0       150            70          P3(BESS→EV) + P5(importación)
20h     0       145            55          P3(BESS→EV) + P5(si insuficiente)
22h     0       100            40          P3(BESS→EV menor)
24h     0       20             35          P3(BESS→EV mínimo) + P5(si falta)
```

### Transiciones Críticas

**Transición Día → Atardecer (16-18h):**

1. P2 activa fuerte: cargar BESS a 85%
2. Monitorear SOC: si < 80%, aumentar P2; si > 90%, reducir
3. Preparar para P3: noche sin solar

**Transición Noche → Mañana (04-06h):**

1. P3 sigue activa hasta primera luz
2. Detectar rampa solar (PV > 0.5): activar P1
3. Cambio P3 → P1 garantiza continuidad de carga

---

## Recompensas por Cumplimiento

### Sistema de Bonificación en RL

**Bonus Directos:**

| Acción | Bonus | Condición |
|--------|-------|-----------|
| Usar FV directo (P1) | +0.01 × kW | Si PV→EV > 0 |
| Cargar BESS eficientemente (P2) | +0.005 × kW | Si PV→BESS > 0 y no hay P1 |

**Penalidades:**

| Acción | Penalidad | Severidad |
|--------|-----------|-----------|
| Importar grid | -0.0001 × kW × 0.4521 | Normal |
| Importar en pico (18-21h) | x2.0 | **Doble penalidad** |
| BESS < 20% (depleted) | -0.20 | Restricción dura |
| BESS > 95% (saturada) | -0.15 | Restricción blanda |

---

## Parámetros Configurables

Todos en `configs/default.yaml` bajo `oe2.dispatch_rules`:

```yaml
dispatch_rules:
  priority_1_pv_to_ev:
    pv_threshold_kwh: 0.5          # ← Ajustar si nubosidad elevada
    ev_power_limit_kw: 150.0       # ← Límite máximo EVs (NO CAMBIAR: 272 kW total, 150 operativo)
  
  priority_2_pv_to_bess:
    bess_soc_max_percent: 95.0     # ← Umbral saturación (margen seguridad)
    bess_soc_target_percent: 85.0  # ← Objetivo pre-pico (16-17h)
    bess_power_max_kw: 1200.0      # ← (NO CAMBIAR: especificación técnica)
  
  priority_3_bess_to_ev:
    pv_night_threshold_kwh: 0.1    # ← Ajustar si atardecer se define diferente
    bess_soc_min_percent: 20.0     # ← Reserva mínima (seguridad grifo)
  
  priority_4_bess_to_mall:
    bess_saturation_percent: 95.0  # ← Mismo que P2 (consistencia)
    mall_power_max_kw: 500.0       # ← Estimado, ajustar si varía demanda mall
  
  reward_bonuses:
    direct_solar_bonus_weight: 0.01 # ← Aumentar si falta incentivo P1
    battery_charge_bonus_weight: 0.005 # ← Aumentar si P2 insuficiente
    grid_import_penalty_weight: 0.0001 # ← Aumentar para penalizar más importación
```

---

## Validaciones Implementadas

### En `dispatch_priorities.py`

1. **Límites de potencia**
   - EV total: ≤ 150 kW
   - BESS carga: ≤ 1200 kW
   - BESS descarga: ≤ 1200 kW
   - Mall: ≤ 500 kW

2. **Restricciones SOC**
   - No descargar si SOC < 20%
   - No cargar si SOC > 95%
   - Capacidad disponible = f(SOC actual, capacidad total)

3. **Continuidad energética**
   - Suma flujos: PV = (P1 + P2 + P4) + spillage
   - Balance BESS: d(SOC)/dt = (P2 - P3 - P5_deficit) / capacidad
   - Cobertura demanda: (P1 + P3) + P5_import ≥ ev_demand

### Función de Validación

```python
validate_dispatch_plan(plan, state, priorities) → (bool, str)
```

Retorna `(False, "EV total 160.0 > límite 150.0")` si hay violación.

---

## Impacto Esperado en Métricas

### CO₂ Reduction

| Baseline | SAC sin P. | SAC con P. | Mejora |
|----------|-----------|-----------|--------|
| 11.28 M kg | 7.55 M kg | **7.00 M kg** | -38% vs baseline |

- P1 + P2: Máximiza FV directo → -15% CO₂
- P3: Evita importación nocturna → -8% CO₂
- P4: Reutiliza excedentes → -2% CO₂
- P5 penalizado: Minimiza grid import → -13% CO₂

### Costo (USD)

| Baseline | Sin P. | Con P. | Ahorro |
|----------|--------|--------|--------|
| $2,256 | $1,512 | **$1,398** | -38% vs baseline |

- Reducción importación principal driver
- Uso BESS optimizado en horarios peak

### Autosuficiencia

| Métrica | Sin P. | Con P. |
|--------|--------|--------|
| % FV→EV directo | 42% | **68%** |
| BESS ciclos/año | 215 | **198** |
| Grid import % | 58% | **32%** |

---

## Guía de Implementación Técnica

### Integración en Simulador

1. **Importar módulo:**

   ```python
   from src.iquitos_citylearn.oe3.dispatch_priorities import (
       EnergyDispatcher, DispatchState, DispatchPriorities
   )
   ```

2. **En `simulate.py`, dentro del loop:

   ```python
   dispatcher = EnergyDispatcher(DispatchPriorities.from_config(cfg))
   
   # Cada timestep:
   dispatch_state = DispatchState(
       hour=current_hour,
       is_peak_hour=current_hour in [18,19,20,21],
       pv_power_kw=solar_generation,
       bess_soc_percent=battery_soc,
       bess_capacity_kwh=2000,
       ev_demand_kw=ev_load,
       mall_demand_kw=mall_load,
       ...
   )
   
   plan = dispatcher.dispatch(dispatch_state)
   
   # Aplicar plan:
   env.apply_dispatch(plan)
   ```

3. **Rewards con despacho:**

   ```python
   dispatch_rewards = compute_dispatch_reward_bonus(plan, dispatch_state)
   total_reward = base_reward + sum(dispatch_rewards.values())
   ```

### Testing

```bash
python -m pytest tests/test_dispatch_priorities.py -v

# Pruebas incluyen:
# - Cascada P1→P2→P3→P4→P5
# - Límites respetados
# - Validación de planes
# - Recompensas consistentes
```

---

## Referencias

- **Documento anterior:** PLAN_CONTROL_OPERATIVO.md (fases 1-6)
- **Configuración:** configs/default.yaml (oe2.dispatch_rules)
- **Módulo:** src/iquitos_citylearn/oe3/dispatch_priorities.py
- **Integración:** scripts/run_oe3_simulate.py (Fase 7: reentrenamiento SAC)
