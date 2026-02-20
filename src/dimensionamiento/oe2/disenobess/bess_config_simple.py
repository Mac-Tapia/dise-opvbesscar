"""
CONFIGURACION SIMPLIFICADA DEL BESS v5.7
========================================

Este archivo contiene TODOS los parámetros del BESS en UN SOLO LUGAR
para facilitar modificaciones en el futuro.

ESTRUCTURA:
- BESS_SPECS: Especificaciones técnicas
- SOC_LIMITS: Límites operacionales
- DISPATCH_RULES: Reglas de despacho
"""

# ============================================================================
# BESS: ESPECIFICACIONES TECNICAS
# ============================================================================

BESS_SPECS = {
    'capacity_kwh': 2000.0,          # Capacidad total
    'power_kw': 400.0,               # Potencia de carga/descarga
    'efficiency_rtc': 0.95,          # Eficiencia round-trip (95%)
}

# ============================================================================
# BESS: LIMITES OPERACIONALES
# ============================================================================

SOC_LIMITS = {
    'min_percent': 20.0,             # SOC mínimo operativo (%)
    'max_percent': 100.0,            # SOC máximo operativo (%)
    'min_kwh': 400.0,                # SOC mínimo en kWh (20% de 2000)
    'max_kwh': 2000.0,               # SOC máximo en kWh (100% de 2000)
}

DOD_CONFIG = {
    'depth_of_discharge': 0.80,      # 80% DoD (profundidad de descarga)
    'usable_capacity_kwh': 1600.0,   # 80% de 2000 = 1600 kWh usables
}

# ============================================================================
# BESS: REGLAS DE DESPACHO
# ============================================================================

DISPATCH_RULES = {
    # PRIORIDAD 1: Cobertura 100% EV
    'ev_priority': True,
    'ev_coverage_target': 1.0,       # 100% cobertura
    
    # PRIORIDAD 2: Peak shaving (cuando Mall demand > pico de referencia)
    'peak_shaving': True,
    'peak_threshold_kw': 1900.0,     # Demanda pico referencia
    
    # RESTRICCIÓN: CIERRE DEL DÍA A LAS 22h
    'closing_hour': 22,              # Hora de cierre (0-23)
    'closing_soc_target': 0.20,      # SOC objetivo a cierre (20% exacto)
}

# ============================================================================
# VARIABLES DERIVADAS (NO MODIFICAR DIRECTAMENTE)
# ============================================================================

def get_soc_in_kwh(soc_percent):
    """Convertir SOC % a kWh"""
    return soc_percent / 100.0 * BESS_SPECS['capacity_kwh']

def get_soc_in_percent(soc_kwh):
    """Convertir SOC kWh a %"""
    return soc_kwh / BESS_SPECS['capacity_kwh'] * 100.0

def is_soc_valid(soc_percent):
    """Verificar si SOC está dentro de límites operacionales"""
    return SOC_LIMITS['min_percent'] <= soc_percent <= SOC_LIMITS['max_percent']

# ============================================================================
# RESUMEN PARA DOCUMENTACION
# ============================================================================

BESS_SUMMARY = f"""
CONFIGURACION BESS v5.7
======================

ESPECIFICACIONES:
  • Capacidad: {BESS_SPECS['capacity_kwh']:.0f} kWh
  • Potencia: {BESS_SPECS['power_kw']:.0f} kW
  • Eficiencia round-trip: {BESS_SPECS['efficiency_rtc']*100:.0f}%

LIMITES OPERACIONALES:
  • SOC mínimo: {SOC_LIMITS['min_percent']:.0f}% ({SOC_LIMITS['min_kwh']:.0f} kWh)
  • SOC máximo: {SOC_LIMITS['max_percent']:.0f}% ({SOC_LIMITS['max_kwh']:.0f} kWh)
  • DoD (Depth of Discharge): {DOD_CONFIG['depth_of_discharge']*100:.0f}%
  • Capacidad usable: {DOD_CONFIG['usable_capacity_kwh']:.0f} kWh

REGLAS DE DESPACHO:
  • Prioridad 1: Cobertura {DISPATCH_RULES['ev_coverage_target']*100:.0f}% EV
  • Prioridad 2: Peak shaving cuando demand > {DISPATCH_RULES['peak_threshold_kw']:.0f} kW
  • Restricción: Cierre a las {DISPATCH_RULES['closing_hour']}h con SOC = {DISPATCH_RULES['closing_soc_target']*100:.0f}%
"""

if __name__ == '__main__':
    print(BESS_SUMMARY)
