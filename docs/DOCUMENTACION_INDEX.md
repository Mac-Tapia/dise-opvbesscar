# 📚 ÍNDICE CENTRAL DE DOCUMENTACIÓN

**Actualizado:** 17 Feb 2026  
**Status:** ✅ GUÍA ÚNICA DE NAVEGACIÓN  

---

## 🎯 COMIENZA AQUÍ

Este documento es tu **mapa único** de toda la documentación técnica del proyecto.

**¿Qué necesitas?**

- 🚀 [**Empezar rápido**](#empezar-rápido) → Nuevos desarrolladores
- 📊 [**Entender arquitectura**](#arquitectura) → Diseño del sistema
- 🤖 [**Entrenar agentes**](#entrenar-agentes) → RL training
- 📈 [**Analizar resultados**](#análisis-resultados) → Métricas y KPIs
- 🔧 [**Datos y datasets**](#datos-y-datasets) → Estructura de datos
- 📚 [**Referencias académicas**](#referencias-académicas) → Papers y teoría

---

## 🚀 EMPEZAR RÁPIDO

### Para Nuevo Developer (20 minutos)

| Documento | Lectura | Qué aprenderás |
|-----------|---------|---|
| [README.md](../README.md) | 10 min | Visión general, OE1/OE2/OE3 |
| [INSTALACION.md](#instalación) | 5 min | Setup del ambiente |
| [PRIMEROS_PASOS.md](#primeros-pasos) | 5 min | Tu primer entrenamiento |

### Para DevOps / Infraestructura

| Documento | Lectura | Qué aprenderás |
|-----------|---------|---|
| [requirements.txt](../requirements.txt) | 2 min | Dependencias Python |
| [Docker setup](#docker) | 5 min | Containerización |
| [Config files](../configs/) | 10 min | Configuración agentes |
| [Checkpoints](../checkpoints/) | 5 min | Manejo de modelos entrenados |

---

## 🏗️ ARQUITECTURA

### Visión General del Proyecto

```
pvbesscar: Optimización RL para EV Charging en Iquitos, Perú

    OE1: UBICACIÓN              OE2: DIMENSIONAMIENTO         OE3: CONTROL
    ┌──────────────────┐       ┌──────────────────────┐     ┌─────────────────┐
    │ Iquitos, Perú    │   →   │ 4,050 kWp solar      │  →  │ RL Agents:      │
    │ Grid aislado     │       │ 1,700 kWh BESS       │     │ - PPO ✅        │
    │ 0.45 kg CO₂/kWh  │       │ 38 sockets EV        │     │ - A2C ✅        │
    │                  │       │ 270 motos + 39 taxis │     │ - SAC           │
    └──────────────────┘       └──────────────────────┘     └─────────────────┘
                                       ↓
                            CityLearn v2 Environment
                            (8,760 timesteps/año)
                                       ↓
                              KPI: CO₂ Reducción
                            (Target: 62% vs baseline)
```

### Documentos de Arquitectura

| Doc | Propósito |
|-----|-----------|
| [ESPECIFICACION_CITYLEARN_v2.md](ESPECIFICACION_CITYLEARN_v2.md) | Dataset técnico (357 columnas) |
| [RUTAS_DATOS_FIJAS_v58.md](../src/dataset_builder_citylearn/RUTAS_DATOS_FIJAS_v58.md) | Single Source of Truth (SSOT) |
| [CityLearn Integration](#citylearn) | Cómo funcionan las observaciones/acciones |

---

## 🤖 ENTRENAR AGENTES

### Training Workflow

```
1. Preparar Datasets
   python prepare_datasets_all_agents.py

2. Seleccionar Agente
   PPO (recomendado)  → scripts/train/train_ppo_multiobjetivo.py
   A2C (rápido)       → scripts/train/train_a2c_multiobjetivo.py
   SAC (experimental) → scripts/train/train_sac_multiobjetivo.py

3. Entrenar
   python scripts/train/train_ppo_multiobjetivo.py --episodes 10

4. Evaluar
   python compare_agents_complete.py

5. Analizar
   Gráficas en: outputs/{ppo,a2c,sac}_training/
```

### Scripts de Entrenamiento

| Script | Agente | Duración | Recomendación |
|--------|--------|----------|---|
| [train_ppo_multiobjetivo.py](../scripts/train/train_ppo_multiobjetivo.py) | PPO | 4-5 min/ep | ✅ **USAR ESTE** |
| [train_a2c_multiobjetivo.py](../scripts/train/train_a2c_multiobjetivo.py) | A2C | 3-4 min/ep | ✅ Rápido |
| [train_sac_multiobjetivo.py](../scripts/train/train_sac_multiobjetivo.py) | SAC | 8-10 min/ep | ⚠️ Experimental |

### ¿PPO vs A2C vs SAC?

Consulta: [REFERENCIAS_ACADEMICAS_COMPLETAS.md](REFERENCIAS_ACADEMICAS_COMPLETAS.md)

**Resumido:**
- **PPO**: ✅ Mejor reward (+45%), estabilidad, constraints
- **A2C**: ✅ Entrenamiento rápido, on-policy
- **SAC**: ⚠️ Entropía → inestable en energía, constraints riesgosos

---

## 📈 ANÁLISIS RESULTADOS

### Scripts de Comparación

```bash
# Comparar 3 agentes (genera tablas y gráficas)
python compare_agents_complete.py

# Analizar PPO en detalle
python analyze_ppo_improvements.py

# Verificar consistencia (SOC tracking)
python scripts/validate_cross_agent_consistency.py
```

### Métricas Principales

| Métrica | Target | Unidad | Cálculo |
|---------|--------|--------|---------|
| **CO₂ Reducción** | -62% | kg/año | (baseline - agent) / baseline |
| **Solar Utilización** | 65% | % | pv_used / pv_available |
| **BESS Compliance** | 98% | % | horas con SOC ∈ [20,100] |
| **Reward Promedio** | > 0 | points | sum(rewards) / episodes |

### Salidas de Entrenamiento

```
outputs/
├── ppo_training/
│   ├── result_ppo.json           ← Métricas finales
│   ├── timeseries_ppo.csv        ← Datos por timestep
│   ├── trace_ppo.csv             ← Trazado detallado
│   └── ppo_dashboard.png         ← Visualización
├── a2c_training/
│   └── ...
└── sac_training/
    └── ...
```

### Gráficas Estándar

```python
# Generar gráficas de análisis
from src.utils import plot_training_metrics
plot_training_metrics('outputs/ppo_training/timeseries_ppo.csv')
```

---

## 📊 DATOS Y DATASETS

### Datasets Principales

| Dataset | Ubicación | Filas | Columnas | Status |
|---------|-----------|-------|----------|--------|
| **Solar PV** | `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv` | 8,760 | 2 | ✅ |
| **BESS** | `data/oe2/bess/bess_ano_2024.csv` | 8,760 | 6 | ✅ |
| **Chargers EV** | `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` | 8,760 | 357 | ✅ |
| **Mall Demand** | `data/oe2/demandamallkwh/demandamallhorakwh.csv` | 8,760 | 2 | ✅ |

### Especificaciones Técnicas

| Dataset | Doc | Detalles |
|---------|-----|----------|
| Chargers (EV) | [ESPECIFICACION_CITYLEARN_v2.md](ESPECIFICACION_CITYLEARN_v2.md) | 38 sockets, 357 cols, CO₂/tarifa |
| Solar, BESS, Demand | [RUTAS_DATOS_FIJAS_v58.md](../src/dataset_builder_citylearn/RUTAS_DATOS_FIJAS_v58.md) | Rutas SSOT, validación |

### Cargar Datasets

```python
import pandas as pd

# Solar
solar_df = pd.read_csv('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
print(f"Solar: {len(solar_df)} rows, {solar_df['power_w'].sum()/1e6:.1f} MWh/año")

# Chargers (con 357 columnas)
chargers_df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
print(f"Chargers: {len(chargers_df)} timesteps, {chargers_df['ev_demand_kwh'].sum():.0f} kWh/año")
```

---

## 📚 REFERENCIAS ACADÉMICAS

### Papers Clave

Comparación SAC vs PPO para sistemas energéticos: [REFERENCIAS_ACADEMICAS_COMPLETAS.md](REFERENCIAS_ACADEMICAS_COMPLETAS.md)

| Paper | Autores | Año | Hallazgo Principal |
|-------|---------|------|---|
| Deep RL for EMS in Microgrids | He et al. | 2020 | PPO +45% superior |
| Stability in Deep RL | Yang et al. | 2021 | SAC oscila 2-3x más |
| RL for BESS Operations | Li et al. | 2022 | PPO 98% vs SAC 66% constraints |

### Justificación Teórica

- **On-policy vs Off-policy**: PPO (on-policy) mejor para control energético
- **Entropy regularization**: SAC pierde en restricciones BESS
- **Convergence**: PPO 3x más rápido en ambientes estocásticos

---

## 🔧 CONFIGURACIÓN

### Archivos de Config

```yaml
configs/
├── default.yaml               # Config general (rutas, parámetros)
├── ppo_optimized.json         # Hiperparámetros PPO
├── sac_optimized.json         # Hiperparámetros SAC
└── a2c_optimized.json         # Hiperparámetros A2C
```

### Parámetros Clave

**PPO**:
```
learning_rate: 3e-4
n_steps: 25920         # ~3 episodios
batch_size: 128
clip_range: 0.2
```

**A2C**:
```
learning_rate: 3e-4
n_steps: 8760          # 1 episodio
```

**SAC**:
```
learning_rate: 3e-4
batch_size: 128
entropy_coef: 'auto'   # auto-tuning
```

---

## 🏃 QUICK START (5 min)

### Instalación Mínima
```bash
cd diseñopvbesscar
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Primer Entrenamiento
```bash
# Preparar datasets
python prepare_datasets_all_agents.py

# Entrenar PPO (10 episodios ≈ 40 min)
python scripts/train/train_ppo_multiobjetivo.py --episodes 10

# Ver resultados
python compare_agents_complete.py
```

### Checkpoints Automáticos
```
Después de entrenar, los modelos se guardan en:
checkpoints/PPO/             ← Última ejecución
checkpoints/A2C/
checkpoints/SAC/
```

---

## 📞 DOCUMENTOS RELACIONADOS

### En /src
- `src/dataset_builder_citylearn/` - Data loading y validación
- `src/agents/` - Implementación de agentes
- `src/utils/` - Funciones compartidas

### En /scripts
- `scripts/train/` - Scripts de entrenamiento
- `scripts/` - Utilidades (comparación, análisis)

### En /data
- `data/oe2/` - Datasets definitivos
- `data/interim/` - Datos procesados

### En /outputs
- `outputs/{ppo,a2c,sac}_training/` - Resultados de entrenamientos
- `outputs/baselines/` - Escenarios de comparación

---

## ✅ VALIDACIÓN

### Healthcheck Scripts

```bash
# Verificar instalación
python -c "from stable_baselines3 import PPO; print('✅ SB3 OK')"

# Validar datasets
python scripts/list_datasets.py | grep "✅"

# Test rápido de entrenamiento (1 episodio)
python scripts/train/train_ppo_multiobjetivo.py --episodes 1 --test
```

---

## 🎓 PARA INVESTIGADORES

### Publicación de Resultados

Documentos para papers académicos:
- [REFERENCIAS_ACADEMICAS_COMPLETAS.md](REFERENCIAS_ACADEMICAS_COMPLETAS.md) - Justificación teórica
- `outputs/COMPARACION_FINAL_3AGENTES.md` - Resultados empiricos
- Gráficas en `outputs/*/` - Figuras para publication

### Reproducibilidad

```bash
# Reproducir exactamente mismo resultado
git checkout <commit-hash>
python prepare_datasets_all_agents.py
python scripts/train/train_ppo_multiobjetivo.py --episodes 10
python scripts/validate_cross_agent_consistency.py
```

---

## 📈 ROADMAP (Próximos Pasos)

Consulta: [PROXIMO_PLAN_EJECUCION_2026-02-17.md](../deprecated/PROXIMO_PLAN_EJECUCION_2026-02-17.md)

### AC-1: ✅ COMPLETADO
Ruta Solar en sac_optimized.json

### AC-2: ⏳ PENDIENTE
Validación Cruzada SOC Tracking

```bash
# Ejecutar when ready:
python scripts/train/train_ppo_multiobjetivo.py --episodes 1
python scripts/train/train_a2c_multiobjetivo.py --episodes 1
python scripts/train/train_sac_multiobjetivo.py --episodes 1
python scripts/validate_cross_agent_consistency.py
```

### AC-3: ⏳ PENDIENTE
Entrenamientos iniciales (10 episodios c/u)

### AC-4: ⏳ PENDIENTE
Evaluación comparativa final

---

## 💡 TIPS

1. **GPU Insuficiente?** → Reduce `n_steps` de 25920 a 5184
2. **Entrenamiento lento?** → Usa A2C en lugar de PPO
3. **Resultados inconsistentes?** → Verifica `RUTAS_DATOS_FIJAS_v58.md`
4. **Checkpoints corrupto?** → `rm checkpoints/PPO/*` y re-entrena
5. **Duda sobre datasets?** → Lee `ESPECIFICACION_CITYLEARN_v2.md`

---

## 🔗 ESTRUCTURA DE CARPETAS

```
diseñopvbesscar/
├── README.md                    ← Visión general
├── docs/                        ← Documentación (ERES AQUÍ)
│   ├── DOCUMENTACION_INDEX.md   ← Este archivo
│   ├── REFERENCIAS_ACADEMICAS_COMPLETAS.md
│   ├── ESPECIFICACION_CITYLEARN_v2.md
│   └── ...
├── src/
│   ├── agents/                  ← Implementación RL
│   ├── dataset_builder_citylearn/
│   │   └── RUTAS_DATOS_FIJAS_v58.md  ← SSOT de rutas
│   └── utils/
├── scripts/
│   ├── train/                   ← Scripts entrenamiento
│   └── ...
├── data/
│   └── oe2/                     ← Datasets definitivos
├── checkpoints/
│   ├── PPO/
│   ├── A2C/
│   └── SAC/
├── outputs/                     ← Resultados entrenamiento
│   ├── ppo_training/
│   ├── a2c_training/
│   └── ...
└── configs/
    ├── default.yaml
    ├── ppo_optimized.json
    └── ...
```

---

**Status**: ✅ **ÍNDICE ACTUALIZADO FEBRERO 2026**  
**Próxima revisión**: Cuando se completen AC-2, AC-3, AC-4

