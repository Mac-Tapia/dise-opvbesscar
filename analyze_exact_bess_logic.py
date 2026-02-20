import pandas as pd
import numpy as np

# Cargar dataset original
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

# Revisar día 180 con la lógica exacta
day_idx = 180
day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()

print('=' * 160)
print('LÓGICA BESS EXACTA - DÍA 180')
print('=' * 160)
print()
print('Hora | PV | EV | Mall | Total | >1900? | SOC(%) | BESS_C(kW) | BESS_D(kW) | Estado | Lógica')
print('-' * 160)

for h in range(24):
    row = day_df.iloc[h]
    pv = row.get('pv_kwh', 0)
    ev = row.get('ev_kwh', 0)
    mall = row.get('mall_kwh', 0)
    total = mall + ev
    soc = row.get('soc_percent', 0)
    bess_c = row.get('bess_energy_stored_hourly_kwh', 0)
    bess_d = row.get('bess_energy_delivered_hourly_kwh', 0)
    
    # Determinar estado
    exceeds_1900 = "SÍ" if total > 1900 else "NO"
    
    # Lógica
    if bess_c > 0 and soc < 100:
        logica = "CARGA: PV→BESS (SOC<100%)"
    elif soc == 100 and bess_c == 0 and bess_d == 0:
        logica = "REPOSO: SOC 100%, espera déficit"
    elif pv < mall and bess_d > 0:
        logica = "DESCARGA: PV<Mall"
        if total > 1900:
            logica += " + CRÍTICO(>1900)"
    elif bess_d == 0 and soc > 20 and pv > mall:
        logica = "EXCEDENTE: PV>Mall, SOC no carga"
    else:
        logica = "SIN_ACCIÓN"
    
    estado = "CARGA" if bess_c > 0 else ("DESC" if bess_d > 0 else "REPOSO")
    print(f'{h:2d}h | {pv:5.0f} | {ev:5.0f} | {mall:8.0f} | {total:9.0f} | {exceeds_1900:>5} | {soc:6.1f} | {bess_c:10.1f} | {bess_d:10.1f} | {estado:6} | {logica}')

print()
print('=' * 160)
print('VERIFICACIÓN CIERRE DIARIO (SOC a las 22h debe ser ~20%)')
print('=' * 160)
print()

for h in [21, 22, 23]:
    row = day_df.iloc[h]
    soc = row.get('soc_percent', 0)
    print(f'Hora {h:2d}: SOC = {soc:5.1f}%')

print()
print('=' * 160)
print('VERIFICACIÓN NO USA RED PARA CARGA')
print('=' * 160)
print()

# Verificar si BESS se carga desde la red
# Carga BESS debe venir de PV solamente
grid_import = df['grid_import_kwh'].values
pv = df['pv_kwh'].values
bess_c = df['bess_energy_stored_hourly_kwh'].values
ev = df['ev_kwh'].values
mall = df['mall_kwh'].values

# Si hay carga BESS pero PV=0 y grid>0, entonces usa red
suspicious = (bess_c > 0) & (pv <= 0) & (grid_import > 0)
print(f'Horas donde BESS carga y PV=0 pero hay importación: {suspicious.sum()} de {len(df)}')
if suspicious.sum() < 10:
    print('Primeros ejemplos:')
    idx = np.where(suspicious)[0][:5]
    for i in idx:
        h = i % 24
        d = i // 24
        print(f'  Día {d} Hora {h}: BESS_C={bess_c[i]:.1f}, PV={pv[i]:.0f}, Grid={grid_import[i]:.0f}')
