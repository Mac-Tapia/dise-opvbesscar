#!/usr/bin/env python
"""Monitor entrenamiento PPO en tiempo real."""
import pandas as pd
from pathlib import Path
import numpy as np
import time
from datetime import datetime

def monitor_training():
    csv_files = sorted(Path('outputs/ppo_training').glob('*.csv'))
    if not csv_files:
        print('⏳ Aún sin logs disponibles')
        return
    
    df = pd.read_csv(csv_files[-1])
    
    print('\n' + '='*75)
    print('📊 MONITOREO ENTRENAMIENTO PPO - ' + datetime.now().strftime('%H:%M:%S'))
    print('='*75)
    
    # Estadísticas generales
    print(f'\n📈 PROGRESO GENERAL:')
    print(f'   • Timesteps ejecutados: {len(df):,} / 87,600')
    print(f'   • Porcentaje completado: {(len(df)/87600)*100:.1f}%')
    print(f'   • Episodios completados: {int(df["episode"].max())-1} / 10')
    
    # Última fila
    last_row = df.iloc[-1]
    print(f'\n⏱️  ÚLTIMO TIMESTEP:')
    print(f'   • Timestep: {int(last_row["timestep"]):,}')
    print(f'   • Recompensa: {float(last_row["reward"]):.4f}')
    print(f'   • CO₂ evitado (directo): {float(last_row["co2_avoided_direct_kg"]):.2f} kg')
    print(f'   • Solar generado: {float(last_row["solar_generation_kwh"]):.2f} kWh')
    print(f'   • EV cargado: {float(last_row["ev_charging_kwh"]):.2f} kWh')
    print(f'   • Grid importado: {float(last_row["grid_import_kwh"]):.2f} kWh')
    
    # Episodio actual
    last_ep = int(df['episode'].max())
    ep_data = df[df['episode'] == last_ep]
    
    if len(ep_data) > 0:
        print(f'\n🎮 EPISODIO {last_ep} (EN PROGRESO):')
        print(f'   • Horas completadas: {len(ep_data)} / 8,760')
        print(f'   • Recompensa promedio: {ep_data["reward"].mean():.4f}')
        print(f'   • Recompensa máxima: {ep_data["reward"].max():.4f}')
        co2_total = (ep_data["co2_avoided_direct_kg"].sum() + ep_data["co2_avoided_indirect_kg"].sum())
        print(f'   • CO₂ total evitado: {co2_total:,.0f} kg')
    
    # Comparativa últimos 3 episodios completados
    print(f'\n📊 DESEMPEÑO ÚLTIMOS 3 EPISODIOS:')
    print(f'   {"Ep":<3} {"Reward Avg":<12} {"Reward Max":<12} {"CO₂ Evitado":<15} {"Solar":<12}')
    print(f'   {"-"*54}')
    
    for ep in sorted(df['episode'].unique())[-3:]:
        ep_df = df[df['episode'] == ep]
        if len(ep_df) == 8760:  # Episodio completado
            print(f'   {int(ep):<3} {ep_df["reward"].mean():<12.4f} {ep_df["reward"].max():<12.4f} {ep_df["co2_avoided_direct_kg"].sum() + ep_df["co2_avoided_indirect_kg"].sum():<15,.0f} {ep_df["solar_generation_kwh"].sum():<12,.0f}')
    
    print('='*75 + '\n')

if __name__ == '__main__':
    monitor_training()
