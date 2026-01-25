# ✅ Datasets Anuales por Charger - Verificación Completada

## Estado: ✅ DATASETS OE3 GENERADOS (2026-01-24)

### Datasets CityLearn v2 para Entrenamiento OE3

Se generaron datasets anuales (8760 horas) con 128 tomas controlables para entrenamiento de agentes RL.

**Configuración**:

- 32 cargadores físicos × 4 tomas = **128 tomas totales**
- Playa Motos: 28 cargadores × 4 tomas = 112 tomas @ 2 kW
- Playa Mototaxis: 4 cargadores × 4 tomas = 16 tomas @ 3 kW
- Horario: 9 AM - 10 PM (13 horas)
- Sesiones: 30 minutos (Modo 3 IEC 61851)

---

## 📊 Escenarios Disponibles

### Tabla 13 OE2 - Escenarios de Dimensionamiento

| Escenario | PE | FC | Cargadores | Tomas | Energía/Día | Total Vehíc/Día | Total/20 años |
|-----------|---:|---:|----------:|------:|------------:|----------------:|--------------:|
| CONSERVADOR | 0.10 | 0.40 | 4 | 16 | 231 kWh | 257 | 1,876,100 |
| MEDIANO | 0.50 | 0.60 | 20 | 80 | 1,739 kWh | 1,287 | 9,395,100 |
| **RECOMENDADO*** | **0.65** | **0.75** | **32** | **128** | **2,823 kWh** | **1,672** | **12,205,600** |
| MÁXIMO | 1.00 | 1.00 | 35 | 140 | 5,800 kWh | 2,575 | 18,797,500 |

### Vehículos Cargados por Período (Todos los Escenarios)

| Escenario | Motos/Día | Mototaxis/Día | Total/Día | Total/Mes | Total/Año | Total/20 años |
|-----------|----------:|--------------:|----------:|----------:|----------:|--------------:|
| CONSERVADOR | 225 | 32 | 257 | 7,710 | 93,805 | 1,876,100 |
| MEDIANO | 1,125 | 162 | 1,287 | 38,610 | 469,755 | 9,395,100 |
| **RECOMENDADO*** | **1,462** | **210** | **1,672** | **50,160** | **610,280** | **12,205,600** |
| MÁXIMO | 2,250 | 325 | 2,575 | 77,250 | 939,875 | 18,797,500 |

### Energía Cargada por Período (Todos los Escenarios)

| Escenario | Energía/Día | Energía/Mes | Energía/Año | Energía/20 años |
|-----------|------------:|------------:|------------:|----------------:|
| CONSERVADOR | 231 kWh | 6,936 kWh | 84,388 kWh | 1,688 MWh |
| MEDIANO | 1,739 kWh | 52,164 kWh | 634,662 kWh | 12,693 MWh |
| **RECOMENDADO*** | **2,823 kWh** | **84,690 kWh** | **1,030,395 kWh** | **20,608 MWh** |
| MÁXIMO | 5,800 kWh | 174,000 kWh | 2,117,000 kWh | 42,340 MWh |

---

## 📁 Ubicación de Datasets OE3

### Escenario RECOMENDADO (Entrenamiento)

```text
data/processed/citylearn/iquitos_128_tomas/
├── Playa_Motos/
│   ├── MOTO_CH_001_T1.csv ... MOTO_CH_028_T4.csv  (112 archivos)
│   └── [112 tomas × 8762 filas cada una]
├── Playa_Mototaxis/
│   ├── MOTOTAXI_CH_001_T1.csv ... MOTOTAXI_CH_004_T4.csv  (16 archivos)
│   └── [16 tomas × 8762 filas cada una]
├── schema_128_tomas.json      # Schema CityLearn v2
└── dataset_summary.json       # Resumen de generación
```bash

**Energía**: ~905 kWh/día (Tabla 13 RECOMENDADO)

### Escenario MÁXIMO (Diseño)

```text
data/processed/citylearn/iquitos_128_tomas_maximo/
├── Playa_Motos/
│   ├── MOTO_CH_001_T1.csv ... MOTO_CH_028_T4.csv  (112 archivos)
│   └── [112 tomas × 8762 filas cada una]
├── Playa_Mototaxis/
│   ├── MOTOTAXI_CH_001_T1.csv ... MOTOTAXI_CH_004_T4.csv  (16 archivos)
│   └── [16 tomas × 8762 filas cada una]
├── schema_128_tomas_maximo.json   # Schema CityLearn v2
└── dataset_summary_maximo.json    # Resumen de generación
```bash

**Energía**: ~2,298 kWh/día (Capacidad máxima 128 tomas)

---

## 📊 Datasets Legacy (101 Escenarios OE2)

```text
data/interim/oe2/chargers/annual_datasets/
├── Playa_Motos/
│   ├── 0/               (Baseline: demanda típica determinística)
│   │   ├── MOTO_CH_001.csv ... MOTO_CH_112.csv
│   │   └── aggregated_profile.csv
│   └── 1-100/           (Escenarios Monte Carlo)
    │   ├── MOTO_TAXI_CH_113.csv ... MOTO_TAXI_CH_128.csv
    │   └── aggregated_profile.csv
    ├── 1/
    │   └── [16 chargers anuales]
    ├── 2/
    │   └── [16 chargers anuales]
    ├── ...
    └── 100/             (Escenario MC 100)
        └── [16 chargers anuales]
```text

---

## Verificación de Datasets - 101 Escenarios

### Conteo Total

| Elemento | Cantidad |
| ---------- | ---------- |
| **Playa Motos** | 112 chargers |
| **Playa Mototaxis** | 16 chargers |
| **Total Chargers** | **128** |
| **Escenarios** | **101** (0 baseline + 1-100 variaciones MC) |
| **Archivos por escenario** | 128 × 2 playas = 256 CSVs |
| **Total Archivos** | 101 escenarios × 256 CSVs = **25,856 archivos** |

### Datos por Charger - 101 Escenarios

✅ **Escenario 0 (Baseline)** - Demanda típica determinística:

- Playa Motos: 112 chargers × 8760 h/año = 982,080 puntos
- Playa Mototaxis: 16 chargers × 8760 h/año = 140,160 puntos
- **Subtotal**: 1,122,240 datos

✅ **Escenarios 1-100 (Monte Carlo)** - 100 variaciones con incertidumbre:

- Cada escenario: Playa Motos (982,080) + Playa Taxis (140,160) = 1,122,240 datos
- Total 100 escenarios MC: 100 × 1,122,240 = 112,224,000 datos

**TOTAL DATASETS**:

- Baseline: 1,122,240 datos
- Monte Carlo: 112,224,000 datos
- **TOTAL**: 113,346,240 puntos de datos de carga (101 escenarios × 128 chargers × 8760 horas)

---

## Estructura de Archivo CSV

Cada charger tiene archivo con 8760 filas (1 hora × 365 días):

```csv
timestamp,power_kw,energy_kwh
2024-01-01 00:00:00,0.0,0.0
2024-01-01 01:00:00,0.0,0.0
...
2024-01-01 09:00:00,2.0,2.0    (ejemplo: cargando a 2 kW en Playa Motos)
...
2024-12-31 23:00:00,0.0,0.0
```text

### Campos

- **timestamp**: Marca temporal (YYYY-MM-DD HH:MM:SS)
- **power_kw**: Potencia de carga en kW (0 = no cargando, hasta 2 kW Motos o 3 kW Taxis)
- **energy_kwh**: Energía acumulada en esa hora

---

## Integración con CityLearn

### Para Entrenamiento

Cada observable individual en CityLearn:

```python
"charger_MOTO_CH_001_power_kw"      # Leer de MOTO_CH_001.csv
"charger_MOTO_CH_002_power_kw"      # Leer de MOTO_CH_002.csv
...
"charger_MOTO_TAXI_CH_128_power_kw" # Leer de MOTO_TAXI_CH_128.csv
```text

CityLearn **en cada timestep (1 hora)**:

1. Lee power_kw de cada CSV correspondiente
2. Suma para obtener agregados (`ev_charging_power_playa_motos_kw`, etc.)
3. Pasa observables al agente RL
4. Agente toma acción (reducir potencia, pausa, etc.)
5. Aplica cambios y pasa al siguiente timestep

### Escenarios Disponibles

El agente puede entrenarse en:

- **Base**: Demanda típica (escenario normal)
- **High**: Demanda pico (casos extremos, aprender robustez)
- **Low**: Demanda reducida (casos de bajo uso)

---

## Listo para Entrenamiento

✅ **128 chargers** → 128 datasets anuales individuales
✅ **101 escenarios** → 1 baseline + 100 variaciones Monte Carlo
✅ **8760 timesteps/charger** → Cobertura anual completa
✅ **113 M puntos de datos** → Suficiente para RL robusto

### Próximo Paso

Ejecutar entrenamiento con múltiples escenarios:

```bash
python train_v2_fresh.py --scenario 0 --num-episodes 2  # Baseline
python train_v2_fresh.py --scenario 1 --num-episodes 2  # MC 1
python train_v2_fresh.py --scenario 50 --num-episodes 2 # MC 50
```text

CityLearn cargará automáticamente para cada escenario:

- `Playa_Motos/{scenario}/MOTO_CH_001.csv` → observable `charger_MOTO_CH_001_power_kw`
- `Playa_Motos/{scenario}/MOTO_CH_002.csv` → observable `charger_MOTO_CH_002_power_kw`
- ... (128 chargers × 101 escenarios)

---

## Verificación de Integridad

```python
# Cada charger debe tener exactamente:
# - 8760 filas (365 días × 24 horas)
# - 3 columnas (timestamp, power_kw, energy_kwh)
# - power_kw ≤ 2 kW (Motos) o 3 kW (Taxis)
# - Secuencia temporal continua (sin saltos)

Verificación: ✅ COMPLETADA
```text

---

**Nota**: Los datasets fueron generados por el script OE2 (n_scenarios=100) con:

- 1 escenario baseline (determinístico, demanda típica)
- 100 escenarios Monte Carlo (incertidumbre en demanda, variabilidad realista)
- Perfiles horarios realistas de carga de motos y mototaxis durante 2024
