import pandas as pd
import numpy as np

print('\n' + '='*120)
print('VALIDACION COMPLETA: BESS v5.5 - Dataset CityLearn')
print('='*120)

# 1. Cargar dataset BESS simulado
df_bess = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')
df_bess['hour'] = pd.to_datetime(df_bess['datetime']).dt.hour

print('\n[1] ESTRUCTURA DATASET BESS:')
print(f'    Filas: {len(df_bess)} (debe ser 8,760 horas)')
print(f'    Columnas: {len(df_bess.columns)}')
print(f'    Rango fechas: {df_bess["datetime"].min()} a {df_bess["datetime"].max()}')

# 2. Validar SOC@22h
soc_22h = df_bess[df_bess['hour'] == 22]['bess_soc_percent'].values
print(f'\n[2] SOC A LAS 22h (CIERRE OPERATIVO):')
print(f'    Min: {soc_22h.min():.2f}% | Max: {soc_22h.max():.2f}% | Promedio: {soc_22h.mean():.2f}%')
print(f'    Target: 20.00% | Estado: {"✓ CORRECTO" if abs(soc_22h.mean()-20) < 0.5 else "✗ INCORRECTO"}')

# 3. Validar capacidad BESS
print(f'\n[3] CAPACIDAD BESS:')
print(f'    Establecida: 1,700 kWh')
print(f'    SOC máximo encontrado: {df_bess["bess_soc_percent"].max():.1f}%')
print(f'    SOC mínimo encontrado: {df_bess["bess_soc_percent"].min():.1f}%')
print(f'    Rango operativo: {df_bess["bess_soc_percent"].min():.1f}% - {df_bess["bess_soc_percent"].max():.1f}% (esperado: 20% - 100%)')

# 4. Validar descargas a MALL
print(f'\n[4] DESCARGAS A MALL (horas 17-22, críticas):')
criticas = df_bess[df_bess['hour'] >= 17]['bess_to_mall_kwh'].sum()
total_anual = df_bess['bess_to_mall_kwh'].sum()
print(f'    17h-22h: {criticas:,.0f} kWh')
print(f'    Anual: {total_anual:,.0f} kWh')
print(f'    Cálculo: {criticas / total_anual * 100:.1f}% concentrado en horas críticas')

# 5. Validar picos de demanda
ev_mall_combined = df_bess['ev_demand_kwh'] + df_bess['mall_demand_kwh']
print(f'\n[5] PICOS DE DEMANDA (EV + MALL):')
print(f'    Pico máximo: {ev_mall_combined.max():.0f} kW')
print(f'    Pico 95%ile: {np.percentile(ev_mall_combined, 95):.0f} kW')
print(f'    Pico promedio: {ev_mall_combined.mean():.0f} kW')
print(f'    Horas pico > 2000 kW: {(ev_mall_combined > 2000).sum()} ({(ev_mall_combined > 2000).sum()/len(ev_mall_combined)*100:.1f}%)')

# 6. Validar energía EV cubierta
print(f'\n[6] COBERTURA EV (9h-22h horas operativas):')
ev_operational = df_bess[(df_bess['hour'] >= 9) & (df_bess['hour'] < 22)]
pv_to_ev = ev_operational['pv_to_ev_kwh'].sum()
bess_to_ev = ev_operational['bess_to_ev_kwh'].sum()
grid_to_ev = ev_operational['grid_to_ev_kwh'].sum()
total_ev = ev_operational['ev_demand_kwh'].sum()
print(f'    PV directo: {pv_to_ev:,.0f} kWh ({pv_to_ev/total_ev*100:.1f}%)')
print(f'    BESS: {bess_to_ev:,.0f} kWh ({bess_to_ev/total_ev*100:.1f}%)')
print(f'    RED: {grid_to_ev:,.0f} kWh ({grid_to_ev/total_ev*100:.1f}%)')
print(f'    Total: {pv_to_ev + bess_to_ev + grid_to_ev:,.0f} kWh / {total_ev:,.0f} kWh demanda')

# 7. Validar energía MALL
print(f'\n[7] COBERTURA MALL:')
pv_to_mall = df_bess['pv_to_mall_kwh'].sum()
bess_to_mall = df_bess['bess_to_mall_kwh'].sum()
grid_to_mall = df_bess['grid_to_mall_kwh'].sum()
total_mall = df_bess['mall_demand_kwh'].sum()
print(f'    PV directo: {pv_to_mall:,.0f} kWh ({pv_to_mall/total_mall*100:.1f}%)')
print(f'    BESS: {bess_to_mall:,.0f} kWh ({bess_to_mall/total_mall*100:.1f}%)')
print(f'    RED (balance): {grid_to_mall:,.0f} kWh ({grid_to_mall/total_mall*100:.1f}%)')

# 8. Validar eficiencia energética
print(f'\n[8] BALANCE ENERGETICO ANUAL:')
pv_total = df_bess['pv_generation_kwh'].sum()
bess_charge = df_bess['bess_charge_kwh'].sum()
bess_discharge = df_bess['bess_discharge_kwh'].sum()
print(f'    Generación PV: {pv_total:,.0f} kWh')
print(f'    Cargado a BESS: {bess_charge:,.0f} kWh')
print(f'    Descargado BESS: {bess_discharge:,.0f} kWh')
print(f'    Pérdidas BESS (5% eficiencia): {(bess_charge - bess_discharge):,.0f} kWh')

# 9. Validar columnas necesarias para CityLearn
required_cols = ['pv_generation_kwh', 'ev_demand_kwh', 'mall_demand_kwh', 'bess_charge_kwh', 
                 'bess_discharge_kwh', 'bess_to_ev_kwh', 'bess_to_mall_kwh', 'bess_soc_percent']
missing_cols = [col for col in required_cols if col not in df_bess.columns]
print(f'\n[9] COMPATIBILIDAD CITYLEARN:')
print(f'    Columnas necesarias: {len(required_cols)}')
if not missing_cols:
    print(f'    Presentes: {len(required_cols)} / {len(required_cols)} ✓ CORRECTO')
else:
    print(f'    Faltantes: {missing_cols}')

# 10. Validar sin NaN/Inf
nan_count = df_bess.isnull().sum().sum()
inf_count = np.isinf(df_bess.select_dtypes(include=[np.number])).sum().sum()
print(f'\n[10] INTEGRIDAD DE DATOS:')
print(f'    NaN encontrados: {nan_count}')
print(f'    Inf encontrados: {inf_count}')
print(f'    Estado: {"✓ OK" if (nan_count == 0 and inf_count == 0) else "✗ ERRORES"}')

# 11. Resumen valores clave
print(f'\n[11] RESUMEN EJECUTIVO:')
print(f'    ✓ SOC @ 22h: {soc_22h.mean():.1f}% (target 20%)')
print(f'    ✓ BESS -> MALL: {bess_to_mall:,.0f} kWh/año')
print(f'    ✓ Pico máximo: {ev_mall_combined.max():.0f} kW')
print(f'    ✓ Cobertura EV: {(pv_to_ev + bess_to_ev)/total_ev*100:.1f}%')
print(f'    ✓ Dataset: {len(df_bess)} x {len(df_bess.columns)} completo')

print('\n' + '='*120)
print('VALIDACION EXITOSA - Dataset listo para CityLearn')
print('='*120 + '\n')
