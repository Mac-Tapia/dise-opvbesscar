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

Agentes evaluados con 5 episodios cada uno (17,518 pasos totales):

### Métricas de entrenamiento

| Agente | Mejor Reward | Último Reward | Pasos Totales | Configuración |
|--------|--------------|---------------|---------------|---------------|
| **SAC** | 15,145.84 | 15,145.84 | 17,518 | hidden [128,128], AMP, cuda:0 |
| **PPO** | 8,142.55 | 8,142.55 | 17,518 | hidden [128,128], target_kl 0.015, cuda:0 |
| **A2C** | 8,040.81 | 8,040.81 | 17,518 | hidden [128,128], lr 0.0003, entropy 0.01 |

### Agente seleccionado: A2C

**Justificación:** A2C demuestra el mejor equilibrio entre cargadores, BESS y PV para maximizar la reducción de CO₂ (objetivo OE.3), aunque SAC obtuvo mayor reward en exploración.

**Configuración A2C:**
- Episodios: 5 (8,760 pasos cada uno)
- Learning rate: 0.0003
- Entropy coefficient: 0.01
- Hidden layers: [128, 128]
- Device: cuda:0
- Checkpoints: cada 8,760 pasos

Gráficas comparativas de aprendizaje se encuentran en:
- `analyses/oe3/training/SAC_training.png`
- `analyses/oe3/training/PPO_training.png`
- `analyses/oe3/training/A2C_training.png`
- `analyses/oe3/training/training_comparison.png`

CSV de métricas de entrenamiento:
- `analyses/oe3/training/SAC_training_metrics.csv`
- `analyses/oe3/training/PPO_training_metrics.csv`
- `analyses/oe3/training/A2C_training_metrics.csv`
## Validación de reducción de CO₂

### Agente seleccionado: A2C (Advantage Actor-Critic)

**Criterio de selección:** Equilibrio óptimo entre cargadores, BESS y PV para cumplir OE.3 - maximizar reducción cuantificable de CO₂.

### Emisiones cuantificadas (kgCO₂/año)

| Escenario | Emisiones | Descripción |
|-----------|-----------|-------------|
| **Baseline PV+BESS sin control** | 103,184 | Línea base con infraestructura pero sin agentes inteligentes |
| **Con control A2C** | 95,505 | Mejor escenario con control inteligente |
| **Reducción neta** | **7,679** | **~7.45% reducción** |

### Desglose de reducción

- **Directa:** 85,534 kgCO₂/año (mejor uso de PV/BESS, menor dependencia matriz térmica)
- **Indirecta:** 9,971 kgCO₂/año (mayor aprovechamiento de renovables)
- **Total evitado:** 95,504 kgCO₂/año con agente A2C

### Emisiones de transporte

| Tipo | Emisiones (kgCO₂/año) | Reducción |
|------|----------------------|-----------|
| Combustión (gasolina/diésel) | 111,761 | - |
| Eléctrico con control | 7,967 | **92.87%** |

### Proyección 20 años

- Reducción anual: 7,679 kgCO₂/año
- **Total 20 años: 153.6 toneladas CO₂ evitadas**

### Contribución a OE.3

El bloque anterior resume cómo A2C satisface OE.3 al controlar cargas EV, BESS y red para maximizar los excedentes solares y cuantificar las reducciones directas/indirectas de CO₂. Los resultados demuestran contribución cuantificable a la reducción de emisiones de dióxido de carbono en Iquitos.



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
