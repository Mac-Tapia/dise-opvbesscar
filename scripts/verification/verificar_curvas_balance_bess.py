"""
VERIFICACION: Curvas de BESS en Balance Energetico
Analiza si el comportamiento del SOC coincide con lo esperado:
- Carga a 100%
- Mantiene al 100%
- Desciende cuando hay deficit
- Llega a 20% al cierre (22h)
"""
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# Cargar balance energético
balance_csv = Path("reports/balance_energetico/balance_energetico_horario.csv")
if not balance_csv.exists():
    print(f"ERROR: No encontrado {balance_csv}")
    exit(1)

df = pd.read_csv(balance_csv)
print(f"\n[OK] Cargado balance: {len(df)} registros")
print(f"Columnas disponibles: {list(df.columns)}\n")

# Extraer columna SOC (buscar en diferentes nombres)
soc_col = None
for col in ['bess_soc_percent', 'soc_percent', 'SOC_%', 'soc_%']:
    if col in df.columns:
        soc_col = col
        break

if soc_col is None:
    print(f"ERROR: No se encontró columna SOC")
    print(f"Columnas: {list(df.columns)}")
    exit(1)

# Añadir hora del día
df['hour'] = df.index % 24

print("="*80)
print("ANALISIS DE CURVAS: COMPORTAMIENTO DEL BESS EN EL BALANCE")
print("="*80)

# Analizar 3 días representativos
test_days = [0, 100, 200]  # Enero, Abril, Julio

for day in test_days:
    start_idx = day * 24
    end_idx = (day + 1) * 24
    
    if end_idx > len(df):
        continue
    
    df_day = df.iloc[start_idx:end_idx].copy()
    
    soc_values = df_day[soc_col].values
    hours = df_day['hour'].values
    pv = df_day['pv_generation_kw'].values
    ev = df_day['ev_demand_kw'].values
    mall = df_day['mall_demand_kw'].values
    
    print(f"\n[DIA {day+1}] Curva esperada: Sube a 100% → Baja desde déficit")
    print("-" * 80)
    print(f"{'H':<3} {'PV':>6} {'EV':>6} {'MALL':>6} {'TOTAL':>6} {'SOC%':>6} {'ESTADO':<20}")
    print("-" * 80)
    
    for h in range(len(hours)):
        hour_val = int(hours[h])
        pv_val = pv[h]
        ev_val = ev[h]
        mall_val = mall[h]
        total_dem = ev_val + mall_val
        soc_val = soc_values[h]
        
        # Clasificar estado
        if soc_val >= 99:
            estado = "⚡ CARGADO 100%"
        elif h > 0 and soc_values[h] < soc_values[h-1]:
            estado = "🔋 DESCARGANDO"
        elif h > 0 and soc_values[h] > soc_values[h-1]:
            estado = "⬆️  CARGANDO"
        else:
            estado = "➡️  MANTENIENDO"
        
        print(f"{hour_val:<3} {pv_val:>6.0f} {ev_val:>6.0f} {mall_val:>6.0f} {total_dem:>6.0f} {soc_val:>6.1f} {estado:<20}")

# Crear gráfica comparativa: Primeros 3 días
print("\n" + "="*80)
print("GENERANDO GRAFICA: Primeros 3 días (72 horas)")
print("="*80)

fig, axes = plt.subplots(3, 1, figsize=(16, 10))
fig.suptitle('Análisis de Curvas BESS - Balance Energético\nVerificación SOC @ 100% → Baja', 
             fontsize=14, fontweight='bold')

# Seleccionar primeros 72 horas
df_3days = df.iloc[:72].copy()
hours_plot = df_3days.index.values

# Grafica 1: Generación y Demanda
ax1 = axes[0]
ax1.plot(hours_plot, df_3days['pv_generation_kw'], 'o-', label='PV Generación', linewidth=2, color='gold')
ax1.plot(hours_plot, df_3days['ev_demand_kw'], 's-', label='EV Demanda', linewidth=2, color='blue')
ax1.plot(hours_plot, df_3days['mall_demand_kw'], '^-', label='MALL Demanda', linewidth=2, color='red')
ax1.plot(hours_plot, df_3days['ev_demand_kw'] + df_3days['mall_demand_kw'], 'D-', 
         label='TOTAL Demanda', linewidth=2, color='darkred', alpha=0.6)
ax1.set_ylabel('Potencia (kW)', fontsize=11, fontweight='bold')
ax1.set_title('Generación PV vs Demandas (EV + MALL)', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left', fontsize=10)
ax1.set_xlim(0, 72)

# Grafica 2: SOC del BESS
ax2 = axes[1]
ax2.plot(hours_plot, df_3days[soc_col], 'o-', linewidth=3, markersize=6, color='darkgreen', label='SOC BESS')
ax2.axhline(y=100, color='green', linestyle='--', linewidth=2, label='100% (Máximo)')
ax2.axhline(y=20, color='red', linestyle='--', linewidth=2, label='20% (Mínimo)')
ax2.fill_between(hours_plot, 20, df_3days[soc_col], alpha=0.3, color='green', label='Rango Operacional')
ax2.set_ylabel('SOC (%)', fontsize=11, fontweight='bold')
ax2.set_title('Estado de Carga BESS - Esperado: Sube a 100%, baja desde déficit', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='lower left', fontsize=10)
ax2.set_ylim(0, 110)
ax2.set_xlim(0, 72)

# Grafica 3: Carga/Descarga BESS
ax3 = axes[2]
ax3.bar(hours_plot, df_3days['bess_charge_kw'], label='Carga BESS', color='green', alpha=0.6, width=0.9)
ax3.bar(hours_plot, -df_3days['bess_discharge_kw'], label='Descarga BESS', color='red', alpha=0.6, width=0.9)
ax3.axhline(y=0, color='black', linewidth=1)
ax3.set_xlabel('Hora del Año', fontsize=11, fontweight='bold')
ax3.set_ylabel('Energía (kWh)', fontsize=11, fontweight='bold')
ax3.set_title('Operación BESS - Carga (verde) y Descarga (rojo)', fontsize=12, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')
ax3.legend(loc='upper left', fontsize=10)
ax3.set_xlim(0, 72)

plt.tight_layout()
out_file = Path("reports/balance_energetico/verificacion_curvas_bess.png")
plt.savefig(out_file, dpi=150, bbox_inches='tight')
print(f"  [OK] Gráfica guardada: {out_file}")
plt.close()

# Análisis detallado del día 1
print("\n" + "="*80)
print("ANALISIS DETALLADO: DIA 1 (Primeras 24 horas)")
print("="*80)

df_day1 = df.iloc[0:24].copy()

# Punto 1: ¿Cuándo llega a 100%?
max_soc_hour = df_day1[soc_col].idxmax() % 24
max_soc_val = df_day1[soc_col].max()
print(f"\n1. CARGA A 100%:")
print(f"   Hora de máximo SOC: {int(max_soc_hour)}h")
print(f"   Valor máximo: {max_soc_val:.2f}%")

# Punto 2: ¿Cuándo empieza a bajar desde 100%?
soc_over_99 = (df_day1[soc_col] > 99.0)
if soc_over_99.any():
    first_100 = soc_over_99.idxmax() % 24
    last_100 = df_day1[soc_over_99]
    last_100_hour = last_100.index[-1] % 24 if len(last_100) > 0 else None
    print(f"\n2. MANTIENE EN 100%:")
    print(f"   Primera vez que llega: {int(first_100)}h")
    print(f"   Última vez al 100%: {int(last_100_hour)}h")
    print(f"   Horas mantenido: {int(last_100_hour) - int(first_100) + 1}h") if last_100_hour else print(f"   N/A")

# Punto 3: ¿Cuándo empieza a bajar (descarga)?
discharge_starts = None
for h in range(1, len(df_day1)):
    if df_day1[soc_col].iloc[h] < df_day1[soc_col].iloc[h-1]:
        discharge_starts = h % 24
        break

if discharge_starts:
    print(f"\n3. COMIENZA DESCARGA:")
    print(f"   Hora de inicio: {int(discharge_starts)}h")
    print(f"   Motivo: Demanda > Generación PV")
else:
    print(f"\n3. SIN DESCARGA EN EL DIA 1")

# Punto 4: SOC a las 22h
closing_hour = 22
idx_closing = closing_hour
if idx_closing < len(df_day1):
    soc_closing = df_day1[soc_col].iloc[idx_closing]
    print(f"\n4. CIERRE (22h):")
    print(f"   SOC a las 22h: {soc_closing:.2f}%")
    print(f"   Distancia a 20%: {soc_closing - 20:.2f}%")

# Punto 5: Correlación PV-SOC
print(f"\n5. CORRELACION PV vs SOC:")
corr = df_day1['pv_generation_kw'].corr(df_day1[soc_col])
print(f"   Correlación: {corr:.4f} (Esperado: >0.7 = suben juntos)")

# Verificación final
print("\n" + "="*80)
print("VERIFICACION: ¿Concuerdan las curvas con lo esperado?")
print("="*80)

checks = []

# Check 1: ¿Llega a 100%?
if max_soc_val >= 99:
    checks.append(("✅", "SOC llega a 100%", f"{max_soc_val:.2f}%"))
else:
    checks.append(("❌", "SOC NO llega a 100%", f"{max_soc_val:.2f}%"))

# Check 2: ¿Mantiene el 100%?
if soc_over_99.sum() >= 2:
    checks.append(("✅", "SOC se mantiene en 100%", f"{soc_over_99.sum()} horas"))
else:
    checks.append(("⚠️", "SOC poco tiempo en 100%", f"{soc_over_99.sum()} horas"))

# Check 3: ¿Desciende después?
if discharge_starts:
    checks.append(("✅", "BESS descarga cuando hay deficit", f"A partir de {int(discharge_starts)}h"))
else:
    checks.append(("⚠️", "Sin descarga significativa", "Posible sobredimensión"))

# Check 4: ¿Cierra en rango esperado?
if 50 < soc_closing < 80:
    checks.append(("✅", "SOC de cierre en rango esperado", f"{soc_closing:.2f}%"))
elif soc_closing < 20:
    checks.append(("❌", "SOC de cierre BAJO (< 20%)", f"{soc_closing:.2f}%"))
else:
    checks.append(("⚠️", "SOC de cierre alto (> 80%)", f"{soc_closing:.2f}%"))

for symbol, check, value in checks:
    print(f"  {symbol} {check:<40} {value:>15}")

print("\n" + "="*80)
