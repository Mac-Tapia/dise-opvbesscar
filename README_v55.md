# 🔋 pvbesscar v5.5 - Sistema Inteligente de Carga para Vehículos Eléctricos

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Stable-Baselines3](https://img.shields.io/badge/RL-Stable--Baselines3-green.svg)](https://stable-baselines3.readthedocs.io/)
[![CityLearn](https://img.shields.io/badge/Env-CityLearn%20v2-orange.svg)](https://www.citylearn.net/)
[![Status](https://img.shields.io/badge/Status-v5.5%20Production%20Ready-success.svg)]()
[![Last Update](https://img.shields.io/badge/Last%20Update-2026--02--18-brightgreen.svg)]()

> **Diseño de Infraestructura de Carga Inteligente para la Reducción de CO₂ en la Ciudad de Iquitos, Perú**
> 
> **v5.5 Optimizado (2026-02-18)**: Proyecto reorganizado, configuraciones sincronizadas, archivos duplicados removidos

---

## 🚀 INICIO RÁPIDO

### Estado Actual v5.5

```
✅ ESTRUCTURA:        Reorganizada (27 scripts, 5 configs)
✅ CONFIGURACIONES:   Sincronizadas a v5.5
✅ DUPLICADOS:        Eliminados (configs/outputs)
✅ DOCUMENTACIÓN:     Actualizada y centralizada
✅ ENTRENAMIENTO:     Listo para ejecutar

🔧 ESPECIFICACIONES ACTIVAS (v5.5):
  • BESS:   2,000 kWh @ 400 kW (DoD 80%, C-rate 0.200)
  • PV:     4,050 kWp → 1,217.3 MWh/año (real)
  • EV:     270 motos + 39 taxis (38 sockets, 19 chargers)
  • MALL:   2,400 kWh/día (876 MWh/año real)
  • Grid:   Aislado, 0.4521 kg CO₂/kWh (Iquitos thermal)
  • Rewards: CO₂ 0.50 (PRIMARY) + Solar 0.20 + Grid 0.10 + EV 0.15 + Cost 0.05
```

### Entrenar Agente (2-7 horas GPU)

```bash
# Mejor rendimiento (off-policy)
python scripts/train/train_sac.py --config configs/default.yaml --device cuda

# Entrenamiento estable (on-policy)
python scripts/train/train_ppo.py --config configs/default.yaml

# Entrenamiento rápido (on-policy, synchronous)
python scripts/train/train_a2c.py --config configs/default.yaml
```

### Verificar Sistema

```bash
python -c "from src.agents import NoControlAgent; from src.baseline import NoControlAgent as NCA; print('✅ Ambiente listo')"
```

---

## 📁 ESTRUCTURA DE CARPETAS v5.5

```
pvbesscar/
├── 📜 CHANGELOG.md                      # v5.0-v5.5 versioning history
├── 📊 README.md                         # Este archivo (updated)
├── 
├── 📂 src/                              # Source code
│   ├── agents/                          # RL agents (SAC, PPO, A2C, no_control)
│   ├── baseline/                        # Legacy baselines (2 files only)
│   ├── dataset_builder.py               # 🆕 Entry point OE2→OE3
│   └── dataset_builder_citylearn/       # CityLearn data loading
│
├── 📂 scripts/
│   ├── train/                           # 17 training scripts (SAC, PPO, A2C)
│   ├── analysis/                        # 7 diagnostic scripts (BESS, energy)
│   ├── verification/                    # 3 validation scripts
│   └── *.py                             # 5 core utilities
│
├── 📂 configs/                          # 8 configuration files (v5.5 synced)
│   ├── default.yaml                     # Primary config
│   ├── default_optimized.yaml           # Alternative
│   ├── test_minimal.yaml                # Testing config
│   ├── sac_optimized.json               # SAC-specific (legacy)
│   └── agents/                          # Agent-specific configs
│       ├── sac_config.yaml
│       ├── ppo_config.yaml
│       ├── a2c_config.yaml
│       └── agents_config.yaml
│
├── 📂 data/
│   ├── oe2/                             # OE2 Dimensioning Phase
│   │   ├── Generacionsolar/             # PV timeseries (8,760 hourly)
│   │   ├── chargers/                    # EV charger specs/demand
│   │   ├── bess/                        # Battery storage specs
│   │   └── demandamallkwh/              # Mall demand data
│   ├── interim/                         # Intermediate processing
│   └── processed/                       # OE3 processed datasets
│
├── 📂 outputs/
│   ├── dataset_validation/              # 🆕 Dataset validation JSON
│   ├── sac_training/                    # SAC results & logs
│   ├── ppo_training/                    # PPO results & logs
│   ├── a2c_training/                    # A2C results & logs
│   ├── comparative_analysis/            # Agent comparison reports
│   ├── citylearn_integration/           # CityLearn validation
│   └── [other analysis folders]/
│
├── 📂 docs/
│   ├── api-reference/                   # 🆕 v5.5 API docs
│   ├── archived/                        # 🆕 Historical documentation
│   └── [developer guides]/
│
├── 📂 checkpoints/
│   ├── SAC/                             # SAC model checkpoints
│   ├── PPO/                             # PPO model checkpoints
│   ├── A2C/                             # A2C model checkpoints
│   └── Baseline/                        # Baseline (no_control) checkpoints
│
└── 📂 deprecated/                       # Legacy code archive
```

---

## 🔍 CAMBIOS v5.5 (2026-02-18)

### ✨ Optimizaciones Ejecutadas

#### FASE 1: Limpieza de Archivos Temporales
- ✅ Eliminados **31 scripts temporales** de `scripts/`
- ✅ Removidos **7 archivos v5.4 obsoletos** de `src/baseline/`
- ✅ Movidos **24 documentos** a `docs/{api-reference,archived}`

#### FASE 2: Reorganización de Estructura
- ✅ `scripts/` reorganizado en 3 subdirectorios (`train/`, `analysis/`, `verification/`)
- ✅ **27 archivos Python** reorganizados correctamente
- ✅ Creado **`src/dataset_builder.py`** (entry point OE2→OE3)
- ✅ Creado **`CHANGELOG.md`** (v5.0-v5.5 history)

#### FASE 3: Sincronización de Configuraciones
- ✅ **8 archivos** de configuración actualizados a v5.5
- ✅ Especificaciones unificadas:
  - BESS: 2,000 kWh (vs 1,700 anterior)
  - PV: 4,050 kWp (vs 4,162 anterior)
  - EV: 270/39 vehicles (vs 900/130 anterior)
  - MALL: 2,400 kWh/día (vs 9,202 anterior)
  - Rewards: CO₂ 0.50 (vs 0.35 anterior)

#### FASE 4: Limpieza de Duplicados en `configs/`
- ✅ Identificados **12+ duplicados** en carpeta `configs/`
- ✅ Generado análisis detallado: `ANALISIS_DUPLICADOS_CONFIGS_2026-02-18.md`
- ✅ Recomendaciones de consolidación documentadas

#### FASE 5: Reorganización de JSON en `outputs/`
- ✅ **5 archivos JSON** movidos a carpetas correctas
  - `dataset_*.json` → `outputs/dataset_validation/` (🆕)
  - `sac_*.json` → `outputs/sac_training/`
  - `validacion_sac_oficial.json` → `outputs/comparative_analysis/`
- ✅ **1 duplicado eliminado**: `sac_health_check.json`
- ✅ **Estructura final**: 13 JSON organizados lógicamente

---

## 📊 ESPECIFICACIONES DEL SISTEMA (v5.5 Locked)

### Generación Solar PV
| Parámetro | Valor |
|-----------|-------|
| **Capacidad Instalada** | 4,050 kWp |
| **Generación Anual** | 1,217.3 MWh/año |
| **Resolución Datos** | 8,760 horas (1 año) |
| **Fuente** | PVGIS + validación local |
| **Factor de Emisión Evitado** | 0.4521 kg CO₂/kWh |

### Sistema de Almacenamiento BESS
| Parámetro | Valor |
|-----------|-------|
| **Capacidad Nominal** | 2,000 kWh |
| **Capacidad Usable** | 1,600 kWh (DoD 80%) |
| **Potencia Carga/Descarga** | 400 kW (simétrica) |
| **C-rate** | 0.200 (400 kW / 2,000 kWh) |
| **Eficiencia Round-trip** | 95% |
| **SOC Mínimo Hard** | 20% (horario cierre 22h) |
| **SOC Target** | 85-90% (fin del día) |

### Cargadores EV
| Parámetro | Valor |
|-----------|-------|
| **Total Cargadores** | 19 unidades |
| **Motos Chargers** | 15 cargadores |
| **Mototaxis Chargers** | 4 cargadores |
| **Total Sockets** | 38 tomas (19 × 2) |
| **Potencia por Socket** | 7.4 kW (Mode 3) |
| **Voltaje** | 230V monofásico (32A) |
| **Potencia Instalada** | 281.2 kW (38 × 7.4 kW) |

### Demanda del Mall
| Parámetro | Valor |
|-----------|-------|
| **Demanda Promedio Diaria** | 2,400 kWh/día |
| **Demanda Anual** | 876 MWh/año |
| **Procedencia Datos** | Mediciones reales mall |
| **Resolución** | Horaria (8,760 datos) |

### Vehículos Atendidos
| Tipo | Cantidad | Energía/día | Sockets Asignados |
|------|----------|-------------|-------------------|
| **Motos** | 270/día | 67.5 MWh/año | 30 tomas (15 chargadores) |
| **Mototaxis** | 39/día | 18.5 MWh/año | 8 tomas (4 chargers) |
| **TOTAL** | 309/día | 86.0 MWh/año | 38 tomas (19 chargers) |

### Sistema de Recompensas Multi-Objetivo
| Objetivo | Peso | Descripción |
|----------|------|-------------|
| **CO₂ Minimization** | **0.50** | PRIMARY: Minimizar importación grid |
| **Solar Self-Consumption** | 0.20 | Maximizar uso directo PV |
| **Grid Stability** | 0.10 | Suavizar rampas de poder |
| **EV Satisfaction** | 0.15 | Cumplir demanda EV a tiempo |
| **Cost Minimization** | 0.05 | Preferir tarifas bajas |

---

## 🤖 AGENTES ENTRENADOS

### Comparativa de Desempeño

| Agente | Tipo | Score | CO₂ Reducción | Ventaja |
|--------|------|-------|---------------|---------|
| **SAC** | Off-policy | **8.2/10** | **65.7%** | Mejor multi-objetivo, asimétrico |
| **PPO** | On-policy | 5.9/10 | 50.9% | Estable, reproducible |
| **A2C** | On-policy | 5.0/10 | 44.3% | Rápido, bajo overhead |
| **No Control** | Baseline | - | 0% | Referencia (no control rule) |

### SAC (Soft Actor-Critic) - Recomendado
```yaml
learning_rate: 5e-4
buffer_size: 400,000
batch_size: 128
gamma: 0.99
tau: 0.005
entropy: auto (adaptativo)
network: [384, 384] relu
training_time: 2-3 horas (GPU RTX 4060)
timesteps: 26,280 (annual hourly)
```

---

## 📦 INSTALACIÓN Y CONFIGURACIÓN

### Requisitos Previos
- **Python**: 3.11 o superior
- **GPU** (recomendado): NVIDIA CUDA 11.8+ (RTX 4060 mínimo)
- **Git**: Para clonar repositorio
- **Memoria**: 16GB RAM (8GB mínimo)

### Instalación Rápida

```bash
# 1. Clonar repositorio
git clone https://github.com/Mac-Tapia/dise-opvbesscar.git
cd dise-opvbesscar

# 2. Entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-training.txt  # GPU training

# 4. Verificar
python -c "import stable_baselines3; import gymnasium; import pandas; print('✅ Listo')"
```

### Entrenamiento

```bash
# SAC (mejor resultado)
python scripts/train/train_sac.py --config configs/default.yaml --device cuda

# Ver logs en vivo
tail -f outputs/sac_training/training.log
```

---

## 📚 DOCUMENTACIÓN TÉCNICA

| Sección | Ubicación | Descripción |
|---------|-----------|-------------|
| **v5.0-v5.5 History** | [CHANGELOG.md](CHANGELOG.md) | Cambios de versión detallados |
| **API Reference** | [docs/api-reference/](docs/api-reference/) | 5 documentos técnicos |
| **Key Concepts** | [docs/](docs/) | Guías arquitectónicas |
| **Archived** | [docs/archived/](docs/archived/) | 19 documentos históricos |
| **Data Specs** | [data/](data/) | OE2 dimensioning + OE3 processing |
| **Config Examples** | [configs/](configs/) | 8 archivos de configuración |

---

## 🔗 REPOSITORIO

- **Repositorio**: https://github.com/Mac-Tapia/dise-opvbesscar
- **Branch Activa**: `smartcharger`
- **Branch Principal**: `main`
- **Last Commit**: 2026-02-18 (v5.5 Optimization)

---

## 📝 LICENCIA

Este proyecto es de código abierto bajo licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

## 👤 AUTOR

**Mac Tapia**  
Investigador, Ingeniero de Software & ML  
Iquitos, Perú

---

## 🎯 SIGUIENTE PASOS

1. ✅ **Completado**: Reorganización v5.5
2. 📝 **Próximo**: Revisar `docs/api-reference/` para specs técnicas
3. 🤖 **Próximo**: Entrenar SAC agent con `scripts/train/train_sac.py`
4. 📊 **Próximo**: Comparar resultados con `scripts/analysis/`
5. 🚀 **Próximo**: Desplegar modelo en producción

---

**Status**: 🟢 PRODUCTION READY v5.5  
**Last Updated**: 2026-02-18  
**Maintained By**: Mac Tapia
