# Análisis de Generación Solar - Iquitos 2024

Script principal para consultas y análisis detallados de generación solar fotovoltaica para el proyecto OE2-OE3 de Iquitos.

## 📋 Contenido

```
src/dimensionamiento/oe2/generacionsolar/run/
├── main.py              ← Script principal de análisis
├── utils.py             ← Utilidades y funciones helper
└── README.md            ← Este archivo
```

## 🚀 Uso Rápido

### 1. Generar datos de generación solar (primero)
```bash
cd d:\diseñopvbesscar
python run_solar_generation_hourly.py
```

Este script descarga datos TMY de PVGIS y simula la generación solar hora a hora para todo el año 2024.

**Salida:**
- `data/oe2/Generacionsolar/pv_generation_timeseries.csv` - Datos horarios (8,760 registros)
- `data/oe2/Generacionsolar/estadisticas_generacion.txt` - Resumen estadístico
- `data/oe2/Generacionsolar/solar_technical_report.md` - Reporte técnico

### 2. Ejecutar análisis y consultas
```bash
cd d:\diseñopvbesscar
python src/dimensionamiento/oe2/generacionsolar/run/main.py
```

Genera análisis completo con:
- Resumen anual
- Estadísticas mensuales
- Análisis de días representativos
- Análisis detallado de temperatura, irradiancia y potencia
- Gráficas en alta resolución

**Salida:**
- Consola: Reporte detallado
- `data/oe2/Generacionsolar/graficas/` - 8 gráficas PNG

### 3. Usar utilidades en tu código
```python
from src.dimensionamiento.oe2.generacionsolar.run.utils import *

# Cargar datos
df = cargar_generacion_solar()

# Consultas rápidas
energia_anual = energia_total_anual(df)
potencia_max = potencia_maxima(df)
temp_promedio = temperatura_promedio(df)

# Días representativos
fecha_despejado, energia_despejado = dia_mas_despejado(df)
fecha_nublado, energia_nublado = dia_mas_nublado(df)
fecha_templado, energia_templado = dia_templado(df)

# Perfil de un día específico
perfil = perfil_horario(df, pd.Timestamp('2024-03-21'))

# Exportar resumen
resumen = exportar_resumen_json(df)
```

## 📊 Análisis Disponibles

### Resumen Anual
- **Energía generada**: kWh, MWh, GWh
- **Potencia**: promedio, máxima, mínima
- **Temperatura**: promedio, máxima, mínima
- **Irradiancia**: promedio, máxima

### Resumen Mensual
Tabla con datos para cada mes:
- Energía generada (kWh)
- Potencia promedio y máxima (kW)
- Temperatura promedio (°C)
- Irradiancia promedio (W/m²)
- Número de días

### Días Representativos
- **Día más despejado**: Máxima generación (día despejado)
- **Día más nublado**: Mínima generación (día nublado)
- **Día templado**: Energía cercana a la mediana

Para cada día se muestra:
- Fecha y energía generada
- Potencia máxima
- Temperatura promedio
- Irradiancia máxima

### Análisis Detallados
- **Temperatura**: promedio, mediana, máx, mín, desviación estándar, percentiles
- **Irradiancia**: promedio, mediana, máx, mín, desviación estándar, percentiles
- **Potencia AC**: promedio, mediana, máx, mín, desviación estándar, percentiles

## 📈 Gráficas Generadas

| Archivo | Descripción |
|---------|-------------|
| `energia_mensual.png` | Energía generada por mes (barras) |
| `energia_diaria.png` | Serie temporal de energía diaria con promedio |
| `perfil_horario.png` | Perfil promedio de potencia hora por hora |
| `temperatura_mensual.png` | Temperatura promedio por mes (línea) |
| `irradiancia_mensual.png` | Irradiancia global por mes (barras) |
| `distribucion_potencia.png` | Histograma de distribución de potencia |
| `series_temporales_mensual.png` | 12 gráficas (una por mes) de series temporales horarias |
| `correlacion_temperatura_potencia.png` | Correlación entre temperatura y potencia con tendencia |

## 📁 Estructura de Datos

### CSV Principal: `pv_generation_timeseries.csv`

Columnas:
| Columna | Tipo | Descripción |
|---------|------|-------------|
| `timestamp` | datetime | Fecha y hora (2024-01-01 00:00 a 2024-12-31 23:00) |
| `ghi_wm2` | float | Irradiancia Global Horizontal (W/m²) |
| `dni_wm2` | float | Irradiancia Normal Directa (W/m²) |
| `dhi_wm2` | float | Irradiancia Difusa Horizontal (W/m²) |
| `temp_air_c` | float | Temperatura del aire (°C) |
| `wind_speed_ms` | float | Velocidad del viento (m/s) |
| `dc_power_kw` | float | Potencia DC (kW) |
| `ac_power_kw` | float | **Potencia AC / Salida (kW)** ✅ |
| `dc_energy_kwh` | float | Energía DC por hora (kWh) |
| `ac_energy_kwh` | float | **Energía AC por hora (kWh)** ✅ |

### Parámetros del Sistema

```
Ubicación:      Iquitos, Perú
Latitud:        -3.75°
Longitud:       -73.25°
Altitud:        104 m
Zona horaria:   America/Lima (UTC-5)

Módulo FV:      Kyocera KS20 (20.2W)
Inversor:       Eaton Xpert1670 (3,201.2 kW)
Capacidad DC:   4,162 kWp
Capacidad AC:   3,201 kW
```

## 📊 Resultados Esperados

### Energía Anual
- **Total**: ~8,080,000 kWh (8.08 GWh)
- **Promedio diario**: ~22,134 kWh/día

### Potencia
- **Promedio**: ~923 kW
- **Máxima**: ~3,900 kW
- **Mínima**: ~0 kW

### Clima
- **Temperatura promedio**: ~26.5 °C
- **Rango**: 20-32 °C
- **Irradiancia promedio**: ~140-160 W/m²

## 🔍 Opciones de Línea de Comandos

```bash
python main.py [opciones]

Opciones:
  --show-plots          Mostrar gráficas interactivas (default: solo guardar)
  --output-dir DIR      Directorio para guardar gráficas
                       (default: data/oe2/Generacionsolar/graficas)
  --csv-path PATH       Ruta al CSV de generación solar
                       (default: data/oe2/Generacionsolar/pv_generation_timeseries.csv)
```

### Ejemplos
```bash
# Análisis completo con gráficas interactivas
python src/dimensionamiento/oe2/generacionsolar/run/main.py --show-plots

# Usar CSV personalizado
python src/dimensionamiento/oe2/generacionsolar/run/main.py --csv-path mi_archivo.csv

# Guardar gráficas en directorio específico
python src/dimensionamiento/oe2/generacionsolar/run/main.py --output-dir mi_carpeta/graficas
```

## 🛠️ Requisitos

```
pandas>=1.3.0
numpy>=1.20.0
matplotlib>=3.3.0  (opcional, para gráficas)
pvlib>=0.9.0       (para generación solar)
```

Instalar:
```bash
pip install -r requirements.txt
```

## 📝 Notas Importantes

1. **Los datos se generan con 8,760 registros horarios** (365 días × 24 horas)
2. **Resolución**: 1 hora (no 15 minutos) para compatibilidad con CityLearn
3. **Período**: Año completo 2024 (enero a diciembre)
4. **Precisión**: Datos descargados desde PVGIS (satélite Copernicus)
5. **Temperatura**: Incluye variación diaria y mensual realista

## 🎯 Integración con CityLearn

Los datos generados están optimizados para ser usados en:
- `src/iquitos_citylearn/oe3/dataset_builder.py`
- Observables: 394-dimensionales (incluye generación solar)
- Timesteps: 8,760 (año completo)

Cargar en CityLearn:
```python
from pathlib import Path
import pandas as pd

solar_csv = Path('data/oe2/Generacionsolar/pv_generation_timeseries.csv')
df_solar = pd.read_csv(solar_csv)

# Usar en dataset_builder.py
# df_solar['ac_power_kw'] → Potencia disponible cada hora
# df_solar['ac_energy_kwh'] → Energía disponible cada hora
```

## 📞 Soporte

Para problemas:
1. Verificar que `pv_generation_timeseries.csv` existe
2. Ejecutar primero `run_solar_generation_hourly.py`
3. Revisar logs en la consola para mensajes de error
4. Verificar que matplotlib está instalado (para gráficas)

## 📜 Licencia

Proyecto: OE2-OE3 Iquitos  
Año: 2024  
Entidad: Diseño PV-BESS-CAR
