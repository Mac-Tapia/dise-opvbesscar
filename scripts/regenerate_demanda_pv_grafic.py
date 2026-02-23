#!/usr/bin/env python3
"""
Regenerar gráfica 01_demanda_pv.png con datos correctos
Muestra: Demanda Total (MALL + EV) vs PV
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def main():
    """Regenerar gráfica de demanda y PV"""
    
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
    pv = df_day.get('pv_kwh', df_day.get('pv_generation_kw', np.zeros(len(df_day)))).values
    ev_demand = df_day.get('ev_kwh', df_day.get('ev_demand_kwh', np.zeros(len(df_day)))).values
    mall_demand = df_day.get('mall_kwh', df_day.get('mall_demand_kwh', np.zeros(len(df_day)))).values
    
    total_demand = ev_demand + mall_demand
    
    print(f"Datos extraídos:")
    print(f"  PV total: {pv.sum():,.0f} kWh/año")
    print(f"  EV total: {ev_demand.sum():,.0f} kWh/año")
    print(f"  MALL total: {mall_demand.sum():,.0f} kWh/año")
    print(f"  Demanda total: {total_demand.sum():,.0f} kWh/año")
    
    # Crear figura - Panel 1: Demanda Total
    print("[3/3] Creando gráfica...")
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # Demanda mall achurada en azul
    ax.fill_between(hours, 0, mall_demand, color='steelblue', alpha=0.5, hatch='///', edgecolor='blue', label='Demanda Mall')
    ax.bar(hours, ev_demand, bottom=mall_demand, color='salmon', alpha=0.9, label='Vehículos Eléctricos', edgecolor='darkred', linewidth=1)
    ax.plot(hours, total_demand, 'r-', linewidth=3, marker='o', markersize=5, label='Demanda Total', zorder=10)
    
    ax.set_xlabel('Hora del Día', fontsize=13, fontweight='bold')
    ax.set_ylabel('Energía (kWh)', fontsize=13, fontweight='bold')
    ax.set_title('Panel 1: Demanda Energética Total - Mall + Vehículos Eléctricos', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(range(24))
    ax.set_xticklabels([f'{h:02d}h' for h in range(24)], fontsize=11, fontweight='bold', rotation=45)
    
    ax.grid(True, alpha=0.3, linestyle=':', axis='y')
    ax.legend(loc='upper left', fontsize=11, framealpha=0.95, edgecolor='black')
    
    # Métricas
    mall_total = mall_demand.sum()
    ev_total = ev_demand.sum()
    total = total_demand.sum()
    
    metrics_text = (
        f'DEMANDA ENERGÉTICA:\n'
        f'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Mall:           {mall_total:>10,.0f} kWh/año\n'
        f'EV (38 sockets):{ev_total:>10,.0f} kWh/año\n'
        f'TOTAL:          {total:>10,.0f} kWh/año\n'
        f'\n'
        f'Proporción:\n'
        f'  • Mall: {(mall_total/total)*100:>5.1f}%\n'
        f'  • EV:   {(ev_total/total)*100:>5.1f}%\n'
    )
    
    ax.text(0.02, 0.75, metrics_text, transform=ax.transAxes, fontsize=10, family='monospace',
            verticalalignment='top', horizontalalignment='left',
            bbox=dict(boxstyle='round', facecolor='#FFFACD', alpha=0.95, edgecolor='black', linewidth=1.5))
    
    plt.tight_layout()
    
    output_dir = project_root / "reports" / "oe2" / "bess"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "01_demanda_pv.png"
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\n✅ Gráfica regenerada: {output_file}")
    print(f"\nDemanda energética:")
    print(f"  • Mall:  {mall_total:>10,.0f} kWh/año ({(mall_total/total)*100:>5.1f}%)")
    print(f"  • EV:    {ev_total:>10,.0f} kWh/año ({(ev_total/total)*100:>5.1f}%)")
    print(f"  • TOTAL: {total:>10,.0f} kWh/año")

if __name__ == '__main__':
    main()
