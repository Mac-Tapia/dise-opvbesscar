"""
Módulo de visualización avanzada para el sistema fotovoltaico.
Genera gráficas de calidad para tesis/reportes técnicos.

Gráficas incluidas:
1. Energía y Potencia Máxima Diaria anual
2. Perfil de día representativo (despejado/intermedio/nublado)
3. Resumen del sistema FV (4 paneles)
4. Relación POA vs Potencia AC
5. Comparación de escenarios
6. Análisis temporal avanzado (mapa de calor, boxplots, PR mensual)
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.cm as cm  # type: ignore[import-untyped]
from matplotlib.gridspec import GridSpec
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING
import json
from scipy import stats

# Configuración global de matplotlib para español
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False


def _get_decimal_hours(df: pd.DataFrame) -> np.ndarray:
    """Extrae horas decimales del índice de un DataFrame."""
    idx_dt = pd.to_datetime(df.index)
    return np.asarray(idx_dt.hour + idx_dt.minute / 60)  # type: ignore[union-attr]


def _get_values(series: pd.Series) -> np.ndarray:  # type: ignore[type-arg]
    """Extrae valores como numpy array."""
    return np.asarray(series.values)


def load_solar_data(data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Carga todos los datos solares necesarios."""
    # Serie temporal
    ts_path = data_dir / "pv_generation_timeseries.csv"
    df = pd.read_csv(ts_path, parse_dates=['timestamp'], index_col='timestamp')
    
    # Energía mensual
    monthly_path = data_dir / "pv_monthly_energy.csv"
    monthly = pd.read_csv(monthly_path, parse_dates=['timestamp'], index_col='timestamp')
    
    # Resultados JSON
    json_path = data_dir / "solar_results.json"
    with open(json_path, 'r') as f:
        results = json.load(f)
    
    return df, monthly, results


def plot_energia_potencia_diaria(df: pd.DataFrame, results: Dict, out_dir: Path) -> None:
    """
    Gráfica 1: Energía y Potencia Máxima Diaria del Sistema FV
    Doble eje Y con barras de energía y línea de potencia máxima.
    """
    fig, ax1 = plt.subplots(figsize=(14, 6))
    
    # Calcular datos diarios
    daily_energy = df['ac_energy_kwh'].resample('D').sum() / 1000  # MWh
    daily_pmax = df['ac_power_kw'].resample('D').max()
    
    # Estadísticas
    energy_mean = daily_energy.mean()
    pmax_mean = daily_pmax.mean()
    pmax_absolute = daily_pmax.max()
    pmax_date = pd.Timestamp(daily_pmax.idxmax())  # type: ignore[arg-type]
    
    # Eje izquierdo: Energía diaria (barras)
    ax1.fill_between(daily_energy.index, np.asarray(daily_energy.values), alpha=0.6, 
                     color='lightblue', label=f'Energía diaria (MWh)')
    ax1.axhline(y=energy_mean, color='blue', linestyle='--', linewidth=1.5,
                label=f'Promedio: {energy_mean:.2f} MWh')
    ax1.set_xlabel('Fecha', fontsize=11)
    ax1.set_ylabel('Energía diaria (MWh)', fontsize=11, color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.set_ylim(0, daily_energy.max() * 1.1)
    
    # Eje derecho: Potencia máxima diaria (línea)
    ax2 = ax1.twinx()
    ax2.plot(daily_pmax.index, np.asarray(daily_pmax.values), 'r-', linewidth=0.8, 
             label='Potencia máxima diaria (kW)')
    ax2.axhline(y=pmax_mean, color='darkred', linestyle='--', linewidth=1.5,
                label=f'Pmax promedio: {pmax_mean:.0f} kW')
    ax2.set_ylabel('Potencia máxima diaria (kW)', fontsize=11, color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    ax2.set_ylim(0, pmax_absolute * 1.15)
    
    # Anotación del máximo absoluto - usar pmax_date como objeto Timestamp
    pmax_date_num = float(mdates.date2num(pmax_date))
    ax2.annotate(f'Pmax absoluta: {pmax_absolute:.1f} kW\nFecha: {pmax_date.strftime("%d/%m/%Y")}',
                 xy=(pmax_date_num, float(pmax_absolute)), xytext=(pmax_date_num, float(pmax_absolute) * 1.05),
                 fontsize=9, ha='center',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', edgecolor='orange'))
    
    # Formato de fechas
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    
    # Título y leyendas
    year = df.index[0].year
    plt.title(f'Energía y Potencia Máxima Diaria del Sistema FV ({year})', fontsize=13, fontweight='bold')
    
    # Combinar leyendas
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)
    
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / 'solar_energia_potencia_diaria.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Grafica: Energia y Potencia Maxima Diaria")


def plot_dia_representativo(df: pd.DataFrame, date_str: str, day_type: str, 
                            results: Dict, out_dir: Path) -> None:
    """
    Gráfica 2: Perfil de Potencia, Energía (15 min) y POA - Día representativo
    Con energía acumulada en panel inferior.
    """
    date = pd.to_datetime(date_str)
    # Filtrar por fecha usando pd.to_datetime para el índice
    day_data = df[pd.to_datetime(df.index).date == date.date()].copy()  # type: ignore[union-attr]
    
    if len(day_data) == 0:
        print(f"  ⚠ No hay datos para {date_str}")
        return
    
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 1, height_ratios=[2, 1], hspace=0.15)
    
    # Panel superior: Potencia, Energía 15 min y POA
    ax1 = fig.add_subplot(gs[0])
    
    # Calcular horas decimales
    idx_dt = pd.to_datetime(day_data.index)
    hours = np.asarray(idx_dt.hour + idx_dt.minute / 60)  # type: ignore[union-attr]
    
    # Potencia AC
    ax1.plot(hours, day_data['ac_power_kw'], 'b-', linewidth=2, label='Potencia (kW)')
    
    # Energía 15 min (línea discontinua naranja)
    ax1.plot(hours, day_data['ac_energy_kwh'], '--', color='orange', linewidth=1.5, 
             label='Energía 15 min (kWh)')
    
    ax1.set_ylabel('Potencia (kW)', fontsize=11, color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.set_ylim(0, day_data['ac_power_kw'].max() * 1.15)
    
    # Eje derecho: POA
    ax1_r = ax1.twinx()
    # Calcular POA aproximado (GHI * cos(incidencia) ≈ GHI para tilt pequeño)
    poa = day_data['ghi_wm2'].values  # Simplificación
    ax1_r.plot(hours, poa, 'r-', linewidth=1.5, label='POA (W/m²)')
    ax1_r.set_ylabel('POA (W/m²)', fontsize=11, color='red')
    ax1_r.tick_params(axis='y', labelcolor='red')
    ax1_r.set_ylim(0, max(poa) * 1.1 if max(poa) > 0 else 100)
    
    # Combinar leyendas
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_r.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)
    
    ax1.set_xlim(0, 24)
    ax1.grid(True, alpha=0.3)
    
    # Panel inferior: Energía acumulada
    ax2 = fig.add_subplot(gs[1])
    energy_cumsum = day_data['ac_energy_kwh'].cumsum()
    ax2.fill_between(hours, energy_cumsum, alpha=0.5, color='purple')
    ax2.plot(hours, energy_cumsum, 'purple', linewidth=2, label='Energía acumulada (kWh)')
    ax2.set_xlabel('Hora del día', fontsize=11)
    ax2.set_ylabel('Energía acumulada (kWh)', fontsize=11)
    ax2.set_xlim(0, 24)
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # Título
    type_names = {'despejado': 'Despejado', 'intermedio': 'Intermedio', 'nublado': 'Nublado'}
    plt.suptitle(f'Perfil de Potencia, Energía (15 min) y POA - Día {type_names.get(day_type, day_type)} ({date_str})',
                 fontsize=13, fontweight='bold')
    
    plt.savefig(out_dir / f'solar_dia_{day_type}.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Grafica: Dia {type_names.get(day_type, day_type)} ({date_str})")


def plot_dia_barras(df: pd.DataFrame, date_str: str, day_type: str,
                    results: Dict, out_dir: Path) -> None:
    """
    Gráfica 3: Día Representativo con barras de energía 15 min
    """
    date = pd.to_datetime(date_str)
    day_data = df[pd.to_datetime(df.index).date == date.date()].copy()  # type: ignore[union-attr]
    
    if len(day_data) == 0:
        return
    
    # Filtrar solo horas con generación
    day_data = day_data[day_data['ac_energy_kwh'] > 0]
    
    if len(day_data) == 0:
        return
    
    fig, ax1 = plt.subplots(figsize=(14, 6))
    
    # Barras de energía 15 min
    times = day_data.index
    widths = 0.01  # Ancho de barras
    ax1.bar(times, day_data['ac_energy_kwh'], width=widths, color='gold', 
            edgecolor='orange', alpha=0.8, label='Energía 15 min (kWh)')
    
    ax1.set_ylabel('Energía 15 min (kWh)', fontsize=11, color='darkorange')
    ax1.tick_params(axis='y', labelcolor='darkorange')
    
    # Eje derecho: Potencia AC
    ax2 = ax1.twinx()
    ax2.plot(times, day_data['ac_power_kw'], 'b-', linewidth=2, label='Potencia AC (kW)')
    ax2.set_ylabel('Potencia AC (kW)', fontsize=11, color='blue')
    ax2.tick_params(axis='y', labelcolor='blue')
    
    # Estadísticas
    total_energy = day_data['ac_energy_kwh'].sum()
    max_power = day_data['ac_power_kw'].max()
    hours_gen = len(day_data) * 0.25  # intervalos de 15 min
    peak_hour = day_data['ac_power_kw'].idxmax()
    
    # Anotación
    ax2.annotate(f'Horas de generación: {hours_gen:.1f} h\nHora pico: {peak_hour.strftime("%H:%M")}',
                 xy=(0.98, 0.95), xycoords='axes fraction', ha='right', va='top',
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange'))
    
    # Formato
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.xticks(rotation=45)
    
    # Combinar leyendas
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)
    
    ax1.grid(True, alpha=0.3, axis='y')
    
    type_names = {'despejado': 'Despejado', 'intermedio': 'Intermedio', 'nublado': 'Nublado'}
    plt.title(f'Día {type_names.get(day_type, day_type)} Representativo - {date_str}\n'
              f'Energía total: {total_energy:.0f} kWh | Potencia máxima: {max_power:.0f} kW',
              fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(out_dir / f'solar_dia_{day_type}_barras.png', dpi=150, bbox_inches='tight')
    plt.close()


def plot_resumen_sistema(df: pd.DataFrame, monthly: pd.DataFrame, 
                         results: Dict, out_dir: Path) -> None:
    """
    Gráfica 4: Sistema FV Iquitos - Resumen (4 paneles)
    - Energía diaria (serie temporal)
    - Energía mensual (barras)
    - Distribución de energía diaria (histograma)
    - Distribución de energía por hora del día
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    year = df.index[0].year
    
    daily_energy = df['ac_energy_kwh'].resample('D').sum() / 1000  # MWh
    
    # Panel 1: Energía diaria
    ax1 = axes[0, 0]
    ax1.plot(daily_energy.index, daily_energy.values, 'steelblue', linewidth=0.8)
    mean_daily = daily_energy.mean()
    ax1.axhline(y=mean_daily, color='gray', linestyle='--', linewidth=1.5,
                label=f'Promedio: {mean_daily:.2f} MWh')
    ax1.set_ylabel('MWh/día', fontsize=10)
    ax1.set_xlabel('Fecha', fontsize=10)
    ax1.set_title('Energía diaria', fontsize=11, fontweight='bold')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # Anotación
    total_annual = daily_energy.sum()
    ax1.annotate(f'Total anual: {total_annual:.1f} MWh\nDías: {len(daily_energy)}',
                 xy=(0.02, 0.98), xycoords='axes fraction', ha='left', va='top',
                 fontsize=8, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Panel 2: Energía mensual
    ax2 = axes[0, 1]
    months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    monthly_mwh = np.asarray(monthly['ac_energy_kwh'].values) / 1000
    colors = cm.Blues(np.linspace(0.4, 0.9, 12))  # type: ignore[attr-defined]
    bars = ax2.bar(months, monthly_mwh, color=colors, edgecolor='darkblue', alpha=0.8)
    mean_monthly = float(monthly_mwh.mean())
    ax2.axhline(y=mean_monthly, color='gray', linestyle='--', linewidth=1.5,
                label=f'Promedio: {mean_monthly:.1f} MWh')
    ax2.set_ylabel('MWh/mes', fontsize=10)
    ax2.set_xlabel('Mes', fontsize=10)
    ax2.set_title('Energía mensual', fontsize=11, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=8)
    
    # Etiquetas en barras
    for bar, val in zip(bars, monthly_mwh):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                 f'{val:.1f}', ha='center', va='bottom', fontsize=7)
    
    # Panel 3: Distribución de energía diaria
    ax3 = axes[1, 0]
    daily_kwh = daily_energy * 1000  # volver a kWh
    ax3.hist(daily_kwh, bins=30, color='steelblue', edgecolor='white', alpha=0.7)
    mean_kwh = daily_kwh.mean()
    median_kwh = daily_kwh.median()
    ax3.axvline(x=mean_kwh, color='blue', linestyle='--', linewidth=1.5,
                label=f'Media: {mean_kwh:.0f} kWh')
    ax3.axvline(x=median_kwh, color='cyan', linestyle='--', linewidth=1.5,
                label=f'Mediana: {median_kwh:.0f} kWh')
    ax3.set_xlabel('Energía diaria (kWh)', fontsize=10)
    ax3.set_ylabel('Frecuencia (días)', fontsize=10)
    ax3.set_title('Distribución de energía diaria', fontsize=11, fontweight='bold')
    ax3.legend(loc='upper right', fontsize=8)
    
    # Panel 4: Distribución de energía por hora del día
    ax4 = axes[1, 1]
    hourly_energy = df.groupby(pd.to_datetime(df.index).hour)['ac_energy_kwh'].sum()  # type: ignore[union-attr]
    bars4 = ax4.bar(hourly_energy.index, np.asarray(hourly_energy.values), color='steelblue', 
                    edgecolor='darkblue', alpha=0.8)
    
    # Encontrar hora pico
    peak_hour = hourly_energy.idxmax()
    peak_energy = hourly_energy.max()
    total_energy = hourly_energy.sum()
    
    ax4.axhline(y=hourly_energy.mean(), color='gray', linestyle='--', linewidth=1.5)
    ax4.set_xlabel('Hora del día', fontsize=10)
    ax4.set_ylabel('Energía anual total (kWh)', fontsize=10)
    ax4.set_title('Distribución de energía por hora del día', fontsize=11, fontweight='bold')
    ax4.set_xticks(range(0, 24, 2))
    ax4.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)], fontsize=8)
    
    # Anotación hora pico
    ax4.annotate(f'Hora pico: {peak_hour}:00\nEnergía: {peak_energy:.0f} kWh\n({peak_energy/total_energy*100:.1f}% del total)',
                 xy=(0.98, 0.95), xycoords='axes fraction', ha='right', va='top',
                 fontsize=8, bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange'))
    
    plt.suptitle(f'Sistema FV Iquitos - Resumen {year}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(out_dir / 'solar_resumen_sistema.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Grafica: Resumen del Sistema FV")


def plot_poa_vs_potencia(df: pd.DataFrame, results: Dict, out_dir: Path) -> None:
    """
    Gráfica 5: Relación POA vs Potencia AC
    Scatter plot con línea de tendencia y correlación.
    """
    # Filtrar datos con producción
    mask = df['ac_power_kw'] > 0
    poa = np.asarray(df.loc[mask, 'ghi_wm2'].values)  # Usar GHI como proxy de POA
    power = np.asarray(df.loc[mask, 'ac_power_kw'].values)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Scatter plot con color por potencia
    scatter = ax.scatter(poa, power, c=power, cmap='viridis', alpha=0.5, s=5)
    plt.colorbar(scatter, ax=ax, label='Potencia AC (kW)')
    
    # Línea de tendencia
    linreg_result = stats.linregress(poa, power)
    slope_val = float(linreg_result[0])  # type: ignore[arg-type]
    intercept_val = float(linreg_result[1])  # type: ignore[arg-type]
    x_line = np.linspace(0, float(poa.max()) * 1.1, 100)
    y_line = slope_val * x_line + intercept_val
    ax.plot(x_line, y_line, 'b--', linewidth=2, 
            label=f'Tendencia: P = {slope_val:.3f}·POA + {intercept_val:.1f}')
    
    # Estadísticas
    correlation = float(np.corrcoef(poa, power)[0, 1])
    pmax = float(power.max())
    poa_at_pmax_idx = int(np.argmax(power))
    poa_at_pmax = float(poa[poa_at_pmax_idx])
    
    ax.set_xlabel('POA - Irradiancia en plano del arreglo (W/m²)', fontsize=11)
    ax.set_ylabel('Potencia AC total (kW)', fontsize=11)
    ax.set_title('Relación POA vs Potencia AC - 2024', fontsize=13, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9)
    
    # Anotación de estadísticas
    stats_text = f'Correlación: {correlation:.3f}\nPmax: {pmax:.1f} kW\nPOA en Pmax: {poa_at_pmax:.0f} W/m²\nPuntos: {len(poa):,}'
    ax.annotate(stats_text, xy=(0.98, 0.25), xycoords='axes fraction', ha='right', va='top',
                fontsize=9, bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='gray'))
    
    ax.set_xlim(0, float(poa.max()) * 1.1)
    ax.set_ylim(0, pmax * 1.15)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(out_dir / 'solar_poa_vs_potencia.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Grafica: Relacion POA vs Potencia AC")


def plot_comparacion_escenarios(df: pd.DataFrame, results: Dict, out_dir: Path) -> None:
    """
    Gráfica 6: Comparación de Escenarios - Sistema FV
    Compara días despejado, intermedio, nublado y máxima energía.
    """
    # Obtener fechas de días representativos
    despejado_date = results.get('despejado_date', '')
    intermedio_date = results.get('intermedio_date', '')
    nublado_date = results.get('nublado_date', '')
    max_energy_date = results.get('max_daily_energy_date', '')
    
    if not despejado_date:
        print("  ⚠ No hay datos de días representativos")
        return
    
    # Extraer datos de cada día
    def get_day_data(date_str: str) -> pd.DataFrame:
        date = pd.to_datetime(date_str)
        return df[pd.to_datetime(df.index).date == date.date()].copy()  # type: ignore[union-attr]
    
    days = {
        'Despejado': get_day_data(despejado_date),
        'Intermedio': get_day_data(intermedio_date),
        'Nublado': get_day_data(nublado_date),
    }
    
    # Verificar datos
    for name, data in days.items():
        if len(data) == 0:
            print(f"  ⚠ Sin datos para día {name}")
            return
    
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    colors = {'Despejado': 'orange', 'Intermedio': 'green', 'Nublado': 'gray'}
    
    # Panel 1: Potencia por escenario
    ax1 = fig.add_subplot(gs[0, 0])
    for name, data in days.items():
        dt_idx = pd.to_datetime(data.index)
        hours = np.asarray((dt_idx.hour + dt_idx.minute / 60).values)
        ax1.plot(hours, np.asarray(data['ac_power_kw'].values), '-', color=colors[name], 
                 linewidth=1.5, label=f'{name} ({results.get(f"{name.lower()}_date", "")})')
    ax1.set_xlabel('Hora del día')
    ax1.set_ylabel('Potencia AC (kW)')
    ax1.set_title('POTENCIA POR ESCENARIO', fontsize=10, fontweight='bold')
    ax1.legend(fontsize=7)
    ax1.set_xlim(6, 18)
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Energía acumulada
    ax2 = fig.add_subplot(gs[0, 1])
    for name, data in days.items():
        dt_idx = pd.to_datetime(data.index)
        hours = np.asarray((dt_idx.hour + dt_idx.minute / 60).values)
        cumsum = np.asarray(data['ac_energy_kwh'].cumsum().values)
        ax2.plot(hours, cumsum, '-', color=colors[name], linewidth=1.5, label=name)
        # Anotación del total
        if len(hours) > 0 and len(cumsum) > 0:
            ax2.annotate(f'{cumsum[-1]:.0f}', xy=(hours[-1], cumsum[-1]),
                         fontsize=8, color=colors[name])
    ax2.set_xlabel('Hora del día')
    ax2.set_ylabel('Energía acumulada (kWh)')
    ax2.set_title('ENERGÍA ACUMULADA - ESCENARIOS', fontsize=10, fontweight='bold')
    ax2.legend(fontsize=7)
    ax2.set_xlim(6, 18)
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: Irradiancia POA
    ax3 = fig.add_subplot(gs[0, 2])
    for name, data in days.items():
        dt_idx = pd.to_datetime(data.index)
        hours = np.asarray((dt_idx.hour + dt_idx.minute / 60).values)
        ax3.plot(hours, np.asarray(data['ghi_wm2'].values), '-', color=colors[name], linewidth=1.5, label=name)
    ax3.set_xlabel('Hora del día')
    ax3.set_ylabel('POA (W/m²)')
    ax3.set_title('IRRADIANCIA POA POR ESCENARIO', fontsize=10, fontweight='bold')
    ax3.legend(fontsize=7)
    ax3.set_xlim(6, 18)
    ax3.grid(True, alpha=0.3)
    
    # Panel 4: Máx energía vs Máx potencia
    ax4 = fig.add_subplot(gs[1, 0])
    # Día de máxima energía
    max_e_data = get_day_data(max_energy_date)
    # Día de máxima potencia
    max_p_date = results.get('max_power_timestamp', '')[:10]
    max_p_data = get_day_data(max_p_date)
    
    if len(max_e_data) > 0:
        dt_idx = pd.to_datetime(max_e_data.index)
        hours = np.asarray((dt_idx.hour + dt_idx.minute / 60).values)
        ax4.plot(hours, np.asarray(max_e_data['ac_power_kw'].values), 'g-', linewidth=1.5, 
                 label=f'Máx Energía ({max_energy_date})')
    if len(max_p_data) > 0:
        dt_idx = pd.to_datetime(max_p_data.index)
        hours = np.asarray((dt_idx.hour + dt_idx.minute / 60).values)
        ax4.plot(hours, np.asarray(max_p_data['ac_power_kw'].values), 'r-', linewidth=1.5,
                 label=f'Máx Potencia ({max_p_date})')
    ax4.set_xlabel('Hora del día')
    ax4.set_ylabel('Potencia AC (kW)')
    ax4.set_title('MÁX ENERGÍA vs MÁX POTENCIA', fontsize=10, fontweight='bold')
    ax4.legend(fontsize=7)
    ax4.set_xlim(6, 18)
    ax4.grid(True, alpha=0.3)
    
    # Panel 5: Comparación de energía diaria (barras)
    ax5 = fig.add_subplot(gs[1, 1])
    daily_energy = df['ac_energy_kwh'].resample('D').sum()
    energies = [
        results.get('despejado_energy_kwh', 0),
        results.get('intermedio_energy_kwh', 0),
        results.get('nublado_energy_kwh', 0),
        daily_energy.mean(),
        daily_energy.max()
    ]
    labels = ['Despejado', 'Intermedio', 'Nublado', 'Promedio', 'Máx Energía']
    bar_colors = ['orange', 'green', 'gray', 'steelblue', 'lightblue']
    bars = ax5.bar(labels, energies, color=bar_colors, edgecolor='black')
    
    for bar, val in zip(bars, energies):
        ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 200,
                 f'{val:.0f}', ha='center', fontsize=8, fontweight='bold')
    
    ax5.set_ylabel('Energía diaria (kWh)')
    ax5.set_title('ENERGÍA DIARIA - COMPARACIÓN', fontsize=10, fontweight='bold')
    plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Panel 6: Tabla comparativa
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis('off')
    
    # Calcular datos para tabla
    table_data = []
    for name, data in days.items():
        energy = data['ac_energy_kwh'].sum()
        pmax = data['ac_power_kw'].max()
        poa_total = data['ghi_wm2'].sum() / 4 / 1000  # kWh/m²
        hours_gen = (data['ac_power_kw'] > 0).sum() * 0.25
        table_data.append([name, f'{energy:.0f}', f'{pmax:.0f}', f'{poa_total:.1f}', f'{hours_gen:.1f}'])
    
    table_data.append(['Promedio', f'{daily_energy.mean():.0f}', '0', '0.0', '0.0'])
    table_data.append(['Máx Energía', f'{daily_energy.max():.0f}', '0', '0.0', '0.0'])
    
    table = ax6.table(cellText=table_data,
                      colLabels=['Escenario', 'Energía\n(kWh)', 'Pot. Máx\n(kW)', 'POA\n(kWh/m²)', 'Horas\nGen.'],
                      cellLoc='center',
                      loc='center',
                      colWidths=[0.25, 0.18, 0.18, 0.18, 0.18])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    
    # Colorear header
    for i in range(5):
        table[(0, i)].set_facecolor('steelblue')
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    
    ax6.set_title('TABLA COMPARATIVA DE ESCENARIOS', fontsize=10, fontweight='bold', y=0.95)
    
    year = df.index[0].year
    plt.suptitle(f'Comparación de Escenarios - Sistema FV Iquitos {year}', fontsize=14, fontweight='bold')
    
    plt.savefig(out_dir / 'solar_comparacion_escenarios.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Grafica: Comparacion de Escenarios")


def plot_analisis_temporal_avanzado(df: pd.DataFrame, monthly: pd.DataFrame,
                                     results: Dict, out_dir: Path) -> None:
    """
    Gráfica 7: Análisis Temporal Avanzado
    - Mapa de calor mes x hora
    - Box plots mensuales
    - Producción por trimestre
    - Variabilidad de producción diaria
    - Distribución de energía diaria con percentiles
    - Performance Ratio mensual
    """
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    year = df.index[0].year
    
    # Preparar datos - crear columnas temporales
    df = df.copy()  # Evitar modificar el original
    df['hour'] = pd.to_datetime(df.index).hour  # type: ignore[union-attr]
    df['month'] = pd.to_datetime(df.index).month  # type: ignore[union-attr]
    daily_energy = df['ac_energy_kwh'].resample('D').sum()
    
    # Panel 1: Mapa de calor (mes x hora)
    ax1 = fig.add_subplot(gs[0, 0])
    heatmap_data = df.pivot_table(values='ac_power_kw', index='hour', columns='month', aggfunc='mean')
    im = ax1.imshow(heatmap_data.values, aspect='auto', cmap='YlOrRd', origin='lower')
    ax1.set_yticks(range(0, 24, 2))
    ax1.set_yticklabels([str(h) for h in range(0, 24, 2)])
    ax1.set_xticks(range(12))
    ax1.set_xticklabels(['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 
                         'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'], fontsize=8)
    ax1.set_ylabel('Hora del día')
    ax1.set_xlabel('Mes')
    ax1.set_title('MAPA DE CALOR - POTENCIA PROMEDIO', fontsize=10, fontweight='bold')
    cbar = plt.colorbar(im, ax=ax1)
    cbar.set_label('kW')
    
    # Panel 2: Box plots de energía diaria por mes
    ax2 = fig.add_subplot(gs[0, 1])
    daily_energy_df = daily_energy.to_frame()
    daily_energy_df['month'] = pd.to_datetime(daily_energy_df.index).month  # type: ignore[union-attr]
    daily_by_month = [np.asarray(daily_energy_df[daily_energy_df['month'] == m]['ac_energy_kwh'].values) for m in range(1, 13)]
    bp = ax2.boxplot(daily_by_month, patch_artist=True)
    colors_box = cm.viridis(np.linspace(0.2, 0.8, 12))  # type: ignore[attr-defined]
    for patch, color in zip(bp['boxes'], colors_box):
        patch.set_facecolor(color)
    ax2.set_xticklabels(['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                         'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'], fontsize=8)
    ax2.set_ylabel('Energía diaria (kWh)')
    ax2.set_xlabel('Mes')
    ax2.set_title('DISTRIBUCIÓN MENSUAL DE ENERGÍA DIARIA', fontsize=10, fontweight='bold')
    
    # Panel 3: Producción por trimestre
    ax3 = fig.add_subplot(gs[0, 2])
    quarterly = daily_energy.resample('QE').sum() / 1000  # MWh
    quarters = ['Q1\n(Ene-Mar)', 'Q2\n(Abr-Jun)', 'Q3\n(Jul-Sep)', 'Q4\n(Oct-Dic)']
    colors_q = ['#ff9999', '#99ff99', '#9999ff', '#ffcc99']
    quarterly_vals = np.asarray(quarterly.values)
    bars = ax3.bar(quarters, quarterly_vals, color=colors_q, edgecolor='black')
    for bar, val in zip(bars, quarterly_vals):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                 f'{val:.1f}', ha='center', fontsize=9, fontweight='bold')
    ax3.set_ylabel('Energía (MWh)')
    ax3.set_title('PRODUCCIÓN POR TRIMESTRE', fontsize=10, fontweight='bold')
    
    # Panel 4: Variabilidad de producción diaria
    ax4 = fig.add_subplot(gs[1, 0])
    mean_val = daily_energy.mean()
    std_val = daily_energy.std()
    
    ax4.fill_between(daily_energy.index, mean_val - std_val, mean_val + std_val,
                     alpha=0.3, color='blue', label=f'±1σ ({std_val:.0f} kWh)')
    ax4.plot(daily_energy.index, np.asarray(daily_energy.values), 'b-', linewidth=0.5, label='Energía diaria')
    ax4.axhline(y=mean_val, color='red', linestyle='--', linewidth=1.5, label=f'Promedio')
    
    ax4.set_ylabel('Energía (kWh)')
    ax4.set_xlabel('Fecha')
    ax4.set_title('VARIABILIDAD DE PRODUCCIÓN DIARIA', fontsize=10, fontweight='bold')
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax4.xaxis.set_major_locator(mdates.MonthLocator())
    ax4.legend(fontsize=7, loc='lower left')
    
    # Anotación CV
    cv = std_val / mean_val * 100
    ax4.annotate(f'CV = {cv:.1f}%\nMin = {daily_energy.min():.0f} kWh\nMax = {daily_energy.max():.0f} kWh',
                 xy=(0.98, 0.05), xycoords='axes fraction', ha='right', va='bottom',
                 fontsize=8, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Panel 5: Distribución con percentiles
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.hist(daily_energy, bins=30, color='steelblue', edgecolor='white', alpha=0.7)
    
    p25 = np.percentile(daily_energy, 25)
    p75 = np.percentile(daily_energy, 75)
    median = daily_energy.median()
    
    ax5.axvline(x=mean_val, color='blue', linestyle='--', linewidth=1.5, label=f'Media: {mean_val:.0f} kWh')
    ax5.axvline(x=median, color='red', linestyle='--', linewidth=1.5, label=f'Mediana: {median:.0f} kWh')
    ax5.axvline(x=p25, color='green', linestyle=':', linewidth=1.5, label=f'P25: {p25:.0f} kWh')
    ax5.axvline(x=p75, color='green', linestyle=':', linewidth=1.5, label=f'P75: {p75:.0f} kWh')
    
    ax5.set_xlabel('Energía diaria (kWh)')
    ax5.set_ylabel('Frecuencia (días)')
    ax5.set_title('DISTRIBUCIÓN DE ENERGÍA DIARIA', fontsize=10, fontweight='bold')
    ax5.legend(fontsize=7)
    
    # Anotación
    n_days = len(daily_energy)
    ax5.annotate(f'N = {n_days} días\nP25 = {p25:.0f} kWh\nP75 = {p75:.0f} kWh',
                 xy=(0.02, 0.98), xycoords='axes fraction', ha='left', va='top',
                 fontsize=8, bbox=dict(boxstyle='round', facecolor='lightyellow'))
    
    # Panel 6: Performance Ratio mensual
    ax6 = fig.add_subplot(gs[1, 2])
    
    # Calcular PR mensual (simplificado)
    monthly_energy = monthly['ac_energy_kwh'].values
    monthly_ghi = np.asarray(df.groupby(pd.to_datetime(df.index).month)['ghi_wm2'].sum().values) / 4 / 1000  # kWh/m²
    
    system_dc_kw = results.get('target_dc_kw', 4162)
    pr_monthly = []
    for e, g in zip(monthly_energy, monthly_ghi):
        if g > 0:
            pr = (e / system_dc_kw) / g * 100  # %
            pr_monthly.append(min(pr, 100))  # Limitar a 100%
        else:
            pr_monthly.append(0)
    
    months_labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                     'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    ax6.plot(months_labels, pr_monthly, 'go-', linewidth=2, markersize=8)
    pr_mean = float(np.mean([p for p in pr_monthly if p > 0]))
    ax6.axhline(y=pr_mean, color='red', linestyle='--', linewidth=1.5, 
                label=f'PR anual: {pr_mean:.1f}%')
    
    ax6.set_ylabel('PR (%)')
    ax6.set_xlabel('Mes')
    ax6.set_title('PERFORMANCE RATIO MENSUAL', fontsize=10, fontweight='bold')
    ax6.legend(fontsize=8)
    ax6.set_ylim(min(pr_monthly) * 0.95, max(pr_monthly) * 1.05)
    ax6.grid(True, alpha=0.3)
    
    # Anotaciones min/max
    pr_min = min([p for p in pr_monthly if p > 0])
    pr_max = max(pr_monthly)
    ax6.annotate(f'Mín: {pr_min:.1f}%\nMáx: {pr_max:.1f}%\nPromedio: {pr_mean:.1f}%',
                 xy=(0.02, 0.05), xycoords='axes fraction', ha='left', va='bottom',
                 fontsize=8, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.suptitle(f'Análisis Temporal Avanzado - Sistema FV Iquitos {year}', fontsize=14, fontweight='bold')
    
    plt.savefig(out_dir / 'solar_analisis_temporal_avanzado.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Grafica: Analisis Temporal Avanzado")
    
    # Limpiar columnas auxiliares
    df.drop(columns=['hour', 'month'], inplace=True, errors='ignore')


def generate_all_solar_plots(data_dir: Path, out_dir: Path) -> None:
    """
    Genera todas las gráficas del sistema fotovoltaico.
    
    Args:
        data_dir: Directorio con datos (solar_results.json, pv_generation_timeseries.csv)
        out_dir: Directorio de salida para las gráficas
    """
    print("\n" + "="*60)
    print("  GENERACIÓN DE GRÁFICAS AVANZADAS - SISTEMA FV")
    print("="*60)
    
    # Crear directorio de salida si no existe
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Cargar datos
    print("\n[+] Cargando datos...")
    df, monthly, results = load_solar_data(data_dir)
    print(f"   Series temporal: {len(df):,} registros")
    print(f"   Período: {df.index[0]} a {df.index[-1]}")
    
    print("\n[+] Generando graficas...")
    
    # 1. Energía y Potencia Máxima Diaria
    plot_energia_potencia_diaria(df, results, out_dir)
    
    # 2. Días representativos
    despejado_date = results.get('despejado_date', '')
    intermedio_date = results.get('intermedio_date', '')
    nublado_date = results.get('nublado_date', '')
    
    if despejado_date:
        plot_dia_representativo(df, despejado_date, 'despejado', results, out_dir)
        plot_dia_barras(df, despejado_date, 'despejado', results, out_dir)
    if intermedio_date:
        plot_dia_representativo(df, intermedio_date, 'intermedio', results, out_dir)
    if nublado_date:
        plot_dia_representativo(df, nublado_date, 'nublado', results, out_dir)
    
    # 3. Resumen del sistema
    plot_resumen_sistema(df, monthly, results, out_dir)
    
    # 4. POA vs Potencia
    plot_poa_vs_potencia(df, results, out_dir)
    
    # 5. Comparación de escenarios
    plot_comparacion_escenarios(df, results, out_dir)
    
    # 6. Análisis temporal avanzado
    plot_analisis_temporal_avanzado(df, monthly, results, out_dir)
    
    print("\n" + "="*60)
    print(f"[OK] Graficas guardadas en: {out_dir}")
    print("="*60)
    
    # Listar archivos generados
    print("\n[+] Archivos generados:")
    for f in sorted(out_dir.glob('solar_*.png')):
        print(f"   - {f.name}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generar gráficas avanzadas del sistema FV')
    parser.add_argument('--data-dir', type=str, default='data/interim/oe2/solar',
                        help='Directorio con datos de entrada')
    parser.add_argument('--out-dir', type=str, default='reports/oe2/solar_plots',
                        help='Directorio de salida para gráficas')
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    
    generate_all_solar_plots(data_dir, out_dir)
