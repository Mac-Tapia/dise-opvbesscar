"""Regenerar gráfica de barras con verificación."""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json

df = pd.read_csv(
    'd:/diseñopvbesscar/data/interim/oe2/solar/pv_generation_timeseries.csv',
    parse_dates=['timestamp'],
    index_col='timestamp'
)

with open('d:/diseñopvbesscar/data/interim/oe2/solar/solar_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

date_str = results['despejado_date']
date = pd.to_datetime(date_str)
day_data = df[pd.to_datetime(df.index).date == date.date()].copy()
day_data = day_data[day_data['ac_energy_kwh'] > 0]

print(f"Fecha: {date_str}")
print(f"Registros con generación: {len(day_data)}")
print(f"Primer registro: {day_data.index[0]}")
print(f"Último registro: {day_data.index[-1]}")

fig, ax1 = plt.subplots(figsize=(14, 6))

times = day_data.index
widths = 0.01
ax1.bar(times, day_data['ac_energy_kwh'], width=widths, color='gold',
        edgecolor='orange', alpha=0.8, label='Energía 15 min (kWh)')
ax1.set_ylabel('Energía 15 min (kWh)', fontsize=11, color='darkorange')

ax2 = ax1.twinx()
ax2.plot(times, day_data['ac_power_kw'], 'b-', linewidth=2, label='Potencia AC (kW)')
ax2.set_ylabel('Potencia AC (kW)', fontsize=11, color='blue')

total_energy = day_data['ac_energy_kwh'].sum()
max_power = day_data['ac_power_kw'].max()
hours_gen = len(day_data) * 0.25
peak_hour = day_data['ac_power_kw'].idxmax()
peak_str = peak_hour.strftime('%H:%M')

print(f"Hora pico: {peak_str}")
print(f"Potencia máxima: {max_power:.0f} kW")
print(f"Energía total: {total_energy:.0f} kWh")

ax2.annotate(f'Horas de generación: {hours_gen:.1f} h\nHora pico: {peak_str}',
             xy=(0.98, 0.95), xycoords='axes fraction', ha='right', va='top',
             fontsize=9, bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange'))

# Formato del eje X - usar DateFormatter con %H:%M
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax1.xaxis.set_major_locator(mdates.HourLocator(interval=1))
plt.xticks(rotation=45)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)
ax1.grid(True, alpha=0.3, axis='y')

plt.title(f'Día Despejado Representativo - {date_str}\n'
          f'Energía total: {total_energy:.0f} kWh | Potencia máxima: {max_power:.0f} kW',
          fontsize=12, fontweight='bold')

plt.tight_layout()
out_path = 'd:/diseñopvbesscar/reports/oe2/solar_plots/solar_dia_despejado_barras.png'
plt.savefig(out_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"\n✅ Gráfica regenerada: {out_path}")
print(f"Rango horario mostrado: {times[0].strftime('%H:%M')} a {times[-1].strftime('%H:%M')}")
