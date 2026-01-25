# Actualización Completa: Resolución de 15 Minutos

## Estado Actual

### Cambios Implementados ✓

1. **load_pv_generation()** - Genera datos a 15 minutos
   - Expandir 8,760 horas → 35,040 intervalos (÷4 cada hora)
   - Mantener 35,040 si ya está en 15 minutos
   
2. **load_ev_demand()** - Soporta 15 minutos
   - 96 intervalos/día → expande a 35,040 anuales
   - 35,040 intervalos → retorna tal cual
   - 24 horas → convierte a 35,040 (cada hora ÷4)

3. **simulate_bess_operation()** - Simula a 15 minutos
   - Entrada: 35,040 datos de PV, EV, Mall
   - Salida: DataFrame con columna 'interval' (0-35039)
   - Resolución: 15 minutos garantizada

4. **run_bess_sizing()** - Alineación automática
   - EV: DEBE ser 35,040 (error si no)
   - PV: Expande 8,760 → 35,040 automáticamente
   - Mall: Expande 8,760 → 35,040 automáticamente
   - Análisis de cruce usa primeros 96 intervalos (1 día)

5. **prepare_citylearn_data()** - Exporta a 15 minutos
   - building_load.csv: 35,040 filas (Interval, non_shiftable_load)
   - bess_solar_generation.csv: 35,040 filas (Interval, solar_generation)
   - bess_schema_params.json: BESS 4,520 kWh, 2,712 kW

### Archivos Generados

```
data/interim/oe2/citylearn/
├── building_load.csv              35,040 filas (15 min)
├── bess_solar_generation.csv      35,040 filas (15 min)
└── bess_schema_params.json        BESS schema con parametros
```

### Próximos Pasos Necesarios

⚠️ **IMPORTANTE**: El dataset_builder.py aún genera charger_simulation_*.csv con 8,760 filas (horario). Necesita actualización para generar 35,040 filas.

```python
# Actual:
charger_simulation_001.csv: 8,760 filas (horario)

# Esperado:
charger_simulation_001.csv: 35,040 filas (15 minutos)
```

### Impacto en CityLearn

**Antes**: 8,760 timesteps (horario)
**Ahora**: 35,040 timesteps (15 minutos)

**Consecuencias**:
- Observation space: ~4x más grande
- Resolución temporal: 4x mejor
- Detección de picos: Más precisa
- Training: Más episodios requeridos (más datos)

### Cómo Completar la Actualización

**Ubicación**: [src/iquitos_citylearn/oe3/dataset_builder.py](src/iquitos_citylearn/oe3/dataset_builder.py)

**Cambio necesario** (alrededor de línea 540):
```python
# Actual: Lee CSVs de 8,760 horas
for charger in chargers:
    df = pd.read_csv(...)  # 8,760 filas

# Requerido: Expandir a 35,040 intervalos (15 minutos)
for charger in chargers:
    df = pd.read_csv(...)  # 8,760 filas
    df_expanded = []
    for _, row in df.iterrows():
        value = row['Power'] / 4  # Dividir entre 4
        for _ in range(4):
            df_expanded.append({'Power': value})
    df_15min = pd.DataFrame(df_expanded)
```

### Validación

Para verificar que bess.py genera datos correctamente:
```bash
python -c "
from pathlib import Path
from src.iquitos_citylearn.oe2.bess import run_bess_sizing
result = run_bess_sizing(...)
df = result['bess_output']
assert len(df) == 35040  # Debe ser verdadero
"
```

Para verificar que dataset_builder.py genera datos correctamente:
```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
# Verificar: charger_simulation_001.csv debe tener 35,040 filas
```

---

## Resumen de Cambios en bess.py

| Función | Cambio | Estado |
|---------|--------|--------|
| load_pv_generation() | Expande 8,760 → 35,040 | ✓ Hecho |
| load_ev_demand() | Expande/mantiene 35,040 | ✓ Hecho |
| load_mall_demand_real() | (sin cambios) | - |
| simulate_bess_operation() | Simula 35,040 intervalos | ✓ Hecho |
| run_bess_sizing() | Alinea a 35,040 | ✓ Hecho |
| prepare_citylearn_data() | Exporta 35,040 CSV | ✓ Hecho |

---

## Testing Realizado

✓ load_pv_generation() genera 35,040 intervalos
✓ load_ev_demand() soporta 35,040 intervalos
✓ Alineación automática funciona (PV, Mall expandidas)
✓ Análisis de cruce usa 15 minutos correctamente
✓ CSV de CityLearn generados con 35,040 filas
✓ Schema JSON contiene BESS params correctamente

❌ dataset_builder.py aún genera chargers con 8,760 (PENDIENTE)
❌ train_agents_real_v2.py aún espera 8,760 obs (PENDIENTE)

---

## Notas Técnicas

1. **Cálculos diarios**: Se dividen por 365 (no 8760/24)
   ```python
   # Antes: value / (8760 / 24) = value / 365
   # Ahora: value / 365  (mismo resultado)
   ```

2. **Descarga BESS**: Se calcula correctamente a partir de 35,040 datos
   - Máscara de descarga creada como array de 35,040
   - Cada intervalo `i` → hora = `i // 4`

3. **Picos y promedios**: Más precisos con 15 minutos
   - Permite detectar variabilidad intra-horaria
   - Mejora estimación de capacidad BESS

4. **Backward compatibility**: 
   - EV DEBE ser 35,040 (fuerza nueva resolución)
   - PV y Mall se adaptan automáticamente
   - Schema XML compatible

---

## Comando para Completar la Actualización

Una vez que dataset_builder.py sea actualizado:
```bash
python scripts/run_full_pipeline.py
```

Esto ejecutará:
1. ✓ BESS dimensioning (35,040)
2. ? Dataset generation (35,040) - PENDIENTE
3. ? Baseline (35,040) - PENDIENTE
4. ? Training (35,040) - PENDIENTE
5. ? Comparison - PENDIENTE

---

**Fecha de completado**: 2026-01-25
**Próxima tarea**: Actualizar dataset_builder.py y train_agents_real_v2.py
