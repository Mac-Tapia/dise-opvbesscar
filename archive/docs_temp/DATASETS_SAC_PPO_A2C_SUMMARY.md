# 🎯 Datasets Utilizados por SAC, PPO y A2C

## Respuesta Corta
**SAC, PPO y A2C usan EXACTAMENTE LOS MISMOS 5 datasets OE2.**

Todos se cargan a través de una única ruta de código en `src/citylearnv2/dataset_builder/data_loader.py`:

```python
from src.citylearnv2.dataset_builder.dataset_builder import (
    load_solar_data,
    load_chargers_data, 
    load_bess_data,
    load_mall_demand_data,
    load_scenarios_metadata
)
```

---

## 📊 Los 5 Datasets Compartidos

### 1️⃣ SOLAR (Generación FV)
| Propiedad | Valor |
|-----------|-------|
| **Archivo** | `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv` |
| **Resolución** | 8,760 horas (1 año completo) |
| **Columna** | `potencia_kw` |
| **Rango** | 0 - 4,050 kW (pico) |
| **Función** | `load_solar_data()` |
| **Generador** | PVGIS (Iquitos, Perú, 3.75°S 73.25°W) |
| **Energía anual** | 8,292,514 kWh |

### 2️⃣ CHARGERS (Cargadores EV + Demanda)
| Propiedad | Valor |
|-----------|-------|
| **Archivo** | `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` |
| **Resolución** | 8,760 horas × 38 tomas |
| **Tomas** | 30 motos (15 cargadores × 2) + 8 taxis (4 cargadores × 2) |
| **Potencia** | 7.4 kW por toma (Mode 3, 32A @ 230V monofásico) |
| **Potencia instalada** | 281.2 kW |
| **Función** | `load_chargers_data()` |
| **Energía anual** | 2,463,312 kWh (EV cargadas) |
| **Estructura** | DataFrame con 38 columnas (1 por toma) |

### 3️⃣ BESS (Almacenamiento)
| Propiedad | Valor |
|-----------|-------|
| **Archivo** | `data/oe2/bess/bess_ano_2024.csv` |
| **Resolución** | 8,760 horas |
| **Capacidad nominal** | 1,700 kWh (SOC máx = 95% = 1,615 kWh) |
| **Potencia** | 342 kW (carga/descarga) |
| **Función** | `load_bess_data()` |
| **SOC inicial** | Variable por hora (dataset real) |
| **SOC promedio** | 48.1% |

### 4️⃣ MALL (Centro Comercial)
| Propiedad | Valor |
|-----------|-------|
| **Archivo** | `data/oe2/demandamallkwh/demandamallhorakwh.csv` |
| **Resolución** | 8,760 horas |
| **Demanda mínima** | ~30 kW |
| **Demanda máxima** | ~240 kW |
| **Demanda promedio** | 1,411 kW |
| **Función** | `load_mall_demand_data()` |
| **Energía anual** | 12,368,653 kWh |

### 5️⃣ ESCENARIOS (Metadata, NO observables)
| Propiedad | Valor |
|-----------|-------|
| **Directorio** | `data/oe2/chargers/` |
| **Archivos** | 5 CSV (horarios, perfiles, etc.) |
| **Función** | `load_scenarios_metadata()` |
| **Contenido** | Contexto: vehículos demandando carga, SOC inicial, etc. |
| **Propósito** | No se usa en observables; solo para lógica simulación |

---

## 🔄 Flujo de Datos: OE2 → Agentes

```
OE2 (Dimensionamiento)
├─ Solar: pv_generation_citylearn2024.csv
├─ Chargers: chargers_ev_ano_2024_v3.csv
├─ BESS: bess_ano_2024.csv
├─ Mall: demandamallhorakwh.csv
└─ Scenarios: 5 CSVs en data/oe2/chargers/

        ↓ [load_* functions en data_loader.py]

OE3 (Control / CityLearn v2)
├─ Todas 27 observables → Espacio obs concatenado
├─ 39 acciones (1 BESS + 38 chargers)
└─ 8,760 timesteps (1 año)

        ↓ [mismo dataset para todos]

RL Agents (SAC, PPO, A2C)
├─ SAC (off-policy)
├─ PPO (on-policy) ← ENTRENANDO AHORA
└─ A2C (on-policy, simple)
```

---

## 🔍 Dónde se Cargan los Datos

### Ubicación física en código:

**SAC Agent** (`src/agents/sac.py`):
```python
from src.citylearnv2.dataset_builder.data_loader import (
    load_solar_data,
    load_chargers_data,
    load_bess_data,
    load_mall_demand_data
)
# Carga idéntica a PPO y A2C
```

**PPO Agent** (`src/agents/ppo_sb3.py`):
```python
from src.citylearnv2.dataset_builder.data_loader import (
    load_solar_data,
    load_chargers_data,
    load_bess_data,
    load_mall_demand_data
)
# Misma ruta de importación
```

**A2C Agent** (`src/agents/a2c_sb3.py`):
```python
from src.citylearnv2.dataset_builder.data_loader import (
    load_solar_data,
    load_chargers_data,
    load_bess_data,
    load_mall_demand_data
)
# Idéntico a SAC y PPO
```

### Validación de datos:
Todos los agentes validan contra las mismas rutas en [data_loader.py](src/citylearnv2/dataset_builder/data_loader.py):
- Solar: `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv`
- Chargers: `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`
- BESS: `data/oe2/bess/bess_ano_2024.csv`
- Mall: `data/oe2/demandamallkwh/demandamallhorakwh.csv`

---

## ✅ Confirmación de Sincronización

Desde el log de entrenamiento (2026-02-14 08:40:02):
```
✅ SOLAR:     8,292,514 kWh/año (8,760h)
✅ CHARGERS:  2,463,312 kWh/año (38 tomas)
✅ BESS:      1,700 kWh kapacidad (SOC: 48.1% promedio)
✅ MALL:     12,368,653 kWh/año (promedio 1,411.9 kW/h)
✅ ESCENARIOS: 19 cargadores, 38 tomas, 1,129 kWh/día
```

**Conclusión:** Todos los datos están sincronizados y usados por:
- ✅ SAC
- ✅ PPO (entrenando)
- ✅ A2C

---

## 🚀 Próximos Pasos

1. **PPO Training en progreso**: Monitorear SOC contours en logs
2. **SAC & A2C**: Pueden entrenarse con los mismos datos cuando sea necesario
3. **Comparación de resultados**: Los tres agentes usan datos idénticos → sólo diferencia es arquitectura RL

---

**Última actualización:** 2026-02-14 08:40:02  
**Estado de datos:** ✅ SINCRONIZADO (8,760 horas cada uno)
