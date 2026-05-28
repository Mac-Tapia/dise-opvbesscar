import pandas as pd
import numpy as np

bess = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
bess['datetime'] = pd.to_datetime(bess['datetime'])
bess['hour'] = bess['datetime'].dt.hour

fase1 = bess[bess['hour'].between(6, 14)]
fase2 = bess[bess['hour'].between(15, 16)]
fase3 = bess[bess['hour'].between(17, 21)]

print("=== VALIDACION TABLA 28: FASES OPERATIVAS BESS ===")
print()
print("FASE 1 - CARGA (6:00-15:00):")
print("  Energia cargada: {:,.0f} kWh/ano".format(fase1['bess_charge_kwh'].sum()))
print("  SOC promedio inicio (6h): {:.1f}%".format(bess[bess['hour']==6]['soc_percent'].mean()))
print("  SOC promedio fin (14h): {:.1f}%".format(bess[bess['hour']==14]['soc_percent'].mean()))
print()
print("FASE 2 - ESTANCO (15:00-17:00):")
print("  Energia cargada: {:,.0f} kWh/ano".format(fase2['bess_charge_kwh'].sum()))
print("  Energia descargada: {:,.0f} kWh/ano".format(fase2['bess_discharge_kwh'].sum()))
print("  SOC promedio: {:.1f}%".format(bess[bess['hour'].between(15,16)]['soc_percent'].mean()))
print()
print("FASE 3 - DESCARGA (17:00-22:00):")
print("  Energia descargada: {:,.0f} kWh/ano".format(fase3['bess_discharge_kwh'].sum()))
print("  BESS->EV: {:,.0f} kWh/ano".format(fase3['bess_to_ev_kwh'].sum()))
print("  BESS->Mall: {:,.0f} kWh/ano".format(fase3['bess_to_mall_kwh'].sum()))
print("  SOC promedio inicio (17h): {:.1f}%".format(bess[bess['hour']==17]['soc_percent'].mean()))
print("  SOC promedio fin (21h): {:.1f}%".format(bess[bess['hour']==21]['soc_percent'].mean()))

fase3_peaks = fase3[fase3['mall_kwh'] > 1900]
print("  Horas 17-22h con mall > 1900 kW: {}".format(len(fase3_peaks)))
print("  BESS->Mall en picos HP: {:,.0f} kWh/ano".format(fase3_peaks['bess_to_mall_kwh'].sum()))

print()
print("=== PRIORIDAD EV VERIFICADA ===")
print("BESS->EV total: {:,.0f} kWh/ano".format(bess['bess_to_ev_kwh'].sum()))
print("BESS->Mall total: {:,.0f} kWh/ano".format(bess['bess_to_mall_kwh'].sum()))
ev_pos = bess['bess_to_ev_kwh'] > 0
mall_pos = bess['bess_to_mall_kwh'] > 0
print("Horas con descarga simultanea EV+Mall: {}".format(int((ev_pos & mall_pos).sum())))

print()
print("=== PEAK SHAVING HFP (12-16h) ===")
hfp = bess[bess['hour'].between(12, 16) & (bess['mall_kwh'] > 1900)]
print("Horas HFP con mall > 1900 kW: {}".format(len(hfp)))
print("BESS descarga HFP picos: {:,.0f} kWh".format(hfp['bess_discharge_kwh'].sum()))
print("BESS->Mall HFP picos: {:,.0f} kWh".format(hfp['bess_to_mall_kwh'].sum()))
print()
print("Razon: a 12-15h, PV cubre toda la demanda de mall (PV >> mall)")
pv_col = 'pv_kwh'
print("  PV promedio 12-15h: {:,.0f} kW".format(bess[bess['hour'].between(12,15)][pv_col].mean()))
print("  Mall promedio 12-15h: {:,.0f} kW".format(bess[bess['hour'].between(12,15)]['mall_kwh'].mean()))
print("  PV cubre mall en 12-15h: {:.1f}% horas".format(
    100 * (bess[bess['hour'].between(12,15)][pv_col] >= bess[bess['hour'].between(12,15)]['mall_kwh']).mean()
))
