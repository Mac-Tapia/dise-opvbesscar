# 🌐 Integración de Datos Climate Zone - Guía Rápida

## ✅ Cambios Realizados

Se han integrado tres archivos CSV de datos climate zone en el constructor de dataset de CityLearn v2:

### 1. **Archivos Agregados**
- `src/citylearnv2/climate_zone/carbon_intensity.csv` - Intensidad de carbono del grid (kg CO₂/kWh)
- `src/citylearnv2/climate_zone/pricing.csv` - Precios de electricidad (USD/kWh)
- `src/citylearnv2/climate_zone/weather.csv` - Datos meteorológicos (temperatura, humedad, viento, radiación)

### 2. **Métodos Agregados en OE2DataLoader**

```python
class OE2DataLoader:
    def load_carbon_intensity() -> Optional[pd.DataFrame]
    def load_pricing() -> Optional[pd.DataFrame]
    def load_weather() -> Optional[pd.DataFrame]
```

**Ubicación**: `src/citylearnv2/dataset_builder/dataset_builder_consolidated.py` (líneas 336-425)

### 3. **Integración en build_citylearn_dataset()**

**STEP 2**: Ahora carga los tres nuevos conjuntos de datos:
```python
artifacts["carbon_intensity"] = loader.load_carbon_intensity()
artifacts["pricing"] = loader.load_pricing()
artifacts["weather"] = loader.load_weather()
```

**STEP 5**: Schema.json ahora incluye referencias a:
```json
{
  "electricity_pricing": "electricity_pricing.csv",
  "weather": "weather.csv"
}
```

**STEP 6B (NUEVO)**: Genera los tres archivos CSV en el directorio del building:
```python
_generate_climate_csvs(artifacts, building_dir, overwrite=overwrite)
```

### 4. **Nueva Función Helper**

```python
def _generate_climate_csvs(
    artifacts: Dict[str, Any],
    building_dir: Path,
    overwrite: bool = False,
) -> None:
```

**Ubicación**: `src/citylearnv2/dataset_builder/dataset_builder_consolidated.py` (líneas 752-798)

---

## 🧪 Validación

### Test 1: Verificar que los archivos CSV existen
```bash
python test_climate_integration.py
```

✅ Comprobará:
- CSV files exist
- Row counts (8,760)
- Column presence
- Loader methods implemented
- Schema fields included

### Test 2: Ejecutar construcción completa del dataset
```bash
python -m src.citylearnv2.dataset_builder.dataset_builder_consolidated
```

✅ Generará:
- `processed_data/Iquitos_EV_Mall/schema.json`
- `processed_data/Iquitos_EV_Mall/charger_simulation_*.csv` (128 files)
- `processed_data/Iquitos_EV_Mall/carbon_intensity.csv`
- `processed_data/Iquitos_EV_Mall/electricity_pricing.csv`
- `processed_data/Iquitos_EV_Mall/weather.csv`

---

## 📋 Estructura de Datos

### carbon_intensity.csv
| time | carbon_intensity |
|------|-----------------|
| 2024-01-01 00:00:00 | 0.4521 |
| 2024-01-01 01:00:00 | 0.4521 |
| ... | ... |
| 2024-12-31 23:00:00 | 0.4521 |

**Filas**: 8,762 (8,760 datos + 1 header + 1 blanco)
**Significado**: kg CO₂ por kWh generado en el grid de Iquitos (térmica)

### pricing.csv
| time | electricity_pricing |
|------|-------------------|
| 2024-01-01 00:00:00 | 0.2 |
| 2024-01-01 01:00:00 | 0.2 |
| ... | ... |
| 2024-12-31 23:00:00 | 0.2 |

**Filas**: 8,762 (8,760 datos + 1 header + 1 blanco)
**Significado**: USD por kWh de tarifa de electricidad

### weather.csv
| time | dry_bulb_temperature | relative_humidity | wind_speed | direct_normal_irradiance | diffuse_horizontal_irradiance |
|------|---------------------|-----------------|-----------|------------------------|-------------------------------|
| 2024-01-01 00:00:00 | 23.5 | 85 | 1.2 | 0 | 0 |
| 2024-01-01 01:00:00 | 23.2 | 87 | 1.1 | 0 | 0 |
| ... | ... | ... | ... | ... | ... |

**Filas**: 8,762 (8,760 datos + 1 header + 1 blanco)
**Significado**: Datos meteorológicos reales para ubicación de Iquitos

---

## 🔧 Troubleshooting

### Problema: "Carbon intensity not found"
**Solución**: Verificar que `src/citylearnv2/climate_zone/carbon_intensity.csv` existe
```bash
ls -la src/citylearnv2/climate_zone/
```

### Problema: "Insufficient rows" (< 8,760)
**Solución**: Asegurar que cada CSV tiene exactamente 8,760 filas de datos
```bash
wc -l src/citylearnv2/climate_zone/*.csv
```

### Problema: Schema.json no incluye campos weather/pricing
**Solución**: Ejecutar con la versión actualizada del código (pull latest)
```bash
git status
git pull origin oe3-optimization-sac-ppo
```

---

## 📝 Cambios de Código - Resumen

| Componente | Cambios | Líneas |
|-----------|---------|--------|
| **OE2DataLoader** | +3 métodos (load_carbon_intensity, load_pricing, load_weather) | 336-425 |
| **build_citylearn_dataset()** | +5 llamadas a nuevos loaders en STEP 2 | 514-518 |
| **_build_schema()** | +2 campos en schema.json (electricity_pricing, weather) | 666-667 |
| **_generate_climate_csvs()** | Nueva función helper para generar CSVs | 752-798 |
| **build_citylearn_dataset()** | +STEP 6B para generar climate CSVs | 585-594 |

**Total**: ~150 líneas nuevas de código, 0 errores de Pyright ✅

---

## ✨ Características

✅ **Carga automática** de tres archivos CSV climate zone  
✅ **Generación de schema.json** con referencias a climate data  
✅ **Generación de CSVs** en output directory para CityLearn  
✅ **Manejo de errores** robusto con fallbacks a valores por defecto  
✅ **Type hints** completos - 0 errores Pyright  
✅ **Logging detallado** de cada paso del proceso  
✅ **Validación** de row counts (8,760) y columnas  

---

## 🚀 Próximos Pasos

1. **Ejecutar test de integración**:
   ```bash
   python test_climate_integration.py
   ```

2. **Ejecutar construcción completa**:
   ```bash
   python -c "from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset; build_citylearn_dataset()"
   ```

3. **Verificar archivos generados**:
   ```bash
   ls -la processed_data/Iquitos_EV_Mall/
   ```

4. **Validar schema.json**:
   ```bash
   cat processed_data/Iquitos_EV_Mall/schema.json | grep -E "electricity_pricing|weather"
   ```

---

## 📊 Estado de la Integración

| Componente | Estado | Nota |
|-----------|--------|------|
| CSV files exist | ✅ | 3/3 archivos presentes |
| Loaders implemented | ✅ | load_carbon_intensity, load_pricing, load_weather |
| STEP 2 integration | ✅ | Archivos cargados en artifacts dict |
| Schema generation | ✅ | Campos electricity_pricing y weather en schema.json |
| CSV generation | ✅ | Función _generate_climate_csvs() implementada |
| Pyright validation | ✅ | 0 errores (después de int() casts) |
| Testing | ⏳ | test_climate_integration.py listo |

---

**Última actualización**: 2026-02-04  
**Status**: 🟢 LISTO PARA TESTING  
**Autor**: GitHub Copilot  
**Rama**: oe3-optimization-sac-ppo
