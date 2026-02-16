# 📚 Catálogo de Datasets - Referencia Rápida

**Última actualización**: 2026-02-14  
**Status**: ✅ Completo y validado

---

## 1. Cargar Datasets Automáticamente

### Opción 1: Desde Catálogo (Recomendado)
```python
from src.dataset_builder_citylearn.catalog_datasets import get_dataset
import pandas as pd

# Cargar Solar
solar_info = get_dataset("SOLAR_v2")
solar_df = pd.read_csv(solar_info.path)
print(f"Solar: {len(solar_df)} filas × {len(solar_df.columns)} columnas")

# Cargar Chargers
chargers_info = get_dataset("CHARGERS_v2")
chargers_df = pd.read_csv(chargers_info.path)

# Cargar BESS
bess_info = get_dataset("BESS_v1")
bess_df = pd.read_csv(bess_info.path)
```

### Opción 2: Rutas Directas (Si necesitas control total)
```python
import pandas as pd
from pathlib import Path

DATASETS_PATH = Path("data/interim/oe2")

solar_df = pd.read_csv(DATASETS_PATH / "solar/pv_generation_citylearn_enhanced_v2.csv")
chargers_df = pd.read_csv(DATASETS_PATH / "chargers/chargers_ev_ano_2024_enriched_v2.csv")
bess_df = pd.read_csv(DATASETS_PATH / "bess/bess_ano_2024.csv")
```

---

## 2. Información de Datasets

### A. SOLAR_v2 (Energía Solar)
| Campo | Valor |
|-------|-------|
| **Filas** | 8,760 (1 año × 365 días × 24 horas) |
| **Columnas Originales** | 10 |
| **Columnas Nuevas ⭐** | 5 |
| **Total Columnas** | 15 |
| **Tamaño Archivo** | 1.50 MB |
| **Ruta** | `data/interim/oe2/solar/pv_generation_citylearn_enhanced_v2.csv` |
| **Periodo** | 2024-01-01 a 2024-12-31 |
| **Resolución** | Horaria (1 hora/fila) |

#### Columnas Nuevas (⭐)
1. `energia_suministrada_al_bess_kwh` - Energía al almacenamiento (9.5% del total)
2. `energia_suministrada_al_ev_kwh` - Energía a cargadores EV (3.9% del total)
3. `energia_suministrada_al_mall_kwh` - Energía al mall/carga base (72.3% del total)
4. `energia_suministrada_a_red_kwh` - Energía exportada a red (21.8% del total)
5. `reduccion_indirecta_co2_kg_total` - CO₂ ahorrado por desplazamiento solar (3,749 ton/año)

#### Estadísticas Clave
- **Generación Total**: 8,292,514 kWh/año
- **CO₂ Evitado**: 3,746,993 kg/año (3,747 tons)
- **Factor de Conversión**: 0.4521 kg CO₂/kWh (desplazamiento diesel 100%)

---

### B. CHARGERS_v2 (Cargadores EV)
| Campo | Valor |
|-------|-------|
| **Filas** | 8,760 (1 año × 365 días × 24 horas) |
| **Columnas Originales** | 352 |
| **Columnas Nuevas ⭐** | 5 |
| **Total Columnas** | 357 |
| **Tamaño Archivo** | 16.05 MB |
| **Ruta** | `data/interim/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv` |
| **Infraestructura** | 19 cargadores × 2 sockets = 38 sockets controlables |
| **Potencia por Socket** | 7.4 kW (Mode 3, 32A @ 230V) |
| **Potencia Instalada** | 281.2 kW |

#### Columnas Nuevas (⭐)
1. `cantidad_motos_cargadas` - Vehículos motos en carga (rango: 0-26)
2. `cantidad_mototaxis_cargadas` - Vehículos mototaxis en carga (rango: 0-8)
3. `reduccion_directa_co2_motos_kg` - CO₂ de sustitución motos (gasolina→eléctrico)
4. `reduccion_directa_co2_mototaxis_kg` - CO₂ de sustitución mototaxis (diésel→eléctrico)
5. `reduccion_directa_co2_total_kg` - Suma total CO₂ directo (rango: 0-272 kg/h)

#### Metodología CO₂
- **Motos**: 6.08 kg CO₂/carga
  - Consumo: 2.86 L/100km gasolina
  - Emisiones: 2.31 kg CO₂/L
  
- **Mototaxis**: 14.28 kg CO₂/carga
  - Consumo: 3.6 L/100km diésel
  - Emisiones: 2.68 kg CO₂/L

#### Estadísticas Clave
- **Motos**: 78,280 veh-h/año → 475,791 kg CO₂
- **Mototaxis**: 20,532 veh-h/año → 293,177 kg CO₂
- **Total Directo**: 98,812 veh-h/año → 768,968 kg CO₂ (769 tons)
- **Equivalencias**: 36,617 árboles, 167,170 km auto gasolina, 96 personas/año

---

### C. BESS_v1 (Almacenamiento Energético)
| Campo | Valor |
|-------|-------|
| **Filas** | 8,760 (1 año × 365 días × 24 horas) |
| **Columnas** | 25 (todas originales) |
| **Tamaño Archivo** | 2.50 MB |
| **Ruta** | `data/interim/oe2/bess/bess_ano_2024.csv` |
| **Capacidad Máxima** | 1,700 kWh |
| **Tipo** | Batería de ión de litio (LiFePO₄) |
| **Función** | Almacenar exceso solar, cubrir picos de demanda |

#### Descripción
- **Controlada por**: Agentes RL (SAC, PPO, A2C) en OE3
- **Parámetros**: Estado de carga (%), flujos de carga/descarga
- **Coordinación**: Distribuye energía solar entre BESS, EV, Mall, Red

---

## 3. Alineamiento Temporal

Todos los datasets están **perfectamente alineados**:

```
Timestamp                 SOLAR        CHARGERS        BESS
2024-01-01 00:00:00      ✓ Gen. 0 kW  ✓ 5 motos      ✓ SOC 50%
2024-01-01 01:00:00      ✓ Gen. 0 kW  ✓ 0 carga      ✓ SOC 49%
...                       ...          ...             ...
2024-12-31 23:00:00      ✓ Gen. 0 kW  ✓ 12 motos     ✓ SOC 48%
```

- **Resolución**: 1 hora (3,600 segundos/timestep)
- **Período**: 2024-01-01 a 2024-12-31 (365 días)
- **Total Filas**: 8,760 (365 × 24)
- **Alineamiento**: Índice "hora" común entre todos

---

## 4. Validación de Integridad

### Chequeo Manual
```python
from src.dataset_builder_citylearn.catalog_datasets import validate_datasets

# Valida que todos los archivos existan y tengan las columnas correctas
results = validate_datasets()
if results["all_valid"]:
    print("✅ Todos los datasets son válidos y accesibles")
else:
    print("❌ Problema detectado:", results["errors"])
```

### Dimensiones Esperadas
```python
import pandas as pd

datasets = {
    "SOLAR": ("data/interim/oe2/solar/pv_generation_citylearn_enhanced_v2.csv", (8760, 15)),
    "CHARGERS": ("data/interim/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv", (8760, 357)),
    "BESS": ("data/interim/oe2/bess/bess_ano_2024.csv", (8760, 25)),
}

for name, (path, expected_shape) in datasets.items():
    df = pd.read_csv(path)
    assert df.shape == expected_shape, f"{name} shape mismatch: {df.shape} != {expected_shape}"
    print(f"✓ {name}: {df.shape[0]:,} filas × {df.shape[1]} columnas")
```

---

## 5. Uso en OE3 (Agentes RL)

### Inicialización del Ambiente
```python
import pandas as pd
from src.dataset_builder_citylearn.catalog_datasets import DATASETS_CATALOG
from gymnasium import Env

class CityLearnEnv(Env):
    def __init__(self):
        # Cargar datasets desde catálogo
        self.solar = pd.read_csv(DATASETS_CATALOG["SOLAR_v2"].path)
        self.chargers = pd.read_csv(DATASETS_CATALOG["CHARGERS_v2"].path)
        self.bess = pd.read_csv(DATASETS_CATALOG["BESS_v1"].path)
        
        # Observation space: 
        # - Solar: 15 observables (irradiancia, generación, distribución energética, CO₂)
        # - Chargers: 38 × 3 (ocupación, potencia, CO₂ directo)
        # - BESS: 3 (SOC, carga, descarga)
        # - Time: 6 (hora, mes, día_semana, etc.)
        # Total: 394-dim
        
        self.observation_dim = 394  # 15 + (38×3) + 3 + 6
        
        # Action space:
        # - Continuous [0,1]: 1 BESS + 38 sockets EV = 39 acciones
        self.action_dim = 39
```

### Observables Nuevas (⭐)
```python
# Desde SOLAR (5 columnas nuevas):
solar_to_bess = self.solar["energia_suministrada_al_bess_kwh"]
solar_to_ev = self.solar["energia_suministrada_al_ev_kwh"]
solar_to_mall = self.solar["energia_suministrada_al_mall_kwh"]
solar_to_grid = self.solar["energia_suministrada_a_red_kwh"]
solar_co2_avoided = self.solar["reduccion_indirecta_co2_kg_total"]

# Desde CHARGERS (5 columnas nuevas):
motos_charging = self.chargers["cantidad_motos_cargadas"]
taxis_charging = self.chargers["cantidad_mototaxis_cargadas"]
co2_motos = self.chargers["reduccion_directa_co2_motos_kg"]
co2_taxis = self.chargers["reduccion_directa_co2_mototaxis_kg"]
co2_total = self.chargers["reduccion_directa_co2_total_kg"]
```

### Función de Recompensa Multi-Objetivo
```python
def compute_reward(self, t):
    """Recompensa ponderada para minimizar CO₂ y maximizar eficiencia."""
    
    # CO₂ grid (desplazamiento diesel): 0.4521 kg/kWh
    grid_import = self.current_state["grid_import_kw"]  # kW en hora t
    co2_grid = grid_import * 0.4521 * (1/1000)  # Escalar a ton/h
    
    # CO₂ solar directo: Ya en conjunto CHARGERS + SOLAR
    co2_direct = self.solar["reduccion_indirecta_co2_kg_total"].iloc[t]
    
    # Componentes:
    reward = (
        + 0.50 * (100 - co2_grid)           # Minimizar import grid (CO₂ grid)
        + 0.20 * co2_direct                 # Maximizar solar directo
        + 0.15 * self.charge_completion     # EV completaron carga
        + 0.10 * self.grid_stability        # Suavidad de rampas
        + 0.05 * (-self.peak_shaving)       # Peak shaving reward
    )
    
    return reward
```

---

## 6. Estadísticas Consolidadas

### Resumen Total
```
Dataset                    Filas    Cols  Nuevas  Tamaño   CO₂ Evitado/Directo
─────────────────────────────────────────────────────────────────────────────────
SOLAR_v2                   8,760    15      5    1.50 MB   3,747 ton (indirecto)
CHARGERS_v2                8,760    357     5   16.05 MB   769 ton (directo)
BESS_v1                    8,760    25      0    2.50 MB   (coordinador)
─────────────────────────────────────────────────────────────────────────────────
TOTAL                     26,280    397    10   20.05 MB   4,516 ton/año
```

### CO₂ por Fuente
| Fuente | ton/año | % | Factor |
|--------|---------|---|--------|
| Solar Indirecto | 3,747 | 83.0% | 0.4521 kg/kWh |
| Motos Directo | 476 | 10.5% | 6.08 kg/carga |
| Mototaxis Directo | 293 | 6.5% | 14.28 kg/carga |
| **TOTAL** | **4,516** | **100%** | - |

---

## 7. Próximos Pasos

### ✅ Completado en OE2
- [x] Solar enriched con distribución energética y CO₂ indirecto
- [x] Chargers enriquecido con cantidades y CO₂ directo
- [x] BESS base (coordinador de flujos)
- [x] Catálogo centralizado de todos datasets
- [x] Validación de integridad

### ⏳ Siguiente: OE3 (Agentes RL)
- [ ] Inicializar CityLearn v2 con datasets enriquecidos
- [ ] Configurar observation space (394-dim)
- [ ] Configurar action space (39-dim: 1 BESS + 38 sockets)
- [ ] Implementar reward function multi-objetivo
- [ ] Entrenar SAC, PPO, A2C agents
- [ ] Evaluar CO₂ minimization vs baselines

---

## 8. Acceso Rápido a Rutas

```python
from pathlib import Path

# Base paths
OE2_PATH = Path("data/interim/oe2")
SOLAR_PATH = OE2_PATH / "solar/pv_generation_citylearn_enhanced_v2.csv"
CHARGERS_PATH = OE2_PATH / "chargers/chargers_ev_ano_2024_enriched_v2.csv"
BESS_PATH = OE2_PATH / "bess/bess_ano_2024.csv"

# Load
import pandas as pd
solar = pd.read_csv(SOLAR_PATH)
chargers = pd.read_csv(CHARGERS_PATH)
bess = pd.read_csv(BESS_PATH)
```

---

**Preguntas Frecuentes**:

**P: ¿Por qué hay 5 columnas nuevas en CHARGERS pero solo 2 parecen de "cantidad"?**  
R: Las 5 son: 2 del tipo "cantidad" (motos/mototaxis) + 3 del tipo CO₂ (motos, taxis, total). Esto permite tracking granular: "¿cuántos vehículos?" y "¿cuánto CO₂ evitado?"

**P: ¿Cuál es la diferencia entre CO₂ "indirecto" de SOLAR y CO₂ "directo" de CHARGERS?**  
R: 
- **Indirecto (SOLAR)**: Diésel que NO se usa en red porque hay solar (3,747 ton/año)
- **Directo (CHARGERS)**: Gasolina/diésel que NO se usa porque motos/taxis cargan con electricidad (769 ton/año)

**P: ¿Cómo uso esto en mi agente RL?**  
R: Ver sección 5 (Uso en OE3). Importa dataset con `get_dataset()`, pasa a `CityLearnEnv`, accede con `.iloc[timestep]`

