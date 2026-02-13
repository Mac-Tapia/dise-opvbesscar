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

import json
from pathlib import Path
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd  # type: ignore[import]

import matplotlib.dates as mdates  # type: ignore[import-untyped]
import matplotlib.pyplot as plt  # type: ignore[import-untyped]
import pvlib  # type: ignore[import-untyped]
from matplotlib.gridspec import GridSpec  # type: ignore[import-untyped]
from scipy import stats  # type: ignore[import-untyped]

# Configuración global de matplotlib para español
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False


def _get_decimal_hours(df: pd.DataFrame) -> np.ndarray[Any, np.dtype[np.floating[Any]]]:
    """Extrae horas decimales del índice de un DataFrame."""
    idx_dt: pd.DatetimeIndex = pd.to_datetime(df.index)  # type: ignore[assignment]
    hours: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(idx_dt.hour + idx_dt.minute / 60)  # type: ignore[union-attr]
    return hours


def _get_values(series: pd.Series[Any]) -> np.ndarray[Any, np.dtype[Any]]:
    """Extrae valores como numpy array."""
    values_array: np.ndarray[Any, np.dtype[Any]] = np.asarray(series.values)  # type: ignore[assignment]
    return values_array


def load_solar_data(solar_data_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Carga todos los datos solares necesarios."""
    # Serie temporal
    ts_path: Path = solar_data_dir / "pv_generation_timeseries.csv"
    df: pd.DataFrame = pd.read_csv(ts_path, parse_dates=['timestamp'], index_col='timestamp')  # type: ignore[assignment]

    # Energía mensual
    monthly_path: Path = solar_data_dir / "pv_monthly_energy.csv"
    monthly: pd.DataFrame = pd.read_csv(monthly_path, parse_dates=['timestamp'], index_col='timestamp')  # type: ignore[assignment]

    # Resultados JSON
    json_path: Path = solar_data_dir / "solar_results.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        results: Dict[str, Any] = json.load(f)

    return df, monthly, results

    return df, monthly, results


def plot_energia_potencia_diaria(
    df: pd.DataFrame,
    _results: Dict[str, Any],
    out_dir: Path,
) -> None:
    """
    Gráfica 1: Energía y Potencia Máxima Diaria del Sistema FV
    Doble eje Y con barras de energía y línea de potencia máxima.
    """
    from matplotlib.figure import Figure  # type: ignore[import]
    from matplotlib.axes import Axes  # type: ignore[import]

    _fig: Figure
    ax1: Axes
    _fig, ax1 = plt.subplots(figsize=(14, 6))  # type: ignore[assignment]

    # Calcular datos diarios
    daily_energy: pd.Series[Any] = df['ac_energy_kwh'].resample('D').sum() / 1000  # type: ignore[assignment]  # MWh
    daily_pmax: pd.Series[Any] = df['ac_power_kw'].resample('D').max()  # type: ignore[assignment]

    # Estadísticas
    energy_mean: float = float(daily_energy.mean())  # type: ignore[arg-type]
    pmax_mean: float = float(daily_pmax.mean())  # type: ignore[arg-type]
    pmax_absolute: float = float(daily_pmax.max())  # type: ignore[arg-type]
    pmax_date_idx: Any = daily_pmax.idxmax()
    pmax_date: pd.Timestamp = pd.Timestamp(pmax_date_idx)  # type: ignore[arg-type]

    # Eje izquierdo: Energía diaria (barras)
    energy_values: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(daily_energy.values, dtype=np.float64)  # type: ignore[assignment]
    x_values: np.ndarray[Any, np.dtype[np.intp]] = np.arange(len(energy_values))  # type: ignore[assignment]
    ax1.fill_between(x_values, energy_values, alpha=0.6,  # type: ignore[arg-type]
                     color='lightblue', label='Energía diaria (MWh)')
    ax1.axhline(y=energy_mean, color='blue', linestyle='--', linewidth=1.5,
                label=f'Promedio: {energy_mean:.2f} MWh')
    ax1.set_xlabel('Fecha', fontsize=11)
    ax1.set_ylabel('Energía diaria (MWh)', fontsize=11, color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.set_ylim(0, daily_energy.max() * 1.1)

    # Eje derecho: Potencia máxima diaria (línea)
    ax2 = ax1.twinx()
    pmax_values: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(daily_pmax.values, dtype=np.float64)  # type: ignore[assignment]
    ax2.plot(daily_pmax.index, pmax_values, 'r-', linewidth=0.8,
             label='Potencia máxima diaria (kW)')
    ax2.axhline(y=pmax_mean, color='darkred', linestyle='--', linewidth=1.5,
                label=f'Pmax promedio: {pmax_mean:.0f} kW')
    ax2.set_ylabel('Potencia máxima diaria (kW)', fontsize=11, color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    ax2.set_ylim(0, pmax_absolute * 1.15)

    # Anotación del máximo absoluto - usar pmax_date como objeto Timestamp
    pmax_date_num = float(mdates.date2num(pmax_date))  # type: ignore[arg-type]
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
    print("  [OK] Grafica: Energia y Potencia Maxima Diaria")


def plot_dia_representativo(df: pd.DataFrame, date_str: str, day_type: str,
                            _results: Dict[str, Any], out_dir: Path) -> None:
    """
    Gráfica 2: Perfil de Potencia, Energía (15 min) y POA - Día representativo
    Con energía acumulada en panel inferior.
    """
    date: pd.Timestamp = pd.to_datetime(date_str)  # type: ignore[assignment]
    # Filtrar por fecha usando pd.to_datetime para el índice
    idx_dates: np.ndarray[Any, np.dtype[Any]] = pd.to_datetime(df.index).date  # type: ignore[union-attr]
    day_data_raw: pd.DataFrame | Any = df[idx_dates == date.date()].copy()  # type: ignore[assignment]
    day_data: pd.DataFrame = day_data_raw if isinstance(day_data_raw, pd.DataFrame) else pd.DataFrame()

    if day_data.empty:
        print(f"  ⚠ No hay datos para {date_str}")
        return

    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 1, height_ratios=[2, 1], hspace=0.15)

    # Panel superior: Potencia, Energía 15 min y POA
    ax1 = fig.add_subplot(gs[0])

    # Calcular horas decimales
    idx_dt: pd.DatetimeIndex = pd.to_datetime(day_data.index)  # type: ignore[assignment]
    hours: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(idx_dt.hour + idx_dt.minute / 60)  # type: ignore[union-attr]

    # Potencia AC
    ac_power: pd.Series[Any] = day_data['ac_power_kw']  # type: ignore[assignment]
    ac_power_arr: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(ac_power.values)  # type: ignore[assignment]
    ax1.plot(hours, ac_power_arr, 'b-', linewidth=2, label='Potencia (kW)')

    # Energía 15 min (línea discontinua naranja)
    ac_energy: pd.Series[Any] = day_data['ac_energy_kwh']  # type: ignore[assignment]
    ac_energy_arr: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(ac_energy.values)  # type: ignore[assignment]
    ax1.plot(hours, ac_energy_arr, '--', color='orange', linewidth=1.5,
             label='Energía 15 min (kWh)')

    ax1.set_ylabel('Potencia (kW)', fontsize=11, color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    max_power: float = float(day_data['ac_power_kw'].max())  # type: ignore[arg-type]
    ax1.set_ylim(0, max(max_power * 1.15, 1.0))

    # Eje derecho: POA
    ax1_r = ax1.twinx()
    # Calcular POA aproximado (GHI * cos(incidencia) ≈ GHI para tilt pequeño)
    poa: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(day_data['ghi_wm2'].values)  # type: ignore[assignment]
    ax1_r.plot(hours, poa, 'r-', linewidth=1.5, label='POA (W/m²)')
    ax1_r.set_ylabel('POA (W/m²)', fontsize=11, color='red')
    ax1_r.tick_params(axis='y', labelcolor='red')
    poa_max: float = float(np.max(poa))  # type: ignore[arg-type]
    ax1_r.set_ylim(0, poa_max * 1.1 if poa_max > 0 else 100)

    # Combinar leyendas
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_r.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)

    ax1.set_xlim(0, 24)
    ax1.set_xticks(range(0, 25, 2))
    ax1.set_xticklabels([f'{h:02d}:00' for h in range(0, 25, 2)], fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Panel inferior: Energía acumulada
    ax2 = fig.add_subplot(gs[1])
    energy_cumsum: pd.Series[Any] = day_data['ac_energy_kwh'].cumsum()  # type: ignore[assignment]
    cumsum_array: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(energy_cumsum.values)  # type: ignore[assignment]
    ax2.fill_between(hours, cumsum_array, alpha=0.5, color='purple')  # type: ignore[arg-type]
    ax2.plot(hours, cumsum_array, 'purple', linewidth=2, label='Energía acumulada (kWh)')
    ax2.set_xlabel('Hora del día', fontsize=11)
    ax2.set_ylabel('Energía acumulada (kWh)', fontsize=11)
    ax2.set_xlim(0, 24)
    ax2.set_xticks(range(0, 25, 2))
    ax2.set_xticklabels([f'{h:02d}:00' for h in range(0, 25, 2)], fontsize=9)
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
                    _results: Dict[str, Any], out_dir: Path) -> None:
    """
    Gráfica 3: Día Representativo con barras de energía 15 min
    """
    date: pd.Timestamp = pd.to_datetime(date_str)  # type: ignore[assignment]
    idx_dates: np.ndarray[Any, np.dtype[Any]] = pd.to_datetime(df.index).date  # type: ignore[union-attr]
    day_data_raw: pd.DataFrame | Any = df[idx_dates == date.date()].copy()  # type: ignore[assignment]
    day_data: pd.DataFrame = day_data_raw if isinstance(day_data_raw, pd.DataFrame) else pd.DataFrame()

    if day_data.empty:
        return

    # Filtrar solo horas con generación
    day_data = day_data[day_data['ac_energy_kwh'] > 0]

    if day_data.empty:
        return

    _fig, ax1 = plt.subplots(figsize=(14, 6))

    # Convertir índice a hora local sin timezone para que matplotlib muestre correctamente
    # (evita que matplotlib convierta a UTC)
    times_idx: pd.DatetimeIndex = pd.to_datetime(day_data.index)  # type: ignore[assignment]
    times_local: pd.DatetimeIndex = times_idx.tz_localize(None)  # type: ignore[union-attr]

    # Barras de energía 15 min
    widths = 0.01  # Ancho de barras
    energy_15min: pd.Series[Any] = day_data['ac_energy_kwh']  # type: ignore[assignment]
    energy_arr: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(energy_15min.values)  # type: ignore[assignment]
    ax1.bar(times_local, energy_arr, width=widths, color='gold',
            edgecolor='orange', alpha=0.8, label='Energía 15 min (kWh)')

    ax1.set_ylabel('Energía 15 min (kWh)', fontsize=11, color='darkorange')
    ax1.tick_params(axis='y', labelcolor='darkorange')

    # Eje derecho: Potencia AC
    ax2 = ax1.twinx()
    ac_power: pd.Series[Any] = day_data['ac_power_kw']  # type: ignore[assignment]
    ac_power_arr: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(ac_power.values)  # type: ignore[assignment]
    ax2.plot(times_local, ac_power_arr, 'b-', linewidth=2, label='Potencia AC (kW)')
    ax2.set_ylabel('Potencia AC (kW)', fontsize=11, color='blue')
    ax2.tick_params(axis='y', labelcolor='blue')

    # Estadísticas
    total_energy: float = float(day_data['ac_energy_kwh'].sum())  # type: ignore[arg-type]
    max_power: float = float(day_data['ac_power_kw'].max())  # type: ignore[arg-type]
    hours_gen: float = len(day_data.index) * 0.25  # intervalos de 15 min
    peak_hour_idx: int | str = day_data['ac_power_kw'].idxmax()  # type: ignore[assignment]
    peak_hour: pd.Timestamp = pd.Timestamp(peak_hour_idx)  # type: ignore[arg-type]

    # Anotación - usar hora local
    peak_hour_str = peak_hour.strftime("%H:%M")
    ax2.annotate(f'Horas de generación: {hours_gen:.1f} h\nHora pico: {peak_hour_str} (hora local)',
                 xy=(0.98, 0.95), xycoords='axes fraction', ha='right', va='top',
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange'))

    # Formato - hora local Perú (UTC-5)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax1.set_xlabel('Hora local (UTC-5 Perú)', fontsize=10)
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
                         _results: Dict[str, Any], out_dir: Path) -> None:
    """
    Gráfica 4: Sistema FV Iquitos - Resumen (4 paneles)
    - Energía diaria (serie temporal)
    - Energía mensual (barras)
    - Distribución de energía diaria (histograma)
    - Distribución de energía por hora del día
    """
    _fig, axes = plt.subplots(2, 2, figsize=(14, 10))  # type: ignore[assignment]
    year: int = int(df.index[0].year)  # type: ignore[index]

    daily_energy: pd.Series[Any] = df['ac_energy_kwh'].resample('D').sum() / 1000  # type: ignore[assignment]  # MWh

    # Panel 1: Energía diaria
    ax1 = axes[0, 0]
    ax1.plot(daily_energy.index, daily_energy.values, 'steelblue', linewidth=0.8)
    mean_daily: float = float(daily_energy.mean())  # type: ignore[arg-type]
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
    total_annual: float = float(daily_energy.sum())  # type: ignore[arg-type]
    ax1.annotate(f'Total anual: {total_annual:.1f} MWh\nDías: {len(daily_energy)}',
                 xy=(0.02, 0.98), xycoords='axes fraction', ha='left', va='top',
                 fontsize=8, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Panel 2: Energía mensual
    ax2 = axes[0, 1]
    months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    monthly_mwh: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(monthly['ac_energy_kwh'].values) / 1000  # type: ignore[assignment]
    cmap_blues: Any = plt.colormaps().get_cmap('Blues')  # type: ignore[attr-defined]
    colors = cmap_blues(np.linspace(0.4, 0.9, 12))
    bars = ax2.bar(months, monthly_mwh, color=colors, edgecolor='darkblue', alpha=0.8)
    mean_monthly: float = float(monthly_mwh.mean())  # type: ignore[arg-type]
    ax2.axhline(y=mean_monthly, color='gray', linestyle='--', linewidth=1.5,
                label=f'Promedio: {mean_monthly:.1f} MWh')
    ax2.set_ylabel('MWh/mes', fontsize=10)
    ax2.set_xlabel('Mes', fontsize=10)
    ax2.set_title('Energía mensual', fontsize=11, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=8)

    # Etiquetas en barras
    for rect, val in zip(bars, monthly_mwh):
        ax2.text(rect.get_x() + rect.get_width()/2, rect.get_height() + 5,
                 f'{val:.1f}', ha='center', va='bottom', fontsize=7)

    # Panel 3: Distribución de energía diaria
    ax3 = axes[1, 0]
    daily_kwh: pd.Series[Any] = daily_energy * 1000  # volver a kWh  # type: ignore[assignment]
    ax3.hist(daily_kwh, bins=30, color='steelblue', edgecolor='white', alpha=0.7)
    mean_kwh: float = float(daily_kwh.mean())  # type: ignore[arg-type]
    median_kwh: float = float(daily_kwh.median())  # type: ignore[arg-type]
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
    hourly_energy: pd.Series[Any] = df.groupby(pd.to_datetime(df.index).hour)['ac_energy_kwh'].sum()  # type: ignore[union-attr,assignment]
    hourly_arr: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(hourly_energy.values)  # type: ignore[assignment]
    ax4.bar(hourly_energy.index, hourly_arr, color='steelblue',
            edgecolor='darkblue', alpha=0.8)

    # Encontrar hora pico
    peak_hour: int = int(hourly_energy.idxmax())  # type: ignore[arg-type]
    peak_energy: float = float(hourly_energy.max())  # type: ignore[arg-type]
    total_energy: float = float(hourly_energy.sum())  # type: ignore[arg-type]
    hourly_mean: float = float(hourly_energy.mean())  # type: ignore[arg-type]

    ax4.axhline(y=hourly_mean, color='gray', linestyle='--', linewidth=1.5)
    ax4.set_xlabel('Hora del día', fontsize=10)
    ax4.set_ylabel('Energía anual total (kWh)', fontsize=10)
    ax4.set_title('Distribución de energía por hora del día', fontsize=11, fontweight='bold')
    ax4.set_xticks(range(0, 24, 2))
    ax4.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)], fontsize=8)

    # Anotación hora pico
    pico_text = (f'Hora pico: {peak_hour}:00\nEnergía: {peak_energy:.0f} kWh\n'
                 f'({peak_energy/total_energy*100:.1f}% del total)')
    ax4.annotate(pico_text,
                 xy=(0.98, 0.95), xycoords='axes fraction', ha='right', va='top',
                 fontsize=8, bbox=dict(boxstyle='round', facecolor='lightyellow',
                                       edgecolor='orange'))

    plt.suptitle(f'Sistema FV Iquitos - Resumen {year}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(out_dir / 'solar_resumen_sistema.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  [OK] Grafica: Resumen del Sistema FV")


def plot_poa_vs_potencia(df: pd.DataFrame, _results: Dict[str, Any], out_dir: Path) -> None:
    """
    Gráfica 5: Relación POA vs Potencia AC
    Scatter plot con línea de tendencia y correlación.
    """
    # Filtrar datos con producción
    mask: pd.Series[Any] = df['ac_power_kw'] > 0
    poa: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(df.loc[mask, 'ghi_wm2'].values)  # type: ignore[assignment]  # Usar GHI como proxy de POA
    power: np.ndarray[Any, np.dtype[np.floating[Any]]] = np.asarray(df.loc[mask, 'ac_power_kw'].values)  # type: ignore[assignment]

    from matplotlib.figure import Figure  # type: ignore[import]
    fig: Figure
    fig, ax = plt.subplots(figsize=(10, 8))  # type: ignore[assignment]

    # Scatter plot con color por potencia
    scatter = ax.scatter(
        poa,
        power,
        c=power,
        cmap='viridis',
        alpha=0.5,
        s=5,
    )
    fig.colorbar(scatter, ax=ax, label='Potencia AC (kW)')

    # Línea de tendencia
    linreg_result = stats.linregress(poa, power)
    slope_val: float = linreg_result.slope  # type: ignore[union-attr]
    intercept_val: float = linreg_result.intercept  # type: ignore[union-attr]
    poa_max = float(poa.max())
    x_line = np.linspace(0, poa_max * 1.1, 100)
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
    stats_text = (f'Correlación: {correlation:.3f}\nPmax: {pmax:.1f} kW\n'
                  f'POA en Pmax: {poa_at_pmax:.0f} W/m²\nPuntos: {len(poa):,}')
    ax.annotate(stats_text, xy=(0.98, 0.25), xycoords='axes fraction',
                ha='right', va='top', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='lightyellow',
                          edgecolor='gray'))

    ax.set_xlim(0, float(poa.max()) * 1.1)
    ax.set_ylim(0, pmax * 1.15)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_dir / 'solar_poa_vs_potencia.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  [OK] Grafica: Relacion POA vs Potencia AC")


def plot_comparacion_escenarios(df: pd.DataFrame, results: Dict[str, Any], out_dir: Path) -> None:
    """
    Gráfica 6: Comparación de Escenarios - Sistema FV
    Compara días despejado, intermedio, nublado y máxima energía.
    """
    # Obtener fechas de días representativos
    despejado_date: str = results.get('despejado_date', '')
    intermedio_date: str = results.get('intermedio_date', '')
    nublado_date: str = results.get('nublado_date', '')
    max_energy_date: str = results.get('max_daily_energy_date', '')

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

    for rect, val in zip(bars, energies):
        ax5.text(rect.get_x() + rect.get_width()/2, rect.get_height() + 200,
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
    print("  [OK] Grafica: Comparacion de Escenarios")


def plot_analisis_temporal_avanzado(df: pd.DataFrame, monthly: pd.DataFrame,
                                     results: Dict[str, Any], out_dir: Path) -> None:
    """
    Gráfica 7: Análisis Temporal Avanzado
    - Mapa de calor mes x hora
    - Box plots mensuales
    - Producción por trimestre
    - Variabilidad de producción diaria
    - Distribución de energía diaria con percentiles
    - Performance Ratio mensual
    """
    from matplotlib.figure import Figure  # type: ignore[import]
    fig: Figure
    fig = plt.figure(figsize=(16, 12))  # type: ignore[assignment]
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    year: int = int(df.index[0].year)  # type: ignore[index]

    # Preparar datos - crear columnas temporales
    df = df.copy()  # Evitar modificar el original
    df['hour'] = pd.to_datetime(df.index).hour  # type: ignore[union-attr]
    df['month'] = pd.to_datetime(df.index).month  # type: ignore[union-attr]
    daily_energy: pd.Series[Any] = df['ac_energy_kwh'].resample('D').sum()  # type: ignore[assignment]

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
    daily_energy_df: pd.DataFrame = daily_energy.to_frame()
    idx_month: np.ndarray[Any, np.dtype[Any]] = pd.to_datetime(daily_energy_df.index).month  # type: ignore[union-attr,assignment]
    daily_energy_df['month'] = idx_month
    daily_by_month: list[np.ndarray[Any, np.dtype[Any]]] = [
        np.asarray(daily_energy_df[daily_energy_df['month'] == m]['ac_energy_kwh'].values)
        for m in range(1, 13)
    ]
    bp = ax2.boxplot(daily_by_month, patch_artist=True)
    cmap_viridis = plt.colormaps()['viridis']  # type: ignore
    colors_box = cmap_viridis(np.linspace(0.2, 0.8, 12))
    for patch, color in zip(bp['boxes'], colors_box):
        patch.set_facecolor(color)  # type: ignore
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
    for rect, val in zip(bars, quarterly_vals):
        ax3.text(rect.get_x() + rect.get_width()/2, rect.get_height() + 10,
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
    ax4.axhline(y=mean_val, color='red', linestyle='--', linewidth=1.5, label='Promedio')

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

    p25: float = float(np.percentile(daily_energy, 25))
    p75: float = float(np.percentile(daily_energy, 75))
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

    # Calcular PR mensual con POA (PVLIB, sin truncar a 100 %)
    lat = results.get('lat', -3.75)
    lon = results.get('lon', -73.25)
    tz = results.get('tz', 'America/Lima')
    tilt = results.get('tilt', 10.0)
    azimuth = results.get('azimuth', 0.0)
    system_dc_kw = results.get('target_dc_kw', 4162)
    location = pvlib.location.Location(latitude=lat, longitude=lon, tz=tz)
    sp = location.get_solarposition(df.index)
    irr = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        dni=df['dni_wm2'],
        ghi=df['ghi_wm2'],
        dhi=df['dhi_wm2'],
        solar_zenith=sp['zenith'],
        solar_azimuth=sp['azimuth']
    )
    poa = irr['poa_global'].fillna(0)
    dt_hours = (df.index[1] - df.index[0]).total_seconds() / 3600
    poa_kwh_m2 = poa * dt_hours / 1000  # kWh/m2 por paso
    monthly_energy = monthly['ac_energy_kwh']
    monthly_poa = poa_kwh_m2.resample('ME').sum()
    pr_monthly_series = monthly_energy / (system_dc_kw * monthly_poa)
    pr_monthly = pr_monthly_series.values * 100  # a porcentaje

    months_labels = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                     'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    ax6.plot(months_labels, pr_monthly, 'go-', linewidth=2, markersize=8)
    pr_mean = float(np.mean(pr_monthly))
    ax6.axhline(y=pr_mean, color='red', linestyle='--', linewidth=1.5,
                label=f'PR anual: {pr_mean:.1f}%')

    ax6.set_ylabel('PR (%)')
    ax6.set_xlabel('Mes')
    ax6.set_title('PERFORMANCE RATIO MENSUAL', fontsize=10, fontweight='bold')
    ax6.legend(fontsize=8)
    ax6.set_ylim(min(pr_monthly) * 0.95, max(pr_monthly) * 1.05)
    ax6.grid(True, alpha=0.3)

    # Anotaciones min/max
    pr_min = float(np.min(pr_monthly))
    pr_max = float(np.max(pr_monthly))
    ax6.annotate(f'Mín: {pr_min:.1f}%\nMáx: {pr_max:.1f}%\nPromedio: {pr_mean:.1f}%',
                 xy=(0.02, 0.05), xycoords='axes fraction', ha='left', va='bottom',
                 fontsize=8, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.suptitle(f'Análisis Temporal Avanzado - Sistema FV Iquitos {year}', fontsize=14, fontweight='bold')

    plt.savefig(out_dir / 'solar_analisis_temporal_avanzado.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  [OK] Grafica: Analisis Temporal Avanzado")

    # Limpiar columnas auxiliares
    df.drop(columns=['hour', 'month'], inplace=True, errors='ignore')


def generate_all_solar_plots(input_data_dir: Path, output_dir: Path) -> None:
    """
    Genera todas las gráficas del sistema fotovoltaico.

    Args:
        input_data_dir: Directorio con datos (solar_results.json, pv_generation_timeseries.csv)
        output_dir: Directorio de salida para las gráficas
    """
    print("\n" + "="*60)
    print("  GENERACIÓN DE GRÁFICAS AVANZADAS - SISTEMA FV")
    print("="*60)

    # Crear directorio de salida si no existe
    output_dir.mkdir(parents=True, exist_ok=True)

    # Cargar datos
    print("\n[+] Cargando datos...")
    df, monthly, results = load_solar_data(input_data_dir)
    print(f"   Series temporal: {len(df):,} registros")
    print(f"   Período: {df.index[0]} a {df.index[-1]}")

    print("\n[+] Generando graficas...")

    # 1. Energía y Potencia Máxima Diaria
    plot_energia_potencia_diaria(df, results, output_dir)

    # 2. Días representativos
    despejado_date = results.get('despejado_date', '')
    intermedio_date = results.get('intermedio_date', '')
    nublado_date = results.get('nublado_date', '')

    if despejado_date:
        plot_dia_representativo(df, despejado_date, 'despejado', results, output_dir)
        plot_dia_barras(df, despejado_date, 'despejado', results, output_dir)
    if intermedio_date:
        plot_dia_representativo(df, intermedio_date, 'intermedio', results, output_dir)
    if nublado_date:
        plot_dia_representativo(df, nublado_date, 'nublado', results, output_dir)

    # 3. Resumen del sistema
    plot_resumen_sistema(df, monthly, results, output_dir)

    # 4. POA vs Potencia
    plot_poa_vs_potencia(df, results, output_dir)

    # 5. Comparación de escenarios
    plot_comparacion_escenarios(df, results, output_dir)

    # 6. Análisis temporal avanzado
    plot_analisis_temporal_avanzado(df, monthly, results, output_dir)

    print("\n" + "="*60)
    print(f"[OK] Graficas guardadas en: {output_dir}")
    print("="*60)

    # Listar archivos generados
    print("\n[+] Archivos generados:")
    for f in sorted(output_dir.glob('solar_*.png')):
        print(f"   - {f.name}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generar gráficas avanzadas del sistema FV')
    parser.add_argument('--data-dir', type=str, default='data/interim/oe2/solar',
                        help='Directorio con datos de entrada')
    parser.add_argument('--out-dir', type=str, default='reports/oe2/solar_plots',
                        help='Directorio de salida para gráficas')

    args = parser.parse_args()

    _data_dir = Path(args.data_dir)
    _out_dir = Path(args.out_dir)

    generate_all_solar_plots(_data_dir, _out_dir)
