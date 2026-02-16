# Balance Energético del Sistema Eléctrico de Iquitos

Módulo para analizar y visualizar el balance energético integral del sistema eléctrico de Iquitos, considerando todos los componentes del dataset de CityLearn.

## 📋 Descripción

Este módulo integra **todos los datasets** de CityLearn en un análisis unificado del balance energético:

| Componente | Capacidad | Fuente Datos |
|-----------|-----------|------------|
| **Generación Solar (PV)** | 4,050 kWp | `pv_generation_hourly_citylearn_v2.csv` |
| **Almacenamiento (BESS)** | 1,700 kWh max SOC / 342 kW | `electrical_storage_simulation.csv` |
| **Demanda Mall** | ~100 kW | `demandamallhorakwh.csv` |
| **Demanda EV (38 sockets)** | ~50 kW (9h-22h) | `chargers_real_hourly_2024.csv` |
| **Red Eléctrica** | ilimitada | Complementa déficit de PV+BESS |

## 🏗️ Estructura del Módulo

```
src/dimensionamiento/oe2/balance_energetico/
├── balance.py              # Módulo principal (clase BalanceEnergeticoSystem)
├── __init__.py             # Importaciones públicas
├── example_usage.py        # Ejemplos de uso (4 variantes)
├── test_quick.py           # Prueba rápida
└── README.md               # Este archivo
```

## 🚀 Uso Rápido

### Opción 1: Análisis Completo Automático (Recomendado)

```python
from pathlib import Path
from src.dimensionamiento.oe2.balance_energetico import main

# Ejecutar análisis completo
system = main(
    data_dir=Path("data/processed/citylearn/iquitos_ev_mall"),
    output_dir=Path("reports/balance_energetico"),
    generate_plots=True
)
```

### Opción 2: Control Granular

```python
from src.dimensionamiento.oe2.balance_energetico import BalanceEnergeticoSystem, BalanceEnergeticoConfig

# Crear configuración
config = BalanceEnergeticoConfig(
    data_dir=Path("data/processed/citylearn/iquitos_ev_mall"),
    pv_capacity_kwp=4050.0,
    bess_capacity_kwh=1700.0,  # v5.2 CORRECTED: 1,700 kWh max SOC
    dod=0.80,  # 80% depth of discharge
)

# Crear sistema
system = BalanceEnergeticoSystem(config)

# Cargar datos
if system.load_all_datasets():
    # Calcular balance
    df_balance = system.calculate_balance()
    
    # Ver metricas
    system.print_summary()
    
    # Generar gráficas
    system.plot_energy_balance(Path("reports/balance_energetico"))
    system.export_balance_csv(Path("reports/balance_energetico"))
```

## 📊 Gráficas Generadas

El módulo genera **7 gráficas profesionales** para análisis multiescala:

### 1. **Balance 5 Días Representativos** (`01_balance_5dias.png`)
- Generación solar en 5 puntos del año (variabilidad climática)
- Muestra patrones estacionales
- Identificación de días nublados vs soleados

### 2. **Balance Diario (365 días)** (`02_balance_diario.png`)
- Evolución temporal de generación PV vs demanda
- Importaciones de red por día
- Identificación de períodos críticos

### 3. **Distribución de Fuentes (Pie Chart)** (`03_distribucion_fuentes.png`)
- Descomposición: PV Directo, BESS, Red Eléctrica
- Porcentajes y energías totales anuales
- Visualización de autosuficiencia

### 4. **Cascada Energética** (`04_cascada_energetica.png`)
- Flujos desde generación hasta carga
- Desglose: PV → Demanda, PV → BESS, PV → Red (desperdicio)
- Sankey simplificado de energía

### 5. **Estado de Carga BESS** (`05_bess_soc.png`)
- SOC diario (min, max, promedio) durante 365 días
- Límites operacionales (DoD)
- Ciclos de carga/descarga

### 6. **Emisiones de CO2** (`06_emisiones_co2.png`)
- Emisiones diarias del grid (0.4521 kg CO2/kWh para generación térmica)
- Promedio anual
- Identifica días de mayor demanda de red

### 7. **Utilización PV Mensual** (`07_utilizacion_pv.png`)
- Distribución mensual de flujos solares
- Descomposición: PV → Demanda, PV → BESS, PV → Red
- Variabilidad estacional

## 📈 Métricas Calculadas

El módulo calcula automáticamente 13 métricas de desempeño anual:

```
GENERACIÓN Y DEMANDA (Anuales):
  Generación PV:          1,234,567 kWh/año
  Demanda Total:            987,654 kWh/año
  Importación Red:          234,567 kWh/año
  Descarga BESS:             45,678 kWh/año

COBERTURA DE DEMANDA:
  PV Directo:                75.2 %
  BESS:                       4.6 %
  Red Eléctrica:             20.2 %
  ───────────────────────────────
  AUTOSUFICIENCIA:           79.8 %

EFICIENCIA PV:
  PV Utilizado:             987,654 kWh/año
  PV Desperdiciado:         246,913 kWh/año
  Utilización:               80.0 %

EMISIONES (Grid @ 0.4521 kg CO2/kWh):
  Total CO2:              106,084 kg CO2/año
  Intensidad:               0.107 kg CO2/kWh
```

## 🔧 Configuración Personalizada

### Parámetros de Entrada

```python
BalanceEnergeticoConfig(
    # Rutas
    data_dir: Path = Path("data/processed/citylearn/iquitos_ev_mall")
    
    # Capacidades del sistema
    pv_capacity_kwp: float = 4050.0          # kW pico
    bess_capacity_kwh: float = 1700.0         # kWh (v5.2 CORRECTED)
    bess_power_kw: float = 342.0             # kW nominal (0.36 C-rate)
    
    # Parámetros de operación
    dod: float = 0.80                        # Profundidad de descarga
    efficiency_roundtrip: float = 0.95       # Eficiencia round-trip v5.2
    
    # Contexto de análisis
    year: int = 2024
    timezone: str = "America/Lima"           # UTC-5
    co2_intensity_kg_per_kwh: float = 0.4521 # kg CO2/kWh
)
```

## 📂 Estructura de Datos de Entrada

El módulo espera los siguientes archivos en `data/processed/citylearn/iquitos_ev_mall/`:

```
data/processed/citylearn/iquitos_ev_mall/
├── Generacionsolar/
│   └── pv_generation_hourly_citylearn_v2.csv    (8,760 filas)
├── chargers/
│   ├── chargers_real_hourly_2024.csv            (8,760 filas)
│   └── chargers_real_statistics.csv
├── demandamallkwh/
│   └── demandamallhorakwh.csv                   (8,760 filas)
├── electrical_storage_simulation.csv            (8,760 filas)
└── schema.json
```

### Columnas Requeridas

| Archivo | Columnas Aceptadas |
|---------|-------------------|
| **Solar** | `pv_generation_kw`, `pv_kwh`, `ac_power_kw` |
| **Chargers** | `total_demand_kw`, `total_power_kw`, `demand_kw` |
| **Mall** | `demand_kw`, `demandamallkwh`, `mal_kwh` |
| **BESS** | `soc_percent`, `state_of_charge`, `soc` |

El módulo busca automáticamente entre múltiples nombres de columnas para máxima compatibilidad.

## 🖥️ Ejemplos de Uso

### Ejemplo 1: Análisis Completo

```bash
python -c "from src.dimensionamiento.oe2.balance_energetico import main; main()"
```

### Ejemplo 2: Prueba Rápida

```bash
python src/dimensionamiento/oe2/balance_energetico/test_quick.py
```

### Ejemplo 3: Con Ejemplos de Código

```bash
# Análisis completo
python src/dimensionamiento/oe2/balance_energetico/example_usage.py 1

# Configuración personalizada
python src/dimensionamiento/oe2/balance_energetico/example_usage.py 2

# Solo métricas
python src/dimensionamiento/oe2/balance_energetico/example_usage.py 3

# Generación incremental
python src/dimensionamiento/oe2/balance_energetico/example_usage.py 4
```

## 📊 Flujo de Energía

```
┌─────────────────────────────────────────────────────────┐
│              GENERACIÓN Y ALMACENAMIENTO                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  PV Solar (4,050 kWp)  →  [Distribución Horaria]       │
│         ↓                                                │
│    ┌────────────┴──────────────┬─────────────┐           │
│    ↓                           ↓             ↓           │
│  DEMANDA                    BESS            GRID         │
│  (Mall+EV)                (Carga)          (Export)      │
│    │                         │               │           │
│    └────────────┬──────────────┴─────────────┘           │
│                 ↓                                        │
│         [Simulación Horaria 8,760h]                      │
│                 ↓                                        │
│  ┌─────────────────────────────────────┐                │
│  │  BALANCE ENERGÉTICO INTEGRAL        │                │
│  │  - Flujos energéticos               │                │
│  │  - Estado BESS (SOC)                │                │
│  │  - Emisiones CO2 (grid)             │                │
│  │  - Autosuficiencia                  │                │
│  └─────────────────────────────────────┘                │
│                 ↓                                        │
│  [7 GRÁFICAS PROFESIONALES]                             │
│  [CSV EXPORT PARA ANÁLISIS]                             │
└─────────────────────────────────────────────────────────┘
```

## ⚙️ Requisitos

- Python 3.11+
- pandas, numpy, matplotlib
- CityLearn v2.5.0 (datasets)

## 📝 Ejemplo de Salida

```
======================================================================
  BALANCE ENERGÉTICO - SISTEMA ELÉCTRICO IQUITOS
======================================================================

GENERACIÓN Y DEMANDA (Anuales):
  Generación PV:            1,234,567 kWh/año
  Demanda Total:              987,654 kWh/año
  Importación Red:            234,567 kWh/año
  Descarga BESS:               45,678 kWh/año

COBERTURA DE DEMANDA:
  PV Directo:                   75.2 %
  BESS:                          4.6 %
  Red Eléctrica:                20.2 %
  ───────────────────────────────
  AUTOSUFICIENCIA:              79.8 %

EFICIENCIA PV:
  PV Utilizado:              987,654 kWh/año
  PV Desperdiciado:          246,913 kWh/año
  Utilización:                 80.0 %

EMISIONES (Grid @ 0.4521 kg CO2/kWh):
  Total CO2:                106,084 kg CO2/año
  Intensidad:                  0.107 kg CO2/kWh

======================================================================
```

## 🔍 Solución de Problemas

### Error: "Archivo no encontrado"

**Verificar:**
- Ruta del directorio `data/processed/citylearn/iquitos_ev_mall/`
- Que todos los 4 archivos principales existan
- Usar comando de diagnóstico:
  ```bash
  ls -la data/processed/citylearn/iquitos_ev_mall/
  ```

### Error: "Longitudes inconsistentes"

**Causa:** Los datasets no tienen 8,760 horas (1 año).

**Solución:**
- Verificar que todos los CSV tengan exactamente 8,760 filas
- Si tienen 15 minutos (35,040 filas), resamplear a horario:
  ```python
  df.set_index('time').resample('h').mean()
  ```

### Gráficas no se generan

**Verificar:**
- Que matplotlib esté instalado: `pip install matplotlib`
- Permisos de escritura en `reports/balance_energetico/`
- Espacio en disco disponible

## 📚 Referencias Internas

- `balance.py`: Implementación principal (1,300+ líneas)
  - Clase `BalanceEnergeticoSystem`: Orquestación del análisis
  - Clase `BalanceEnergeticoConfig`: Configuración (inmutable)
  - Función `main()`: Interfaz simplificada

- `bess.py`: Simulación BESS (módulo relacionado)
  - Simulación de flujos energéticos
  - Cálculo de SOC y ciclos

- `dataset_builder.py`: Validación de datos CityLearn
  - Verificación de consistencia
  - Mapeo de columnas

## 📞 Contacto & Soporte

Para reportes de errores o solicitudes de funcionalidades:
- Revisar logs en `test_quick.py`
- Verificar datos en `reports/balance_energetico/balance_energetico_horario.csv`
- Consultar ejemplos en `example_usage.py`

---

**Última actualización:** 2026-02-11  
**Versión:** 1.0  
**Departamento:** Diseño OE2 - Dimensionamiento de BESS  
**Proyecto:** EV Charging Optimization - Iquitos, Peru
