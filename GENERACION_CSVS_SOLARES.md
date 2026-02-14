# Generación Automática de Datasets CSV - Energía Solar

## 📋 Resumen de Cambios

Se ha actualizado el archivo `solar_pvlib.py` para agregar funcionalidad de generación automática de **11 archivos CSV** de energía solar cada vez que se ejecuta el script.

**Ubicación:** `data/oe2/Generacionsolar/`

---

## 📊 Datasets Generados

### 1. **Energía Diaria** `pv_daily_energy.csv`
- **Filas:** 365 (un registro por día)
- **Columnas:** datetime, ac_energy_kwh
- **Propósito:** Energía generada cada día del año

### 2. **Energía Mensual** `pv_monthly_energy.csv`
- **Filas:** 12 (un registro por mes)
- **Columnas:** datetime, ac_energy_kwh  
- **Propósito:** Energía generada por mes

### 3. **Perfil Promedio 24h** `pv_profile_24h.csv`
- **Filas:** 24 (una por hora del día)
- **Columnas:** hour, pv_kwh_avg, pv_kwh_per_kwp
- **Propósito:** Energía promedio normalizada por hora

### 4-7. **Días Representativos** (4 archivos)
- `pv_profile_dia_maxima_generacion.csv` - Día con energía máxima (2024-04-23: 26,620 kWh)
- `pv_profile_dia_despejado.csv` - Día despejado/bueno (2024-09-08: 24,500 kWh)
- `pv_profile_dia_intermedio.csv` - Día promedio (2024-07-30: 23,644 kWh)
- `pv_profile_dia_nublado.csv` - Día nublado/malo (2024-12-24: 4,972 kWh)

**Filas por archivo:** 24 (una por hora)
**Columnas:** hora, ghi_wm2, ac_power_kw, ac_energy_kwh, fecha, tipo_dia
**Propósito:** Perfiles horarios para análisis de casos extremos

### 8. **Perfil Horario Mensual** `pv_profile_monthly_hourly.csv`
- **Filas:** 24 (horas del día)
- **Columnas:** hour, mes_01, mes_02, ..., mes_12
- **Propósito:** Variación de generación por hora y mes

### 9. **Módulos Candidatos** `pv_candidates_modules.csv`
- **Filas:** 5 opciones de módulos FV
- **Columnas:** name, pmp_w, area_m2, density_w_m2, n_max, dc_kw_max
- **Propósito:** Catálogo de módulos disponibles para dimensionamiento

### 10. **Inversores Candidatos** `pv_candidates_inverters.csv`
- **Filas:** 5 opciones de inversores
- **Columnas:** name, paco_kw, pdco_kw, efficiency, n_inverters, oversize_ratio, score
- **Propósito:** Catálogo de inversores disponibles

### 11. **Combinaciones Módulo+Inversor** `pv_candidates_combinations.csv`
- **Filas:** 5 combinaciones optimizadas
- **Columnas:** module_name, inverter_name, annual_kwh, energy_per_m2, performance_ratio, score, system_dc_kw, area_modules_m2, modules_per_string, strings_parallel, total_modules, num_inverters
- **Propósito:** Combinaciones recomendadas para análisis de escenarios

---

## 🔧 Implementación Técnica

### Nueva Función: `generate_pv_csv_datasets()`
```python
def generate_pv_csv_datasets(
    dataset_path: Path | str,
    output_dir: Path | str = Path("data/oe2/Generacionsolar")
) -> dict[str, Path]:
    """Genera todos los archivos CSV de generación solar."""
```

**Ubicación en código:** Líneas 2214-2395 de `solar_pvlib.py`

**Características:**
- ✅ Lee el dataset completo de 8,760 registros horarios
- ✅ Calcula energía diaria, mensual y perfiles horarios
- ✅ Identifica días representativos automáticamente
- ✅ Genera catálogos de componentes
- ✅ Crea 11 CSVs listos para usar
- ✅ Valida y verifica creación de archivos
- ✅ Logging completo de operaciones

### Ejecución Automática
El archivo `solar_pvlib.py` ahora ejecuta automáticamente `generate_pv_csv_datasets()` cuando se corre como script principal:

```bash
python src/dimensionamiento/oe2/generacionsolar/disenopvlib/solar_pvlib.py
```

**Flujo de ejecución:**
1. Genera dataset completo con `generate_solar_dataset_citylearn_complete()`
2. Ejecuta validación 7-fase de CityLearn v2
3. Crea directorio `data/oe2/Generacionsolar/` si no existe
4. Genera automáticamente 11 CSVs
5. Valida creación de archivos
6. Imprime resumen completo

---

## ✅ Validación

### Script de Validación: `validate_solar_csvs.py`

Uso:
```bash
python validate_solar_csvs.py
```

**Verifica:**
- ✅ Existencia de cada CSV
- ✅ Estructura de columnas correcta
- ✅ Número mínimo de filas
- ✅ Tamaño de archivos
- ✅ Integridad de datos

**Resultado actual:**
```
✅ VALIDACIÓN COMPLETA - 11/11 CSVs generados correctamente
```

---

## 📐 Especificaciones de Datos

### Dataset Base
- **Período:** Año 2024 completo (365 días × 24 horas = 8,760 registros)
- **Resolución:** Horaria (no 15-minutos)
- **Energía total:** 8,292,514 kWh/año
- **Potencia promedio:** 946.63 kW
- **Reducción CO₂:** 3,749 ton/año (factor 0.4521 kg CO₂/kWh)

### Sistema FV
- **Potencia instalada:** 4,050 kWp
- **Módulos recomendados:** Kyocera Solar KS20 (20.2W, 280.3 W/m²)
- **Inversores recomendados:** Eaton Xpert 1670 (3,201.2 kW AC)
- **Área total:** 20,637 m²
- **Inclinación:** 10° (tumbado)
- **Acimut:** 0° (norte)

### Ubicación (Iquitos, Perú)
- **Latitud:** -3.75°
- **Longitud:** -73.25°
- **Altitud:** 104 m
- **Zona horaria:** America/Lima
- **Irradiancia horizontal media:** Variable (estacional)

---

## 🚀 Uso en Pipelines

### Para CityLearn v2 Training
Los CSVs se pueden usar para:
1. **Análisis de generación:** Cargar `pv_daily_energy.csv` o `pv_profile_24h.csv`
2. **Casos extremos:** Usar archivos de días representativos
3. **Variación estacional:** Analizar con `pv_profile_monthly_hourly.csv`

### Para Dimensionamiento OE2
1. Cargar combinaciones from `pv_candidates_combinations.csv`
2. Validar eficiencia con `pv_candidates_modules.csv` + `pv_candidates_inverters.csv`
3. Calcular costo/beneficio usando energía anual

---

## 📝 Notas de Implementación

### Decisiones de Diseño
- **Generación automática:** Cada ejecución de `solar_pvlib.py` regenera todos los CSVs
- **Días representativos:** Seleccionados automáticamente por percentiles (máx, Q3, mediana, mín)
- **Normalización:** Energía por kWp instalado para comparación relativa
- **Formato:** CSV simple, índices numéricos, separador coma

### Advertencias Registradas
- `UserWarning` al convertir período con timezone (línea 2255) - no afecta resultados
- Puede haber diferencias pequeñas en cálculos si se modifica el dataset base

### Testing
- ✅ Test script: `test_solar_csv_generation.py` (prueba función aislada)
- ✅ Validate script: `validate_solar_csvs.py` (verifica 11 CSVs)
- ✅ Resultado: 11/11 CSVs validados correctamente

---

## 📈 Próximas Mejoras Sugeridas

1. **Histórico de ejecuciones:** Guardar CSVs con timestamp para comparación
2. **Configuración flexible:** Parámetros externos para período, ubicación, componentes
3. **Gráficas automáticas:** Generar visualizaciones PNG junto a CSVs
4. **Base de datos:** Almacenar en SQLite para queries rápidas
5. **Versionado:** Incluir hash/SHA para validar integridad

---

## 📊 Resumen de Archivos

| Archivo | Filas | Columnas | Tamaño | Propósito |
|---------|-------|----------|--------|-----------|
| pv_daily_energy.csv | 365 | 2 | 16 KB | Energía diaria |
| pv_monthly_energy.csv | 12 | 2 | 0.6 KB | Energía mensual |
| pv_profile_24h.csv | 24 | 3 | 0.7 KB | Perfil promedio 24h |
| pv_profile_dia_*_generacion.csv | 24 | 6 | 1.5 KB | Días de máxima/mínima |
| pv_profile_dia_despejado.csv | 24 | 6 | 1.3 KB | Día bueno |
| pv_profile_dia_intermedio.csv | 24 | 6 | 1.3 KB | Día promedio |
| pv_profile_dia_nublado.csv | 24 | 6 | 1.2 KB | Día malo |
| pv_profile_monthly_hourly.csv | 24 | 13 | 3.3 KB | Variación mensual |
| pv_candidates_modules.csv | 5 | 6 | 0.4 KB | Módulos opcionales |
| pv_candidates_inverters.csv | 5 | 7 | 0.5 KB | Inversores opcionales |
| pv_candidates_combinations.csv | 5 | 12 | 0.9 KB | Combinaciones óptimas |

**Total:** ~27 KB de datasets estructurados

---

**Fecha de implementación:** 13 de febrero, 2026  
**Versión:** Solar_PVLib v5.3 + CSV Generator v1.0  
**Estado:** ✅ Producción Lista
