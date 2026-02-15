# Rutas de Datos Fijas - Dataset Builder CityLearn v5.7

**Actualizado**: 14 de febrero de 2026

## 📍 Rutas Primarias (Source of Truth - OE2)

Estos archivos son **OBLIGATORIOS** y permanentes en el sistema de construcción de datasets:

### 1. **Solar - Generación PV Horaria**
```
data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
```
- **Descripción**: Timeseries horaria de generación solar PV 2024
- **Información requerida**: 8,760 filas (1 año × 24 horas)
- **Formato**: CSV con índice datetime
- **Usado en**: 
  - `data_loader.py` → `DEFAULT_SOLAR_PATH`
  - `integrate_datasets.py` → parámetro `solar_path`
  - `main_build_citylearn.py` → carga automática

---

### 2. **BESS - Almacenamiento de Energía**
```
data/oe2/bess/bess_ano_2024.csv
```
- **Descripción**: Datos horarios de carga/descarga del sistema de almacenamiento
- **Capacidad**: 1,700 kWh (max SOC)
- **Datos**: 8,760 filas (1 año)
- **Formato**: CSV con índice datetime
- **Usado en**:
  - `data_loader.py` → `DEFAULT_BESS_PATH`
  - `integrate_datasets.py` → parámetro `bess_path`
  - `main_build_citylearn.py` → carga automática

---

### 3. **Chargers - Cargadores EV**
```
data/oe2/chargers/chargers_ev_ano_2024_v3.csv
```
- **Descripción**: Datos de operación de 19 cargadores × 2 sockets = 38 conectables
- **Especificaciones**:
  - 19 cargadores Mode 3 @ 7.4 kW (32A @ 230V)
  - 38 sockets controlables
  - Demanda: 270 motos + 39 mototaxis/día
- **Datos**: 8,760 filas (1 año)
- **Formato**: CSV con índice datetime
- **Usado en**:
  - `data_loader.py` → `DEFAULT_CHARGERS_PATH`
  - `enrich_chargers.py` → parámetro `chargers_path`
  - `integrate_datasets.py` → parámetro `chargers_path`
  - `main_build_citylearn.py` → carga automática

---

### 4. **Demanda Mall - Consumo No-Desplazable**
```
data/oe2/demandamallkwh/demandamallhorakwh.csv
```
- **Descripción**: Timeseries de demanda horaria del centro comercial
- **Demanda base**: ~100 kW promedio
- **Datos**: 8,760 filas (1 año)
- **Formato**: CSV
- **Usado en**:
  - `data_loader.py` → `DEFAULT_MALL_DEMAND_PATH`
  - `load_mall_demand_data()` → carga automática
  - CityLearn environment → observación/acción

---

## 🔧 Cómo Están Integradas en el Código

### En `data_loader.py` (líneas 59-62)
```python
# Primary data sources (OE2 - source of truth - FIXED PATHS v5.7)
DEFAULT_SOLAR_PATH = Path("data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv")
DEFAULT_BESS_PATH = Path("data/oe2/bess/bess_ano_2024.csv")
DEFAULT_CHARGERS_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
DEFAULT_MALL_DEMAND_PATH = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
```

### En `integrate_datasets.py` (línea 25)
```python
def integrate_datasets(
    solar_path: str | Path = "data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv",
    chargers_path: str | Path = "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
    bess_path: str | Path = "data/oe2/bess/bess_ano_2024.csv",
    output_path: str | Path = "data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv"
) -> pd.DataFrame:
```

### En `enrich_chargers.py` (línea 28)
```python
def enrich_chargers_dataset(
    chargers_path: str | Path = "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
    output_path: str | Path = "data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv"
):
```

---

## ✅ Validación de Rutas

Todas las rutas se validan automáticamente en:

```python
from src.dataset_builder_citylearn import load_solar_data, load_bess_data, load_chargers_data, load_mall_demand_data

# Automáticamente busca y valida las rutas fijas:
solar = load_solar_data()          # Busca DEFAULT_SOLAR_PATH
bess = load_bess_data()            # Busca DEFAULT_BESS_PATH
chargers = load_chargers_data()    # Busca DEFAULT_CHARGERS_PATH
demand = load_mall_demand_data()   # Busca DEFAULT_MALL_DEMAND_PATH

# Si no existen, lanza OE2ValidationError con ruta clara
```

---

## 📋 Ejecución Completa del Pipeline

```bash
# Ejecuta carga automática de las 4 rutas fijas:
python -m src.dataset_builder_citylearn.main_build_citylearn

# Salida esperada:
# ✅ Solar: 8,760 filas × N columnas
# ✅ BESS: 8,760 filas × N columnas
# ✅ Chargers: 8,760 filas × 38 sockets
# ✅ Mall demand: 8,760 filas
```

---

## 🚨 Si Alguna Ruta Falta

El sistema levanta `OE2ValidationError` con este mensaje:

```
Data not found in any fallback path:
data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv | ...
Current working directory: d:\diseñopvbesscar
```

**Solución**: Copiar/crear el archivo en exactamente esa ubicación.

---

## 📦 Constantes Asociadas (en `data_loader.py`)

```python
BESS_CAPACITY_KWH = 1700.0         # Capacidad máxima BESS (kWh)
BESS_MAX_POWER_KW = 400.0          # Potencia máx carga/descarga (kW)
TOTAL_SOCKETS = 38                 # 19 chargers × 2 sockets
N_CHARGERS = 19                    # Número de cargadores
MALL_DEMAND_KW = 100.0             # Demanda base Mall (kW)
SOLAR_PV_KWP = 4050.0              # Potencia pico solar instalada (kWp)

CO2_FACTOR_GRID_KG_PER_KWH = 0.4521   # Factor CO₂ red pública (kg/kWh)
```

---

## 📝 Historial de Cambios

| Versión | Cambio | Fecha |
|---------|--------|-------|
| v5.7 | Fijadas 4 rutas primarias OE2 como obligatorias | 2026-02-14 |
| v5.6 | Unificado con catalog_datasets.py | 2026-02-14 |
| v5.3 | BESS capacity = 1,700 kWh (verificado CSV) | 2026-02-12 |

---

**Marca de Control**: Todas las rutas son absolutes dentro del proyecto. No cambiar sin actualizar este documento y todos los módulos de carga.
