# ✅ CORRECCIÓN IMPLEMENTADA: Solar Consumido vs Solar Disponible (2026-01-30)

## Problema Identificado

El cálculo anterior de `solar_energy_sum` en los agentes SAC, PPO y A2C contaba **solar_generation DISPONIBLE** (bruto), no **solar CONSUMIDO** (según reglas de despacho).

**Ejemplo del error**:
```
Paso 400: solar_kWh = 248.0 (solar disponible)
Pero la realidad es:
  - Solar a EVs: 98 kWh (60%)
  - Solar a BESS: 58 kWh (23%)
  - Solar a MALL: 16 kWh (7%)
  - Solar curtailed: 76 kWh (10%)
  
CONSUMO REAL: 98+58+16 = 172 kWh
DISPONIBLE: 248 kWh (diferencia = 76 kWh perdido)
```

## Solución Implementada

### 1. Nueva función: `calculate_solar_dispatch()` en `rewards.py`

```python
def calculate_solar_dispatch(
    solar_available_kw: float,
    ev_demand_kw: float,
    mall_demand_kw: float,
    bess_soc_pct: float,
    bess_max_power_kw: float,
    bess_capacity_kwh: float,
) -> Dict[str, float]:
    """
    Calcula despacho de energía solar según prioridades OE2:
    1. PV → EV (primero)
    2. PV → BESS (lo que sobra)
    3. PV → MALL (demanda edificio)
    4. BESS → Grid (si SOC > 95%)
    5. Grid → Demanda (si hace falta)
    """
```

**Salida**:
```python
{
    "solar_available_kw": 248.0,
    "solar_to_ev_kw": 98.0,
    "solar_to_bess_kw": 58.0,
    "solar_to_mall_kw": 16.0,
    "solar_consumed_kw": 172.0,  # ← Esto es lo que acumulamos ahora
    "solar_curtailed_kw": 76.0,
    "grid_import_needed_kw": 92.0,
    "bess_charging_power_kw": 58.0,
}
```

### 2. Actualización de agentes: SAC, PPO, A2C

**Cambio en `step_callback()` de cada agente**:

```python
# ANTES (incorrecto):
extracted_solar = b.solar_generation[-1]  # Solar disponible
self.solar_energy_sum += extracted_solar

# DESPUÉS (correcto):
dispatch = calculate_solar_dispatch(
    solar_available_kw=solar_available_kw,
    ev_demand_kw=ev_demand_kw,
    mall_demand_kw=mall_demand_kw,
    bess_soc_pct=bess_soc_pct,
    bess_max_power_kw=2712.0,
    bess_capacity_kwh=4520.0,
)
self.solar_energy_sum += dispatch["solar_consumed_kw"]  # ← Solo consumido
self.grid_energy_sum += dispatch["grid_import_needed_kw"]  # ← Solo importado
```

**Archivos modificados**:
- ✅ `src/iquitos_citylearn/oe3/rewards.py` - Nueva función
- ✅ `src/iquitos_citylearn/oe3/agents/sac.py` - Línea ~830
- ✅ `src/iquitos_citylearn/oe3/agents/ppo_sb3.py` - Línea ~590
- ✅ `src/iquitos_citylearn/oe3/agents/a2c_sb3.py` - Línea ~370

## Impacto en Métricas

### Cambios esperados en logs

**ANTES (incorrecto)**:
```
paso 100: solar_kWh=62.0, grid_kWh=137.0, co2_kg=61.9
paso 200: solar_kWh=124.0, grid_kWh=274.0, co2_kg=123.9
paso 400: solar_kWh=248.0, grid_kWh=548.0, co2_kg=247.8
```
→ solar_kWh = solar disponible (bruto, inflado)

**DESPUÉS (correcto)**:
```
paso 100: solar_kWh=45.0, grid_kWh=92.0, co2_kg=41.6
paso 200: solar_kWh=88.0, grid_kWh=186.0, co2_kg=84.2
paso 400: solar_kWh=172.0, grid_kWh=376.0, co2_kg=170.2
```
→ solar_kWh = solar consumido (real)
→ grid_kWh = solar consumido + EV sin cubrir + MALL sin cubrir
→ Métricas más honestas del desempeño

## Por qué es importante

1. **Honestidad de métricas**: Saber cuánto solar realmente se aprovecha vs se desperdicia
2. **Mejor entrenamiento RL**: Agentes optimizan basados en consumo real, no disponibilidad
3. **Alineamiento OE2↔OE3**: Respeta las prioridades de despacho definidas en OE2
4. **Diferenciar agentes**: Ahora veremos cuál agente mejor aprovecha el solar disponible

## Validación

Ejecuta después del entrenamiento:
```bash
python scripts/run_oe3_co2_table --config configs/default.yaml
```

Verifica en logs que:
- ✅ `solar_kWh` < `solar_generation` (hay consumo = bueno)
- ✅ `grid_kWh` correlaciona con demanda no cubierta por solar
- ✅ `co2_kg ≈ grid_kWh × 0.4521` (factor Iquitos)

## Rollback (si es necesario)

Si necesitas revertir:
```bash
git diff src/iquitos_citylearn/oe3/agents/sac.py  # Ver cambios
git checkout src/iquitos_citylearn/oe3/agents/sac.py  # Revertir
```

---

**Fecha**: 2026-01-30
**Versión**: pvbesscar v1.2 (Cálculo Solar Correcto)
**Estado**: ✅ Implementado y listo para entrenamiento

