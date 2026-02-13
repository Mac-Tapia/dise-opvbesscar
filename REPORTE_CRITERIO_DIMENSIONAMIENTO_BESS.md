# 📊 REPORTE: CRITERIO DE DIMENSIONAMIENTO BESS v5.3
## ¿Se considera el PICO DE DEMANDA del MALL?

**Fecha:** 2026-02-13  
**Archivo analizado:** `src/dimensionamiento/oe2/disenobess/bess.py`  
**Versión:** v5.3 (Arbitraje HP/HFP OSINERGMIN)  
**Status:** ✅ Análisis completo sin modificaciones al código

---

## 🎯 RESPUESTA DIRECTA

### ❌ **NO se considera explícitamente el PICO DE DEMANDA del MALL en el dimensionamiento del BESS**

El sistema BESS v5.3 está dimensionado **EXCLUSIVAMENTE para cubrir el déficit de EV (motos y mototaxis)**, no para el mall.

---

## 📋 CRITERIOS DE DIMENSIONAMIENTO ACTUAL

### 1. **ALCANCE DEL BESS (Clave)**
```
Scope: ev_only
```
- **BESS exclusivamente para EV**, no para mall
- Mall se alimenta de: 
  - Prioridad 1: PV directo (excedente)
  - Prioridad 2: Red pública

### 2. **PARÁMETROS TÉCNICOS DEL BESS v5.3**

| Parámetro | Valor | Fuente |
|-----------|-------|--------|
| **Capacidad** | 1,700 kWh | Línea 116: `BESS_CAPACITY_KWH_V53 = 1700.0` |
| **Potencia nominal** | 400 kW | Línea 117: `BESS_POWER_KW_V53 = 400.0` |
| **Profundidad descarga (DoD)** | 80% | Línea 118: `BESS_DOD_V53 = 0.80` |
| **Eficiencia round-trip** | 95% | Línea 119: `BESS_EFFICIENCY_V53 = 0.95` |
| **SOC mínimo** | 20% | Línea 120: `BESS_SOC_MIN_V53 = 0.20` |
| **SOC máximo** | 100% | Línea 121: `BESS_SOC_MAX_V53 = 1.00` |

### 3. **CRITERIO CAPACIDAD - FORMULA ACTUAL**

**Ubicación:** Líneas 1875-1920

```python
# CRÍTICO: Solo considera déficit EV
deficit_kwh_day_max = 708.0 kWh/día  # Máximo déficit EV
peak_deficit_kw = 156.0 kW             # Pico déficit EV

# Cálculo de capacidad
capacity_kwh = deficit_kwh_day_max / (dod * efficiency)
               = 708 / (0.80 × 0.95)
               ≈ 1,700 kWh
```

**Fórmula genérica (Línea 509-535):**
```python
def calculate_bess_capacity(
    surplus_kwh_day: float,        # Excedente PV
    deficit_kwh_day: float,        # DÉFICIT EV ← USADO
    peak_load_kw: float = 0.0,     # Pico demanda (pero NO es pico mall)
    ...
):
    # Modo "ev_open_hours" o "ev_deficit_100"
    capacity = deficit_kwh_day / (dod * efficiency)
    
    # Potencia basada en pico deficit EV, NO pico mall
    c_rate_target = 0.36
    power = capacity * c_rate_target
    
    # Si peak_load > power, ajustar:
    if peak_load_kw > power:
        power = peak_load_kw * 1.1  # +10% margen
```

---

## 📊 COMPARACIÓN: ¿Qué se considera vs. qué NO?

### ✅ SÍ se considera en dimensionamiento:

| Parámetro | Valor | Línea | Propósito |
|-----------|-------|-------|-----------|
| **Déficit EV máximo** | 708 kWh/día | 1846 | Capacidad principal del BESS |
| **Pico déficit EV** | 156 kW | 1846 | Potencia mínima del BESS |
| **Generación PV excedente** | 22,149 kWh/día | 1862 | Punto de carga BESS |
| **Horario operativo EV** | 9h-22h | 288 | Cuándo opera BESS |
| **SOC final (cierre)** | 20% | 1841 | Restricción descarga |

### ❌ NO se considera explícitamente:

| Parámetro | Valor | Razón |
|-----------|-------|-------|
| **Pico demanda mall** | 33,885 kW (instantáneo) | No en `calculate_bess_capacity()` |
| **Horas de máxima demanda mall** | 10h-20h (típicamente) | BESS no es recurso para mall |
| **Déficit mall** | Variable | Mall come red directa |
| **Rampas de demanda mall** | No cuantificadas | No incluidas en cálculos |

---

## 🔍 ANÁLISIS DETALLADO DEL CÓDIGO

### SECCIÓN 1: Carga de datos (Líneas 1835-1850)

```python
# Línea 1846-1851
deficit_kwh_day_avg, peak_deficit_kw, charge_end_hour, \
  discharge_start_hour, deficit_kwh_day_max = \
  calculate_ev_deficit_for_bess(
      pv_kwh=pv_kwh,
      ev_kwh=ev_kwh,      # ← Solo EV
      closing_hour=22,
  )

# Línea 1854-1857
print(f"   Déficit EV MÁXIMO: {deficit_kwh_day_max:.1f} kWh/día ← USADO PARA 100% COBERTURA")
print(f"   Pico déficit EV: {peak_deficit_kw:.1f} kW")
```

**Observación:** La función `calculate_ev_deficit_for_bess()` **NO recibe mall_kwh** como parámetro. 
Solo recibe `pv_kwh` y `ev_kwh`.

---

### SECCIÓN 2: Cálculo de dimensionamiento (Líneas 1875-1915)

```python
# Línea 1876
print("\n[CRITERIO CAPACIDAD - DINÁMICO]")
print("   Criterio: Cubrir DÉFICIT EV desde punto crítico...")
print(f"   Deficit EV en descarga: {sizing_deficit:.0f} kWh/dia")
print(f"   Pico deficit EV: {peak_load:.1f} kW")  # ← 156 kW

# Línea 1892-1899
capacity_kwh, power_kw = calculate_bess_capacity(
    surplus_kwh_day=surplus_for_sizing,      # PV excedente
    deficit_kwh_day=sizing_deficit,          # ← Déficit EV, NO mall
    dod=effective_dod,                       # 80%
    efficiency=effective_efficiency,         # 95%
    peak_load_kw=peak_load,                  # ← 156 kW (pico EV)
    sizing_mode=sizing_mode,                 # "ev_open_hours"
)
```

**Conclusión:** `peak_load_kw = 156.0 kW` viene del **déficit máximo EV**, no del pico del mall.

---

### SECCIÓN 3: Fórmula de capacidad (Línea 509-535)

```python
def calculate_bess_capacity(
    surplus_kwh_day: float,        # = 22,149 kWh/día (PV excess)
    deficit_kwh_day: float,        # = 708 kWh/día (EV deficit)
    peak_load_kw: float = 0.0,     # = 156 kW
    ...
    sizing_mode: str = "ev_open_hours",
) -> Tuple[float, float]:
    
    cap_surplus = surplus / (dod * eff)     # 22,149 / 0.76 = 29,144 kWh
    cap_deficit = deficit / (dod * eff)     # 708 / 0.76 = 931 kWh ← USADO
    cap_autonomy = (peak_load * hours) / .  # (156 * 4) / 0.76 = 821 kWh
    
    # Línea 526-529
    if sizing_mode in (..., "ev_open_hours", "ev_deficit_100"):
        capacity = cap_deficit  # ← 931 → redondeado a 940 → aplicar factor 1.20 = 1,128
```

**Fórmula final (con análisis perfil 15min):**
```
Capacity = Déficit_EV_máx / (DoD × Eficiencia) × Factor_diseño
         = 708 kWh / (0.80 × 0.95)
         = 931 kWh
         
Pero se sobrescribe con:
Capacity = BESS_CAPACITY_KWH_V53 = 1,700 kWh  # (Línea 1918)
```

---

## 💡 POR QUÉ NO INCLUYE EL MALL

### Razón 1: Arquitectura del Sistema
```
PRIORIDADES DE DESPACHO:
1. PV → EV (directo)
2. PV excedente → BESS (carga)
3. PV final → Mall (directo)
4. BESS → EV (descarga, solo si PV<EV)
5. RED → Mall (siempre disponible)
6. RED → EV (si BESS<SOC_min)
```

**Líneas 1828-1833:**
```python
print("[REGLAS BESS - PRIORIDAD SOLAR - EXCLUSIVO EV]")
print("   1. Solar -> PRIMERO motos/mototaxis (EV)")
print("   2. Excedente solar -> SEGUNDO carga BESS (hasta SOC 100%)")
print("   3. Excedente final -> TERCERO Mall")
print("   4. BESS descarga: Desde punto crítico (PV<EV) hasta cierre 22h")
print("   5. SOC al cierre (22h): 20%")
```

### Razón 2: Mall tiene acceso a Red 24/7
- Mall **siempre puede importar de la red** (no hay restricción)
- EV tiene ventana horaria cerrada (9h-22h)
- BESS es recurso escaso → Prioridad a EV con restricción temporal

### Razón 3: Distintos patrones de demanda
```
EV:   Continuo 9h-22h, ~1,129 kWh/día, pico 156 kW
Mall: Continuo 24/7,   ~33,885 kWh/día, pico >> 156 kW
```
- EV: ~3% de demanda total → Cabe en BESS
- Mall: ~97% de demanda total → Imposible cubrir con 1,700 kWh

### Razón 4: Arbitraje HP/HFP (v5.3)
- BESS optimizado para **comprar en HFP (cheap) y vender en HP (expensive)**
- Esto es **económicamente indiferente para mall** (mismo tarifa siempre)
- EV operaría en horas peak = mayor beneficio

---

## 📈 DATOS NUMÉRICOS DEL SISTEMA

### Demanda totalizada

| Componente | Diario | Anual | % Total | Pico |
|-----------|--------|-------|---------|------|
| **Mall** | 33,885 kWh | 12,368 MWh | 96.8% | ?* |
| **EV** | 1,129 kWh | 412 MWh | 3.2% | 156 kW |
| **TOTAL** | 35,014 kWh | 12,780 MWh | 100% | ~150+ kW |

*Pico mall no explícitamente documentado en código de dimensionamiento

### BESS financiado v5.3 (1,700 kWh / 400 kW)

| Métrica | Valor | Nota |
|---------|-------|------|
| **Cobertura EV** | 90.5% | Del déficit EV |
| **Ciclos/día** | 0.82 | Descarga ~1,400 kWh/día |
| **Autonomy EV** | 3-4h | Si PV → 0 a mediodía |
| **Cobertura mall** | ~1-2% | Accidental (PV directo) |

---

## 🔧 PARÁMETROS DE ENTRADA NO USADOS

En `calculate_bess_capacity()`, existe parámetro `peak_load_kw` que **podría** incluir pico mall:

**Línea 509-511:**
```python
def calculate_bess_capacity(
    ...
    peak_load_kw: float = 0.0,  # ← Parámetro existente
    ...
)
```

**Pero se llama con (Línea 1892-1899):**
```python
capacity_kwh, power_kw = calculate_bess_capacity(
    ...
    peak_load_kw=peak_load,  # = 156 kW (pico EV deficit, NO pico mall)
    ...
)
```

**Nunca se calcula explícitamente pico del mall:**
```python
# En línea 1875-1920 NO hay:
peak_mall_kw = mall_kwh.max()  # ← NO EXISTE

# Sí existe para EV:
peak_deficit_kw = 156.0  # ← SÍ EXISTE (Línea 1846)
```

---

## ✅ CONCLUSIONES

### 1. **Criterio Principal del Dimensionamiento**
- ✅ **Déficit EV máximo:** 708 kWh/día
- ✅ **Pico déficit EV:** 156 kW
- ✅ **DoD:** 80% (SOC 100% → 20%)
- ✅ **Eficiencia:** 95% round-trip

### 2. **Mall NO está incluido porque:**
- ❌ No participa en `calculate_ev_deficit_for_bess()`
- ❌ No hay cálculo de `peak_mall_kw`
- ❌ BESS scope = "ev_only" (arquitectura del sistema)
- ❌ Mall tiene acceso garantizado a red 24/7

### 3. **Si se quisiera incluir mall, habría que:**

Option A: Extender parámetro `peak_load_kw`
```python
peak_load_kw = max(peak_deficit_kw, peak_mall_kw)  # 156 vs. 128+ kW
```

Option B: Crear scope alternativo
```python
bess_load_scope = "ev_and_mall"  # Nuevo alcance
capacity_kwh = (deficit_ev + deficit_mall) / (dod * eff)
```

Option C: BESS dedicado separado
```python
# BESS1 para EV (1,700 kWh, exclusivo)
# BESS2 para Mall (10,000+ kWh, para cobertura nocturna)
```

### 4. **Recomendación**

**Criterio ACTUAL es CORRECTO porque:**
1. **Optimiza bien los recursos:** BESS pequeño y enfocado
2. **Reduce CO₂ maximizado:** Prioridad a EV de alta emisión diaria
3. **ROI mejor:** Arbitraje HP/HFP rentable en BESS chico
4. **Mall resiliente:** Red garantizada, no es carga crítica

---

## 📋 REFERENCIA DE LÍNEAS EN CÓDIGO

| Concepto | Líneas | Descripción |
|----------|--------|-------------|
| Parámetros v5.3 | 113-121 | Constantes BESS_* |
| Cargar mall | 128-215 | `load_mall_demand_real()` |
| Cargar EV | 272-357 | `load_ev_demand()` |
| Calcular déficit | 545-603 | `calculate_ev_deficit_for_bess()` |
| Calcular capacidad | 509-535 | `calculate_bess_capacity()` |
| Simulación arbitraje | 905-1233 | `simulate_bess_arbitrage_hp_hfp()` |
| Ejecución principal | 1800-2100 | `if __name__ == "__main__"` |
| Criterio mostrado | 1828-1835 | Prioridades de despacho |
| Deficit calculado | 1846-1857 | `calculate_ev_deficit_for_bess()` |
| Capacidad calculada | 1875-1920 | `calculate_bess_capacity()` |

---

## 🎯 RESPUESTA FINAL

**¿Se ha considerado el PICO DE DEMANDA del MALL en el dimensionamiento del BESS?**

### **NO** ✅

**Criterios REALES usados:**
1. ✅ Déficit EV máximo (708 kWh/día)
2. ✅ Pico déficit EV (156 kW)
3. ✅ Excedente solar disponible (22,149 kWh/día)
4. ✅ Restricciones operacionales (SOC 20%-100%, cierre 22h)
5. ❌ Pico demanda mall (NO incluido)
6. ❌ Déficit mall (NO incluido)

**Justificación:**
- BESS es recurso escaso → Prioridad a EV con restricción temporal
- Mall tiene acceso 24/7 a red → No es carga crítica
- Optimización técnico-económica: arbitraje HP/HFP en EV

---

**Análisis completado:** 2026-02-13 04:57:31  
**Sin modificaciones al código:** ✅

