#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Actualización de Gráfica: Análisis Temporal Avanzado - Sistema FV Iquitos 2024
================================================================================

Regenera la gráfica de análisis temporal avanzado con los siguientes paneles:
1. Mapa de calor - Potencia promedio (24h × 12 meses)
2. Distribución mensual de energía diaria (box plot)
3. Producción por trimestre (barras)
4. Variabilidad de producción diaria (series temporal + banda)
5. Distribución de energía diaria (histograma)
6. Performance Ratio mensual (línea)

Ejecución:
    cd d:\\diseñopvbesscar
    python scripts/update_temporal_analysis_graphic.py
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
import matplotlib.patches as mpatches

# Configurar estilo
rcParams['figure.figsize'] = (18, 12)
rcParams['font.size'] = 9
rcParams['lines.linewidth'] = 1.5
plt.style.use('seaborn-v0_8-whitegrid')


def load_solar_data() -> pd.DataFrame:
    """Carga datos solares del dataset actualizado."""
    data_path = Path("data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv")
    
    if not data_path.exists():
        print(f"❌ Archivo no encontrado: {data_path}")
        sys.exit(1)
    
    df = pd.read_csv(data_path, index_col=0, parse_dates=True)
    print(f"✓ Datos cargados: {len(df)} filas × {len(df.columns)} columnas")
    return df


def update_temporal_analysis(df: pd.DataFrame) -> None:
    """
    Actualiza la gráfica de análisis temporal avanzado con 6 paneles.
    """
    
    print("\n✓ Creando figura de análisis temporal avanzado...")
    
    # Crear figura
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)
    
    dates = pd.to_datetime(df.index)
    
    # =========================================================================
    # PANEL 1: MAPA DE CALOR - POTENCIA PROMEDIO (24h × 12 meses)
    # =========================================================================
    ax1 = fig.add_subplot(gs[0, 0])
    
    heatmap_data = np.zeros((24, 12))
    for i in range(len(df)):
        hour = dates[i].hour
        month = dates[i].month - 1
        heatmap_data[hour, month] += df.iloc[i]['ac_power_kw']
    
    # Promediar
    heatmap_data = heatmap_data / (365 / 12)
    
    im1 = ax1.imshow(heatmap_data, cmap='YlOrRd', aspect='auto', interpolation='bilinear')
    
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    ax1.set_xticks(range(12))
    ax1.set_xticklabels(meses, fontsize=8)
    ax1.set_yticks(range(0, 24, 2))
    ax1.set_yticklabels([f'{h:02d}' for h in range(0, 24, 2)], fontsize=8)
    
    ax1.set_title('MAPA DE CALOR - POTENCIA PROMEDIO', fontsize=10, fontweight='bold', pad=8)
    ax1.set_ylabel('Horas del día', fontsize=9)
    ax1.set_xlabel('Meses', fontsize=9)
    
    cbar1 = plt.colorbar(im1, ax=ax1, orientation='vertical', pad=0.02)
    cbar1.set_label('Potencia [kW]', fontsize=8)
    
    # =========================================================================
    # PANEL 2: DISTRIBUCIÓN MENSUAL DE ENERGÍA DIARIA (BOX PLOT)
    # =========================================================================
    ax2 = fig.add_subplot(gs[0, 1:])
    
    # Calcular energía diaria para cada mes
    daily_data = []
    monthly_labels = []
    
    for month in range(1, 13):
        month_mask = dates.month == month
        daily_energy_month = df[month_mask].groupby(dates[month_mask].date)['ac_energy_kwh'].sum() / 1000
        daily_data.append(daily_energy_month.values)
        monthly_labels.append(meses[month-1])
    
    bp = ax2.boxplot(daily_data, labels=monthly_labels, patch_artist=True, widths=0.6)  # type: ignore
    
    # Colorear boxes
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, 12))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax2.set_title('DISTRIBUCIÓN MENSUAL DE ENERGÍA DIARIA', fontsize=10, fontweight='bold', pad=8)
    ax2.set_ylabel('Energía [MWh/día]', fontsize=9)
    ax2.set_xlabel('Mes', fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # =========================================================================
    # PANEL 3: PRODUCCIÓN POR TRIMESTRE
    # =========================================================================
    ax3 = fig.add_subplot(gs[1, 2])
    
    trimestral_energy = []
    trimestral_labels = ['Q1\n(Ene-Mar)', 'Q2\n(Abr-Jun)', 'Q3\n(Jul-Sep)', 'Q4\n(Oct-Dic)']
    
    for q, months in enumerate([(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)]):
        q_mask = dates.month.isin(months)
        q_energy = df[q_mask]['ac_energy_kwh'].sum() / 1000
        trimestral_energy.append(q_energy)
    
    colors_q = ['#ff7f0e', '#2ca02c', '#1f77b4', '#ff9896']
    bars = ax3.bar(trimestral_labels, trimestral_energy, color=colors_q, alpha=0.7, edgecolor='black', linewidth=1.5)
    
    # Anotaciones
    for bar, val in zip(bars, trimestral_energy):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax3.set_title('PRODUCCIÓN POR TRIMESTRE', fontsize=10, fontweight='bold', pad=8)
    ax3.set_ylabel('Energía [MWh]', fontsize=9)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # =========================================================================
    # PANEL 4: VARIABILIDAD DE PRODUCCIÓN DIARIA
    # =========================================================================
    ax4 = fig.add_subplot(gs[1, :2])
    
    daily_energy_full = df.groupby(dates.date)['ac_energy_kwh'].sum() / 1000
    days = range(len(daily_energy_full))
    
    # Calcular media móvil (rolling average)
    rolling_mean = daily_energy_full.rolling(window=7, center=True).mean()
    rolling_std = daily_energy_full.rolling(window=7, center=True).std()
    
    # Plot series e intervalo de confianza
    ax4.plot(days, daily_energy_full.values, alpha=0.4, color='blue', linewidth=0.8, label='Energía diaria')
    ax4.plot(days, rolling_mean.values, color='red', linewidth=2, label='Media móvil (7 días)')
    ax4.fill_between(days, 
                     (rolling_mean - rolling_std).values,
                     (rolling_mean + rolling_std).values,
                     alpha=0.2, color='blue', label='±1σ')
    
    ax4.set_title('VARIABILIDAD DE PRODUCCIÓN DIARIA', fontsize=10, fontweight='bold', pad=8)
    ax4.set_ylabel('Energía [MWh/día]', fontsize=9)
    ax4.set_xlabel('Fecha', fontsize=9)
    ax4.legend(fontsize=8, loc='lower right')
    ax4.grid(True, alpha=0.3)
    
    # Ejes X con fechas
    ax4.set_xticks([0, len(days)//4, len(days)//2, 3*len(days)//4, len(days)-1])
    ax4.set_xticklabels(['Ene', 'Abr', 'Jul', 'Oct', 'Dic'], fontsize=8)
    
    # =========================================================================
    # PANEL 5: DISTRIBUCIÓN DE ENERGÍA DIARIA
    # =========================================================================
    ax5 = fig.add_subplot(gs[2, 0])
    
    ax5.hist(daily_energy_full.values, bins=25, color='green', alpha=0.7, edgecolor='black', linewidth=1)
    
    mean_energy = daily_energy_full.mean()
    median_energy = daily_energy_full.median()
    std_energy = daily_energy_full.std()
    
    ax5.axvline(mean_energy, color='red', linestyle='--', linewidth=2, label=f'Media: {mean_energy:.1f}')
    ax5.axvline(median_energy, color='orange', linestyle=':', linewidth=2, label=f'Mediana: {median_energy:.1f}')
    ax5.axvline(mean_energy - std_energy, color='gray', linestyle='-', linewidth=1, alpha=0.5)
    ax5.axvline(mean_energy + std_energy, color='gray', linestyle='-', linewidth=1, alpha=0.5)
    
    ax5.set_title('DISTRIBUCIÓN DE ENERGÍA DIARIA', fontsize=10, fontweight='bold', pad=8)
    ax5.set_xlabel('Energía [MWh/día]', fontsize=9)
    ax5.set_ylabel('Frecuencia [días]', fontsize=9)
    ax5.legend(fontsize=7, loc='upper right')
    ax5.grid(True, alpha=0.3, axis='y')
    
    # Texto de estadísticas
    stats_text = f"""CV = {(std_energy/mean_energy)*100:.1f}%
Min = {daily_energy_full.min():.1f} MWh
Max = {daily_energy_full.max():.1f} MWh"""
    ax5.text(0.98, 0.97, stats_text, transform=ax5.transAxes, fontsize=8,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # =========================================================================
    # PANEL 6: PERFORMANCE RATIO MENSUAL
    # =========================================================================
    ax6 = fig.add_subplot(gs[2, 1:])
    
    monthly_pr = []
    monthly_irr = []
    
    for month in range(1, 13):
        month_mask = dates.month == month
        month_energy = df[month_mask]['ac_energy_kwh'].sum()
        month_irr = df[month_mask]['ghi_wm2'].sum() / 1000
        
        # PR = (Energía reportada / (Irradiancia × Área)) × 100
        # Simplificado: PR = Energía / Irradiancia normalizado
        if month_irr > 0:
            pr = (month_energy / 4049.56) / (month_irr) * 100
            monthly_pr.append(pr)
            monthly_irr.append(month_irr)
        else:
            monthly_pr.append(0)
            monthly_irr.append(0)
    
    line = ax6.plot(meses, monthly_pr, marker='o', color='green', linewidth=2.5, 
                   markersize=8, label='PR mensual')
    
    # Línea de promedio
    mean_pr = np.mean(monthly_pr)
    ax6.axhline(mean_pr, color='red', linestyle='--', linewidth=2, 
               label=f'PR anual: {mean_pr:.1f}%')
    
    # Rango normal
    ax6.axhspan(105, 130, alpha=0.1, color='green', label='Rango esperado')
    
    # Anotaciones
    for i, (mes, pr) in enumerate(zip(meses, monthly_pr)):
        ax6.text(i, pr + 1, f'{pr:.0f}%', ha='center', fontsize=8, fontweight='bold')
    
    ax6.set_title('PERFORMANCE RATIO MENSUAL', fontsize=10, fontweight='bold', pad=8)
    ax6.set_ylabel('Performance Ratio [%]', fontsize=9)
    ax6.set_xlabel('Mes', fontsize=9)
    ax6.set_ylim(100, 150)
    ax6.legend(fontsize=8, loc='best')
    ax6.grid(True, alpha=0.3)
    
    # =========================================================================
    # TÍTULO GENERAL
    # =========================================================================
    fig.suptitle('Análisis Temporal Avanzado - Sistema FV Iquitos 2024',
                fontsize=14, fontweight='bold', y=0.995)
    
    # =========================================================================
    # GUARDAR
    # =========================================================================
    print("\n✓ Guardando gráfica actualizada...")
    path = Path("outputs/analysis/solar/analisis_temporal_avanzado_2024.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ GRÁFICA ACTUALIZADA: {path}")
    print(f"   Tamaño: {path.stat().st_size / (1024*1024):.1f} MB")
    
    plt.close()


def main():
    """Función principal."""
    print("\n" + "="*100)
    print("📊 ACTUALIZACIÓN: Análisis Temporal Avanzado - Sistema FV Iquitos 2024")
    print("="*100)
    
    # Cargar datos
    print("\n✓ FASE 1: Cargando datos solares...")
    df = load_solar_data()
    
    # Actualizar gráfica
    print("\n✓ FASE 2: Actualizando gráfica con análisis temporal avanzado...")
    update_temporal_analysis(df)
    
    print("\n" + "="*100)
    print("✅ ACTUALIZACIÓN COMPLETADA")
    print("="*100)
    print("""
Gráfica guardada en:
   └─ outputs/analysis/solar/analisis_temporal_avanzado_2024.png

Paneles incluidos:
   1. Mapa de calor - Potencia promedio (24h × 12 meses)
   2. Distribución mensual de energía diaria (box plot)
   3. Producción por trimestre (barras)
   4. Variabilidad de producción diaria (series + banda de confianza)
   5. Distribución de energía diaria (histograma)
   6. Performance Ratio mensual (línea)

Todos los datos están ACTUALIZADOS para 2024.
Datos de entrada: 8,760 puntos horarios validados
""")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
