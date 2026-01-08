# Schemas OE3 Actualizados

## Fecha de Actualizacion

2025-12-22

## Línea Base de Emisiones CO₂ - Iquitos 2025

Fuente: Plan de Desarrollo Concertado de la Provincia de Maynas 2025-2030 [4]

| Sector | Detalle | Emisiones (tCO₂/año) |
| ------ | ------- | ------------------- |
| Transporte | 61,000 mototaxis | 152,500 |
| Transporte | 70,500 motos lineales | 105,750 |
| **Total transporte** | 95% del sector | **258,250** |
| Generación eléctrica | Central térmica (22.5M gal/año) | **290,000** |

---

## Schema: PV + BESS (schema_pv_bess.json)

| Parametro | Valor |
| --- | --- |
| PV Nominal | 2,591.15 kWp |
| BESS Capacidad | 740 kWh |
| BESS Potencia | 370 kW |
| BESS Eficiencia | 90% |
| BESS DOD | 80% |

## Schema: Grid Only (schema_grid_only.json)

| Parametro | Valor |
| --- | --- |
| PV Nominal | 0 kWp |
| BESS Capacidad | 0 kWh |
| BESS Potencia | 0 kW |

## Uso en Simulacion

```python
## Con PV + BESS

from citylearn.citylearn import CityLearnEnv
env = CityLearnEnv(schema='data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json')

## Solo Grid (baseline)

env = CityLearnEnv(schema='data/processed/citylearn/iquitos_ev_mall/schema_grid_only.json')
```

## Baseline vs Control (misma infraestructura, distinto agente)

- Baseline sin control: `schema_pv_bess.json` + agente `Uncontrolled` (EV al maximo).
- Control inteligente: `schema_pv_bess.json` + agente elegido (SAC/PPO/RBC).

La diferencia entre escenarios se obtiene por la politica del agente, no por cambios
en el schema.

## Resultados de entrenamiento (OE3)

Grafica comparativa de aprendizaje para SAC, PPO y A2C:

![Comparativa de entrenamiento OE3](training_comparison.png)

Graficas individuales de aprendizaje por agente:

![SAC entrenamiento](SAC_training.png)

![PPO entrenamiento](PPO_training.png)

![A2C entrenamiento](A2C_training.png)

CSV de metricas de entrenamiento:

Resumen numérico (mejor reward por episodio):

- SAC: reward_final=8,258.94, steps=87,595
- PPO: reward_final=8,578.47, steps=88,851
- A2C: reward_final=8,502.52, steps=96,531

- `../../analyses/oe3/training/SAC_training_metrics.csv`
- `../../analyses/oe3/training/PPO_training_metrics.csv`
- `../../analyses/oe3/training/A2C_training_metrics.csv`

## Validación de reducción de CO₂ (DATOS CORREGIDOS 2026-01-08)

**Línea Base Combinada:**

- Grid-only (red térmica): 5,596.26 tCO₂/año
- Tailpipe (gasolina evitada): 2,784.91 tCO₂/año
- **TOTAL BASE: 8,381.16 tCO₂/año**

**Resultados por Agente:**

| Agente | Emisiones (tCO₂/año) | Reducción vs Base |
| ------ | -------------------: | ----------------: |
| Uncontrolled | 2,475.06 | 70.47% |
| A2C | 2,476.32 | 70.45% |
| PPO | 2,499.15 | 70.18% |
| SAC | 2,657.36 | 68.29% |

**Proyección 20 años:** ~118,000 tCO₂ evitados

**Contribución al sector transporte de Iquitos:** 2.29% (5,906 / 258,250 tCO₂)

## Perfiles estocásticos de cargadores (charger_profile_variants)

La carpeta `data/processed/citylearn/iquitos_ev_mall/charger_profile_variants/`
contiene un CSV por escenario muestreado en la fase OE2 (PE/FC variables). El
campo `charger_profile_variants` del `schema_pv_bess.json` expone una lista de
metadatos que incluye:

- `scenario_id`: identificador único de escenario (1 es el escenario recomendado).
- `pe` / `fc`: probabilidad de evento y factor de carga usados para cada variante.
- `energy_day_kwh`: energía diaria asociada en kWh.
- `chargers_required`: número de cargadores calculado.
- `peak_sessions_per_hour`: sesiones pico horarias calculadas.
- `profile_path`: ruta relativa del CSV en `charger_profile_variants/`.
- `is_recommended`: true cuando corresponde al escenario principal.

Estos datos permiten que los agentes OE3 (por ejemplo SAC/ppo) obtengan perfiles
discretos para simular distintos escenarios de carga EV y enlacen el control de los
chargers con los datos de OE2. Basta con leer el esquema y usar `profile_path` para
abrir la variante deseada antes de ejecutar `simulate.py`.
