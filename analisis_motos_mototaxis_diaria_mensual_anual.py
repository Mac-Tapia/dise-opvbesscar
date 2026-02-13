#!/usr/bin/env python
"""
Análisis: Cantidad de Motos y Mototaxis por Período (Diaria, Mensual, Anual)

Sistema de 128 Cargadores EV en Iquitos:
- Playa de Motos: 112 sockets (motos)
- Playa de Mototaxis: 16 sockets (mototaxis)

Cálculo de distribución por período.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

print("\n" + "="*90)
print("ANÁLISIS: CANTIDAD DE MOTOS Y MOTOTAXIS POR PERÍODO")
print("="*90)

# ═════════════════════════════════════════════════════════════════════════════════════════
# PARTE 1: DATOS GENERALES DEL SISTEMA
# ═════════════════════════════════════════════════════════════════════════════════════════

print("\n[1] ESPECIFICACIONES DEL SISTEMA DE CARGA")
print("─" * 90)

# Total de vehículos en el sistema
MOTOS_TOTAL = 112
MOTOTAXIS_TOTAL = 16
VEHICULOS_TOTAL = MOTOS_TOTAL + MOTOTAXIS_TOTAL

print(f"\n📊 CAPACIDAD INSTALADA:")
print(f"  • Motos (Sockets 001-112):        {MOTOS_TOTAL} unidades")
print(f"  • Mototaxis (Sockets 113-128):    {MOTOTAXIS_TOTAL} unidades")
print(f"  • TOTAL CARGADORES:               {VEHICULOS_TOTAL} puertos")

ratio_motos = MOTOS_TOTAL / VEHICULOS_TOTAL * 100
ratio_mototaxis = MOTOTAXIS_TOTAL / VEHICULOS_TOTAL * 100

print(f"\n📈 DISTRIBUCIÓN:")
print(f"  • Motos:       {ratio_motos:.1f}% ({MOTOS_TOTAL})")
print(f"  • Mototaxis:   {ratio_mototaxis:.1f}% ({MOTOTAXIS_TOTAL})")

# ═════════════════════════════════════════════════════════════════════════════════════════
# PARTE 2: CARGAR DATOS DE DEMANDA REAL DE MALL
# ═════════════════════════════════════════════════════════════════════════════════════════

print("\n[2] CARGAR DEMANDA REAL DE MALL")
print("─" * 90)

mall_demand_path = Path("data/interim/oe2/demandamallkwh/demandamallhorakwh.csv")

if mall_demand_path.exists():
    try:
        # Cargar con separador correcto
        df_demand = pd.read_csv(mall_demand_path, sep=';')
        df_demand.columns = ['FECHAHORA', 'kWh']
        
        # Parsear datetime
        df_demand['datetime'] = pd.to_datetime(df_demand['FECHAHORA'], format='%d/%m/%Y %H:%M', errors='coerce')
        df_demand = df_demand.dropna(subset=['datetime'])
        
        # Agrupar por día
        df_demand['fecha'] = df_demand['datetime'].dt.date
        df_demand['mes'] = df_demand['datetime'].dt.month
        df_demand['año'] = df_demand['datetime'].dt.year
        df_demand['hora'] = df_demand['datetime'].dt.hour
        df_demand['dia_semana'] = df_demand['datetime'].dt.day_name()
        
        print(f"✓ Dataset cargado: {len(df_demand)} registros horarios")
        print(f"  Período: {df_demand['datetime'].min().date()} a {df_demand['datetime'].max().date()}")
        print(f"  Energía total: {df_demand['kWh'].sum():,.0f} kWh")
        
    except Exception as e:
        print(f"⚠️  Error cargando demanda: {e}")
        df_demand = None
else:
    print(f"⚠️  Archivo no encontrado: {mall_demand_path}")
    df_demand = None

# ═════════════════════════════════════════════════════════════════════════════════════════
# PARTE 3: ESTIMAR DISTRIBUCIÓN DE MOTOS/MOTOTAXIS POR PERÍODO
# ═════════════════════════════════════════════════════════════════════════════════════════

print("\n[3] ANÁLISIS: UTILIZACIÓN POR PERÍODO")
print("─" * 90)

# Parámetros de carga (estimados según patrón típico)
HORAS_PICO_CARGA = 8  # 06:00 - 14:00 (máxima demanda solar)
HORAS_PICO_DESCARGA = 6  # 18:00 - 00:00 (pico de uso)
HORAS_FUERA_PICO = 10  # 14:00 - 00:00

# Capacidad de carga simultánea
CAPACIDAD_SIMULTANEA_MOTOS = 0.70  # 70% de 112 = 78 motos en paralelo
CAPACIDAD_SIMULTANEA_MOTOTAXIS = 0.75  # 75% de 16 = 12 mototaxis en paralelo

print(f"\n⚡ PARÁMETROS DE OPERACIÓN:")
print(f"  • Horas pico carga (solar):      06:00 - 14:00 ({HORAS_PICO_CARGA} h)")
print(f"  • Horas fuera pico:              14:00 - 00:00 ({HORAS_FUERA_PICO} h)")
print(f"  • Horas pico descarga (noche):   18:00 - 00:00 ({HORAS_PICO_DESCARGA} h)")

print(f"\n🔌 CAPACIDAD DE CARGA SIMULTÁNEA:")
motos_simultaneas_pico = int(MOTOS_TOTAL * CAPACIDAD_SIMULTANEA_MOTOS)
mototaxis_simultáneas_pico = int(MOTOTAXIS_TOTAL * CAPACIDAD_SIMULTANEA_MOTOTAXIS)

print(f"  • Motos en paralelo (pico):      {motos_simultaneas_pico} de {MOTOS_TOTAL}")
print(f"  • Mototaxis en paralelo (pico):  {mototaxis_simultáneas_pico} de {MOTOTAXIS_TOTAL}")
print(f"  • TOTAL simultáneo (pico):       {motos_simultaneas_pico + mototaxis_simultáneas_pico} de {VEHICULOS_TOTAL}")

# ═════════════════════════════════════════════════════════════════════════════════════════
# PARTE 4: DISTRIBUCIÓN DIARIA
# ═════════════════════════════════════════════════════════════════════════════════════════

print("\n[4] DISTRIBUCIÓN DIARIA")
print("─" * 90)

# Estimación de ciclos de carga/descarga por día
CICLOS_CARGA_DIA = 3  # Moto típica carga 3 veces/día (mañana, tarde, noche)
CICLOS_MOTOTAXI_DIA = 2  # Mototaxi ~2 veces/día (horarios más fijos)

# Motos que pasan por sistema diariamente
motos_cargadas_dia = int(MOTOS_TOTAL / CICLOS_CARGA_DIA)
motos_recargadas_dia = motos_cargadas_dia * CICLOS_CARGA_DIA

# Mototaxis que pasan por sistema diariamente
mototaxis_cargadas_dia = int(MOTOTAXIS_TOTAL / CICLOS_MOTOTAXI_DIA)
mototaxis_recargadas_dia = mototaxis_cargadas_dia * CICLOS_MOTOTAXI_DIA

print(f"\n📅 UTILIZACIÓN DIARIA (Escenario Normal):")
print(f"\n  MOTOS:")
print(f"    • Unidades únicas cargadas/día:    {motos_cargadas_dia} motos")
print(f"    • Total recargas (3 ciclos):       {motos_recargadas_dia} transacciones")
print(f"    • Ciclo promedio:                  {CICLOS_CARGA_DIA} cargas/moto/día")
print(f"    • En carga simultánea (pico):      {motos_simultaneas_pico} motos")

print(f"\n  MOTOTAXIS:")
print(f"    • Unidades únicas cargadas/día:    {mototaxis_cargadas_dia} mototaxis")
print(f"    • Total recargas (2 ciclos):       {mototaxis_recargadas_dia} transacciones")
print(f"    • Ciclo promedio:                  {CICLOS_MOTOTAXI_DIA} cargas/mototaxi/día")
print(f"    • En carga simultánea (pico):      {mototaxis_simultáneas_pico} mototaxis")

print(f"\n  TOTAL DIARIO:")
print(f"    • Vehículos únicos transitando:    {motos_cargadas_dia + mototaxis_cargadas_dia} de {VEHICULOS_TOTAL}")
print(f"    • Total transacciones/día:         {motos_recargadas_dia + mototaxis_recargadas_dia}")
print(f"    • Ocupación promedio (24h):        {((motos_simultaneas_pico + mototaxis_simultáneas_pico) / VEHICULOS_TOTAL * 100):.1f}%")

# ═════════════════════════════════════════════════════════════════════════════════════════
# PARTE 5: DISTRIBUCIÓN HORARIA (PERFIL TÍPICO)
# ═════════════════════════════════════════════════════════════════════════════════════════

print("\n[5] DISTRIBUCIÓN HORARIA (PATRÓN TÍPICO)")
print("─" * 90)

# Crear perfil horario de ocupación
horas = np.arange(0, 24)
ocupacion = np.array([
    0.05, 0.05, 0.05, 0.05, 0.10, 0.15,  # 00:00-05:00: Mínimo (servicios nocturnos)
    0.50, 0.70, 0.85, 0.90, 0.85, 0.80,  # 06:00-11:00: Pico SOLAR (máxima carga)
    0.75, 0.70, 0.65, 0.60, 0.55, 0.65,  # 12:00-17:00: Descenso gradual
    0.80, 0.95, 0.90, 0.60, 0.30, 0.10   # 18:00-23:00: Pico DEMANDA (descarga nocturna)
])

print(f"\n⏰ OCUPACIÓN POR HORA (% de capacidad en uso):")
print(f"\n{'Hora':<8}{'% Ocupación':<15}{'Motos Aprox.':<18}{'Mototaxis Aprox.':<18}")
print("─" * 60)

for h in horas:
    ocu_percent = ocupacion[h] * 100
    motos_activas = int(MOTOS_TOTAL * ocupacion[h])
    mototaxis_activos = int(MOTOTAXIS_TOTAL * ocupacion[h])
    
    # Destacar horas pico
    marker = "⭐" if ocupacion[h] > 0.80 else ""
    print(f"{h:02d}:00 {marker:<2}{ocu_percent:>6.1f}%         {motos_activas:>3}               {mototaxis_activos:>2}")

# ═════════════════════════════════════════════════════════════════════════════════════════
# PARTE 6: DISTRIBUCIÓN MENSUAL
# ═════════════════════════════════════════════════════════════════════════════════════════

print("\n[6] DISTRIBUCIÓN MENSUAL")
print("─" * 90)

meses_año = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# Variación mensual (estación lluviosa/seca en Iquitos)
# Enero-Marzo: lluvia (menos viajes)
# Abril-Octubre: seco (más viajes)
# Noviembre-Diciembre: transición

variacion_estacional = np.array([
    0.85, 0.85, 0.90,  # Enero-Marzo (estación lluviosa)
    1.00, 1.05, 1.10,  # Abril-Junio (seco)
    1.10, 1.15, 1.10,  # Julio-Septiembre (seco)
    1.05, 0.95, 0.85   # Octubre-Diciembre (transición)
])

print(f"\n📊 CARGA ESTACIONAL (Variación mensual respecto a promedio):")
print(f"\n{'Mes':<12}{'Variación':<15}{'Motos/Día':<18}{'Mototaxis/Día':<18}")
print("─" * 65)

for i, mes in enumerate(meses_año):
    var_percent = (variacion_estacional[i] - 1) * 100
    motos_mes = int(motos_cargadas_dia * variacion_estacional[i])
    mototaxis_mes = int(mototaxis_cargadas_dia * variacion_estacional[i])
    
    print(f"{mes:<12}{var_percent:>+6.1f}%         {motos_mes:>3}              {mototaxis_mes:>2}")

# ═════════════════════════════════════════════════════════════════════════════════════════
# PARTE 7: PROYECCIÓN ANUAL
# ═════════════════════════════════════════════════════════════════════════════════════════

print("\n[7] PROYECCIÓN ANUAL")
print("─" * 90)

# Calcular totales anuales
año_2024 = 365  # 2024 bisiesto
dias_laborales = int(año_2024 * 0.86)  # ~86% laborales
dias_fin_semana = año_2024 - dias_laborales

# Motos anuales
motos_transacciones_diarias_prom = motos_recargadas_dia  # 3 ciclos
motos_transacciones_anuales = motos_transacciones_diarias_prom * año_2024

# Mototaxis anuales
mototaxis_transacciones_diarias_prom = mototaxis_recargadas_dia  # 2 ciclos
mototaxis_transacciones_anuales = mototaxis_transacciones_diarias_prom * año_2024

# Con variación estacional
motos_transacciones_estacional = motos_transacciones_diarias_prom * variacion_estacional.sum()
mototaxis_transacciones_estacional = mototaxis_transacciones_diarias_prom * variacion_estacional.sum()

print(f"\n💾 ESTADÍSTICAS ANUALES (2024 - 365 días):")
print(f"\n  MOTOS:")
print(f"    • Ciclos carga/día (promedio):     {CICLOS_CARGA_DIA}")
print(f"    • Transacciones/año (sin variación):  {motos_transacciones_anuales:,}")
print(f"    • Transacciones/año (c/estacionalidad): {int(motos_transacciones_estacional):,}")
print(f"    • Cobertura anual:                 {MOTOS_TOTAL} motos × {año_2024} días")

print(f"\n  MOTOTAXIS:")
print(f"    • Ciclos carga/día (promedio):     {CICLOS_MOTOTAXI_DIA}")
print(f"    • Transacciones/año (sin variación):  {mototaxis_transacciones_anuales:,}")
print(f"    • Transacciones/año (c/estacionalidad): {int(mototaxis_transacciones_estacional):,}")
print(f"    • Cobertura anual:                 {MOTOTAXIS_TOTAL} mototaxis × {año_2024} días")

print(f"\n  TOTAL SISTEMA:")
total_transacciones = motos_transacciones_anuales + mototaxis_transacciones_anuales
total_transacciones_estacional = motos_transacciones_estacional + mototaxis_transacciones_estacional

print(f"    • Transacciones totales/año:       {int(total_transacciones):,}")
print(f"    • Transacciones (c/estacionalidad): {int(total_transacciones_estacional):,}")
print(f"    • Promedio diario:                 {int(total_transacciones / año_2024)} transacciones")

# ═════════════════════════════════════════════════════════════════════════════════════════
# PARTE 8: RESUMEN COMPARATIVO
# ═════════════════════════════════════════════════════════════════════════════════════════

print("\n[8] RESUMEN COMPARATIVO: MOTOS vs MOTOTAXIS")
print("─" * 90)

print(f"\n┌─────────────────────────┬──────────────────────┬──────────────────────┐")
print(f"│ MÉTRICA                 │ MOTOS                │ MOTOTAXIS            │")
print(f"├─────────────────────────┼──────────────────────┼──────────────────────┤")
print(f"│ Cantidad del sistema    │ {MOTOS_TOTAL:>18} │ {MOTOTAXIS_TOTAL:>18} │")
print(f"│ % del total             │ {ratio_motos:>17.1f}% │ {ratio_mototaxis:>17.1f}% │")
print(f"│ Ciclos carga/día        │ {CICLOS_CARGA_DIA:>18} │ {CICLOS_MOTOTAXI_DIA:>18} │")
print(f"│ Únicas cargadas/día     │ {motos_cargadas_dia:>18} │ {mototaxis_cargadas_dia:>18} │")
print(f"│ Transacciones/día       │ {motos_recargadas_dia:>18} │ {mototaxis_recargadas_dia:>18} │")
print(f"│ Simultáneas (pico)      │ {motos_simultaneas_pico:>18} │ {mototaxis_simultáneas_pico:>18} │")
print(f"│ Transacciones/año       │ {int(motos_transacciones_anuales):>18,} │ {int(mototaxis_transacciones_anuales):>18,} │")
print(f"└─────────────────────────┴──────────────────────┴──────────────────────┘")

# ═════════════════════════════════════════════════════════════════════════════════════════
# PARTE 9: GUARDAR RESULTADOS EN CSV
# ═════════════════════════════════════════════════════════════════════════════════════════

print("\n[9] GUARDAR RESULTADOS")
print("─" * 90)

# Crear DataFrames para exportar
output_dir = Path("data/interim/oe2/analisis")
output_dir.mkdir(parents=True, exist_ok=True)

# 1. Distribución horaria
df_horario_perfil = pd.DataFrame({
    'Hora': horas,
    'Ocupacion_Percent': ocupacion * 100,
    'Motos_Aprox': (MOTOS_TOTAL * ocupacion).astype(int),
    'Mototaxis_Aprox': (MOTOTAXIS_TOTAL * ocupacion).astype(int),
})

csv_hourly = output_dir / "distribucion_horaria.csv"
df_horario_perfil.to_csv(csv_hourly, index=False)
print(f"✓ Guardado: {csv_hourly}")

# 2. Distribución mensual
df_mensual = pd.DataFrame({
    'Mes': meses_año,
    'Numero_Mes': range(1, 13),
    'Variacion_Estacional': (variacion_estacional - 1) * 100,
    'Motos_Por_Dia': (motos_cargadas_dia * variacion_estacional).astype(int),
    'Mototaxis_Por_Dia': (mototaxis_cargadas_dia * variacion_estacional).astype(int),
})

csv_monthly = output_dir / "distribucion_mensual.csv"
df_mensual.to_csv(csv_monthly, index=False)
print(f"✓ Guardado: {csv_monthly}")

# 3. Resumen anual
df_anual = pd.DataFrame({
    'Categoria': ['Motos', 'Mototaxis', 'Total'],
    'Cantidad_Sistema': [MOTOS_TOTAL, MOTOTAXIS_TOTAL, VEHICULOS_TOTAL],
    'Ciclos_Dia': [CICLOS_CARGA_DIA, CICLOS_MOTOTAXI_DIA, '-'],
    'Transacciones_Dia': [motos_recargadas_dia, mototaxis_recargadas_dia, motos_recargadas_dia + mototaxis_recargadas_dia],
    'Transacciones_Año': [int(motos_transacciones_anuales), int(mototaxis_transacciones_anuales), int(total_transacciones)],
})

csv_annual = output_dir / "resumen_anual.csv"
df_anual.to_csv(csv_annual, index=False)
print(f"✓ Guardado: {csv_annual}")

print("\n" + "="*90)
print("✅ ANÁLISIS COMPLETADO")
print("="*90 + "\n")
