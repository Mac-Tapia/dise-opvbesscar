# GUÍA DE IMPLEMENTACIÓN: CORRECCIONES TIER 1

## 4 Correcciones críticas para desbloquear RL training

---

## CORRECCIÓN #1: Downsampling Solar 15-min → 1-hora

**Archivo**: `src/iquitos_citylearn/oe3/dataset_builder.py`  
**Línea aprox**: ~87 (en `_load_oe2_artifacts`)  
**Tiempo**: 5-10 minutos  
**Impacto**: Soluciona resolución incorrecta

### Paso 1: Localizar código actual

Buscar en `dataset_builder.py`:

```python
# Solar timeseries
solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
if solar_path.exists():
    artifacts["solar_ts"] = pd.read_csv(solar_path)
```bash

### Paso 2: Reemplazar con código mejorado

```python
# === SOLAR TIMESERIES (con resampling) ===
solar_path = interim_dir / "oe2" / "solar" / "pv_generation_timeseries.csv"
if solar_path.exists():
    df_solar = pd.read_csv(solar_path)
    
    # Detectar y resample si es necesario
    if len(df_solar) > 15000:  # Resolución 15-minutos
        logger.info(f"[SOLAR] Detectada resolución 15-min ({len(df_solar)} filas),
            resampling...")
        
        # Preparar datetime index
        if 'timestamp' in df_solar.columns:
            df_solar['timestamp'] = pd.to_datetime(df_solar['timestamp'], utc=True)
            df_solar = df_solar.set_index('timestamp')
        else:
            df_solar.index = pd.date_range(start='2024-01-01', periods=len(df_solar), freq='15min')
        
        # Resample 15-min → 1-hora
        df_solar_hourly = df_solar[['ac_power_kw', 'dc_power_kw']].resample('1H').mean()
        df_solar = df_solar_hourly.reset_index()
        
        logger.info(f"[SOLAR] ✓ Resampling completado: {len(df_solar)} filas (1-hora)")
    else:
        logger.info(f"[SOLAR] Resolución ya es 1-hora ({len(df_solar)} filas)")
    
    artifacts["solar_ts"] = df_solar
```bash

### Validación

```python
# Validar resultado
assert len(artifacts["solar_ts"]) == 8760, f"Solar debe tener 8760 filas, tiene {len(artifacts['solar_ts'])}"
```bash

---

## CORRECCIÓN #2: Generar 128 Charger Simulation CSVs

**Archivo**: `src/iquitos_citylearn/oe3/dataset_builder.py`  
**Línea aprox**: ~550 (después de crear schema y chargers)  
**Tiempo**: 45-60 minutos  
**Impacto**: Soluciona falta de archivos CSV para CityLearn

### Paso 1: Agregar nueva función (antes de `build_citylearn_dataset`)

```python
def _generate_charger_csvs(
    chargers_df: pd.DataFrame,
    profile_24h_path: Path,
    output_dir: Path,
    interim_dir: Path,
) -> int:
    """
    Genera archivos CSV individuales para cada charger (8,760 horas anuales).
    
    Returns:
        Número de CSVs generados
    """
    import numpy as np
    
    building_dir = output_dir / "buildings" / "Mall_Iquitos"
    building_dir.mkdir(parents=True, exist_ok=True)
    
    # Cargar perfil 24h base
    df_profile_24h = pd.read_csv(profile_24h_path)
    
    count_generated = 0
    
    for idx, row in chargers_df.iterrows():
        charger_id = str(row.get("charger_id", f"charger_{idx}"))
        charger_csv = building_dir / f"{charger_id}.csv"
        
        # Crear perfil anual replicando 24h + ruido estocástico
        df_annual = pd.concat([df_profile_24h] * 365, ignore_index=True)
        
        # Agregar ruido (~10% variación) para realismo
        np.random.seed(idx + 42)  # Reproducible pero diferente por charger
        noise = np.random.normal(1.0, 0.1, len(df_annual))
        noise = np.clip(noise, 0.5, 1.5)
        
        # Aplicar ruido a columnas de potencia
        for col in ['power_kw', 'energy_kwh']:
            if col in df_annual.columns:
                df_annual[col] = df_annual[col] * noise
        
        # Validar no negativos
        df_annual = df_annual.clip(lower=0)
        
        # Guardar
        df_annual.to_csv(charger_csv, index=False)
        count_generated += 1
        
        if (idx + 1) % 32 == 0:
            logger.info(f"  [{idx+1}/128] CSVs generados")
    
    logger.info(f"[CHARGERS] ✓ {count_generated} archivos CSV generados en {building_dir}")
    return count_generated
```bash

### Paso 2: Llamar la función en `build_citylearn_dataset`

Buscar la línea donde se crean los chargers (aprox línea 450-500), después de
asignar `all_chargers`al building:

```python
# Después de: b_mall["chargers"] = all_chargers

# === GENERAR CHARGER CSVs ===
chargers_csv_dir = interim_dir / "oe2" / "chargers"
if chargers_csv_dir.exists():
    profile_24h_path = chargers_csv_dir / "perfil_horario_carga.csv"
    if profile_24h_path.exists():
        n_generated = _generate_charger_csvs(
            chargers_df=chargers_df,
            profile_24h_path=profile_24h_path,
            output_dir=out_dir,
            interim_dir=interim_dir,
        )
        if n_generated != 128:
            logger.warning(f"[CHARGERS] Esperaban 128 CSVs,
                se generaron {n_generated}")
```bash

### Validación (2)

```bash
# Después de ejecutar dataset_builder, verificar:
 ls -la outputs/oe3/citylearnv2_dataset/buildings/Mall_Iquitos/ | grep "\.csv$" | wc -l 
# Debería mostrar 128 (más algunos CSVs del schema como solar, building_load, etc.)
```bash

---

## CORRECCIÓN #3: Corregir Charger Simulation Paths

**Archivo**: `src/iquitos_citylearn/oe3/dataset_builder.py`  
**Línea aprox**: ~360 (donde se asigna `charger_simulation`)  
**Tiempo**: 2-5 minutos  
**Impacto**: Schema tendrá paths correctos para CityLearn

### Paso 1: Localizar línea problemática

Buscar:

```python
charger_csv = f"{charger_name}.csv"  # ← INCORRECTO
```bash

### Paso 2: Reemplazar

```python
# ✅ CORRECTO: Path relativo desde raíz del dataset
charger_csv = f"buildings/Mall_Iquitos/{charger_name}.csv"
```bash

Hacer este cambio en TODAS las ocurrencias donde se asigna `charger_simulation`
(buscar con Ctrl+F).

### Ejemplo contexto completo

```python
# Línea ~360-380
for idx, row in chargers_df.iterrows():
    charger_name = str(row.get("charger_id", f"charger_mall_{idx+1}"))
    power_kw = float(row.get("power_kw", 2.0))
    sockets = int(row.get("sockets", 1)) if row.get("sockets", 1) else 1
    
    # ✅ CORRECCIÓN AQUÍ:
    charger_csv = f"buildings/Mall_Iquitos/{charger_name}.csv"  # Path correcto
    
    if charger_template:
        new_charger = json.loads(json.dumps(charger_template))
        new_charger["charger_simulation"] = charger_csv
    else:
        new_charger = {
            "charger_simulation": charger_csv,
            # ... resto de atributos ...
        }
    
    all_chargers[charger_name] = new_charger
```bash

---

## CORRECCIÓN #4: Resolver BESS Capacity Mismatch

**Archivo**: Múltiples (config.yaml, bess_results.json, README.md)  
**Línea aprox**: Varía  
**Tiempo**: 30 minutos (investigación + decisión)  
**Impacto**: Capacidad energética correcta en simulación

### Opción A: Mantener 4,520 kWh (datos actuales)

**Cambios necesarios**:

1. Actualizar `configs/default.yaml`:

```yaml
oe2:
  bess:
    capacity_kwh: 4520.0  # Cambiar de 2000 a 4520
    nominal_power_kw: 2712.0
```bash

1. Actualizar `README.md`:

```markdown
- **BESS**: 4.52 MWh / 2.71 MW (DoD 80%, η 90%)
```bash

1. Actualizar `copilot-instructions.md`:

```markdown
- **BESS**: 4,520 kWh / 2,712 kW
```bash

### Opción B: Reducir a 2,000 kWh (como documenta README)

**Cambios necesarios**:

1. Actualizar `data/interim/oe2/bess/bess_results.json`:

```json
{
  "capacity_kwh": 2000.0,  // Cambiar de 4520
  "nominal_power_kw": 1200.0,  // Ajustar proporcionalmente
  ...
}
```bash

1. Recalcular balance BESS (requiere re-optimización)

### Recomendación

**→ Opción A (mantener 4,520 kWh)** parece ser la decisión implícita del
proyecto
**Justificación**: bess_results.json es el resultado de optimización, más
reciente que README

### En dataset_builder.py, asegurar asignación completa

En función `_update_bess_schema` (búscar aprox línea ~320):

```python
# === BESS CONFIGURATION (CORRECCIÓN COMPLETA) ===
if "bess" in artifacts and "electrical_storage" in building:
    bess_cfg = artifacts["bess"]
    es = building["electrical_storage"]
    
    # Capacidad
    es["capacity"] = float(bess_cfg.get("capacity_kwh", 4520.0))
    es["nominal_power"] = float(bess_cfg.get("nominal_power_kw", 2712.0))
    
    # Atributos
    if "attributes" not in es:
        es["attributes"] = {}
    
    es["attributes"]["capacity"] = es["capacity"]
    es["attributes"]["nominal_power"] = es["nominal_power"]
    es["attributes"]["efficiency"] = float(bess_cfg.get("efficiency_roundtrip", 0.9))
    
    dod = float(bess_cfg.get("dod", 0.8))
    es["attributes"]["depth_of_discharge"] = dod
    es["attributes"]["min_soc"] = 1.0 - dod
    es["attributes"]["max_soc"] = 1.0
    
    logger.info(f"[BESS] ✓ {es['capacity']:.0f} kWh, "
               f"{es['nominal_power']:.0f} kW, "
               f"η={es['attributes']['efficiency']:.1%}")
```bash

---

## VALIDACIÓN DE TODAS LAS CORRECCIONES

Después de aplicar los 4 cambios, ejecutar:

```bash
# 1. Activar virtualenv
.venv\Scripts\Activate.ps1

# 2. Ejecutar dataset_builder corregido
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Resultado esperado:
# [SOLAR] ✓ Resampling completado: 8760 filas (1-hora)
# [CHARGERS] ✓ 128 archivos CSV generados
# [BESS] ✓ 4520 kWh, 2712 kW, η=90%
```bash

### Validación adicional

```python
# Verificar schema
import json
schema = json.load(open('outputs/oe3/citylearnv2_dataset/schema.json'))

# Contar chargers
print(len(schema['buildings']['Mall_Iquitos']['chargers']))  # Debe ser 128

# Verificar un charger tiene path correcto
ch = list(schema['buildings']['Mall_Iquitos']['chargers'].values())[0]
print(ch['charger_simulation'])  # Debe comenzar con "buildings/Mall_Iquitos/"

# Verificar BESS
bess = schema['buildings']['Mall_Iquitos']['electrical_storage']
print(f"BESS: {bess['capacity']} kWh")  # Debe ser 4520
```bash

---

## ORDEN DE IMPLEMENTACIÓN

### Tiempo total: **~2 horas**

```bash
Paso 1: Corrección #1 (Solar downsampling)
        ├─ Búsqueda de código: 5 min
        ├─ Modificación: 10 min
        ├─ Testing: 5 min
        └─ Total: 20 min

Paso 2: Corrección #3 (Path fixing)
        ├─ Búsqueda: 5 min
        ├─ Reemplazo: 5 min
        └─ Total: 10 min

Paso 3: Corrección #4 (BESS config)
        ├─ Decisión: 15 min
        ├─ Actualización archivos: 15 min
        └─ Total: 30 min

Paso 4: Corrección #2 (CSV generation)
        ├─ Agregar función: 20 min
        ├─ Integración: 15 min
        ├─ Testing: 20 min
        └─ Total: 55 min

VALIDACIÓN FINAL: 15 min

TOTAL: ~2 horas 10 minutos
```bash

---

## CHECKLIST DE IMPLEMENTACIÓN

### Pre-implementación

- [ ] Leer esta guía completamente
- [ ] Leer reporte completo: AUDITORIA_EXHAUSTIVA_OE2_OE3_REPORTE_COMPLETO.md
- [ ] Backup de dataset_builder.py
- [ ] Backup de configs/default.yaml

### Correcciones

- [ ] Corrección #1: Downsampling solar
- [ ] Corrección #2: Generar charger CSVs
- [ ] Corrección #3: Paths correctos
- [ ] Corrección #4: BESS config

### Validación (3)

- [ ] Ejecutar dataset_builder sin errores
- [ ] Verificar 128 charger CSVs creados
- [ ] Verificar schema JSON tiene paths correctos
- [ ] Inicializar CityLearnEnv y verificar obs_space

### Post-implementación

- [ ] Guardar cambios en git
- [ ] Documentar cambios (CHANGELOG)
- [ ] Ejecutar agentes RL (training basic)
- [ ] Comparar vs baseline

---

## TROUBLESHOOTING

### Error: "FileNotFoundError: pv_generation_timeseries.csv"

**Causa**: Ruta incompleta  
**Solución**: Verificar interim_dir está correcta en config

### Error: "AssertionError: Solar debe tener 8760 filas"

**Causa**: Resampling no funcionó correctamente  
**Solución**: Revisar que 'timestamp' o index sea datetime

### Error: "No charger CSVs generated"

**Causa**: chargers_df vacío o no existe perfil_horario_carga.csv  
**Solución**: Verificar individual_chargers.json y perfil_horario_carga.csv
existen

### Error: "CityLearn cannot find charger_simulation files"

**Causa**: Paths en schema no coinciden con paths reales de archivos  
**Solución**: Verificar corrección #3 se aplicó correctamente

---

## REFERENCIAS

- Script de auditoría:
  - [AUDITORIA_OE2_OE3_EXHAUSTIVA.py][url1]
- Código de correcciones:
  - [CORRECCIONES_DATASET_BUILDER_TIER1.py][url2]
- Reporte completo:
  - [AUDITORIA_EXHAUSTIVA_OE2_OE3_REPORTE_COMPLETO.md][url3]

---

**Última actualización**: 25 Enero 2026  
**Dificultad**: MEDIA (requiere comprensión del pipeline)  
**Riesgo**: BAJO (cambios aislados y bien documentados)  
**Beneficio**: ALTÍSIMO (desbloquea RL training)


[url1]: file:///d:/diseñopvbesscar/AUDITORIA_OE2_OE3_EXHAUSTIVA.py
[url2]: file:///d:/diseñopvbesscar/CORRECCIONES_DATASET_BUILDER_TIER1.py
[url3]: file:///d:/diseñopvbesscar/AUDITORIA_EXHAUSTIVA_OE2_OE3_REPORTE_COMPLETO.md