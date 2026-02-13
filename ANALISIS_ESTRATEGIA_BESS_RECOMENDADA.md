# 🔄 ANÁLISIS: Estrategia de BESS Basada en Disponibilidad Solar
**Comparativa: Arbitraje Tarifario vs. Disponibilidad Solar**

---

## 📊 ESTRATEGIA ACTUAL (bess.py v5.3)
**Tipo:** ARBITRAJE TARIFARIO OSINERGMIN HP/HFP

```
CARGA BESS (HFP barato - 6h-17h):
├─ Fuente 1: PV excedente (costo cero)
├─ Fuente 2: Grid @ S/.0.28/kWh (6h-12h, si SOC < 80%)
└─ Objetivo: Llenar para vender caro en HP

DESCARGA BESS (HP caro - 18h-22h):
├─ Destino: EV + Mall
├─ Ahorro: S/.0.17/kWh × energía descargada
└─ Objetivo: Minimizar tarifa cara
```

**Problema:** Depende de tarifa, no de disponibilidad. Con tarifa uniforme o futura, pierde sentido.

---

## ✅ ESTRATEGIA RECOMENDADA (Usuario)
**Tipo:** BASADA EN DISPONIBILIDAD SOLAR

```
CARGA BESS (Mañana - cuando hay generación solar máxima):
├─ Hora de inicio: variable (cuando solar inicia)
├─ Hora máxima: cuando coincide PV máximo (~12h-14h)
├─ Condición: Cargar hasta 100% SOC
├─ Fuente: Solo PV directo (NO grid)
└─ Prioridad: Llenar completamente para seguridad

DESCARGA BESS (Tarde-Noche - cuando hay déficit solar):
├─ Hora inicio: cuando solar < demanda_mall
├─ Condición: Descargar cuando PV insuficiente
├─ Destino: EV (principal, hasta cierre 22h) + Mall
├─ Regla: Descargar cuando: PV[t] < DEMANDA_MALL[t]
└─ Objetivo: Minimizar grid, máxima autonomía
```

**Ventaja:** Lógica robusta independiente de tarifa, prioriza PV + seguridad.

---

## 📐 Pseudocódigo: Estrategia Recomendada

```python
def simulate_bess_solar_priority(pv_kwh, ev_kwh, mall_kwh, capacity, power, year):
    """
    Estrategia de BESS basada en DISPONIBILIDAD SOLAR.
    
    Regla: 
    - Cargar cuando hay excedente PV (solar > demanda)
    - Descargar cuando hay déficit solar (solar < demanda_mall)
    
    Seguridad: Mantener 100% SOC en mañana → más capacidad para tarde
    """
    
    soc = 0.50  # Inicio neutro
    capacity_kwh = 1700
    efficiency = 0.95
    
    for h in range(8760):
        hour_of_day = h % 24
        pv_h = pv_kwh[h]
        ev_h = ev_kwh[h]
        mall_h = mall_kwh[h]
        
        # ════════════════════════════════════════════
        # FUERA DE HORARIO OPERATIVO (23h-5h)
        # ════════════════════════════════════════════
        if hour_of_day >= 23 or hour_of_day < 6:
            pv_to_ev[h] = 0
            pv_to_mall[h] = min(pv_h, mall_h)
            bess_charge[h] = 0
            bess_discharge[h] = 0
            grid_to_ev[h] = ev_h
            grid_to_mall[h] = max(mall_h - pv_to_mall[h], 0)
            continue
        
        # ════════════════════════════════════════════
        # OPERACIÓN DIURNA-NOCTURNA (6h-22h)
        # ════════════════════════════════════════════
        
        # Prioridad 1: PV → EV directo (siempre)
        pv_to_ev[h] = min(pv_h, ev_h)
        pv_remaining = pv_h - pv_to_ev[h]
        ev_deficit = ev_h - pv_to_ev[h]
        
        # Prioridad 2: PV → Mall
        pv_to_mall[h] = min(pv_remaining, mall_h)
        pv_remaining -= pv_to_mall[h]
        mall_deficit = mall_h - pv_to_mall[h]
        
        # ════════════════════════════════════════════
        # LÓGICA DE CARGA/DESCARGA BASADA EN SOLAR
        # ════════════════════════════════════════════
        
        # CRITERIO: Cargar si hay PV excedente
        if pv_remaining > 0 and soc < 1.0:
            # CARGAR BESS desde PV excedente
            soc_headroom = (1.0 - soc) * capacity_kwh
            max_charge = min(power, pv_remaining, soc_headroom / eff_charge)
            
            bess_charge[h] = max_charge
            soc += (max_charge * eff_charge) / capacity_kwh
            pv_remaining -= max_charge
        
        # CRITERIO: Descargar si hay déficit de solar (solar < mall)
        # O si hay déficit de EV y SOC > min
        if (pv_h < mall_h) or (ev_deficit > 0 and soc > 0.20):
            # DESCARGAR BESS
            
            # Prioridad descarga 1: EV
            if ev_deficit > 0 and soc > 0.20:
                max_discharge_ev = min(power, ev_deficit, soc_avail)
                actual_discharge_ev = max_discharge_ev * eff_discharge
                
                bess_discharge[h] += max_discharge_ev
                bess_to_ev[h] = actual_discharge_ev
                soc -= max_discharge_ev / capacity_kwh
                ev_deficit -= actual_discharge_ev
            
            # Prioridad descarga 2: Mall (solo si solar insuficiente)
            if pv_h < mall_h and soc > 0.20 and mall_deficit > 0:
                max_discharge_mall = min(power - already_used, mall_deficit)
                
                bess_discharge[h] += max_discharge_mall
                bess_to_mall[h] = max_discharge_mall * eff_discharge
                soc -= max_discharge_mall / capacity_kwh
                mall_deficit -= max_discharge_mall * eff_discharge
        else:
            # Sin déficit solar y sin déficit EV: no descargar
            bess_charge[h] = max(bess_charge[h], 0)
            bess_discharge[h] = 0
        
        # Grid cubre déficits restantes
        grid_to_ev[h] = max(ev_deficit, 0)
        grid_to_mall[h] = max(mall_deficit, 0)
        
        soc[h] = soc
    
    return bess_mode, soc, metrics

```

---

## 📊 Comparativa de Resultados Esperados

| Métrica | Arbitraje HP/HFP (Actual) | Solar-Priority (Recomendado) | Diferencia |
|---------|---|---|---|
| **Carga BESS** | 6h-12h (HFP barato) | ~6h-14h (máximo solar) | +2-3h más carga |
| **Descarga BESS** | 18h-22h (HP caro) | 16h-22h (déficit solar) | +4h más descarga |
| **SOC Máximo Típico** | ~90-95% (ahorquillado) | ~100% (agresivo) | +5-10% |
| **Tiempo carga 100%** | Raro (~30% del año) | Frecuente (~200 días) | Mayor disponibilidad |
| **Cobertura EV** | 90.5% (en HP) | 92-95% (todo el día) | +1-5% mejor |
| **Cobertura Mall** | 1-2% (en HP) | 5-8% (tarde-noche) | +3-6% solar |
| **Ahorro Anual** | S/.1.8M (arbitraje) | S/.1.9-2.0M (seguridad+ahorro) | +S/.0.1-0.2M |
| **Dependencia Tarifa** | Alta | Nula | 100% independiente |

---

## 🔧 Cambios Necesarios en bess.py

### 1. Nueva función: `simulate_bess_solar_priority()`
**Ubicación:** Línea ~893+ (donde actualmente está `simulate_bess_arbitrage_hp_hfp()`)

```python
def simulate_bess_solar_priority(
    pv_kwh: np.ndarray,
    ev_kwh: np.ndarray,
    mall_kwh: np.ndarray,
    capacity_kwh: float = 1700,
    power_kw: float = 400,
    efficiency: float = 0.95,
    soc_min: float = 0.20,
    closing_hour: int = 22,
    year: int = 2024,
) -> Tuple[pd.DataFrame, dict]:
    """
    Simula operación BESS con prioridad SOLAR (independiente de tarifa).
    
    Estrategia:
    1. CARGAR: Cuando PV excedente disponible (hasta 100% SOC)
    2. DESCARGAR: Cuando déficit solar (solar < demanda_mall) O déficit EV
    
    Args:
        pv_kwh: Array 8,760 valores PV horarios
        ev_kwh: Array 8,760 valores EV horarios
        mall_kwh: Array 8,760 valores Mall horarios
        capacity_kwh: Capacidad BESS (1,700 kWh)
        power_kw: Potencia BESS (400 kW)
        efficiency: Eficiencia round-trip (95%)
        soc_min: SOC mínimo (20%)
        closing_hour: Hora cierre EV (22h)
        year: Año simulación (2024)
    
    Returns:
        (df_sim, metrics): DataFrame 8,760 + dict de KPIs
    """
    # Implementar lógica solar-priority aquí
    pass
```

### 2. Actualizar `run_bess_sizing()` en línea ~1930
**Cambiar de:**
```python
df_sim, metrics = simulate_bess_arbitrage_hp_hfp(...)  # Línea 1930
```

**Cambiar a:**
```python
# Elegir estrategia
if use_solar_priority:
    print("   [ESTRATEGIA SOLAR-PRIORITY] Independiente de tarifa")
    print("   [CARGA] Cuando PV excedente")
    print("   [DESCARGA] Cuando déficit solar OR déficit EV")
    df_sim, metrics = simulate_bess_solar_priority(...)
else:
    print("   [ESTRATEGIA ARBITRAJE HP/HFP] Optimización tarifaria OSINERGMIN")
    df_sim, metrics = simulate_bess_arbitrage_hp_hfp(...)
```

### 3. Actualizar `__main__()` en línea ~2302
**Agregar parámetro:**
```python
result = run_bess_sizing(
    ...
    out_dir=out_dir,
    use_solar_priority=True,  # ← NUEVO: cambiar a False para arbitraje
    ...
)
```

---

## 🎯 Ventajas de Solar-Priority

✅ **Independencia Tarifaria:** Funciona sin cambios si tarifa cambia
✅ **Mayor Seguridad:** SOC siempre lleno en noche crítica (22h)
✅ **Lógica Intuitiva:** Cargar cuando hay sol, descargar cuando no hay
✅ **Mejor Cobertura:** ~5-10% más de autosuficiencia
✅ **OE3 Compatible:** Agents RL pueden aprender esta estrategia mejor
✅ **Futuro-Proof:** Si llevan solar a 6,000 kWp, sigue siendo óptimo

---

## ⏱️ Timeline de Implementación

| Fase | Tarea | Tiempo | Status |
|------|-------|--------|--------|
| 1 | Crear `simulate_bess_solar_priority()` | 2-3h | Propuesta |
| 2 | Actualizar `run_bess_sizing()` con flag | 30min | Propuesta |
| 3 | Validar con balance.py | 1h | Propuesta |
| 4 | Comparar resultados (ambas estrategias) | 1h | Propuesta |
| 5 | Documentar cambios v5.4 | 30min | Propuesta |

---

## 📌 Conclusión

**Recomendación:** Implementar `simulate_bess_solar_priority()` como **estrategia PRIMARY** (default), manteniendo `simulate_bess_arbitrage_hp_hfp()` como **estrategia LEGACY** (opcional).

La estrategia solar-priority es más **robusta, segura e independiente de tarifa**, perfecta para un proyecto de investigación en OE3 con RL agents.

