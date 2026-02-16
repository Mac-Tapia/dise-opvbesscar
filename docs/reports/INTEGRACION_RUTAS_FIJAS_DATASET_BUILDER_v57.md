# INTEGRACIÓN DE RUTAS FIJAS - Dataset Builder v5.7

**Fecha**: 14 de febrero de 2026  
**Estado**: ✅ Todas las rutas validadas y disponibles

---

## 📊 Resumen de Rutas Fijas

| Componente | Ruta Fija | Filas | Columnas | Tamaño | Estado |
|-----------|-----------|-------|----------|--------|--------|
| **Solar** | `data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv` | 8,760 | 16 | 1.2 MB | ✅ |
| **BESS** | `data/oe2/bess/bess_ano_2024.csv` | 8,760 | 25 | 1.6 MB | ✅ |
| **Chargers** | `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` | 8,760 | 353 | 15.5 MB | ✅ |
| **Mall Demand** | `data/oe2/demandamallkwh/demandamallhorakwh.csv` | 8,785 | 6 | 0.4 MB | ✅ |

---

## 🔗 Integración en Módulos

### 1. [src/dataset_builder_citylearn/data_loader.py](../src/dataset_builder_citylearn/data_loader.py)

**Líneas 59-62** - Definición de rutas primarias:
```python
# Primary data sources (OE2 - source of truth - FIXED PATHS v5.7)
DEFAULT_SOLAR_PATH = Path("data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv")
DEFAULT_BESS_PATH = Path("data/oe2/bess/bess_ano_2024.csv")
DEFAULT_CHARGERS_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
DEFAULT_MALL_DEMAND_PATH = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
```

**Función `load_solar_data()`** (línea 215):
- Usa `DEFAULT_SOLAR_PATH`
- Valida que sean 8,760 filas (horario)
- Detecta columna de potencia automáticamente

**Función `load_bess_data()`** (línea 269):
- Usa `DEFAULT_BESS_PATH`
- Verifica capacidad = 1,700 kWh
- Valida 8,760 filas

**Función `load_chargers_data()`** (línea 310):
- Usa `DEFAULT_CHARGERS_PATH`
- Valida 38 sockets = 19 chargers × 2
- Detecta columnas de potencia por socket

**Función `load_mall_demand_data()`** (línea 347):
- Usa `DEFAULT_MALL_DEMAND_PATH`
- Detección automática de columna de demanda
- Fallback a 100 kW constante si falta

---

### 2. [src/dataset_builder_citylearn/integrate_datasets.py](../src/dataset_builder_citylearn/integrate_datasets.py)

**Línea 25** - Función principal:
```python
def integrate_datasets(
    solar_path: str | Path = "data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv",
    chargers_path: str | Path = "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
    bess_path: str | Path = "data/oe2/bess/bess_ano_2024.csv",
    output_path: str | Path = "data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv"
) -> pd.DataFrame:
```

**Propósito**: Integra Solar + Chargers + BESS  
**Enriquecimiento**: Agrega 5 columnas nuevas al dataset solar

---

### 3. [src/dataset_builder_citylearn/enrich_chargers.py](../src/dataset_builder_citylearn/enrich_chargers.py)

**Línea 28** - Función de enriquecimiento:
```python
def enrich_chargers_dataset(
    chargers_path: str | Path = "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
    output_path: str | Path = "data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv"
):
```

**Propósito**: Agrega 5 columnas de reducción CO₂ directo

---

### 4. [src/dataset_builder_citylearn/main_build_citylearn.py](../src/dataset_builder_citylearn/main_build_citylearn.py)

**Orquestrador principal**:
- Paso 1: Enriquecimiento CHARGERS → `chargers_ev_ano_2024_enriched_v2.csv`
- Paso 2: Integración OE2 → `pv_generation_citylearn_enhanced_v2.csv`
- Paso 3: Análisis y validación (usa todas las rutas)

**Ejecución**:
```bash
python -m src.dataset_builder_citylearn.main_build_citylearn
```

---

## ✅ Validación Automática

Todas las rutas se validan al cargar:

```python
from src.dataset_builder_citylearn import rebuild_oe2_datasets_complete

# Carga y valida automáticamente las 4 rutas fijas
data = rebuild_oe2_datasets_complete()

# Resultado:
# {
#   'solar': SolarData(...),      # data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
#   'bess': BESSData(...),        # data/oe2/bess/bess_ano_2024.csv
#   'chargers': ChargerData(...), # data/oe2/chargers/chargers_ev_ano_2024_v3.csv
#   'demand': DemandData(...),    # data/oe2/demandamallkwh/demandamallhorakwh.csv
#   'scenarios': {...}            # Metadatos opcionales
# }
```

---

## 🚨 Manejo de Errores

Sise intenta cargar con rutas inválidas:

```python
OE2ValidationError: Data not found in any fallback path:
data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv | ...
Current working directory: d:\diseñopvbesscar
```

**Solución**: Asegurar que el archivo existe exactamente en esa ubicación.

---

## 📋 Pipeline Completo de Construcción

```
ENTRADA (4 rutas fijas OE2):
├── data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
├── data/oe2/bess/bess_ano_2024.csv
├── data/oe2/chargers/chargers_ev_ano_2024_v3.csv
└── data/oe2/demandamallkwh/demandamallhorakwh.csv

        ↓ [data_loader.py: load_*_data()]

PASO 1: Enriquecimiento CHARGERS
├── enrich_chargers.py
└── Output: data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv
    (+5 columnas reducción CO₂)

PASO 2: Integración OE2 completa
├── integrate_datasets.py
└── Output: data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv
    (Solar + 5 columnas energía suministrada)

PASO 3: Análisis y Validación
├── analyze_datasets.py
└── Output: reports/ y logs/

SALIDA (datasets listos para CityLearn v2):
└── data/processed/citylearn/iquitos_ev_mall/
    ├── observations_*.csv
    ├── rewards_*.csv
    └── metadata_*.json
```

---

## 🎯 Cómo Usar en Código

### Opción 1: Carga automática (recomendado)
```python
from src.dataset_builder_citylearn import load_solar_data, load_bess_data

solar = load_solar_data()      # Busca DEFAULT_SOLAR_PATH automáticamente
bess = load_bess_data()        # Busca DEFAULT_BESS_PATH automáticamente
```

### Opción 2: Carga con override
```python
from src.dataset_builder_citylearn import load_solar_data

solar = load_solar_data(
    path=Path("custom/path/solar.csv")  # Override ruta primaria
)
```

### Opción 3: Carga completa
```python
from src.dataset_builder_citylearn import rebuild_oe2_datasets_complete

data = rebuild_oe2_datasets_complete()
solar = data['solar']
bess = data['bess']
chargers = data['chargers']
demand = data['demand']
```

---

## 📦 Constants Definidas

```python
# data_loader.py (líneas 85-97)
BESS_CAPACITY_KWH = 1700.0         # Capacidad máxima BESS
BESS_MAX_POWER_KW = 400.0          # Potencia máx carga/descarga
EV_DEMAND_KW = 50.0                # Demanda EV constante
N_CHARGERS = 19                    # Número de cargadores
TOTAL_SOCKETS = 38                 # 19 × 2 sockets
MALL_DEMAND_KW = 100.0             # Demanda base Mall
SOLAR_PV_KWP = 4050.0              # Potencia PV pico instalada

CO2_FACTOR_GRID_KG_PER_KWH = 0.4521    # Red pública (térmica Iquitos)
CO2_FACTOR_EV_KG_PER_KWH = 2.146       # Equivalente combustible
```

---

## 🔐 Checkpoint de Control

✅ **Verificado 2026-02-14**:
- Solar: 8,760 filas horarias
- BESS: Capacidad 1,700 kWh confrmada
- Chargers: 38 sockets controlables (19×2)
- Mall: 100 kW demanda base
- Todas las rutas existen y son válidas

---

## 📞 Referencia Rápida

**Para cargar TODO**:
```bash
python -m src.dataset_builder_citylearn.main_build_citylearn
```

**Para validar rutas**:
```python
from src.dataset_builder_citylearn import rebuild_oe2_datasets_complete
rebuild_oe2_datasets_complete()  # Levanta OE2ValidationError si hay error
```

**Para integración personalizada**:
```python
from src.dataset_builder_citylearn import integrate_datasets
df_enhanced_solar = integrate_datasets()  # Usa rutas por defecto
```
