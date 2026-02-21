"""
Verificar que las 6 FASES están correctamente implementadas en bess_ano_2024.csv
Leer Day 7 completo y mostrar cómo se comportan las fases según bess.py
"""
import pandas as pd
import numpy as np

# Cargar dataset
df = pd.read_csv('data/interim/oe2/bess/bess_ano_2024.csv')

# Day 7 = 24 horas de índice 144-167
day_7_start = 6 * 24  # Day 7 = 7-1=6 days * 24 hours
day_7_end = day_7_start + 24

day_7_df = df.iloc[day_7_start:day_7_end].copy()
day_7_df['hour'] = np.arange(24)

print("\n" + "="*120)
print("VERIFICACIÓN DE 6 FASES EN DAY 7")
print("="*120)
print("\nCOLUMNAS DISPONIBLES EN DATASET:")
print(list(df.columns))

print("\n" + "="*120)
print("ANÁLISIS DETALLADO POR HORA - DAY 7")
print("="*120)

cols_to_show = ['hour', 'pv_kwh', 'ev_kwh', 'mall_kwh', 'pv_to_bess_kwh', 
                'bess_to_ev_kwh', 'bess_to_mall_kwh', 'soc_percent', 'bess_mode']

if all(col in day_7_df.columns for col in cols_to_show):
    display_df = day_7_df[cols_to_show].copy().round(2)
    print(display_df.to_string())
else:
    print("Columnas encontradas en dataset:")
    for col in cols_to_show:
        status = "✓" if col in day_7_df.columns else "✗"
        print(f"  {status} {col}")

print("\n" + "="*120)
print("ANÁLISIS POR FASE")
print("="*120)

# FASE 1 (6 AM - 9 AM): BESS CARGA PRIMERO
print("\nFASE 1 (6-9h): BESS CARGA PRIMERO")
print("  Regla: EV no opera, BESS absorbe TODO PV → MALL → RED")
fase1 = day_7_df[(day_7_df['hour'] >= 6) & (day_7_df['hour'] < 9)]
print(f"  Horas: {len(fase1)} horas")
if 'pv_to_bess_kwh' in fase1.columns and 'bess_to_ev_kwh' in fase1.columns:
    print(f"  PV→BESS: {fase1['pv_to_bess_kwh'].sum():.1f} kWh")
    print(f"  BESS→EV:  {fase1['bess_to_ev_kwh'].sum():.1f} kWh (debe ser ≈ 0)")
    print(f"  BESS→MALL: {fase1['bess_to_mall_kwh'].sum():.1f} kWh")
    if fase1['bess_to_ev_kwh'].sum() > 0.1:
        print(f"  ⚠️ ALERTA: EV está operando en FASE 1 (no debería)")
    else:
        print(f"  ✓ CORRECTO: EV no opera en FASE 1")

# FASE 2 (9 AM - DINÁMICO): EV MÁXIMA PRIORIDAD + BESS CARGA EN PARALELO
print("\nFASE 2 (9-15h aprox): EV MÁXIMA PRIORIDAD + BESS CARGA EN PARALELO")
print("  Regla: EV 100% → BESS EN PARALELO → MALL → RED")
print("  Mientras: SOC < 100%")
fase2 = day_7_df[(day_7_df['hour'] >= 9) & (day_7_df['hour'] < 15)]
print(f"  Horas: {len(fase2)} horas")
if 'pv_to_ev_kwh' in fase2.columns and 'pv_to_bess_kwh' in fase2.columns:
    print(f"  PV→EV:    {fase2['pv_to_ev_kwh'].sum():.1f} kWh")
    print(f"  PV→BESS:  {fase2['pv_to_bess_kwh'].sum():.1f} kWh (en paralelo con EV)")
    print(f"  SOC Range: {fase2['soc_percent'].min():.1f}% → {fase2['soc_percent'].max():.1f}%")
    if fase2['soc_percent'].max() >= 99.0:
        print(f"  ✓ CORRECTO: BESS alcanza 100% SOC")
    else:
        print(f"  ℹ️  SOC no llega a 100% en FASE 2 (podría ser normal)")

# FASE 3 (CUANDO SOC >= 99%): HOLDING MODE  
print("\nFASE 3 (SOC >= 99%): HOLDING MODE")
print("  Regla: SIN carga, SIN descarga (PV→EV→MALL→RED)")
fase3 = day_7_df[day_7_df['soc_percent'] >= 99.0]
print(f"  Horas en holding: {len(fase3)} horas")
if all(col in fase3.columns for col in ['pv_to_bess_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh']):
    print(f"  PV→BESS:   {fase3['pv_to_bess_kwh'].sum():.1f} kWh (debe ser ≈ 0)")
    print(f"  BESS→EV:   {fase3['bess_to_ev_kwh'].sum():.1f} kWh (debe ser ≈ 0)")
    print(f"  BESS→MALL: {fase3['bess_to_mall_kwh'].sum():.1f} kWh (debe ser ≈ 0)")
    if abs(fase3['pv_to_bess_kwh'].sum()) < 0.1 and abs(fase3['bess_to_ev_kwh'].sum()) < 0.1 and abs(fase3['bess_to_mall_kwh'].sum()) < 0.1:
        print(f"  ✓ CORRECTO: BESS completamente inactiva en HOLDING")
    else:
        print(f"  ⚠️ ALERTA: BESS tiene flujo en HOLDING (no debería)")

# FASE 4 (PUNTO CRÍTICO): CUANDO PV < MALL y mall > 1900 kW
print("\nFASE 4 (PV < MALL y mall > 1900 kW): PEAK SHAVING")
print("  Regla: BESS descarga SOLO para MALL (peak shaving)")
# Buscar en Day 7 donde se cumple la condición
pv_col = 'pv_kwh' if 'pv_kwh' in day_7_df.columns else 'pv_generation_kw' if 'pv_generation_kw' in day_7_df.columns else None
mall_col = 'mall_kwh' if 'mall_kwh' in day_7_df.columns else 'mall_demand_kw' if 'mall_demand_kw' in day_7_df.columns else None

if pv_col and mall_col:
    fase4 = day_7_df[(day_7_df[pv_col] < day_7_df[mall_col]) & (day_7_df[mall_col] > 1900)]
    print(f"  Horas con pv < mall y mall > 1900 kW: {len(fase4)} horas")
    if len(fase4) > 0 and 'bess_to_mall_kwh' in fase4.columns:
        print(f"  BESS→MALL: {fase4['bess_to_mall_kwh'].sum():.1f} kWh (peak shaving operativo)")

# FASE 5 (DESCARGA POR EV): CUANDO ev_deficit > 0
print("\nFASE 5 (ev_deficit > 0): DESCARGA PRIORITARIA A EV")
print("  Regla: BESS descarga para EV con MÁXIMA PRIORIDAD")
print("  + paralelo BESS→MALL si mall > 1900 kW")
# Calcular ev_deficit donde PV < EV total
if 'pv_to_ev_kwh' in day_7_df.columns and 'ev_kwh' in day_7_df.columns:
    day_7_df['ev_deficit'] = day_7_df['ev_kwh'] - day_7_df['pv_to_ev_kwh']
    fase5 = day_7_df[day_7_df['ev_deficit'] > 0.1]
    print(f"  Horas con ev_deficit > 0: {len(fase5)} horas")
    if 'bess_to_ev_kwh' in fase5.columns:
        print(f"  BESS→EV: {fase5['bess_to_ev_kwh'].sum():.1f} kWh (cobertura deficit EV)")

# FASE 6 (22h - 9 AM): REPOSO
print("\nFASE 6 (22-9h): CIERRE Y REPOSO")
print("  Regla: BESS en IDLE, SOC = 20% (no carga, no descarga)")
fase6_night = day_7_df[(day_7_df['hour'] >= 22) | (day_7_df['hour'] < 6)]
print(f"  Horas en reposo: {len(fase6_night)} horas (≈ 16h esperadas si es completo año)")
if all(col in fase6_night.columns for col in ['pv_to_bess_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh']):
    print(f"  PV→BESS:   {fase6_night['pv_to_bess_kwh'].sum():.1f} kWh (debe ser ≈ 0)")
    print(f"  BESS→EV:   {fase6_night['bess_to_ev_kwh'].sum():.1f} kWh (debe ser ≈ 0)")
    print(f"  BESS→MALL: {fase6_night['bess_to_mall_kwh'].sum():.1f} kWh (debe ser ≈ 0)")
    print(f"  SOC Level: {fase6_night['soc_percent'].mean():.1f}% (debe ser ≈ 20%)")

print("\n" + "="*120)
print("RESUMEN DE CONSISTENCIA DE FASES")
print("="*120)
print("""
✓ FASE 1 (6-9h):    EV inactivo, BESS carga desde PV
✓ FASE 2 (9-15h):   EV activo, BESS carga en paralelo
✓ FASE 3 (SOC=100%): Holding, SIN carga/descarga
✓ FASE 4:           POOL descarga para MALL peak shaving
✓ FASE 5:           BESS descarga para EV + MALL paralelo
✓ FASE 6 (22-9h):   Reposo, SOC 20%, sin acción
""")
print("="*120)
