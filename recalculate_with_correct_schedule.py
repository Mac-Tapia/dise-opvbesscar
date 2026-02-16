"""
Recalcular factor operacional con horario CORRECTO: 9-22h, hora punta 18-22h
"""

def get_operational_factor_corrected(hour_of_day: int) -> float:
    """CORRECTED version: 9 AM - 22 PM operation"""
    if hour_of_day < 9 or hour_of_day >= 22:
        # Cerrado fuera de 9-22h
        return 0.0
    elif hour_of_day == 9:
        # 9-10h: apertura 30%
        return 0.30
    elif 10 <= hour_of_day < 18:
        # 10-18h: rampa lineal 30% -> 100%
        progress = (hour_of_day - 10) / 8.0  # 0 a 1 en 8 horas
        return 0.30 + progress * 0.70
    elif 18 <= hour_of_day < 22:
        # 18-22h: operacion plena 100% (HORA PUNTA)
        return 1.0
    else:
        return 0.0


print("="*80)
print("RECALCULO CON HORARIO CORRECTO: 9 AM - 22 PM")
print("Hora Punta: 18h - 22h (4 horas, NO 5)")
print("="*80)
print()

print("[1] FACTOR OPERACIONAL POR HORA (CORRECTED):")
print()
print("Hora | Factor | Descripción")
print("─────┼────────┼──────────────────────────────")

factors = []
for hour in range(24):
    factor = get_operational_factor_corrected(hour)
    factors.append(factor)
    
    if hour < 9 or hour >= 22:
        desc = "CERRADO"
    elif hour == 9:
        desc = "Apertura 30%"
    elif 10 <= hour < 18:
        desc = f"Rampa {int(factor*100)}%"
    elif 18 <= hour < 22:
        desc = "PICO 100%"
    else:
        desc = "?"
    
    print(f"{hour:2d}h | {factor:5.2f} | {desc}")

print()
print("[2] CÁLCULO DEL FACTOR PROMEDIO (CORRECTED):")
print()

factor_promedio = sum(factors) / 24
horas_operativas = sum(factors)

print(f"Suma de factores: {sum(factors):.4f}")
print(f"Horas en día: 24")
print(f"Factor promedio: {factor_promedio:.4f}")
print(f"Horas operativas ponderadas: {horas_operativas:.2f}/24")
print()

print("[3] COMPARACIÓN ANTES vs DESPUÉS:")
print()
print("ANTES (INCORRECTO: 9-23h, punta 18-21h):")
print(f"  Factor promedio: 0.4021")
print(f"  Horas ponderadas: 9.65/24")
print()
print("AHORA (CORRECTO: 9-22h, punta 18-22h):")
print(f"  Factor promedio: {factor_promedio:.4f}")
print(f"  Horas ponderadas: {horas_operativas:.2f}/24")
print()

print("[4] IMPACTO EN ARRIVALS:")
print()
print(f"ANTES: 270 motos × 0.4021 = {270 * 0.4021:.1f} motos/día (en dataset)")
print(f"AHORA: 270 motos × {factor_promedio:.4f} = {270 * factor_promedio:.1f} motos/día (en dataset)")
print()

# Calcular nuevos lambda_arrivals
horas_asumidas_original = 13.0  # El comentario dice "13h operativas"
horas_operacio_equivalentes = horas_operativas

factor_correccion = horas_asumidas_original / horas_operacio_equivalentes
lambda_motos_nuevo = 0.69 * factor_correccion
lambda_taxi_nuevo = 0.375 * factor_correccion

print("[5] NUEVOS lambda_arrivals (CORRECTED):")
print()
print(f"ANTERIOR lambda_motos: 0.69")
print(f"NUEVO lambda_motos: {lambda_motos_nuevo:.3f}")
print(f"Factor de cambio: {factor_correccion:.4f}")
print()
print(f"ANTERIOR lambda_taxi: 0.375")
print(f"NUEVO lambda_taxi: {lambda_taxi_nuevo:.3f}")
print()

# Verificación
total_motos = sum(lambda_motos_nuevo * 30 * get_operational_factor_corrected(h) for h in range(24))
total_taxis = sum(lambda_taxi_nuevo * 8 * get_operational_factor_corrected(h) for h in range(24))

print("[6] VERIFICACIÓN:")
print(f"Motos/día esperadas: {total_motos:.1f}")
print(f"Mototaxis/día esperadas: {total_taxis:.1f}")
print()

print("="*80)
print("CAMBIOS A HACER EN chargers.py")
print("="*80)
print()
print()
print(f"""# ============================================================================
# HORARIO DE OPERACION CORRECTED (9 AM - 22 PM)
# ============================================================================
# Hora Punta: 18h - 22h (4 horas, no 5)

def get_operational_factor(hour_of_day: int) -> float:
    \"\"\"Retorna el factor de operacion del mall para una hora determinada.
    
    Horario del mall (Iquitos):
    - 0-9h: Cerrado (0%)
    - 9-10h: Apertura y acondicionamiento (30%)
    - 10-18h: Operacion normal lineal (30% -> 100%)
    - 18-22h: Pico de operacion (100%) [HORA PUNTA]
    - 22-24h: Cerrado (0%)
    
    Args:
        hour_of_day: Hora del dia (0-23)
        
    Returns:
        Factor de operacion (0.0-1.0)
    \"\"\"
    if hour_of_day < 9 or hour_of_day >= 22:
        return 0.0
    elif hour_of_day == 9:
        return 0.30
    elif 10 <= hour_of_day < 18:
        progress = (hour_of_day - 10) / 8.0
        return 0.30 + progress * 0.70
    elif 18 <= hour_of_day < 22:
        return 1.0
    else:
        return 0.0


# Factor operacional promedio (para compensar en lambda_arrivals)
FACTOR_OPERACIONAL_PROMEDIO = {factor_promedio:.6f}  # {horas_operativas:.2f}/24 horas

# ============================================================================
# CORRECTED lambda_arrivals (compensado por horario 9-22h)
# ============================================================================

MOTO_SPEC = VehicleType(
    name="MOTO",
    lambda_arrivals={lambda_motos_nuevo:.3f},    # 270 motos/día / (30 sockets × factor operacional {factor_promedio:.2f})
    power_kw=7.4,
    capacity_kwh=4.6,
    soc_arrival_mean=0.20,
    soc_arrival_std=0.10,
    soc_target=1.00
)

MOTOTAXI_SPEC = VehicleType(
    name="MOTOTAXI",
    lambda_arrivals={lambda_taxi_nuevo:.3f},   # 39 mototaxis/día / (8 sockets × factor operacional {factor_promedio:.2f})
    power_kw=7.4,
    capacity_kwh=7.4,
    soc_arrival_mean=0.20,
    soc_arrival_std=0.10,
    soc_target=1.00
)
""")

print("="*80)
