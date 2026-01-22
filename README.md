# Proyecto Iquitos EV + PV/BESS (OE2 → OE3)

Este repositorio contiene el pipeline de dimensionamiento (OE2) y control inteligente (OE3) para un sistema de carga de motos y mototaxis eléctricos con integración fotovoltaica y BESS en Iquitos, Perú.

## Alcance
- **OE2 (dimensionamiento):** PV 4,162 kWp (Kyocera KS20) con inversor Eaton Xpert1670 (2 unidades, 31 módulos por string, 6,009 strings), BESS 2 MWh/1.2 MW y 128 cargadores (112 motos @2 kW, 16 mototaxis @3 kW).
- **OE3 (control RL):** Agentes SAC/PPO/A2C en CityLearn v2 para minimizar CO₂, costo y picos, maximizando uso solar y satisfacción EV.
- **Reducción CO₂ anual (capacidad OE2):**
  - Directa: 3,081.20 tCO₂/año (gasolina → EV).
  - Indirecta: 3,626.66 tCO₂/año (PV/BESS desplaza red).
  - Neta: 6,707.86 tCO₂/año. Emisiones con PV/BESS: 2,501.49 tCO₂/año.

## Requisitos
- Python 3.11 (activar `.venv`).
- Dependencias: `pip install -r requirements.txt` (y `requirements-training.txt` para RL).
- Herramientas: `git`, `poetry` opcional, Docker (para despliegues).

## Estructura clave
- `configs/default.yaml`: parámetros OE2/OE3 (PV, BESS, flota, recompensas).
- `scripts/run_oe2_solar.py`: dimensionamiento PV (pvlib + PVGIS).
- `data/interim/oe2/`: artefactos de entrada OE2 (solar, BESS, chargers).
- `reports/oe2/co2_breakdown/`: tablas de reducción de CO₂.
- `src/iquitos_citylearn/oe3/`: agentes y dataset builder CityLearn.
- `COMPARACION_BASELINE_VS_RL.txt`: resumen cuantitativo baseline vs RL.

## Uso rápido
```bash
# Activar entorno
python -m venv .venv
./.venv/Scripts/activate  # en Windows

# Dimensionamiento solar (Eaton Xpert1670)
python -m scripts.run_oe2_solar --config configs/default.yaml --no-plots

# Ejecutar pipeline visible OE3
python run_pipeline_visible.py
```

## Referencias de resultados
- CO₂: `reports/oe2/co2_breakdown/oe2_co2_breakdown.json`
- Solar (Eaton Xpert1670): `data/interim/oe2/solar/solar_results.json` y `solar_technical_report.md`
- Documentación RL: `docs/INFORME_UNICO_ENTRENAMIENTO_TIER2.md`, `COMPARACION_BASELINE_VS_RL.txt`

## Despliegue
- Docker: `docker/` y `docker-compose*.yml`
- Kubernetes: `k8s-deployment.yaml`, `k8s_manager.py`
