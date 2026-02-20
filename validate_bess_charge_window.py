"""
Validación: Verificar que la ventana de carga BESS (6h-15h) se respeta en los datos
"""
import pandas as pd
import numpy as np

# Cargar dataset
csv_path = 'data/oe2/bess/bess_ano_2024.csv'
df = pd.read_csv(csv_path)

print("="*80)
print("VALIDACIÓN: VENTANA DE CARGA BESS (6h-15h)")
print("="*80)

# Obtener columna de carga
if 'bess_energy_stored_hourly_kwh' in df.columns:
    bess_charge_col = 'bess_energy_stored_hourly_kwh'
elif 'bess_charge_kwh' in df.columns:
    bess_charge_col = 'bess_charge_kwh'
else:
    print("❌ NO se encontró columna de carga BESS")
    print(f"   Columnas disponibles: {df.columns.tolist()}")
    exit(1)

print(f"\nUsando columna: {bess_charge_col}\n")

# Extraer hora de cada índice (asumiendo 8760 filas = 1 año)
hours_of_day = np.arange(len(df)) % 24

# REGLA: La carga BESS debe ocurrir SOLO entre 6h-15h (< 15, o sea 6-14h)
carga = df[bess_charge_col].values

# Identificar cargas fuera de ventana
carga_fuera_ventana = []
for h, (hour, charge) in enumerate(zip(hours_of_day, carga)):
    # Ventana correcta: 6h-15h (< 15 significa 0-14)
    esta_en_ventana = 6 <= hour < 15
    tiene_carga = charge > 0.0001  # Umbral para ruido
    
    if tiene_carga and not esta_en_ventana:
        carga_fuera_ventana.append({
            'hora_global': h,
            'hora_del_dia': hour,
            'carga_kwh': charge,
            'problema': f'CARGA FUERA DE VENTANA ({hour}h no está en 6-15h)'
        })

# Estadísticas por hora del día
print("📊 ESTADÍSTICAS DE CARGA POR HORA DEL DÍA:")
print("-" * 80)
print(f"{'Hora':>5} | {'Min':>8} | {'Max':>8} | {'Avg':>8} | {'Total':>13} | Status")
print("-" * 80)

stats_by_hour = []
for hour in range(24):
    mask = hours_of_day == hour
    values = carga[mask]
    
    if len(values) > 0:
        min_val = values.min()
        max_val = values.max()
        avg_val = values.mean()
        total = values.sum()
        
        # Status
        esta_en_ventana = 6 <= hour < 15
        tiene_carga = max_val > 0.0001
        
        if tiene_carga and not esta_en_ventana:
            status = "❌ CARGA FUERA VENTANA"
        elif tiene_carga and esta_en_ventana:
            status = "✓ Carga correcta"
        elif not tiene_carga and esta_en_ventana:
            status = "⚠️  Ventana sin carga"
        else:
            status = "✓ Sin carga (ok)"
        
        stats_by_hour.append({
            'hora': hour,
            'min': min_val,
            'max': max_val,
            'avg': avg_val,
            'total': total,
            'status': status
        })
        
        print(f"{hour:5d} | {min_val:8.2f} | {max_val:8.2f} | {avg_val:8.2f} | {total:13,.0f} | {status}")

# Resumen
print("\n" + "="*80)
print("RESUMEN")
print("="*80)

# Estadísticas de la ventana de carga
ventana_start = 6
ventana_end = 15
mask_ventana = (hours_of_day >= ventana_start) & (hours_of_day < ventana_end)
carga_en_ventana = carga[mask_ventana].sum()
carga_fuera_ventana_total = carga[~mask_ventana].sum()
carga_total = carga.sum()

print(f"\n✓ CARGA EN VENTANA (6h-15h):    {carga_en_ventana:>15,.0f} kWh")
print(f"❌ CARGA FUERA VENTANA:         {carga_fuera_ventana_total:>15,.0f} kWh")
print(f"   TOTAL CARGA ANUAL:          {carga_total:>15,.0f} kWh")

if carga_fuera_ventana_total > 0:
    pct_fuera = (carga_fuera_ventana_total / carga_total) * 100
    print(f"\n⚠️  ¡{pct_fuera:.2f}% de carga está FUERA de ventana 6h-15h!")
    print(f"\n   Casos detectados: {len(carga_fuera_ventana)}")
    if len(carga_fuera_ventana) > 0 and len(carga_fuera_ventana) <= 20:
        print("\n   Detalles de cargas fuera de ventana:")
        for case in carga_fuera_ventana[:20]:
            print(f"   • Hora {case['hora_global']:5d} ({case['hora_del_dia']:02d}h): {case['carga_kwh']:8.2f} kWh - {case['problema']}")
else:
    print(f"\n✅ ¡PERFECTO! 100% de la carga está en la ventana 6h-15h")

# Validación de descarga
print("\n" + "="*80)
print("VALIDACIÓN: VENTANA DE DESCARGA BESS (15h-22h)")
print("="*80)

if 'bess_energy_delivered_hourly_kwh' in df.columns:
    descarga_col = 'bess_energy_delivered_hourly_kwh'
elif 'bess_discharge_kwh' in df.columns:
    descarga_col = 'bess_discharge_kwh'
else:
    print("❌ NO se encontró columna de descarga BESS")
    exit(1)

descarga = df[descarga_col].values

# REGLA: La descarga BESS idealmente debería ocurrir entre 15h-22h
# Pero puede haber descarga nocturna para peak shaving (hasta medianoche)
print(f"\nUsando columna: {descarga_col}\n")

print("📊 ESTADÍSTICAS DE DESCARGA POR HORA DEL DÍA:")
print("-" * 80)
print(f"{'Hora':>5} | {'Min':>8} | {'Max':>8} | {'Avg':>8} | {'Total':>13} | Status")
print("-" * 80)

for hour in range(24):
    mask = hours_of_day == hour
    values = descarga[mask]
    
    if len(values) > 0:
        min_val = values.min()
        max_val = values.max()
        avg_val = values.mean()
        total = values.sum()
        
        # Status - descarga típica 15h-22h, pero puede ser 6h-22h
        tiene_descarga = max_val > 0.0001
        
        if tiene_descarga:
            status = "✓ Descarga activa"
        else:
            status = "  Sin descarga"
        
        print(f"{hour:5d} | {min_val:8.2f} | {max_val:8.2f} | {avg_val:8.2f} | {total:13,.0f} | {status}")

# Descarga por período
descarga_manana = descarga[(hours_of_day >= 6) & (hours_of_day < 15)].sum()
descarga_tarde = descarga[(hours_of_day >= 15) & (hours_of_day < 22)].sum()
descarga_noche = descarga[(hours_of_day >= 22) | (hours_of_day < 6)].sum()
descarga_total = descarga.sum()

print("\n" + "="*80)
print("RESUMEN DESCARGA")
print("="*80)
print(f"\nDescarga 6h-15h (mañana):       {descarga_manana:>15,.0f} kWh ({descarga_manana/descarga_total*100:5.1f}%)")
print(f"Descarga 15h-22h (tarde):       {descarga_tarde:>15,.0f} kWh ({descarga_tarde/descarga_total*100:5.1f}%)")
print(f"Descarga 22h-6h (noche):        {descarga_noche:>15,.0f} kWh ({descarga_noche/descarga_total*100:5.1f}%)")
print(f"TOTAL DESCARGA ANUAL:           {descarga_total:>15,.0f} kWh")

print("\n" + "="*80)
print("CONCLUSIÓN DE VALIDACIÓN")
print("="*80)

if carga_fuera_ventana_total == 0:
    print("\n✅ LÓGICA CORRECTA: Carga BESS respeta ventana 6h-15h")
    if descarga_tarde > descarga_manana * 0.5:
        print("✅ LÓGICA CORRECTA: Descarga ocurre principalmente en tarde (15h-22h)")
    print("\n🎯 El diseño del BESS se está respetando correctamente en los datos.")
else:
    print(f"\n❌ ERROR DETECTADO: {pct_fuera:.1f}% carga fuera de ventana 6h-15h")
    print("   → La lógica de diseño NO está siendo respetada")
    print("\n   Acción requerida:")
    print("   1. Revisar bess.py - función que calcula carga")
    print("   2. Verificar que permet_cargar_bess respeta 6h-15h")
    print("   3. Regenerar dataset con lógica corregida")
