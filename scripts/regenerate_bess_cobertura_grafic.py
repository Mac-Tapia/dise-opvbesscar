#!/usr/bin/env python3
"""
Regenerar gráfica 04_bess_cobertura_ev.png con datos correctos del archivo bess.py

Gráfica muestra cómo se cubre la demanda EV:
- PV directo a EV
- BESS a EV
- Grid a EV
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Constantes
BESS_CAPACITY_KWH = 2000.0
BESS_POWER_KW = 400.0

def main():
    """Regenerar gráfica de cobertura EV"""
    
    project_root = Path(__file__).parent.parent
    
    # Cargar datos del BESS ya simulado
    print("[1/4] Cargando datos de simulación BESS...")
    bess_file = project_root / "data" / "interim" / "oe2" / "bess" / "bess_ano_2024.csv"
    
    if not bess_file.exists():
        print(f"ERROR: No se encuentra {bess_file}")
        sys.exit(1)
    
    df_sim = pd.read_csv(bess_file)
    print(f"Datos cargados: {len(df_sim)} filas")
    
    # Convertir datetime si existe
    if 'datetime' in df_sim.columns:
        df_sim['datetime'] = pd.to_datetime(df_sim['datetime'])
        df_sim.set_index('datetime', inplace=True)
    
    # Promediar por hora del día
    print("[2/4] Calculando promedio horario...")
    df_sim_copy = df_sim.copy()
    if isinstance(df_sim_copy.index, pd.DatetimeIndex):
        df_sim_copy['hour'] = df_sim_copy.index.hour
    else:
        df_sim_copy['hour'] = np.arange(len(df_sim_copy)) % 24
    
    numeric_cols = df_sim_copy.select_dtypes(include=['number']).columns.tolist()
    if 'hour' in numeric_cols:
        numeric_cols.remove('hour')
    
    df_day = df_sim_copy[numeric_cols + ['hour']].groupby('hour').mean().reset_index()
    
    # Completar 24 horas
    all_hours = pd.DataFrame({'hour': range(24)})
    df_day = all_hours.merge(df_day, on='hour', how='left').fillna(0)
    
    # Datos por hora - usar nombres correctos de columnas
    hours = df_day['hour'].values
    
    # Buscar columnas con diferentes nombres posibles
    pv_to_ev = df_day.get('pv_to_ev_kwh', np.zeros(len(df_day))).values
    bess_to_ev = df_day.get('bess_to_ev_kwh', np.zeros(len(df_day))).values
    grid_to_ev = df_day.get('grid_to_ev_kwh', df_day.get('grid_import_ev_kwh', np.zeros(len(df_day)))).values
    ev_demand = df_day.get('ev_kwh', df_day.get('ev_demand_kwh', np.zeros(len(df_day)))).values
    
    print(f"\nDatos extraídos:")
    print(f"  PV → EV anual: {pv_to_ev.sum():,.0f} kWh")
    print(f"  BESS → EV anual: {bess_to_ev.sum():,.0f} kWh")
    print(f"  Grid → EV anual: {grid_to_ev.sum():,.0f} kWh")
    print(f"  EV Total anual: {ev_demand.sum():,.0f} kWh")
    
    # Crear figura
    print("[3/4] Creando gráfica...")
    fig, ax = plt.subplots(figsize=(14, 6))
    
    width = 0.6
    
    # Barras apiladas: PV → BESS → Grid
    ax.bar(hours, pv_to_ev, width=width, label='PV Directo a EV', color='#FFD700', edgecolor='orange', linewidth=1.5, alpha=0.9)
    ax.bar(hours, bess_to_ev, width=width, bottom=pv_to_ev, label='BESS a EV', color='#228B22', edgecolor='darkgreen', linewidth=1.5, alpha=0.9)
    ax.bar(hours, grid_to_ev, width=width, bottom=pv_to_ev+bess_to_ev, label='Red Pública a EV', color='#DC143C', edgecolor='darkred', linewidth=1.5, alpha=0.9)
    
    # Curva de demanda EV
    ax.plot(hours, ev_demand, 'b-', linewidth=3.5, marker='o', markersize=6, label='Demanda EV Total', zorder=10)
    
    # Configuración
    ax.set_xlabel('Hora del Día', fontsize=13, fontweight='bold')
    ax.set_ylabel('Energía (kWh)', fontsize=13, fontweight='bold')
    ax.set_title('Panel 4: Cobertura de Demanda EV - PV + BESS + Red Pública', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(range(24))
    ax.set_xticklabels([f'{h:02d}h' for h in range(24)], fontsize=11, fontweight='bold', rotation=45)
    ax.set_ylim(0, max(ev_demand.max() * 1.15, 400))
    
    ax.grid(True, alpha=0.3, linestyle=':', axis='y')
    ax.legend(loc='upper left', fontsize=11, framealpha=0.95, edgecolor='black')
    
    # Métricas
    pv_to_ev_total = pv_to_ev.sum()
    bess_to_ev_total = bess_to_ev.sum()
    grid_to_ev_total = grid_to_ev.sum()
    ev_total = ev_demand.sum()
    
    pv_coverage_pct = (pv_to_ev_total / max(ev_total, 1e-9)) * 100
    bess_coverage_pct = (bess_to_ev_total / max(ev_total, 1e-9)) * 100
    grid_coverage_pct = (grid_to_ev_total / max(ev_total, 1e-9)) * 100
    
    metrics_text = (
        f'COBERTURA DE DEMANDA EV:\n'
        f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Demanda Total:        {ev_total:>10,.0f} kWh/año\n'
        f'\n'
        f'PV Directo:           {pv_to_ev_total:>10,.0f} kWh ({pv_coverage_pct:>5.1f}%)\n'
        f'BESS:                 {bess_to_ev_total:>10,.0f} kWh ({bess_coverage_pct:>5.1f}%)\n'
        f'Red Pública:          {grid_to_ev_total:>10,.0f} kWh ({grid_coverage_pct:>5.1f}%)\n'
        f'\n'
        f'Autosuficiencia:      {(pv_coverage_pct + bess_coverage_pct):>10.1f}%\n'
    )
    
    ax.text(0.02, 0.40, metrics_text, transform=ax.transAxes, fontsize=10, family='monospace',
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round', facecolor='#FFFACD', alpha=0.95, edgecolor='black', linewidth=1.5))
    
    # Línea de cierre
    ax.axvline(x=22, color='red', linestyle='-', linewidth=2.5, alpha=0.7, label='Cierre 22h')
    
    plt.tight_layout()
    
    # Guardar
    output_dir = project_root / "reports" / "oe2" / "bess"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "04_bess_cobertura_ev.png"
    
    print(f"[4/4] Guardando en {output_file}...")
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\n✅ Gráfica regenerada: {output_file}")
    print(f"\nResumen de cobertura:")
    print(f"  • PV → EV:   {pv_to_ev_total:>10,.0f} kWh/año ({pv_coverage_pct:>5.1f}%)")
    print(f"  • BESS → EV: {bess_to_ev_total:>10,.0f} kWh/año ({bess_coverage_pct:>5.1f}%)")
    print(f"  • RED → EV:  {grid_to_ev_total:>10,.0f} kWh/año ({grid_coverage_pct:>5.1f}%)")
    print(f"  • TOTAL EV:  {ev_total:>10,.0f} kWh/año")

if __name__ == '__main__':
    main()
