#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regeneración de Gráficas Complementarias - Datos Reales solar_pvlib
================================================================================

Regenera gráficas complementarias:
1. Solar Profile Visualization (9 paneles)
2. Análisis Temporal Avanzado (6 paneles)
3. Comparación de Escenarios
4. Día Despejado Representativo
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
from matplotlib.gridspec import GridSpec

rcParams['font.size'] = 8
rcParams['axes.labelsize'] = 8
rcParams['axes.titlesize'] = 9
rcParams['xtick.labelsize'] = 7
rcParams['ytick.labelsize'] = 7
rcParams['legend.fontsize'] = 7


def load_real_solar_data():
    """Carga datos REALES de solar_pvlib."""
    csv_path = Path(__file__).parent.parent / 'data' / 'oe2' / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
    df = pd.read_csv(csv_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df


def solar_profile_visualization(df):
    """Gráfica: Solar Profile Visualization (9 paneles)."""
    print("  📊 Regenerando: Solar Profile Visualization (9 paneles)...")
    
    df['hour'] = df['datetime'].dt.hour
    df['date'] = df['datetime'].dt.date
    df['month'] = df['datetime'].dt.month
    
    hourly_avg = df.groupby('hour')['ac_power_kw'].mean()
    monthly_energy = df.groupby('month')['ac_energy_kwh'].sum() / 1000
    daily_energy = df.groupby('date')['ac_energy_kwh'].sum()
    
    fig = plt.figure(figsize=(16, 14))
    gs = GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.3)
    fig.suptitle('Solar Profile Visualization - Iquitos 2024', fontsize=14, fontweight='bold')
    
    # 1: Perfil potencia 24h
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(hourly_avg.index, hourly_avg.values, marker='o', linewidth=2, markersize=6, color='steelblue')
    ax.fill_between(hourly_avg.index, hourly_avg.values, alpha=0.3, color='steelblue')
    ax.set_title('Perfil Potencia 24h', fontsize=9, fontweight='bold')
    ax.set_ylabel('Potencia [kW]', fontsize=8)
    ax.set_xlim(0, 23)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 4))
    
    # 2: Energía mensual
    ax = fig.add_subplot(gs[0, 1])
    months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    ax.bar(range(12), monthly_energy.values, color='orange', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax.set_title('Energía Mensual', fontsize=9, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=8)
    ax.set_xticks(range(12))
    ax.set_xticklabels(months, fontsize=7, rotation=45)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3: Distribución diaria
    ax = fig.add_subplot(gs[0, 2])
    ax.hist(daily_energy.values, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(daily_energy.mean(), color='red', linestyle='--', linewidth=2, label=f'Media: {daily_energy.mean():.0f}')
    ax.set_title('Distribucion Energía Diaria', fontsize=9, fontweight='bold')
    ax.set_xlabel('Energía [kWh]', fontsize=8)
    ax.set_ylabel('Frecuencia', fontsize=8)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4: GHI
    ax = fig.add_subplot(gs[1, 0])
    ax.hist(df['ghi_wm2'].values, bins=40, color='orange', alpha=0.7, edgecolor='black')
    ax.set_title('GHI - Global Horizontal', fontsize=9, fontweight='bold')
    ax.set_xlabel('GHI [W/m²]', fontsize=8)
    ax.set_ylabel('Frecuencia', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 5: Correlación GHI-Potencia
    ax = fig.add_subplot(gs[1, 1])
    ax.scatter(df['ghi_wm2'], df['ac_power_kw'], alpha=0.2, s=5)
    ax.set_title('Correlación GHI - Potencia', fontsize=9, fontweight='bold')
    ax.set_xlabel('GHI [W/m²]', fontsize=8)
    ax.set_ylabel('Potencia [kW]', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 6: Temperatura promedio
    ax = fig.add_subplot(gs[1, 2])
    monthly_temp = df.groupby('month')['temp_air_c'].mean()
    ax.bar(range(1, 13), monthly_temp.values, color='red', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax.set_title('Temperatura Promedio Mensual', fontsize=9, fontweight='bold')
    ax.set_ylabel('Temperatura [°C]', fontsize=8)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(months, fontsize=7, rotation=45)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 7: Heatmap mensual-horaria
    ax = fig.add_subplot(gs[2, :2])
    heatmap = df.groupby(['month', 'hour'])['ac_power_kw'].mean().unstack(fill_value=0)
    im = ax.imshow(heatmap.values, aspect='auto', cmap='YlOrRd', origin='lower')
    ax.set_title('Heatmap: Potencia Mensual-Horaria', fontsize=9, fontweight='bold')
    ax.set_xlabel('Hora del día', fontsize=8)
    ax.set_ylabel('Mes', fontsize=8)
    ax.set_xticks(np.arange(0, 24, 4))
    ax.set_yticks(range(12))
    ax.set_yticklabels(months, fontsize=7)
    plt.colorbar(im, ax=ax, label='kW')
    
    # 8: KPI resumen
    ax = fig.add_subplot(gs[2, 2])
    ax.axis('off')
    annual_energy = df['ac_energy_kwh'].sum()
    max_power = df['ac_power_kw'].max()
    cf = (df['ac_power_kw'].mean() * 24 * 365) / (3201 * 1000)
    
    kpi_text = (f"RESUMEN ANUAL\n\n"
               f"Energía: {annual_energy/1e6:.2f} GWh\n"
               f"Pot.Máx: {max_power:.0f} kW\n"
               f"CF: {cf*100:.1f}%\n"
               f"GHI: {df['ghi_wm2'].sum()/1000:.0f} kWh/m²")
    ax.text(0.5, 0.5, kpi_text, ha='center', va='center', fontsize=9, fontweight='bold',
           transform=ax.transAxes, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    
    save_matplotlib_figure(fig, 'solar_profile_visualization_2024.png', subdir='solar')
    plt.close(fig)


def analisis_temporal_avanzado(df):
    """Gráfica: Análisis Temporal Avanzado (6 paneles)."""
    print("  ⏰ Regenerando: Análisis Temporal Avanzado (6 paneles)...")
    
    df['hour'] = df['datetime'].dt.hour
    df['month'] = df['datetime'].dt.month
    df['date'] = df['datetime'].dt.date
    df['trimestre'] = df['datetime'].dt.quarter
    
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    fig.suptitle('Análisis Temporal Avanzado - 2024', fontsize=13, fontweight='bold')
    
    # 1: Heatmap 24h x 12 meses
    ax = fig.add_subplot(gs[0, 0])
    heatmap = df.groupby(['month', 'hour'])['ac_power_kw'].mean().unstack(fill_value=0)
    im = ax.imshow(heatmap.values, aspect='auto', cmap='YlOrRd', origin='lower')
    ax.set_title('Potencia Mensual-Horaria [kW]', fontsize=10, fontweight='bold')
    ax.set_xlabel('Hora', fontsize=8)
    ax.set_ylabel('Mes', fontsize=8)
    ax.set_xticks(np.arange(0, 24, 4))
    ax.set_yticks(range(12))
    ax.set_yticklabels(['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'], fontsize=8)
    plt.colorbar(im, ax=ax)
    
    # 2: Box plot por mes
    ax = fig.add_subplot(gs[0, 1])
    monthly_data = [df[df['month'] == m]['ac_power_kw'].values for m in range(1, 13)]
    bp = ax.boxplot(monthly_data, labels=['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'])  # type: ignore
    ax.set_title('Distribución Potencia Mensual', fontsize=10, fontweight='bold')
    ax.set_ylabel('Potencia [kW]', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3: Energía por trimestre
    ax = fig.add_subplot(gs[0, 2])
    trimestral = df.groupby('trimestre')['ac_energy_kwh'].sum() / 1000
    bars = ax.bar([f'Q{i}' for i in range(1, 5)], trimestral.values, color=['#FF6B6B', '#4ECDC4', '#95E1D3', '#FFE66D'], 
                  alpha=0.7, edgecolor='black', linewidth=1)
    for bar, val in zip(bars, trimestral.values):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:.0f}', ha='center', va='bottom', fontsize=8)
    ax.set_title('Energía por Trimestre [MWh]', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4: Variabilidad diaria
    ax = fig.add_subplot(gs[1, 0])
    daily_energy = df.groupby('date')['ac_energy_kwh'].sum()
    ax.plot(daily_energy.values, linewidth=0.8, color='steelblue', alpha=0.7)
    ax.fill_between(range(len(daily_energy)), daily_energy.values, alpha=0.2, color='steelblue')
    ax.set_title('Energía Diaria (Variabilidad)', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [kWh]', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 5: Distribución potencia
    ax = fig.add_subplot(gs[1, 1])
    ax.hist(df['ac_power_kw'].values, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(df['ac_power_kw'].mean(), color='red', linestyle='--', linewidth=2, label='Media')
    ax.axvline(df['ac_power_kw'].max(), color='green', linestyle='--', linewidth=2, label='Máximo')
    ax.set_title('Distribución Potencia AC', fontsize=10, fontweight='bold')
    ax.set_xlabel('Potencia [kW]', fontsize=8)
    ax.set_ylabel('Frecuencia', fontsize=8)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 6: Performance Ratio mensual
    ax = fig.add_subplot(gs[1, 2])
    monthly_energy = df.groupby('month')['ac_energy_kwh'].sum()
    monthly_ghi = df.groupby('month')['ghi_wm2'].sum() / 1000
    pr_monthly = (monthly_energy / 1e6) / (4.0496 * (monthly_ghi / 100))  # Approximate PR
    ax.bar(range(1, 13), pr_monthly.values, color='gold', alpha=0.7, edgecolor='black', linewidth=1)
    ax.axhline(1.0, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Ref: 1.0')
    ax.set_title('Performance Ratio Mensual', fontsize=10, fontweight='bold')
    ax.set_ylabel('PR', fontsize=8)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'], fontsize=8)
    ax.set_ylim(0.8, 1.4)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    
    save_matplotlib_figure(fig, 'analisis_temporal_avanzado_2024.png', subdir='solar')
    plt.close(fig)


def comparacion_escenarios(df):
    """Gráfica: Comparación de Escenarios (6 paneles)."""
    print("  📊 Regenerando: Comparación de Escenarios...")
    
    df['hour'] = df['datetime'].dt.hour
    df['date'] = df['datetime'].dt.date
    df['month'] = df['datetime'].dt.month
    
    # Escenarios reales basados en datos solar_pvlib
    scenario_real = df.copy()
    
    # Escenario optimista (simulado): +10% sobre real
    scenario_optimista = df.copy()
    scenario_optimista['ac_power_kw'] = scenario_optimista['ac_power_kw'] * 1.10
    scenario_optimista['ac_energy_kwh'] = scenario_optimista['ac_energy_kwh'] * 1.10
    
    # Escenario pesimista (simulado): -10% sobre real
    scenario_pesimista = df.copy()
    scenario_pesimista['ac_power_kw'] = scenario_pesimista['ac_power_kw'] * 0.90
    scenario_pesimista['ac_energy_kwh'] = scenario_pesimista['ac_energy_kwh'] * 0.90
    
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    fig.suptitle('Comparación de Escenarios Operacionales - 2024', fontsize=13, fontweight='bold')
    
    # 1: Potencia promedio
    ax = fig.add_subplot(gs[0, 0])
    scenarios = ['Real', 'Optimista\n(+10%)', 'Pesimista\n(-10%)']
    powers = [
        scenario_real['ac_power_kw'].mean(),
        scenario_optimista['ac_power_kw'].mean(),
        scenario_pesimista['ac_power_kw'].mean()
    ]
    bars = ax.bar(scenarios, powers, color=['steelblue', 'green', 'red'], alpha=0.7, edgecolor='black', linewidth=1)
    for bar, val in zip(bars, powers):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    ax.set_title('Potencia Promedio Comparada', fontsize=10, fontweight='bold')
    ax.set_ylabel('Potencia [kW]', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 2: Energía acumulada
    ax = fig.add_subplot(gs[0, 1])
    energies = [
        scenario_real['ac_energy_kwh'].sum() / 1e6,
        scenario_optimista['ac_energy_kwh'].sum() / 1e6,
        scenario_pesimista['ac_energy_kwh'].sum() / 1e6
    ]
    bars = ax.bar(scenarios, energies, color=['steelblue', 'green', 'red'], alpha=0.7, edgecolor='black', linewidth=1)
    for bar, val in zip(bars, energies):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:.2f}', ha='center', va='bottom', fontsize=9)
    ax.set_title('Energía Anual Comparada', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [GWh]', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3: Irradiancia
    ax = fig.add_subplot(gs[0, 2])
    ax.plot(scenario_real.groupby('hour')['ghi_wm2'].mean().index, 
           scenario_real.groupby('hour')['ghi_wm2'].mean().values, marker='o', label='Real', linewidth=2)
    ax.fill_between(scenario_real.groupby('hour')['ghi_wm2'].mean().index,
                   scenario_real.groupby('hour')['ghi_wm2'].mean().values, alpha=0.3)
    ax.set_title('Perfil GHI Horario Promedio', fontsize=10, fontweight='bold')
    ax.set_xlabel('Hora', fontsize=8)
    ax.set_ylabel('GHI [W/m²]', fontsize=8)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    
    # 4: Energía mensual por escenario
    ax = fig.add_subplot(gs[1, 0])
    months = ['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
    x = np.arange(len(months))
    w = 0.25
    
    real_m = scenario_real.groupby('month')['ac_energy_kwh'].sum() / 1000
    opt_m = scenario_optimista.groupby('month')['ac_energy_kwh'].sum() / 1000
    pes_m = scenario_pesimista.groupby('month')['ac_energy_kwh'].sum() / 1000
    
    ax.bar(x - w, real_m.values, w, label='Real', color='steelblue', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax.bar(x, opt_m.values, w, label='Optimista', color='green', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax.bar(x + w, pes_m.values, w, label='Pesimista', color='red', alpha=0.7, edgecolor='black', linewidth=0.5)
    
    ax.set_title('Energía Mensual por Escenario', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=8)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 5: Máxima energía/potencia
    ax = fig.add_subplot(gs[1, 1])
    max_data = {
        'Potencia': [
            scenario_real['ac_power_kw'].max(),
            scenario_optimista['ac_power_kw'].max(),
            scenario_pesimista['ac_power_kw'].max()
        ],
        'Energía\n(MWh)': [
            scenario_real['ac_energy_kwh'].max() / 1000,
            scenario_optimista['ac_energy_kwh'].max() / 1000,
            scenario_pesimista['ac_energy_kwh'].max() / 1000
        ]
    }
    
    x = np.arange(len(scenarios))
    w = 0.35
    
    p1 = ax.bar(x - w/2, max_data['Potencia'], w, label='Potencia Máx [kW]', color='orange', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax2 = ax.twinx()
    p2 = ax2.bar(x + w/2, max_data['Energía\n(MWh)'], w, label='Energía Máx [MWh]', color='purple', alpha=0.7, edgecolor='black', linewidth=0.5)
    
    ax.set_title('Máximos por Escenario', fontsize=10, fontweight='bold')
    ax.set_ylabel('Potencia Máx [kW]', fontsize=8, color='orange')
    ax2.set_ylabel('Energía Máx [MWh]', fontsize=8, color='purple')
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 6: Tabla resumen
    ax = fig.add_subplot(gs[1, 2])
    ax.axis('off')
    
    table_data = [
        ['Métrica', 'Real', 'Optimista', 'Pesimista'],
        ['Energía [GWh]', f'{energies[0]:.2f}', f'{energies[1]:.2f}', f'{energies[2]:.2f}'],
        ['Pot.Máx [kW]', f'{powers[0]:.0f}', f'{powers[1]:.0f}', f'{powers[2]:.0f}'],
        ['Pot.Prom [kW]', f'{scenario_real["ac_power_kw"].mean():.0f}', f'{scenario_optimista["ac_power_kw"].mean():.0f}', f'{scenario_pesimista["ac_power_kw"].mean():.0f}']
    ]
    
    table = ax.table(cellText=table_data, cellLoc='center', loc='center', colWidths=[0.25, 0.25, 0.25, 0.25])
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 2)
    
    for i in range(len(table_data)):
        for j in range(len(table_data[0])):
            cell = table[(i, j)]
            if i == 0:
                cell.set_facecolor('#B0E0E6')
                cell.set_text_props(weight='bold')
            else:
                cell.set_facecolor('lightyellow' if j == 1 else 'lightgreen' if j == 2 else 'lightcoral')
    
    ax.text(0.5, 1.15, 'Tabla Resumen de Escenarios', ha='center', fontsize=10, fontweight='bold', transform=ax.transAxes)
    
    save_matplotlib_figure(fig, 'escenarios_comparacion_2024.png', subdir='solar')
    plt.close(fig)


def dia_despejado_representativo(df):
    """Gráfica: Día Despejado Representativo."""
    print("  ☀️  Regenerando: Día Despejado Representativo...")
    
    # Buscar día con máximo GHI
    df['date'] = df['datetime'].dt.date
    daily_ghi = df.groupby('date')['ghi_wm2'].sum()
    max_ghi_date = daily_ghi.idxmax()
    
    day_data = df[df['date'] == max_ghi_date].copy()
    day_data['time_str'] = day_data['datetime'].dt.strftime('%H:%M')
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
    fig.suptitle(f'Día Despejado Representativo - {max_ghi_date} (Máximo GHI)', fontsize=12, fontweight='bold')
    
    # Panel 1: Energía 15min como barras
    ax1.bar(range(len(day_data)), day_data['ac_energy_kwh'].values, color='steelblue', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax1.set_title('Energía por Hora (Valores Horarios)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Energía [kWh]', fontsize=10)
    ax1.set_xlabel('Hora del día', fontsize=10)
    ax1.grid(True, alpha=0.3, axis='y')
    
    if len(day_data) <= 24:
        ax1.set_xticks(range(0, len(day_data), 1))
        ax1.set_xticklabels([f'{i:02d}' for i in range(len(day_data))], fontsize=9)
    
    # Panel 2: Potencia AC como línea
    ax2.plot(range(len(day_data)), day_data['ac_power_kw'].values, marker='o', 
            linewidth=2.5, markersize=6, color='darkgreen', label='Potencia AC')
    ax2.fill_between(range(len(day_data)), day_data['ac_power_kw'].values, alpha=0.3, color='darkgreen')
    
    ax2.set_title('Potencia AC Horaria', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Potencia [kW]', fontsize=10)
    ax2.set_xlabel('Hora del día', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=9)
    
    if len(day_data) <= 24:
        ax2.set_xticks(range(0, len(day_data), 1))
        ax2.set_xticklabels([f'{i:02d}' for i in range(len(day_data))], fontsize=9)
    
    plt.tight_layout()
    save_matplotlib_figure(fig, 'dia_despejado_representativo_2024.png', subdir='solar')
    plt.close(fig)


def main():
    """Función principal."""
    print("\n" + "="*100)
    print("📊 REGENERADOR: Gráficas Complementarias - Datos Reales solar_pvlib")
    print("="*100 + "\n")
    
    print("📊 Cargando datos de solar_pvlib...")
    df = load_real_solar_data()
    print(f"✅ {len(df)} puntos cargados\n")
    
    print("📈 REGENERANDO GRÁFICAS COMPLEMENTARIAS:\n")
    
    solar_profile_visualization(df)
    analisis_temporal_avanzado(df)
    comparacion_escenarios(df)
    dia_despejado_representativo(df)
    
    print("\n" + "="*100)
    print("✅ REGENERACIÓN COMPLETADA")
    print("="*100)
    print("\n4 gráficas complementarias regeneradas con datos REALES")
    print("Ubicación: outputs/analysis/solar/\n")
    print("="*100 + "\n")


if __name__ == '__main__':
    main()
