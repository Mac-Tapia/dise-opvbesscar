#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regeneración Master: Todas las Gráficas en Raíz - Datos Reales solar_pvlib
================================================================================

Regenera TODAS las gráficas solares en la raíz de outputs/analysis/solar/:
- SIN subdirectorios (profiles/, heatmaps/, etc.)
- SOLO datos REALES de solar_pvlib
- Todos los paneles originales
- Actualización completa con datos 2024

Ejecución:
    python scripts/regenerate_all_graphics_root.py
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

rcParams['font.size'] = 9
rcParams['axes.labelsize'] = 9
rcParams['axes.titlesize'] = 10
rcParams['xtick.labelsize'] = 8
rcParams['ytick.labelsize'] = 8
rcParams['legend.fontsize'] = 8


def load_real_solar_data():
    """Carga datos REALES únicos de solar_pvlib."""
    csv_path = Path(__file__).parent.parent / 'data' / 'oe2' / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
    df = pd.read_csv(csv_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df


def generate_all_graphics_root(df):
    """Genera TODAS las gráficas en la raíz de outputs/analysis/solar/"""
    
    print("\n📊 REGENERANDO TODAS LAS GRÁFICAS EN RAÍZ (SIN SUBDIRECTORIOS):")
    print("=" * 90)
    
    df['hour'] = df['datetime'].dt.hour
    df['date'] = df['datetime'].dt.date
    df['month'] = df['datetime'].dt.month
    
    # ========================================================================
    # 1. PERFIL POTENCIA 24H
    # ========================================================================
    print("\n  1️⃣  Perfil Potencia 24h...")
    hourly_avg = df.groupby('hour')['ac_power_kw'].mean()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(hourly_avg.index, hourly_avg.values, marker='o', linewidth=2.5, markersize=8, color='steelblue')
    ax.fill_between(hourly_avg.index, hourly_avg.values, alpha=0.3, color='steelblue')
    ax.set_title('Perfil de Potencia 24 Horas - Promedio 2024', fontsize=12, fontweight='bold')
    ax.set_xlabel('Hora del día', fontsize=10)
    ax.set_ylabel('Potencia [kW]', fontsize=10)
    ax.set_xlim(0, 23)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    save_matplotlib_figure(fig, '01_perfil_potencia_24h.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 2. ENERGÍA MENSUAL
    # ========================================================================
    print("  2️⃣  Energía Mensual...")
    monthly = df.groupby('month')['ac_energy_kwh'].sum() / 1000
    
    fig, ax = plt.subplots(figsize=(12, 6))
    months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    bars = ax.bar(range(len(monthly)), monthly.values, color='steelblue', alpha=0.7, edgecolor='black', linewidth=1)
    
    for barra, val in zip(bars, monthly.values):
        ax.text(barra.get_x() + barra.get_width()/2., barra.get_height(),
               f'{val:.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax.set_title('Energía Mensual - 2024', fontsize=12, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=10)
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months)
    ax.set_ylim(0, monthly.max() * 1.15)
    ax.grid(True, alpha=0.3, axis='y')
    
    save_matplotlib_figure(fig, '02_energia_mensual.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 3. DISTRIBUCIÓN ENERGÍA DIARIA
    # ========================================================================
    print("  3️⃣  Distribución Energía Diaria...")
    daily = df.groupby('date')['ac_energy_kwh'].sum()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(daily.values, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(daily.mean(), color='red', linestyle='--', linewidth=2, label=f'Media: {daily.mean():.0f}')
    ax.axvline(daily.median(), color='green', linestyle='--', linewidth=2, label=f'Mediana: {daily.median():.0f}')
    
    ax.set_title('Distribución de Energía Diaria - 2024', fontsize=12, fontweight='bold')
    ax.set_xlabel('Energía [kWh]', fontsize=10)
    ax.set_ylabel('Frecuencia [días]', fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    
    save_matplotlib_figure(fig, '03_distribucion_energia_diaria.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 4. ANÁLISIS IRRADIANCIA (4 PANELES)
    # ========================================================================
    print("  4️⃣  Análisis Irradiancia (4 paneles)...")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Análisis de Irradiancia - 2024', fontsize=12, fontweight='bold')
    
    axes[0, 0].hist(df['ghi_wm2'].values, bins=50, color='orange', alpha=0.7, edgecolor='black')
    axes[0, 0].set_title('GHI - Global Horizontal Irradiance', fontsize=10, fontweight='bold')
    axes[0, 0].set_xlabel('GHI [W/m²]', fontsize=9)
    axes[0, 0].set_ylabel('Frecuencia', fontsize=9)
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    
    axes[0, 1].hist(df['dni_wm2'].values, bins=50, color='red', alpha=0.7, edgecolor='black')
    axes[0, 1].set_title('DNI - Direct Normal Irradiance', fontsize=10, fontweight='bold')
    axes[0, 1].set_xlabel('DNI [W/m²]', fontsize=9)
    axes[0, 1].set_ylabel('Frecuencia', fontsize=9)
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    
    axes[1, 0].hist(df['dhi_wm2'].values, bins=50, color='blue', alpha=0.7, edgecolor='black')
    axes[1, 0].set_title('DHI - Diffuse Horizontal Irradiance', fontsize=10, fontweight='bold')
    axes[1, 0].set_xlabel('DHI [W/m²]', fontsize=9)
    axes[1, 0].set_ylabel('Frecuencia', fontsize=9)
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    
    axes[1, 1].scatter(df['ghi_wm2'], df['ac_power_kw'], alpha=0.3, s=10, label='GHI vs Potencia')
    axes[1, 1].set_title('Correlación GHI - Potencia AC', fontsize=10, fontweight='bold')
    axes[1, 1].set_xlabel('GHI [W/m²]', fontsize=9)
    axes[1, 1].set_ylabel('Potencia AC [kW]', fontsize=9)
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].legend(fontsize=8)
    
    plt.tight_layout()
    save_matplotlib_figure(fig, '04_analisis_irradiancia.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 5. HEATMAP MENSUAL-HORARIA
    # ========================================================================
    print("  5️⃣  Heatmap Potencia Mensual-Horaria...")
    
    heatmap_data = df.groupby(['month', 'hour'])['ac_power_kw'].mean().unstack(fill_value=0)
    
    fig, ax = plt.subplots(figsize=(14, 8))
    im = ax.imshow(heatmap_data.values, aspect='auto', cmap='YlOrRd', origin='lower')
    
    ax.set_xlabel('Hora del día', fontsize=10)
    ax.set_ylabel('Mes', fontsize=10)
    ax.set_xticks(np.arange(0, 24, 2))
    ax.set_xticklabels([f'{i:02d}' for i in range(0, 24, 2)], fontsize=9)
    ax.set_yticks(np.arange(12))
    ax.set_yticklabels(['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'], fontsize=9)
    
    ax.set_title('Heatmap: Potencia Promedio Mensual-Horaria - 2024', fontsize=12, fontweight='bold')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Potencia [kW]', fontsize=9)
    
    save_matplotlib_figure(fig, '05_heatmap_potencia_mensual_horaria.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 6. HEATMAP DIARIA-HORARIA (60 DÍAS)
    # ========================================================================
    print("  6️⃣  Heatmap Diaria-Horaria (60 días)...")
    
    df_60 = df.head(60 * 24)
    df_60_copy = df_60.copy()
    df_60_copy['day'] = df_60_copy['datetime'].dt.day
    heatmap_data_60 = df_60_copy.groupby(['day', 'hour'])['ac_power_kw'].mean().unstack(fill_value=0)
    
    fig, ax = plt.subplots(figsize=(14, 10))
    im = ax.imshow(heatmap_data_60.values, aspect='auto', cmap='viridis', origin='lower')
    
    ax.set_xlabel('Hora del día', fontsize=10)
    ax.set_ylabel('Día', fontsize=10)
    ax.set_xticks(np.arange(0, 24, 2))
    ax.set_xticklabels([f'{i:02d}' for i in range(0, 24, 2)], fontsize=9)
    ax.set_yticks(np.arange(0, 60, 5))
    ax.set_yticklabels(np.arange(0, 60, 5), fontsize=8)
    
    ax.set_title('Heatmap: Potencia Diaria-Horaria (60 días)', fontsize=12, fontweight='bold')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Potencia [kW]', fontsize=9)
    
    save_matplotlib_figure(fig, '06_heatmap_diaria_horaria_60dias.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 7. MÉTRICAS DESEMPEÑO (4 KPIs)
    # ========================================================================
    print("  7️⃣  Métricas Desempeño (4 KPIs)...")
    
    annual_energy = df['ac_energy_kwh'].sum()
    max_power = df['ac_power_kw'].max()
    avg_power = df['ac_power_kw'].mean()
    cf = (avg_power * 24 * 365) / (3201 * 1000)
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Métricas de Desempeño - 2024', fontsize=12, fontweight='bold')
    
    axes[0, 0].text(0.5, 0.5, f'{annual_energy/1e6:.2f}\nGWh/año', ha='center', va='center', fontsize=14, fontweight='bold',
           transform=axes[0, 0].transAxes, bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    axes[0, 0].set_title('Energía Anual', fontsize=10, fontweight='bold')
    axes[0, 0].axis('off')
    
    axes[0, 1].text(0.5, 0.5, f'{max_power:.0f}\nkW', ha='center', va='center', fontsize=14, fontweight='bold',
           transform=axes[0, 1].transAxes, bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
    axes[0, 1].set_title('Potencia Máxima', fontsize=10, fontweight='bold')
    axes[0, 1].axis('off')
    
    axes[1, 0].text(0.5, 0.5, f'{avg_power:.0f}\nkW', ha='center', va='center', fontsize=14, fontweight='bold',
           transform=axes[1, 0].transAxes, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    axes[1, 0].set_title('Potencia Promedio', fontsize=10, fontweight='bold')
    axes[1, 0].axis('off')
    
    axes[1, 1].text(0.5, 0.5, f'{cf*100:.1f}%', ha='center', va='center', fontsize=14, fontweight='bold',
           transform=axes[1, 1].transAxes, bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))
    axes[1, 1].set_title('Capacity Factor', fontsize=10, fontweight='bold')
    axes[1, 1].axis('off')
    
    save_matplotlib_figure(fig, '07_metricas_desempenio.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 8. EFECTO TEMPERATURA-POTENCIA
    # ========================================================================
    print("  8️⃣  Efecto Temperatura-Potencia...")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    scatter = ax.scatter(df['temp_air_c'], df['ac_power_kw'], alpha=0.3, s=10, c=df['ghi_wm2'], cmap='hot')
    
    ax.set_title('Efecto Temperatura en Potencia - 2024', fontsize=12, fontweight='bold')
    ax.set_xlabel('Temperatura [°C]', fontsize=10)
    ax.set_ylabel('Potencia AC [kW]', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('GHI [W/m²]', fontsize=9)
    
    save_matplotlib_figure(fig, '08_efectotemperatura_potencia.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 9. ANÁLISIS VARIABILIDAD CLIMÁTICA (4 PANELES)
    # ========================================================================
    print("  9️⃣  Análisis Variabilidad Climática...")
    
    daily_ghi = df.groupby('date')['ghi_wm2'].sum()
    daily_power = df.groupby('date')['ac_power_kw'].mean()
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Análisis Variabilidad Climática - 2024', fontsize=12, fontweight='bold')
    
    axes[0, 0].plot(daily_ghi.values, linewidth=1, color='orange')
    axes[0, 0].fill_between(range(len(daily_ghi)), daily_ghi.values, alpha=0.3, color='orange')
    axes[0, 0].set_title('GHI Diario', fontsize=10, fontweight='bold')
    axes[0, 0].set_ylabel('GHI [Wh/m²]', fontsize=9)
    axes[0, 0].grid(True, alpha=0.3)
    
    axes[0, 1].plot(daily_power.values, linewidth=1, color='steelblue')
    axes[0, 1].fill_between(range(len(daily_power)), daily_power.values, alpha=0.3, color='steelblue')
    axes[0, 1].set_title('Potencia Promedio Diaria', fontsize=10, fontweight='bold')
    axes[0, 1].set_ylabel('Potencia [kW]', fontsize=9)
    axes[0, 1].grid(True, alpha=0.3)
    
    monthly_temp = df.groupby('month')['temp_air_c'].mean()
    axes[1, 0].bar(range(len(monthly_temp)), monthly_temp.values, color='red', alpha=0.7)
    axes[1, 0].set_title('Temperatura Promedio Mensual', fontsize=10, fontweight='bold')
    axes[1, 0].set_ylabel('Temperatura [°C]', fontsize=9)
    axes[1, 0].set_xticks(range(12))
    axes[1, 0].set_xticklabels(['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'], fontsize=8)
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    
    monthly_wind = df.groupby('month')['wind_speed_ms'].mean()
    axes[1, 1].bar(range(len(monthly_wind)), monthly_wind.values, color='cyan', alpha=0.7)
    axes[1, 1].set_title('Velocidad Viento Promedio Mensual', fontsize=10, fontweight='bold')
    axes[1, 1].set_ylabel('Velocidad [m/s]', fontsize=9)
    axes[1, 1].set_xticks(range(12))
    axes[1, 1].set_xticklabels(['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'], fontsize=8)
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    save_matplotlib_figure(fig, '09_analisis_variabilidad_climatica.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 10. RESUMEN COMPLETO SISTEMA
    # ========================================================================
    print("  ✅ Resumen Completo Sistema...")
    
    daily_energy = df.groupby('date')['ac_energy_kwh'].sum() / 1000
    monthly_energy = df.groupby('month')['ac_energy_kwh'].sum() / 1000
    hourly_energy = df.groupby('hour')['ac_energy_kwh'].sum()
    
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3)
    fig.suptitle('Resumen Completo del Sistema FV Iquitos - 2024', fontsize=14, fontweight='bold')
    
    ax = fig.add_subplot(gs[0, :2])
    ax.bar(range(len(daily_energy)), daily_energy.values, color='steelblue', alpha=0.6, width=0.8)
    ax.axhline(daily_energy.mean(), color='red', linestyle='--', linewidth=2, label=f'Promedio: {daily_energy.mean():.1f}')
    ax.set_title('Energía Diaria', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=9)
    ax.set_xlim(0, len(daily_energy))
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    ax = fig.add_subplot(gs[0, 2])
    months_list = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    bars = ax.bar(range(len(monthly_energy)), monthly_energy.values, color='steelblue', alpha=0.7, edgecolor='black')
    for b, v in zip(bars, monthly_energy.values):
        ax.text(b.get_x() + b.get_width()/2., b.get_height(), f'{v:.0f}', ha='center', va='bottom', fontsize=7)
    ax.set_title('Energía Mensual', fontsize=10, fontweight='bold')
    ax.set_ylabel('[MWh]', fontsize=8)
    ax.set_xticks(range(len(months_list)))
    ax.set_xticklabels(months_list, fontsize=7, rotation=45)
    ax.grid(True, alpha=0.3, axis='y')
    
    ax = fig.add_subplot(gs[1, 0])
    ax.hist(daily_energy.values, bins=25, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(daily_energy.mean(), color='red', linestyle='--', linewidth=2, label='Media')
    ax.set_title('Distribución Energía Diaria', fontsize=10, fontweight='bold')
    ax.set_xlabel('Energía [MWh]', fontsize=8)
    ax.set_ylabel('Frecuencia', fontsize=8)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    
    ax = fig.add_subplot(gs[1, 1:])
    ax.bar(range(24), hourly_energy.values / 1000, color='orange', alpha=0.7, edgecolor='black')
    ax.set_title('Distribución Energía por Hora del Día', fontsize=10, fontweight='bold')
    ax.set_xlabel('Hora del día', fontsize=8)
    ax.set_ylabel('Energía [MWh]', fontsize=8)
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3, axis='y')
    
    ax = fig.add_subplot(gs[2, :])
    ax.axis('off')
    
    kpi_text = (f"MÉTRICAS ANUALES 2024\n"
               f"Energía: {annual_energy/1e6:.2f} GWh  |  "
               f"Potencia Máx: {max_power:.0f} kW  |  "
               f"GHI: {df['ghi_wm2'].sum()/1000:.1f} kWh/m²  |  "
               f"CF: {(annual_energy/1e6*1000)/(3201*365/1000):.1f}%")
    
    ax.text(0.5, 0.5, kpi_text, ha='center', va='center', fontsize=11, fontweight='bold',
           transform=ax.transAxes, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    save_matplotlib_figure(fig, '10_resumen_completo_sistema.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 11. SOLAR PROFILE VISUALIZATION (9 PANELES)
    # ========================================================================
    print("  1️⃣1️⃣ Solar Profile Visualization (9 paneles)...")
    
    # (Código para 9 paneles completos)
    fig = plt.figure(figsize=(16, 14))
    gs_sub = GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.3)
    fig.suptitle('Solar Profile Visualization - Iquitos 2024', fontsize=14, fontweight='bold')
    
    # 1: Perfil 24h
    ax = fig.add_subplot(gs_sub[0, 0])
    ax.plot(hourly_avg.index, hourly_avg.values, marker='o', linewidth=2, markersize=6, color='steelblue')
    ax.fill_between(hourly_avg.index, hourly_avg.values, alpha=0.3, color='steelblue')
    ax.set_title('Perfil Potencia 24h', fontsize=9, fontweight='bold')
    ax.set_ylabel('Potencia [kW]', fontsize=8)
    ax.set_xlim(0, 23)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 4))
    
    # 2: Energía mensual
    ax = fig.add_subplot(gs_sub[0, 1])
    ax.bar(range(12), monthly_energy.values, color='orange', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax.set_title('Energía Mensual', fontsize=9, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=8)
    ax.set_xticks(range(12))
    ax.set_xticklabels(months_list, fontsize=7, rotation=45)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3: Distribución
    ax = fig.add_subplot(gs_sub[0, 2])
    ax.hist(daily_energy.values, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(daily_energy.mean(), color='red', linestyle='--', linewidth=2, label=f'Media')
    ax.set_title('Distribución Energía Diaria', fontsize=9, fontweight='bold')
    ax.set_xlabel('Energía [MWh]', fontsize=8)
    ax.set_ylabel('Frecuencia', fontsize=8)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4: GHI
    ax = fig.add_subplot(gs_sub[1, 0])
    ax.hist(df['ghi_wm2'].values, bins=40, color='orange', alpha=0.7, edgecolor='black')
    ax.set_title('GHI - Global Horizontal', fontsize=9, fontweight='bold')
    ax.set_xlabel('GHI [W/m²]', fontsize=8)
    ax.set_ylabel('Frecuencia', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 5: Correlación
    ax = fig.add_subplot(gs_sub[1, 1])
    ax.scatter(df['ghi_wm2'], df['ac_power_kw'], alpha=0.2, s=5)
    ax.set_title('Correlación GHI - Potencia', fontsize=9, fontweight='bold')
    ax.set_xlabel('GHI [W/m²]', fontsize=8)
    ax.set_ylabel('Potencia [kW]', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 6: Temperatura
    ax = fig.add_subplot(gs_sub[1, 2])
    ax.bar(range(1, 13), monthly_temp.values, color='red', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax.set_title('Temperatura Promedio Mensual', fontsize=9, fontweight='bold')
    ax.set_ylabel('Temperatura [°C]', fontsize=8)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(months_list, fontsize=7, rotation=45)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 7: Heatmap
    ax = fig.add_subplot(gs_sub[2, :2])
    heatmap = df.groupby(['month', 'hour'])['ac_power_kw'].mean().unstack(fill_value=0)
    im = ax.imshow(heatmap.values, aspect='auto', cmap='YlOrRd', origin='lower')
    ax.set_title('Heatmap: Potencia Mensual-Horaria', fontsize=9, fontweight='bold')
    ax.set_xlabel('Hora del día', fontsize=8)
    ax.set_ylabel('Mes', fontsize=8)
    ax.set_xticks(np.arange(0, 24, 4))
    ax.set_yticks(range(12))
    ax.set_yticklabels(months_list, fontsize=7)
    plt.colorbar(im, ax=ax, label='kW')
    
    # 8: Resumen KPI
    ax = fig.add_subplot(gs_sub[2, 2])
    ax.axis('off')
    kpi_9 = (f"RESUMEN ANUAL\n\n"
            f"Energía: {annual_energy/1e6:.2f} GWh\n"
            f"Pot.Máx: {max_power:.0f} kW\n"
            f"CF: {cf*100:.1f}%\n"
            f"GHI: {df['ghi_wm2'].sum()/1000:.0f} kWh/m²")
    ax.text(0.5, 0.5, kpi_9, ha='center', va='center', fontsize=9, fontweight='bold',
           transform=ax.transAxes, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    
    save_matplotlib_figure(fig, 'solar_profile_visualization_2024.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 12. ANÁLISIS TEMPORAL AVANZADO (6 PANELES)
    # ========================================================================
    print("  1️⃣2️⃣ Análisis Temporal Avanzado (6 paneles)...")
    
    fig = plt.figure(figsize=(16, 10))
    gs_adv = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    fig.suptitle('Análisis Temporal Avanzado - 2024', fontsize=13, fontweight='bold')
    
    # Panel 1: Heatmap
    ax = fig.add_subplot(gs_adv[0, 0])
    heatmap = df.groupby(['month', 'hour'])['ac_power_kw'].mean().unstack(fill_value=0)
    im = ax.imshow(heatmap.values, aspect='auto', cmap='YlOrRd', origin='lower')
    ax.set_title('Potencia Mensual-Horaria [kW]', fontsize=10, fontweight='bold')
    ax.set_xlabel('Hora', fontsize=8)
    ax.set_ylabel('Mes', fontsize=8)
    ax.set_xticks(np.arange(0, 24, 4))
    ax.set_yticks(range(12))
    ax.set_yticklabels(months_list, fontsize=8)
    plt.colorbar(im, ax=ax)
    
    # Panel 2: Box plot
    ax = fig.add_subplot(gs_adv[0, 1])
    monthly_data = [df[df['month'] == m]['ac_power_kw'].values for m in range(1, 13)]
    bp = ax.boxplot(monthly_data, labels=months_list)  # type: ignore
    ax.set_title('Distribución Potencia Mensual', fontsize=10, fontweight='bold')
    ax.set_ylabel('Potencia [kW]', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=8)
    
    # Panel 3: Trimestral
    ax = fig.add_subplot(gs_adv[0, 2])
    df_tri = df.copy()
    df_tri['trimestre'] = df_tri['datetime'].dt.quarter
    trimestral = df_tri.groupby('trimestre')['ac_energy_kwh'].sum() / 1000
    bars = ax.bar([f'Q{i}' for i in range(1, 5)], trimestral.values, color=['#FF6B6B', '#4ECDC4', '#95E1D3', '#FFE66D'],
                  alpha=0.7, edgecolor='black', linewidth=1)
    for bar, val in zip(bars, trimestral.values):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:.0f}', ha='center', va='bottom', fontsize=8)
    ax.set_title('Energía por Trimestre [MWh]', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 4: Variabilidad diaria
    ax = fig.add_subplot(gs_adv[1, 0])
    ax.plot(daily_energy.values, linewidth=0.8, color='steelblue', alpha=0.7)
    ax.fill_between(range(len(daily_energy)), daily_energy.values, alpha=0.2, color='steelblue')
    ax.set_title('Energía Diaria (Variabilidad)', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Panel 5: Distribución potencia
    ax = fig.add_subplot(gs_adv[1, 1])
    ax.hist(df['ac_power_kw'].values, bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(df['ac_power_kw'].mean(), color='red', linestyle='--', linewidth=2, label='Media')
    ax.axvline(df['ac_power_kw'].max(), color='green', linestyle='--', linewidth=2, label='Máximo')
    ax.set_title('Distribución Potencia AC', fontsize=10, fontweight='bold')
    ax.set_xlabel('Potencia [kW]', fontsize=8)
    ax.set_ylabel('Frecuencia', fontsize=8)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 6: PR mensual
    ax = fig.add_subplot(gs_adv[1, 2])
    monthly_energy_2 = df.groupby('month')['ac_energy_kwh'].sum()
    monthly_ghi = df.groupby('month')['ghi_wm2'].sum() / 1000
    pr_monthly = (monthly_energy_2 / 1e6) / (4.0496 * (monthly_ghi / 100))
    ax.bar(range(1, 13), pr_monthly.values, color='gold', alpha=0.7, edgecolor='black', linewidth=1)
    ax.axhline(1.0, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Ref: 1.0')
    ax.set_title('Performance Ratio Mensual', fontsize=10, fontweight='bold')
    ax.set_ylabel('PR', fontsize=8)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(months_list, fontsize=8)
    ax.set_ylim(0.8, 1.4)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, fontsize=8)
    
    save_matplotlib_figure(fig, 'analisis_temporal_avanzado_2024.png', subdir='solar')
    plt.close(fig)
    
    # ========================================================================
    # 13. COMPARACIÓN DE ESCENARIOS
    # ========================================================================
    print("  1️⃣3️⃣ Comparación de Escenarios...")
    
    daily_ghi_sorted = daily_ghi.sort_values()
    worst_date = daily_ghi_sorted.index[0]  # Peor día
    best_date = daily_ghi_sorted.index[-1]   # Mejor día
    typical_idx = len(daily_ghi) // 2
    typical_date = daily_ghi.index[typical_idx]
    
    df_worst = df[df['date'] == worst_date]
    df_best = df[df['date'] == best_date]
    df_typical = df[df['date'] == typical_date]
    
    fig = plt.figure(figsize=(16, 10))
    gs_scen = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.3)
    fig.suptitle('Comparación de Escenarios - Sistema FV Iquitos 2024', fontsize=13, fontweight='bold')
    
    # 1: Potencia
    ax = fig.add_subplot(gs_scen[0, 0])
    worst_power = df_worst['ac_power_kw'].mean() if len(df_worst) > 0 else daily_power.min()
    best_power = df_best['ac_power_kw'].mean() if len(df_best) > 0 else daily_power.max()
    typical_power = df_typical['ac_power_kw'].mean() if len(df_typical) > 0 else daily_power.mean()
    
    scenarios = ['Nublado\nPeor día', 'Típico\nPromedio', 'Despejado\nMejor día']
    powers = [worst_power, typical_power, best_power]
    colors_bar = ['#95E1D3', '#4ECDC4', '#FF6B6B']
    
    bars = ax.bar(scenarios, powers, color=colors_bar, alpha=0.7, edgecolor='black', linewidth=1.5)
    for bar, val in zip(bars, powers):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:.0f}', ha='center', va='bottom', fontsize=9)
    ax.set_title('POTENCIA POR ESCENARIO', fontsize=10, fontweight='bold')
    ax.set_ylabel('Potencia [kW]', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 2: Energía
    ax = fig.add_subplot(gs_scen[0, 1])
    worst_energy = df_worst['ac_energy_kwh'].sum() if len(df_worst) > 0 else daily_energy.min()
    best_energy = df_best['ac_energy_kwh'].sum() if len(df_best) > 0 else daily_energy.max()
    typical_energy = df_typical['ac_energy_kwh'].sum() if len(df_typical) > 0 else daily_energy.mean()
    
    energies = [worst_energy / 1000, typical_energy / 1000, best_energy / 1000]
    
    bars = ax.bar(scenarios, energies, color=colors_bar, alpha=0.7, edgecolor='black', linewidth=1.5)
    for bar, val in zip(bars, energies):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    ax.set_title('ENERGÍA ACUMULADA - ESCENARIOS', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3: Irradiancia
    ax = fig.add_subplot(gs_scen[0, 2])
    ax.plot(hourly_avg.index, hourly_avg.values, marker='o', linewidth=2, markersize=6, color='steelblue', label='Promedio')
    ax.fill_between(hourly_avg.index, hourly_avg.values, alpha=0.3, color='steelblue')
    ax.set_title('IRRADIANCIA POA POR ESCENARIO', fontsize=10, fontweight='bold')
    ax.set_xlabel('Hora del día', fontsize=9)
    ax.set_ylabel('GHI [W/m²]', fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 23)
    ax.set_xticks(range(0, 24, 2))
    
    # 4: Max energía vs potencia
    ax = fig.add_subplot(gs_scen[1, 0])
    x_pos = np.arange(3)
    width = 0.35
    
    max_energies = [worst_energy / 1000, typical_energy / 1000, best_energy / 1000]
    max_powers = [
        df_worst['ac_power_kw'].max() if len(df_worst) > 0 else df['ac_power_kw'].min(),
        df_typical['ac_power_kw'].max() if len(df_typical) > 0 else df['ac_power_kw'].mean(),
        df_best['ac_power_kw'].max() if len(df_best) > 0 else df['ac_power_kw'].max()
    ]
    
    bars1 = ax.bar(x_pos - width/2, max_energies, width, label='Energía Máx [MWh]', color='#4ECDC4', alpha=0.8)
    ax2 = ax.twinx()
    bars2 = ax2.bar(x_pos + width/2, max_powers, width, label='Potencia Máx [kW]', color='#FF6B6B', alpha=0.8)
    
    ax.set_title('MAX ENERGÍA vs POTENCIA', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=9, color='#4ECDC4')
    ax2.set_ylabel('Potencia [kW]', fontsize=9, color='#FF6B6B')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(scenarios, fontsize=8)
    ax.tick_params(axis='y', labelcolor='#4ECDC4')
    ax2.tick_params(axis='y', labelcolor='#FF6B6B')
    ax.grid(True, alpha=0.3, axis='y')
    
    # 5: Energía diaria comparativa
    ax = fig.add_subplot(gs_scen[1, 1])
    scenario_labels = ['Nublado\nPeor', 'Típico\nPromedio', 'Despejado\nMejor']
    scenario_energies = [worst_energy / 1000, typical_energy / 1000, best_energy / 1000]
    bars = ax.bar(scenario_labels, scenario_energies, color=colors_bar, alpha=0.8, edgecolor='black', linewidth=1.5)
    for bar, val in zip(bars, scenario_energies):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(), f'{val:.1f}', ha='center', va='bottom', fontsize=10)
    ax.set_title('ENERGÍA DIARIA - COMPARACIÓN', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 6: Tabla resumen
    ax = fig.add_subplot(gs_scen[1, 2])
    ax.axis('off')
    
    table_data_3 = [
        ['Escenario', 'Energía [kWh]', 'P-Máx [kW]', 'P-Prom [kW]'],
        [f'Nublado\n({worst_date})', f'{worst_energy:.0f}', f'{max_powers[0]:.0f}', f'{worst_power:.0f}'],
        [f'Típico\n({typical_date})', f'{typical_energy:.0f}', f'{max_powers[1]:.0f}', f'{typical_power:.0f}'],
        [f'Despejado\n({best_date})', f'{best_energy:.0f}', f'{max_powers[2]:.0f}', f'{best_power:.0f}'],
    ]
    
    table = ax.table(cellText=table_data_3, cellLoc='center', loc='center', colWidths=[0.25, 0.25, 0.25, 0.25])
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1, 2)
    
    for i in range(len(table_data_3)):
        for j in range(len(table_data_3[0])):
            cell = table[(i, j)]
            if i == 0:
                cell.set_facecolor('#B0C4DE')
                cell.set_text_props(weight='bold')
            else:
                cell.set_facecolor(colors_bar[i-1] if i <= 3 else 'lightyellow')
            cell.set_edgecolor('black')
            cell.set_linewidth(1)
    
    save_matplotlib_figure(fig, 'escenarios_comparacion_2024.png', subdir='solar')
    plt.close(fig)
    
    print("\n" + "=" * 90)


def main():
    """Función principal."""
    print("\n" + "="*100)
    print("📊 REGENERADOR MASTER: Todas las Gráficas en Raíz (SIN SUBDIRECTORIOS)")
    print("="*100 + "\n")
    
    print("📊 Cargando datos de solar_pvlib...")
    df = load_real_solar_data()
    print(f"✅ {len(df)} puntos cargados ({df['datetime'].min()} a {df['datetime'].max()})")
    print(f"⚡ Energía anual: {df['ac_energy_kwh'].sum():,.0f} kWh")
    print(f"🔋 Potencia máxima: {df['ac_power_kw'].max():,.0f} kW\n")
    
    generate_all_graphics_root(df)
    
    print("=" * 100)
    print("✅ REGENERACIÓN COMPLETADA")
    print("=" * 100)
    print("\n✅ 13 gráficas regeneradas en RAÍZ:")
    print("   - outputs/analysis/solar/01_perfil_potencia_24h.png")
    print("   - outputs/analysis/solar/02_energia_mensual.png")
    print("   - outputs/analysis/solar/03_distribucion_energia_diaria.png")
    print("   - outputs/analysis/solar/04_analisis_irradiancia.png")
    print("   - outputs/analysis/solar/05_heatmap_potencia_mensual_horaria.png")
    print("   - outputs/analysis/solar/06_heatmap_diaria_horaria_60dias.png")
    print("   - outputs/analysis/solar/07_metricas_desempenio.png")
    print("   - outputs/analysis/solar/08_efectotemperatura_potencia.png")
    print("   - outputs/analysis/solar/09_analisis_variabilidad_climatica.png")
    print("   - outputs/analysis/solar/10_resumen_completo_sistema.png")
    print("   - outputs/analysis/solar/solar_profile_visualization_2024.png (9 paneles)")
    print("   - outputs/analysis/solar/analisis_temporal_avanzado_2024.png (6 paneles)")
    print("   - outputs/analysis/solar/escenarios_comparacion_2024.png (6 paneles)")
    print("\n✅ Datos: 100% REALES de solar_pvlib")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    main()
