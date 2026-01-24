"""Análisis de parámetros para la Tabla 13 del OE2."""
import numpy as np
import pandas as pd
import math

# Valores esperados de la Tabla 13:
# Cargadores (4 tomas): min=4, max=35, prom=20.61, mediana=20
# Tomas totales: min=16, max=140, prom=82.46, mediana=80
# Sesiones pico 4h: min=103, max=1030, prom=593.52, mediana=566.50
# Cargas día: min=87.29, max=3058.96, prom=849.83, mediana=785.62
# Energía día [kWh]: min=92.80, max=3252.00, prom=903.46, mediana=835.20
# Potencia pico [kW]: min=11.60, max=406.50, prom=112.93, mediana=104.40

# ANÁLISIS INVERSO:
# Sesiones/día = Energía_día / 1.06 kWh por sesión
# 3252 / 1.06 = 3068 sesiones/día max
# 92.80 / 1.06 = 87.5 sesiones/día min

# La energía por sesión de 30 min:
# E_sesion = 1.06 kWh (promedio entre 1.0 kWh moto y 1.5 kWh mototaxi)
# Esto implica potencia promedio = 1.06 / 0.5 = 2.12 kW

# Para el cálculo de cargadores (fórmula):
# Sesiones pico = total_sesiones_día × pico_share / n_horas_pico
# Con pico_share=0.5 y n_horas_pico=4:
# Sesiones_pico_hora = total_sesiones × 0.5 / 4 = total_sesiones × 0.125

# Max: 1030 sesiones pico en 4h = 257.5 sesiones/hora
# Con sesión de 30 min, un socket atiende 2 sesiones/hora
# Cargadores = ceil(257.5 / (4 sockets × 2 ses/hora)) = ceil(257.5 / 8) = 33

# Verificación:
# max_cargadores = 35 (esperado), calculado = 33 (cercano)

print("=" * 60)
print("ANÁLISIS DE PARÁMETROS PARA TABLA 13 OE2")
print("=" * 60)

# Parámetros base
n_motos = 500
n_mototaxis = 500
n_total = n_motos + n_mototaxis
bat_moto = 2.0  # kWh
bat_mototaxi = 4.0  # kWh
power_moto = 2.0  # kW
power_mototaxi = 3.0  # kW
session_minutes = 30
sockets_per_charger = 4
peak_hours = 4
peak_share = 0.5
utilization = 0.85

# Energía por sesión de 30 min
energy_per_moto_session = power_moto * (session_minutes / 60)  # 1.0 kWh
energy_per_mototaxi_session = power_mototaxi * (session_minutes / 60)  # 1.5 kWh
energy_avg_session = (energy_per_moto_session + energy_per_mototaxi_session) / 2  # 1.25 kWh

print(f"\nEnergía por sesión:")
print(f"  Moto (30min @ 2kW): {energy_per_moto_session:.2f} kWh")
print(f"  Mototaxi (30min @ 3kW): {energy_per_mototaxi_session:.2f} kWh")
print(f"  Promedio: {energy_avg_session:.2f} kWh")
print(f"  Nota Tabla 13 usa 1.06 kWh (ajustado por FC)")

# Función para evaluar escenario
def evaluate_scenario(pe, fc):
    # Vehículos que cargan
    motos_charging = n_motos * pe
    mototaxis_charging = n_mototaxis * pe
    total_vehicles = motos_charging + mototaxis_charging

    # Energía (basada en capacidad de batería × FC, no potencia del cargador)
    # El FC representa el % de batería descargada que necesita recarga
    energy_motos = motos_charging * bat_moto * fc
    energy_mototaxis = mototaxis_charging * bat_mototaxi * fc
    energy_day = energy_motos + energy_mototaxis

    # Sesiones por hora pico
    sessions_peak_hour = total_vehicles / peak_hours

    # Cargadores necesarios
    sessions_per_socket_hour = 60 / (session_minutes / utilization)
    capacity_per_charger_hour = sockets_per_charger * sessions_per_socket_hour
    chargers = math.ceil(sessions_peak_hour / max(capacity_per_charger_hour, 1e-9))

    # Métricas derivadas
    sockets_total = chargers * sockets_per_charger
    sessions_4h = sessions_peak_hour * 4
    cargas_dia = energy_day / 1.06  # Según nota Tabla 13
    potencia_pico = energy_day * 0.125  # Según nota Tabla 13

    return {
        'pe': pe,
        'fc': fc,
        'chargers': chargers,
        'sockets_total': sockets_total,
        'sessions_4h': sessions_4h,
        'cargas_dia': cargas_dia,
        'energy_day': energy_day,
        'potencia_pico': potencia_pico,
    }

# Generar 101 escenarios aleatorios
rng = np.random.default_rng(42)
pe_values = np.linspace(0.10, 1.0, 10)
fc_values = np.linspace(0.40, 1.0, 7)

print(f"\nRangos de PE: {pe_values}")
print(f"Rangos de FC: {fc_values}")

# Generar escenarios únicos
scenarios = []
pe_fc_pairs = []

for pe in pe_values:
    for fc in fc_values:
        pe_fc_pairs.append((pe, fc))

# Seleccionar 101 combinaciones aleatorias (con reemplazo si es necesario)
rng.shuffle(pe_fc_pairs)
selected_pairs = pe_fc_pairs[:70]  # Solo 70 únicas disponibles

# Añadir más combinaciones aleatorias para llegar a 101
while len(selected_pairs) < 101:
    pe = rng.choice(pe_values)
    fc = rng.choice(fc_values)
    selected_pairs.append((pe, fc))

for pe, fc in selected_pairs[:101]:
    scenarios.append(evaluate_scenario(pe, fc))

df = pd.DataFrame(scenarios)

print(f"\n{'='*60}")
print("ESTADÍSTICAS SIMULADAS (101 escenarios)")
print('='*60)
print(f"Métrica                     |    Min |    Max |   Prom | Mediana")
print('-'*60)
print(f"Cargadores [unid]           | {df['chargers'].min():6.2f} | {df['chargers'].max():6.2f} | {df['chargers'].mean():6.2f} | {df['chargers'].median():6.2f}")
print(f"Tomas totales [tomas]       | {df['sockets_total'].min():6.2f} | {df['sockets_total'].max():6.2f} | {df['sockets_total'].mean():6.2f} | {df['sockets_total'].median():6.2f}")
print(f"Sesiones pico 4h [sesiones] | {df['sessions_4h'].min():6.2f} | {df['sessions_4h'].max():6.2f} | {df['sessions_4h'].mean():6.2f} | {df['sessions_4h'].median():6.2f}")
print(f"Cargas día total [cargas]   | {df['cargas_dia'].min():6.2f} | {df['cargas_dia'].max():6.2f} | {df['cargas_dia'].mean():6.2f} | {df['cargas_dia'].median():6.2f}")
print(f"Energía día [kWh]           | {df['energy_day'].min():6.2f} | {df['energy_day'].max():6.2f} | {df['energy_day'].mean():6.2f} | {df['energy_day'].median():6.2f}")
print(f"Potencia pico [kW]          | {df['potencia_pico'].min():6.2f} | {df['potencia_pico'].max():6.2f} | {df['potencia_pico'].mean():6.2f} | {df['potencia_pico'].median():6.2f}")

print(f"\n{'='*60}")
print("VALORES ESPERADOS TABLA 13")
print('='*60)
print(f"Cargadores [unid]           |   4.00 |  35.00 |  20.61 |  20.00")
print(f"Tomas totales [tomas]       |  16.00 | 140.00 |  82.46 |  80.00")
print(f"Sesiones pico 4h [sesiones] | 103.00 |1030.00 | 593.52 | 566.50")
print(f"Cargas día total [cargas]   |  87.29 |3058.96 | 849.83 | 785.62")
print(f"Energía día [kWh]           |  92.80 |3252.00 | 903.46 | 835.20")
print(f"Potencia pico [kW]          |  11.60 | 406.50 | 112.93 | 104.40")

# Calcular qué combinación produce energía máxima de 3252 kWh
print(f"\n{'='*60}")
print("ANÁLISIS PARA ALCANZAR VALORES MÁXIMOS")
print('='*60)

# E_max = n_motos × PE × FC × bat_moto + n_mototaxis × PE × FC × bat_mototaxi
# E_max = PE × FC × (n_motos × bat_moto + n_mototaxis × bat_mototaxi)
# E_max = PE × FC × (500 × 2 + 500 × 4) = PE × FC × 3000

# Con PE=1, FC=1: E_max = 3000 kWh
# Para 3252: PE × FC × 3000 = 3252 => PE × FC = 1.084 (imposible con PE,FC <= 1)

# Entonces la Tabla 13 usa diferentes valores de n_motos/n_mototaxis o baterías diferentes
# O la energía se calcula de forma diferente

target_energy_max = 3252
base_energy = n_motos * bat_moto + n_mototaxis * bat_mototaxi
print(f"Energía base (PE=1, FC=1): {base_energy} kWh")
print(f"Energía objetivo máxima: {target_energy_max} kWh")
print(f"Factor requerido: {target_energy_max / base_energy:.3f}")

# Si ajustamos las baterías:
# bat_avg_required = 3252 / (1000 × 1 × 1) = 3.252 kWh
# O si motos tienen 2.5 kWh y mototaxis 4.5 kWh:
# 500 × 2.5 + 500 × 4.5 = 1250 + 2250 = 3500 kWh (más que suficiente)

# Otra opción: la flota es mayor
# 3252 = N × 3 (promedio) × 1 × 1 => N = 1084 vehículos

print(f"\nOpciones para alcanzar 3252 kWh:")
print(f"  1. Usar batería promedio de 3.252 kWh")
print(f"  2. Usar flota de 1084 vehículos con bat_avg=3 kWh")
print(f"  3. Ajustar n_motos=542, n_mototaxis=542 (1084 total)")

# ============================================================
# AJUSTE PARA COINCIDIR CON TABLA 13
# ============================================================
print(f"\n{'='*60}")
print("SIMULACIÓN AJUSTADA PARA TABLA 13")
print('='*60)

# La Tabla 13 usa:
# - Energía máxima = 3252 kWh
# - Con PE=1, FC=1, necesitamos E_base = 3252 kWh
# - Si bat_moto=2, bat_mototaxi=4, entonces:
#   E = n_motos × 2 + n_mototaxis × 4 = 3252
#   Asumiendo n_motos = n_mototaxis = N:
#   N × 2 + N × 4 = 3252 => N × 6 = 3252 => N = 542

# Pero los valores mínimos sugieren PE=0.1 o menos
# Con E_min = 92.80 kWh y n_total=1000:
# 92.80 = PE × FC × 3000 => PE × FC = 0.0309
# Con FC=0.4 (mínimo), PE = 0.077 ≈ 0.08

# AJUSTE: Usar n_motos=542, n_mototaxis=542
n_motos_adj = 542
n_mototaxis_adj = 542
n_total_adj = n_motos_adj + n_mototaxis_adj

# O ajustar PE mínimo a 0.08
pe_values_adj = np.array([0.08, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.0])

# Recalcular con valores ajustados
def evaluate_scenario_adj(pe, fc, n_motos, n_mototaxis):
    total_vehicles = (n_motos + n_mototaxis) * pe

    # Energía basada en batería (como en Tabla 13)
    energy_day = n_motos * pe * fc * bat_moto + n_mototaxis * pe * fc * bat_mototaxi

    # Sesiones por hora pico (todos los vehículos llegan en 4 horas pico)
    sessions_peak_hour = total_vehicles / peak_hours

    # Cargadores
    sessions_per_socket_hour = 60 / (session_minutes / utilization)
    capacity_per_charger_hour = sockets_per_charger * sessions_per_socket_hour
    chargers = math.ceil(sessions_peak_hour / max(capacity_per_charger_hour, 1e-9))

    sockets_total = chargers * sockets_per_charger
    sessions_4h = sessions_peak_hour * 4
    cargas_dia = energy_day / 1.06
    potencia_pico = energy_day * 0.125

    return {
        'pe': pe, 'fc': fc,
        'chargers': chargers,
        'sockets_total': sockets_total,
        'sessions_4h': sessions_4h,
        'cargas_dia': cargas_dia,
        'energy_day': energy_day,
        'potencia_pico': potencia_pico,
    }

# Generar 101 escenarios con parámetros ajustados
scenarios_adj = []
rng2 = np.random.default_rng(42)

for _ in range(101):
    pe = rng2.choice(pe_values_adj)
    fc = rng2.choice(fc_values)
    scenarios_adj.append(evaluate_scenario_adj(pe, fc, n_motos_adj, n_mototaxis_adj))

df_adj = pd.DataFrame(scenarios_adj)

print(f"\nUsando n_motos={n_motos_adj}, n_mototaxis={n_mototaxis_adj}")
print(f"PE values: {pe_values_adj}")
print(f"\n{'='*60}")
print("ESTADÍSTICAS AJUSTADAS (101 escenarios)")
print('='*60)
print(f"Métrica                     |    Min |    Max |   Prom | Mediana")
print('-'*60)
print(f"Cargadores [unid]           | {df_adj['chargers'].min():6.2f} | {df_adj['chargers'].max():6.2f} | {df_adj['chargers'].mean():6.2f} | {df_adj['chargers'].median():6.2f}")
print(f"Tomas totales [tomas]       | {df_adj['sockets_total'].min():6.2f} | {df_adj['sockets_total'].max():6.2f} | {df_adj['sockets_total'].mean():6.2f} | {df_adj['sockets_total'].median():6.2f}")
print(f"Sesiones pico 4h [sesiones] | {df_adj['sessions_4h'].min():6.2f} | {df_adj['sessions_4h'].max():6.2f} | {df_adj['sessions_4h'].mean():6.2f} | {df_adj['sessions_4h'].median():6.2f}")
print(f"Cargas día total [cargas]   | {df_adj['cargas_dia'].min():6.2f} | {df_adj['cargas_dia'].max():6.2f} | {df_adj['cargas_dia'].mean():6.2f} | {df_adj['cargas_dia'].median():6.2f}")
print(f"Energía día [kWh]           | {df_adj['energy_day'].min():6.2f} | {df_adj['energy_day'].max():6.2f} | {df_adj['energy_day'].mean():6.2f} | {df_adj['energy_day'].median():6.2f}")
print(f"Potencia pico [kW]          | {df_adj['potencia_pico'].min():6.2f} | {df_adj['potencia_pico'].max():6.2f} | {df_adj['potencia_pico'].mean():6.2f} | {df_adj['potencia_pico'].median():6.2f}")

# Guardar parámetros óptimos
print(f"\n{'='*60}")
print("PARÁMETROS PARA chargers.py")
print('='*60)
print(f"n_motos = {n_motos_adj}")
print(f"n_mototaxis = {n_mototaxis_adj}")
print(f"pe_values = {list(pe_values_adj)}")
print(f"fc_values = {list(fc_values)}")
print(f"bat_moto = {bat_moto}")
print(f"bat_mototaxi = {bat_mototaxi}")
print(f"session_minutes = {session_minutes}")
print(f"sockets_per_charger = {sockets_per_charger}")
print(f"peak_hours = {peak_hours}")
print(f"utilization = {utilization}")
