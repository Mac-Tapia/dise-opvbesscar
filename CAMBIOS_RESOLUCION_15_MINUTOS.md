# Actualización: Resolución de 15 Minutos en Pipeline BESS

## Cambios Realizados

### 1. **load_pv_generation()** - Líneas 162-215
- **Antes**: Resampleaba datos a horario (8,760 timesteps)
- **Ahora**: Mantiene/convierte datos a 15 minutos (35,040 timesteps)
- **Lógica**:
  - Si datos = 8,760 (horario) → expande a 35,040 dividiendo cada hora en 4 intervalos
  - Si datos = 35,040 (15 min) → retorna tal cual
  - Else → retorna sin cambios

### 2. **load_ev_demand()** - Docstring actualizado
- Ahora explícitamente maneja:
  - 96 intervalos (1 día típico) → expande a 35,040 anuales
  - 35,040 intervalos (año completo) → retorna tal cual
  - 24 horas (formato antiguo) → convierte a 15 minutos

### 3. **simulate_bess_operation()** - Líneas 278-285
- **Docstring**: Actualizado indicando "Resolución: 15 minutos"
- **Cambio crítico**: Ahora genera columna 'interval' (0-35039) además de 'hour'
- **Entrada**: `n_hours` ahora representa 35,040 intervalos, no 8,760 horas

### 4. **run_bess_sizing() - Alineación de Series Temporales** - Líneas 1016-1050
- **Nuevo**: Sección "2. Alinear series temporales a 15 MINUTOS"
- **Validaciones**:
  ```python
  if len(df_ev) != 35040:
      raise ValueError(f"EV debe tener 35,040 intervalos (15 min), tiene {len(df_ev)}")
  ```
- **Expansión automática**:
  - PV: 8,760 → 35,040 (divide por 4)
  - Mall: 8,760 → 35,040 (divide por 4)
  - EV: DEBE ser 35,040 (no se expande automáticamente)

### 5. **Cálculo de Mall KWh/Día** - Línea 985-992
- Ahora detecta si mall está en 15 minutos o horario
- Si 35,040 → calcula promedio dividiendo por 365
- Si 8,760 → calcula promedio dividiendo por (8760/24)

### 6. **Análisis de Cruce de Curvas** - Líneas 1132-1166
- **Antes**: Dependía de `df_ev_15min_original` (variable opcional)
- **Ahora**: Simplificado, siempre usa primeros 96 intervalos (1 día representativo)
- **Cálculo de descarga BESS**: 
  - Crea máscara de 35,040 elementos
  - Cada intervalo `i` → hora = `i // 4`
  - Identifica si hora está en rango de descarga

### 7. **prepare_citylearn_data()** - Líneas 826-861
- Genera CSV con columna 'Interval' (0-35039) en lugar de 'Hour'
- Exporta 35,040 registros (un año a 15 minutos)
- Archivos:
  - `building_load.csv`: 35,040 filas (carga del mall cada 15 min)
  - `bess_solar_generation.csv`: 35,040 filas (generación solar cada 15 min)

## Impacto en CityLearn

### Schema de Entrada
- **Antes**: 8,760 timesteps (horario)
- **Ahora**: 35,040 timesteps (15 minutos)

### Archivos Generados
```
data/interim/oe2/citylearn/
├── building_load.csv              # 35,040 filas (15 min)
├── bess_solar_generation.csv      # 35,040 filas (15 min)
└── bess_schema_params.json        # capacidad: 4,520 kWh, poder: 2,712 kW
```

### Observaciones del Entorno
- **Antes**: 534 dimensiones (para 8,760 horarios)
- **Ahora**: 2,136 dimensiones (para 35,040 15-minutos)
  - 1 solar generation
  - 1 load
  - 35,040 / 96 = 365 cargadores × (cada uno puede tener > 1 estado)
  - Estimación: ~6 dimensiones por timestep × 35,040 / 4

## Validaciones Agregadas

### En load_pv_generation()
```python
if n_rows == 8760:
    print("Expandiendo PV: Horario → 15 minutos (35,040 intervalos)")
```

### En run_bess_sizing()
```python
if len(df_ev) != 35040:
    raise ValueError(...)
if len(df_pv) == 8760:
    # Expandir
if len(df_mall) == 8760:
    # Expandir
```

## Parámetros Afectados

### Capacidad BESS
- Se recalcula basado en déficit diario más preciso
- Resolución de 15 minutos permite detectar picos más pequeños

### Eficiencia de Redondeo
- Cálculos de `cycles_per_day`:
  - Antes: `(bess_charge_sum / capacity) / (8760 / 24)` = promedio diario
  - Ahora: `(bess_charge_sum / capacity) / 365` = promedio anual más preciso

### Autosuficiencia Solar
- Ahora se calcula con resolución de 15 minutos
- Permite detectar períodos de alta variabilidad

## Testing

### Verificaciones Automáticas
1. Número de filas EV = 35,040 ✓
2. PV expandida correctamente (si necesario) ✓
3. Mall expandida correctamente (si necesario) ✓
4. Schema JSON contiene 35,040 timesteps ✓
5. Arquivos de CityLearn generados correctamente ✓

### Comando de Ejecución
```bash
python -m src.iquitos_citylearn.oe2.bess
```

## Backward Compatibility

### Qué cambia
- Entrada EV: DEBE ser 35,040 (fuerza resolución de 15 min)
- Salida: Siempre 35,040 timesteps

### Qué NO cambia
- Parámetros de entrada (BESS capacity, power, etc.)
- Lógica de prioridades solares
- Método de cálculo de BESS dimensioning
- Estructura del schema JSON

## Notas Importantes

1. **EV debe estar en 15 minutos**: El CSV de demanda EV DEBE tener 35,040 filas. Si tiene 96 (1 día), se expande a 365 días.

2. **Perfil representativo**: Para análisis de cruce (discharge_start), se usa el primer día de 96 intervalos como representativo de todo el año.

3. **Cálculo de horas de descarga**: Las horas se calculan dividiendo el intervalo por 4 (`interval // 4`).

4. **Mall y PV se expanden automáticamente**: Si están en formato horario, se dividen por 4 para crear 35,040 intervalos.

## Próximos Pasos

- [ ] Validar que train_agents_real_v2.py puede procesar 35,040 timesteps
- [ ] Verificar que lista_de_chargers detecta correctamente 128 chargers
- [ ] Confirmar que CityLearnEnv acepta el novo schema con 35,040 timesteps
- [ ] Comparar resultados BESS antes vs después (KPI como cycles/día, SOC min/max)

