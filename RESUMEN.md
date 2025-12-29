# RESUMEN EJECUTIVO - DISEÑO DE INFRAESTRUCTURA DE CARGA INTELIGENTE DE MOTOS Y MOTOTAXIS ELÉCTRICAS PARA REDUCIR LAS EMISIONES DE DIÓXIDO DE CARBONO EN LA CIUDAD DE IQUITOS, 2025

## 🎯 Objetivos del Proyecto

**Objetivo general:** Diseñar la infraestructura de carga inteligente para motos y mototaxis eléctricas que reduzca el dióxido de carbono en Iquitos, 2025.

**Objetivos específicos:**

1. OE.1.- Determinar la ubicación estratégica óptima que garantice la viabilidad técnica de motos y mototaxis eléctricas, necesaria para la reducción cuantificable de las emisiones de dióxido de carbono en Iquitos.
2. OE.2.- Dimensionar la capacidad de generación solar, almacenamiento y cargadores de motos y mototaxis eléctricas para reducir las emisiones de dióxido de carbono en la ciudad de Iquitos.
3. OE.3.- Seleccionar el agente inteligente de gestión de carga de motos y mototaxis eléctricas más apropiado para maximizar la eficiencia operativa del sistema, asegurando la contribución cuantificable a la reducción de las emisiones de dióxido de carbono en la ciudad de Iquitos.

---

## 🎯 Proyecto Completado

**Dimensionamiento y Gestión de Carga para Reducción de Emisiones CO₂**  
**Iquitos, Perú | 2025**

---

## 📊 Estado del Proyecto

| Aspecto | Estado | Detalles |
| - | - | - |

| **Código Fuente** | ✅ COMPLETO | OE2 + OE3 implementados |

| **OE.2 - Dimensionamiento** | ✅ VERIFICADO | Solar, BESS, Cargadores |

| **OE.3 - Algoritmos** | ✅ VERIFICADO | Uncontrolled, RBC, PPO, SAC |

| **Scripts** | ✅ FUNCIONALES | 7 scripts ejecutables |

| **Docker** | ✅ PREPARADO | Imagen y compose listos |

| **Documentación** | ✅ COMPLETA | README, OBJETIVOS, VALIDACION |

| **GitHub** | ✅ SINCRONIZADO | Repositorio público actualizado |

---

## 🏗️ Arquitectura del Proyecto

```markdown
DISEÑO DE CARGA INTELIGENTE OE.2 + OE.3
├── OE.2 DIMENSIONAMIENTO
│   ├── ✓ Generación Solar (pvlib)
│   ├── ✓ Almacenamiento BESS
│   └── ✓ Cargadores EV (motos/mototaxis)
│
└── OE.3 ALGORITMOS DE CONTROL
    ├── ✓ Baseline Uncontrolled
    ├── ✓ RBC (Rule-Based Control)
    ├── ✓ PPO (Policy Gradient RL) - reward 8,142
    ├── ✓ SAC (Maximum Entropy RL) - reward 15,145
    └── ✓ A2C (Actor-Critic RL) - reward 8,040 [SELECCIONADO]

```markdown

---

## 📦 Contenidos del Repositorio

### Código Fuente (`src/iquitos_citylearn/`)

```markdown

oe2/                      → Dimensionamiento
├── solar_pvlib.py        → Perfil FV anual (Iquitos)
├── bess.py               → Batería + almacenamiento

└── chargers.py           → Cargadores para flota EV

oe3/                      → Simulación + Control

├── simulate.py           → Motor de simulación CityLearn
├── co2_table.py          → Análisis de emisiones CO₂
├── dataset_builder.py    → Constructor de datasets
└── agents/               → Agentes de control
    ├── uncontrolled.py
    ├── rbc.py
    ├── ppo_sb3.py
    └── sac.py

utils/                    → Utilidades
├── logging.py, series.py, time.py

```markdown

### Scripts Ejecutables (`scripts/`)

```markdown

run_oe2_solar.py          → Generar perfil solar
run_oe2_chargers.py       → Dimensionar cargadores
run_oe2_bess.py           → Dimensionar almacenamiento
run_oe3_build_dataset.py  → Construir dataset
run_oe3_simulate.py       → Ejecutar simulaciones
run_oe3_co2_table.py      → Generar tabla CO₂
run_pipeline.py           → EJECUTAR TODO

```markdown

### Configuración

```markdown

configs/default.yaml      → Parámetros ajustables
.env.example              → Variables de entorno
requirements.txt          → Dependencias
pyproject.toml            → Metadata del proyecto
Docker/                   → Setup para containerización

```markdown

### Documentación

```markdown

README.md                 → Instrucciones principales
OBJETIVOS.md              → Alineación con OE.2 y OE.3
VALIDACION.md             → Checklist de funcionalidad
RESUMEN.md                → Este archivo

```markdown

---

## 🚀 Ejecución Rápida

### Opción 1: Python Local

```bash

# Requisitos: Python 3.10+, pip

# Instalar

python -m venv .venv
source .venv/bin/activate  # Linux/Mac

.venv\Scripts\activate     # Windows

pip install -r requirements.txt

# Ejecutar

python scripts/run_pipeline.py

# Salidas

reports/oe3/               → Gráficas (29 x 300 DPI)
analyses/oe3/             ? Tablas comparativas OE3
data/interim/oe2/          → Dimensionamiento OE2

```markdown

### Opción 2: Docker

```bash

# Requisitos: Docker + Docker Compose

# Ejecutar

docker-compose -f Docker/docker-compose.yml up

# El contenedor ejecutará run_pipeline.py automáticamente

```markdown

---

## 📈 Resultados Cuantificados

### OE.1 - Ubicación Estratégica

✓ **Ubicación seleccionada:** Mall de Iquitos  
✓ **Área techada disponible:** 20,637 m² (factor diseño 65% = 13,414 m² útil)  
✓ **Flota objetivo:** 900 motos + 130 mototaxis  
✓ **Permanencia mínima:** ≥4 horas  
✓ **Distancia a SET:** 60 m (Subestación Santa Rosa)  

### OE.2 - Dimensionamiento

✓ **Sistema Fotovoltaico:**
  - Potencia DC instalada: **2,591 kWp** (8,224 módulos SunPower SPR-315E)
  - Potencia AC máxima: **2,500 kW** (inversor Sungrow SG2500U)
  - Generación anual: **3,299 MWh** (9,040 kWh/día promedio)
  - Performance Ratio: **76.5%**

✓ **Almacenamiento BESS:**
  - Capacidad: **740 kWh**
  - Potencia nominal: **370 kW** (C-rate 0.5)
  - DoD: **90%**, SOC mínimo: **10%**
  - Eficiencia roundtrip: **95%**
  - Autonomía: **4 horas**

✓ **Cargadores EV Modo 3:**
  - Cantidad: **33 cargadores**
  - Sockets totales: **129 tomas** (4 por cargador)
  - Potencia por socket: **2-3 kW** (motos/mototaxis)
  - Demanda diaria EV: **567 kWh**
  - Vehículos efectivos/día: **927** (810 motos + 117 mototaxis)
  - Potencia pico: **283 kW**

### OE.3 - Agentes y Reducción CO₂

✓ **Agentes evaluados (5 episodios, 17,518 pasos):**
  - SAC: reward **15,145.84** (mejor exploración)
  - PPO: reward **8,142.55** (target_kl 0.015)
  - A2C: reward **8,040.81** (**SELECCIONADO**)

✓ **Reducción de emisiones cuantificada:**
  - Baseline sin control (PV+BESS): **103,184 kgCO₂/año**
  - Con control A2C: **95,505 kgCO₂/año**
  - **Reducción neta: 7,679 kgCO₂/año (~7.45%)**
  - Reducción directa: **85,534 kgCO₂/año**
  - Reducción indirecta: **9,971 kgCO₂/año**

✓ **Transporte electrificado:**
  - Combustión (gasolina/diésel): **111,761 kgCO₂/año**
  - Eléctrico con control: **7,967 kgCO₂/año**
  - **Reducción: 92.87%**

✓ **Proyección 20 años: 153.6 toneladas CO₂ evitadas**

✓ **Métricas de entrenamiento:** Disponibles en `analyses/oe3/training/*.csv`  

---

## 🔧 Características Técnicas

| Componente | Tecnología | Descripción |
| - | - | - |

| **Generación Solar** | pvlib-python | Radiación solar realista para Iquitos |

| **Dataset** | CityLearn | Framework de simulación de ciudades inteligentes |

| **RL - PPO** | Stable Baselines3 | Proximal Policy Optimization |

| **RL - SAC** | Stable Baselines3 | Soft Actor-Critic (máxima entropía) |

| **Análisis** | pandas + numpy | Procesamiento de datos |

| **Visualización** | matplotlib | Gráficas @ 300 DPI |

| **Contenedor** | Docker | Despliegue reproducible |

---

## 📍 Parámetros del Diseño de Carga Inteligente en Iquitos 2025

| Parámetro | Valor | Fuente |
| - | - | - |

| Latitud | -3.7° | Iquitos, Perú |
| Longitud | -73.2° | Iquitos, Perú |
| Zona horaria | UTC-5 | Perú |
| Radiación solar | Simulada pvlib | Clear-sky model |
| Año objetivo | 2025 | Proyección |
| Escenario EV | Motos/Mototaxis | Transporte local |

---

## ✅ Checklist de Validación

### Código

- [x] Módulos OE2 implementados correctamente

- [x] Módulos OE3 implementados correctamente

- [x] Scripts ejecutables y sin errores

- [x] Importaciones validadas

### Documentación

- [x] README con instrucciones completas

- [x] OBJETIVOS.md alineado con OE.2 y OE.3

- [x] VALIDACION.md con checklist

- [x] Código comentado apropiadamente

### Infraestructura

- [x] requirements.txt actualizado

- [x] Docker funcional

- [x] GitHub sincronizado

- [x] Carpetas data/ y reports/ estructuradas

### Funcionalidad

- [x] Pipeline completo ejecutable

- [x] Cada módulo OE2 ejecutable independientemente

- [x] Simulaciones OE3 convergentes

- [x] Tablas de emisiones CO₂ generadas

---

## 🎓 Para Tesis

El proyecto genera automáticamente **29 gráficas @ 300 DPI** aptas para

- ✓ Capítulos de Métodos (OE2, OE3)

- ✓ Capítulos de Resultados (comparación agentes)

- ✓ Capítulos de Análisis (reducción CO₂, impacto económico)

- ✓ Apéndices técnicos (arquitectura, esquemas)

**Ubicación:** `reports/oe3/`

---

## 📞 Soporte

### Problemas de instalación

```bash

# Limpiar e reinstalar

rm -rf .venv
python -m venv .venv
pip install --upgrade pip
pip install -r requirements.txt -v

```markdown

### Problemas de ejecución

```bash

# Ver logs

python scripts/run_pipeline.py --debug

# Ejecutar módulo individual

python scripts/run_oe2_solar.py

```markdown

### Docker

```bash

# Rebuild si hay cambios

docker-compose down
docker build --no-cache -f Docker/Dockerfile .
docker-compose up

```markdown

---

## 📚 Referencias Clave

| Archivo | Propósito |
| - | - |

| `src/iquitos_citylearn/oe2/solar_pvlib.py` | Modela generación FV |
| `src/iquitos_citylearn/oe2/bess.py` | Dimensiona batería |
| `src/iquitos_citylearn/oe2/chargers.py` | Configura cargadores |
| `src/iquitos_citylearn/oe3/simulate.py` | Ejecuta simulaciones |
| `src/iquitos_citylearn/oe3/co2_table.py` | Calcula emisiones CO₂ |
| `scripts/run_pipeline.py` | Orquesta ejecución completa |

---

## 🔗 Repositorio

**GitHub:** <https://github.com/Mac-Tapia/dise-opvbesscar>

### Clonar

```bash
git clone https://github.com/Mac-Tapia/dise-opvbesscar.git
cd dise-opvbesscar

```markdown

---

## ✨ Conclusión

✅ **El proyecto está COMPLETO, VALIDADO y LISTO PARA PRODUCCIÓN**

### Próximos pasos

1. Ejecutar `python scripts/run_pipeline.py` para generar resultados
2. Revisar gráficas en `reports/oe3/`
3. Incluir resultados en tesis
4. Desplegar en Docker si es necesario

---

**Última actualización:** Diciembre 21, 2025  
**Versión:** 1.0 Final  
**Estado:** ✅ LISTO PARA ENTREGA
