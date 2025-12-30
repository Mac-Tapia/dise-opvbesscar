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
- Parámetros: `oe1.site.coverage_required_pct: 0.65`, `oe2.solar.area_total_m2: 20637.0`, `oe2.solar.factor_diseno: 0.65`  
- Resultado OE2: área útil 13,414 m², 8,224 módulos, 2,591 kWp DC, 2,500 kW AC, 3,299 MWh/año
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
- Parámetros: `oe2.bess.dod: 0.90`, `c_rate: 0.50`, `efficiency_roundtrip: 0.95`, `autonomy_hours: 4.0`, `min_soc_percent: 10`
- Resultado OE2: capacidad 740 kWh, potencia 370 kW, DoD 80%, SOC mín 20%, eficiencia 90%, autonomía 4h
- Código: `src/iquitos_citylearn/oe2/bess.py`  
- Script: `scripts/run_oe2_bess.py`  
- Salidas: `data/interim/oe2/bess/bess_results.json` (capacity_kwh, autonomy_hours, peak_load_kw), `bess_simulation_hourly.csv`

**Cantidad de cargadores**  
- Indicador: potencia simultánea máxima y cantidad de cargadores.  
- Parámetros: `oe2.ev_fleet.pe_motos: 1.00`, `fc_motos: 1.00` (escenario recomendado 100%), `sockets_per_charger: 4`
- Resultado OE2: 33 cargadores, 129 sockets, 567 kWh/día EV, 283 kW pico, 927 vehículos/día efectivos
- Código: `src/iquitos_citylearn/oe2/chargers.py`  
- Script: `scripts/run_oe2_chargers.py`  
- Salidas: `data/interim/oe2/chargers/chargers_results.json` (peak_power_kw, n_chargers_recommended), `perfil_horario_carga.csv`

## Variable dependiente: Emisiones de CO₂

**Emisiones directas**  
- Indicadores: actividad base, emisiones base, emisiones por carga eléctrica.  
- Resultado OE3: Reducción directa 85,534 kgCO₂/año (uso eficiente PV/BESS vs red térmica)
- Código: `src/iquitos_citylearn/oe3/co2_table.py`  
- Script: `scripts/run_oe3_co2_table.py`  
- Salida: `analyses/oe3/co2_breakdown.csv` (direct_avoided_kgco2_y)

**Emisiones indirectas**  
- Indicadores: energía FV efectiva y CO₂ evitado por desplazamiento.  
- Resultado OE3: Reducción indirecta 9,971 kgCO₂/año (mayor aprovechamiento renovables)
- Código: `src/iquitos_citylearn/oe3/co2_table.py`  
- Script: `scripts/run_oe3_co2_table.py`  
- Salida: `analyses/oe3/co2_breakdown.csv` (indirect_avoided_kgco2_y)

**Reducción neta de CO₂**  
- Indicadores: CO₂ evitado total y proyección.  
- Resultado OE3: 
  - Baseline sin control PV+BESS: 103,184 kgCO₂/año
  - Con control A2C: 95,505 kgCO₂/año
  - **Reducción neta: 7,679 kgCO₂/año (~7.45%)**
  - Emisiones transporte: 111,761 kg (combustión) vs 7,967 kg (control eléctrico) = **92.87% reducción**
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
- Agentes evaluados: SAC (mejor reward 15,145), PPO (8,142), A2C (8,040) - todos 17,518 pasos
- **Agente seleccionado: A2C** (equilibrio entre cargadores, BESS y PV para cumplir OE.3)
- Configuración: 5 episodios, hidden_sizes [128, 128], device cuda:0, checkpoints cada 8760 pasos
- Código: `src/iquitos_citylearn/oe3/simulate.py`, `agents/sac.py`, `agents/ppo_sb3.py`, `agents/a2c_sb3.py`
- Script: `scripts/run_oe3_simulate.py`  
- Salidas: `outputs/oe3/simulations/simulation_summary.json`, `analyses/oe3/agent_comparison.csv`, `analyses/oe3/training/*.csv`

## Validación automatizada
- Script: `scripts/VALIDAR_CUMPLIMIENTO_ESTRICTO.py`  
- Salida: `REPORTE_CUMPLIMIENTO.json`
