#!/usr/bin/env python3
import json, pathlib
BASE = pathlib.Path(__file__).resolve().parents[1]

bl = json.loads((BASE/'checkpoints/Baseline/baseline_results.json').read_text('utf-8'))
print('=== BASELINE ===')
print('annual_kwh:', bl['annual_kwh'])
print('annual_co2:', bl['annual_co2_kg'])
print()

for name, fpath in [
    ('SAC', 'outputs/sac_training/result_sac.json'),
    ('A2C', 'outputs/a2c_training/result_a2c.json'),
    ('PPO', 'outputs/ppo_training/result_ppo.json'),
]:
    j = json.loads((BASE/fpath).read_text('utf-8'))
    vc = j.get('vehicle_charging', {})
    sm = j.get('summary_metrics', {})
    v  = j.get('validation', {})
    te = j.get('training_evolution', {})
    print(f'=== {name} ===')
    print('vehicle_charging:', json.dumps(vc, indent=2))
    for k in ['total_ev_charging_peak_kwh','total_ev_charging_offpeak_kwh',
              'energy_validation','total_co2_avoided_direct_kg','total_co2_avoided_indirect_kg',
              'total_co2_avoided_kg']:
        print(f'  SM.{k} = {sm.get(k, "N/A")}')
    print('  VAL:', {k:v[k] for k in ['mean_co2_avoided_kg','mean_grid_import_kwh','mean_solar_kwh']})
    ev_list = te.get('episode_ev_charging', [])
    mc_list = te.get('episode_motos_charged', [])
    mt_list = te.get('episode_mototaxis_charged', [])
    print('  EV_ep50=', ev_list[-1] if ev_list else 0)
    print('  Motos_ep50=', mc_list[-1] if mc_list else 0)
    print('  Mototaxis_ep50=', mt_list[-1] if mt_list else 0)
    print()
