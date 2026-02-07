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

## 🏆 Resultados de Entrenamiento SAC (2026-02-07)

Entrenamiento completado con **10 episodios** (87,600 timesteps) usando GPU NVIDIA RTX 4060.

### Configuración del Entrenamiento

| Parámetro | Valor |
| --------- | ----- |
| **Device** | CUDA (RTX 4060 - 8.6 GB VRAM) |
| **Timesteps totales** | 87,600 (10 episodios × 8,760 horas) |
| **Duración** | 812.9 segundos (~13.5 minutos) |
| **Learning Rate** | 0.0002 |
| **Batch Size** | 128 |
| **Buffer Size** | 2,000,000 |
| **Network** | [512, 512] |

### Reward Weights Aplicados

| Componente | Peso | Descripción |
| ---------- | ---- | ----------- |
| **CO₂ Grid** | 0.35 | Minimizar importación de red |
| **EV Satisfaction** | 0.30 | Carga completa de vehículos |
| **Solar** | 0.20 | Autoconsumo PV |
| **Cost** | 0.10 | Minimizar costo energético |
| **Grid Stability** | 0.05 | Suavizar picos de demanda |

### Métricas Finales (Promedio 10 episodios)

| Métrica | Valor |
| ------- | ----- |
| **Mean Reward** | 3,483.32 |
| **CO₂ Evitado Total** | 4,402,465 kg/año |
| **CO₂ Grid (emitido)** | 3,077,672 kg/año |
| **CO₂ NETO** | **-1,324,793 kg/año** |
| **Reducción CO₂** | **58.9%** |
| **Solar Generada** | 8,292,514 kWh/año |
| **Grid Import** | 6,801,431 kWh/año |
| **Costo Total** | $915,179 USD |
| **Ahorro desde Baseline** | $1,658,503 USD |

### Componentes de Reward (Último Episodio)

| Componente | Valor | Peso |
| ---------- | ----- | ---- |
| r_ev (satisfacción) | **0.9998** | 0.30 |
| r_co2 (reducción) | 0.2493 | 0.35 |
| r_solar (autoconsumo) | -0.2478 | 0.20 |
| r_cost (costo) | -0.2798 | 0.10 |
| r_grid (estabilidad) | -0.0195 | 0.05 |

### Evolución por Episodio

| Episodio | Reward | CO₂ Grid (kg) | CO₂ Evitado (kg) |
| -------- | ------ | ------------- | ---------------- |
| 1 | 3,487.44 | 3,079,398 | 673,129 |
| 2 | 3,487.60 | 3,079,087 | 669,735 |
| 3 | 3,482.02 | 3,070,888 | 630,081 |
| 4 | 3,478.71 | 3,070,579 | 616,593 |
| 5 | 3,484.42 | 3,080,431 | 669,836 |
| 6 | 3,485.68 | 3,082,783 | 667,679 |
| 7 | 3,482.03 | 3,076,725 | 641,781 |
| 8 | 3,482.27 | 3,079,682 | 650,403 |
| 9 | 3,483.77 | 3,078,978 | 659,050 |
| 10 | 3,483.61 | 3,079,164 | 650,164 |

### Archivos Generados

```text
checkpoints/SAC/
├── sac_final_model.zip              # Modelo final (37.11 MB)
├── sac_checkpoint_50000_steps.zip   # Checkpoint intermedio
└── sac_checkpoint_replay_buffer_50000_steps.pkl  # Buffer (16.9 GB)

outputs/sac_training/
├── result_sac.json           # Métricas de validación
├── sac_training_metrics.json # Métricas de entrenamiento
├── timeseries_sac.csv        # Series temporales (87,600 filas)
└── trace_sac.csv             # Trace detallado (87,600 filas)
```

### Cargar Modelo Entrenado

```python
from stable_baselines3 import SAC

# Cargar modelo SAC entrenado
model = SAC.load("checkpoints/SAC/sac_final_model")

# Usar para predicción
action, _ = model.predict(observation, deterministic=True)
```

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

## � Datasets OE2 Verificados (2026-02-07)

Todos los datasets están completos con **8,760 horas** (1 año) de datos reales de Iquitos, Perú.

### Resumen de Datasets

| Dataset | Archivo | Filas | Valor Anual | Promedio/Hora |
| ------- | ------- | ----- | ----------- | ------------- |
| **Generación Solar** | `pv_generation_timeseries.csv` | 8,760 | **4,775.9 MWh** | 545.2 kWh |
| **Demanda Mall** | `demandamallhorakwh.csv` | 8,760 | **12.37 GWh** | 1,411.9 kWh |
| **Chargers EV** | `chargers_hourly_profiles_annual.csv` | 8,760 | **232,341 kWh** | 26.5 kWh |
| **BESS SOC** | `bess_hourly_dataset_2024.csv` | 8,760 | SOC 15.6% prom | - |

### Detalle por Dataset

#### 1. Generación Solar (4,050 kWp instalados)

```text
Ubicación: data/interim/oe2/solar/
Columnas:  fecha, hora, irradiancia_ghi, potencia_kw, energia_kwh, temperatura_c, velocidad_viento_ms
Total:     4,775,948 kWh/año (4.78 GWh)
Máximo:    1,982.7 kWh/hora
```

#### 2. Demanda Mall (Centro Comercial)

```text
Ubicación: data/interim/oe2/demandamallkwh/
Columnas:  FECHAHORA, kWh
Total:     12,368,653 kWh/año (12.37 GWh)
Máximo:    2,763.0 kWh/hora
```

#### 3. Chargers EV (128 sockets controlables)

```text
Ubicación: data/interim/oe2/chargers/
Formato:   32 chargers × 4 sockets = 128 puntos de carga
Total:     232,341 kWh/año demanda EV
Tipos:     112 motos (2 kWh) + 16 mototaxis (4.5 kWh)
```

#### 4. BESS - Battery Energy Storage System (4,520 kWh)

```text
Ubicación: data/interim/oe2/bess/
Columnas:  timestamp, power_kw, energy_kwh, soc_percent
Capacidad: 4,520 kWh | Potencia máx: 500 kW
SOC prom:  15.6% | SOC máx: 75.4%
```

### Verificar Datasets

```bash
# Verificación rápida de todos los datasets
python -c "
import pandas as pd
datasets = {
    'Solar': 'data/interim/oe2/solar/pv_generation_timeseries.csv',
    'Mall': 'data/interim/oe2/demandamallkwh/demandamallhorakwh.csv',
    'Chargers': 'data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv',
    'BESS': 'data/interim/oe2/bess/bess_hourly_dataset_2024.csv'
}
for name, path in datasets.items():
    try:
        sep = ';' if 'mall' in path.lower() else ','
        df = pd.read_csv(path, sep=sep)
        print(f'✓ {name}: {len(df):,} filas')
    except Exception as e:
        print(f'✗ {name}: {e}')
"
```

---

## �🔧 Configuración

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
| Dataset Solar | ✅ 8,760 horas - 4.78 GWh/año  |
| Dataset Mall  | ✅ 8,760 horas - 12.37 GWh/año |
| Dataset Chargers | ✅ 8,760 × 128 sockets       |
| Dataset BESS | ✅ 8,760 horas - 4,520 kWh     |
| Agentes      | ✅ SAC, PPO, A2C operacionales  |
| GPU          | ✅ CUDA RTX 4060 habilitado     |
| Output Files | ✅ result_*.json, timeseries_*.csv, trace_*.csv |

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
