#!/usr/bin/env python3
"""
Regenerar gráfica 03_bess_operacion.png con datos correctos
Muestra: Carga BESS, Descarga BESS, Flujos de energía
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def main():
    """Regenerar gráfica de operación BESS"""
    
    project_root = Path(__file__).parent.parent
    
    print("[1/3] Cargando datos de simulación BESS...")
    bess_file = project_root / "data" / "interim" / "oe2" / "bess" / "bess_ano_2024.csv"
    
    if not bess_file.exists():
        print(f"ERROR: No se encuentra {bess_file}")
        sys.exit(1)
    
    df_sim = pd.read_csv(bess_file)
    
    if 'datetime' in df_sim.columns:
        df_sim['datetime'] = pd.to_datetime(df_sim['datetime'])
        df_sim.set_index('datetime', inplace=True)
    
    # Promediar por hora del día
    print("[2/3] Calculando promedio horario...")
    df_sim_copy = df_sim.copy()
    if isinstance(df_sim_copy.index, pd.DatetimeIndex):
        df_sim_copy['hour'] = df_sim_copy.index.hour
    else:
        df_sim_copy['hour'] = np.arange(len(df_sim_copy)) % 24
    
    numeric_cols = df_sim_copy.select_dtypes(include=['number']).columns.tolist()
    if 'hour' in numeric_cols:
        numeric_cols.remove('hour')
    
    df_day = df_sim_copy[numeric_cols + ['hour']].groupby('hour').mean().reset_index()
    
    all_hours = pd.DataFrame({'hour': range(24)})
    df_day = all_hours.merge(df_day, on='hour', how='left').fillna(0)
    
    hours = df_day['hour'].values
    
    # Extraer datos
    pv = df_day.get('pv_kwh', 0)
    if isinstance(pv, (int, float)):
        pv = df_day.get('pv_generation_kw', np.zeros(len(df_day))).values
    else:
        pv = pv.values if hasattr(pv, 'values') else pv
    
    bess_charge = df_day.get('bess_charge_kwh', np.zeros(len(df_day)))
    bess_charge = bess_charge.values if hasattr(bess_charge, 'values') else bess_charge
    
    bess_discharge = df_day.get('bess_discharge_kwh', np.zeros(len(df_day)))
    bess_discharge = bess_discharge.values if hasattr(bess_discharge, 'values') else bess_discharge
    
    grid_import = df_day.get('grid_import_total_kwh', df_day.get('demand_from_grid_kw', np.zeros(len(df_day))))
    grid_import = grid_import.values if hasattr(grid_import, 'values') else grid_import
    
    ev_demand = df_day.get('ev_kwh', df_day.get('ev_demand_kwh', np.zeros(len(df_day))))
    ev_demand = ev_demand.values if hasattr(ev_demand, 'values') else ev_demand
    
    print(f"Datos extraídos:")
    print(f"  PV total: {pv.sum():,.0f} kWh/año")
    print(f"  BESS carga: {bess_charge.sum():,.0f} kWh/año")
    print(f"  BESS descarga: {bess_discharge.sum():,.0f} kWh/año")
    print(f"  Grid importado: {grid_import.sum():,.0f} kWh/año")
    
    # Crear figura
    print("[3/3] Creando gráfica...")
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Generación solar (área amarilla)
    ax.fill_between(hours, 0, pv, color='yellow', alpha=0.35, label='Generación Solar PV')
    
    # BARRAS DE CARGA BESS: verdes hacia arriba
    ax.bar(hours, bess_charge, width=0.7, color='green', alpha=0.8, edgecolor='darkgreen',
            linewidth=1.5, label='Carga BESS (solar → batería)', zorder=4)
    
    # BARRAS DE DESCARGA BESS: naranjas desplazadas
    ax.bar(np.array(hours) + 0.35, bess_discharge, width=0.35, color='orange', alpha=0.8, 
            edgecolor='darkorange', linewidth=1.5, label='Descarga BESS (batería → EV)', zorder=4)
    
    # CURVA RED PÚBLICA: linea roja
    ax.plot(hours, grid_import, 'r-', linewidth=3, marker='x', markersize=7,
             label=f'Importación Red Pública', zorder=6)
    ax.fill_between(hours, 0, grid_import, color='red', alpha=0.15, zorder=2)
    
    # PERFIL EV: línea magenta
    ax.plot(hours, ev_demand, 'm-', linewidth=3, marker='o', markersize=6,
             label=f'Demanda EV', zorder=5)
    
    ax.set_xlabel('Hora del Día', fontsize=13, fontweight='bold')
    ax.set_ylabel('Energía (kWh)', fontsize=13, fontweight='bold')
    ax.set_title('Panel 3: Operación BESS - Flujos de Energía', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(range(24))
    ax.set_xticklabels([f'{h:02d}h' for h in range(24)], fontsize=11, fontweight='bold', rotation=45)
    
    # Línea de cierre a las 22h
    ax.axvline(x=22, color='red', linestyle='-', linewidth=2.5, alpha=0.8, zorder=10)
    ax.axvspan(22, 24, alpha=0.15, color='gray', zorder=1)
    
    ax.grid(True, alpha=0.3, linestyle=':', axis='y')
    ax.legend(loc='upper left', fontsize=11, framealpha=0.95, edgecolor='black', ncol=2)
    
    # Métricas
    bess_charge_total = bess_charge.sum()
    bess_discharge_total = bess_discharge.sum()
    grid_total = grid_import.sum()
    ev_total = ev_demand.sum()
    pv_total = pv.sum()
    
    # Calcular ciclos
    cycles_per_day = bess_charge_total / 2000 if bess_charge_total > 0 else 0
    
    metrics_text = (
        f'BALANCE BESS:\n'
        f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Carga (solar):   {bess_charge_total:>10,.0f} kWh/año\n'
        f'Descarga (EV):   {bess_discharge_total:>10,.0f} kWh/año\n'
        f'Ciclos/día:      {cycles_per_day:>10.2f}\n'
        f'\n'
        f'DEMANDA EV:\n'
        f'Total:           {ev_total:>10,.0f} kWh/año\n'
        f'Desde BESS:      {bess_discharge_total:>10,.0f} kWh/año\n'
        f'Desde Red:       {max(grid_total - (pv_total - bess_charge_total), 0):>10,.0f} kWh/año\n'
    )
    
    ax.text(0.02, 0.40, metrics_text, transform=ax.transAxes, fontsize=9, family='monospace',
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round', facecolor='#FFFACD', alpha=0.9, edgecolor='orange', linewidth=2))
    
    plt.tight_layout()
    
    output_dir = project_root / "reports" / "oe2" / "bess"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "03_bess_operacion.png"
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\n✅ Gráfica regenerada: {output_file}")
    print(f"\nOperación BESS:")
    print(f"  • Carga (solar):   {bess_charge_total:>10,.0f} kWh/año")
    print(f"  • Descarga (EV):   {bess_discharge_total:>10,.0f} kWh/año")
    print(f"  • Ciclos/día:      {cycles_per_day:>10.2f}")
    print(f"  • PV generado:     {pv_total:>10,.0f} kWh/año")
    print(f"  • Red importada:   {grid_total:>10,.0f} kWh/año")

if __name__ == '__main__':
    main()
