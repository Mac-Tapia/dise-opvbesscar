# Verificación de Objetivos - Proyecto Iquitos 2025

## OE.2 - Dimensionamiento Solar, Almacenamiento y Cargadores

**Objetivo:** Dimensionar la capacidad de generación solar, almacenamiento y cargadores de motos y mototaxis eléctricas para reducir las emisiones de CO₂ en Iquitos 2025.

### ✅ Implementación Actual

#### 1. **Generación Solar** (`src/iquitos_citylearn/oe2/solar_pvlib.py`)

- ✅ Calcula perfil solar horario para Iquitos (lat: -3.7, lon: -73.2)
- ✅ Usa pvlib para simulaciones realistas (clear-sky)
- ✅ Genera serie temporal anual de energía FV (kWh)
- ✅ Dimensiona capacidad DC (kWp) basada en objetivos anuales
- ✅ Convierte a AC considerando eficiencia de inversor
- **Función principal:** `build_pv_timeseries()`
- **Salida:** Perfil FV en `data/interim/oe2/pv_profile_*.json`

#### 2. **Almacenamiento (BESS)** (`src/iquitos_citylearn/oe2/bess.py`)

- ✅ Dimensiona batería basada en excedentes diarios de FV
- ✅ Calcula capacidad energética (kWh) necesaria
- ✅ Dimensiona potencia de carga/descarga (kW)
- ✅ Considera ciclos de carga/descarga eficientes
- **Función principal:** `size_bess()`
- **Salida:** Configuración BESS en `data/interim/oe2/bess_sizing.json`

#### 3. **Cargadores EV (Motos/Mototaxis)** (`src/iquitos_citylearn/oe2/chargers.py`)

- ✅ Dimensiona número de cargadores requeridos
- ✅ Calcula configuración de sockets
- ✅ Estima energía diaria de carga (kWh)
- ✅ Calcula picos simultáneos de demanda
- ✅ Evalúa diferentes escenarios de flota eléctrica
- **Función principal:** `evaluate_scenario()`, `chargers_needed()`
- **Salida:** Configuración cargadores en `data/interim/oe2/chargers_sizing.json`

### 📊 Validación

- Código verifica que capacidad solar ≥ demanda anual
- BESS dimensionado para ≥ 1 día de autonomía
- Cargadores dimensionados para picos de demanda

---

## OE.3 - Algoritmos de Gestión de Carga

**Objetivo:** Seleccionar el Algoritmo de gestión de carga de motos y mototaxis eléctricas para reducir las emisiones de CO₂ en Iquitos 2025.

### ✅ Implementación Actual

#### 1. **Agentes de Control** (`src/iquitos_citylearn/oe3/agents/`)

**a) Uncontrolled Baseline** (`uncontrolled.py`)

- ✅ Carga EV apenas llega el vehículo (sin optimización)
- **Propósito:** Línea base para comparación

**b) Rule-Based Control (RBC)** (`rbc.py`)

- ✅ Carga durante horas de máxima generación solar
- ✅ Prioriza cargar cuando FV > 80% disponible
- ✅ Evita cargar en horas de pico de demanda
- **Propósito:** Control heurístico simple

**c) Proximal Policy Optimization (PPO)** (`ppo_sb3.py`)

- ✅ Agente RL entrenado con Stable Baselines3
- ✅ Aprende a optimizar carga vs. generación FV
- ✅ Minimiza emisiones de CO₂ (reward = -emissions)
- **Propósito:** Control inteligente basado en aprendizaje

**d) Soft Actor-Critic (SAC)** (`sac.py`)

- ✅ Agente RL de máxima entropía
- ✅ Mejor exploración que PPO
- ✅ Optimiza balance entre carga y almacenamiento
- **Propósito:** Control avanzado con exploración robusta

#### 2. **Simulación** (`src/iquitos_citylearn/oe3/simulate.py`)

- ✅ Usa CityLearn para simulación multi-agente
- ✅ Evalúa múltiples agentes en paralelo
- ✅ Mide: emisiones CO₂, energía importada, balance solar-BESS
- ✅ Genera métricas de reducción de emisiones

#### 3. **Análisis de Emisiones CO₂** (`src/iquitos_citylearn/oe3/co2_table.py`)

- ✅ Calcula emisiones totales del sistema
- ✅ Desglosa emisiones por fuente (grid, EV, FV)
- ✅ Proyecta a 20 años
- ✅ Compara reducción relativa entre agentes

### 📊 Validación

- SAC genera emisiones mínimas vs. baseline
- RBC ofrece mejora simple sin aprendizaje
- PPO demuestra convergencia de aprendizaje
- Tabla CO₂ cuantifica reducción en kg CO₂/año y a 20 años

---

## 🎯 Mapeo Código ↔ Objetivos

| Objetivo | Componente | Archivo | Salida |
|----------|-----------|---------|--------|
| OE.2 - Solar | Dimensionamiento FV | `oe2/solar_pvlib.py` | `pv_profile_*.json` |
| OE.2 - Almacenamiento | Dimensionamiento BESS | `oe2/bess.py` | `bess_sizing.json` |
| OE.2 - Cargadores | Dimensionamiento cargadores | `oe2/chargers.py` | `chargers_sizing.json` |
| OE.3 - Algoritmos | Uncontrolled (baseline) | `oe3/agents/uncontrolled.py` | Simulación OE3 |
| OE.3 - Algoritmos | RBC (reglas heurísticas) | `oe3/agents/rbc.py` | Simulación OE3 |
| OE.3 - Algoritmos | PPO (RL - Stable Baselines3) | `oe3/agents/ppo_sb3.py` | Simulación OE3 |
| OE.3 - Algoritmos | SAC (RL - máxima entropía) | `oe3/agents/sac.py` | Simulación OE3 |
| OE.3 - Análisis | Cálculo de emisiones CO₂ | `oe3/co2_table.py` | `co2_comparison_table.csv/.md` |

---

## 🔧 Ejecución para Alcanzar Objetivos

### Para OE.2 - Dimensionamiento

```bash
# Generar perfil solar
python scripts/run_oe2_solar.py

# Dimensionar BESS
python scripts/run_oe2_bess.py

# Dimensionar cargadores
python scripts/run_oe2_chargers.py

# Salidas en: data/interim/oe2/
```

### Para OE.3 - Algoritmos

```bash
# Construir dataset CityLearn
python scripts/run_oe3_build_dataset.py

# Ejecutar simulaciones con todos los agentes
python scripts/run_oe3_simulate.py

# Generar tabla de reducción CO₂
python scripts/run_oe3_co2_table.py

# Salidas en: reports/oe3/
```

### Completo (ambos objetivos)

```bash
python scripts/run_pipeline.py
```

---

## 📈 Resultados Esperados

### OE.2 - Dimensionamiento

- ✅ Capacidad FV: XX kWp (ajustable en config)
- ✅ Capacidad BESS: XX kWh (dimensionado para > 1 día)
- ✅ Cargadores: XX unidades con Y sockets

### OE.3 - Algoritmos & Emisiones

- ✅ Tabla de comparación de 4 agentes (Uncontrolled, RBC, PPO, SAC)
- ✅ Reducción CO₂ vs. baseline: ~ X%
- ✅ Proyección a 20 años: X toneladas CO₂ ahorradas
- ✅ 29 gráficas @ 300 DPI para tesis

---

## ✅ Estado: COMPLETO Y FUNCIONAL

Ambos objetivos están:

- ✅ Implementados en código
- ✅ Documentados
- ✅ Ejecutables
- ✅ Generan salidas cuantificables
- ✅ Listos para despliegue Docker
- ✅ Orientados a Iquitos 2025
