#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gráficas Solares: Datos Reales desde solar_pvlib
================================================================================

Genera TODAS las gráficas del sistema FV usando ÚNICAMENTE datos reales de:
- pv_generation_hourly_citylearn_v2.csv (generado por solar_pvlib)
- Sin datos artificiales, sin escenarios inventados

Ejecución:
    cd d:\\diseñopvbesscar
    python scripts/generate_all_graphics_realdata.py
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
    print("❌ Error importando módulos de graficas")
    sys.exit(1)

if not is_matplotlib_available():
    print("❌ matplotlib NO disponible")
    sys.exit(1)

import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.gridspec import GridSpec

# Configurar estilo
rcParams['font.size'] = 9
rcParams['axes.labelsize'] = 9
rcParams['axes.titlesize'] = 10
rcParams['xtick.labelsize'] = 8
rcParams['ytick.labelsize'] = 8
rcParams['legend.fontsize'] = 8


def load_real_solar_data():
    """Carga ÚNICAMENTE datos reales generados por solar_pvlib."""
    try:
        csv_path = Path(__file__).parent.parent / 'data' / 'oe2' / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
        df = pd.read_csv(csv_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        print(f"✓ Datos reales cargados: {len(df)} filas × {len(df.columns)} columnas")
        print(f"  • Fecha inicio: {df['datetime'].min()}")
        print(f"  • Fecha fin: {df['datetime'].max()}")
        print(f"  • Energía total anual: {df['ac_energy_kwh'].sum():,.0f} kWh")
        print(f"  • Potencia máxima: {df['ac_power_kw'].max():,.0f} kW")
        
        return df
    except Exception as e:
        print(f"❌ Error cargando datos reales: {e}")
        sys.exit(1)


def generate_dia_despejado_real(df):
    """Genera gráfica de día despejado REAL (máxima radiación observada)."""
    print("\n📊 Generando: Día Despejado Representativo...")
    
    # Encontrar día con máxima irradiancia GHI (datos reales)
    df['date'] = df['datetime'].dt.date
    daily_ghi = df.groupby('date')['ghi_wm2'].sum().sort_values(ascending=False)
    clear_day = daily_ghi.index[0]
    
    day_data = df[df['date'] == clear_day].sort_values('datetime').reset_index(drop=True)
    
    # Calcular intervalos de 15 min (datos horarios distribuidos uniformemente)
    energy_15min = day_data['ac_energy_kwh'].values / 4
    power_kw = day_data['ac_power_kw'].values
    
    total_energy = day_data['ac_energy_kwh'].sum()
    max_power = day_data['ac_power_kw'].max()
    generation_hours = (day_data['ac_power_kw'] > 100).sum()
    
    # Crear figura
    fig, ax1 = plt.subplots(figsize=(14, 6))
    
    hours = np.arange(24)
    horas_15min = np.arange(0, 24 + 0.25, 0.25)
    energy_15min_filled = np.zeros(4*24)
    energy_15min_filled[:len(energy_15min)] = energy_15min
    power_filled = np.repeat(power_kw, 4)[:4*24]
    
    # Título
    fig.suptitle(f'Día Despejado Representativo {clear_day} | Energía total: {total_energy:,.1f} kWh | Potencia máxima: {max_power:,.0f} kW',
                fontsize=12, fontweight='bold', y=0.98)
    
    # Barras de energía
    color_energia = '#FFC000'
    ax1.set_xlabel('Hora del día', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Energía 15 min (kWh)', fontsize=11, fontweight='bold', color=color_energia)
    ax1.bar(horas_15min[:-1], energy_15min_filled, width=0.24, color=color_energia, alpha=0.8, edgecolor='darkorange', linewidth=0.5)
    ax1.tick_params(axis='y', labelcolor=color_energia)
    ax1.set_xlim(0, 24)
    
    # Línea de potencia
    ax2 = ax1.twinx()
    color_potencia = '#0066CC'
    ax2.set_ylabel('Potencia AC (kW)', fontsize=11, fontweight='bold', color=color_potencia)
    ax2.plot(horas_15min[:-1], power_filled, color=color_potencia, linewidth=3, marker='o', markersize=4, zorder=5)
    ax2.tick_params(axis='y', labelcolor=color_potencia)
    ax2.set_ylim(0, max_power * 1.1)
    
    ax1.set_ylim(0, energy_15min_filled.max() * 1.3)
    ax1.text(0.02, 0.95, f'(Horas de generación: {generation_hours/4:.1f} h)',
            transform=ax1.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(np.arange(0, 25, 2))
    ax1.set_xticklabels([f'{int(h):02d}' for h in np.arange(0, 25, 2)], fontsize=9)
    
    plt.tight_layout()
    save_matplotlib_figure(fig, 'dia_despejado_real_2024.png')
    print("✅ Gráfica guardada: dia_despejado_real_2024.png")
    plt.close(fig)


def generate_resumen_real(df):
    """Genera resumen con 4 paneles usando ÚNICAMENTE datos reales."""
    print("\n📊 Generando: Resumen 2024...")
    
    # Energía diaria
    df['date'] = df['datetime'].dt.date
    daily_energy = df.groupby('date')['ac_energy_kwh'].sum() / 1000  # MWh
    
    # Energía mensual
    df['month'] = df['datetime'].dt.to_period('M')
    monthly_energy = df.groupby('month')['ac_energy_kwh'].sum() / 1000  # MWh
    
    # Energía por hora
    df['hour'] = df['datetime'].dt.hour
    hourly_energy = df.groupby('hour')['ac_energy_kwh'].sum()
    
    # Figura 2x2
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('Sistema FV Iquitos - Resumen 2024', fontsize=14, fontweight='bold', y=0.98)
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)
    
    daily_avg = daily_energy.mean()
    daily_median = daily_energy.median()
    
    # Panel 1: Energía diaria
    ax1 = fig.add_subplot(gs[0, 0])
    x_daily = np.arange(len(daily_energy))
    ax1.bar(x_daily, daily_energy.values, color='steelblue', alpha=0.6, width=0.8)
    ax1.axhline(daily_avg, color='red', linestyle='--', linewidth=2.5, label=f'Promedio: {daily_avg:.1f} MWh')
    ax1.axhline(daily_median, color='green', linestyle='--', linewidth=2.5, label=f'Mediana: {daily_median:.1f} MWh')
    ax1.set_title('Energía diaria', fontsize=10, fontweight='bold', pad=10)
    ax1.set_xlabel('Fecha', fontsize=9)
    ax1.set_ylabel('Energía [MWh]', fontsize=9)
    ax1.set_xlim(0, len(daily_energy))
    ax1.set_ylim(0, daily_energy.max() * 1.1)
    ax1.legend(fontsize=8, loc='upper left')
    ax1.grid(True, alpha=0.3, axis='y')
    xtick_pos = np.linspace(0, len(daily_energy)-1, 13, dtype=int)
    xtick_labels = [daily_energy.index[i].strftime('%b') for i in xtick_pos]
    ax1.set_xticks(xtick_pos)
    ax1.set_xticklabels(xtick_labels, fontsize=8)
    
    # Panel 2: Energía mensual
    ax2 = fig.add_subplot(gs[0, 1])
    months_labels = [period.strftime('%b') for period in monthly_energy.index]
    x_pos = np.arange(len(months_labels))
    bars = ax2.bar(x_pos, monthly_energy.values, color='steelblue', alpha=0.7, edgecolor='black', linewidth=1)
    monthly_avg = monthly_energy.mean()
    ax2.axhline(monthly_avg, color='red', linestyle='--', linewidth=2.5, label=f'Promedio: {monthly_avg:.1f} MWh')
    for barra, val in zip(bars, monthly_energy.values):
        ax2.text(barra.get_x() + barra.get_width()/2., barra.get_height(),
                f'{val:.0f}', ha='center', va='bottom', fontsize=8, fontweight='bold')
    ax2.set_title('Energía mensual', fontsize=10, fontweight='bold', pad=10)
    ax2.set_xlabel('Mes', fontsize=9)
    ax2.set_ylabel('Energía [MWh]', fontsize=9)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(months_labels, fontsize=8)
    ax2.set_ylim(0, monthly_energy.max() * 1.15)
    ax2.legend(fontsize=8, loc='upper right')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Distribución diaria (histograma)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.hist(daily_energy.values, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
    ax3.axvline(daily_avg, color='red', linestyle='--', linewidth=2.5, label=f'Media: {daily_avg:.1f} kWh')
    ax3.axvline(daily_median, color='green', linestyle='--', linewidth=2.5, label=f'Mediana: {daily_median:.1f} kWh')
    ax3.text(0.98, 0.97, f'Media: {daily_avg:.1f} kWh\nMediana: {daily_median:.1f} kWh',
            transform=ax3.transAxes, fontsize=9, ha='right', va='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax3.set_title('Distribución de energía diaria', fontsize=10, fontweight='bold', pad=10)
    ax3.set_xlabel('Energía diaria [kWh]', fontsize=9)
    ax3.set_ylabel('Frecuencia (días)', fontsize=9)
    ax3.legend(fontsize=8, loc='upper left')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Panel 4: Energía por hora
    ax4 = fig.add_subplot(gs[1, 1])
    hours = np.arange(24)
    hourly_energy_mwh = hourly_energy / 1000
    colors = ['steelblue' if i < 6 or i > 18 else 'navy' if i < 10 or i > 16 else '#FF6B35' for i in hours]
    ax4.bar(hours, hourly_energy_mwh.values, color=colors, alpha=0.7, edgecolor='black', linewidth=1)
    peak_hour = hourly_energy_mwh.idxmax()
    peak_energy = hourly_energy_mwh.max()
    ax4.text(peak_hour, peak_energy, f'Hora pico: {peak_hour:02d}:00\nEnergía: {hourly_energy.max():,.0f} kWh',
            ha='center', va='bottom', fontsize=8, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax4.set_title('Distribución de energía por hora del día', fontsize=10, fontweight='bold', pad=10)
    ax4.set_xlabel('Hora del día', fontsize=9)
    ax4.set_ylabel('Energía acumulada [MWh]', fontsize=9)
    ax4.set_xticks(np.arange(0, 24, 2))
    ax4.set_xticklabels([f'{i:02d}:00' for i in range(0, 24, 2)], fontsize=8)
    ax4.set_xlim(-0.5, 23.5)
    ax4.set_ylim(0, peak_energy * 1.15)
    ax4.grid(True, alpha=0.3, axis='y')
    
    save_matplotlib_figure(fig, 'sistema_fv_iquitos_resumen_real_2024.png')
    print("✅ Gráfica guardada: sistema_fv_iquitos_resumen_real_2024.png")
    plt.close(fig)


def generate_temporal_analysis_real(df):
    """Genera análisis temporal con datos REALES."""
    print("\n📊 Generando: Análisis Temporal Avanzado...")
    
    df['month'] = df['datetime'].dt.month
    df['day'] = df['datetime'].dt.day
    df['hour'] = df['datetime'].dt.hour
    df['date'] = df['datetime'].dt.date
    
    # Datos para heatmap (promedio horario por mes)
    heatmap_data = df.groupby(['month', 'hour'])['ac_power_kw'].mean().unstack(fill_value=0)
    
    # Energía mensual diaria
    daily_by_month = df.groupby(['month', 'date'])['ac_energy_kwh'].sum()
    
    # Energía trimestral
    df['quarter'] = (df['month'] - 1) // 3 + 1
    quarterly = df.groupby('quarter')['ac_energy_kwh'].sum() / 1000
    
    # Variabilidad diaria (desv. estándar de energía diaria)
    daily_energy = df.groupby('date')['ac_energy_kwh'].sum()
    cv = daily_energy.std() / daily_energy.mean() * 100
    
    # Performance Ratio mensual (real, basado en datos)
    monthly_pr = []
    months_labels = []
    for month in range(1, 13):
        month_data = df[df['month'] == month]
        if len(month_data) > 0:
            energy = month_data['ac_energy_kwh'].sum()
            irr = month_data['ghi_wm2'].sum() / 1000
            if irr > 0:
                pr = (energy / 4049.56) / irr * 100
                monthly_pr.append(pr)
                months_labels.append(['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'][month-1])
    
    # Figura con 6 paneles
    fig = plt.figure(figsize=(18, 12))
    fig.suptitle('Análisis Temporal Avanzado - Sistema FV Iquitos 2024 (DATOS REALES)', fontsize=14, fontweight='bold', y=0.98)
    gs = GridSpec(3, 2, figure=fig, hspace=0.35, wspace=0.3)
    
    # Panel 1: Heatmap
    ax1 = fig.add_subplot(gs[0, 0])
    im = ax1.imshow(heatmap_data.values, aspect='auto', cmap='YlOrRd', origin='lower')
    ax1.set_xlabel('Hora del día', fontsize=9)
    ax1.set_ylabel('Mes', fontsize=9)
    ax1.set_xticks(np.arange(0, 24, 2))
    ax1.set_xticklabels([f'{i:02d}' for i in range(0, 24, 2)], fontsize=8)
    ax1.set_yticks(np.arange(12))
    ax1.set_yticklabels(['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'], fontsize=8)
    ax1.set_title('Potencia Promedio Mensual-Horaria (REAL)', fontsize=10, fontweight='bold', pad=8)
    plt.colorbar(im, ax=ax1, label='Potencia [kW]')
    
    # Panel 2: Distribución mensual de energía diaria
    ax2 = fig.add_subplot(gs[0, 1])
    daily_per_month = [df[df['month'] == m].groupby('date')['ac_energy_kwh'].sum() for m in range(1, 13)]
    ax2.boxplot(daily_per_month, labels=['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'])  # type: ignore
    ax2.set_title('Distribución Mensual de Energía Diaria (REAL)', fontsize=10, fontweight='bold', pad=8)
    ax2.set_ylabel('Energía diaria [kWh]', fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Producción por trimestre
    ax3 = fig.add_subplot(gs[1, 0])
    quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    colors_q = ['#FF9500', '#07C441', '#0066CC', '#FF5733']
    bars = ax3.bar(quarters, quarterly.values, color=colors_q, alpha=0.7, edgecolor='black', linewidth=1.5)
    for barra, val in zip(bars, quarterly.values):
        ax3.text(barra.get_x() + barra.get_width()/2., barra.get_height(),
                f'{val:.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax3.set_title('Producción por Trimestre (REAL)', fontsize=10, fontweight='bold', pad=8)
    ax3.set_ylabel('Energía [MWh]', fontsize=9)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Panel 4: Variabilidad diaria
    ax4 = fig.add_subplot(gs[1, 1])
    rolling_mean = daily_energy.rolling(window=7).mean()
    ax4.plot(daily_energy.values, color='steelblue', alpha=0.6, linewidth=1, label='Diario')
    ax4.plot(rolling_mean.values, color='red', linewidth=2, label='Media móvil 7 días')
    ax4.fill_between(np.arange(len(daily_energy)), 
                     (rolling_mean - daily_energy.std()).values,
                     (rolling_mean + daily_energy.std()).values,
                     alpha=0.2, color='red')
    ax4.set_title(f'Variabilidad de Producción Diaria (CV={cv:.1f}%, REAL)', fontsize=10, fontweight='bold', pad=8)
    ax4.set_ylabel('Energía [kWh]', fontsize=9)
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)
    
    # Panel 5: Distribución de energía diaria
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.hist(daily_energy.values, bins=25, color='steelblue', alpha=0.7, edgecolor='black')
    ax5.axvline(daily_energy.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {daily_energy.mean():.0f}')
    ax5.axvline(daily_energy.median(), color='green', linestyle='--', linewidth=2, label=f'Median: {daily_energy.median():.0f}')
    ax5.set_title('Distribución de Energía Diaria (REAL)', fontsize=10, fontweight='bold', pad=8)
    ax5.set_xlabel('Energía [kWh]', fontsize=9)
    ax5.set_ylabel('Frecuencia', fontsize=9)
    ax5.legend(fontsize=8)
    ax5.grid(True, alpha=0.3, axis='y')
    
    # Panel 6: Performance Ratio mensual
    ax6 = fig.add_subplot(gs[2, 1])
    x_pr = np.arange(len(monthly_pr))
    ax6.plot(x_pr, monthly_pr, marker='o', color='green', linewidth=2.5, markersize=8, label='PR mensual')
    mean_pr = np.mean(monthly_pr)
    ax6.axhline(mean_pr, color='red', linestyle='--', linewidth=2, label=f'PR anual: {mean_pr:.1f}%')
    ax6.axhspan(105, 130, alpha=0.1, color='green', label='Rango esperado')
    for i, pr in enumerate(monthly_pr):
        ax6.text(i, pr + 1, f'{pr:.0f}%', ha='center', fontsize=8, fontweight='bold')
    ax6.set_title('Performance Ratio Mensual (REAL)', fontsize=10, fontweight='bold', pad=8)
    ax6.set_ylabel('PR [%]', fontsize=9)
    ax6.set_xticks(x_pr)
    ax6.set_xticklabels(months_labels, fontsize=8)
    ax6.set_ylim(100, 150)
    ax6.legend(fontsize=8)
    ax6.grid(True, alpha=0.3)
    
    save_matplotlib_figure(fig, 'analisis_temporal_real_2024.png')
    print("✅ Gráfica guardada: analisis_temporal_real_2024.png")
    plt.close(fig)


def main():
    """Función principal."""
    print("\n" + "="*80)
    print("📊 GENERADOR: Gráficas Solares con DATOS REALES de solar_pvlib")
    print("="*80 + "\n")
    
    # Cargar ÚNICAMENTE datos reales
    df = load_real_solar_data()
    
    # Generar todas las gráficas con datos reales
    generate_dia_despejado_real(df)
    generate_resumen_real(df)
    generate_temporal_analysis_real(df)
    
    print("\n" + "="*80)
    print("✅ PROCESO COMPLETADO")
    print("="*80)
    print("\nGráficas generadas (DATOS REALES ÚNICAMENTE):")
    print("   1. dia_despejado_real_2024.png")
    print("   2. sistema_fv_iquitos_resumen_real_2024.png")
    print("   3. analisis_temporal_real_2024.png")
    print("\nTodas las gráficas usan exclusivamente datos de pv_generation_hourly_citylearn_v2.csv")
    print("generados por solar_pvlib (SIN datos artificiales ni inventados)")
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()
