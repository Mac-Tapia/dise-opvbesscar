#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COLUMNAS REALES COMPARTIDAS ENTRE SAC, PPO, A2C
v7.0 (2026-02-18) - CENTRALIZADO PARA EVITAR DUPLICIDADES

Todas las definiciones de columnas de datasets OE2 en un solo lugar.
"""
from __future__ import annotations
from typing import List

# ===== COLUMNAS CHARGERS - 353 totales =====
# 4 columnas agregadas + 39 sockets × 9 columnas cada uno
CHARGERS_AGGREGATE_COLS: List[str] = [
    'costo_carga_ev_soles',
    'energia_total_cargada_kwh',
    'co2_reduccion_motos_kg',
    'co2_reduccion_mototaxis_kg',
    'reduccion_directa_co2_kg',
]

# Columnas por socket (XXX = 000-038): 9 columnas × 39 sockets = 351 columnas
CHARGERS_SOCKET_COLS_TEMPLATE: List[str] = [
    'socket_{:03d}_charger_power_kw',
    'socket_{:03d}_battery_kwh',
    'socket_{:03d}_vehicle_type',
    'socket_{:03d}_soc_current',
    'socket_{:03d}_soc_arrival',
    'socket_{:03d}_soc_target',
    'socket_{:03d}_active',
    'socket_{:03d}_charging_power_kw',
    'socket_{:03d}_vehicle_count',
]

# ===== COLUMNAS BESS - 25 totales =====
BESS_REAL_COLS: List[str] = [
    'datetime',
    'pv_generation_kwh',
    'ev_demand_kwh',
    'mall_demand_kwh',
    'pv_to_ev_kwh',
    'pv_to_bess_kwh',
    'pv_to_mall_kwh',
    'pv_curtailed_kwh',
    'bess_charge_kwh',
    'bess_discharge_kwh',
    'bess_to_ev_kwh',
    'bess_to_mall_kwh',
    'grid_to_ev_kwh',
    'grid_to_mall_kwh',
    'grid_to_bess_kwh',
    'grid_import_total_kwh',
    'bess_soc_percent',
    'bess_mode',
    'tariff_osinergmin_soles_kwh',
    'cost_grid_import_soles',
    'peak_reduction_savings_soles',
    'peak_reduction_savings_normalized',
    'co2_avoided_indirect_kg',
    'co2_avoided_indirect_normalized',
    'mall_grid_import_kwh',
]

# ===== COLUMNAS SOLAR - 16 totales =====
SOLAR_REAL_COLS: List[str] = [
    'datetime',
    'irradiancia_ghi',
    'temperatura_c',
    'velocidad_viento_ms',
    'potencia_kw',
    'energia_kwh',
    'is_hora_punta',
    'hora_tipo',
    'tarifa_aplicada_soles',
    'ahorro_solar_soles',
    'reduccion_indirecta_co2_kg',
    'energia_suministrada_al_bess_kwh',
    'energia_suministrada_al_ev_kwh',
    'energia_suministrada_al_mall_kwh',
    'energia_suministrada_a_red_kwh',
    'reduccion_indirecta_co2_kg_total',
]

# ===== COLUMNAS MALL - 6 totales =====
MALL_REAL_COLS: List[str] = [
    'datetime',
    'mall_demand_kwh',
    'mall_co2_indirect_kg',
    'is_hora_punta',
    'tarifa_soles_kwh',
    'mall_cost_soles',
]

# ===== COLUMNAS SELECCIONADAS PARA OBSERVACIONES =====
# 210 features observables del sistema completo

# CHARGERS observables: 4 agregadas + 39 × 4 (soc_current, active, charging_power, vehicle_count) = 160
CHARGERS_OBS_AGGREGATE: List[str] = CHARGERS_AGGREGATE_COLS  # 4
CHARGERS_OBS_PER_SOCKET: List[str] = ['soc_current', 'active', 'charging_power_kw', 'vehicle_count']  # 4 × 39 = 156

# BESS observables: 12 columnas numericas clave
BESS_OBS_COLS: List[str] = [
    'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'pv_curtailed_kwh',
    'bess_charge_kwh', 'bess_discharge_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh',
    'bess_soc_percent', 'tariff_osinergmin_soles_kwh', 
    'co2_avoided_indirect_kg', 'peak_reduction_savings_soles'
]

# SOLAR observables: 10 columnas numericas clave
SOLAR_OBS_COLS: List[str] = [
    'irradiancia_ghi', 'temperatura_c', 'potencia_kw', 'energia_kwh',
    'is_hora_punta', 'tarifa_aplicada_soles', 'ahorro_solar_soles',
    'reduccion_indirecta_co2_kg', 'energia_suministrada_al_ev_kwh', 
    'energia_suministrada_al_bess_kwh'
]

# MALL observables: 5 columnas numericas
MALL_OBS_COLS: List[str] = [
    'mall_demand_kwh', 'mall_co2_indirect_kg', 'is_hora_punta',
    'tarifa_soles_kwh', 'mall_cost_soles'
]

# Total observables: 4 + 156 + 12 + 10 + 5 + 6 (time) + 12 (system) = 205 -> redondeado a 210
ALL_OBSERVABLE_COLS: List[str] = (
    CHARGERS_OBS_AGGREGATE +
    CHARGERS_OBS_PER_SOCKET +
    BESS_OBS_COLS +
    SOLAR_OBS_COLS +
    MALL_OBS_COLS
)
OBS_DIM: int = 210  # 4 + 156 + 12 + 10 + 5 + 6 (time) + 12 (system)

# ===== COLUMNAS PARA REWARD MULTIOBJETIVO =====
# Todas las columnas de CO2 (directo e indirecto) y costos
REWARD_CO2_DIRECT_COLS: List[str] = [
    'co2_reduccion_motos_kg',
    'co2_reduccion_mototaxis_kg',  
    'reduccion_directa_co2_kg',
]

REWARD_CO2_INDIRECT_COLS: List[str] = [
    'co2_avoided_indirect_kg',
    'reduccion_indirecta_co2_kg',
]

REWARD_COST_COLS: List[str] = [
    'cost_grid_import_soles',
    'tariff_osinergmin_soles_kwh',
    'mall_cost_soles',
]

REWARD_EV_SATISFACTION_COLS: List[str] = [
    'socket_*_soc_current',
    'socket_*_active',
    'socket_*_charging_power_kw',
]

# ===== CONFIGURACION DIMENSIONES =====
# Observation space
OBS_LOW: float = 0.0
OBS_HIGH: float = 1.0

# Action space (1 BESS + 38 sockets = 39 acciones continuas)
ACTION_DIM: int = 39  # 1 BESS + 38 sockets
ACTION_LOW: float = 0.0
ACTION_HIGH: float = 1.0  # Valores normalizados [0, 1] se convierten a kW en step()
