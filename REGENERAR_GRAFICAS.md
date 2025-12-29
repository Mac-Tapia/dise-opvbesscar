# Regeneración de Gráficas OE2 y OE3

Este documento explica cómo regenerar todas las gráficas del proyecto.

## Requisitos Previos

1. **Python 3.11** instalado
2. Dependencias del proyecto instaladas:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # O en Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```

## Métodos de Regeneración

### Opción 1: Script Automático Bash (Linux/Mac)

El método más simple:

```bash
./scripts/regenerate_graphics.sh
```

O con configuración personalizada:

```bash
./scripts/regenerate_graphics.sh configs/custom.yaml
```

### Opción 2: Script Python

Más control sobre qué regenerar:

```bash
# Todo
python scripts/regenerate_all_graphics.py --config configs/default.yaml

# Solo OE2
python scripts/regenerate_all_graphics.py --config configs/default.yaml --oe2-only

# Solo OE3
python scripts/regenerate_all_graphics.py --config configs/default.yaml --oe3-only

# Solo gráficas (sin re-simular)
python scripts/regenerate_all_graphics.py --skip-simulation
```

### Opción 3: Scripts Individuales

Para regenerar gráficas específicas:

#### OE2 - Dimensionamiento

```bash
# 1. Ejecutar dimensionamiento (genera datos)
python -m scripts.run_oe2_solar --config configs/default.yaml
python -m scripts.run_oe2_chargers --config configs/default.yaml
python -m scripts.run_oe2_bess --config configs/default.yaml

# 2. Generar gráficas
python -m scripts.run_oe2_solar_plots --config configs/default.yaml
python -m scripts.generate_oe2_report
```

#### OE3 - Agentes y Simulación

```bash
# 1. Ejecutar simulación (genera datos y entrena agentes)
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
python -m scripts.run_oe3_simulate --config configs/default.yaml
python -m scripts.run_oe3_co2_table --config configs/default.yaml

# 2. Generar gráficas de entrenamiento
python -m scripts.plot_oe3_training --config configs/default.yaml
```

## Ubicación de las Gráficas Generadas

### OE2
- `reports/oe2/` - Reportes y dashboards
- `reports/oe2/solar_plots/` - Gráficas detalladas del sistema FV
- Tipos de gráficas:
  - Generación solar anual
  - Perfil diario promedio
  - Análisis de rendimiento
  - Balance energético

### OE3
- `analyses/oe3/training/` - Curvas de entrenamiento
- `reports/oe3/` - Reportes y comparativas
- Tipos de gráficas:
  - Curvas de aprendizaje (SAC, PPO, A2C)
  - Comparativa de agentes
  - Evolución de recompensas
  - Análisis de CO₂

## Gráficas Generadas

### OE2 - Sistema Fotovoltaico

1. **Generación Solar Anual** (`solar_annual_generation.png`)
   - Serie temporal 8,760 horas
   - Generación DC y AC
   - Irradiación

2. **Perfil Diario Promedio** (`solar_daily_profile.png`)
   - Perfil 24h promedio
   - Potencia pico
   - Performance ratio

3. **Análisis Cargadores** (`chargers_analysis.png`)
   - Demanda horaria EV
   - Distribución de carga
   - Sesiones por hora

4. **Balance BESS** (`bess_balance.png`)
   - Estado de carga (SOC)
   - Flujos de energía
   - Ciclos diarios

5. **Dashboard Integrado** (`oe2_dashboard_integrado.png`)
   - Vista completa del sistema
   - Todos los componentes

### OE3 - Entrenamiento y Control

1. **Curvas de Entrenamiento** (`training_comparison.png`)
   - Mean reward vs steps
   - SAC, PPO, A2C comparados
   - Convergencia

2. **Recompensa por Episodio** (`training_comparison_episode_reward.png`)
   - Episode reward por agente
   - Evolución temporal
   - Mejor episodio

3. **Curvas Individuales** (`SAC_training.png`, `PPO_training.png`, `A2C_training.png`)
   - Detalle por agente
   - Métricas específicas

## Resolución de Problemas

### Error: Python 3.11 no encontrado

Instala Python 3.11:

**Ubuntu/Debian:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv
```

**macOS:**
```bash
brew install python@3.11
```

**Windows:**
Descarga desde [python.org](https://www.python.org/downloads/)

### Error: ModuleNotFoundError

Asegúrate de haber instalado las dependencias:

```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Error: No se encuentran datos

Debes ejecutar primero el dimensionamiento/simulación:

```bash
# Para OE2
python -m scripts.run_oe2_solar --config configs/default.yaml
python -m scripts.run_oe2_chargers --config configs/default.yaml
python -m scripts.run_oe2_bess --config configs/default.yaml

# Para OE3
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

### Error: CUDA no disponible (OE3)

Si no tienes GPU, el código automáticamente usará CPU. Para forzar CPU:

1. Edita `configs/default.yaml`:
   ```yaml
   oe3:
     evaluation:
       sac:
         device: cpu
       ppo:
         device: cpu
       a2c:
         device: cpu
   ```

## Tiempos de Ejecución Aproximados

| Etapa | CPU | GPU |
|-------|-----|-----|
| OE2 Solar | ~2 min | ~2 min |
| OE2 Chargers | ~1 min | ~1 min |
| OE2 BESS | ~1 min | ~1 min |
| OE2 Gráficas | ~30 seg | ~30 seg |
| OE3 Dataset | ~2 min | ~2 min |
| OE3 Simulate (SAC/PPO/A2C) | ~60 min | ~15 min |
| OE3 CO2 Table | ~1 min | ~1 min |
| OE3 Gráficas | ~30 seg | ~30 seg |
| **Total** | **~70 min** | **~25 min** |

## Personalización

### Cambiar Resolución de Gráficas

Edita el DPI en los scripts:

```python
# En scripts/plot_oe3_training.py
fig.savefig(path, dpi=300, bbox_inches="tight")  # Cambiar de 150 a 300
```

### Agregar Nuevas Gráficas

1. Crea un nuevo script en `scripts/`
2. Usa matplotlib para generar la gráfica
3. Guarda en el directorio apropiado (`reports/` o `analyses/`)
4. Agrega al script de regeneración

## Formato de Salida

Todas las gráficas se generan en formato PNG con:
- **DPI:** 150 (estándar) o 300 (alta calidad)
- **Bbox:** tight (sin espacios en blanco)
- **Encoding:** UTF-8

Para cambiar el formato:

```python
fig.savefig(path, dpi=300, bbox_inches="tight", format="pdf")  # PDF en vez de PNG
```
