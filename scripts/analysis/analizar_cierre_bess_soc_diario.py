"""
ANALISIS: SOC DE CIERRE DIARIO DEL BESS (22h)
Pregunta: ¿Con cuánto SOC cierra el BESS cada día a las 22h?
          ¿Cuánto le falta para llegar al 20% (mínimo requerido)?
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Cargar simulación BESS completa
bess_csv = Path("data/oe2/bess/bess_ano_2024.csv")
df = pd.read_csv(bess_csv)

print("\n" + "="*80)
print("SOC DE CIERRE DIARIO DEL BESS (CLOSING HOUR = 22h)")
print("="*80)

# Extraer columna SOC
soc_col = None
for col in ['soc_percent', 'bess_soc_percent', 'SOC_%', 'soc_%']:
    if col in df.columns:
        soc_col = col
        break

if soc_col is None:
    print("ERROR: No se encontró columna SOC en el CSV")
    print(f"Columnas disponibles: {list(df.columns)}")
    exit(1)

# Añadir hora del día
df['hour'] = df.index % 24

# Analizar por día
closing_hour = 22
n_hours = len(df)
n_days = n_hours // 24

print(f"\nPeriodo: {n_days} días (8,760 horas)")
print(f"Hora de cierre: {closing_hour}h (22:00)")
print(f"SOC mínimo requerido: 20%")

# Extraer SOC de cierre (a las 22h) para cada día
soc_cierres = []
soc_deficit_lista = []

for day in range(n_days):
    idx_closing = day * 24 + closing_hour
    if idx_closing < len(df):
        soc_closing = df.loc[idx_closing, soc_col]
        soc_deficit = max(0, 20.0 - soc_closing)  # ¿Cuánto le falta para 20%?
        soc_cierres.append(soc_closing)
        soc_deficit_lista.append(soc_deficit)

soc_cierres = np.array(soc_cierres)
soc_deficit_lista = np.array(soc_deficit_lista)

# Estadísticas de cierre
print("\n" + "-"*80)
print("ESTADISTICAS DE CIERRE (SOC A LAS 22h)")
print("-"*80)
print(f"SOC Promedio:           {soc_cierres.mean():>8.2f}%")
print(f"SOC Mínimo:             {soc_cierres.min():>8.2f}%")
print(f"SOC Máximo:             {soc_cierres.max():>8.2f}%")
print(f"SOC Mediana:            {np.median(soc_cierres):>8.2f}%")
print(f"Desviacion Std:         {soc_cierres.std():>8.2f}%")

print("\n" + "-"*80)
print("DEFICIT PARA ALCANZAR SOC MINIMO (20%)")
print("-"*80)
print(f"Deficit Promedio:       {soc_deficit_lista.mean():>8.2f}% (kWh: {soc_deficit_lista.mean()*1700/100:.1f})")
print(f"Deficit Máximo:         {soc_deficit_lista.max():>8.2f}% (kWh: {soc_deficit_lista.max()*1700/100:.1f})")
print(f"Deficit Mínimo:         {soc_deficit_lista.min():>8.2f}% (kWh: {soc_deficit_lista.min()*1700/100:.1f})")
print(f"Horas bajo 20%:         {(soc_cierres < 20).sum()} días (cierra BAJO el mínimo)")
print(f"Horas sobre 20%:        {(soc_cierres >= 20).sum()} días (cierra SOBRE el mínimo)")

# Análisis detallado: ¿Qué % cierran exactamente a 20%?
close_to_20 = (soc_cierres >= 19.5) & (soc_cierres <= 20.5)
print(f"Cierres entre 19.5%-20.5%: {close_to_20.sum()} días")

# Mostrar los 10 primeros días
print("\n" + "-"*80)
print("DETALLE DE LOS PRIMEROS 30 DIAS")
print("-"*80)
print(f"{'DIA':<5} {'SOC CIERRE':<12} {'DEFICIT 20%':<15} {'ESTADO':<20}")
print("-"*80)

for day in range(min(30, n_days)):
    soc_c = soc_cierres[day]
    deficit = soc_deficit_lista[day]
    
    # Clasificar
    if soc_c < 15:
        estado = "⚠️ CRITICO (<15%)"
    elif soc_c < 20:
        estado = "🔴 BAJO (<20%)"
    elif abs(soc_c - 20) <= 1:
        estado = "✅ OPTIMO (~20%)"
    elif soc_c < 30:
        estado = "🟡 MODERADO (20-30%)"
    else:
        estado = "🟢 ALTO (>30%)"
    
    print(f"{day+1:<5} {soc_c:>10.2f}% {deficit:>13.2f}% {estado:<20}")

# Análisis de tendencias
print("\n" + "-"*80)
print("ANALISIS DE PATRONES")
print("-"*80)

# Calcular promedios mensuales
monthly_soc = []
for month in range(12):
    start_day = month * (365 // 12)
    end_day = (month + 1) * (365 // 12)
    monthly_avg = soc_cierres[start_day:end_day].mean()
    monthly_soc.append(monthly_avg)

print("\nSOC Promedio de Cierre por Mes:")
for month in range(12):
    print(f"  Mes {month+1:2d}: {monthly_soc[month]:6.2f}%")

# Comparar primeros 100 días vs últimos 100 días
print("\n" + "-"*80)
print("COMPARACION: Primeros 100 días vs Últimos 100 días")
print("-"*80)
early_soc = soc_cierres[:100].mean()
late_soc = soc_cierres[-100:].mean()
print(f"Primeros 100 días: {early_soc:.2f}% promedio")
print(f"Últimos 100 días:  {late_soc:.2f}% promedio")
print(f"Diferencia:        {abs(early_soc - late_soc):.2f}% ({'+' if late_soc > early_soc else '-'} tendencia)")

# Conclusión
print("\n" + "="*80)
print("CONCLUSIONES")
print("="*80)

if soc_cierres.mean() < 20:
    print(f"""
El BESS cierra en promedio a {soc_cierres.mean():.2f}%, DEBAJO del 20% requerido.
- Falta promedio: {soc_deficit_lista.mean():.2f}% ({soc_deficit_lista.mean()*1700/100:.1f} kWh)
- Esto indica que la estrategia de PICO SHAVING consume más energía de la
  que puede recuperarse en 24h.
- ACCION: Reducir la descarga a MALL o aumentar BESS capacity/power
""")
elif soc_cierres.mean() > 25:
    print(f"""
El BESS cierra en promedio a {soc_cierres.mean():.2f}%, ARRIBA del 20% requerido.
- Excedente promedio: {soc_cierres.mean() - 20:.2f}% ({(soc_cierres.mean()-20)*1700/100:.1f} kWh)
- Esto indica que la estrategia es CONSERVADORA y subutiliza el BESS.
- OPORTUNIDAD: Mayor capacidad disponible para peak shaving o descarga.
""")
else:
    print(f"""
El BESS cierra en promedio a {soc_cierres.mean():.2f}%, cercano al 20% requerido.
- Deficit/Excedente: {soc_deficit_lista.mean():.2f}% (prácticamente en equilibrio)
- Esto indica que la estrategia está BIEN CALIBRADA.
- ESTABILIDAD: El BESS completa su ciclo diario de forma predecible.
""")

print("="*80 + "\n")
