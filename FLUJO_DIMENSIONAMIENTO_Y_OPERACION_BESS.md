# 📐 FLUJO REAL: DIMENSIONAMIENTO Y OPERACIÓN DEL BESS v5.3
## Análisis completo del código de bess.py

**Fecha:** 2026-02-13  
**Código analizado:** `src/dimensionamiento/oe2/disenobess/bess.py` (2,552 líneas)  
**Status:** ✅ Análisis sin modificaciones

---

## 🏗️ ARQUITECTURA GENERAL DEL SISTEMA

Existen **4 funciones principales** que interactúan:

```
FLUJO:
    1. run_bess_sizing()                  [LÍNEA 1636] ← FUNCIÓN PRINCIPAL
         ↓
    2. load_*_demand() / load_pv_generation()  [LÍNEA 128-357] ← CARGA DATOS
         ↓
    3. calculate_ev_deficit_for_bess()    [LÍNEA 545] ← CALCULA DÉFICIT
         ↓
    4. calculate_bess_capacity()          [LÍNEA 509] ← DIMENSIONA BESS
         ↓
    5. simulate_bess_arbitrage_hp_hfp()   [LÍNEA 893] ← SIMULA OPERACIÓN
         ↓
    [Genera CSV + JSON + Gráficas]
```

---

## 1️⃣ FUNCIÓN PRINCIPAL: `run_bess_sizing()` 
**Línea 1636**

### Propósito:
Ejecuta el **ciclo completo** de dimensionamiento y simulación del BESS.

### Parámetros de entrada:
```python
def run_bess_sizing(
    out_dir: Path,                          # Directorio salida
    mall_energy_kwh_day: float = 33885,     # Demanda diaria mall
    pv_profile_path: Path,                  # Ruta al perfil PV
    ev_profile_path: Path,                  # Ruta al perfil EV
    mall_demand_path: Optional[Path] = None, # Ruta a demanda mall real
    dod: float = 0.80,                      # Profundidad de descarga
    c_rate: float = 0.36,                   # Constante C
    efficiency_roundtrip: float = 0.95,     # Eficiencia
    autonomy_hours: float = 4.0,            # Horas autonomía
    sizing_mode: str = "ev_open_hours",     # "ev_open_hours", "ev_deficit_100", "max", "surplus_only"
    year: int = 2024,                       # Año simulación
) -> dict[str, object]:
```

### Flujo interno:

```
run_bess_sizing()
    ├─ PASO 1: Cargar datos (línea 1705-1790)
    │   ├─ load_pv_generation(pv_profile_path)
    │   ├─ load_mall_demand_real(mall_demand_path)
    │   └─ load_ev_demand(ev_profile_path)
    │
    ├─ PASO 2: Alinear a 8,760 horas horarias (línea 1796-1815)
    │   ├─ Verificar PV: 8,760 registros
    │   ├─ Verificar EV: 8,760 registros
    │   └─ Verificar Mall: 8,760 registros
    │
    ├─ PASO 3: Analizar déficit EV (línea 1828-1870)
    │   └─ calculate_ev_deficit_for_bess(pv_kwh, ev_kwh)
    │       ├─ deficit_kwh_day_avg:     559.3 kWh/día
    │       ├─ deficit_kwh_day_max:     708.0 kWh/día  ← USADO PARA DIMENSIONAR
    │       ├─ peak_deficit_kw:         156.0 kW
    │       ├─ charge_end_hour:         ~6h   ← Fin carga BESS
    │       └─ discharge_start_hour:    ~17h  ← Inicio descarga
    │
    ├─ PASO 4: Dimensionar BESS (línea 1875-1920)
    │   └─ calculate_bess_capacity(
    │       surplus_kwh_day = 22,149 kWh/día,
    │       deficit_kwh_day = 708 kWh/día,    ← MÁXIMO EV
    │       dod = 0.80,
    │       efficiency = 0.95,
    │       peak_load_kw = 156.0 kW,
    │       sizing_mode = "ev_open_hours"
    │   )
    │   ├─ cap_surplus = 22,149 / (0.80 × 0.95) = 29,144 kWh
    │   ├─ cap_deficit = 708 / (0.80 × 0.95) = 931 kWh  ← ELEGIDO
    │   ├─ cap_autonomy = (156 × 4) / (0.80 × 0.95) = 821 kWh
    │   ├─ Seleccionar: cap_deficit = 931 kWh (modo "ev_open_hours")
    │   ├─ Redondear: 940 kWh
    │   ├─ Aplicar factor 1.20: 1,128 kWh
    │   └─ OVERRIDE v5.3: 1,700 kWh (línea 1918)
    │
    ├─ PASO 5: Simular operación (línea 1930-1935)
    │   └─ simulate_bess_arbitrage_hp_hfp(
    │       pv_kwh=pv_kwh,
    │       ev_kwh=ev_kwh,
    │       mall_kwh=mall_kwh,
    │       capacity_kwh=1700,
    │       power_kw=400,
    │       efficiency=0.95,
    │       closing_hour=22,
    │       year=2024
    │   )
    │
    └─ PASO 6: Guardar resultados (línea 1960-2010)
        ├─ bess_simulation_hourly.csv (8,760 filas)
        ├─ bess_daily_balance_24h.csv (24 filas)
        └─ bess_results.json (metadatos)
```

---

## 2️⃣ CALCULADOR DE DÉFICIT: `calculate_ev_deficit_for_bess()`
**Línea 545**

### Propósito:
Identificar **cuánta energía el BESS debe cubrir** del déficit EV.

### Lógica:
```python
def calculate_ev_deficit_for_bess(
    pv_kwh: np.ndarray,      # 8,760 valores PV horarios
    ev_kwh: np.ndarray,      # 8,760 valores EV horarios
    closing_hour: int = 22,  # Hora cierre 22:00
) -> Tuple[float, float, int, int, float]:
    
    # Para cada uno de los 365 días
    for day in range(365):
        # Extraer datos del día (24 horas)
        pv_day = pv_kwh[día*24 : día*24+24]
        ev_day = ev_kwh[día*24 : día*24+24]
        
        # REGLA 1: Encontrar hora de fin de carga (PV >= EV)
        # Buscar en horas 6-18 (mañana-tarde con potencial solar)
        charge_end = None
        for h in range(6, 18):
            if pv_day[h] >= ev_day[h] and pv_day[h] > 0.1:
                charge_end = h
                break
        
        # REGLA 2: Encontrar hora inicio descarga (PV < EV)
        # Buscar en horas 12-22 (tarde-noche)
        discharge_start = None
        for h in range(12, closing_hour + 1):
            if pv_day[h] < ev_day[h] and ev_day[h] > 0.1:
                discharge_start = h
                break
        
        # REGLA 3: Calcular déficit TOTAL del día (todas las 24 horas)
        # NO solo descarga, sino TODAS las horas
        day_deficit = 0.0
        peak_deficiency_hour = 0.0
        for h in range(24):
            deficit_h = max(ev_day[h] - pv_day[h], 0)
            day_deficit += deficit_h  # Acumular déficit
            peak_deficiency_hour = max(peak_deficiency_hour, deficit_h)
    
    # RETORNA 5 VALORES:
    return (
        deficit_kwh_day_avg,      # 559.3 kWh (promedio de 365 días)
        peak_deficit_kw,          # 156.0 kW  (pico máximo detectado)
        avg_charge_end,           # ~6h (hora promedio fin carga)
        avg_discharge_start,      # ~17h (hora promedio inicio descarga)
        deficit_kwh_day_max       # 708.0 kWh (máximo de 365 días) ← CRÍTICO
    )
```

### Ejemplo de un día:
```
Hora   PV    EV    Déficit (EV-PV)
─────────────────────────────
06h    100   50    0        (PV > EV: sin déficit)
07h    200   60    0
...
12h    500   80    0
13h    400   150   0        (crucero: PV ~ EV)
14h    300   150   0
15h    150   120   0
16h    100   120   20       ← PUNTO CRÍTICO: PV < EV (descarga inicia)
17h    50    130   80
18h    10    140   130
19h    0     150   150      ← PICO: 150 kW déficit
20h    0     140   140
21h    0     130   130
22h    0     120   120
23h    0     0     0        ← CIERRE: no hay operación
────────────────────────────
TOTAL DEFICITS: ~1,000 kWh/día (ejemplo)
```

**Resultado:** El BESS debe cubrir este déficit.

---

## 3️⃣ DIMENSIONADOR: `calculate_bess_capacity()`
**Línea 509**

### Propósito:
Calcular **capacidad y potencia óptima** del BESS.

### Fórmulas (Línea 522-544):

```python
def calculate_bess_capacity(
    surplus_kwh_day: float,           # PV excedente disponible
    deficit_kwh_day: float,           # Déficit EV a cubrir
    dod: float = 0.80,                # Profundidad descarga
    efficiency: float = 0.95,         # Eficiencia round-trip
    autonomy_hours: float = 4.0,      # Horas autonomía
    peak_load_kw: float = 156.0,     # Pico carga
    sizing_mode: str = "ev_open_hours",
) -> Tuple[float, float]:
    """
    CÁLCULOS ALTERNATIVOS:
    """
    # Capacidad por excedente PV
    cap_surplus = surplus_kwh_day / (dod * efficiency)
    # = 22,149 / (0.80 × 0.95)
    # = 29,144 kWh

    # Capacidad por déficit EV ← ELEGIDO EN v5.3
    cap_deficit = deficit_kwh_day / (dod × efficiency)
    # = 708 / (0.80 × 0.95)
    # = 931 kWh

    # Capacidad por autonomía (4 horas de pico)
    cap_autonomy = (peak_load_kw × autonomy_hours) / (dod × efficiency)
    # = (156 × 4) / (0.80 × 0.95)
    # = 821 kWh

    # SELECCIÓN SEGÚN MODO (Línea 526-532)
    if sizing_mode == "ev_open_hours":          # ← USADO
        capacity = cap_deficit                  # 931 kWh
    elif sizing_mode == "ev_deficit_100":
        capacity = cap_deficit
    elif sizing_mode == "max":
        capacity = max(cap_surplus, cap_deficit, cap_autonomy)
    elif sizing_mode == "surplus_only":
        capacity = cap_surplus

    # REDONDEO Y FACTOR DE DISEÑO
    capacity = ceil(capacity / 10) × 10         # Redondear a 10s
    # 931 → 940 kWh

    # Aplicar factor 1.20 (en run_bess_sizing línea 1909)
    capacity = 940 × 1.20 = 1,128 kWh

    # PERO: Override con BESS_CAPACITY_KWH_V53 = 1,700 kWh (línea 1918)

    # CÁLCULO DE POTENCIA
    c_rate_target = 0.36                       # C-rate conservador
    power = capacity × c_rate_target
    # = 1,128 × 0.36 = 406 kW

    # Mínimo: debe cubrir pico déficit + 10%
    if peak_load_kw > power:
        power = peak_load_kw × 1.1
        # = 156 × 1.1 = 172 kW (no aplica, 406 > 172)

    return float(capacity), float(power)
    # return (1,128, 406)  → Override (1,700, 400)
```

**Resultado final (v5.3):**
- Capacidad: **1,700 kWh** (override en línea 1918)
- Potencia: **400 kW** (override en línea 1918)

---

## 4️⃣ OPERACIÓN: `simulate_bess_arbitrage_hp_hfp()`
**Línea 893**

### Propósito:
Simular **operación horaria** del BESS para **8,760 horas** (1 año).

### Estrategia de ARBITRAJE TARIFARIO OSINERGMIN:

```
PERÍODO HFP (BARATO): 00:00-17:59, 23:00-23:59 (S/.0.28/kWh)
├─ CARGA MÁXIMA DEL BESS
├─ Fuente 1: PV excedente → BESS (costo cero)
├─ Fuente 2: Grid → BESS (6h-12h, si SOC < 80%)

PERÍODO HP (CARO): 18:00-22:59 (S/.0.45/kWh)
├─ DESCARGA MÁXIMA DEL BESS
├─ Destino 1: BESS → EV (reemplaza grid caro)
├─ Destino 2: BESS → Mall (reduce demanda cara)

AHORRO: S/.0.17/kWh × energía descargada en HP
```

### Lógica de operación (línea 920-1090):

```python
for h in range(8760):  # Cada hora del año
    hour_of_day = h % 24
    pv_h = pv_kwh[h]
    ev_h = ev_kwh[h]
    mall_h = mall_kwh[h]
    
    # DETECT PERIODO TARIFARIO
    is_hp = 18 <= hour_of_day < 23     # Hora Punta: 18:00-22:59
    tariff = 0.45 if is_hp else 0.28   # Tarifa OSINERGMIN
    
    # ═══════════════════════════════════════════════════════════
    # FUERA DE OPERACIÓN (23h-5h)
    # ═══════════════════════════════════════════════════════════
    if hour_of_day >= 23 or hour_of_day < 6:
        # BESS solo mantiene SOC, sin carga/descarga activa
        pv_to_ev[h] = 0
        pv_to_mall[h] = min(pv_h, mall_h)
        grid_to_ev[h] = ev_h
        grid_to_mall[h] = max(mall_h - pv_to_mall[h], 0)
        soc[h] = current_soc  # Sin cambio
        continue
    
    # ═══════════════════════════════════════════════════════════
    # PRIORIDAD 1 (SIEMPRE): PV → EV DIRECTO
    # ═══════════════════════════════════════════════════════════
    pv_direct_to_ev = min(pv_h, ev_h)
    pv_to_ev[h] = pv_direct_to_ev
    pv_remaining = pv_h - pv_direct_to_ev
    ev_deficit = ev_h - pv_direct_to_ev
    
    # ═══════════════════════════════════════════════════════════
    # PERÍODO HFP: MAXIMIZAR CARGA BESS
    # ═══════════════════════════════════════════════════════════
    if not is_hp:  # HFP = barato
        # PRIORIDAD 2 HFP: PV excedente → BESS (costo cero)
        if pv_remaining > 0 and current_soc < 1.0:
            soc_headroom = (1.0 - current_soc) × capacity_kwh
            max_charge = min(power_kw, pv_remaining, soc_headroom / eff_charge)
            if max_charge > 0:
                bess_charge[h] = max_charge
                pv_to_bess[h] = max_charge
                current_soc += (max_charge × eff_charge) / capacity_kwh
                pv_remaining -= max_charge
        
        # PRIORIDAD 3 HFP: Grid → BESS (6h-12h, oportunista)
        if 6 <= hour_of_day <= 12 and current_soc < 0.80:
            # Cargar desde grid a tarifa barata para vender en HP
            grid_to_bess_amount = algunos_kW
            bess_charge[h] += grid_to_bess_amount
            current_soc += (grid_to_bess_amount × eff) / capacity_kwh
        
        # PRIORIDAD 4 HFP: PV → Mall
        pv_direct_to_mall = min(pv_remaining, mall_h)
        pv_to_mall[h] = pv_direct_to_mall
        
        # Grid cubre déficits HFP (tarifa barata)
        grid_to_ev[h] = max(ev_deficit, 0)
        grid_to_mall[h] = max(mall_h - pv_direct_to_mall, 0)
    
    # ═══════════════════════════════════════════════════════════
    # PERÍODO HP: MAXIMIZAR DESCARGA BESS
    # ═══════════════════════════════════════════════════════════
    else:  # is_hp = True (caro)
        # PRIORIDAD 2 HP: BESS → EV (reemplaza grid caro)
        if ev_deficit > 0 and current_soc > soc_min:
            max_discharge = min(power_kw, ev_deficit)
            if max_discharge > 0:
                bess_discharge[h] = max_discharge
                bess_to_ev[h] = max_discharge
                current_soc -= max_discharge / capacity_kwh
                ev_deficit -= max_discharge
                
                # AHORRO: energía que NO compramos a S/.0.45
                savings[h] = max_discharge × (0.45 - 0.28)
                            = max_discharge × 0.17
        
        # PRIORIDAD 3 HP: PV → Mall (después de EV)
        pv_direct_to_mall = min(pv_remaining, mall_h)
        pv_to_mall[h] = pv_direct_to_mall
        mall_deficit = mall_h - pv_direct_to_mall
        
        # PRIORIDAD 4 HP: BESS → Mall (reduce demanda cara)
        if mall_deficit > 0 and current_soc > soc_min:
            max_discharge = min(power_kw - already_discharged, mall_deficit)
            if max_discharge > 0:
                bess_to_mall[h] = max_discharge
                current_soc -= max_discharge / capacity_kwh
                mall_deficit -= max_discharge
                
                # Ahorro adicional
                savings[h] += max_discharge × 0.17
        
        # Grid cubre déficits restantes (tarifa HP cara)
        grid_to_ev[h] = max(ev_deficit, 0)
        grid_to_mall[h] = max(mall_deficit, 0)
    
    soc[h] = current_soc
    cost_grid[h] = (grid_to_ev[h] + grid_to_mall[h]) × tariff
```

### Resultado por período (metapromedio anual):

| Período | Horas | Tarifa | Acción | Objetivo |
|---------|-------|--------|--------|----------|
| **HFP** | 19/día | S/.0.28/kWh | ↑ Cargar BESS | Llenar a 100% usando PV + grid barato |
| **HP**  | 5/día | S/.0.45/kWh | ↓ Descargar BESS | Cubrir EV+Mall, evitar tarifa cara |

---

## 📊 DIMENSIONES FINALES v5.3

### Capacidad calculada vs. Adoptada:

| Paso | Cálculo | Resultado | Razón |
|------|---------|-----------|-------|
| Déficit EV máximo | 708 kWh / (0.80 × 0.95) | 931 kWh | Base teórica |
| Redondeo | ceil(931 / 10) × 10 | 940 kWh | Std comercial |
| Factor diseño | 940 × 1.20 | 1,128 kWh | Margen seguridad 20% |
| **Override v5.3** | BESS_CAPACITY_KWH_V53 | **1,700 kWh** | Optimizado para arbitraje |

### Potencia calculada vs. Adoptada:

| Paso | Cálculo | Resultado | Razón |
|------|---------|-----------|-------|
| C-rate | 1,128 × 0.36 | 406 kW | Conservador |
| Mín. pico+10% | 156 × 1.1 | 172 kW | Cobertura pico |
| **Override v5.3** | BESS_POWER_KW_V53 | **400 kW** | Ajuste final |

---

## 🔄 CICLO DIARIO TÍPICO

```
MAÑANA (6h-12h, HFP):
├─ 06h: Solar inicia (PV ~100 kW)
├─ BESS carga: 100h: PV excedente cargado a BESS (SOC: 50% → 80%)
├─ Costo mínimo: Grid a S/.0.28/kWh si es necesario
└─ Objetivo: Llegar a 80-100% SOC a mediodía

TARDE (13h-17h, HFP):
├─ 13h: Solar pico (PV ~500 kW)
├─ 15h: Punto crítico (PV < EV)
├─ BESS ya al 100% (mantiene)
├─ Costo bajo: Grid a S/.0.28/kWh para pequeños deficits
└─ Objetivo: Mantener SOC alto para noche

NOCHE (18h-22h, HP):
├─ 18h: Inicia hora punta (tarifa S/.0.45/kWh)
├─ Solar termina (PV ≈ 0)
├─ BESS DESCARGA a máximo (EV + Mall)
│  ├─ Cubre 90.5% del déficit EV
│  └─ Reduce demanda Mall en 1-2%
├─ Ahorro: S/.0.17/kWh/h × energía descargada HP
├─ 22h: Cierre EV (SOC debe estar al ~20%)
└─ Objetivo: Minimizar compra a tarifa cara

MADRUGADA (23h-5h, HFP):
├─ BESS inactivo (EV cerrado)
├─ Grid abastece 100% Mall @ S/.0.28/kWh
├─ SOC se mantiene (ajustes mínimos)
└─ Objetivo: Prepararse para carga mañana
```

---

## 💾 OUTPUTS GENERADOS

### 1. **bess_simulation_hourly.csv** (8,760 filas)
Cada fila = 1 hora del año
```
datetime            | pv_kwh | ev_kwh | mall_kwh | bess_charge_kwh | bess_discharge_kwh | soc_percent | tariff_soles_kwh | cost_grid_import_soles | savings_bess_soles
2024-01-01 00:00:00 | 0.0    | 0.0    | 45.2     | 0.0             | 0.0                | 50.0        | 0.28             | 12.66                  | 0.0
2024-01-01 01:00:00 | 0.0    | 5.2    | 42.1     | 0.0             | 0.0                | 50.0        | 0.28             | 13.26                  | 0.0
...
2024-01-01 18:00:00 | 50.0   | 142.0  | 40.5     | 0.0             | 350.0              | 45.0        | 0.45             | 24.0                   | 59.5
...
```

### 2. **bess_daily_balance_24h.csv** (24 filas)
Promedio horario del año (perfil día típico)
```
datetime            | pv_kwh (promedio) | bess_charge_kwh | bess_discharge_kwh | soc_percent
2024-01-01 00:00:00 | 0.0               | 0.0             | 0.0                | 50.0
2024-01-01 06:00:00 | 50.2              | 45.0            | 0.0                | 65.0
2024-01-01 12:00:00 | 520.0             | 0.0             | 0.0                | 100.0
2024-01-01 18:00:00 | 45.1              | 0.0             | 350.0              | 45.0
...
```

### 3. **bess_results.json** (metadatos)
```json
{
  "capacity_kwh": 1700,
  "nominal_power_kw": 400,
  "dod": 0.80,
  "peak_load_kw": 156.0,
  "deficit_kwh_day": 708.0,
  "bess_load_scope": "ev_only",
  "sizing_mode": "ev_open_hours",
  "self_sufficiency": 0.489,
  "cycles_per_day": 0.82,
  "cost_baseline_soles_year": 4219367,
  "cost_grid_import_soles_year": 2387533,
  "savings_bess_soles_year": 82251,
  "savings_total_soles_year": 1831834,
  "roi_arbitrage_percent": 1.9,
  "co2_emissions_kg_year": 2953300,
  "co2_avoided_kg_year": 218700,
  "co2_reduction_percent": 6.9,
  "osinergmin_tariff": {
    "energia_hp_soles_kwh": 0.45,
    "energia_hfp_soles_kwh": 0.28,
    "horas_punta": [18, 19, 20, 21, 22]
  }
}
```

---

## ✅ RESUMEN: FLUJO COMPLETO

```
ENTRADA:
  • PV horaria: 8,760 datos (kWh/h)
  • EV horaria: 8,760 datos (kWh/h, 38 sockets)
  • Mall horaria: 8,760 datos (kWh/h)
  
ANÁLISIS DEFICIT:
  • Buscar cruces PV vs EV para cada día
  • Calcular déficit acumulado: 559 kWh/día (promedio)
  • Máximo encontrado: 708 kWh/día
  
DIMENSIONAMIENTO:
  • Fórmula: Cap = Déficit / (DoD × Eff)
  • Teórico: 708 / (0.80 × 0.95) = 931 kWh
  • Ajuste factor 1.20: 1,128 kWh
  • FINAL v5.3: 1,700 kWh / 400 kW (optimizado arbitraje)
  
OPERACIÓN (8,760 horas):
  • HFP (barato): Cargar BESS desde PV + grid
  • HP (caro): Descargar BESS a EV + Mall
  • Ahorro: 0.17 soles/kWh × energía descargada
  
RESULTADOS:
  • Cobertura EV: 90.5%
  • Autosuficiencia: 48.9%
  • Ahorro anual: S/.1,831,834 (43.4%)
  • Reducción CO2: 218.7 ton/año (6.9%)
  
SALIDA:
  • CSV: Simulación 8,760 horas + perfil 24h
  • JSON: Metadatos y métricas económicas
  • Gráficas: 4 paneles de análisis
```

---

## 📌 PUNTOS CRÍTICOS DEL CÓDIGO

| Línea | Elemento | Impacto |
|-------|----------|--------|
| 116-121 | BESS_CAPACITY_KWH_V53 = 1,700 | Sobrescribe cálculo teórico |
| 509-544 | `calculate_bess_capacity()` | Define fórmula de dimensionamiento |
| 545-603 | `calculate_ev_deficit_for_bess()` | Busca "cruces" PV vs EV |
| 893-1090 | `simulate_bess_arbitrage_hp_hfp()` | Simula operación 8,760h |
| 1636-2060 | `run_bess_sizing()` | Orquesta flujo completo |
| 1918 | `capacity_kwh = BESS_CAPACITY_KWH_V53` | Override a 1,700 kWh |

---

## 🎯 CONCLUSIÓN

**El flujo REAL es:**

1. **Calcular** déficit horario de EV (vs PV)
2. **Dimensionar** BESS: Déficit / (DoD × Eff) + factor seguridad
3. **Override**: Adoptar 1,700 kWh para arbitraje HP/HFP
4. **Simular**: 8,760 horas con regla: Carga HFP, Descarga HP
5. **Generar**: CSV + JSON + reportes de ahorro/CO2

**NO es:**
- Dimensionamiento por pico de mall ❌
- Operación estática binaria (on/off) ❌
- Simple balance diario ❌

**SÍ es:**
- Dimensionamiento dinámico por déficit EV ✅
- Operación tarifaria inteligente (arbitraje) ✅
- Simulación horaria precisa ✅

