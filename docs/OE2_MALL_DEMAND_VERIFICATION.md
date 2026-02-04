# ✅ VERIFICACIÓN: Demanda Real del Mall en OE2

## 📊 Resultado: CONFIRMADO ✓

**La demanda de 3,092,204 kWh/año que aparece en Building_1.csv procede directamente de OE2.**

---

## 🔍 Fuente OE2

**Archivo**: `data/interim/oe2/demandamallkwh/demanda_mall_horaria_anual.csv`

**Contenido**:
- Registros: 8,760 horas (1 año completo)
- Período: 2024-01-01 00:00 a 2024-12-30 23:00
- Columnas: `datetime`, `kwh` (potencia en kWh por hora)

---

## 📈 Datos Técnicos

### Resumen Anual

| Métrica | Valor |
|---------|-------|
| **Total Anual** | **3,092,204 kWh** |
| Potencia Media | 352.99 kW |
| Mínima | 0.00 kW (horario cerrado/bajo) |
| Máxima | 690.75 kW (pico máximo) |
| Desv. Estándar | 201.21 kW |

### Validación Cruzada

| Fuente | Total Anual | Diferencia |
|--------|-------------|-----------|
| OE2 (`demanda_mall_horaria_anual.csv`) | 3,092,204 kWh | - |
| Building_1.csv (`non_shiftable_load`) | 3,092,204 kWh | **0 kWh (0.00%)** ✓ |

**Conclusión**: COINCIDENCIA EXACTA - Los datos son idénticos

---

## 📊 Perfil de Demanda Horario

### Rango por Hora del Día (Promedios Anuales)

```
Hora  Media(kW)  Mín(kW)  Máx(kW)  Patrón
────────────────────────────────────────
00    132.89     29.25    194.25   Bajo - Noche
01    120.76     0.00     180.75   Muy Bajo - Madrugada
02    117.41     0.00     174.25   Muy Bajo - Madrugada
03    114.92     0.00     166.25   Muy Bajo - Madrugada ← MÍNIMO
04    113.37     0.00     164.00   Muy Bajo - Madrugada
05    108.64     55.00    158.25   Bajo - Antes apertura
06    128.41     31.75    187.00   Bajo - Apertura temprana
07    165.11     0.00     249.75   Bajo-Medio - Apertura
08    217.03     0.00     315.00   Medio - Mañana temprana
09    280.22     0.00     468.00   Medio-Alto - Mañana
10    427.92     0.00     546.25   Alto - Mediodía inicio
11    548.57     0.00     676.50   Muy Alto - Pico
12    560.09     0.00     689.50   Muy Alto - Pico ← MÁXIMO (~690 kW)
13    562.68     0.00     690.25   Muy Alto - Pico
14    568.44     0.00     689.25   Muy Alto - Pico ← PICO MÁXIMO
15    570.28     0.00     686.00   Muy Alto - Pico ← PICO MÁXIMO
16    566.09     15.50    690.75   Muy Alto - Pico ← REAL MÁXIMO (690.75)
17    560.91     255.00   676.50   Muy Alto - Tarde
18    554.95     264.50   662.50   Alto - Tarde
19    547.34     267.75   663.50   Alto - Tarde
20    536.99     263.50   648.75   Alto - Tarde
21    497.62     252.25   616.50   Medio-Alto - Atardecer
22    306.90     141.75   545.00   Medio - Noche temprana
23    164.25     114.25   388.50   Bajo - Noche
────────────────────────────────────────
```

### Interpretación

**Picos de demanda (11:00-17:00)**:
- Horas 11-16 (11am-4pm): **548-570 kW promedio**
- Coincide con horario de operación máxima del mall
- Pico real máximo: **690.75 kW** (hora 16)

**Valle de demanda (04:00-06:00)**:
- Horas 4-5 (4am-6am): **108-113 kW promedio**
- Coincide con horario de cierre nocturno
- Valor mínimo: **0 kW** (varias horas de madrugada)

**Patrón típico**:
1. Noche baja (00:00-07:00): 108-165 kW
2. Subida matinal (08:00-11:00): 217-548 kW
3. **PICO MÁXIMO (12:00-16:00): 560-570 kW**
4. Bajada vespertina (17:00-23:00): 555-165 kW

---

## 🔗 Integración OE2 → OE3

### Pipeline de Datos

```
OE2 (Dimensionamiento)
  ↓
demanda_mall_horaria_anual.csv (3,092,204 kWh/año)
  ↓
dataset_builder.py: dataset_builder.py líneas 881-907
  ├─ Lee demanda del mall de OE2
  ├─ Asigna a energy_simulation.csv (non_shiftable_load)
  ↓
Building_1.csv (CityLearn)
  ├─ non_shiftable_load: 3,092,204 kWh/año
  ├─ dhw_demand: 0 kWh
  ├─ cooling_demand: 0 kWh
  ├─ heating_demand: 0 kWh
  ↓
simulate.py: _extract_building_load_kwh()
  └─ Extrae non_shiftable_load durante simulación
```

### Validación en dataset_builder.py (líneas 881-907)

```python
# PRIORIDAD 1: Usar datos OE2 directos (mall_demand)
if "mall_demand" in artifacts:
    mall_df = artifacts["mall_demand"].copy()
    # ... procesamiento ...
    mall_series = mall_df['kwh'].values[:n]  # Extrae exactos 3,092,204 kWh
    
# Asignar a energy_simulation
df_energy[load_col] = mall_series  # non_shiftable_load ← 3,092,204 kWh

df_energy.to_csv(energy_path, index=False)
```

---

## ✅ Conclusiones Verificadas

1. **✓ Demanda del mall está correctamente importada de OE2**
   - Fuente: `data/interim/oe2/demandamallkwh/demanda_mall_horaria_anual.csv`
   - Valor: 3,092,204 kWh/año

2. **✓ Está correctamente asignada a Building_1.csv**
   - Columna: `non_shiftable_load`
   - Valor: 3,092,204 kWh/año
   - Coincidencia: EXACTA (0.00% diferencia)

3. **✓ El perfil horario es coherente**
   - Picos: 12:00-16:00 (~560-570 kW)
   - Valles: 04:00-06:00 (~108-113 kW)
   - Patrón: Típico de operación comercial/mall

4. **✓ Está siendo extraída correctamente en simulaciones**
   - Función: `_extract_building_load_kwh()` en simulate.py
   - Modo: Se extrae `non_shiftable_load` del building

5. **✓ EV chargers se extraen por separado**
   - Fuente: `charger_simulation_001.csv` a `charger_simulation_128.csv`
   - Función: `_extract_ev_charging_kwh()` en simulate.py
   - NO está incluido en los 3,092,204 kWh

---

## 📋 Resumen

**La demanda del mall de 3,092,204 kWh/año es:**
- ✅ Correcta según OE2
- ✅ Coherente con el perfil horario (picos 12-16h, valles 4-6h)
- ✅ Correctamente importada a CityLearn (Building_1.csv)
- ✅ Correctamente extraída en simulaciones (non_shiftable_load)
- ✅ Completamente separada de demanda de chargers (que se extrae aparte)

**VERIFICACIÓN COMPLETADA**: Sistema en correcto funcionamiento ✓
