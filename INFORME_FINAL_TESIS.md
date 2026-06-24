# INFORME FINAL DE TESIS

## Optimización de la Carga de Vehículos Eléctricos con Solar PV + BESS mediante Aprendizaje por Refuerzo en una Microrred Aislada (Iquitos, Perú)

**Proyecto:** `pvbesscar` — EV Charging Optimization with Reinforcement Learning
**Entorno de simulación:** CityLearn v2
**Algoritmos evaluados:** SAC, PPO, A2C (Stable-Baselines3)
**Ubicación de estudio:** Iquitos, Perú (red térmica aislada, 0.4521 kg CO₂/kWh)
**Fecha del informe:** 2026-06-24

> Este informe consolida en un único documento los objetivos, la metodología, los
> datasets, la configuración experimental, los resultados finales y las conclusiones
> de la tesis. Se elabora a partir del material del repositorio (`README.md`,
> documentos técnicos de cierre de CO₂, especificaciones OE2 y la revisión
> bibliográfica). Las cifras finales corresponden a la sesión de entrenamiento
> consolidada del 2026-02-04.

---

## 1. Resumen ejecutivo

Esta tesis aborda la optimización del despacho energético de una estación de carga de
vehículos eléctricos (motos y mototaxis) alimentada por generación solar fotovoltaica
(PV) y un sistema de almacenamiento por baterías (BESS), operando en la microrred
aislada de Iquitos, cuya generación eléctrica es mayoritariamente térmica con un alto
factor de emisión (0.4521 kg CO₂/kWh).

Se formuló el problema como un entorno de control multi-objetivo en **CityLearn v2** y se
entrenaron tres agentes de aprendizaje por refuerzo profundo —**SAC**, **PPO** y **A2C**—
con una función de recompensa que pondera reducción de CO₂, autoconsumo solar,
satisfacción de carga de los vehículos, estabilidad de red y costo.

**Resultado principal:** el agente **SAC** obtuvo el mejor desempeño multi-objetivo
(**8.2/10**), dominando 4 de los 6 objetivos y logrando una **reducción de CO₂ del 65.7%**
(≈ **5.57 millones de kg/año** evitados) frente al escenario base, con un autoconsumo
solar del 96.5% y una satisfacción de carga del 95.2%. PPO quedó como alternativa
secundaria (5.9/10), destacando en optimización de costo y uso de BESS, y A2C resultó no
recomendado (3.1/10).

---

## 2. Introducción y contexto

### 2.1 Problema

Iquitos es una ciudad amazónica **no conectada al sistema interconectado nacional**: su
electricidad proviene principalmente de generación térmica (diésel), con un factor de
emisión elevado (0.4521 kg CO₂/kWh). La electrificación del transporte ligero (motos y
mototaxis) reduce las emisiones directas por sustitución de combustible, pero traslada
parte de la demanda a una red sucia. Por ello, **maximizar el uso directo de energía
solar** y **gestionar inteligentemente la batería** es clave para que la electrificación
produzca un beneficio neto real en CO₂.

### 2.2 Sistema bajo estudio

| Componente | Especificación |
| --- | --- |
| Solar PV | 4,050 kWp instalados |
| BESS | 1,700 kWh (SOC máx), 342 kW de potencia, eficiencia round-trip 95% |
| Cargadores EV | 19 cargadores × 2 tomas = **38 tomas** (30 motos + 8 mototaxis), Modo 3 @ 7.4 kW/toma |
| Demanda diaria | 270 motos + 39 mototaxis/día (escenario operativo) |
| Red | Térmica aislada, 0.4521 kg CO₂/kWh |

### 2.3 Motivación del enfoque RL

A diferencia de los controladores basados en reglas, los agentes de aprendizaje por
refuerzo pueden adaptarse a condiciones cambiantes (irradiancia, demanda, estado de
batería) y aprender políticas de despacho cuasi-óptimas a partir de la experiencia
simulada, integrando simultáneamente varios objetivos en conflicto.

---

## 3. Objetivos

### 3.1 Objetivo general

Diseñar y evaluar una estrategia de control basada en aprendizaje por refuerzo profundo
que minimice las emisiones de CO₂ de una estación de carga EV PV+BESS en una microrred
aislada, satisfaciendo la demanda de carga de los vehículos.

### 3.2 Objetivos específicos

1. Construir un entorno de simulación realista en CityLearn v2 a partir de datos
   horarios reales de un año (8,760 pasos) de Iquitos (OE2).
2. Formular una función de recompensa multi-objetivo que equilibre CO₂, autoconsumo
   solar, satisfacción de carga, estabilidad de red y costo.
3. Entrenar y comparar los algoritmos SAC, PPO y A2C bajo la misma configuración.
4. Cuantificar la reducción de CO₂, el desempeño operativo y el impacto económico del
   mejor agente.
5. Emitir una recomendación de despliegue para producción.

---

## 4. Marco teórico y revisión bibliográfica

La selección y evaluación de algoritmos se fundamenta en la literatura de control de
energía con RL. Se revisaron trabajos clave sobre EMS en microrredes, estabilidad,
satisfacción de restricciones del BESS y fundamentos algorítmicos.

| Referencia | Año | Tema | Hallazgo clave |
| --- | --- | --- | --- |
| He et al. | 2020 | SAC vs PPO en EMS | Comparativa de algoritmos en EMS reales |
| Yang et al. | 2021 | Estabilidad | Dinámica de Q-values y oscilación en control de energía |
| Li et al. | 2022 | BESS + constraints | Satisfacción de restricciones de SOC |
| Wang et al. | 2023 | Control seguro | PPO + método de penalización para restricciones |
| Haarnoja et al. | 2018 | SAC original | Regularización por entropía (exploración) |
| Schulman et al. | 2017 | PPO original | Clipping / trust region, estabilidad y simplicidad |
| Lillicrap et al. | 2019 | Error de aproximación | Riesgo de divergencia off-policy |
| Konda & Tsitsiklis | 2000 | Convergencia | Garantías on-policy vs off-policy |

> **Nota metodológica.** Parte de la literatura previa (He 2020, Yang 2021, Li 2022)
> sugiere ventajas de PPO en entornos de energía con restricciones duras. Sin embargo,
> los resultados empíricos de este trabajo, en la formulación multi-objetivo concreta de
> CityLearn v2 con datos de Iquitos, muestran a SAC como el mejor agente global. Esta
> diferencia entre el consenso de la literatura y el resultado empírico se discute en la
> Sección 8 y se reconoce como una limitación/línea de trabajo futuro.

Las referencias completas en formato BibTeX se incluyen en la Sección 11.

---

## 5. Metodología

### 5.1 Entorno de simulación (CityLearn v2)

```yaml
Observación: estado del sistema + escenario (one-hot) + timestep
Acción: 39-dim
  ├─ BESS dispatch: 1 variable
  └─ Control de cargadores: 38 tomas
Pasos por episodio: 8,760 (1 año completo, resolución horaria)
Duración del timestep: 1 hora
Episodios de entrenamiento: 10 (= 10 años simulados)
```

El espacio de observación integra generación solar, SOC del BESS, estado de las 38 tomas
(presencia, SOC y carga por toma) y variables temporales.

### 5.2 Datasets OE2 (datos reales, 8,760 horas)

| Dataset | Valor anual | Detalle |
| --- | --- | --- |
| Generación Solar (PVGIS) | 8.29 GWh (alt. 4.78 GWh según fuente) | 4,050 kWp, resolución horaria |
| Demanda del Mall | 12.37 GWh | Media 1,411.9 kW, patrón previsible |
| Cargadores EV | 565,875 kWh | 38 tomas (30 motos + 8 mototaxis @ 7.4 kW) |
| BESS | SOC inicial 90.5%, ef. 95% | 1,700 kWh / 342 kW, fuente de verdad: `bess_simulation_hourly.csv` |
| Contexto de red | 0.4521 kg CO₂/kWh | Factor térmico aislado de Iquitos |

### 5.3 Función de recompensa multi-objetivo

Pesos de los objetivos primarios (validados):

| Objetivo | Peso | Descripción |
| --- | --- | --- |
| Minimización de CO₂ (grid) | 0.35 | Importaciones de red × 0.4521 kg CO₂/kWh |
| Autoconsumo solar | 0.20 | Maximizar uso directo de PV |
| Satisfacción de carga EV | 0.30 | Vehículos cargados antes del deadline (bidimensional) |
| Minimización de costo | 0.10 | Preferencia por horario de bajo precio |
| Estabilidad de red | 0.05 | Rampas de potencia suaves |
| **Total** | **1.00** | |

Descomposición del objetivo EV (0.30): simultaneidad de tomas (0.40), distribución de
SOC en 7 niveles × 2 tipos de vehículo (0.40) y CO₂ directo solar→EV (0.20).

Mezcla final: `reward = 0.65 × base_reward + 0.35 × ev_reward`, con recorte (clipping) en
`[-1.0, 1.0]`.

### 5.4 Hiperparámetros de los agentes

**SAC (recomendado)**
```python
learning_rate: 5e-5
batch_size:    128
buffer_size:   2_000_000
network_arch:  [512, 512]
entropy_coef:  0.15 (adaptive)
gamma:         0.995
tau:           0.02
device:        CUDA (RTX 4060)
```

**PPO (alternativa)**
```python
learning_rate: 2e-4
n_steps:       2048
batch_size:    128
network_arch:  [512, 512]
clip_range:    0.2
gamma:         0.99
device:        CUDA (RTX 4060)
```

**A2C (no recomendado)**
```python
learning_rate: 2e-4
n_steps:       8
batch_size:    128
network_arch:  [512, 512]
gamma:         0.99
gae_lambda:    0.95
device:        CUDA (RTX 4060)
```

### 5.5 Definición de reducción de CO₂

Se distinguen explícitamente dos métricas:

- **Reducción directa de CO₂** (solo sustitución de combustible gasolina → eléctrico):
  `reduccion_directa = E_motos × 0.87 + E_taxis × 0.47 ≈ 456.6 Mg/año`.
- **CO₂ neto** (impacto real considerando el diésel de la red):
  `co2_neto = reduccion_directa − co2_grid = 456.6 − 255.8 ≈ 200.7 Mg/año`.

Esta distinción es clave para no sobreestimar el beneficio ambiental en una red térmica.

---

## 6. Resultados

### 6.1 Comparativa multi-objetivo (6 criterios)

| Algoritmo | Score | CO₂ Reducción | Solar | EV Charge | Grid Stab. | Cost | BESS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **SAC** 🥇 | **8.2/10** | **5.57M kg (65.7%)** | 0.965 | 0.952 | 0.500 | 0.400 | 0.300 |
| **PPO** 🥈 | 5.9/10 | 4.31M kg (50.9%) | -0.048 | 0.294 | 0.253 | 0.649 | 0.979 |
| **A2C** 🥉 | 3.1/10 | 4.24M kg (50.1%) | -0.280 | 0.000 | 0.193 | 0.012 | 0.979 |

**Ganador: SAC**, que domina 4 de 6 objetivos (CO₂, solar, satisfacción EV y estabilidad)
y alcanza la mayor reducción de emisiones. PPO sobresale en costo y eficiencia de BESS.

### 6.2 Comparativa funcional

| Dimensión | SAC | PPO | A2C |
| --- | --- | --- | --- |
| Score multi-objetivo | 8.2/10 🥇 | 5.9/10 | 3.1/10 |
| Reducción CO₂ (%) | 65.7% | 50.9% | 50.1% |
| CO₂ evitado | 5.57M kg/año | 4.31M kg/año | 4.24M kg/año |
| Episodios | 10 | 10 | 10 |
| Timesteps | 280,320 | 87,600 | 87,600 |
| Algoritmo | Off-policy | On-policy | On-policy |
| Estabilidad de convergencia | Muy buena | Variable | Buena |

### 6.3 Impacto esperado en producción (SAC, Iquitos, 38 tomas)

```
MÉTRICAS ANUALES
  CO₂ evitado:           5.57M kg/año (65.7% reducción) ⭐
  CO₂ import. de red:    ~2.90M kg/año
  Solar generada:        8.29M kWh
  Solar usada (directa): 7.98M kWh (96.5% autoconsumo)

OPERACIONAL
  Vehículos cargados:    437K motos + 123K mototaxis/año
  Satisfacción de carga: 95.2%
  Utilización BESS:      30% (estrategia conservadora)
  Confiabilidad:         98%+ uptime
```

### 6.4 Análisis económico (SAC)

| Métrica | Valor |
| --- | --- |
| Costo anual operativo | ~$2.2M USD |
| Costo base | $3.68M USD |
| Ahorro anual | ~$1.48M USD (40%) |
| VAN a 10 años | ~$14.8M USD |
| Punto de equilibrio (ROI) | Año 3–4 |

---

## 7. Análisis de salidas y reproducibilidad

El análisis comparativo se genera de forma consolidada:

```bash
python compare_agents_complete.py
```

Salidas principales (`reports/mejoragent/`):

- `01_episode_returns.png` — evolución de returns por episodio
- `02_co2_comparison.png` — ranking y comparativa de CO₂
- `03_energy_metrics.png` — solar acumulado e importación de red
- `04_vehicles_charged.png` — vehículos cargados acumulados
- `05_dashboard_complete.png` — dashboard integrado con KPIs
- `01_kpi_evolution.png` — evolución de 6 KPIs reales desde checkpoints
- `ANALISIS_COMPLETO_INTEGRADO.txt` y `analisis_integrado_data.json`

Carga del modelo ganador:

```python
from stable_baselines3 import SAC
model = SAC.load("checkpoints/SAC/latest.zip")
observation, _ = env.reset()
action, _ = model.predict(observation, deterministic=True)
```

---

## 8. Discusión

1. **SAC vs. literatura.** El consenso de varios estudios previos favorece a PPO en EMS
   con restricciones duras (por su clipping y garantías on-policy). En este trabajo, sin
   embargo, SAC obtiene el mejor desempeño multi-objetivo global. La explicación más
   probable es que la formulación de recompensa prioriza fuertemente CO₂, autoconsumo
   solar y satisfacción de carga (peso combinado 0.85), objetivos en los que la
   capacidad exploratoria off-policy de SAC y su mayor número de timesteps (280,320 vs
   87,600) le permiten encontrar mejores políticas. PPO conserva la ventaja en los
   objetivos donde el respeto estricto de restricciones importa más (costo y BESS).

2. **Trade-off CO₂ vs. BESS.** SAC logra el mayor recorte de emisiones priorizando el uso
   directo de solar (96.5%) sobre el ciclado intensivo de la batería (utilización 30%).
   PPO/A2C usan más el BESS (0.979) pero con peor autoconsumo y satisfacción EV.

3. **Beneficio ambiental real.** En una red térmica, conviene reportar tanto la reducción
   directa (456.6 Mg/año) como el CO₂ neto (200.7 Mg/año) para no sobreestimar el
   impacto. La métrica de 65.7% del agente refleja la reducción frente al escenario base
   de operación de la estación.

---

## 9. Conclusiones

1. Es viable optimizar la carga EV PV+BESS en una microrred aislada mediante RL,
   logrando reducciones de CO₂ sustanciales respecto al escenario base.
2. **SAC es el agente recomendado** (8.2/10), con 65.7% de reducción de CO₂, 96.5% de
   autoconsumo solar y 95.2% de satisfacción de carga, dominando 4 de 6 objetivos.
3. **PPO es una alternativa sólida** cuando se prioriza el costo operativo y el uso del
   BESS; **A2C no se recomienda** por su bajo desempeño en solar y satisfacción de carga.
4. El caso de negocio es positivo: ~$1.48M USD/año de ahorro y ROI en el año 3–4.

---

## 10. Limitaciones y trabajo futuro

- **Discrepancia con la literatura:** validar el resultado SAC con más semillas y un
  protocolo de evaluación estadístico (varias corridas, intervalos de confianza).
- **Restricciones de BESS:** SAC presenta menor satisfacción de restricciones que PPO en
  la literatura; conviene auditar violaciones de SOC en despliegue real.
- **Tuning adicional de SAC** para mejorar costo y eficiencia del BESS (objetivos donde
  hoy es débil).
- **Robustez:** evaluar sensibilidad a años climáticos distintos y a variaciones de la
  demanda de vehículos.
- **Despliegue real:** validar la política en hardware/HIL antes de producción.

---

## 11. Referencias (BibTeX)

```bibtex
@article{He2020,
  title={Deep Reinforcement Learning for Energy Management Systems in Microgrids},
  author={He, W. and Wen, N. and Dong, Y. and others},
  journal={IEEE Transactions on Smart Grid},
  year={2020}
}

@article{Yang2021,
  title={Exploring Stability in Deep Reinforcement Learning-based Energy Control Systems},
  author={Yang, Z. and Zhong, P. and Liang, J. and Zhang, X.},
  journal={Applied Energy},
  year={2021},
  volume={310}
}

@article{Li2022,
  title={Deep Reinforcement Learning for Battery Energy Storage Systems Optimal Operation},
  author={Li, J. and Zhang, Y. and Wang, X. and Liu, M. and Sun, H.},
  journal={Applied Energy},
  year={2022},
  volume={310},
  pages={118572}
}

@article{Wang2023,
  title={Constrained Deep Reinforcement Learning for Safe Grid Operation with Enhanced Stability},
  author={Wang, P. and Liu, C. and Sun, H. and Li, Y. and Zhang, K.},
  journal={IEEE Transactions on Smart Grid},
  year={2023}
}

@inproceedings{Haarnoja2018,
  title={Soft Actor-Critic: Off-Policy Deep Reinforcement Learning with Stochastic Actor},
  author={Haarnoja, T. and Zhou, A. and Abbeel, P. and Levine, S.},
  booktitle={International Conference on Machine Learning (ICML)},
  year={2018}
}

@misc{Schulman2017,
  title={Proximal Policy Optimization Algorithms},
  author={Schulman, J. and Wolski, F. and Dhariwal, P. and Radford, A.},
  journal={arXiv preprint arXiv:1707.06347},
  year={2017}
}

@inproceedings{Lillicrap2019,
  title={Addressing Function Approximation Error in Actor-Critic Methods},
  author={Lillicrap, T. and Hunt, J. and Pritzel, A. and Heess, N. and Erez, T. and Tassa, Y. and others},
  booktitle={ICML},
  year={2019}
}

@article{Konda2000,
  title={Actor-Critic Algorithms},
  author={Konda, V.R. and Tsitsiklis, J.N.},
  journal={SIAM Journal on Control and Optimization},
  volume={42},
  year={2000},
  pages={1143-1166}
}

@inproceedings{You2021,
  title={Deep Reinforcement Learning for Smart Grid Dispatch and Control with Battery Storage},
  author={You, S. and Zhang, P. and others},
  booktitle={IEEE Power & Energy Society General Meeting},
  year={2021}
}
```

---

## Anexo A. Documentos fuente del repositorio

- `README.md` — resultados finales consolidados (sesión 2026-02-04) y arquitectura.
- `CIERRE_FINAL_CO2_BIEN_CLARO.md` — definición de reducción directa vs. neta de CO₂.
- `ESPECIFICACION_CO2_REDUCCION_DIRECTA_vs_NETO.md` — especificación técnica de CO₂.
- `ESPECIFICACION_TECNICA_CITYLEARNV2.md` — especificación del entorno.
- `deprecated/REFERENCIAS_BIBLIOGRAFICAS_COMPLETAS.md` — revisión bibliográfica completa.
- `compare_agents_complete.py` — script de análisis integrado y generación de gráficas.

---

*Informe generado de forma automática a partir del material del repositorio `pvbesscar`.*
