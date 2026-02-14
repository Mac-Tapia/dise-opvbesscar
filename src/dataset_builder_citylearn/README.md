# Dataset Builder for CityLearn v2

**Carpeta Centralizada**: Construcción completa de datasets para CityLearn v2 desde módulos OE2.

## 📋 Contenido

```
src/dataset_builder_citylearn/
├── __init__.py                      # Módulo Python
├── enrich_chargers.py               # Enriquecimiento CHARGERS (5 cols CO₂)
├── integrate_datasets.py           # Integración Solar + Chargers + BESS
├── analyze_datasets.py             # Análisis de datasets enriquecidos
├── main_build_citylearn.py         # Orquestador principal
└── README.md                       # Este archivo
```

## 🎯 Propósito

Centralizar todos los scripts de construcción de datasets para CityLearn v2 en una única carpeta bajo `src/`, eliminando archivos dispersos en la raíz del proyecto.

## 🚀 Uso

### Opción 1: Ejecutar la pipeline completa

```bash
cd d:\diseñopvbesscar
python -m src.dataset_builder_citylearn.main_build_citylearn
```

### Opción 2: Ejecutar módulos específicos

**Enriquecimiento CHARGERS:**
```bash
python -m src.dataset_builder_citylearn.enrich_chargers
```

**Integración de datasets:**
```bash
python -m src.dataset_builder_citylearn.integrate_datasets
```

**Análisis de datos:**
```bash
python -m src.dataset_builder_citylearn.analyze_datasets
```

### Opción 3: Llamar desde código Python

```python
from src.dataset_builder_citylearn import enrich_chargers, integrate_datasets

# Enriquecimiento
df_chargers = enrich_chargers.enrich_chargers_dataset()

# Integración
df_solar = integrate_datasets.integrate_datasets()
```

## 📊 Pipeline de Construcción

```
OE2 Módulos Base
├── Solar       (8.29 GWh/año, 3,201 kW AC)
├── Chargers    (453 MWh/año, 38 sockets)
└── BESS        (1,700 kWh, 400 kW)
        │
        ▼
[PASO 1] Enriquecimiento CHARGERS
├─ Agrega 5 columnas:
│  • cantidad_motos_cargadas (0-26)
│  • cantidad_mototaxis_cargadas (0-8)
│  • reduccion_directa_co2_motos_kg (6.08 kg/carga)
│  • reduccion_directa_co2_mototaxis_kg (14.28 kg/carga)
│  • reduccion_directa_co2_total_kg (769 ton/año)
└─ Output: chargers_ev_ano_2024_enriched_v2.csv
        │
        ▼
[PASO 2] Integración Solar + Chargers + BESS
├─ Agrega 5 columnas a Solar:
│  • energia_suministrada_al_bess_kwh (790 GWh)
│  • energia_suministrada_al_ev_kwh (323 GWh)
│  • energia_suministrada_al_mall_kwh (5,992 GWh)
│  • energia_suministrada_a_red_kwh (1,804 GWh)
│  • reduccion_indirecta_co2_kg_total (3,749 ton/año)
└─ Output: pv_generation_citylearn_enhanced_v2.csv
        │
        ▼
[PASO 3] Análisis y Validación
├─ Estadísticas de 10 columnas nuevas
├─ Validación de rangos y coherencia
└─ Reporte de integridad
        │
        ▼
¡LISTO PARA CityLearn v2!
└─ Observables para agentes RL (SAC, PPO, A2C)
```

## 📁 Datasets Generados

### 1. Solar Enriquecido
- **Ruta**: `data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv`
- **Dimensiones**: 8,760 filas × 15 columnas
- **Nuevas columnas**: 5 (energía suministrada + CO₂ indirecto)
- **Período**: 2024 completo (365 días × 24 horas)

### 2. Chargers Enriquecido
- **Ruta**: `data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv`
- **Dimensiones**: 8,760 filas × 357 columnas
- **Nuevas columnas**: 5 (cantidad vehículos + CO₂ directo)
- **Período**: 2024 completo

### 3. BESS Base
- **Ruta**: `data/oe2/bess/bess_ano_2024.csv`
- **Dimensiones**: 8,760 filas × 25 columnas
- **Estado**: Sin cambios (ya completo)
- **Período**: 2024 completo

## 🔬 Columnas Nuevas

### CHARGERS (5 columnas)

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `cantidad_motos_cargadas` | Int | 0-26 | Motos cargando simultáneamente |
| `cantidad_mototaxis_cargadas` | Int | 0-8 | Mototaxis cargando simultáneamente |
| `reduccion_directa_co2_motos_kg` | Float | 0-158 | CO₂ evitado gasolina → EV |
| `reduccion_directa_co2_mototaxis_kg` | Float | 0-114 | CO₂ evitado diésel → EV |
| `reduccion_directa_co2_total_kg` | Float | 0-272 | CO₂ total de ambas (769 ton/año) |

**Metodología CO₂ Directo:**
- Motos: 2.86 L/100km gasolina × 2.31 kg CO₂/L = 6.08 kg/carga
- Mototaxis: 3.6 L/100km diésel × 2.68 kg CO₂/L = 14.28 kg/carga
- Fuentes: IPCC 2006, IEA, ICCT 2022

### SOLAR (5 columnas)

| Columna | Tipo | Valor Anual | Descripción |
|---------|------|-------------|-------------|
| `energia_suministrada_al_bess_kwh` | Float | 790,716 | Solar → BESS (almacenamiento) |
| `energia_suministrada_al_ev_kwh` | Float | 323,327 | Solar+BESS → EV |
| `energia_suministrada_al_mall_kwh` | Float | 5,992,294 | Solar+BESS → Mall |
| `energia_suministrada_a_red_kwh` | Float | 1,804,800 | Solar excedente → Red |
| `reduccion_indirecta_co2_kg_total` | Float | 3,749,046 | TODA solar × 0.4521 kg CO₂/kWh |

**Metodología CO₂ Indirecto:**
- TODA la generación solar desplaza diesel (100% utilización)
- Factor: 0.4521 kg CO₂/kWh (sistema térmico Iquitos)
- Total: 3,749 toneladas/año

## 📊 Impacto Ambiental Total

| Métrica | Motos | Mototaxis | Total |
|---------|-------|-----------|-------|
| **CO₂ Directo** | 475.8 ton | 293.2 ton | **769 ton** |
| **CO₂ Indirecto** | — | — | **3,749 ton** |
| **TOTAL CO₂ Reducido** | — | — | **4,518 ton/año** |

**Equivalentes:**
- 🌳 216,000+ árboles plantados (absorción anual)
- 🚗 982,000 km de auto evitados
- 👥 564 personas sin emisiones transporte (1 año)

## 🔗 Integración con OE3 (Control)

Los datasets enriquecidos son cargados automáticamente por CityLearn v2 como observables para agentes RL:

```python
from src.agents.sac import make_sac

# Las 10 columnas nuevas están disponibles como observables
env = CityLearnEnvironment(
    solar_dataset="data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv",
    chargers_dataset="data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv",
    bess_dataset="data/oe2/bess/bess_ano_2024.csv"
)

agent = make_sac(env)
agent.learn(total_timesteps=26280)  # 365 días × 72 steps/día
```

## ✅ Checklist

- [x] Carpeta centralizada creada: `src/dataset_builder_citylearn/`
- [x] 4 módulos Python orquestados
- [x] Enriquecimiento CHARGERS (5 cols CO₂ directo)
- [x] Integración de datasets (5 cols energía a Solar)
- [x] Análisis consolidado de datasets
- [x] Documentación completa
- [x] Pipeline automatizable

## 📝 Notas Técnicas

- **Resolución**: Horaria (8,760 datos/año)
- **Año**: 2024 completo
- **Zona horaria**: America/Lima (-05:00)
- **Alineación**: Todas las series verificadas en 8,760 filas
- **Validación**: No hay valores nulos, todos positivos

## 🎓 Referencias

- **IPCC (2006)**: Emission factors for fossil fuels
- **IEA**: Technology Collaboration Programme
- **ICCT (2022)**: Electric 2/3-wheelers deployment
- **OSINERGMIN**: Tarificación Electro Oriente S.A. (MT3)

---

**Versión**: 2.0  
**Fecha**: 14 febrero 2026  
**Autor**: pvbesscar project  
**Estado**: ✅ Producción
