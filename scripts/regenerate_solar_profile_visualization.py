#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regenerador de Gráfica: solar_profile_visualization_2024.png
==============================================================

Regenera la gráfica 'solar_profile_visualization_2024.png' con:
- Todos los paneles originales preservados
- Datos actuales del dataset solar (2024)
- Guardado en: outputs/analysis/solar/

Ejecución:
    cd d:\\diseñopvbesscar
    python scripts/regenerate_solar_profile_visualization.py
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
rcParams['figure.figsize'] = (20, 16)
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


def regenerate_solar_profile_visualization(df: pd.DataFrame) -> None:
    """
    Regenera la gráfica completa de perfil solar con múltiples paneles.
    
    Paneles incluidos:
    1. Perfil diario promedio (24h)
    2. Energía mensual
    3. Variación semanal
    4. Heatmap mensual-horario
    5. Distribución de GHI
    6. Curva de duración
    7. Estadísticas clave (tabla)
    8. Mapa de variabilidad diaria
    """
    
    print("\n✓ Creando figura multi-panel...")
    
    # Crear figura con subplots
    fig = plt.figure(figsize=(20, 16))
    gs = fig.add_gridspec(4, 3, hspace=0.35, wspace=0.3, 
                         left=0.06, right=0.95, top=0.96, bottom=0.05)
    
    # PANEL 1: Perfil diario promedio (24h)
    ax1 = fig.add_subplot(gs[0, 0])
    dates = pd.to_datetime(df.index)
    hourly_avg = df.groupby(dates.hour)['ac_power_kw'].mean()
    hours = range(24)
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, 24))
    ax1.bar(hours, hourly_avg.values, color=colors, edgecolor='black', linewidth=1)
    ax1.set_title('Perfil Diario Promedio (24h)', fontsize=11, fontweight='bold')
    ax1.set_xlabel('Hora', fontsize=10)
    ax1.set_ylabel('Potencia [kW]', fontsize=10)
    ax1.set_xticks(range(0, 24, 3))
    ax1.grid(True, alpha=0.3, axis='y')
    
    # PANEL 2: Energía mensual
    ax2 = fig.add_subplot(gs[0, 1])
    monthly_energy = df.groupby(dates.month)['ac_energy_kwh'].sum() / 1000
    meses = ['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
    ax2.bar(meses, monthly_energy.values, color='steelblue', alpha=0.7, edgecolor='black')
    ax2.set_title('Energía Mensual', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Energía [MWh]', fontsize=10)
    ax2.axhline(monthly_energy.mean(), color='red', linestyle='--', linewidth=2, label='Promedio')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # PANEL 3: Variación semanal
    ax3 = fig.add_subplot(gs[0, 2])
    dayofweek_energy = df.groupby(dates.dayofweek)['ac_energy_kwh'].sum() / 1000
    dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    ax3.plot(dias, dayofweek_energy.values, marker='o', linewidth=2.5, markersize=8, color='darkblue')
    ax3.fill_between(range(len(dias)), dayofweek_energy.values, alpha=0.3, color='lightblue')
    ax3.set_title('Variación Semanal', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Energía [MWh/día]', fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # PANEL 4: Heatmap mensual-horario
    ax4 = fig.add_subplot(gs[1, :2])
    heatmap_data = np.zeros((12, 24))
    for i in range(len(df)):
        month = dates[i].month - 1
        hour = dates[i].hour
        heatmap_data[month, hour] += df.iloc[i]['ac_power_kw']
    heatmap_data = heatmap_data / (365 / 12)
    
    im = ax4.imshow(heatmap_data, cmap='hot', aspect='auto', interpolation='bilinear')
    ax4.set_xticks(range(0, 24, 2))
    ax4.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)], fontsize=9)
    ax4.set_yticks(range(12))
    ax4.set_yticklabels(meses)
    ax4.set_title('Potencia Horaria-Mensual [kW]', fontsize=11, fontweight='bold')
    ax4.set_xlabel('Hora del Día', fontsize=10)
    ax4.set_ylabel('Mes', fontsize=10)
    cbar = plt.colorbar(im, ax=ax4, pad=0.01)
    cbar.set_label('Potencia [kW]', fontsize=9)
    
    # PANEL 5: Distribución de GHI
    ax5 = fig.add_subplot(gs[1, 2])
    daily_ghi = df.groupby(dates.date)['ghi_wm2'].sum() / 1000
    ax5.hist(daily_ghi.values, bins=25, color='gold', alpha=0.7, edgecolor='black')
    ax5.axvline(daily_ghi.mean(), color='red', linestyle='--', linewidth=2, label=f'Media: {daily_ghi.mean():.2f}')
    ax5.set_title('Distribución GHI Diario', fontsize=11, fontweight='bold')
    ax5.set_xlabel('GHI [kWh/m²/día]', fontsize=10)
    ax5.set_ylabel('Frecuencia', fontsize=10)
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3, axis='y')
    
    # PANEL 6: Curva de duración de potencia
    ax6 = fig.add_subplot(gs[2, 0])
    power_sorted = np.sort(df['ac_power_kw'].values)[::-1]  # type: ignore[no-overload-found]
    cumulative_pct = np.arange(1, len(power_sorted) + 1) / len(power_sorted) * 100
    ax6.plot(cumulative_pct, power_sorted, linewidth=2.5, color='darkblue')
    ax6.fill_between(cumulative_pct, power_sorted, alpha=0.3, color='lightblue')
    ax6.set_title('Curva de Duración de Potencia', fontsize=11, fontweight='bold')
    ax6.set_xlabel('% del Tiempo', fontsize=10)
    ax6.set_ylabel('Potencia [kW]', fontsize=10)
    ax6.grid(True, alpha=0.3)
    
    # PANEL 7: Distribución de energía diaria
    ax7 = fig.add_subplot(gs[2, 1])
    daily_energy = df.groupby(dates.date)['ac_energy_kwh'].sum() / 1000
    ax7.hist(daily_energy.values, bins=30, color='lightgreen', alpha=0.7, edgecolor='black')
    media = daily_energy.mean()
    std = daily_energy.std()
    ax7.axvline(media, color='red', linestyle='-', linewidth=2, label=f'Media: {media:.2f}')
    ax7.axvline(media + std, color='orange', linestyle=':', linewidth=2, label=f'±σ')
    ax7.axvline(media - std, color='orange', linestyle=':', linewidth=2)
    ax7.set_title('Distribución Energía Diaria', fontsize=11, fontweight='bold')
    ax7.set_xlabel('Energía [MWh/día]', fontsize=10)
    ax7.set_ylabel('Frecuencia [días]', fontsize=10)
    ax7.legend(fontsize=9)
    ax7.grid(True, alpha=0.3, axis='y')
    
    # PANEL 8: Porcentaje de tiempo > umbral
    ax8 = fig.add_subplot(gs[2, 2])
    max_power = df['ac_power_kw'].max()
    thresholds = [0.25, 0.50, 0.75, 0.90]
    percentages = [(df['ac_power_kw'] > (max_power * t)).sum() / len(df) * 100 for t in thresholds]
    labels = [f'{int(t*100)}%' for t in thresholds]
    ax8.bar(labels, percentages, color='coral', alpha=0.7, edgecolor='black')
    ax8.set_title('% Tiempo con P > Umbral', fontsize=11, fontweight='bold')
    ax8.set_ylabel('Porcentaje [%]', fontsize=10)
    for i, v in enumerate(percentages):
        ax8.text(i, v + 2, f'{v:.1f}%', ha='center', fontweight='bold', fontsize=9)
    ax8.grid(True, alpha=0.3, axis='y')
    
    # PANEL 9: Tabla de estadísticas principales
    ax9 = fig.add_subplot(gs[3, :])
    ax9.axis('off')
    
    # Calcular estadísticas
    annual_energy = df['ac_energy_kwh'].sum()
    max_power = df['ac_power_kw'].max()
    mean_power = df['ac_power_kw'].mean()
    ghi_annual = df['ghi_wm2'].sum() / 1000
    capacity_factor = (annual_energy / (3201 * 8760)) * 100
    
    stats_text = f"""ESTADÍSTICAS DEL SISTEMA FOTOVOLTAICO - IQUITOS 2024 (DATOS ACTUALIZADOS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CAPACIDAD DEL SISTEMA
├─ Potencia DC nominal:        4,049.56 kWp
├─ Potencia AC nominal:        3,201.00 kW
├─ Número de módulos:          200,632 unidades
├─ Número de inversores:       2 × Eaton Xpert1670

PRODUCCIÓN ANUAL 2024
├─ Energía AC total:           {annual_energy/1e9:>10.3f} TWh ({annual_energy/1e6:>10.0f} MWh)
├─ Energía promedio diaria:    {annual_energy/365/1e3:>10.1f} MWh/día
├─ Potencia máxima registrada: {max_power:>10.0f} kW
├─ Potencia media anual:       {mean_power:>10.0f} kW

EFICIENCIA Y RENDIMIENTO
├─ Factor de Capacidad:        {capacity_factor:>10.1f} % (EXCELENTE para latitud ecuatorial)
├─ Yield específico:           {annual_energy/4049.56:>10.0f} kWh/kWp/año
├─ Horas equivalentes:         {annual_energy/max_power:>10.0f} h/año
├─ Performance Ratio:          {(annual_energy/4049.56)/(ghi_annual)*100:>10.1f} %

RADIACIÓN SOLAR (PVGIS)
├─ GHI anual total:            {ghi_annual:>10.1f} kWh/m²/año
├─ GHI máximo horario:         {df['ghi_wm2'].max():>10.0f} W/m²
├─ Horas GHI > 500 W/m²:       {(df['ghi_wm2'] > 500).sum():>10.0f} horas
├─ Horas con generación:       {(df['ac_power_kw'] > 0).sum():>10.0f} horas

VARIABILIDAD Y RIESGOS
├─ Desv. Est. Energía Diaria:  {daily_energy.std():>10.2f} MWh
├─ Coef. Variación:            {(daily_energy.std()/daily_energy.mean())*100:>10.1f} %
├─ Energía máxima diaria:      {daily_energy.max():>10.2f} MWh (día despejado)
├─ Energía mínima diaria:      {daily_energy.min():>10.2f} MWh (día nublado)

SOSTENIBILIDAD
├─ CO₂ evitado (indirecto):    {annual_energy*0.4521/1000:>10.0f} toneladas/año
├─ Factor CO₂ (sistema aislado): 0.4521 kg/kWh
├─ Ahorro económico anual:     S/. {annual_energy * 0.28:>10.0f} (HFP @ S/.0.28/kWh)
"""
    
    ax9.text(0.02, 0.95, stats_text, transform=ax9.transAxes, fontsize=8.5,
            verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='#f5f5f5', alpha=0.95, pad=1))
    
    # Título general
    fig.suptitle('PERFIL SOLAR COMPLETO - 2024 (Datos Actualizados) | Iquitos, Perú',
                fontsize=14, fontweight='bold', y=0.985)
    
    # Guardar
    print("\n✓ Guardando gráfica...")
    path = Path("outputs/analysis/solar/solar_profile_visualization_2024.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ GRÁFICA REGENERADA: {path}")
    print(f"   Tamaño: {path.stat().st_size / (1024*1024):.1f} MB")
    
    plt.close()


def main():
    """Función principal."""
    print("\n" + "="*100)
    print("🔄 REGENERADOR: solar_profile_visualization_2024.png")
    print("="*100)
    
    # Cargar datos
    print("\n✓ FASE 1: Cargando datos solares...")
    df = load_solar_data()
    
    # Regenerar gráfica
    print("\n✓ FASE 2: Regenerando gráfica con paneles completos...")
    regenerate_solar_profile_visualization(df)
    
    print("\n" + "="*100)
    print("✅ REGENERACIÓN COMPLETADA")
    print("="*100)
    print("""
Gráfica guardada en:
   └─ outputs/analysis/solar/solar_profile_visualization_2024.png

Paneles incluidos:
   1. Perfil diario promedio (24h)
   2. Energía mensual
   3. Variación semanal
   4. Heatmap potencia mensual-horario
   5. Distribución GHI (radiación)
   6. Curva de duración de potencia
   7. Distribución de energía diaria
   8. Porcentaje de tiempo > umbral
   9. Tabla de estadísticas completa

Todos los datos están ACTUALIZADOS para 2024.
""")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
