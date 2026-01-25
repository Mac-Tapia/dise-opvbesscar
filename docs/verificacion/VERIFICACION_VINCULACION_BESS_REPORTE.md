# VERIFICACIÓN DE VINCULACIÓN: bess.py ↔ chargers.py ↔ solar_pvlib.py

**Fecha:** 24 de enero de 2026  
**Estado:** ✅ VERIFICADO - Todos los vínculos funcionan correctamente

---

## RESUMEN EJECUTIVO

El archivo `bess.py`está **correctamente vinculado y actualizado** con los
datos calculados por `chargers.py`y `solar_pvlib.py`. Todas las verificaciones
han pasado exitosamente.

---

## 1. ARCHIVOS DE ENTRADA PARA BESS

### Desde CHARGERS (EV Fleet)

- **Archivo principal:** `data/interim/oe2/chargers/perfil_horario_carga.csv`
- **Formato:** 24 filas (hour, factor, energy_kwh, power_kw, is_peak)
- **Energía diaria:** 3,252 kWh
- **Función de lectura en bess.py:** `load_ev_demand()`

### Desde SOLAR (Photovoltaic)

- **Archivo primario:** `data/interim/oe2/solar/pv_generation_timeseries.csv`
  - (8760 filas)
- **Archivo secundario:** `data/interim/oe2/solar/pv_profile_24h.csv` (24 filas)
- **Energía diaria promedio:** 22,036 kWh
- **Capacidad instalada:** 4,162 kWp DC
- **Función de lectura en bess.py:** `load_pv_generation()`

### Demanda del Mall

- **Archivo:** `data/interim/oe2/demandamallkwh/demanda_mall_kwh.csv` (si
  - existe)
- **Fallback:** Perfil sintético basado en `mall_energy_kwh_day` del config
- **Función de lectura en bess.py:** `load_mall_demand_real()`

---

## 2. PARÁMETROS CLAVE VERIFICADOS

<!-- markdownlint-disable MD013 -->
### CHARGERS.PY → BESS.PY | Parámetro | Valor en chargers.py | Lectura en bess.py | Estado | |-----------|---------------------|-------------------|--------| | Energía diaria EV | 3,252 kWh | 3,252 kWh | ✅ | | Cargadores instalados | 32 unidades | (referencia) | ✅ | | Potencia pico | 406.5 kW | (referencia) | ✅ | | Potencia instalada | 272 kW | (referencia) | ✅ | | Horario operación | 9h - 22h (13h) | 9h - 22h | ✅ | ### SOLAR_PVLIB.PY → BESS.PY | Parámetro | Valor en solar_pvlib.py | Lectura en bess.py | Estado | |-----------|------------------------|-------------------|--------| | Capacidad DC | 4,162 kWp | 4,162 kWp | ✅ | | Energía anual | 8,043 GWh | 8,043 GWh | ✅ | | Energía diaria promedio | 22,036 kWh | 22,036 kWh | ✅ | | Factor de capacidad | 28.7% | (calculado) | ✅ | | Intervalo de datos | 15 min (8760×4) | Resampleado a horario | ✅ | ---

## 3. FLUJO DE DATOS

<!-- markdownlint-disable MD013 -->
```bash
┌─────────────────────┐
│  chargers.py        │
│  run_charger_sizing()│
└──────────┬──────────┘
           │ Genera
           ▼
   perfil_horario_carga.csv
   (Demanda EV horaria)
           │
           │ Lee
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│                     │     │  solar_pvlib.py     │
│    bess.py          │     │  run_solar_sizing() │
│  run_bess_sizing(...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 4. FUNCIONES DE LECTURA EN BESS.PY

### `load_ev_demand(ev_profile_path, year=2024)`

- **Entrada:** `perfil_horario_carga.csv` (24 filas)
- **Salida:** DataFrame 8760 filas con columna `ev_kwh`
- **Proceso:** Expande perfil de 24h a año completo repitiendo patrón diario
- **Estado:** ✅ Funciona correctamente

### `load_pv_generation(pv_timeseries_path)`

- **Entrada:** `pv_generation_timeseries.csv` (35,040 filas @ 15 min)
- **Salida:** DataFrame 8760 filas con columna `pv_kwh`
- **Proceso:**
  - Detecta columna de tiempo automáticamente
  - Resamplea de 15 min → 1h (sum)
  - Busca columna de energía PV
- **Estado:** ✅ Funciona correctamente

### `load_mall_demand_real(mall_demand_path, year=2024)`

- **Entrada:** Archivo CSV con demanda real del mall
- **Salida:** DataFrame 8760 filas con columna `mall_kwh`
- **Proceso:**
  - Detecta separador (`,` o `;`)
  - Detecta columnas de fecha/demanda automáticamente
  - Convierte kW → kWh si es necesario
  - Resamplea a horario
  - Repite datos si no cubre año completo
- **Estado:** ✅ Funciona correctamente

---

## 5. SCRIPT DE EJECUCIÓN

**Archivo:** `scripts/run_oe2_bess.py`

### Rutas configuradas

<!-- markdownlint-disable MD013 -->
```python
pv_profile_path = rp.interim_dir / "oe2" / "solar" / "pv_profile_24h.csv"
ev_profile_path = rp.interim_dir / "oe2" / "chargers" / "perfil_horario_carga.csv"
mall_demand_path = rp.interim_dir / "oe2" / "demandamallkwh" / "demanda_mall_kwh.csv"
```bash
<!-- markdownlint-enable MD013 -->

### Parámetros pasados desde config

- `mall_energy_kwh_day`: Demanda diaria mall (fallback)
- `dod`: Profundidad...
```

[Ver código completo en GitHub]yaml
oe2:
  ev_fleet:
    motos_count: 900          # ← Usado por chargers.py
    mototaxis_count: 130      # ← Usado por chargers.py
    pe_motos: 0.9             # ← Usado por chargers.py
    pe_mototaxis: 0.9         # ← Usado por chargers.py
    opening_hour: 9           # ← Usado por chargers.py y bess.py
    closing_hour: 22          # ← Usado por chargers.py y bess.py
  
  solar:
    target_dc_kw: 4162.0      # ← Usado por solar_pvlib.py y bess.py
    target_ac_kw: 3201.2      # ← Usado por solar_pvlib.py
    surface_tilt: 10.0        # ← Usado por solar_pvlib.py
    surface_azimuth: 0.0      # ← Usado por solar_pvlib.py
  
  bess:
    dod: 0.90                 # ← Usado por bess.py
    c_rate: 0.50              # ← Usado por bess.py
    efficiency_roundtrip: 0.90 # ← Usado por bess.py
    sizing_mode: "ev_open_hours" # ← Usado por bess.py
    load_scope: "total"       # ← Usado por bess.py
```bash
<!-- markdownlint-enable MD013 -->

---

## 7. VALORES CALCULADOS (ESTADO ACTUAL)

### Sistema EV Charging (chargers.py)

- **Cargadores:** 32 unidades (28 motos + 4 mototaxis)
- **Tomas totales:** 128 (32 × 4)
- **Potencia instalada:** 272 kW
  - Motos: 224 kW (28 × 4 × 2.0 kW)
  - Mototaxis: 48 kW (4 × 4 × 3.0 kW)
- **Energía diaria:** 3,252 kWh
- **Potencia pico:** 406.5 kW
- **Capacidad:** 3,0...
```

[Ver código completo en GitHub]bash
# Ejecutar dimensionamiento BESS con datos actualizados
python scripts/run_oe2_bess.py --config configs/default.yaml

# Verificar vinculación en cualquier momento
python VERIFICACION_VINCULACION_BESS.py
```bash
<!-- markdownlint-enable MD013 -->

### 📊 Próximos Pasos

1. Ejecutar `run_oe2_bess.py` para generar resultados BESS
2. Revisar gráficas de balance energético
3. Analizar autosuficiencia y ciclos de batería
4. Ajustar parámetros de BESS si es necesario (DoD, C-rate, sizing_mode)

---

## 11. REFERENCIAS

### Archivos Clave

- **Código BESS:** `src/iquitos_citylearn/oe2/bess.py`
- **Código Chargers:** `src/iquitos_citylearn/oe2/chargers.py`
- **Código Solar:** `src/iquitos_citylearn/oe2/solar_pvlib.py`
- **Script BESS:** `scripts/run_oe2_bess.py`
- **Configuración:** `configs/default.yaml`
- **Verificación:** `VERIFICACION_VINCULACION_BESS.py`

### Documentación Relacionada

- `ACTUALIZACION_CODIGO_CHARGERS_FINAL.md`: Reglas de cálculo chargers
- `RESUMEN_DIMENSIONAMIENTO_CHARGERS.md`: Documentación técnica chargers
- Reportes técnicos en `data/interim/oe2/*/`

---

**Generado:** 24 de enero de 2026  
**Verificado por:** Script automatizado VERIFICACION_VINCULACION_BESS.py  
**Estado:** ✅ TODAS LAS VERIFICACIONES PASARON
