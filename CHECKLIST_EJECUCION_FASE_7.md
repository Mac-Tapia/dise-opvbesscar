# CHECKLIST DE EJECUCIÓN: FASE 7 INTEGRATION ✅
Guía Paso a Paso | Marcar ☒ Según Progreso

---

## 📋 FASE 0: VERIFICACIÓN PREVIA

- [ ] **Verificar que bess.py está actualizado**
  - Archivo: `src/dimensionamiento/oe2/disenobess/bess.py`
  - Líneas 986-1209: FASE 1-6 implementadas ✓
  - Comando: `grep -n "FASE 1\|FASE 2\|FASE 3\|FASE 4\|FASE 5\|FASE 6" bess.py`
  - Status: ✅ Validado en FASE 6

- [ ] **Verificar que datos de entrada existen**
  - [ ] `data/iquitos_ev_mall/solar_generation.csv` (8,760 filas)
  - [ ] `data/iquitos_ev_mall/chargers_timeseries.csv` (8,760 filas)  
  - [ ] `data/iquitos_ev_mall/mall_demand.csv` (8,760 filas)
  - Comando: `python -c "import pandas as pd; assert len(pd.read_csv('data/iquitos_ev_mall/solar_generation.csv'))==8760"`

- [ ] **Verificar ambiente Python**
  - [ ] Python 3.10+ instalado
  - [ ] Conda/venv activado
  - [ ] Packages instalados: pandas, numpy, pyyaml, stable-baselines3
  - Comando: `python --version && pip list | grep stable-baselines3`

---

## 📋 FASE 1: EJECUTAR VALIDADOR BESS

**Objetivo:** Ejecutar script que valida 6-FASES y genera dataset normalizado

### PASO 1a: Abrir Terminal
```bash
cd d:\diseñopvbesscar
```
- [ ] Terminal abierta en directorio raíz

### PASO 1b: Ejecutar Validador
```bash
python scripts/validate_bess_6fases.py
```

**Esperado:**
```
═══════════════════════════════════════════════════════════════
BESS SIMULATION CON 6 FASES FIJAS - VALIDACIÓN Y NORMALIZACIÓN
═══════════════════════════════════════════════════════════════

✓ FASE 1: Cargando datos reales...
  ✅ PV data: 8760 filas
  ✅ EV data: 8760 filas
  ✅ MALL data: 8760 filas

✓ FASE 2: Ejecutando simulate_bess_solar_priority()...
  ✅ BESS simulado: 8760 filas, 14 columnas

✓ FASE 3: Validando 6 FASES en datos reales...
  ✅ FASE 1 (6-9 AM): 1095/1095 horas con EV=0
  ✅ FASE 2 (9-22h, SOC<99%): 6855 horas operativas EV
  ✅ FASE 3 (HOLDING): 500 horas con SOC>=99%
  ✅ FASE 4 (Peak Shaving): 200 horas con descarga MALL
  ✅ FASE 5 (EV deficit): 900 horas con descarga EV
  ✅ FASE 6 (22h-9 AM, IDLE): 5410/5410 horas sin acción BESS

✓ FASE 4: Validando integridad de columnas...
  ✅ pv_kwh - Min:      0.00 | Max:   4500.00 | Mean:   1250.50
  ✅ ev_kwh - Min:      0.00 | Max:    500.00 | Mean:    125.75
  ...

✓ FASE 5: Validando restricciones críticas...
  ✅ SOC [20%, 100%]: Violaciones bajo=0, alto=0
  ✅ EV operativo 9-22h, inactivo 22h-9 AM (por definición)
  ✅ PV durante noche (18h-6h): 0 anomalías (esperado ~0)

✓ FASE 6: Normalizando y guardando...
  → Guardando en: data/iquitos_ev_mall/bess_timeseries.csv
  ✅ Guardado: 8760 filas, 12 columnas

RESUMEN FINAL DE VALIDACIÓN:
...
✅ VALIDACIÓN EXITOSA: BESS CON 6 FASES FIJAS LISTO PARA USAR EN BALANCE.PY
═════════════════════════════════════════════════════════════════
```

### PASO 1c: Verificar Output
- [ ] Archivo created: `data/iquitos_ev_mall/bess_timeseries.csv`
  - [ ] Tamaño: ~8,760 filas
  - [ ] Columnas: pv_kwh, ev_kwh, mall_kwh, bess_charge_kwh, bess_discharge_kwh, ...
  - [ ] Sin errores de sintaxis
  - Comando: `head -5 data/iquitos_ev_mall/bess_timeseries.csv`

### PASO 1d: Iniciales de Validación
```bash
# Verificar que archivo se creó
python -c "import pandas as pd; df=pd.read_csv('data/iquitos_ev_mall/bess_timeseries.csv'); print(f'✅ BESS validado: {len(df)} filas, {len(df.columns)} columnas')"
```

- [ ] ✅ Dataset BESS validado

**ESTADO FINAL FASE 1:** ☐ Completada

---

## 📋 FASE 2: EJECUTAR INTEGRADOR BALANCE

**Objetivo:** Sincronizar BESS con balance.py y generar 16 gráficas

### PASO 2a: Ejecutar Integrador
```bash
python scripts/integrate_bess_balance.py
```

**Esperado:**
```
══════════════════════════════════════════════════════════════
INTEGRADOR BESS ↔ BALANCE.PY - 6 FASES COMO FUNDACIÓN FIJA
══════════════════════════════════════════════════════════════

[1/4] Ejecutando validador BESS con 6 FASES...
  [Output completo del validador, como FASE 1]

[2/4] Cargando BESS simulado...
  ✅ BESS cargado: 8760 filas x 14 columnas

  Columnas BESS disponibles:
    • pv_kwh
    • ev_kwh
    • mall_kwh
    • bess_charge_kwh
    • bess_discharge_kwh
    ...

[3/4] Verificando balance.py...
  ✅ balance.py imports OK
  ✅ BalanceEnergeticoConfig creado
     • BESS capacity: 2000 kWh
     • BESS max power: 400 kW
     • 16 gráficas configuradas

[4/4] Sincronizando BESS con balance.py...
  ✅ Sistema integrado

  Generando 16 gráficas con 6-FASES como base...
  ✅ Gráficas generadas en: outputs/balance_energetico/2026-02-19_16h30m/

  Archivos generados: 16
    • 01_energy_timeseries.png
    • 02_soc_trajectory.png
    • 03_power_dispatch.png
    ...

RESUMEN DE INTEGRACIÓN:
...
STATUS: ✅ INTEGRACIÓN EXITOSA - 6 FASES COMO FUNDACIÓN FIJA
```

### PASO 2b: Verificar Outputs
- [ ] Carpeta creada: `outputs/balance_energetico/`
- [ ] Número de gráficas: 16 archivos PNG
  - [ ] 01_energy_timeseries.png
  - [ ] 02_soc_trajectory.png
  - [ ] 03_power_dispatch.png
  - [ ] ... (mínimo 13 más)
  - Comando: `ls outputs/balance_energetico/*.png | wc -l`

### PASO 2c: Revisar Gráficas (Visual Inspection)
- [ ] Abrir `outputs/balance_energetico/01_energy_timeseries.png`
  - Verificar que muestra 8,760 horas
  - PV máximo en horas de día (6-18h)
  - EV máximo en 9-22h
  - MALL presente todo el día

- [ ] Abrir `outputs/balance_energetico/02_soc_trajectory.png`
  - SOC comienza en 20% (FASE 6)
  - SOC sube en FASE 1 (6-9 AM)
  - SOC entre 20%-100% TODO el tiempo

- [ ] Abrir `outputs/balance_energetico/03_power_dispatch.png`
  - BESS carga (FASE 1-2): verde
  - BESS descarga (FASE 4-5): rojo
  - BESS IDLE (FASE 3, FASE 6): línea plana en cero

- [ ] Revisar otras gráficas (al menos 3 adicionales)

**ESTADO FINAL FASE 2:** ☐ Completada

---

## 📋 FASE 3: EJECUTAR FULL PIPELINE

**Objetivo:** Ejecutar simulación completa con baselines y validación

### PASO 3a: Ejecutar Pipeline Completo
```bash
python scripts/run_complete_pipeline.py
```

**Esperado:**
```
═════════════════════════════════════════════════════════════
COMPLETE PIPELINE - BESS SOLAR PRIORITY v5.4
═════════════════════════════════════════════════════════════

[PHASE 1/3] OE2 Dimensioning & Validation...
  ✅ Solar PV: 4050 kWp (8,760 hourly timeseries)
  ✅ BESS: 2000 kWh / 400 kW (95% efficiency)
  ✅ Chargers: 19 units × 2 sockets = 38 total
  ✅ CityLearn v2 environment initialized

[PHASE 2/3] Baseline Comparisons (WITH/WITHOUT SOLAR)...
  
  BASELINE 1: WITH SOLAR (4,050 kWp)
    ✅ CO₂: ~190,000 kg/año
    ✅ Solar self-consumption: ~65%
    ✅ Grid imports: ~40%
    ✅ Output: outputs/baselines/with_solar/baseline_comparison.csv

  BASELINE 2: WITHOUT SOLAR (0 kWp)
    ✅ CO₂: ~640,000 kg/año
    ✅ Solar self-consumption: 0%
    ✅ Grid imports: 100%
    ✅ Output: outputs/baselines/without_solar/baseline_comparison.csv

[PHASE 3/3] Final Validation & Report...
  ✅ All 6 FASES validated in real data
  ✅ Energy balance: ±0.1% error
  ✅ Dataset synchronized: bess_timeseries.csv
  ✅ Report available: outputs/reports/pipeline_report.csv

✅ COMPLETE PIPELINE SUCCESSFUL
═════════════════════════════════════════════════════════════
```

### PASO 3b: Verificar Outputs
- [ ] Baselines generados:
  - [ ] `outputs/baselines/with_solar/baseline_comparison.csv`
  - [ ] `outputs/baselines/without_solar/baseline_comparison.csv`

- [ ] Reporte final:
  - [ ] `outputs/reports/pipeline_report.csv`

- [ ] Dataset persistido:
  - [ ] `data/iquitos_ev_mall/bess_timeseries.csv` (actualizado)

### PASO 3c: Revisar Baselines
```bash
# Comparar CO2 emissions
python -c "
import pandas as pd
with_solar = pd.read_csv('outputs/baselines/with_solar/baseline_comparison.csv')
without_solar = pd.read_csv('outputs/baselines/without_solar/baseline_comparison.csv')

co2_with = with_solar['grid_co2_emissions_kg'].sum()
co2_without = without_solar['grid_co2_emissions_kg'].sum()
diff = co2_without - co2_with

print(f'CO2 WITH SOLAR: {co2_with:,.0f} kg/año')
print(f'CO2 WITHOUT SOLAR: {co2_without:,.0f} kg/año')
print(f'SOLAR IMPACT: {diff:,.0f} kg/año ({100*diff/co2_without:.1f}% reduction)')
"
```

**Esperado:**
```
CO2 WITH SOLAR: 190,000 kg/año
CO2 WITHOUT SOLAR: 640,000 kg/año
SOLAR IMPACT: 450,000 kg/año (70.3% reduction)
```

- [ ] ✅ Baselines comparados exitosamente

**ESTADO FINAL FASE 3:** ☐ Completada

---

## 📋 FASE 4: VALIDACIÓN DETALLADA

**Objetivo:** Audita integridad de 6-FASES en datos reales

### PASO 4a: Verificar FASE 1 (EV=0, 6-9 AM)
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/iquitos_ev_mall/bess_timeseries.csv')
df['hour'] = [i % 24 for i in range(len(df))]
fase1 = df[df['hour'] < 9]
ev_zero_count = (fase1['ev_kwh'] == 0).sum()
print(f'FASE 1 Validation:')
print(f'  Total hours (6-9 AM): {len(fase1)}')
print(f'  Hours with EV=0: {ev_zero_count}')
print(f'  ✅ FASE 1 OK' if ev_zero_count == len(fase1) else f'  ❌ FASE 1 FAILED')
"
```

- [ ] ✅ FASE 1 verificada (EV=0 en todas horas)

### PASO 4b: Verificar FASE 2 (EV máxima, 9-22h)
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/iquitos_ev_mall/bess_timeseries.csv')
df['hour'] = [i % 24 for i in range(len(df))]
fase2 = df[(df['hour'] >= 9) & (df['hour'] < 22)]
ev_positive = (fase2['ev_kwh'] > 0).sum()
print(f'FASE 2 Validation:')
print(f'  Total hours (9-22h): {len(fase2)}')
print(f'  Hours with EV>0: {ev_positive}')
print(f'  ✅ FASE 2 OK' if ev_positive > 0 else f'  ⚠️  Check EV demand')
"
```

- [ ] ✅ FASE 2 verificada (EV activo en 9-22h)

### PASO 4c: Verificar FASE 3 (HOLDING, SOC≥99%)
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/iquitos_ev_mall/bess_timeseries.csv')
fase3 = df[df['soc_percent'] >= 99.0]
holding = ((fase3['bess_charge_kwh'] == 0) & (fase3['bess_discharge_kwh'] == 0)).sum()
print(f'FASE 3 Validation:')
print(f'  Total hours (SOC≥99%): {len(fase3)}')
print(f'  Hours with BESS=0: {holding}')
print(f'  ✅ FASE 3 OK' if holding == len(fase3) else f'  ⚠️  Check HOLDING logic')
"
```

- [ ] ✅ FASE 3 verificada (BESS IDLE cuando SOC≥99%)

### PASO 4d: Verificar FASE 4 (Peak Shaving, MALL>1900)
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/iquitos_ev_mall/bess_timeseries.csv')
peak_shaving = df[df['mall_kwh'] > 1900.0]
descarga = (peak_shaving['bess_to_mall_kwh'] > 0).sum()
print(f'FASE 4 Validation:')
print(f'  Total hours (MALL>1900kW): {len(peak_shaving)}')
print(f'  Hours with BESS→MALL: {descarga}')
print(f'  Peak Shaving ratio: {100*descarga/len(peak_shaving):.1f}%')
print(f'  ✅ FASE 4 OK' if descarga > 0 else f'  ⚠️  Check Peak Shaving')
"
```

- [ ] ✅ FASE 4 verificada (BESS descarga para MALL>1900kW)

### PASO 4e: Verificar FASE 5 (Dual Descarga, EV deficit)
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/iquitos_ev_mall/bess_timeseries.csv')
ev_descarga = df[df['bess_to_ev_kwh'] > 0]
print(f'FASE 5 Validation:')
print(f'  Total hours (BESS→EV): {len(ev_descarga)}')
print(f'  ✅ FASE 5 OK' if len(ev_descarga) > 0 else f'  ⚠️  Check EV deficit logic')
"
```

- [ ] ✅ FASE 5 verificada (Dual descarga activa)

### PASO 4f: Verificar FASE 6 (IDLE, 22h-9AM)
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/iquitos_ev_mall/bess_timeseries.csv')
df['hour'] = [i % 24 for i in range(len(df))]
fase6 = df[(df['hour'] >= 22) | (df['hour'] < 9)]
idle = ((fase6['bess_charge_kwh'] == 0) & (fase6['bess_discharge_kwh'] == 0)).sum()
print(f'FASE 6 Validation:')
print(f'  Total hours (22h-9AM): {len(fase6)}')
print(f'  Hours with BESS=0: {idle}')
print(f'  ✅ FASE 6 OK' if idle == len(fase6) else f'  ⚠️  Check IDLE logic')
"
```

- [ ] ✅ FASE 6 verificada (BESS completamente IDLE en 22h-9AM)

### PASO 4g: Verificar Restricciones Críticas
```bash
python -c "
import pandas as pd
df = pd.read_csv('data/iquitos_ev_mall/bess_timeseries.csv')

# SOC [20%, 100%]
soc_min_violation = (df['soc_percent'] < 20).sum()
soc_max_violation = (df['soc_percent'] > 100).sum()

# Potencia ≤ 400 kW
power_violation = (df['bess_discharge_kwh'] > 400).sum()

print('Restricciones Críticas:')
print(f'  SOC < 20%: {soc_min_violation} violaciones')
print(f'  SOC > 100%: {soc_max_violation} violaciones')
print(f'  Potencia > 400 kW: {power_violation} violaciones')
print(f'  ✅ Todas OK' if (soc_min_violation + soc_max_violation + power_violation) == 0 else '  ❌ Violaciones detectadas')
"
```

- [ ] ✅ Restricciones verificadas

**ESTADO FINAL FASE 4:** ☐ Completada

---

## 📋 FASE 5: DOCUMENTACIÓN REVISAR

**Objetivo:** Verificar que documentación oficial existe y es correcta

- [ ] Archivo exists: `ARQUITECTURA_BESS_6FASES_FUNDACION_FIJA.md`
  - [ ] Declaración de intención (6-FASES son inmutables)
  - [ ] Especificación de cada FASE (condiciones, lógica)
  - [ ] Arquitectura de integración (flujo datos)
  - [ ] Protocolo de validación (por FASE)
  - [ ] Métricas esperadas
  - [ ] Garantías de inmutabilidad
  - [ ] Protocolo de modificación

- [ ] Archivo exists: `RESUMEN_EJECUTIVO_FASE_7_COMPLETADA.md`
  - [ ] Objetivo cumplido
  - [ ] Archivos creados
  - [ ] Arquitectura integrada
  - [ ] Métricas de validación
  - [ ] Próximos pasos

**ESTADO FINAL FASE 5:** ☐ Completada

---

## 📋 FASE 6: ENTRENAR RL AGENTS (PRÓXIMA ETAPA)

**Objetivo:** Entrenar SAC, PPO, A2C con 6-FASES como base

### PASO 6a: Preparar Entrenamiento
```bash
# Crear directorio para checkpoints
mkdir -p checkpoints/{SAC,PPO,A2C}

# Limpiar checkpoints anteriores (si existen)
rm -f checkpoints/SAC/*.zip
rm -f checkpoints/PPO/*.zip
rm -f checkpoints/A2C/*.zip
```

- [ ] ✅ Directorios preparados

### PASO 6b: Entrenar SAC
```bash
python scripts/train_sac_multiobjetivo.py
# Duración: ~5-7 horas (GPU)
```

- [ ] SAC training iniciado
- [ ] Monitor checkpoint: `checkpoints/SAC/`

### PASO 6c: Entrenar PPO
```bash
python scripts/train_ppo_multiobjetivo.py
# Duración: ~4-6 horas (GPU)
```

- [ ] PPO training iniciado
- [ ] Monitor checkpoint: `checkpoints/PPO/`

### PASO 6d: Entrenar A2C
```bash
python scripts/train_a2c_multiobjetivo.py
# Duración: ~3-5 horas (GPU)
```

- [ ] A2C training iniciado
- [ ] Monitor checkpoint: `checkpoints/A2C/`

**ESTADO FINAL FASE 6:** ☐ Completada (cuando RL training termine)

---

## 🎯 ESTADO FINAL DEL CHECKLIST

```
✅ FASE 0: Verificación Previa
  - [ ] bess.py contiene 6-FASES
  - [ ] Datos de entrada existen (8,760 filas cada uno)
  - [ ] Python 3.10+ con packages requeridos

✅ FASE 1: Ejecutar Validador BESS
  - [ ] validate_bess_6fases.py ejecutado
  - [ ] Dataset bess_timeseries.csv generado
  - [ ] Todas 6-FASES validadas

✅ FASE 2: Ejecutar Integrador Balance
  - [ ] integrate_bess_balance.py ejecutado
  - [ ] 16 gráficas generadas
  - [ ] Visualización refleja 6-FASES

✅ FASE 3: Ejecutar Full Pipeline
  - [ ] run_complete_pipeline.py ejecutado
  - [ ] Baselines (con/sin solar) comparados
  - [ ] CO2 savings calculados

✅ FASE 4: Validación Detallada
  - [ ] FASE 1 verificada (EV=0, 6-9 AM)
  - [ ] FASE 2 verificada (EV máxima, 9-22h)
  - [ ] FASE 3 verificada (HOLDING, SOC≥99%)
  - [ ] FASE 4 verificada (Peak Shaving, MALL>1900)
  - [ ] FASE 5 verificada (Dual Descarga, EV deficit)
  - [ ] FASE 6 verificada (IDLE, 22h-9 AM)
  - [ ] Restricciones críticas OK

✅ FASE 5: Documentación
  - [ ] ARQUITECTURA_BESS_6FASES_FUNDACION_FIJA.md revisado
  - [ ] RESUMEN_EJECUTIVO_FASE_7_COMPLETADA.md revisado
  - [ ] Protocolo de inmutabilidad entendido

✅ FASE 6: RL Training (PRÓXIMA ETAPA)
  - [ ] SAC entrenado
  - [ ] PPO entrenado
  - [ ] A2C entrenado
  - [ ] Comparativo de agentes generado
```

---

## 🆘 TROUBLESHOOTING

### Error: "No module named 'src.dimensionamiento.oe2.disenobess.bess'"
**Solución:**
```bash
# Verificar que src/__init__.py existe
ls src/__init__.py

# Si no existe, crear:
touch src/__init__.py
touch src/dimensionamiento/__init__.py
touch src/dimensionamiento/oe2/__init__.py
```

### Error: "FileNotFoundError: data/iquitos_ev_mall/..."
**Solución:**
```bash
# Verificar que archivos existen
ls -la data/iquitos_ev_mall/

# Si no existen, descargar o crear datos de prueba
```

### Error: "KeyError: 'soc_percent'" en validate_bess_6fases.py
**Solución:**
- Verificar que bess.py genera todas las columnas esperadas
- Revisar que simulate_bess_solar_priority() devuelve DataFrame correcto

### Error: OutOfMemory durante training
**Solución:**
- Reducir `n_steps` en configuración
- Reducir `batch_size` en configuración
- Usar CPU en lugar de GPU (más lento pero funciona)

---

## 📞 CONTACTO CON SOPORTE

Si encontras problemas:
1. Revisar la línea de error específica
2. Consultar el archivo `ARQUITECTURA_BESS_6FASES_FUNDACION_FIJA.md`
3. Ejecutar script de diagnóstico si existe
4. Reporte completo incluyendo: error message + comando usado + output

---

**GENERAD:** 2026-02-19
**VERSIÓN:** 1.0 - FASE 7 COMPLETADA

[FIN DEL CHECKLIST]
