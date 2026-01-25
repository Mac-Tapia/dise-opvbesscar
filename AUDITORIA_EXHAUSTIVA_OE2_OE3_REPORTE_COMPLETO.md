# AUDITORÍA EXHAUSTIVA OE2→OE3: ANÁLISIS INTEGRAL

## Análisis de Integridad de Datos, Pipeline de Transformación y Conectividad

**Fecha**: 25 de enero de 2026  
**Proyecto**: Iquitos EV + PV/BESS (OE2→OE3)  
**Objetivo**: Identificar gaps, errores e inconsistencias en el pipeline de
datos energéticos

---

<!-- markdownlint-disable MD013 -->
## TABLA RESUMEN EJECUTIVA | Aspecto | Encontrado | Esperado | Estado | Prioridad | |---------|-----------|----------|--------|-----------| | **Estructura OE2** | 35 archivos | - | ✓ Completa | - | |**Timeseries Solar**|35,037 filas (15-min)|8,760 (1-hora)|❌ CRÍTICO|MÁXIMA| | **Chargers individuales** | 128 | 128 | ✓ Correcto | - | | **Charger profiles CSV** | 0 generados | 128 | ❌ CRÍTICO | MÁXIMA | | **BESS configuración** | 4,520 kWh | 2,000 kWh | ⚠️ MISMATCH | ALTO | | **Dataset builder** | Existe | Existe | ✓ | - | | **Schema CityLearn** | No validado | 534-dim obs | ❌ NO VERIFICADO | ALTO | | **Integración OE2→OE3** | Parcial | Completa | ❌ GAPS | CRÍTICO | ---

## PARTE 1: ANÁLISIS ESTRUCTURA OE2

### 1.1 Inventario de Archivos OE2

<!-- markdownlint-disable MD013 -->
#### Carpeta: `data/interim/oe2/solar/` (8 archivos, 4.4 MB) | Archivo | Tamaño | Contenido | Estado | |---------|--------|----------|--------|
|`pv_generation_timeseries.csv`|**4.34 MB**|35,037 filas ×...|❌ Resolución incorrecta| | `solar_results.json` | 0.01 MB | Config PV: 4162 kWp DC,... | ✓ | | `solar_technical_report.md` | 0.01 MB | Reporte técnico Kyocera... | ✓ | | `pv_profile_24h.csv` | <0.01 MB | Perfil 24h agregado | ✓ | | `pv_monthly_energy.csv` | <0.01 MB | Energía mensual | ✓ | |`pv_candidates_*.csv`|~0.01 MB total|Alternativas de diseño|ℹ️ Informativo| **Hallazgo crítico**: Resolución 15-minutos vs esperada 1-hora

<!-- markdownlint-disable MD013 -->
```bash
actual:   35,037 filas × 15 min/fila = ~8,759.25 horas
esperado: 8,760 filas × 60 min/fila = ~8,760 horas
```bash
<!-- markdownlint-enable MD013 -->

**AC Power range**: 0.0 - 2,886.7 kW (válido, con saturación esperada en
inversor)

<!-- markdownlint-disable MD013 -->
#### Carpeta: `data/interim/oe2/chargers/` (17 archivos, 0.2 MB) | Archivo | Tamaño | Contenido | Estado | |---------|--------|---...
```

[Ver código completo en GitHub]bash
✓ Columnas presentes: ghi_wm2, dni_wm2, dhi_wm2, temp_air_c, wind_speed_ms, 
                      dc_power_kw, ac_power_kw, dc_energy_kwh, ac_energy_kwh, pv_kwh
✓ Rango AC Power: 0.0 - 2,886.7 kW (saturado a ~2,886.69 kW durante picos)
✓ Sin valores NaN
❌ Resolución: 35,037 filas (15-min) vs 8,760 esperadas (1-hora)
   → Diferencia: 4x más datos de los necesarios
```bash
<!-- markdownlint-enable MD013 -->

**Implicación**: El downsampling debe hacerse en dataset_builder, pero **NO
está implementado**.

### 2.2 Validación Chargers

<!-- markdownlint-disable MD013 -->
```bash
✓ 128 chargers en individual_chargers.json (CORRECTO)
✓ Estructura: charger_id, charger_type, power_kw, sockets, hourly_load_profile[24]
✓ Perfiles horarios válidos (24 horas por charger)
✗ FAL...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Composición de chargers**:

- Playa Motos: ~28 chargers × 2 kW × 4 tomas = 224 kW
- Playa Mototaxis: ~4 chargers × 3 kW × 4 tomas = 48 kW
- **Total: 272 kW instalado**

**Daily profiles**:

<!-- markdownlint-disable MD013 -->
```bash
 Hora | Power (kW) | Factor | Energy (kWh) | Peak? 
 ------ | ----------- | -------- | -------------- | ------ 
 0-9 | 0 | 0.0 | 0.0 | No 
 10 | 13.9 | 0.0043 | 13.9 | No 
 11 | 51.3 | 0.0158 | 51.3 | No 
...
 18-21 | 406.5 | 0.125 | 406.5 c/hora | YES (peak) 
 22-23 | 0 | 0.0 | 0.0 | No 
 ------ | ----------- | -------- | -------------- | ------ 
 TOTAL | - | - | 3,252.0 | 4 horas pico 
```bash
<...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

<!-- markdownlint-disable MD013 -->
### 2.4 Consistencia Entre Archivos | Métrica | Valor | Validación | |---------|-------|-----------| | PV generación anual | 8.04 GWh | ✓ Razonable (8,760h × 918 kW promedio) | | EV demanda anual | 1,187 MWh | ✓ 3,252 kWh/día × 365 días | | Ratio PV/EV | 6.76× | ✓ PV suficiente... | | BESS ciclos/día | 0.767 | ✓ Realista (no sobredimensionado) | ---

## PARTE 3: ANÁLISIS DATASET_BUILDER

<!-- markdownlint-disable MD013 -->
### 3.1 Cobertura de Artefactos OE2 | Artefacto OE2 | ¿Cargado? | Ubicación en builder | Transformación | |---------------|-----------|----------------------|-----------------| | `solar_ts` | ✓ | Línea ~87 | Lee CSV, pero **NO downsamples** | | `ev_profile_24h` | ✓ | Línea ~94 | Lee perfil 24h, **NO expande a 365d** | | `individual_chargers` | ✓ | Línea ~98 | Lee JSON, pero **NO genera CSVs** | | `bess` | ✓ | Línea ~158 | Lee resultados, **asignación... | | `chargers_results` | ✓ | Línea ~105 | Lee dimensionamiento,... | ### 3.2 Transformaciones Implementadas | Transformación | ¿Implementado? | Estado | Impacto | |----------------|---------------|--------|--------| | Schema generation | ✓ | OK | Crea edificio unificado Mall_Iquitos | | PV update | ✓ | **PARCIAL** | Asigna nominal_power pero no timeseries | | BESS update | ✓ | **PARCIAL** | Asigna capacidad pero no sim. horaria | |Chargers definition|✓|**INCOMPLETO**|Define chargers pero sin CSV paths| | CSV discovery | ✓ | **PROBLEMATIC** | Busca CSVs que no existen | ### 3.3 Transformaciones Faltantes

<!-- markdownlint-disable MD013 -->
```python
# ❌ FALTA 1: Downsampling solar 15-min → 1-hora
# Código que DEBERÍA estar en dataset_builder:
df_solar = pd.read_csv(interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv")
df_solar_hourly = df_solar.resample('1H')['ac_power_kw'].mean()  # 35037 → 8760 filas

# ❌ FALTA 2: Expansión charger 24h → 365d
# Código que DEBERÍA generar:
df_charger_daily = df_charger_24h  # 24 horas
df_charger_an...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## PARTE 4: SCHEMA CITYLEARN V2 - VALIDACIÓN

### 4.1 Estructura Esperada

<!-- markdownlint-disable MD013 -->
```json
{
  "central_agent": true,
  "seconds_per_time_step": 3600,
  "buildings": {
    "Mall_Iquitos": {
      "pv": { "nominal_power": 4162.0 },
      "electrical_storage": { "capacity": 4520.0 },
      "chargers": {
        "MOTO_CH_001": { "charger_simulation": "MOTO_CH_001.csv" },
        "MOTO_CH_002": { "charger_simulation": "MOTO_CH_002.csv" },
        ...
        "TAXI_CH_032": { "charger_simula...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

<!-- markdownlint-disable MD013 -->
### 4.2 Problemas Detectados en Schema Actual | Componente | Esperado | Actual | Problema | |------------|----------|--------|----------| | **pv.nominal_power** | 4,162 kWp | ✓ Asignado | OK | |**electrical_storage.capacity**|2,000-4,520 kWh|⚠️ 4,520|MISMATCH doc.| | **chargers.count** | 128 | ✓ 128 | OK | |**charger_simulation paths**|✓ Valid paths|❌ Paths no existen|CRÍTICO| | **non_shiftable_load.csv** | ✓ 8,760 rows | ❌ NO ENCONTRADO | CRÍTICO | | **electric_vehicles_def.count** | 128 | ✓ 128 | OK | ---

## PARTE 5: ERRORES Y GAPS IDENTIFICADOS (Priorizado)

### Severidad: 🔴 CRÍTICO (Bloquean training)

#### ERROR #1: Resolución Solar Incorrecta

**Componente**: OE2 Solar  
**Descripción**:  

- `pv_generation_timeseries.csv` tiene **35,037 filas** (resolución 15-minutos)
- CityLearn espera **8,760 filas** (resolución 1-hora)
- Diferencia: **4x más datos** de los necesarios

**Impacto**:

- Timesteps desalineados entre solar y otros observables
- Training más lento (4x más pasos por episodio)
- Posible error en cálculo de rewards (rewards a cada 15-min en lugar de cada
  - hora)

**Recomendación**:

<!-- markdownlint-disable MD013 -->
```python
# En dataset_builder, línea ~450 (donde se carga solar):
df_solar = pd.read_csv(interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv")
# Resample 15-min → 1-hora
df_solar['timestamp'] = pd.to_datetime(df_solar['timestamp'])
df_solar = df_solar.set_index('timestamp')
df_solar_hourly = df_solar.resample('1H')['ac_power_kw'].mean()
# Ahora 35037 → 8760 filas
df_solar_hourly.to_csv(output_dir...
```

[Ver código completo en GitHub]python
# En dataset_builder, después de crear schema:
for charger in chargers_df.iterrows():
    charger_id = charger['charger_id']
    charger_path = output_dir / f"buildings/Mall_Iquitos/{charger_id}.csv"
    
    # Crear CSV anual (365 × 24 horas)
    df_annual = pd.concat([df_charger_24h] * 365, ignore_index=True)
    df_annual.to_csv(charger_path, index=False)
```bash
<!-- markdownlint-enable MD013 -->

---

#### ERROR #3: Falta Mapping entre Chargers Individuales y CSVs

**Componente**: OE2 Chargers  
**Descripción**:  

- `individual_chargers.json` contiene 128 chargers con metadata
- Pero **NO hay CSV individual** para cada uno
- Solo existe `perfil_horario_carga.csv` (perfil agregado 24h)
- `annual_datasets/` existe pero no se consulta

**Impacto**:

- data...
```

[Ver código completo en GitHub]python
np.random.seed(charger_id)
noise = np.random.normal(1.0, 0.1, 8760)  # ±10% ruido
df_annual_noisy = df_annual * noise
```bash
<!-- markdownlint-enable MD013 -->

---

#### ERROR #4: No Hay Código para Convertir Solar 15-min → 1-hora

**Componente**: dataset_builder  
**Descripción**:  

- dataset_builder lee `pv_generation_timeseries.csv` (35k filas)
- **NO TIENE LÓGICA** para remuestrear a 8,760 horas
- Línea ~450 simplemente trunca: `n = min(len(df_energy), 8760)`

**Impacto**:

- Solar energy será interpolada/extrapol...
```

[Ver código completo en GitHub]python
# Línea ~450 en dataset_builder:
charger_csv = f"{charger_name}.csv"  # ← Path relativo incorrecto

# DEBERÍA ser:
charger_csv = f"buildings/Mall_Iquitos/{charger_name}.csv"
```bash
<!-- markdownlint-enable MD013 -->

**Impacto**:

- CityLearn no encuentra los CSVs de chargers
- Falla al cargar dataset

---

### Severidad: 🟠 ALTO (Degradan resultados)

#### ERROR #6: Falta CSV Individual para Chargers

**Componente**: dataset_builder  
**Descripción**:  

- dataset_builder intenta asignar `charger_simulation` paths
- **PERO NO CREA LOS ARCHIVOS**
- CityLearn.load_dataset() fa...
```

[Ver código completo en GitHub]python
# En dataset_builder, línea ~320:
building["electrical_storage"]["attributes"]["nominal_power"] = bess_pow
building["electrical_storage"]["attributes"]["efficiency"] = cfg['efficiency_roundtrip']
building["electrical_storage"]["attributes"]["min_soc"] = 1 - cfg['dod']
```bash
<!-- markdownlint-enable MD013 -->

---

#### ERROR #8: Charger Daily Profile No Expandido a 365 Días

**Componente**: OE2 Chargers  
**Descripción**:  

- `perfil_horario_carga.csv` es solo 24 horas
- No hay lógica para expandir a 365 días con variación realista
- Sin variación, datos son muy simplistas para RL

---

#### ERROR #9: Demanda Mall (non_shiftable_load) Incompleta

**Componente**: OE2...
```

[Ver código completo en GitHub]python
# Al final de dataset_builder:
env = CityLearnEnv(schema=schema_path)
obs, _ = env.reset()
assert len(obs) == 534, f"Expected 534-dim obs, got {len(obs)}"
```bash
<!-- markdownlint-enable MD013 -->

---

#### ERROR #12: Función de Recompensa Usa Observables No Documentados

**Componente**: rewards.py  
**Descripción**:  

- rewards.py computa `r_solar` usando 'pv_used_directly'
- Observable **no está claramente mapeado** en schema
- Rewards pueden ser NaN o flat durante training

---

#### ERROR #13: Timezone Inconsistencia

**Componente**: OE2 (All)  
**De...
```

[Ver código completo en GitHub]python
for charger in chargers:
    hourly_sum = sum(charger['hourly_load_profile'])
    daily_energy = charger['daily_energy_kwh']
    assert abs(hourly_sum - daily_energy) < 0.1, f"Profile mismatch for {charger['id']}"
```bash
<!-- markdownlint-enable MD013 -->

---

## PARTE 6: DATA FLOW DIAGRAM (Actual vs Esperado)

### Flujo Actual (Incompleto)

<!-- markdownlint-disable MD013 -->
```bash
OE2 ARTIFACTS
├─ pv_generation_ts.csv (35k filas, 15-min) ──┐
├─ individual_chargers.json (128)             ├──→ dataset_builder ──→ schema.json (INCOMPLETO)
├─ perfil_horario_carga.csv (24h)            │                            ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Flujo Esperado (Correcto)

<!-- markdownlint-disable MD013 -->
```bash
OE2 ARTIFACTS
├─ pv_generation_ts.csv (35k)
│   ↓ [RESAMPLE 15min→1h]
│   → 8,760 filas
│
├─ individual_chargers.json (128)
│   + perfil_horario_carga.csv (24h)
│   ↓ [EXPAND 24h→365d] [GENERATE CSVs]
│   → 128 × charger_X.csv (8,760 filas cada uno)
│
├─ bess_results.json
│   ↓ [ASSIGN ALL PARAMS]
│   → electrical_storage con capacity+power+efficiency+soc_limits
│
└─ building_load.csv (8,760 filas...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## PARTE 7: RECOMENDACIONES PRIORIZADAS

### Tier 1: CRÍTICO (Implementar INMEDIATAMENTE)

1. **[1.1] Implementar downsampling solar 15-min → 1-hora**
   - Archivo: `src/iquitos_citylearn/oe3/dataset_builder.py` línea ~450
   - Cambio: Agregar `df_solar_hourly =
     - df_solar.resample('1H')['ac_power_kw'].mean()`
   - Estimado: 30 minutos

2. **[1.2] Generar charger_simulation CSVs para 128 chargers**
   - Archivo: `src/iquitos_citylearn/oe3/dataset_builder.py` línea ~380
   - Cambio: Loop que crea 128 archivos CSV anuales (365 × 24h)
   - Estimado: 1 hora

3. **[1.3] Corregir paths charger_simulation en schema**
   - Archivo: `src/iquitos_citylearn/oe3/dataset_builder.py` línea ~360
   - Cambio: `charger_csv = f"buildings/Mall_Iquitos/{charger_name}.csv"`
   - Estimado: 15 minutos

4. **[1.4] Validar/Corregir capacidad BESS**
   - **Decisión**: ¿4,520 kWh o 2,000 kWh?
   - Si 4,520: actualizar README (dice 2 MWh)
   - Si 2,000: reducir bess_results.json
   - Estimado: 30 minutos (investigación + decisión)

### Tier 2: ALTO (Implementar en esta semana)

1. **[2.1] Integrar building_load en schema**
   - Validar que `building_load.csv` tiene 8,760 filas
   - Asignar correctamente como `non_shiftable_load`
   - Estimado: 45 minutos

2. **[2.2] Expandir charger profiles 24h → 365d con variación**
   - En lugar de simple replicación, agregar ruido (~10%)
   - Hacer más realista para RL
   - Estimado: 1 hora

3. **[2.3] Completar asignación BESS al schema**
   - Agregar: nominal_power, efficiency, min_soc, max_soc
   - Estimado: 30 minutos

4. **[2.4] Investigar annual_datasets/**
   - ¿Contiene timeseries anuales por charger?
   - Si sí: usar como fuente primaria
   - Estimado: 2 horas

### Tier 3: MEDIO (Después de Tier 1-2)

1. **[3.1] Validar observation space (534-dim)**
   - Agregar assert en dataset_builder
   - Comparar con agents config
   - Estimado: 1 hora

2. **[3.2] Documentar reward↔observable mapping**
    - Crear tabla: reward_component → observable_names
    - Estimado: 2 horas

3. **[3.3] Standarizar timezones (UTC-5)**
    - Validar todos timestamps
    - Estimado: 1 hora

4. **[3.4] Validar charger profiles (suma horaria)**
    - Agregar validación en load_oe2_artifacts
    - Estimado: 30 minutos

---

## PARTE 8: CÓDIGO DE CORRECCIONES

Ver archivo: [CORRECCIONES_DATASET_BUILDER.py][ref]

[ref]: file:///d:/diseñopvbesscar/CORRECCIONES_DATASET_BUILDER.py

### Cambios Mínimos (Crítico)

<!-- markdownlint-disable MD013 -->
```python
# En src/iquitos_citylearn/oe3/dataset_builder.py, ~línea 440:

def _load_oe2_artifacts(interim_dir: Path) -> Dict[str, Any]:
    artifacts: Dict[str, Any] = {}
    
    # === SOLAR ===
    solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
    if solar_path.exists():
        df_solar = pd.read_csv(solar_path)
        # ✅ NUEVA CORRECCIÓN: Resample 15-min → 1-hora
        ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

<!-- markdownlint-disable MD013 -->
## PARTE 9: IMPACTO DE NO CORREGIR | Gap | Impacto Sin Corregir | |-----|---------------------| | Resolución solar | Training 4x más... | | Charger CSVs faltantes | CityLearn falla al... | | Paths incorrectos | Schema inválido, environment crash | | BESS capacity mismatch | Energía disponible incorrecta,... | | building_load faltante | non_shiftable_load es cero,... | | annual_datasets no usado | Pierden datos de variación realista | **Resumen**: Sin correcciones Tier 1, **entrenamiento RL es IMPOSIBLE**.

---

## PARTE 10: RESUMEN EJECUTIVO TÉCNICO

### Hallazgos Principales

<!-- markdownlint-disable MD013 -->
```bash
┌─────────────────────────────────────────────────────────────────────┐
│ OE2→OE3 PIPELINE STATUS: PARCIALMENTE ROTO                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ DATOS OE2 DISPONIBLES:              INTEGRIDAD:                     │
│ ├─ Solar (35k filas)         →      ✓...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Próximos Pasos (Orden)

1. ✅ **Realizar auditoría** (COMPLETADO)
2. ⏳ **Corregir Tier 1** (4 cambios, ~2 horas)
3. ⏳ **Testear dataset_builder** (run_oe3_build_dataset)
4. ⏳ **Validar schema** (assert obs_space shape)
5. ⏳ **Reentrenar agentes** (con datos válidos)
6. ⏳ **Comparar resultados** (baseline vs RL con datos correctos)

---

## APÉNDICE: ESTADÍSTICAS FINALES

<!-- markdownlint-disable MD013 -->
```bash
ARCHIVOS ANALIZADOS:
- OE2 total: 537 archivos en data/interim/oe2/
- Solares: 8 archivos
- Chargers: 17 archivos  
- BESS: 3 archivos
- CityLearn prep: 5 archivos

DATOS VALIDADOS:
- Timeseries solar: 35,037 filas × 12 columnas (4.34 MB)
- Chargers individuales: 128 × profiles 24h válidos
- BESS daily balance: 24 horas válidas
- Demanda mall: ~8,760 registros (requiere validación)

ERRORES/GAPS I...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

**Documento generado**: 2026-01-25  
**Auditor**: GitHub Copilot  
**Estado**: ✅ AUDITORÍA COMPLETADA
