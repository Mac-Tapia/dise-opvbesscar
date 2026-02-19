#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONSTANTES COMPARTIDAS ENTRE SAC, PPO, A2C
v7.2 (2026-02-18) - CENTRALIZADO PARA EVITAR DUPLICIDADES

Todas las constantes OE2 (Iquitos, Peru) en un solo lugar.
Importar desde aqui en lugar de duplicar en cada script.
"""
from __future__ import annotations

# ============================================================================
# CONSTANTES BASICAS OE2 v5.8 (Iquitos, Peru)
# ============================================================================
CO2_FACTOR_IQUITOS: float = 0.4521  # kg CO2/kWh - factor de emision grid Iquitos
HOURS_PER_YEAR: int = 8760

# ============================================================================
# CONSTANTES BESS (VALIDADAS v5.8 - 2026-02-18)
# ============================================================================
BESS_MAX_KWH_CONST: float = 2000.0  # 2,000 kWh max SOC (VERIFICADO v5.8 audit)
BESS_MAX_POWER_KW: float = 400.0    # 400 kW potencia maxima BESS
BESS_MIN_SOC_PERCENT: float = 20.0  # 20% SOC minimo
BESS_MAX_SOC_PERCENT: float = 100.0 # 100% SOC maximo
BESS_EFFICIENCY: float = 0.95       # 95% eficiencia round-trip

# ============================================================================
# CONSTANTES NORMALIZACION (CRITICO para PPO/SAC/A2C)
# ============================================================================
# Basadas en datos OE2 Iquitos reales
SOLAR_MAX_KW: float = 2887.0        # Real max desde pv_generation_citylearn_enhanced_v2.csv
MALL_MAX_KW: float = 3000.0         # Real max=2,763 kW from demandamallhorakwh.csv
CHARGER_MAX_KW: float = 3.7         # Max per socket: 7.4 kW charger / 2 sockets (ALINEADO CON SAC)
CHARGER_MEAN_KW: float = 4.6        # Potencia media efectiva por socket
DEMAND_MAX_KW: float = 300.0        # Demanda total maxima esperada

# ============================================================================
# CONSTANTES VEHICULOS Y CO2 DIRECTO v7.2 (2026-02-17)
# ============================================================================
# DATOS REALES del dataset EV - NO APROXIMACIONES
MOTOS_TARGET_DIARIOS: int = 270     # Motos por día (Iquitos)
MOTOTAXIS_TARGET_DIARIOS: int = 39  # Mototaxis por día (Iquitos)
VEHICLES_TARGET_DIARIOS: int = MOTOS_TARGET_DIARIOS + MOTOTAXIS_TARGET_DIARIOS  # 309 total

MOTO_BATTERY_KWH: float = 4.6       # Capacidad bateria moto (kWh)
MOTOTAXI_BATTERY_KWH: float = 7.4   # Capacidad bateria mototaxi (kWh)
MOTO_SOC_ARRIVAL: float = 0.20      # SOC al llegar (20%)
MOTO_SOC_TARGET: float = 0.80       # SOC objetivo (80%)
MOTO_ENERGY_TO_CHARGE: float = (MOTO_SOC_TARGET - MOTO_SOC_ARRIVAL) * MOTO_BATTERY_KWH / 0.95  # ~2.90 kWh
MOTOTAXI_ENERGY_TO_CHARGE: float = (MOTO_SOC_TARGET - MOTO_SOC_ARRIVAL) * MOTOTAXI_BATTERY_KWH / 0.95  # ~4.68 kWh

CO2_FACTOR_MOTO_KG_KWH: float = 0.87      # kg CO2 por kWh cargado (moto vs gasolina)
CO2_FACTOR_MOTOTAXI_KG_KWH: float = 0.47  # kg CO2 por kWh cargado (mototaxi vs gasolina)

# ============================================================================
# CONSTANTES INFRAESTRUCTURA OE2 v5.4
# ============================================================================
N_CHARGERS: int = 19                # 19 cargadores
TOTAL_SOCKETS: int = 38             # 38 sockets (19 × 2)
MOTOS_SOCKETS: int = 30             # Primeros 30 sockets para motos
TAXIS_SOCKETS: int = 8              # Ultimos 8 sockets para mototaxis
SOLAR_PV_KWP: float = 4050.0        # 4,050 kWp solar capacity
BESS_CAPACITY_KWH: float = 2000.0   # 2,000 kWh BESS capacity (v5.8 audit)

# ============================================================================
# NORMALIZACION DE RECOMPENSAS
# ============================================================================
REWARD_MIN: float = -1.0
REWARD_MAX: float = 1.0
REWARD_CLIP_RANGE: tuple = (-0.0005, 0.0005)  # Para fallback reward single-obj

# ============================================================================
# CONFIGURACION PERIODOS Y HORARIOS
# ============================================================================
HORA_PUNTA_INICIO: int = 18  # Hora punta: 18:00
HORA_PUNTA_FIN: int = 23     # Hora punta al 23:00
HORAS_PICO_DIARIAS: int = 6  # 6 horas pico por día

# Horario operativo EVs (horas activas)
EV_OPERATIONAL_HOURS_START: int = 6   # 06:00
EV_OPERATIONAL_HOURS_END: int = 23    # 23:00
