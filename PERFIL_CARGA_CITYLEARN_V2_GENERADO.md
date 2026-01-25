# 🎮 PERFIL DE CARGA - CITYLEARN V2 GENERADO

## ✅ Generación Completada

**Fecha:** 2025-01-24  
**Proyecto:** Sistema FV + BESS - Mall Dos Playas, Iquitos  
**Período:** 1 año completo (365 días × 8,760 timesteps)  
**Script:** `scripts/generar_perfil_carga_citylearn_v2.py`

---

## 📦 Archivos Generados

**Ubicación:** `data/oe2/citylearn/training_data/`

### 1️⃣ demand_profile.csv

- **Contenido:** Demanda horaria (Mall + EV)
- **Timesteps:** 8,760 (1 año)
- **Demanda Mall:** 33,885 kWh/día (datos reales)
- **Demanda EV:** 2,823 kWh/día (dinámica)
- **Total:** 13,398,420 kWh/año

```csv
Hour,Mall_Load_kWh,EV_Demand_kWh,Total_Demand_kWh
0,788.02,50.23,838.25
1,788.02,40.18,828.20
...
8759,788.02,50.23,838.25
```

### 2️⃣ solar_generation_profile.csv

- **Contenido:** Generación solar Iquitos
- **Timesteps:** 8,760 (1 año)
- **Mínimo:** 0.00 kW
- **Máximo:** 2,845.60 kW
- **Promedio:** 918.17 kW/hora
- **Total:** 8,043,140 kWh/año

```csv
Hour,PV_Generation_kW
0,0.00
1,0.00
...
12,2825.15
...
23,0.00
```

### 3️⃣ energy_balance_profile.csv

- **Contenido:** Balance energético horario
- **Cálculos:** Superávit/Déficit solar
- **Cobertura:** Porcentaje cubierto por solar

```csv
Hour,PV_Generation_kWh,Total_Demand_kWh,Solar_Surplus_Deficit_kWh,PV_Coverage_Percent
0,0.00,838.25,-838.25,0.00
12,2825.15,1200.50,1624.65,235.47
```

### 4️⃣ bess_parameters.csv

- **Contenido:** Parámetros del BESS
- **Formato:** CSV con configuración

```csv
Parameter,Value,Unit,Description
Capacity,1711.60,kWh,Usable energy capacity
Nominal_Power,622.40,kW,Charge/discharge power
DoD,80,%, Depth of Discharge
Efficiency_Roundtrip,95,%,Round-trip efficiency
C_Rate,0.36,C,Power to capacity ratio
Initial_SOC,50,%,Starting state of charge
Min_SOC,20,%,Minimum SOC
Max_SOC,100,%,Maximum SOC
```

### 5️⃣ citylearn_config.json

- **Contenido:** Configuración completa CityLearn v2
- **Formato:** JSON con toda la información

```json
{
  "schema_version": "v2",
  "simulation": {
    "timestep_duration_seconds": 3600,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "total_timesteps": 8760,
    "frequency": "hourly"
  },
  "building": {
    "name": "Mall Dos Playas",
    "location": {
      "city": "Iquitos",
      "state": "Loreto",
      "country": "Peru",
      "latitude": -3.7492,
      "longitude": -73.2345,
      "timezone": "America/Lima",
      "altitude": 106
    }
  },
  ...
}
```

### 6️⃣ run_training.sh

- **Contenido:** Script para ejecutar entrenamiento
- **Propósito:** Facilitar lanzamiento de entrenamientos

---

## 📊 Resumen Estadístico

### Demanda

| Componente | Diaria | Anual | Porcentaje |
|-----------|--------|-------|-----------|
| 🏢 Mall | 33,885 kWh | 12,368,025 kWh | 92.3% |
| 🚗 EV | 2,823 kWh | 1,030,395 kWh | 7.7% |
| **⚡ Total** | **36,708 kWh** | **13,398,420 kWh** | **100.0%** |

### Generación

| Fuente | Diaria | Anual | Cobertura |
|--------|--------|-------|-----------|
| ☀️ Solar | 22,036 kWh | 8,043,140 kWh | 60.0% |
| 🔋 BESS (capacidad/día) | 1,712 kWh | - | - |

### Balance Energético

- **Déficit anual:** 5,355,280 kWh (40% no cubierto por solar)
- **Necesidad almacenamiento:** 14,672 kWh/día (promedio)
- **Ciclaje BESS:** 8.57 ciclos/día (máximo teórico)
- **C-rate:** 0.36C (ratio potencia/capacidad)

---

## 🎯 Datos de Entrada (Reales de Iquitos)

### Demanda del Mall

- **Archivo:** `building_load.csv`
- **Tipo:** Datos reales horarios
- **Período:** 2024 (365 días)
- **Resolución:** 1 hora
- **Rango:** 788 - 2,101 kWh/hora
- **Status:** ✅ VERIFICADO

### Generación Solar

- **Archivo:** `pv_generation_timeseries.csv`
- **Tipo:** Datos reales horarios
- **Período:** 2024-01-01 a 2024-12-30
- **Resolución:** 1 hora
- **Status:** ✅ VERIFICADO

### Demanda EV

- **Patrón:** Dinámico (24 horas repetitivas)
- **Picos:** 08:00-10:00 (mañana), 16:00-18:00 (tarde)
- **Mínimos:** 00:00-05:00 (noche)
- **Total:** 2,823 kWh/día
- **Equipamiento:** 32 cargadores, 128 sockets

### Sistema BESS

- **Capacidad:** 1,711.6 kWh
- **Potencia:** 622.4 kW
- **DoD:** 80%
- **Eficiencia:** 95%
- **Tipo:** Lithium-ion
- **Status:** ✅ PARÁMETROS REALES

---

## 🚀 Cómo Usar el Perfil

### Opción 1: Entrenar con CityLearn v2

```bash
cd d:\diseñopvbesscar

python -m src.iquitos_citylearn.oe2.train_citylearn_v2 \
    --config data/oe2/citylearn/training_data/citylearn_config.json \
    --episodes 50 \
    --device cuda \
    --output-dir ./checkpoints/citylearn_v2/
```

### Opción 2: Cargar datos en script personalizado

```python
import pandas as pd

# Cargar demanda
demand = pd.read_csv('data/oe2/citylearn/training_data/demand_profile.csv')
print(f"Total demand: {demand['Total_Demand_kWh'].sum():.0f} kWh")

# Cargar solar
solar = pd.read_csv('data/oe2/citylearn/training_data/solar_generation_profile.csv')
print(f"Total solar: {solar['PV_Generation_kW'].sum():.0f} kWh")

# Cargar balance
balance = pd.read_csv('data/oe2/citylearn/training_data/energy_balance_profile.csv')
print(f"Solar coverage: {balance['PV_Coverage_Percent'].mean():.1f}%")
```

### Opción 3: Usar configuración JSON

```python
import json

with open('data/oe2/citylearn/training_data/citylearn_config.json', 'r') as f:
    config = json.load(f)

# Acceder a parámetros
building_name = config['building']['name']
capacity = config['electrical_storage']['battery']['capacity_kwh']
```

---

## 🎮 Próximos Pasos

### Corto Plazo (Inmediato)

1. ✅ Perfil generado
2. 📌 Revisar archivos CSV generados
3. 📌 Validar que CityLearn v2 pueda leer la configuración
4. 📌 Lanzar primer entrenamiento (10 episodios)

### Mediano Plazo

5. 📌 Entrenar 50 episodios
2. 📌 Analizar convergencia de agentes
3. 📌 Optimizar parámetros BESS basado en resultados

### Largo Plazo

8. 📌 Implementar control BESS en tiempo real
2. 📌 Validar con datos de operación actual
3. 📌 Desplegar en infraestructura Iquitos

---

## 📁 Estructura de Archivos

```
data/oe2/
├── citylearn/
│   ├── training_data/          ← NUEVOS ARCHIVOS
│   │   ├── demand_profile.csv
│   │   ├── solar_generation_profile.csv
│   │   ├── energy_balance_profile.csv
│   │   ├── bess_parameters.csv
│   │   ├── citylearn_config.json
│   │   └── run_training.sh
│   │
│   ├── building_load.csv       ← Entrada (Real)
│   ├── pv_solar_generation.csv ← Entrada (Real)
│   └── bess_schema_params.json ← Entrada (Real)
│
├── tabla_escenarios_vehiculos.csv
├── pv_generation_timeseries.csv
├── perfil_horario_carga.csv
└── bess_dimensionamiento_schema.json
```

---

## ✅ Status

- ✅ **Perfil de carga generado:** Completo
- ✅ **Datos reales integrados:** 100%
- ✅ **Timesteps:** 8,760 (1 año)
- ✅ **Configuración CityLearn v2:** Lista
- ✅ **Balance energético:** Calculado
- 📌 **Próximo:** Entrenar con CityLearn v2

---

**Generado por:** generar_perfil_carga_citylearn_v2.py  
**Fecha:** 2025-01-24  
**Versión:** v2.0
