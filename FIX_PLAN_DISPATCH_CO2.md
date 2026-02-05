# FIX PLAN: Corrección de Prioridades de Despacho y Cálculos de CO₂

**Fecha:** 2026-02-05  
**Estado:** ANÁLISIS COMPLETADO - PLAN DE CORRECCIÓN  
**Responsable:** Sistema de Control RL - Iquitos EV Mall

---

## 🎯 PROBLEMA CENTRAL IDENTIFICADO

El proyecto tiene **arquitectura correcta documentada** pero **implementación inconsistente** en cálculos y despacho:

### Problema 1: DESPACHO NO RESPETA PRIORIDADES
**Documentado (correcto):**
```
PRIORIDAD:
1. SOLAR → EVs (máxima)
2. SOLAR EXCESO → BESS
3. SOLAR EXCESO → MALL
4. BESS → EVs (tarde/noche)
5. GRID → Deficit total
```

**Implementado (incorrecto):**
- dispatcher.py EXISTE pero no está siendo USADO en la simulación real
- Los rewards.py NO aseguran que EVs tengan máxima prioridad
- ev_satisfaction SOLO tiene 10% de peso, insuficiente

### Problema 2: CÁLCULOS DE CO₂ INCONSISTENTES CON REALIDAD
**Datos Real vs. Sintético:**
```
REAL (OE2):
- Motos: 2,912 total
- Mototaxis: 416 total  
- Capacidad energía/día: ~5,210 kWh (solar 554.8 kWh/h × 24h)
- Demanda realista: 21,216 kWh/día (1.5 cargas × 3,328 vehículos)
- DEFICIT: 75% INSUFICIENTE

SINTÉTICO (entrenamiento actual):
- Motos cargadas/año: 249,141 (683/día)
- Mototaxis cargados/año: 23,727 (65/día)  
- Todos cargados en 1-2 horas (NO distribuido en 9AM-10PM = 13h)
- No refleja realidad operacional
```

### Problema 3: ENERGÍA DISPONIBLE MALA CALCULADA
```
Current: 50 kW constante (INCORRECTO - no refleja solar ni BESS)
Realidad:
- Solar: ~554.8 kWh/h (pico al mediodía)
- BESS: 4,520 kWh @ 2,712 kW (auxiliar, NO fuente primaria)
- Grid: Fallback solo si deficit
```

---

## ✅ PLAN DE CORRECCIÓN EN 3 FASES

### FASE 1: Fijar Prioridades de Despacho (CRÍTICA)
**Ubicación:** `src/rewards/rewards.py`

✅ **Cambios necesarios:**

1. **Aumentar peso de EVs a 30%** (de 10%)
   ```python
   ev_satisfaction: float = 0.30  # WAS 0.10 - TRIPLICADO
   ```

2. **Agregar penalizaciones fuertes por EVs incompletos**
   ```python
   # En compute() método:
   if ev_soc_avg < 0.80:  # Si algún EV < 80%
       r_ev -= 0.3  # Penalidad de -0.3
   
   # Bonus si está cerca de máximo
   if ev_soc_avg > 0.88:
       r_ev += 0.2  # Bonus de +0.2
   ```

3. **Penalidad URGENTE en últimas horas**
   ```python
   hour = time_step % 24
   if hour in [20, 21]:  # 8-10 PM (cierre)
       if ev_soc_avg < 0.90:
           r_ev -= 0.4  # PENALIDAD FUERTE
   ```

4. **Normalizar pesos:**
   ```
   co2: 0.35 (reducido, EVs cargados desde solar ayuda)
   solar: 0.20 (mantener - PV limpio)
   cost: 0.10 (reducido - tarifa baja)
   ev_satisfaction: 0.30 (TRIPLICADO) ← MÁXIMA PRIORIDAD
   grid_stability: 0.05 (mantener)
   = 1.00 ✓
   ```

**Impacto:** Agentes priorizan cargar EVs a máximo SOC (90%+) →  **Reducción CO₂ DIRECTA maximizada**

---

### FASE 2: Realinear Cálculos con Datos OE2 Reales
**Ubicación:** `src/rewards/rewards.py`, línea 1-60

✅ **Cambios necesarios:**

1. **Usar demanda REAL de EVs, NO 50 kW constante**
   ```python
   # ACTUAL (INCORRECTO):
   ev_demand_kwh: float = 0.0  # No definido, default 50 kW fijo
   
   # CORRECTO:
   # Cargar desde OE2 con perfil horario (9AM-10PM)
   ev_profiles_hourly = load_ev_profiles_from_oe2()
   # hour 0-8: 0 kW (noche)
   # hour 9-21: 20-30 kW (distribución con pico mediodía)
   # hour 22-23: 0 kW (cierre)
   ```

2. **Usar solar REAL, NO grid import como referencia**
   ```python
   # El rewards DEBE reconocer:
   # - Solar disponible primero (54.8 kWh/h promedio)
   # - Luego despacho a EVs (máxima prioridad)
   # - Exceso a BESS, luego Mall
   # NO maximizar "minimizar grid" en abstracto
   ```

3. **Corregir factor CO₂ directo**
   ```python
   # ACTUAL (confuso):
   ev_co2_factor: float = 2.146 kg CO₂/kWh (conversion para 50 kW cte)
   
   # CORRECTO:
   # CO₂ DIRECTO = EVs cargados × consumo real × factor grid
   # Ej: 2,000 kWh/día cargados × 0.4521 kg/kWh = 904 kg CO₂ evitado/día
   ```

**Impacto:** Rewards alineados con OE2 real, no valores sintéticos

---

### FASE 3: Implementar Despacho Automático (Reglas Duras)
**Ubicación:** Nueva clase en `src/rewards/dispatcher_hardcoded.py`

✅ **Pseudocódigo:**

```python
class AutomaticDispatcher:
    """Despacho automático que respeta prioridades (NO RL)."""
    
    def dispatch_energy(self, state):
        """
        REGLA 1: SOLAR → EVs (máxima)
        ───────────────────────────────
        """
        solar_avail = state.solar_generation_kw
        ev_demand = state.ev_demand_immediate_kw  # Real, del perfil OE2
        
        solar_to_ev = min(solar_avail, ev_demand)
        solar_remaining = solar_avail - solar_to_ev
        
        # RL agent CAN'T override esto
        
        """
        REGLA 2: SOLAR EXCESO → BESS (mañana)
        ──────────────────────────────────────
        """
        if is_morning_storage and bess_soc < 90%:
            solar_to_bess = min(solar_remaining, bess_charge_rate)
            solar_remaining -= solar_to_bess
        
        """
        REGLA 3: SOLAR EXCESO → MALL
        ────────────────────────────
        """
        solar_to_mall = min(solar_remaining, mall_demand)
        solar_remaining = solar_remaining - solar_to_mall
        
        """
        REGLA 4: BESS → EVs (si deficit)
        ────────────────────────────────
        """
        ev_deficit = max(0, ev_demand - solar_to_ev)
        bess_to_ev = min(bess_available_power, ev_deficit)
        
        """
        REGLA 5: GRID → Deficit residual
        ────────────────────────────────
        """
        grid_needed = ev_deficit - bess_to_ev + mall_deficit
        
        # RL AGENT CONTROLS ONLY:
        # - Timing of when to discharge BESS (but ONLY for EVs)
        # - How to distribute power among 128 chargers
        # - NOT the amount total (that's determined by rules above)
        
        return (solar_to_ev, solar_to_bess, solar_to_mall,
                bess_to_ev, grid_needed)
```

**Impacto:** Reglas garantizadas, RL solo optimiza distribución dentro de restricciones

---

## 📋 CHECKLIST DE CORRECCIÓN

### [  ] FASE 1: Pesos de Recompensa
- [ ] Revisar `rewards.py` línea 115-130 (MultiObjectiveWeights)
- [ ] Cambiar ev_satisfaction: 0.10 → 0.30
- [ ] Cambiar co2: 0.50 → 0.35
- [ ] Re-normalizar suma = 1.0
- [ ] Agregar penalizaciones (línea 320-340)
- [ ] Validar con entrenamiento de prueba (100 pasos)

### [  ] FASE 2: Cálculos CO₂
- [ ] Revisar `rewards.py` línea 1-60 (contexto Iquitos)
- [ ] Cargar perfiles EV desde OE2 (no hardcoded 50 kW)
- [ ] Validar solar en rewards coincide con data
- [ ] Ejemplo: calcular CO₂ real año 1 vs. baseline
- [ ] Documentar en README actualizaciones

### [  ] FASE 3: Despacho Automático
- [ ] Crear `src/rewards/dispatcher_hardcoded.py`
- [ ] Integrar en rewards.py.compute()
- [ ] Verificar que RL agents respetan prioridades
- [ ] Test: forzar demanda EVs > solar, verificar BESS usado
- [ ] Documentar en docs/DISPATCH_RULES.md

### [  ] VALIDACIÓN FINAL
- [ ] Entrenar SAC 100 steps con nuevos pesos
- [ ] Verificar: EV satisfaction > Grid-only baseline
- [ ] Verificar: CO₂ real vs. sintético coherente
- [ ] Actualizar README con nuevos valores
- [ ] Commit con mensaje: "fix: alignment OE2 real data + dispatch priorities"

---

## 📌 REFERENCIA RÁPIDA

| Archivo | Línea | Cambio |
|---------|-------|--------|
| rewards.py | 115 | ev_satisfaction: 0.10 → 0.30 |
| rewards.py | 116 | co2: 0.50 → 0.35 |
| rewards.py | 320 | Agregar penalizaciones EV |
| rewards.py | 1-60 | Usar OE2 real, no sintético |
| (NEW) | - | dispatcher_hardcoded.py |
| README.md | (TBD) | Documentar cambios |

---

## 💡 NOTAS IMPORTANTES

1. **NO es un problema del RL**, es de cómo se **define el problema para RL**
2. **Los agentes son perfectos** - solo optimizan lo que le pedimos
3. **Si pedimos maximizar "minimizar grid"**, lo hacen pero sin considerar EVs
4. **Si aumentamos "evsatisfaction"**, naturalmente priorizan cargar completamente

**Conclusión:** No entrenar más - **RECALIBRAR REWARDS** primero

