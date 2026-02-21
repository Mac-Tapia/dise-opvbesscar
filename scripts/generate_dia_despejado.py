#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gráfica: Día Despejado Representativo - 2024
================================================================================

Genera gráfica de un día despejado con:
- Barras: Energía 15 min (kWh)
- Línea: Potencia AC (kW)
- Información: Fecha, energía total, potencia máxima, horas de generación

Ejecución:
    cd d:\\diseñopvbesscar
    python scripts/generate_dia_despejado.py
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

# Configurar estilo
rcParams['figure.figsize'] = (14, 6)
rcParams['font.size'] = 10
rcParams['axes.labelsize'] = 10
rcParams['axes.titlesize'] = 11
rcParams['xtick.labelsize'] = 9
rcParams['ytick.labelsize'] = 9
rcParams['legend.fontsize'] = 9
rcParams['figure.titlesize'] = 12


def load_solar_data():
    """Carga datos solares reales de 8,760 puntos horarios."""
    try:
        csv_path = Path(__file__).parent.parent / 'data' / 'oe2' / 'Generacionsolar' / 'pv_generation_hourly_citylearn_v2.csv'
        df = pd.read_csv(csv_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        return df
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        sys.exit(1)


def find_clear_day(df):
    """Encuentra el día más despejado (máxima radiación GHI)."""
    df['day'] = df['datetime'].dt.date
    daily_irr = df.groupby('day')['ghi_wm2'].sum().sort_values(ascending=False)
    
    # Obtener el día con mayor irradiancia
    clear_day = daily_irr.index[0]
    
    # Obtener datos del día
    day_data = df[df['day'] == clear_day].copy()
    day_data = day_data.sort_values('datetime')
    
    return day_data, clear_day


def calculate_15min_energy(hourly_data):
    """Convierte datos horarios a energía en intervalos de 15 minutos."""
    # Asumimos que la energía horaria se distribuye uniformemente en 4 intervalos de 15 min
    energy_15min = hourly_data['ac_energy_kwh'].values / 4
    power_kw = hourly_data['ac_power_kw'].values
    
    return energy_15min, power_kw


def generate_dia_despejado():
    """Genera gráfica de día despejado representativo."""
    print("✓ Cargando datos solares...")
    df = load_solar_data()
    print(f"✓ Datos cargados: {len(df)} filas × {len(df.columns)} columnas")
    
    print("✓ Buscando día despejado...")
    day_data, clear_day_date = find_clear_day(df)
    
    # Calcular métricas del día
    energy_15min, power_kw = calculate_15min_energy(day_data)
    total_energy = day_data['ac_energy_kwh'].sum()
    max_power = day_data['ac_power_kw'].max()
    
    # Horas de generación (cuando potencia > 100 kW)
    generation_hours = (day_data['ac_power_kw'] > 100).sum()
    
    # Crear vista de 15 minutos para más detalle
    hours = np.arange(24)
    horas_15min = np.arange(0, 24 + 0.25, 0.25)  # Intervalos de 15 minutos
    energy_15min_expanded = np.append(energy_15min, [0] * (4 * 24 - len(energy_15min)))
    energy_15min_expanded = energy_15min_expanded[:4*24]
    
    power_expanded = np.repeat(power_kw, 4)[:4*24]
    
    # =========================================================================
    # CREAR FIGURA
    # =========================================================================
    print("✓ Creando figura de día despejado...")
    
    fig, ax1 = plt.subplots(figsize=(14, 6))
    
    # Título con información del día
    title_text = (f"Día Despejado Representativo {clear_day_date} | "
                 f"Energía total: {total_energy:,.1f} kWh | "
                 f"Potencia máxima: {max_power:,.0f} kW")
    fig.suptitle(title_text, fontsize=12, fontweight='bold', y=0.98)
    
    # =========================================================================
    # PANEL: Energía 15 min (barras) + Potencia AC (línea)
    # =========================================================================
    
    # Eje Y izquierdo: Energía 15 min
    color_energia = '#FFC000'
    ax1.set_xlabel('Hora del día', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Energía 15 min (kWh)', fontsize=11, fontweight='bold', color=color_energia)
    
    # Barras de energía 15 min
    bars = ax1.bar(horas_15min[:-1], energy_15min_expanded, width=0.24, 
                   color=color_energia, alpha=0.8, edgecolor='darkorange', linewidth=0.5,
                   label='Energía 15 min (kWh)')
    
    ax1.tick_params(axis='y', labelcolor=color_energia)
    ax1.set_xlim(0, 24)
    
    # Eje Y derecho: Potencia AC
    ax2 = ax1.twinx()
    color_potencia = '#0066CC'
    ax2.set_ylabel('Potencia AC (kW)', fontsize=11, fontweight='bold', color=color_potencia)
    
    # Línea de potencia
    line = ax2.plot(horas_15min[:-1], power_expanded, color=color_potencia, linewidth=3,
                   marker='o', markersize=4, label='Potencia AC (kW)', zorder=5)
    
    ax2.tick_params(axis='y', labelcolor=color_potencia)
    ax2.set_ylim(0, max_power * 1.1)
    
    # Ajustar y1
    ax1.set_ylim(0, energy_15min_expanded.max() * 1.3)
    
    # =========================================================================
    # ANOTACIONES
    # =========================================================================
    
    # Información en la esquina superior izquierda
    info_text = f"(Horas de generación: {generation_hours/4:.1f} h)"
    ax1.text(0.02, 0.95, info_text, transform=ax1.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    # Leyenda combinada
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=10, framealpha=0.95)
    
    # Grid
    ax1.grid(True, alpha=0.3)
    
    # Xticks en intervalos de 2 horas
    ax1.set_xticks(np.arange(0, 25, 2))
    ax1.set_xticklabels([f'{int(h):02d}' for h in np.arange(0, 25, 2)], fontsize=9)
    
    plt.tight_layout()
    
    # =========================================================================
    # SALVAR FIGURA
    # =========================================================================
    print("✓ Guardando gráfica...")
    save_matplotlib_figure(fig, 'dia_despejado_representativo_2024.png')
    print(f"✅ GRÁFICA GENERADA: outputs\\analysis\\solar\\dia_despejado_representativo_2024.png")
    
    plt.close(fig)


def main():
    """Función principal."""
    print("\n" + "="*80)
    print("📊 GENERADOR: Día Despejado Representativo - 2024")
    print("="*80 + "\n")
    
    generate_dia_despejado()
    
    print("\n" + "="*80)
    print("✅ PROCESO COMPLETADO")
    print("="*80)
    print("\nGráfica guardada en:")
    print("   └─ outputs/analysis/solar/dia_despejado_representativo_2024.png")
    print("\nContenido:")
    print("   • Energía 15 min (barras amarillas)")
    print("   • Potencia AC (línea azul)")
    print("   • Información: fecha, energía total, potencia máxima, horas de generación")
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()
