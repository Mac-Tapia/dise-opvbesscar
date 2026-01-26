# Proyecto Iquitos EV + PV/BESS (OE2 → OE3)

Este repositorio contiene el pipeline de dimensionamiento (OE2) y control
inteligente (OE3) para un sistema de carga de motos y mototaxis eléctricos con
integración fotovoltaica y BESS en Iquitos, Perú.

## Alcance

- **OE2 (dimensionamiento):** PV 4,050 kWp (Kyocera KS20) con inversor Eaton
  - Xpert1670 (2 unidades, 31 módulos por string, 6,472 strings, 200,632 módulos
    - totales), BESS 2 MWh/1.2 MW y 128 cargadores (112 motos @2 kW, 16 mototaxis
      - @3 kW).
- **OE3 (control RL):** Agentes SAC/PPO/A2C en CityLearn v2 para minimizar CO₂,
  - costo y picos, maximizando uso solar y satisfacción EV.
- **Reducción CO₂ anual (capacidad OE2):**
  - Directa: 3,081.20 tCO₂/año (gasolina → EV).
  - Indirecta: 3,626.66 tCO₂/año (PV/BESS desplaza red).
  - Neta: 6,707.86 tCO₂/año. Emisiones con PV/BESS: 2,501.49 tCO₂/año.

## Requisitos

- Python 3.11 (activar `.venv`).
- Dependencias: `pip install -r requirements.txt` (y
  - `requirements-training.txt` para RL).
- Herramientas: `git`, `poetry` opcional, Docker (para despliegues).

## Estructura clave

- `configs/default.yaml`: parámetros OE2/OE3 (PV, BESS, flota, recompensas).
- `scripts/run_oe2_solar.py`: dimensionamiento PV (pvlib + PVGIS).
- `data/interim/oe2/`: artefactos de entrada OE2 (solar, BESS, chargers).
- `reports/oe2/co2_breakdown/`: tablas de reducción de CO₂.
- `src/iquitos_citylearn/oe3/`: agentes y dataset builder CityLearn.
- `COMPARACION_BASELINE_VS_RL.txt`: resumen cuantitativo baseline vs RL.

## Uso rápido

<!-- markdownlint-disable MD013 -->
```bash
# Activar entorno
python -m venv .venv
./.venv/Scripts/activate  # en Windows

# Dimensionamiento solar (Eaton Xpert1670)
python -m scripts.run_oe2_solar --config configs/default.yaml --no-plots

# Ejecutar pipeline visible OE3
python run_pipeline_visible.py
```bash
<!-- markdownlint-enable MD013 -->

## Referencias de resultados

- CO₂: `reports/oe2/co2_breakdown/oe2_co2_breakdown.json`
- Solar (Eaton Xpert1670): `data/interim/oe2/solar/solar_results.json` y
  - `solar_technical_report.md`
- Documentación RL: `docs/INFORME_UNICO_ENTRENAMIENTO_TIER2.md`,
  - `COMPARACION_BASELINE_VS_RL.txt`

## 📖 Documentación Consolidada

Essential guides consolidated in root directory:

- **[QUICKSTART.md](QUICKSTART.md)** - Start here: 5-minute setup guide
- **[COMANDOS_EJECUTABLES.md](COMANDOS_EJECUTABLES.md)** - All executable commands (dataset build, training, comparisons)
- **[STATUS_ACTUAL_2026_01_25.md](STATUS_ACTUAL_2026_01_25.md)** - Current system status and timeline
- **[RESUMEN_EJECUTIVO_ENTRENAMIENTO_OE3.md](RESUMEN_EJECUTIVO_ENTRENAMIENTO_OE3.md)** - Training results and agent comparisons
- **[CONFIGURACIONES_OPTIMAS_AGENTES_OE3.md](CONFIGURACIONES_OPTIMAS_AGENTES_OE3.md)** - Agent hyperparameters and architecture
- **[ARQUITECTURA_TOMAS_INDEPENDIENTES.md](ARQUITECTURA_TOMAS_INDEPENDIENTES.md)** - System architecture and design
- **[TESTING_FOLDER_ANALYSIS.md](TESTING_FOLDER_ANALYSIS.md)** - Testing folder structure and utilities
- **[PROJECT_VERIFICATION_FINAL.md](PROJECT_VERIFICATION_FINAL.md)** - Final project verification report
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines and standards

### Additional Resources
- `reports/oe2/co2_breakdown/oe2_co2_breakdown.{json,csv}` - CO₂ reduction breakdown
- `data/interim/oe2/solar/solar_technical_report.md` - PV technical specifications
- `docs/` - Additional technical documentation
- `historical/` - Archived one-time scripts (for reference only)
  - utilidades.

## Despliegue

- Docker: `docker/` y `docker-compose*.yml`
- Kubernetes: `k8s-deployment.yaml`, `k8s_manager.py`

## Flujo de trabajo

1) **OE2 (dimensionamiento)**: se generan PV (pvlib+PVGIS), BESS fijo y 128
cargadores (perfiles horarios por cargador). Artefactos en `data/interim/oe2/`.
2) **OE3 (dataset)**: `run_pipeline_visible.py`construye el schema CityLearn v2
con PV/BESS y perfiles EV reales.
3) **Entrenamiento RL**: agentes SAC/PPO/A2C (2 episodios seriales) con función
multiobjetivo (CO2 0.35, costo 0.25, solar 0.20, EV 0.15, grid 0.05).
4) **Evaluación**: métricas CO₂, costos, picos y uso solar; reportes en
`analyses/`y `reports/`.

## Objetivos

- Minimizar CO₂ anual (directo: gasolina → EV; indirecto: PV/BESS desplaza red).
- Reducir costos y picos de red sin sacrificar satisfacción EV.
- Maximizar autoconsumo solar y estabilidad de red.

## Desarrollo del proyecto

- Datos meteo: PVGIS TMY, modelo Sandia (pvlib).
- Componentes: Kyocera KS20; inversor Eaton Xpert1670 (2 uds, 31
  - módulos/string, 6,472 strings, 200,632 módulos).
- BESS: 2 MWh / 1.2 MW (fijo, DoD 80%, eff 95%).
- Cargadores EV: **32 cargadores físicos × 4 tomas = 128 tomas controlables**:
  - Playa Motos: 28 cargadores × 4 tomas × 2.0 kW = **224 kW**
  - Playa Mototaxis: 4 cargadores × 4 tomas × 3.0 kW = **48 kW**
  - **Potencia total instalada: 272 kW**
  - 3,061 vehículos/día (30 min sesión Modo 3, 92% utilización)
- RL: CityLearn v2, recompensas multiobjetivo; scripts en
  - `src/iquitos_citylearn/oe3/` y `scripts/`.

## Resultados (referencia OE2 - actualizado 2026-01-24)

- Reducción directa: 3,081.20 tCO₂/año.
- Reducción indirecta: 3,626.66 tCO₂/año.
- Reducción neta: 6,707.86 tCO₂/año (emisiones con PV/BESS: 2,501.49 tCO₂/año).
- **Generación PV anual: 8.31 GWh (AC)**, yield 2,051 kWh/kWp·año, Factor
  - capacidad 29.6%, PR 123.3%.
- **Potencia DC instalada:** 4,050 kWp (4.05 MWp)
- **Perfil horario solar:** 05:00 - 17:00 hora local Iquitos (UTC-5), pico
  - ~11:00 AM.
- **Área utilizada:** 14,445.5 m² (70% del área total disponible).

## Discusión

- La mayor ganancia viene de la electrificación (directa), pero el PV/BESS
  - aporta reducción adicional similar en magnitud.
- La capacidad de carga (3,061 vehículos/día) dimensiona el impacto;
  - entrenamientos OE3 deben reflejar perfiles horarios reales para capturar picos
    - y autoconsumo.
- El control RL aún requiere ajustes (ver
  - `INFORME_UNICO_ENTRENAMIENTO_TIER2.md`): episodios cortos y señal de
    - recompensa plana limitaron el aprendizaje.

## Conclusiones y próximos pasos

- Infraestructura dimensionada permite reducir ~6.7 ktCO₂/año combinando
  - electrificación y PV/BESS.
- Prioridad: mejorar señal de recompensa/observables para que SAC/PPO/A2C
  - aprendan a desplazar carga hacia ventanas solares y evitar picos.
- Recomendar retraining con recompensas reforzadas en CO₂ pico/importación y
  - monitoreo de autoconsumo solar; luego actualizar reportes de resultados.
