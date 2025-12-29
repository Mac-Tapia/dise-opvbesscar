# Mapeo operacional - Tabla 9 (tesisvefinal)

Mapeo de cada dimensión e indicador de la Tabla 9 al código, parámetros y salidas del proyecto (sin modificar la redacción de la tesis).

## Variable independiente: Diseño de la infraestructura de carga inteligente

**Determinación de ubicación estratégica**  
- Indicadores: área disponible, capacidad de estacionamiento, accesibilidad/seguridad.  
- Parámetros: `configs/default.yaml` → `oe1.site.*`  
- Script: `scripts/run_oe1_location.py`  
- Salidas: `data/interim/oe1/location_summary.json`, `reports/oe1/location_summary.md`

**Área techada y área de estacionamiento**  
- Indicadores: área techada útil, % cobertura, restricciones físicas.  
- Parámetros: `oe1.site.coverage_required_pct`, `oe2.solar.area_total_m2`, `oe2.solar.factor_diseno`  
- Script: `scripts/run_oe2_solar.py`  
- Salidas: `data/interim/oe2/solar/solar_results.json`, `data/interim/oe2/solar/solar_technical_report.md`

**Disponibilidad de red eléctrica**  
- Indicadores: distancia a subestación, capacidad estimada (kVA), continuidad.  
- Parámetros: `oe1.site.distance_to_substation_m`, `oe1.grid_connection.*`  
- Script: `scripts/run_oe1_location.py`  
- Salidas: `data/interim/oe1/location_summary.json` (required_capacity_kva, continuity)

## Dimensionamiento de capacidad (OE2)

**Potencia de generación solar**  
- Indicadores: potencia FV (kWp), energía anual, área requerida.  
- Código: `src/iquitos_citylearn/oe2/solar_pvlib.py`  
- Script: `scripts/run_oe2_solar.py`  
- Salidas: `data/interim/oe2/solar/solar_results.json`, `data/interim/oe2/solar/pv_generation_timeseries.csv`, `data/interim/oe2/solar/pv_candidates_modules.csv`, `pv_candidates_inverters.csv`

**Capacidad nominal de almacenamiento**  
- Indicadores: autonomía, DoD, capacidad nominal, verificación vs picos.  
- Código: `src/iquitos_citylearn/oe2/bess.py`  
- Script: `scripts/run_oe2_bess.py`  
- Salidas: `data/interim/oe2/bess/bess_results.json` (capacity_kwh, autonomy_hours, peak_load_kw), `bess_simulation_hourly.csv`

**Cantidad de cargadores**  
- Indicador: potencia simultánea máxima y cantidad de cargadores.  
- Código: `src/iquitos_citylearn/oe2/chargers.py`  
- Script: `scripts/run_oe2_chargers.py`  
- Salidas: `data/interim/oe2/chargers/chargers_results.json` (peak_power_kw, n_chargers_recommended), `perfil_horario_carga.csv`

## Variable dependiente: Emisiones de CO₂

**Emisiones directas**  
- Indicadores: actividad base, emisiones base, emisiones por carga eléctrica.  
- Código: `src/iquitos_citylearn/oe3/co2_table.py`  
- Script: `scripts/run_oe3_co2_table.py`  
- Salida: `analyses/oe3/co2_breakdown.csv` (direct_avoided_kgco2_y)

**Emisiones indirectas**  
- Indicadores: energía FV efectiva y CO₂ evitado por desplazamiento.  
- Código: `src/iquitos_citylearn/oe3/co2_table.py`  
- Script: `scripts/run_oe3_co2_table.py`  
- Salida: `analyses/oe3/co2_breakdown.csv` (indirect_avoided_kgco2_y)

**Reducción neta de CO₂**  
- Indicadores: CO₂ evitado total y proyección.  
- Código: `src/iquitos_citylearn/oe3/co2_table.py`  
- Script: `scripts/run_oe3_co2_table.py`  
- Salida: `analyses/oe3/co2_breakdown.csv` (net_avoided_kgco2_y, net_avoided_tco2_20y)

## Selección de agente inteligente de gestión de carga (OE3)

**Arquitectura de control**  
- Indicadores: control centralizado y recursos controlables.  
- Código: `src/iquitos_citylearn/oe3/dataset_builder.py`  
- Script: `scripts/run_oe3_build_dataset.py`  
- Salida: `data/processed/citylearn/iquitos_ev_mall/schema.json`

**Tipo de carga EV**  
- Indicadores: compatibilidad de carga y perfiles horarios.  
- Código: `src/iquitos_citylearn/oe3/dataset_builder.py`  
- Salidas: `data/processed/citylearn/iquitos_ev_mall/charger_mall_*.csv`, `data/interim/oe2/chargers/chargers_hourly_profiles.csv`

**Algoritmo de optimización (comparativo)**  
- Indicadores: KPIs y selección del agente con menor CO₂.  
- Código: `src/iquitos_citylearn/oe3/simulate.py`  
- Script: `scripts/run_oe3_simulate.py`  
- Salidas: `outputs/oe3/simulations/simulation_summary.json`, `analyses/oe3/agent_comparison.csv`

## Validación automatizada
- Script: `scripts/VALIDAR_CUMPLIMIENTO_ESTRICTO.py`  
- Salida: `REPORTE_CUMPLIMIENTO.json`
