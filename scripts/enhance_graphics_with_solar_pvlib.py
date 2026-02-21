#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mejora de Gráficas: Actualizar con Datos Calculados por solar_pvlib
======================================================================

Mantiene la estructura y cantidad de paneles, actualiza SOLO los datos
según los cálculos del archivo actual de solar_pvlib:
- pv_generation_hourly_citylearn_v2.csv (8,760 puntos horarios)

Gráficas a actualizar:
1. Día Despejado Representativo (2 paneles)
2. Relación POA vs Potencia AC (scatter + tendencia)
3. Perfil Día Despejado (3 líneas: Potencia, Energía 15min, POA)

Ejecución:
    python scripts/enhance_graphics_with_solar_pvlib.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

try:
    from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import (
        save_matplotlib_figure,
        is_matplotlib_available,
    )
except ImportError:
    print("❌ Error importando módulos")
    sys.exit(1)

if not is_matplotlib_available():
    print("❌ matplotlib NO disponible")
    sys.exit(1)

import matplotlib.pyplot as plt
from matplotlib import rcParams
from scipy import stats

rcParams['font.size'] = 9
rcParams['axes.labelsize'] = 9
rcParams['axes.titlesize'] = 10
rcParams['xtick.labelsize'] = 8
rcParams['ytick.labelsize'] = 8
rcParams['legend.fontsize'] = 8


def load_real_solar_data():
    """Carga datos REALES de solar_pvlib."""
    csv_path = Path(__file__).parent.parent / 'data' / 'oe2' / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
    df = pd.read_csv(csv_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df


def generate_clear_day_profile(df):
    """
    1️⃣ Día Despejado Representativo - 2 Paneles
    ==========================================
    Panel 1: Energía 15 min + Potencia AC (dual axis)
    Panel 2: Energía acumulada del día
    """
    print("\n  1️⃣  Día Despejado Representativo (2 paneles)...")
    
    # Buscar día con mayor GHI
    daily_ghi = df.groupby(df['datetime'].dt.date)['ghi_wm2'].sum()
    best_date = daily_ghi.idxmax()
    df_best = df[df['datetime'].dt.date == best_date].copy()
    
    if df_best.empty:
        print("  ⚠️  No hay datos para día despejado")
        return
    
    df_best['hour'] = df_best['datetime'].dt.hour
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(f'Día Despejado Representativo {best_date} | Energía total: {df_best["ac_energy_kwh"].sum():,.0f} kWh | Potencia máxima: {df_best["ac_power_kw"].max():,.1f} kW',
                 fontsize=11, fontweight='bold')
    
    # ========================================================================
    # Panel 1: Energía 15 min (barras) + Potencia AC (línea)
    # ========================================================================
    ax1 = axes[0]
    ax1_twin = ax1.twinx()
    
    # Barras de energía (15 min)
    energy_15min = df_best['ac_energy_kwh'].values
    hours_continuous = np.arange(len(energy_15min))
    
    bars = ax1.bar(hours_continuous, energy_15min, width=0.8, color='#FFD700', alpha=0.8, edgecolor='orange', linewidth=0.5, label='Energía 15 min (kWh)')
    
    # Línea de potencia AC
    power_ac = df_best['ac_power_kw'].values
    line = ax1_twin.plot(hours_continuous, power_ac, color='#0066CC', linewidth=2.5, marker='o', markersize=4, label='Potencia AC (kW)', zorder=5)
    
    # Anotación potencia máxima
    max_power_idx = np.argmax(power_ac)
    max_power_val = power_ac[max_power_idx]
    ax1_twin.annotate(f'Pmáx: {max_power_val:.0f} kW\nHora: {max_power_idx:02d}:00',
                     xy=(max_power_idx, max_power_val),
                     xytext=(max_power_idx + 2, max_power_val - 200),
                     fontsize=9, fontweight='bold',
                     bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9),
                     arrowprops=dict(arrowstyle='->', color='black', lw=1))
    
    ax1.set_ylabel('Energía 15 min [kWh]', fontsize=9, fontweight='bold', color='#FFD700')
    ax1_twin.set_ylabel('Potencia AC [kW]', fontsize=9, fontweight='bold', color='#0066CC')
    ax1.set_xlabel('Hora del día', fontsize=9)
    ax1.set_xlim(-0.5, len(energy_15min) - 0.5)
    ax1.set_ylim(0, max(energy_15min) * 1.15)
    ax1_twin.set_ylim(0, max_power_val * 1.2)
    
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_xticks(range(0, 24))
    ax1.set_xticklabels([f'{i:02d}:00' for i in range(24)], fontsize=8, rotation=45)
    
    ax1.tick_params(axis='y', labelcolor='#FFD700')
    ax1_twin.tick_params(axis='y', labelcolor='#0066CC')
    
    # Leyenda combinada
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8)
    
    ax1.set_title('Panel 1: Energía 15 min (barras) + Potencia AC (línea)', fontsize=10, fontweight='bold', pad=10)
    
    # ========================================================================
    # Panel 2: Energía acumulada
    # ========================================================================
    ax2 = axes[1]
    energy_cumsum = np.cumsum(energy_15min)
    
    ax2.fill_between(hours_continuous, energy_cumsum, alpha=0.4, color='steelblue')
    ax2.plot(hours_continuous, energy_cumsum, color='steelblue', linewidth=2.5, marker='s', markersize=5, label='Energía acumulada')
    
    # Anotar valor final
    final_energy = energy_cumsum[-1]
    ax2.annotate(f'Total: {final_energy:,.0f} kWh', 
                xy=(len(hours_continuous)-1, final_energy),
                xytext=(len(hours_continuous)-5, final_energy*0.8),
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.9),
                arrowprops=dict(arrowstyle='->', color='black', lw=1))
    
    ax2.set_ylabel('Energía Acumulada [kWh]', fontsize=9, fontweight='bold')
    ax2.set_xlabel('Hora del día', fontsize=9)
    ax2.set_xlim(-0.5, len(energy_15min) - 0.5)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(range(0, 24))
    ax2.set_xticklabels([f'{i:02d}:00' for i in range(24)], fontsize=8, rotation=45)
    ax2.set_title('Panel 2: Energía Acumulada del Día', fontsize=10, fontweight='bold', pad=10)
    ax2.legend(loc='upper left', fontsize=8)
    
    plt.tight_layout()
    save_matplotlib_figure(fig, 'dia_despejado_representativo_2024.png', subdir='solar')
    plt.close(fig)


def generate_poa_vs_power_relationship(df):
    """
    2️⃣ Relación POA vs Potencia AC
    ==============================
    Scatter plot con tendencia lineal + estadísticas
    """
    print("  2️⃣  Relación POA vs Potencia AC...")
    
    # Calcular POA (Plane of Array) - usando GHI como aproximación
    df_clean = df[(df['ghi_wm2'] > 0) & (df['ac_power_kw'] > 0)].copy()
    
    fig, ax = plt.subplots(figsize=(13, 8))
    
    # Scatter plot con color según potencia
    scatter = ax.scatter(df_clean['ghi_wm2'], df_clean['ac_power_kw'], 
                        c=df_clean['ac_power_kw'], cmap='viridis',
                        alpha=0.5, s=15, edgecolors='none', label='Datos horarios')
    
    # Tendencia lineal
    z = np.polyfit(df_clean['ghi_wm2'], df_clean['ac_power_kw'], 1)
    p = np.poly1d(z)
    x_trend = np.linspace(0, df_clean['ghi_wm2'].max(), 100)
    y_trend = p(x_trend)
    
    ax.plot(x_trend, y_trend, 'b--', linewidth=2.5, label=f'Tendencia: P = {z[0]:.3f}·POA + {z[1]:.1f}', zorder=5)
    
    # Estadísticas
    correlation = df_clean['ghi_wm2'].corr(df_clean['ac_power_kw'])
    max_poa = df_clean['ghi_wm2'].max()
    max_power = df_clean['ac_power_kw'].max()
    num_points = len(df_clean)
    
    stats_text = (f"Correlación: {correlation:.3f}\n"
                 f"POA máx: {max_poa:.0f} W/m²\n"
                 f"P máx: {max_power:.0f} kW\n"
                 f"Puntos: {num_points:,}")
    
    ax.text(0.98, 0.03, stats_text, transform=ax.transAxes,
           fontsize=9, verticalalignment='bottom', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.95, edgecolor='black', linewidth=1))
    
    ax.set_title('Relación POA vs Potencia AC - 2024', fontsize=12, fontweight='bold')
    ax.set_xlabel('POA - Irradiancia en Plano del Array [W/m²]', fontsize=10)
    ax.set_ylabel('Potencia AC (kW)', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left', fontsize=9)
    ax.set_xlim(0, max_poa * 1.05)
    ax.set_ylim(0, max_power * 1.05)
    
    cbar = plt.colorbar(scatter, ax=ax, label='Potencia AC [kW]')
    
    plt.tight_layout()
    save_matplotlib_figure(fig, 'relacion_poa_potencia_ac_2024.png', subdir='solar')
    plt.close(fig)


def generate_clear_day_3curves(df):
    """
    3️⃣ Perfil Día Despejado: 3 Líneas (Potencia, Energía 15min, POA)
    ===============================================================
    """
    print("  3️⃣  Perfil Día Despejado (3 líneas)...")
    
    # Buscar día con mayor GHI
    daily_ghi = df.groupby(df['datetime'].dt.date)['ghi_wm2'].sum()
    best_date = daily_ghi.idxmax()
    df_best = df[df['datetime'].dt.date == best_date].copy()
    
    if df_best.empty:
        print("  ⚠️  No hay datos para día despejado")
        return
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    hours = np.arange(len(df_best))
    
    # Normalizar para visualización en mismo gráfico
    potencia_norm = df_best['ac_power_kw'].values / df_best['ac_power_kw'].max() * 100
    energia_norm = df_best['ac_energy_kwh'].values / df_best['ac_energy_kwh'].max() * 100
    poa_norm = df_best['ghi_wm2'].values / df_best['ghi_wm2'].max() * 100
    
    # Tres líneas
    ax.plot(hours, potencia_norm, marker='o', linewidth=2.5, markersize=5, 
           color='#FF6B00', label='Potencia AC (%)' , zorder=3)
    ax.plot(hours, energia_norm, marker='s', linewidth=2.5, markersize=5,
           color='#FFD700', label='Energía 15 min (%)', zorder=2)
    ax.plot(hours, poa_norm, marker='^', linewidth=2.5, markersize=5,
           color='#FF0000', label='POA - GHI (%)', zorder=1)
    
    ax.fill_between(hours, potencia_norm, alpha=0.2, color='#FF6B00')
    ax.fill_between(hours, energia_norm, alpha=0.2, color='#FFD700')
    ax.fill_between(hours, poa_norm, alpha=0.2, color='#FF0000')
    
    ax.set_title(f'Perfil de Potencia, Energía (15 min) y POA - Día despejado ({best_date})', 
                fontsize=12, fontweight='bold')
    ax.set_xlabel('Hora del día', fontsize=10)
    ax.set_ylabel('Valores Normalizados [%]', fontsize=10)
    ax.set_xlim(-0.5, len(hours) - 0.5)
    ax.set_ylim(0, 105)
    ax.set_xticks(range(0, 24))
    ax.set_xticklabels([f'{i:02d}:00' for i in range(24)], fontsize=8)
    
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper center', ncol=3, fontsize=9)
    
    # Anotar máximos
    max_pot_idx = np.argmax(potencia_norm)
    ax.annotate(f'Pmáx: {df_best["ac_power_kw"].max():.0f}kW\n@{max_pot_idx:02d}:00',
               xy=(max_pot_idx, potencia_norm[max_pot_idx]),
               xytext=(max_pot_idx - 3, potencia_norm[max_pot_idx] + 15),
               fontsize=8, fontweight='bold',
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9),
               arrowprops=dict(arrowstyle='->', color='black', lw=1))
    
    plt.tight_layout()
    save_matplotlib_figure(fig, 'perfil_dia_despejado_3curvas_2024.png', subdir='solar')
    plt.close(fig)


def generate_hourly_power_distribution(df):
    """
    4️⃣ Distribución horaria de potencia + perfiles por escenario
    """
    print("  4️⃣  Distribución Horaria de Potencia...")
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Distribución Horaria de Potencia - 2024', fontsize=12, fontweight='bold')
    
    # Panel 1: Perfil promedio horario
    hourly_avg = df.groupby(df['datetime'].dt.hour)['ac_power_kw'].agg(['mean', 'std', 'min', 'max'])
    
    ax = axes[0]
    ax.plot(hourly_avg.index, hourly_avg['mean'], marker='o', linewidth=2.5, markersize=7, 
           color='steelblue', label='Promedio', zorder=3)
    ax.fill_between(hourly_avg.index, 
                    hourly_avg['mean'] - hourly_avg['std'],
                    hourly_avg['mean'] + hourly_avg['std'],
                    alpha=0.3, color='steelblue', label='±1 σ')
    ax.plot(hourly_avg.index, hourly_avg['min'], '--', linewidth=1.5, color='cyan', 
           label='Mín', alpha=0.7)
    ax.plot(hourly_avg.index, hourly_avg['max'], '--', linewidth=1.5, color='orange',
           label='Máx', alpha=0.7)
    
    ax.set_title('Panel 1: Perfil Horario Promedio con Variabilidad', fontsize=10, fontweight='bold')
    ax.set_xlabel('Hora del día', fontsize=9)
    ax.set_ylabel('Potencia [kW]', fontsize=9)
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    
    # Panel 2: Box plot por hora
    ax = axes[1]
    hourly_data = [df[df['datetime'].dt.hour == h]['ac_power_kw'].values for h in range(24)]
    bp = ax.boxplot(hourly_data, labels=range(24), patch_artist=True)
    
    for patch in bp['boxes']:
        patch.set_facecolor('steelblue')
        patch.set_alpha(0.7)
    
    ax.set_title('Panel 2: Distribución de Potencia por Hora', fontsize=10, fontweight='bold')
    ax.set_xlabel('Hora del día', fontsize=9)
    ax.set_ylabel('Potencia [kW]', fontsize=9)
    ax.set_xticklabels(range(24), fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    save_matplotlib_figure(fig, 'distribucion_horaria_potencia_2024.png', subdir='solar')
    plt.close(fig)


def main():
    """Función principal."""
    print("\n" + "="*100)
    print("🔄 MEJORA DE GRÁFICAS: Actualizar con Datos Calculados por solar_pvlib")
    print("="*100 + "\n")
    
    print("📊 Cargando datos de solar_pvlib...")
    df = load_real_solar_data()
    print(f"✅ {len(df)} puntos cargados ({df['datetime'].min()} a {df['datetime'].max()})")
    print(f"⚡ Energía anual: {df['ac_energy_kwh'].sum():,.0f} kWh")
    print(f"🔋 Potencia máxima: {df['ac_power_kw'].max():,.0f} kW\n")
    
    print("📊 MEJORANDO GRÁFICAS CON DATOS ACTUALIZADOS:")
    print("=" * 100)
    
    generate_clear_day_profile(df)
    generate_poa_vs_power_relationship(df)
    generate_clear_day_3curves(df)
    generate_hourly_power_distribution(df)
    
    print("\n" + "=" * 100)
    print("✅ MEJORA DE GRÁFICAS COMPLETADA")
    print("=" * 100)
    print("\n✅ 4 gráficas mejoradas en RAÍZ:")
    print("   - outputs/analysis/solar/dia_despejado_representativo_2024.png (2 paneles)")
    print("   - outputs/analysis/solar/relacion_poa_potencia_ac_2024.png (scatter + tendencia)")
    print("   - outputs/analysis/solar/perfil_dia_despejado_3curvas_2024.png (3 líneas)")
    print("   - outputs/analysis/solar/distribucion_horaria_potencia_2024.png (2 paneles)")
    print("\n✅ Datos: 100% REALES de solar_pvlib")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
