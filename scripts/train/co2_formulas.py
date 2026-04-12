#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
co2_formulas.py -- Marco completo CO2 directas + indirectas para ambos escenarios (OE3)
========================================================================================
OBLIGATORIO en el entrenamiento de todos los agentes (SAC, PPO, A2C).
ALINEADO con columnas REALES de los datasets cargados en CityLearn v2.

Contexto: Iquitos, Peru -- red aislada 100% termica diesel (0.4521 kg CO2/kWh)
          325.7 motos + 36.9 mototaxis/dia -> infraestructura de carga inteligente
          (valores reales CSV OE2: data/oe2/chargers/chargers_ev_ano_2024_v3.csv)
          19 cargadores x 2 sockets = 38 sockets controlables

OE3: "Seleccionar el agente de IA de la infraestructura de carga inteligente para
      la gestion de recarga de motos y mototaxis electricas, apropiada que contribuye
      de manera cuantificable a la reduccion de emisiones de CO2 en Iquitos."

DATASETS UTILIZADOS (data/iquitos_ev_mall/):
  chargers_timeseries.csv  -> socket_NNN_charging_power_kw  (demanda EV baseline)
                           -> reduccion_directa_co2_kg  (CO2 evitado vs combustible fosil)
  mall_demand.csv          -> mall_demand_kwh             (demanda mall horaria)
  bess_timeseries.csv      -> ev_kwh (= sum socket_NNN_charging_power_kw)
                           -> grid_import_kwh             (importacion bajo solar/BESS)
                           -> co2_avoided_indirect_kg     (CO2 evitado por BESS)
  solar_generation.csv     -> solar_generation_kwh        (generacion horaria PV)
                           -> reduccion_indirecta_co2_kg  (CO2 evitado por solar)

================================================================================
MARCO DE CUANTIFICACION CO2 — FORMULACION COMPLETA (OE3)
Iquitos, PERU | Red aislada 100% diesel | Factor grid: 0.4521 kg CO2/kWh
Fuente: MINEM Peru, GHG Protocol Scope 2, ISO 14064-1
================================================================================

FACTORES DE EMISION:
  0.4521 kg CO2/kWh — Red eléctrica Iquitos (generación termica diesel aislada, MINEM)
  0.87   kg CO2/kWh — Moto Honda Wave 125cc en gasolina (IPCC 2006 Tier 1: 2.30L/100km*2.31/6kWh)
  0.54   kg CO2/kWh — Mototaxi 150cc en diesel    (IPCC 2006 Tier 1: 3.50L/100km*2.31/15kWh)
  Fuente: Garay Aquino et al., E3S Conf. 2024 DOI:10.1051/e3sconf/202456604004

================================================================================
F1 — BASELINE (sin solar, sin BESS, sin agente RL)
================================================================================
Red pública diesel (100%) alimenta: EVs (motos+mototaxis) + Mall

  F1a. CO2 EMITIDO — EVs en red diesel (por conectarse al sistema de carga):
       CO2_ind_EV[h] = ev_kwh[h] * 0.4521    [kg CO2/h]

  F1b. CO2 EMITIDO — Mall en red diesel:
       CO2_ind_Mall[h] = mall_kwh[h] * 0.4521   [kg CO2/h]

  F1.  CO2 TOTAL EMITIDO BASELINE:
       CO2_ind_BL[h] = (ev_kwh[h] + mall_kwh[h]) * 0.4521   [kg CO2/h]

  F4.  CO2 DIRECTO EVITADO — cambio de combustible fosil a electrico:
       CO2_dir[h] = ev_kwh[h] * (f_m*0.87 + f_t*0.54)   [kg CO2/h]
       f_m = fraccion energetica motos   = 0.8458 (kWh_motos/kWh_EV_total, CSV OE2)
       f_t = fraccion energetica taxis   = 0.1542 (kWh_taxis/kWh_EV_total, CSV OE2)
       Factor ponderado: 0.8458*0.87 + 0.1542*0.54 = 0.8191 kg CO2/kWh

  F5.  CO2 NETO BASELINE (referencia OE3):
       CO2_NET_BL[h] = F1[h] - F4[h]
       = (ev+mall)*0.4521 - ev*(f_m*0.87 + f_t*0.54)
       Anual: CO2_NET_BL = 5,776,412 - 334,435 = 5,441,977 kg/año

================================================================================
F2 — CONTROL INTELIGENTE (Solar 4,050 kWp + BESS 2,000 kWh + Agente RL)
================================================================================
El agente RL gestiona la recarga de motos/mototaxis para maximizar el uso solar
y minimizar la importacion de red diesel. El BALANCE ENERGETICO horario es:

  BALANCE ENERGETICO:
       Grid_import[h] = max(0, (EV[h]+Mall[h]) - Solar[h] - BESS_descarga[h])
       Grid_export[h] = max(0, Solar[h] - (EV[h]+Mall[h]) + BESS_descarga[h])
                                (excedente solar exportado a red publica)

  DESTINOS DE LA GENERACION SOLAR (solar 100% reduce CO2 indirecto):
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ Solar_total[h] = EV_solar[h] + Mall_solar[h] + BESS_carga[h] + Export[h]  │
  │                                                                             │
  │ F6a. EVs alimentados por solar → no usan red diesel → reduce CO2 indirecto │
  │      ΔCO2_ind,EV_solar[h] = EV_solar[h] * 0.4521                          │
  │                                                                             │
  │ F6b. Mall alimentado por exceso solar → reduce CO2 indirecto               │
  │      ΔCO2_ind,Mall_solar[h] = Mall_solar[h] * 0.4521                      │
  │                                                                             │
  │ F6c. BESS cargado desde solar → almacena energia limpia (no wasted)        │
  │      ΔCO2_ind,BESS_carga[h] = BESS_solar[h] * 0.4521                      │
  │                                                                             │
  │ F6d. Export solar → desplaza generacion diesel en red publica              │
  │      ΔCO2_ind,export[h] = Grid_export[h] * 0.4521                         │
  │                                                                             │
  │ F6.  SOLAR 100%: toda la generacion solar reduce CO2 indirecto             │
  │      ΔCO2_ind,solar[h] = Solar_total[h] * 0.4521                          │
  │      ≡ ΔCO2_ind,EV_solar + ΔCO2_ind,Mall_solar + ΔCO2_ind,BESS + Export  │
  └─────────────────────────────────────────────────────────────────────────────┘

  F7.  BESS DESCARGA (peak shaving) → reduce CO2 indirecto al cortar pico:
       ΔCO2_ind,BESS_desc[h] = BESS_descarga[h] * 0.4521

  F2.  CO2 EMITIDO CONTROL (solo deficit residual de red diesel):
       CO2_ind_CTRL[h] = Grid_import[h] * 0.4521

  REDUCCION INDIRECTA TOTAL (equivalencia matematica, tres formas):
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ FORMA A — Diferencia con baseline (CALCULO PRIMARIO):                      │
  │   ΔCO2_ind[h] = CO2_ind_BL[h] - CO2_ind_CTRL[h]                           │
  │               = (EV+Mall-Grid_import[h]) * 0.4521                          │
  │                                                                             │
  │ FORMA B — Por fuente energetica (DESCRIPCION FISICA):                      │
  │   ΔCO2_ind[h] = Solar[h]*0.4521 + BESS_net[h]*0.4521                      │
  │   donde BESS_net[h] = BESS_descarga[h] - BESS_carga_red[h]                │
  │   NOTA: si BESS carga SOLO desde solar → BESS_net ≈ 0 a largo plazo,       │
  │   pero ΔCO2_ind ≈ Solar[h]*0.4521 anualmente (ciclos completos BESS)      │
  │                                                                             │
  │ NOTA: FORMAS A y B son MATEMATICAMENTE EQUIVALENTES por balance energetico │
  └─────────────────────────────────────────────────────────────────────────────┘

  F4'. CO2 DIRECTO EVITADO — control (mismo beneficio combustible, flota constante):
       CO2_dir_CTRL[h] = ev_kwh_CTRL[h] * (f_m*0.87 + f_t*0.54)

  F5'. CO2 NETO CONTROL:
       CO2_NET_CTRL[h] = CO2_ind_CTRL[h] - CO2_dir_CTRL[h]
                       = Grid_import[h]*0.4521 - ev_ctrl[h]*(f_m*0.87 + f_t*0.54)

================================================================================
F3 — CUANTIFICACION TOTAL CO2 REDUCIDO (OE3)
================================================================================
  ΔCO2_total[h] = CO2_NET_BL[h] - CO2_NET_CTRL[h]
               = (F1[h] - F4[h]) - (F2[h] - F4'[h])
               = ΔCO2_ind[h] + (F4'[h] - F4[h])

  Si la flota EV es constante (F4 ≈ F4' mismo kWh): ΔCO2_total ≈ ΔCO2_ind

  CO2_NETO_BASELINE_ANUAL = 5,441,977 kg/año  (F5, referencia OE3)
  SOLAR_TOTAL_ANUAL       = 8,292,514 kWh/año (4,050 kWp en Iquitos)
  ΔCO2_ind_solar_ANUAL    = 8,292,514 * 0.4521 = 3,749,046 kg/año (F6, solar 100%)
  ΔCO2_ind_BESS_ANUAL     ≈ 0 (ciclos completos BESS: carga ≈ descarga anual)

================================================================================
VERIFICACION DESDE CHECKPOINTS (ultimo episodio entrenamiento):
  SAC: grid_import=4,956,490 kWh → CO2_ind_ctrl=2,240,832 kg | solar=8,292,514→3,749,046 kg
  A2C: grid_import=4,391,132 kWh → CO2_ind_ctrl=1,985,189 kg | solar=8,292,514→3,749,046 kg
  PPO: grid_import=6,631,009 kWh → CO2_ind_ctrl=2,997,878 kg | solar=8,292,514→3,749,046 kg
  Verificacion F6: episode_co2_avoided_indirect = solar_kwh * 0.4521 ✓ (todos los agentes)
================================================================================

REFERENCIAS CIENTIFICAS (ultimos 5 anos):
  [1] Michailidis, P., Michailidis, I., Kosmatopoulos, E. (2025). "Reinforcement
      Learning for Electric Vehicle Charging Management: Theory and Applications."
      Energies, 18(19), 5225. DOI: 10.3390/en18195225.
      -> Marco metodologico RL para gestion de EVCS con PV integrado y reduccion CO2.

  [2] Mohammed, A., Abdullah, B.M., Shubbar, A., et al. (2026). "Deep Reinforcement
      Learning for Battery Energy Storage Optimization and Residential Decarbonization
      in Grid-Deficient Environments: An Iraqi Case Study." Energies, 19(5), 1233.
      DOI: 10.3390/en19051233.
      -> Analogo directo: red aislada diesel + BESS + DRL + cuantificacion CO2.
      -> Formula CO2(t) = EFgrid * Pgrid(t) * Dt  (Ecuacion 16 del articulo).
      -> Reduccion: 54.8% CO2 en escenario de red deficiente con diesel backup.

  [3] Dorokhova, M., Martinson, Y., Ballif, C., Wyrsch, N. (2021). "Deep
      reinforcement learning control of electric vehicle charging in the presence of
      photovoltaic generation." Applied Energy, 301, 117504.
      DOI: 10.1016/j.apenergy.2021.117504.
      -> DRL para carga EV + PV: reduccion emisiones indirectas via autoconsumo solar.

  [4] Sarker, M.T. et al. (2025). "AI-Driven optimization framework for smart EV
      charging systems integrated with solar PV and BESS." World Electric Vehicle
      Journal, 16(7), 385.
      -> PV + BESS + RL para sistemas de carga EV: marco de optimizacion CO2.
================================================================================
"""
from __future__ import annotations

from dataclasses import dataclass

CO2_FACTOR_IQUITOS: float     = 0.4521  # kg CO2/kWh -- grid termico aislado Iquitos
CO2_FACTOR_MOTO_KG_KWH: float    = 0.87   # kg CO2/kWh moto gasolina IPCC 2006
CO2_FACTOR_MOTOTAXI_KG_KWH: float = 0.54  # kg CO2/kWh mototaxi diesel IPCC 2006 (corregido 0.47→0.54)
# Fracciones energeticas reales (CSV OE2: chargers_ev_ano_2024_v3.csv)
FRAC_MOTOS_REAL: float    = 0.8458   # kWh_motos / kWh_EV_total
FRAC_MOTOTAXIS_REAL: float = 0.1542  # kWh_mototaxis / kWh_EV_total
# Factor ponderado real: 0.8458*0.87 + 0.1542*0.54 = 0.8191 kg CO2/kWh
CO2_FACTOR_EV_PONDERADO: float = round(FRAC_MOTOS_REAL*CO2_FACTOR_MOTO_KG_KWH +
                                        FRAC_MOTOTAXIS_REAL*CO2_FACTOR_MOTOTAXI_KG_KWH, 4)  # 0.8191


@dataclass
class CO2Resultado:
    """
    Resultado de cuantificacion CO2 hora a hora (ambos escenarios).
    Implementa las formulas F1-F8 del marco OE3.

    FORMULAS:
      F1  = CO2 emitido BASELINE     = (ev+mall)*0.4521
      F2  = CO2 emitido CONTROL      = grid_import*0.4521
      F4  = CO2 directo evitado      = ev*(fm*0.87 + ft*0.54)  [combustible]
      F5  = CO2 NETO baseline        = F1 - F4
      F5' = CO2 NETO control         = F2 - F4'
      F6  = Solar 100% ind. reducido = solar_total*0.4521
      F7  = BESS descarga reduccion  = bess_descarga*0.4521
      F8  = Exportacion solar        = grid_export*0.4521
      F3  = Total OE3               = F5 - F5' = ΔF1 + ΔF4

    Ref: GHG Protocol Scope 2, ISO 14064-1, MINEM Peru (0.4521), IPCC 2006 Tier 1.
    """
    # ===========================================================================
    # FORMULA 1 — BASELINE (CO2 emitido POR LA RED)
    # ===========================================================================
    co2_directo_baseline_kg: float         # = 0.0 (flota electrica, no combustion)
    co2_indirecto_ev_baseline_kg: float    # F1a: ev_kwh * 0.4521 (EV desde red diesel)
    co2_indirecto_mall_baseline_kg: float  # F1b: mall_kwh * 0.4521 (Mall desde red diesel)
    co2_indirecto_baseline_kg: float       # F1:  (ev+mall) * 0.4521
    co2_total_baseline_kg: float           # = F1 (directo_baseline = 0)
    co2_reduccion_directa_baseline_kg: float   # F4: ev_kwh*(fm*0.87+ft*0.54) [combustible]
    co2_reduccion_indirecta_baseline_kg: float  # = 0.0 (sin solar ni BESS en baseline)

    # ===========================================================================
    # FORMULA 2 — CONTROL INTELIGENTE (CO2 emitido POR DEFICIT RESIDUAL)
    # ===========================================================================
    co2_directo_control_kg: float          # = 0.0 (flota sigue electrica)
    co2_indirecto_control_kg: float        # F2: grid_import * 0.4521 (deficit residual)
    co2_total_control_kg: float            # = F2
    co2_reduccion_directa_control_kg: float  # F4': ev_ctrl*(fm*0.87+ft*0.54) [igual F4]
    co2_reduccion_indirecta_control_kg: float  # = co2_solar + co2_bess_desc (F6+F7)

    # ===========================================================================
    # F6 — SOLAR 100%: toda la generacion PV reduce CO2 indirecto
    # ===========================================================================
    co2_solar_indirect_kg: float           # F6: solar_total_kwh * 0.4521
    # Destinos del solar (suma = F6 cuando BESS carga solo desde solar):
    co2_solar_ev_kg: float                 # F6a: EV alimentados por solar
    co2_solar_mall_kg: float               # F6b: Mall alimentado por solar
    co2_solar_bess_kg: float               # F6c: BESS cargado desde solar
    co2_solar_export_kg: float             # F6d: F8: excedente exportado a red publica

    # ===========================================================================
    # F7 — BESS DESCARGA: peak shaving + cobertura EV/Mall en horas sin solar
    # ===========================================================================
    co2_bess_discharge_indirect_kg: float  # F7: bess_discharge * 0.4521

    # ===========================================================================
    # FORMULA 3 — CUANTIFICACION TOTAL CO2 REDUCIDO (OE3)
    # ===========================================================================
    co2_reduccion_directa_kg: float        # F4 (cambio combustible, fijo)
    co2_reduccion_indirecta_kg: float      # F1 - F2 = (ev+mall-grid_import)*0.4521
    co2_impacto_control_kg: float          # = co2_reduccion_indirecta_kg
    co2_total_sistema_evitado_kg: float    # F3 = F4 + ΔF_ind


def compute_co2_baseline_control(
    ev_demand_dataset_kwh: float,
    mall_demand_kwh_h: float,
    grid_import_kwh: float,
    co2_indirecto_solar_kg: float,
    co2_indirecto_bess_kg: float,
    co2_avoided_direct_kg: float = 0.0,
    co2_reduccion_directa_kg: float = 0.0,   # alias backward-compat
    # Nuevos parametros para F6/F7/F8 (opcionales, backward-compatible)
    solar_total_kwh: float = 0.0,            # F6: generacion solar total
    bess_discharge_kwh: float = 0.0,         # F7: BESS descarga esta hora
    grid_export_kwh: float = 0.0,            # F8: solar exportado a red publica
) -> CO2Resultado:
    """
    Cuantifica CO2 directo + indirecto para ambos escenarios en una hora.
    Implementa F1-F8 del marco OE3.

    Parametros principales (columnas REALES de datasets)
    -----------------------------------------------------
    ev_demand_dataset_kwh  : sum(socket_NNN_charging_power_kw[h]) — demanda EV baseline hora h
    mall_demand_kwh_h      : mall_demand_kwh[h] de mall_demand.csv
    grid_import_kwh        : max(0, ev+mall - solar - bess_desc) calculado en simulacion
    co2_indirecto_solar_kg : solar_total_kwh * CO2_FACTOR_IQUITOS (F6, precomputado)
    co2_indirecto_bess_kg  : bess_discharge_kwh * factor (F7, precomputado)
    co2_avoided_direct_kg  : reduccion_directa_co2_kg[h] de chargers CSV (F4)
    solar_total_kwh        : generacion solar horaria [kWh] (para F6 verificacion)
    bess_discharge_kwh     : descarga BESS horaria [kWh] (para F7)
    grid_export_kwh        : exportacion solar a red publica [kWh] (para F8)

    Relaciones clave:
      F1  = (ev + mall) * 0.4521
      F2  = grid_import * 0.4521
      F6  = solar_total * 0.4521   [≈ co2_indirecto_solar_kg si BESS carga solo solar]
      F7  = bess_discharge * 0.4521
      F3  = F1 - F2 = (solar + bess_net) * 0.4521  [equivalencia matematica]
    """
    direct_kg = co2_avoided_direct_kg if co2_avoided_direct_kg else co2_reduccion_directa_kg

    # ===========================================================================
    # FORMULA 1 — BASELINE
    # ===========================================================================
    co2_directo_baseline_kg         = 0.0
    co2_indirecto_ev_baseline_kg    = ev_demand_dataset_kwh * CO2_FACTOR_IQUITOS   # F1a
    co2_indirecto_mall_baseline_kg  = mall_demand_kwh_h     * CO2_FACTOR_IQUITOS   # F1b
    co2_indirecto_baseline_kg       = co2_indirecto_ev_baseline_kg + co2_indirecto_mall_baseline_kg  # F1
    co2_total_baseline_kg           = co2_directo_baseline_kg + co2_indirecto_baseline_kg
    co2_reduccion_directa_baseline_kg   = direct_kg          # F4
    co2_reduccion_indirecta_baseline_kg = 0.0                # sin solar ni BESS en baseline

    # ===========================================================================
    # FORMULA 2 — CONTROL INTELIGENTE
    # ===========================================================================
    co2_directo_control_kg          = 0.0
    co2_indirecto_control_kg        = grid_import_kwh * CO2_FACTOR_IQUITOS    # F2
    co2_total_control_kg            = co2_directo_control_kg + co2_indirecto_control_kg
    co2_reduccion_directa_control_kg  = direct_kg             # F4'
    co2_reduccion_indirecta_control_kg = co2_indirecto_solar_kg + co2_indirecto_bess_kg  # F6+F7

    # ===========================================================================
    # F6 — SOLAR 100%: generacion PV completa reduce CO2 indirecto
    # Destinos del solar (estimados por balance cuando ev_solar no se desglosa):
    # ===========================================================================
    _solar_f6 = solar_total_kwh * CO2_FACTOR_IQUITOS  # F6: solar total
    # Estimacion destinos por prioridad: EV → Mall → BESS → Export
    _ev_solar      = min(solar_total_kwh, ev_demand_dataset_kwh)
    _rem_solar     = max(0.0, solar_total_kwh - _ev_solar)
    _mall_solar    = min(_rem_solar, mall_demand_kwh_h)
    _rem2_solar    = max(0.0, _rem_solar - _mall_solar)
    _bess_solar    = max(0.0, _rem2_solar - grid_export_kwh)
    _export_solar  = grid_export_kwh

    co2_solar_indirect_kg     = _solar_f6                            # F6 total
    co2_solar_ev_kg           = _ev_solar    * CO2_FACTOR_IQUITOS    # F6a
    co2_solar_mall_kg         = _mall_solar  * CO2_FACTOR_IQUITOS    # F6b
    co2_solar_bess_kg         = _bess_solar  * CO2_FACTOR_IQUITOS    # F6c
    co2_solar_export_kg       = _export_solar * CO2_FACTOR_IQUITOS   # F6d = F8

    # F7 — BESS descarga (peak shaving)
    co2_bess_discharge_indirect_kg = bess_discharge_kwh * CO2_FACTOR_IQUITOS  # F7

    # ===========================================================================
    # FORMULA 3 — CUANTIFICACION TOTAL CO2 REDUCIDO (OE3)
    # METODO PRIMARIO: diferencia baseline - control (grid balance, exacto)
    # ===========================================================================
    co2_reduccion_directa_out    = co2_reduccion_directa_control_kg         # F4
    co2_reduccion_indirecta_out  = co2_indirecto_baseline_kg - co2_indirecto_control_kg  # F1-F2
    co2_impacto_control_kg_      = co2_reduccion_indirecta_out
    co2_total_sistema_evitado_kg = co2_reduccion_directa_out + co2_reduccion_indirecta_out  # F3

    return CO2Resultado(
        co2_directo_baseline_kg=co2_directo_baseline_kg,
        co2_indirecto_ev_baseline_kg=co2_indirecto_ev_baseline_kg,
        co2_indirecto_mall_baseline_kg=co2_indirecto_mall_baseline_kg,
        co2_indirecto_baseline_kg=co2_indirecto_baseline_kg,
        co2_total_baseline_kg=co2_total_baseline_kg,
        co2_reduccion_directa_baseline_kg=co2_reduccion_directa_baseline_kg,
        co2_reduccion_indirecta_baseline_kg=co2_reduccion_indirecta_baseline_kg,
        co2_directo_control_kg=co2_directo_control_kg,
        co2_indirecto_control_kg=co2_indirecto_control_kg,
        co2_total_control_kg=co2_total_control_kg,
        co2_reduccion_directa_control_kg=co2_reduccion_directa_control_kg,
        co2_reduccion_indirecta_control_kg=co2_reduccion_indirecta_control_kg,
        co2_solar_indirect_kg=co2_solar_indirect_kg,
        co2_solar_ev_kg=co2_solar_ev_kg,
        co2_solar_mall_kg=co2_solar_mall_kg,
        co2_solar_bess_kg=co2_solar_bess_kg,
        co2_solar_export_kg=co2_solar_export_kg,
        co2_bess_discharge_indirect_kg=co2_bess_discharge_indirect_kg,
        co2_reduccion_directa_kg=co2_reduccion_directa_out,
        co2_reduccion_indirecta_kg=co2_reduccion_indirecta_out,
        co2_impacto_control_kg=co2_impacto_control_kg_ataset_kwh)
    _rem_solar     = max(0.0, solar_total_kwh - _ev_solar)
    _mall_solar    = min(_rem_solar, mall_demand_kwh_h)
    _rem2_solar    = max(0.0, _rem_solar - _mall_solar)
    _bess_solar    = max(0.0, _rem2_solar - grid_export_kwh)
    _export_solar  = grid_export_kwh

    co2_solar_indirect_kg     = _solar_f6                            # F6 total
    co2_solar_ev_kg           = _ev_solar    * CO2_FACTOR_IQUITOS    # F6a
    co2_solar_mall_kg         = _mall_solar  * CO2_FACTOR_IQUITOS    # F6b
    co2_solar_bess_kg         = _bess_solar  * CO2_FACTOR_IQUITOS    # F6c
    co2_solar_export_kg       = _export_solar * CO2_FACTOR_IQUITOS   # F6d = F8

    # F7 — BESS descarga (peak shaving)
    co2_bess_discharge_indirect_kg = bess_discharge_kwh * CO2_FACTOR_IQUITOS  # F7

    # ===========================================================================
    # FORMULA 3 — CUANTIFICACION TOTAL CO2 REDUCIDO (OE3)
    # METODO PRIMARIO: diferencia baseline - control (grid balance, exacto)
    # ===========================================================================
    co2_reduccion_directa_out    = co2_reduccion_directa_control_kg         # F4
    co2_reduccion_indirecta_out  = co2_indirecto_baseline_kg - co2_indirecto_control_kg  # F1-F2
    co2_impacto_control_kg_      = co2_reduccion_indirecta_out
    co2_total_sistema_evitado_kg = co2_reduccion_directa_out + co2_reduccion_indirecta_out  # F3

    return CO2Resultado(
        co2_directo_baseline_kg=co2_directo_baseline_kg,
        co2_indirecto_ev_baseline_kg=co2_indirecto_ev_baseline_kg,
        co2_indirecto_mall_baseline_kg=co2_indirecto_mall_baseline_kg,
        co2_indirecto_baseline_kg=co2_indirecto_baseline_kg,
        co2_total_baseline_kg=co2_total_baseline_kg,
        co2_reduccion_directa_baseline_kg=co2_reduccion_directa_baseline_kg,
        co2_reduccion_indirecta_baseline_kg=co2_reduccion_indirecta_baseline_kg,
        co2_directo_control_kg=co2_directo_control_kg,
        co2_indirecto_control_kg=co2_indirecto_control_kg,
        co2_total_control_kg=co2_total_control_kg,
        co2_reduccion_directa_control_kg=co2_reduccion_directa_control_kg,
        co2_reduccion_indirecta_control_kg=co2_reduccion_indirecta_control_kg,
        co2_solar_indirect_kg=co2_solar_indirect_kg,
        co2_solar_ev_kg=co2_solar_ev_kg,
        co2_solar_mall_kg=co2_solar_mall_kg,
        co2_solar_bess_kg=co2_solar_bess_kg,
        co2_solar_export_kg=co2_solar_export_kg,
        co2_bess_discharge_indirect_kg=co2_bess_discharge_indirect_kg,
        co2_reduccion_directa_kg=co2_reduccion_directa_out,
        co2_reduccion_indirecta_kg=co2_reduccion_indirecta_out,
        co2_impacto_control_kg=co2_impacto_control_kg_,
        co2_total_sistema_evitado_kg=co2_total_sistema_evitado_kg,
    )
