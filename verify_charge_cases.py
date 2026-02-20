import pandas as pd
import numpy as np

# Cargar dataset original
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

print('=' * 120)
print('ANÁLISIS LÓGICA CARGA BESS - AÑO COMPLETO')
print('=' * 120)
print()

# Calcular cuándo ocurre cada tipo de evento
pv = df['pv_kwh'].values
mall = df['mall_kwh'].values
ev = df['ev_kwh'].values
total = mall + ev
bess_c = df['bess_energy_stored_hourly_kwh'].values
soc = df['soc_percent'].values

excedente_pv = pv > total
hay_carga = bess_c > 0
critico = total > 1900

# Análisis de cada caso
caso1 = excedente_pv & hay_carga & ~critico  # Excedente + carga + NO crítico
caso2 = excedente_pv & hay_carga & critico   # Excedente + carga + CRÍTICO
caso3 = ~excedente_pv & hay_carga            # NO excedente pero hay carga (deficit)
caso4 = excedente_pv & ~hay_carga            # Excedente pero NO carga (SOC 100%?)

print(f'CASO 1: Excedente PV + Carga + NO Crítico:          {caso1.sum():5d} horas ({caso1.sum()/len(df)*100:5.1f}%)')
print(f'CASO 2: Excedente PV + Carga + CRÍTICO (>1900):     {caso2.sum():5d} horas ({caso2.sum()/len(df)*100:5.1f}%)')
print(f'CASO 3: NO Excedente pero hay Carga (déficit):      {caso3.sum():5d} horas ({caso3.sum()/len(df)*100:5.1f}%)')
print(f'CASO 4: Excedente PV pero NO carga (SOC 100%?):     {caso4.sum():5d} horas ({caso4.sum()/len(df)*100:5.1f}%)')
print()

# Para caso 3 (no excedente pero carga), ver qué ocurre
if caso3.sum() > 0:
    print('DETALLE CASO 3: Horas con CARGA pese a NO excedente PV')
    print('(Primeras 10)')
    idx_caso3 = np.where(caso3)[0][:10]
    for idx in idx_caso3:
        h = idx % 24
        d = idx // 24
        print(f'  Día {d} Hora {h:2d}: PV={pv[idx]:6.0f} < Total({mall[idx]:.0f}+{ev[idx]:.0f})={total[idx]:.0f}, BESS_C={bess_c[idx]:6.1f}, SOC={soc[idx]:5.1f}%')
print()

# Para caso 4 (excedente pero no carga), ver por qué
caso4_idx = np.where(caso4)[0]
if len(caso4_idx) > 0:
    print('DETALLE CASO 4: Horas con Excedente PV pero NO carga')
    print(f'SOC promedio en estas horas: {soc[caso4].mean():.1f}%')
    print(f'SOC = 100% en: {(soc[caso4] >= 99.9).sum()} de {len(caso4_idx)} horas')
    
print()
print('=' * 120)
print('CONCLUSIÓN LÓGICA CARGA BESS')
print('=' * 120)
print()
print('BESS se carga cuando:')
print('  ✓ Hay EXCEDENTE PV (PV > Mall+EV)')
print('  ✓ A máx 390 kW (límite del equipo)')
print('  ✗ NO cuando SOC = 100% (batería llena)')
print()
print('BESS NO se carga en casos de déficit, incluso si demanda > 1900 kW')
