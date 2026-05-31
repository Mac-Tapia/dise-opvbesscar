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
# CONSTANTES BESS (VALIDADAS v5.4 - 2026-02-19) ✅ UPDATED
# ============================================================================
BESS_MAX_KWH_CONST: float = 2000.0  # 2,000 kWh max SOC (VERIFIED v5.8 audit)
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
CHARGER_MAX_KW: float = 7.4         # Max per socket: Mode 3 charging 32A @ 230V = 7.4 kW/socket (OE2 v5.2)
CHARGER_MEAN_KW: float = 4.6        # Potencia media efectiva por socket
DEMAND_MAX_KW: float = 300.0        # Demanda total maxima esperada

# ============================================================================
# CONSTANTES VEHICULOS Y CO2 DIRECTO v7.2 (2026-02-17)
# ============================================================================
# DATOS REALES del dataset EV - NO APROXIMACIONES
MOTOS_TARGET_DIARIOS: int = 270     # Motos por día (Iquitos)
MOTOTAXIS_TARGET_DIARIOS: int = 39  # mototaxis por día (Iquitos)
VEHICLES_TARGET_DIARIOS: int = MOTOS_TARGET_DIARIOS + MOTOTAXIS_TARGET_DIARIOS  # 309 total

MOTO_BATTERY_KWH: float = 1.5       # Capacidad batería moto (kWh) — validado YAML/Tabla 13 OE2
MOTOTAXI_BATTERY_KWH: float = 3.0   # Capacidad batería mototaxi (kWh) — validado YAML/OE2
MOTO_SOC_ARRIVAL: float = 0.20      # SOC al llegar (20%)
MOTO_SOC_TARGET: float = 0.80       # SOC objetivo (80%)
MOTO_ENERGY_TO_CHARGE: float = (MOTO_SOC_TARGET - MOTO_SOC_ARRIVAL) * MOTO_BATTERY_KWH / 0.95  # ~0.95 kWh
MOTOTAXI_ENERGY_TO_CHARGE: float = (MOTO_SOC_TARGET - MOTO_SOC_ARRIVAL) * MOTOTAXI_BATTERY_KWH / 0.95  # ~1.89 kWh

# ─────────────────────────────────────────────────────────────────────────────
# DERIVACIÓN CIENTÍFICA DE FACTORES DE CO2 DIRECTO (IPCC 2006 Tier 1)
# ─────────────────────────────────────────────────────────────────────────────
# Fuente primaria: IPCC (2006). "2006 IPCC Guidelines for National Greenhouse
#   Gas Inventories. Volume 2: Energy. Chapter 3: Mobile Combustion."
#   Factor gasolina (Tier 1):  2.31 kg CO2/L  (NCV basis, Tabla 3.2.1)
#   Factor diésel  (Tier 1):   2.68 kg CO2/L  (NCV basis, Tabla 3.2.1)
# Confirmado por: U.S. EPA Greenhouse Gas Equivalencies Calculator (2024):
#   gasolina = 8,887 g CO2/galón EEUU = 2.347 kg CO2/L ≈ 2.31 kg CO2/L
#
# Fuentes adicionales (contexto Peru):
#   - Garay Aquino et al. (2024). "Proposal for the Implementation of Electric
#     Motorcycle Taxis for Sustainable Urban Transportation in Districts of
#     Peru." E3S Web of Conferences 566, 04004. ESRE 2024.
#     DOI: 10.1051/e3sconf/202456604004
#   - Guerra & Pérez (2024). "Study of the replacement of internal combustion
#     motorcycle taxis by electric motor motorcycle taxis using RETScreen
#     Software in the city of Lima, Peru." Congress of Smart Cities.
#
# FÓRMULA DE CONVERSIÓN (kgCO2/kWh_cargado):
#   factor = (consumo_gasolina [L/100km] × 2.31 [kgCO2/L])
#            / (consumo_eléctrico [kWh/100km])
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ MOTO (110-150cc, típica Peru: Honda Wave / Yamaha Crypton / Biz)        │
# │  Consumo gasolina: 2.30 L/100km  (Honda Wave 125 real-world, Peru)      │
# │  Consumo eléctrico: 6.0 kWh/100km  (equivalente e-moto pequeña)        │
# │  factor = 2.30 × 2.31 / 6.0 = 0.885 ≈ 0.87 kg CO2/kWh               │
# │  Net benefit Iquitos: 0.87 − 0.4521 = +0.418 kg CO2/kWh cargado       │
# ├─────────────────────────────────────────────────────────────────────────┤
# │ MOTOTAXI (3 ruedas, 125-200cc gasolina, Loreto/Iquitos)                │
# │  Consumo gasolina: 3.50 L/100km  (3 ruedas, arranque-parada, urbano)   │
# │  Consumo eléctrico: 15.0 kWh/100km  (3 ruedas eléctrico, ~250 kg)     │
# │  factor = 3.50 × 2.31 / 15.0 = 0.539 ≈ 0.54 kg CO2/kWh              │
# │  Net benefit Iquitos: 0.54 − 0.4521 = +0.088 kg CO2/kWh cargado      │
# └─────────────────────────────────────────────────────────────────────────┘
CO2_FACTOR_MOTO_KG_KWH: float = 0.87      # kg CO2/kWh — moto vs gasolina (Honda Wave 125, IPCC 2006)
CO2_FACTOR_MOTOTAXI_KG_KWH: float = 0.54  # kg CO2/kWh — mototaxi vs gasolina (3 ruedas, IPCC 2006)

# ============================================================================
# CONSTANTES INFRAESTRUCTURA OE2 v5.4
# ============================================================================
N_CHARGERS: int = 19                # 19 cargadores
TOTAL_SOCKETS: int = 38             # 38 sockets (19 × 2)
MOTOS_SOCKETS: int = 30             # Primeros 30 sockets para motos
MOTOTAXIS_SOCKETS: int = 8              # Ultimos 8 sockets para mototaxis
SOLAR_PV_KWP: float = 4162.0        # 4,162 kWp DC (PVWatts pdc0, Jinko Tiger Neo JKM580N-72HL4-BDV + 8.7% bifacial)
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
HORA_PUNTA_INICIO: int = 18  # HP empieza a las 18:00 (inclusive)
HORA_PUNTA_FIN: int = 23     # HP termina a las 22:59 (exclusive: h < 23 → {18..22})
HORAS_PICO_DIARIAS: int = 5  # 5 horas pico: 18, 19, 20, 21, 22

# Horario operativo EVs (horas activas)
EV_OPERATIONAL_HOURS_START: int = 6   # 06:00
EV_OPERATIONAL_HOURS_END: int = 23    # 23:00
