"""
Constantes compartidas OE2 — fuente única de verdad (Single Source of Truth).

Todos los módulos de src/dimensionamiento/oe2/ deben importar desde aquí.
No definir estas constantes localmente en bess.py, balance.py, chargers.py ni solar_pvlib.py.
"""
from __future__ import annotations

# ============================================================================
# TARIFAS OSINERGMIN — Electro Oriente S.A. (Iquitos, Loreto)
# Pliego Tarifario MT3 — Media Tensión Comercial/Industrial
# Vigente desde 2024-11-04
# Referencia: OSINERGMIN Resolución N° 047-2024-OS/CD
# Hora Punta (HP):       18:00 – 22:59 (18 ≤ h < 23)
# Hora Fuera de Punta:   00:00 – 17:59 y 23:00 – 23:59
# ============================================================================

TARIFA_ENERGIA_HP_SOLES: float = 0.45       # S/./kWh en HP
TARIFA_ENERGIA_HFP_SOLES: float = 0.28      # S/./kWh en HFP
TARIFA_POTENCIA_HP_SOLES: float = 48.50     # S/./kW-mes en HP
TARIFA_POTENCIA_HFP_SOLES: float = 22.80   # S/./kW-mes en HFP
TIPO_CAMBIO_PEN_USD: float = 3.75           # PEN/USD (referencial)

TARIFA_ENERGIA_HP_USD: float = TARIFA_ENERGIA_HP_SOLES / TIPO_CAMBIO_PEN_USD    # ~0.12 USD/kWh
TARIFA_ENERGIA_HFP_USD: float = TARIFA_ENERGIA_HFP_SOLES / TIPO_CAMBIO_PEN_USD  # ~0.075 USD/kWh

# Horas punta: 18, 19, 20, 21, 22  →  range(18, 23) exclusive-upper
HORA_INICIO_HP: int = 18
HORA_FIN_HP: int = 23       # exclusivo: 18 ≤ h < 23  (cubre 18-22h)
HORAS_PUNTA: list[int] = list(range(HORA_INICIO_HP, HORA_FIN_HP))

# ============================================================================
# FACTOR DE EMISIÓN CO₂ — red aislada Iquitos (generación térmica diesel)
# Fuente: MINEM/OSINERGMIN — Sistema aislado Loreto
#
# Factores variables por período tarifario:
#   HP (18-23h): generadores punta diesel B5 (peakers, eficiencia ~28-30%)
#   HFP (resto): generadores base diesel B5 (carga base, eficiencia ~35-38%)
#   Promedio ponderado (5h HP / 19h HFP): (5×0.61 + 19×0.41)/24 ≈ 0.4517 ≈ 0.4521
# Fuente: MINEM Estadísticas Electricidad Loreto 2024 / IPCC 2006 Tier 2 diesel B5
# ============================================================================

FACTOR_CO2_KG_KWH: float = 0.4521          # kg CO₂/kWh promedio anual (MINEM Loreto)
# Promedios anuales de los factores horarios (calculados desde estacionalidad + HP/HFP):
#   Base lluviosa(0.43)+seca(0.47) promedio=0.45; ×1.35 HP = 0.608; ×0.908 HFP = 0.409
FACTOR_CO2_HP_KG_KWH: float = 0.6080       # kg CO₂/kWh HP promedio anual (18-23h)
FACTOR_CO2_HFP_KG_KWH: float = 0.4090      # kg CO₂/kWh HFP promedio anual (resto)

# Factores de conversión combustible → electricidad (reducción directa CO₂)
FACTOR_CO2_GASOLINA_KG_L: float = 2.31         # kg CO₂/litro gasolina (IPCC)
FACTOR_CO2_NETO_MOTO_KG_KWH: float = 0.87      # kg CO₂ evitado/kWh cargado moto
FACTOR_CO2_NETO_MOTOTAXI_KG_KWH: float = 0.54  # kg CO₂ evitado/kWh cargado mototaxi

# ============================================================================
# ESPECIFICACIÓN BESS v5.3 — Sistema de almacenamiento
# ============================================================================

BESS_CAPACITY_KWH: float = 2000.0   # kWh capacidad nominal
BESS_POWER_KW: float = 400.0        # kW potencia nominal (carga y descarga)
BESS_DOD: float = 0.80              # Depth of Discharge (80 % → 1,600 kWh útiles)
BESS_EFFICIENCY_ROUNDTRIP: float = 0.95  # Eficiencia roundtrip litio-ion
BESS_SOC_MIN: float = 0.20          # SOC mínimo operacional (20 %)
BESS_SOC_MAX: float = 1.00          # SOC máximo (100 %)

# ============================================================================
# ESPECIFICACIÓN SOLAR PV — Instalación Iquitos 2024
# Módulo: Jinko Tiger Neo JKM580N-72HL4-BDV (N-type TOPCon, bifacial 80%)
# Modelo: PVWatts (NREL) + ganancia bifacial 8.7% (albedo=0.22, tilt=10°)
# Fuente: pv_generation_citylearn2024.csv (8,760 filas horarias)
# ============================================================================

PV_INSTALLED_KWP: float = 4162.0            # kWp DC instalados OE2 (PVWatts pdc0, Jinko Tiger Neo JKM580N-72HL4-BDV + 8.7% bifacial)
PV_PVWATTS_PDC0_KWP: float = 4162.0        # kWp pdc0 PVWatts — valor canónico único
PV_ANNUAL_CAPACITY_KWH: float = 5_819_332.0  # kWh/año (PR=83.5%, 1,398 kWh/kWp)
PV_ANNUAL_CAPACITY_GWH: float = PV_ANNUAL_CAPACITY_KWH / 1e6  # 5.82 GWh
PV_MAX_HOURLY_KW: float = 3245.95           # kW pico horario (del dataset)

# ============================================================================
# PARÁMETROS DE UBICACIÓN — Iquitos, Loreto, Perú
# ============================================================================

IQUITOS_LAT: float = -3.75          # latitud °
IQUITOS_LON: float = -73.25         # longitud °
IQUITOS_ALT: float = 104.0          # altitud m.s.n.m.
IQUITOS_TZ: str = "America/Lima"
