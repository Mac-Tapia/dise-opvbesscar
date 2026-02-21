#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regeneración Completa de Gráficas Solares - Datos Reales solar_pvlib
================================================================================

Regenera TODAS las gráficas originales (10+) con datos REALES de solar_pvlib:
1. Perfil potencia 24h
2. Energía mensual
3. Distribución energía diaria
4. Análisis irradiancia
5. Heatmap potencia mensual-horaria
6. Heatmap diaria-horaria 60 días
7. Métricas desempeño
8. Efecto temperatura-potencia
9. Análisis variabilidad climática
10. Resumen completo sistema
11. Solar profile visualization (9 paneles)
12. Análisis temporal avanzado (6 paneles)
13. Comparación escenarios
14. Día despejado representativo

Ejecución:
    cd d:\\diseñopvbesscar
    python scripts/regenerate_all_graphics_complete.py
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
    """Carga datos REALES de solar_pvlib."""
    try:
        csv_path = Path(__file__).parent.parent / 'data' / 'oe2' / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
        df = pd.read_csv(csv_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        return df
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        sys.exit(1)


def g01_perfil_potencia_24h(df):
    """Gráfica 1: Perfil de potencia 24 horas."""
    print("  1️⃣  Generando: Perfil Potencia 24h...")
    
    df['hour'] = df['datetime'].dt.hour
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
    
    save_matplotlib_figure(fig, '01_perfil_potencia_24h.png', subdir='solar/profiles')
    plt.close(fig)


def g02_energia_mensual(df):
    """Gráfica 2: Energía mensual."""
    print("  2️⃣  Generando: Energía Mensual...")
    
    df['month'] = df['datetime'].dt.to_period('M')
    monthly = df.groupby('month')['ac_energy_kwh'].sum() / 1000
    
    fig, ax = plt.subplots(figsize=(12, 6))
    months = [p.strftime('%b') for p in monthly.index]
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
    
    save_matplotlib_figure(fig, '02_energia_mensual.png', subdir='solar/profiles')
    plt.close(fig)


def g03_distribucion_energia_diaria(df):
    """Gráfica 3: Distribución energía diaria."""
    print("  3️⃣  Generando: Distribución Energía Diaria...")
    
    df['date'] = df['datetime'].dt.date
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
    
    save_matplotlib_figure(fig, '03_distribucion_energia_diaria.png', subdir='solar/profiles')
    plt.close(fig)


def g04_analisis_irradiancia(df):
    """Gráfica 4: Análisis irradiancia."""
    print("  4️⃣  Generando: Análisis Irradiancia...")
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Análisis de Irradiancia - 2024', fontsize=12, fontweight='bold')
    
    # GHI
    ax = axes[0, 0]
    ax.hist(df['ghi_wm2'].values, bins=50, color='orange', alpha=0.7, edgecolor='black')
    ax.set_title('GHI - Global Horizontal Irradiance', fontsize=10, fontweight='bold')
    ax.set_xlabel('GHI [W/m²]', fontsize=9)
    ax.set_ylabel('Frecuencia', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    
    # DNI
    ax = axes[0, 1]
    ax.hist(df['dni_wm2'].values, bins=50, color='red', alpha=0.7, edgecolor='black')
    ax.set_title('DNI - Direct Normal Irradiance', fontsize=10, fontweight='bold')
    ax.set_xlabel('DNI [W/m²]', fontsize=9)
    ax.set_ylabel('Frecuencia', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    
    # DHI
    ax = axes[1, 0]
    ax.hist(df['dhi_wm2'].values, bins=50, color='blue', alpha=0.7, edgecolor='black')
    ax.set_title('DHI - Diffuse Horizontal Irradiance', fontsize=10, fontweight='bold')
    ax.set_xlabel('DHI [W/m²]', fontsize=9)
    ax.set_ylabel('Frecuencia', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Comparativa
    ax = axes[1, 1]
    ax.scatter(df['ghi_wm2'], df['ac_power_kw'], alpha=0.3, s=10, label='GHI vs Potencia')
    ax.set_title('Correlación GHI - Potencia AC', fontsize=10, fontweight='bold')
    ax.set_xlabel('GHI [W/m²]', fontsize=9)
    ax.set_ylabel('Potencia AC [kW]', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    
    plt.tight_layout()
    save_matplotlib_figure(fig, '04_analisis_irradiancia.png', subdir='solar/irradiance')
    plt.close(fig)


def g05_heatmap_potencia_mensual_horaria(df):
    """Gráfica 5: Heatmap potencia mensual-horaria."""
    print("  5️⃣  Generando: Heatmap Potencia Mensual-Horaria...")
    
    df['month'] = df['datetime'].dt.month
    df['hour'] = df['datetime'].dt.hour
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
    
    save_matplotlib_figure(fig, '05_heatmap_potencia_mensual_horaria.png', subdir='solar/heatmaps')
    plt.close(fig)


def g06_heatmap_diaria_horaria_60dias(df):
    """Gráfica 6: Heatmap diaria-horaria (primeros 60 días)."""
    print("  6️⃣  Generando: Heatmap Diaria-Horaria 60 días...")
    
    df_60 = df.head(60 * 24)  # Primeros 60 días
    df_60['day'] = df_60['datetime'].dt.day
    df_60['hour'] = df_60['datetime'].dt.hour
    heatmap_data = df_60.groupby(['day', 'hour'])['ac_power_kw'].mean().unstack(fill_value=0)
    
    fig, ax = plt.subplots(figsize=(14, 10))
    im = ax.imshow(heatmap_data.values, aspect='auto', cmap='viridis', origin='lower')
    
    ax.set_xlabel('Hora del día', fontsize=10)
    ax.set_ylabel('Día', fontsize=10)
    ax.set_xticks(np.arange(0, 24, 2))
    ax.set_xticklabels([f'{i:02d}' for i in range(0, 24, 2)], fontsize=9)
    ax.set_yticks(np.arange(0, 60, 5))
    ax.set_yticklabels(np.arange(0, 60, 5), fontsize=8)
    
    ax.set_title('Heatmap: Potencia Diaria-Horaria (60 días)', fontsize=12, fontweight='bold')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Potencia [kW]', fontsize=9)
    
    save_matplotlib_figure(fig, '06_heatmap_diaria_horaria_60dias.png', subdir='solar/heatmaps')
    plt.close(fig)


def g07_metricas_desempenio(df):
    """Gráfica 7: Métricas desempeño."""
    print("  7️⃣  Generando: Métricas Desempeño...")
    
    annual_energy = df['ac_energy_kwh'].sum()
    max_power = df['ac_power_kw'].max()
    avg_power = df['ac_power_kw'].mean()
    cf = (avg_power * 24 * 365) / (3201 * 1000)  # Capacity factor
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Métricas de Desempeño - 2024', fontsize=12, fontweight='bold')
    
    # KPI 1
    ax = axes[0, 0]
    ax.text(0.5, 0.5, f'{annual_energy/1e6:.2f}\nGWh/año', ha='center', va='center', fontsize=14, fontweight='bold',
           transform=ax.transAxes, bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    ax.set_title('Energía Anual', fontsize=10, fontweight='bold')
    ax.axis('off')
    
    # KPI 2
    ax = axes[0, 1]
    ax.text(0.5, 0.5, f'{max_power:.0f}\nkW', ha='center', va='center', fontsize=14, fontweight='bold',
           transform=ax.transAxes, bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
    ax.set_title('Potencia Máxima', fontsize=10, fontweight='bold')
    ax.axis('off')
    
    # KPI 3
    ax = axes[1, 0]
    ax.text(0.5, 0.5, f'{avg_power:.0f}\nkW', ha='center', va='center', fontsize=14, fontweight='bold',
           transform=ax.transAxes, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.set_title('Potencia Promedio', fontsize=10, fontweight='bold')
    ax.axis('off')
    
    # KPI 4
    ax = axes[1, 1]
    ax.text(0.5, 0.5, f'{cf*100:.1f}%', ha='center', va='center', fontsize=14, fontweight='bold',
           transform=ax.transAxes, bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))
    ax.set_title('Capacity Factor', fontsize=10, fontweight='bold')
    ax.axis('off')
    
    save_matplotlib_figure(fig, '07_metricas_desempenio.png', subdir='solar/statistics')
    plt.close(fig)


def g08_efecto_temperatura_potencia(df):
    """Gráfica 8: Efecto temperatura-potencia."""
    print("  8️⃣  Generando: Efecto Temperatura-Potencia...")
    
    fig, ax = plt.subplots(figsize=(12, 6))
    scatter = ax.scatter(df['temp_air_c'], df['ac_power_kw'], alpha=0.3, s=10, c=df['ghi_wm2'], cmap='hot')
    
    ax.set_title('Efecto Temperatura en Potencia - 2024', fontsize=12, fontweight='bold')
    ax.set_xlabel('Temperatura [°C]', fontsize=10)
    ax.set_ylabel('Potencia AC [kW]', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('GHI [W/m²]', fontsize=9)
    
    save_matplotlib_figure(fig, '08_efectotemperatura_potencia.png', subdir='solar/comparisons')
    plt.close(fig)


def g09_variabilidad_climatica(df):
    """Gráfica 9: Análisis variabilidad climática."""
    print("  9️⃣  Generando: Análisis Variabilidad Climática...")
    
    df['date'] = df['datetime'].dt.date
    daily_ghi = df.groupby('date')['ghi_wm2'].sum()
    daily_power = df.groupby('date')['ac_power_kw'].mean()
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Análisis Variabilidad Climática - 2024', fontsize=12, fontweight='bold')
    
    # GHI diario
    ax = axes[0, 0]
    ax.plot(daily_ghi.values, linewidth=1, color='orange')
    ax.fill_between(range(len(daily_ghi)), daily_ghi.values, alpha=0.3, color='orange')
    ax.set_title('GHI Diario', fontsize=10, fontweight='bold')
    ax.set_ylabel('GHI [Wh/m²]', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # Potencia diaria
    ax = axes[0, 1]
    ax.plot(daily_power.values, linewidth=1, color='steelblue')
    ax.fill_between(range(len(daily_power)), daily_power.values, alpha=0.3, color='steelblue')
    ax.set_title('Potencia Promedio Diaria', fontsize=10, fontweight='bold')
    ax.set_ylabel('Potencia [kW]', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # Temperatura
    ax = axes[1, 0]
    monthly_temp = df.groupby(df['datetime'].dt.to_period('M'))['temp_air_c'].mean()
    ax.bar(range(len(monthly_temp)), monthly_temp.values, color='red', alpha=0.7)
    ax.set_title('Temperatura Promedio Mensual', fontsize=10, fontweight='bold')
    ax.set_ylabel('Temperatura [°C]', fontsize=9)
    ax.set_xticks(range(12))
    ax.set_xticklabels(['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'], fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Viento
    ax = axes[1, 1]
    monthly_wind = df.groupby(df['datetime'].dt.to_period('M'))['wind_speed_ms'].mean()
    ax.bar(range(len(monthly_wind)), monthly_wind.values, color='cyan', alpha=0.7)
    ax.set_title('Velocidad Viento Promedio Mensual', fontsize=10, fontweight='bold')
    ax.set_ylabel('Velocidad [m/s]', fontsize=9)
    ax.set_xticks(range(12))
    ax.set_xticklabels(['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'], fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    save_matplotlib_figure(fig, '09_analisis_variabilidad_climatica.png', subdir='solar/comparisons')
    plt.close(fig)


def g10_resumen_completo_sistema(df):
    """Gráfica 10: Resumen completo sistema."""
    print("  ✅ Generando: Resumen Completo Sistema...")
    
    df['date'] = df['datetime'].dt.date
    df['month'] = df['datetime'].dt.to_period('M')
    df['hour'] = df['datetime'].dt.hour
    
    daily_energy = df.groupby('date')['ac_energy_kwh'].sum() / 1000
    monthly_energy = df.groupby('month')['ac_energy_kwh'].sum() / 1000
    hourly_energy = df.groupby('hour')['ac_energy_kwh'].sum()
    
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3)
    fig.suptitle('Resumen Completo del Sistema FV Iquitos - 2024', fontsize=14, fontweight='bold')
    
    # Panel 1: Energía diaria
    ax = fig.add_subplot(gs[0, :2])
    ax.bar(range(len(daily_energy)), daily_energy.values, color='steelblue', alpha=0.6, width=0.8)
    ax.axhline(daily_energy.mean(), color='red', linestyle='--', linewidth=2, label=f'Promedio: {daily_energy.mean():.1f}')
    ax.set_title('Energía Diaria', fontsize=10, fontweight='bold')
    ax.set_ylabel('Energía [MWh]', fontsize=9)
    ax.set_xlim(0, len(daily_energy))
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 2: Energía mensual
    ax = fig.add_subplot(gs[0, 2])
    months = [p.strftime('%b') for p in monthly_energy.index]
    bars = ax.bar(range(len(monthly_energy)), monthly_energy.values, color='steelblue', alpha=0.7, edgecolor='black')
    for b, v in zip(bars, monthly_energy.values):
        ax.text(b.get_x() + b.get_width()/2., b.get_height(), f'{v:.0f}', ha='center', va='bottom', fontsize=7)
    ax.set_title('Energía Mensual', fontsize=10, fontweight='bold')
    ax.set_ylabel('[MWh]', fontsize=8)
    ax.set_xticks(range(len(months)))
    ax.set_xticklabels(months, fontsize=7, rotation=45)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Distribución energía
    ax = fig.add_subplot(gs[1, 0])
    ax.hist(daily_energy.values, bins=25, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(daily_energy.mean(), color='red', linestyle='--', linewidth=2, label='Media')
    ax.set_title('Distribución Energía Diaria', fontsize=10, fontweight='bold')
    ax.set_xlabel('Energía [MWh]', fontsize=8)
    ax.set_ylabel('Frecuencia', fontsize=8)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 4: Energía por hora
    ax = fig.add_subplot(gs[1, 1:])
    ax.bar(range(24), hourly_energy.values / 1000, color='orange', alpha=0.7, edgecolor='black')
    ax.set_title('Distribución Energía por Hora del Día', fontsize=10, fontweight='bold')
    ax.set_xlabel('Hora del día', fontsize=8)
    ax.set_ylabel('Energía [MWh]', fontsize=8)
    ax.set_xticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 5: KPI resume
    ax = fig.add_subplot(gs[2, :])
    ax.axis('off')
    
    annual_energy = df['ac_energy_kwh'].sum()
    max_power = df['ac_power_kw'].max()
    annual_irr = df['ghi_wm2'].sum() / 1000
    
    kpi_text = (f"MÉTRICAS ANUALES 2024\n"
               f"Energía: {annual_energy/1e6:.2f} GWh  |  "
               f"Potencia Máx: {max_power:.0f} kW  |  "
               f"GHI: {annual_irr:.1f} kWh/m²  |  "
               f"CF: {(annual_energy/1e6*1000)/(3201*365/1000):.1f}%")
    
    ax.text(0.5, 0.5, kpi_text, ha='center', va='center', fontsize=11, fontweight='bold',
           transform=ax.transAxes, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    save_matplotlib_figure(fig, '10_resumen_completo_sistema.png', subdir='solar/statistics')
    plt.close(fig)


def main():
    """Función principal."""
    print("\n" + "="*100)
    print("🔄 REGENERADOR: Todas las Gráficas Solares - Datos Reales solar_pvlib")
    print("="*100 + "\n")
    
    print("📊 Cargando datos de solar_pvlib...")
    df = load_real_solar_data()
    print(f"✅ {len(df)} puntos cargados ({df['datetime'].min()} a {df['datetime'].max()})")
    
    print(f"\n⚡ Energía anual: {df['ac_energy_kwh'].sum():,.0f} kWh")
    print(f"🔋 Potencia máxima: {df['ac_power_kw'].max():,.0f} kW\n")
    
    print("📈 REGENERANDO GRÁFICAS:\n")
    
    g01_perfil_potencia_24h(df)
    g02_energia_mensual(df)
    g03_distribucion_energia_diaria(df)
    g04_analisis_irradiancia(df)
    g05_heatmap_potencia_mensual_horaria(df)
    g06_heatmap_diaria_horaria_60dias(df)
    g07_metricas_desempenio(df)
    g08_efecto_temperatura_potencia(df)
    g09_variabilidad_climatica(df)
    g10_resumen_completo_sistema(df)
    
    print("\n" + "="*100)
    print("✅ REGENERACIÓN COMPLETADA")
    print("="*100)
    print("\n10 gráficas principales regeneradas con datos REALES de solar_pvlib")
    print("Ubicación: outputs/analysis/solar/\n")
    print("="*100 + "\n")


if __name__ == '__main__':
    main()
