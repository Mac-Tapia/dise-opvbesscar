#!/usr/bin/env python
"""Verificar estado final del entrenamiento PPO."""
from pathlib import Path
import pandas as pd
from datetime import datetime

csv_files = sorted(Path('outputs/ppo_training').glob('*.csv'))
if csv_files:
    latest = csv_files[-1]
    df = pd.read_csv(latest)
    
    last_ep = df['episode'].max()
    last_step = df.iloc[-1]
    mod_time = datetime.fromtimestamp(latest.stat().st_mtime).strftime('%H:%M:%S')
    
    print('\n' + '='*70)
    print('📊 ESTADO ENTRENAMIENTO PPO - ' + mod_time)
    print('='*70)
    print(f'✅ Archivo log: {latest.name}')
    print(f'\n📈 Progreso General:')
    print(f'   • Timesteps: {len(df):,} / 87,600')
    print(f'   • Episodios: {int(last_ep)} / 10')
    print(f'   • Porcentaje completado: {(len(df)/87600)*100:.1f}%')
    
    print(f'\n🎮 Episodio {int(last_ep)}:')
    print(f'   • Horas completadas: {int(last_step["step_in_episode"]):,} / 8,760')
    print(f'   • Reward promedio últimos 100 steps: {df.tail(100)["reward"].mean():.4f}')
    print(f'   • Reward máximo últimos 100 steps: {df.tail(100)["reward"].max():.4f}')
    
    ep_df = df[df['episode'] == last_ep]
    co2_ep = (ep_df["co2_avoided_direct_kg"].sum() + 
              ep_df["co2_avoided_indirect_kg"].sum())
    print(f'   • CO₂ evitado acumulado: {co2_ep:,.0f} kg')
    print(f'   • Solar generado: {ep_df["solar_generation_kwh"].sum():,.0f} kWh')
    print(f'   • EV cargado: {ep_df["ev_charging_kwh"].sum():,.0f} kWh')
    
    # Checkpoints
    ckpt_dir = Path('checkpoints/PPO')
    if ckpt_dir.exists():
        ckpts = list(ckpt_dir.glob('*.zip'))
        print(f'\n💾 Checkpoints guardados: {len(ckpts)}')
        if ckpts:
            latest_ckpt = max(ckpts, key=lambda p: p.stat().st_mtime)
            print(f'   • Último: {latest_ckpt.name}')
    
    print('='*70 + '\n')
else:
    print('⏳ Sin logs disponibles')
