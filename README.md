# 🔋 pvbesscar - EV Charging Optimization with RL

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Stable-Baselines3](https://img.shields.io/badge/RL-Stable--Baselines3-green.svg)](https://stable-baselines3.readthedocs.io/)
[![CityLearn](https://img.shields.io/badge/Env-CityLearn%20v2-orange.svg)](https://www.citylearn.net/)

> Optimización de carga EV con Solar PV + BESS mediante Reinforcement Learning

---

## 🎯 Descripción del Proyecto

**pvbesscar** optimiza la carga de 128 cargadores eléctricos (2,912 motos + 416 mototaxis) utilizando:

- **Solar PV**: 4,050 kWp de generación fotovoltaica
- **BESS**: 4,520 kWh de almacenamiento en baterías
- **RL Agents**: SAC, PPO, A2C para minimizar emisiones CO₂

**Ubicación**: Iquitos, Perú (red aislada, 0.4521 kg CO₂/kWh de generación térmica)

---

## 🚀 Quick Start

### Instalación

```bash
# Clonar repositorio
git clone https://github.com/Mac-Tapia/dise-opvbesscar.git
cd dise-opvbesscar

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# o: source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-training.txt  # Para GPU
```

### Entrenamiento de Agentes RL

```bash
# SAC (Soft Actor-Critic) - Recomendado
python train_sac_multiobjetivo.py

# PPO (Proximal Policy Optimization)
python train_ppo_multiobjetivo.py

# A2C (Advantage Actor-Critic)
python train_a2c_multiobjetivo.py
```

### Verificación del Sistema

```bash
# Verificar dataset (8,760 timesteps)
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv'); print(f'✓ Solar: {len(df)} rows')"

# Verificar cargadores (128 total)
python scripts/verify_5_datasets.py
```

---

## 📊 Arquitectura del Sistema

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    CityLearn v2 Environment                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐   │
│  │  Solar PV    │  │    BESS      │  │   128 EV Chargers       │   │
│  │  4,050 kWp   │  │  4,520 kWh   │  │   (32 units × 4 sockets)│   │
│  └──────────────┘  └──────────────┘  └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     RL Agents (stable-baselines3)                   │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐                  │
│  │   SAC    │      │   PPO    │      │   A2C    │                  │
│  │ off-pol. │      │ on-pol.  │      │ on-pol.  │                  │
│  └──────────┘      └──────────┘      └──────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Espacios de Observación y Acción

| Componente       | Dimensiones | Descripción                                       |
| ---------------- | ----------- | ------------------------------------------------- |
| **Observación**  | 394-dim     | Solar W/m², BESS SOC %, 128 chargers × 3, tiempo  |
| **Acción**       | 129-dim     | 1 BESS + 128 chargers, valores continuos [0,1]    |

---

## 🎯 Sistema de Recompensa Multi-Objetivo

| Objetivo               | Peso | Descripción                        |
| ---------------------- | ---- | ---------------------------------- |
| **Minimización CO₂**   | 0.50 | Grid imports × 0.4521 kg CO₂/kWh   |
| **Autoconsumo Solar**  | 0.20 | Maximizar uso directo de PV        |
| **Carga EV Completa**  | 0.15 | EVs cargados antes del deadline    |
| **Estabilidad Red**    | 0.10 | Rampas de potencia suaves          |
| **Minimización Costo** | 0.05 | Preferencia horario bajo           |

---

## 📈 Resultados Esperados

### Baseline vs RL Agents

| Escenario              | CO₂ (kg/año) | Reducción |
| ---------------------- | ------------ | --------- |
| **Baseline Sin Solar** | ~640,000     | -         |
| **Baseline Con Solar** | ~190,000     | -70%      |
| **SAC (RL)**           | ~7,200       | -96%      |
| **PPO (RL)**           | ~7,000       | -96%      |
| **A2C (RL)**           | ~7,400       | -96%      |

---

## 📁 Estructura del Proyecto

```text
pvbesscar/
├── src/
│   ├── agents/            # SAC, PPO, A2C implementations
│   ├── citylearnv2/       # CityLearn dataset builder
│   └── dimensionamiento/  # OE2 infrastructure specs
├── data/
│   ├── interim/oe2/       # Solar, chargers, BESS specs
│   └── processed/         # CityLearn-ready datasets
├── configs/               # YAML configurations
├── checkpoints/           # Trained model checkpoints
├── scripts/               # Utility scripts
├── docs/                  # Documentation
└── train_*_multiobjetivo.py  # Training scripts
```

---

## 🔧 Configuración

Archivo principal: `configs/default.yaml`

```yaml
oe3:
  grid:
    carbon_intensity_kg_per_kwh: 0.4521  # Iquitos thermal factor
    tariff_usd_per_kwh: 0.20
  
  agents:
    sac:
      learning_rate: 5e-5
      gamma: 0.995
      tau: 0.02
```

---

## 📚 Documentación

- [docs/README.md](docs/README.md) - Documentación técnica completa
- [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Referencia rápida
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Instrucciones para Copilot

---

## ✅ Estado del Sistema (2026-02-07)

| Componente   | Estado                          |
| ------------ | ------------------------------- |
| Código       | ✅ 0 errores Pylance            |
| Dataset      | ✅ 8,760 timesteps verificados  |
| Agentes      | ✅ SAC, PPO, A2C operacionales  |
| GPU          | ✅ CUDA habilitado              |
| 128 Chargers | ✅ Datasets generados           |

---

## 🛠️ Requisitos

- **Python**: 3.11+
- **GPU**: NVIDIA RTX 4060 (opcional, recomendado)
- **Dependencias**: stable-baselines3, gymnasium, pandas, numpy, torch

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

---

## 👥 Contribuciones

1. Fork el proyecto
2. Crea tu Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push al Branch (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request
