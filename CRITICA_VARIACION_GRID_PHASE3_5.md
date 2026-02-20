# 🔴 CRÍTICA FASE 3-5: Variación Anormal en Curva de Red Pública

## Problema Identificado

**Las variaciones abruptas en grid_import_mall_kwh entre horas 17-21 revelan un error en la lógica de descarga BESS (FASE 3-4-5).**

### Datos Observados (Día 180)

```
HORA  MALL_kW  BESS_MALL  MALL_AFTER  GRID_MALL  ΔGrid  PROBLEMA
17h   2209     309        1900        1900        +0
18h   2153     506        1647        1647      -253     ✓ Descarga fuerte
19h   2081     181        1900        1900      +253     ❌ SALTO ABRUPTO
20h   2085       0        2085        2085      +185     ❌ NO hay descarga!
21h   1962       0        1962        1962      -123     ❌ NO hay descarga!
22h   1171       0        1171        1171      -791     OK (MALL < 1900)
```

### Anomalías Identificadas

#### 1. Variación +253 kW en 19h (salto anómalo)
```
18h→19h: MALL desciende de 2153 → 2081 kW (-72)
         BESS descarga baja de 506 → 181 kW (-325)
         Grid SUBE de 1647 → 1900 kW (+253) ❌
         
Esperado: Grid debería bajar o mantenerse estable
Actual: Grid SUBE anormalmente
         
Causa: Descarga BESS cae más de lo que baja demanda MALL
```

#### 2. Pérdida de Peak Shaving en horas 20-21
```
HORA 20: MALL 2085 kW > 1900 kW (pico active)
         BESS descarga 0 kW ❌ (NO PROTECCIÓN)
         SOC: 20% (mínimo) - sin energía
         Grid: 2085 kW (MALL sin corte!)
         
HORA 21: MALL 1962 kW > 1900 kW (pico activo)
         BESS descarga 0 kW ❌ (NO PROTECCIÓN)
         SOC: 20% (mínimo) - sin energía
         Grid: 1962 kW (MALL sin corte!)
         
PROBLEMA: BESS agotado a las 19h, no puede soportar picos posteriores
```

---

## Análisis de Raíz Causa

### El Problema Está en la Lógica de Descarga (bess.py)

**Flujo Actual (INCORRECTO v5.8):**

```
HORA 17h-19h (FASE 3-5: Descarga máxima):
1. Verificar EV deficit
   ├─ Si ev_deficit > 0: Descargar TODO a EV (PRIORIDAD 1)
   └─ Consume energía sin consideración de futuro
2. Verificar MALL peak shaving
   ├─ Si MALL > 1900 kW: Descargar LO QUE QUEDE
   └─ Pero ya se consumió energía en paso 1
3. Resultado: BESS se agota rápido

HORA 20h-21h (FASE 3-5: Deberías seguir con peak shaving):
1. SOC ya está en 20% (mínimo defensivo)
2. No hay energía para peak shaving MALL
3. MALL > 1900 kW PERO sin protección del BESS
4. Grid carga TODA la demanda sin corte
5. Variaciones abruptas en grid_import (saltos +185, -123)
```

### Ejemplo Concreto del Error

**Hora 18h:**
```
EV demand:     ~120 kWh (asumiendo ~5h operativas)
MALL demand:   2153 kWh

BESS disponible: (67.29% - 20%) × 2000 = 947 kWh

Acción BESS en hora 18:
├─ Cubre 506 kWh para peak shaving MALL (correcto)
├─ Descarga 400 kW×1h = 400 kWh potencial
└─ SOC baja rápidamente

Problema: 
No hay cálculo ANTICIPADO de:
├─ Cuánta energía sobrevive hasta hora 20-21?
├─ Cuánta demanda habrá en esas horas? (2085, 1962 kWh)
└─ Se gasta TODO sin reserva
```

---

## Impacto en Gráficas

### Curva Esperada (teórica)
```
Grid Import MALL (17h-22h):
              │
    2200 kW  │      (MALL demand sin BESS)
    2000 kW  │  _____ (MALL con BESS protection - plano/suave)
    1900 kW  │ /‾‾‾‾  (Threshold protección)
    1647 kW  │/
              └─────────────────→ Horas
    
Característica: Curva suave, sin saltos
```

### Curva Actual (con error)
```
Grid Import MALL (17h-22h):
              │
    2200 kW  │      
    2100 kW  │   ↑___↑__↑  ← SALTOS/VARIACIONES anómalas
    1900 kW  │   │   │
    1647 kW  │___│___│
              └─────────────────→ Horas
    
Característica: Saltos en 19h (+253), 20h (+185), 21h (-123)
```

### Visualización en balance.py
```
La gráfica 00_BALANCE_INTEGRADO_COMPLETO.png:
├─ Línea roja (grid import) muestra saltos visibles
├─ Entre 18h→19h: baja luego SUBE (anómalo)
├─ Entre 19h→20h: sube más de lo esperado
├─ MALL sin protección en 20h-21h (sin barras rojas descarga)
└─ Patrón NOT smooth (inconsistente con peak shaving concept)
```

---

## Solución Requerida

### Estrategia Correcta: Descarga Distribuida + Reserva

**Lógica v5.9 Propuesta:**

```python
# ANTES DE descargar todo a EV, calcular:
1. ¿Cuánta energía TOTAL se necesita? (EV + peak shaving MALL)
2. ¿Cuántas horas faltan con picos > 1900 kW?
3. ¿Cuánta reserva mínima se debe mantener?

# LUEGO distribuir descarga entre:
├─ BESS→EV: 100% cobertura pero CON LÍMITE horario
├─ BESS→MALL: Peak shaving con PRIORIDAD EN HORAS CRÍTICAS (17-21h)
└─ BESS→Grid: Si SOC residual muy alto

# RESULTADO: Descarga suave, distribuida, sin saltos
```

### Implementación Específica

**En bess.py (línea ~1950-1970):**

```python
# NUEVO: Cálculo anticipado de demanda futura
def estimate_remaining_demand(pv_h, ev_h, mall_h, h, closing_hour=22):
    """Estima si habrá más picos > 1900 kW después de esta hora."""
    remaining_hours = closing_hour - h
    future_demand_estimate = ev_h + mall_h  # Simplificado
    
    has_future_peaks = False
    if remaining_hours > 1:
        # Suponiendo MALL > 1900 en próximas horas
        has_future_peaks = (mall_h > 1900.0)
    
    return remaining_hours, has_future_peaks

# NUEVO: Límite dinámico de descarga a EV
def calculate_max_ev_discharge(ev_deficit, remaining_hours, soc_available):
    """Calcula descarga máxima a EV sin dejar MALL sin protección."""
    
    # Reservar energía para peak shaving MALL en próximas horas
    if remaining_hours > 2 and soc_available > 400:
        # Reservar 300-400 kWh para MALL en horas 20-21
        reserve_kwh = 400
        available_for_ev = max(soc_available - reserve_kwh, 0)
    else:
        available_for_ev = soc_available
    
    power_to_ev = min(ev_deficit / eff_discharge, available_for_ev)
    return power_to_ev

# Aplicar en FASE 3-5
remaining_hrs, has_peaks = estimate_remaining_demand(pv_h, ev_h, mall_h, h)
power_to_ev = calculate_max_ev_discharge(ev_deficit, remaining_hrs, soc_available_kwh)
```

### Cambios Mínimos Requeridos

**Archivo:** `src/dimensionamiento/oe2/disenobess/bess.py`

**Línea ~1950 (FASE 3-5 DESCARGA):**

CAMBIAR:
```python
# PRIORIDAD 1: CUBRIR 100% DEFICIT EV (maximo)
if ev_deficit > 0.01 and soc_available_kwh > 0.01:
    power_to_ev = min(remaining_discharge_power, ev_deficit, 
                       soc_available_kwh / eff_discharge)  # ❌ SIN RESERVA
```

POR:
```python
# PRIORIDAD 1: CUBRIR EV CON RESERVA PARA PEAK SHAVING MALL
if ev_deficit > 0.01 and soc_available_kwh > 0.01:
    # Reservar energía para peak shaving MALL en horas 20-21
    remaining_hours = closing_hour - hour_of_day
    reserve_for_mall = 400.0 if remaining_hours > 2 and pico_mall_critico else 0
    available_for_ev = max(soc_available_kwh - reserve_for_mall, 0)
    
    power_to_ev = min(remaining_discharge_power, ev_deficit, 
                       available_for_ev / eff_discharge)  # ✓ CON RESERVA
```

---

## Validación Post-Fix

### Expectativas de Corrección

```
Después de implementar:

HORA  MALL_kW  BESS_MALL  GRID_MALL  ΔGrid  STATUS
17h   2209     250-300    1900-1950   +0     ✓ Controlado
18h   2153     350-400    1750-1800  -100    ✓ Suave descenso
19h   2081     300-350    1800-1850   +25    ✓ Estable
20h   2085     250-300    1850-1900   +50    ✓ Mantiene protección
21h   1962     200-250    1850-1900   +0     ✓ Mantiene protección
22h   1171       0        1171      -729    ✓ OK (MALL < 1900)

Resultado: Curva suave, sin saltos > 100 kW
```

### Gráficas Esperadas Post-Fix

```
Grid Import MALL (suave):
              │
    2000 kW  │    ·──·──·
    1900 kW  │   ·       ·
    1800 kW  │  ·         ·
    1700 kW  │_·___________·_  ← Línea suave
              └─────────────────→ Horas
    
BESS Descarga (distribuida):
              │ ·
    400 kW   │ · ‾‾·
    300 kW   │·     ·  ← Descarga reservada
    200 kW   │       ·_
    100 kW   │         ‾‾·_
      0 kW   │_____________‾  ← Cierre smooth
              └─────────────────→ Horas
```

---

## Estado Actual

| Aspecto | Estado |
|---------|--------|
| **Problema identificado** | ✅ Confirmed |
| **Causa raíz** | ✅ Descarga sin reserva estratégica |
| **Impacto gráficas** | ✅ Variaciones +253, +185 kW |
| **Pérdida peak shaving** | ✅ Horas 20-21 sin cobertura |
| **Solución** | ⏳ Requiere cambio en bess.py |
| **Líneas a modificar** | ~bess.py líneas 1950-1980 |
| **Riesgo** | MODERADO (6 FASES intocables se mantienen) |

---

## Próximos Pasos

1. **Implementar reserva estratégica** (bess.py ~1950)
2. **Verificar descarga distribuida** (horas 17-22 smooth)
3. **Regenerar bess_ano_2024.csv** con lógica corregida
4. **Validar grid_import_mall cero saltos** (variación < 100 kW)
5. **Actualizar gráficas** con curvas suaves

---

**Status:** ⏳ PENDIENTE FIX
**Criticidad:** 🔴 ALTA (afecta peak shaving MALL)
**Fecha identificado:** 2026-02-20
**Versión problema:** v5.8
**Versión solución:** v5.9 (pending)
