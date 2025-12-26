# Schemas OE3 Actualizados

## Fecha de Actualizacion

2025-12-22

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

Resumen num?rico (mejor y ?ltimo reward):

- SAC: mejor=15145.8391, ?ltimo=15145.8391, pasos=17518
- PPO: mejor=8142.5492, ?ltimo=8142.5492, pasos=17518
- A2C: mejor=8040.8059, ?ltimo=8040.8059, pasos=17518


- `../../analyses/oe3/training/SAC_training_metrics.csv`
- `../../analyses/oe3/training/PPO_training_metrics.csv`
- `../../analyses/oe3/training/A2C_training_metrics.csv`
Validación de reducción de CO2:

- Agente seleccionado: A2C (SB3) — equilibrio entre cargadores, BESS y PV para cumplir OE.3.
- CO2 sin control (PV+BESS): 103,184 kgCO2/año (línea base sin agentes inteligentes).
- CO2 con control: 95,505 kgCO2/año (mejor escenario con A2C).
- Reducción neta: 7,679 kgCO2/año (~7.45%) que acredita la contribución a OE.3.
- Directa: 85,534 kgCO2/año (mejor uso de PV/BESS y menor dependencia de la matriz).
- Indirecta: 9,971 kgCO2/año (mayor aprovechamiento de renovables).
- Total: 95,504 kgCO2/año evitados con el agente A2C.
- Emisiones de transporte: 111,761 kgCO2/año sin control vs 7,967 kgCO2/año con control (92.87% menos).

El bloque anterior resume cómo A2C satisface OE.3 al controlar cargas EV, BESS y red para maximizar los excedentes solares y cuantificar las reducciones directas/indirectas de CO2.



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
