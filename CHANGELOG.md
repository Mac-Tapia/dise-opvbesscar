# CHANGELOG - pvbesscar

Todos los cambios notables en este proyecto se documentan en este archivo.
El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## Versionado

El proyecto sigue [Versionado Semántico](https://semver.org/lang/es/):
- **MAJOR**: Cambios incompatibles en arquitectura OE2/OE3
- **MINOR**: Nuevas características o parámetros
- **PATCH**: Correcciones de bugs

---

## [5.5] - 2026-02-18

### Cambios

#### Sistema de Almacenamiento (BESS)
- **Capacidad nominal:** Incrementada de 1,700 → 2,000 kWh
- **Capacidad usable:** 1,600 kWh (DoD: 80%)
- **Poder instantáneo:** 400 kW (carga/descarga simétrica)
- **C-rate:** Actualizado 0.235 → 0.200 (400 kW / 2,000 kWh)
- **Eficiencia round-trip:** 95% (sin cambios)
- **Restricciones SOC:** Min 20%, Max 100%, Target mañana 100%, tarde 50%

#### Sistema Solar (PV)
- **Capacidad instalada:** Confirmada 4,050 kWp (DC)
- **Producción anual:** 1,217,300 kWh (verificado en datos de 8,760 horas)
- **Utilización:** 79.8%
- **Distribución:</b>
  - Consumo directo EV: 25.1% (304.9 MWh)
  - Carga BESS: 55.7% (677.7 MWh)
  - Consumo MALL: 12.2% (148.5 MWh)
  - Curtailment: 6.9% (84.0 MWh)

#### Infraestructura de Carga EV
- **Número de cargadores:** 19 (15 motos + 4 taxis)
- **Sockets totales:** 38 (30 motos + 8 taxis) 
- **Potencia unitaria:** 7.4 kW por socket (Modo 3, 32A @ 230V monofásico)
- **Demanda diaria:** 270 motos + 39 taxis
- **Demanda anual:** 352,887 kWh (769,300 kWh en simulación con aumento de ocupación)

#### Centro Comercial (MALL)
- **Demanda diaria:** 876 MWh/año (2,400 kWh/día)
- **Tipo de carga:** Base load + picos horarios (9:00-21:00)

#### Sistema de Recompensas (Reward Function)
- **Componentes:** 5-objetivo unificado

| Objetivo | Peso | Descripción |
|----------|------|-------------|
| Minimizar CO₂ Grid | 0.50 | PRIMARY: Reducir importación desde grid térmico |
| Maximizar Solar Self-Consumption | 0.20 | SECONDARY: Usar PV directamente |
| EV Charge Satisfaction | 0.15 | TERTIARY: Asegurar carga completa antes de deadline |
| Grid Stability | 0.10 | QUATERNARY: Suavizar rampa de potencia |
| Cost Minimization | 0.05 | QUINARY: Preferir tariff horas bajas |

#### Métricas de CO₂
- **Factor de grid:** 0.4521 kg CO₂/kWh (generación térmica en Iquitos, Perú)
- **Baseline (Sin control):** ~197,262 kg CO₂/año (extrapolado)
- **Reducción esperada con RL:** 80.8% (~157,948 kg CO₂/año ahorrados)

#### Configuraciones
Todas las configuraciones unificadas a v5.5:
- `configs/default.yaml` ✓
- `configs/default_optimized.yaml` ✓
- `configs/agents/sac_config.yaml` ✓
- `configs/agents/ppo_config.yaml` ✓
- `configs/agents/a2c_config.yaml` ✓
- `configs/agents/agents_config.yaml` ✓
- `configs/sac_optimized.json` ✓

### Datos

#### Datasets OE2 (Validados)
- **PV Timeseries:** `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv`
  - Resolución: Horaria (8,760 filas/año)
  - Rango: 0-6,500 W/m² (irradiancia)
  
- **EV Charging Demand:** `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`
  - Resolución: Horaria (8,760 filas/año)
  - Sockets: 38 (30 motos + 8 taxis), cada uno hasta 7.4 kW
  
- **BESS Profile:** `data/oe2/bess/bess_ano_2024.csv`
  - Resolución: Horaria (8,760 filas/año)
  - Carga anual: 580.2 MWh
  - Descarga anual: 209.4 MWh
  - Ciclos/año: ~290
  
- **MALL Base Load:** `data/oe2/demandamallkwh/demandamallhorakwh.csv`
  - Resolución: Horaria (8,760 filas/año)
  - Rango: 80-120 kW (loads diarios)

#### Enviroment OE3
- **Framework:** CityLearn v2 (gymnasium-compatible)
- **Episode length:** 8,760 timesteps (1 año completo)
- **Observation space:** 394 dimensiones
  - Irradiancia solar
  - Frecuencia grid (50 Hz)
  - SOC BESS (% 0-100)
  - 38 sockets × 3 (power demanded, power charged, time to deadine)
  - Time features (hour, month, day_of_week)
- **Action space:** 39 dimensiones
  - 1 acción BESS (potencia normalizada [-1, +1])
  - 38 acciones sockets (power setpoint [0, 1] → 0 a 7.4 kW cada una)

### Agentes RL

#### SAC (Soft Actor-Critic)
- **Tipo:** Off-policy, determinístico
- **Hiperparámetros:**
  - Learning rate: 0.0003
  - Target entropy: Auto
  - Batch size: 256
  - Buffer size: 1,000,000
  - Tau (soft update): 0.005
- **Ventajas:** Maneja rewards asimétricos bien; convergencia rápida
- **Tiempo entrenamiento (GPU RTX 4060):** ~5-7 horas para 26,280 timesteps

#### PPO (Proximal Policy Optimization)
- **Tipo:** On-policy, estocástico
- **Hiperparámetros:**
  - Learning rate: 0.0003
  - N steps: 2,048
  - Batch size: 128
  - Clip ratio: 0.2
  - GAE lambda: 0.95
- **Ventajas:** Convergencia estable; mejor exploración
- **Tiempo entrenamiento (GPU):** ~4-6 horas

#### A2C (Advantage Actor-Critic)
- **Tipo:** On-policy, simple
- **Hiperparámetros:**
  - Learning rate: 0.0003
  - N steps: 2,048
  - GAE lambda: 0.95
- **Ventajas:** Entrenamiento más rápido (CPU/GPU)
- **Tiempo entrenamiento:** ~3-5 horas

### Adiciones

- Script de regeneración de gráficas: `scripts/regenerate_bess_plot_simple.py`
  - Genera 9 paneles con datos v5.5
  - Resolución: 1,600×1,200 px @ 100 DPI
  - Output: `data/oe2/bess/plots/bess_sistema_completo.png`

- Auditoría de estructura: `scripts/audit_detailed_analysis.py`
  - Valida integridad OE2/OE3
  - Identifica confusiones de organización
  - Genera reporte con recomendaciones

- Plan de reorganización:
  - Creadas carpetas: `scripts/analysis/`, `scripts/verification/`, `notebooks/`, `docs/archived/`, `docs/api-reference/`
  - Documentación consolidada en `docs/archived/`
  - Python scripts centralizados en `scripts/`

### Cambios de Arquitectura

- **Wrapper Dataset Builder:** Creado `src/dataset_builder.py` como entry point único
  - Importa desde `src/dataset_builder_citylearn/data_loader.py`
  - Garantiza interfaz consistente OE2 → OE3

---

## [5.4] - 2026-02-13

### Cambios

- BESS capacity: 1,700 kWh (después upgradeo a 2,000 en v5.5)
- Solar: validación de 8,760 horas hourly enforcement
- Charger specification v5.2: 19 units × 2 sockets = 38

---

## [5.3] - 2026-02-10

### Cambios

- Introducción de arquitectura OE2 → OE3
- Dataset builder citylearn v2 integration

---

## [5.2] - 2026-02-05

### Cambios

- Especificación inicial de cargadores (v5.2)
- Dimensionamiento OE2 completo

---

## [5.1] - 2026-01-28

### Cambios

- Integración CityLearn v1

---

## [5.0] - 2026-01-20

### Cambios

Initial release de pvbesscar
- OE1: Análisis de localización Iquitos
- OE2: Dimensionamiento
- OE3 (prototipo): Control básico

---

## Formato de Commits

Para mantener la claridad del CHANGELOG, usa estos prefijos:

- `feat:` nueva característica
- `fix:` corrección de bug
- `docs:` cambios de documentación
- `refactor:` cambios de código sin cambiar funcionalidad
- `perf:` mejoras de rendimiento
- `test:` adiciones/cambios de tests
- `chore:` cambios en build, configuración, etc.

Ejemplo:
```
feat(bess): incrementar capacidad nominal a 2000 kWh y ajustar c-rate
docs(changelog): actualizar v5.5 con especificaciones finales
```

---

*Última actualización: 2026-02-18*
*Responsable: GitHub Copilot*
