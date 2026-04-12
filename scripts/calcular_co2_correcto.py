#!/usr/bin/env python3
"""
Computa las CO₂ CORRECTAS por agente usando fórmulas reales
(no la constante hardcodeada en summary_metrics).
Imprime todo lo necesario para el informe.
"""
import json, pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
CO2_GRID  = 0.4521   # kg CO₂/kWh  — red diésel Iquitos
CO2_MOTO  = 0.87     # kg CO₂/kWh  — gasolina (IPCC 2006)
CO2_TAXI  = 0.54     # kg CO₂/kWh  — diésel (IPCC 2006)
N_MOTOS   = 270      # motos target/día
N_TAXIS   = 39       # mototaxis target/día
N_TOTAL   = 309      # vehículos target/día

def load(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))

bl = load(BASE / 'checkpoints/Baseline/baseline_results.json')
EV_BL     = bl['annual_kwh']['ev_demand']         # 408,281.5 kWh/año
MALL_BL   = bl['annual_kwh']['mall_demand']        # 12,368,653 kWh/año
CO2_BL    = bl['annual_co2_kg']['co2_total_baseline']  # 5,926,304 kg/año
CO2_DIR_BL = bl['annual_co2_kg']['co2_reduccion_directa_baseline']  # 330,029.7 kg/año
CO2_IND_BL = bl['annual_co2_kg']['co2_indirecto_baseline']           # 5,926,304 kg/año

print("=== BASELINE ===")
print(f"EV demand      = {EV_BL:,.1f} kWh/año")
print(f"Mall demand    = {MALL_BL:,.1f} kWh/año")
print(f"CO2 TOTAL BL   = {CO2_BL:,.1f} kg/año")
print(f"CO2 dir BL     = {CO2_DIR_BL:,.1f} kg/año  (desplaza combustible fósil)")
print(f"CO2 ind BL     = {CO2_IND_BL:,.1f} kg/año  (red diésel: grid total × 0.4521)")
print()

# Verificación fórmula baseline directo
# factor_BL = (N_MOTOS/N_TOTAL) * CO2_MOTO + (N_TAXIS/N_TOTAL) * CO2_TAXI
# CO2_dir_BL_calc = EV_BL * factor_BL
factor_BL = (N_MOTOS/N_TOTAL)*CO2_MOTO + (N_TAXIS/N_TOTAL)*CO2_TAXI
co2_dir_bl_calc = EV_BL * factor_BL
print(f"Verificación fórmula directa BL:")
print(f"  factor = ({N_MOTOS}/{N_TOTAL})×{CO2_MOTO} + ({N_TAXIS}/{N_TOTAL})×{CO2_TAXI} = {factor_BL:.4f}")
print(f"  CO2_dir_calc = {EV_BL:,.1f} × {factor_BL:.4f} = {co2_dir_bl_calc:,.1f} kg/año")
print(f"  CO2_dir_JSON = {CO2_DIR_BL:,.1f} kg/año  (discrepancia={abs(co2_dir_bl_calc-CO2_DIR_BL):,.1f})")
print(f"  Factor implícito en JSON = {CO2_DIR_BL/EV_BL:.6f}")
print()

# Factor implícito real (derivado del JSON)
FACTOR_DIR_REAL = CO2_DIR_BL / EV_BL   # = 330029.7 / 408281.5

agents_cfg = {
    'SAC': 'outputs/sac_training/result_sac.json',
    'A2C': 'outputs/a2c_training/result_a2c.json',
    'PPO': 'outputs/ppo_training/result_ppo.json',
}

results = {}
for name, fpath in agents_cfg.items():
    j = load(BASE / fpath)
    te  = j['training_evolution']
    vc  = j.get('vehicle_charging', {})
    v   = j['validation']
    sm  = j.get('summary_metrics', {})
    eps = int(j['training'].get('episodes_completed', j['training'].get('episodes', 50)))

    # Datos del episodio final (ep 50 = política convergida)
    ev_ep50   = te['episode_ev_charging'][-1]
    mc_ep50   = vc.get('motos_charged_per_episode', te.get('episode_motos_charged',[0]))[-1]
    mt_ep50   = vc.get('mototaxis_charged_per_episode', te.get('episode_mototaxis_charged',[0]))[-1]
    
    # Datos de validación (10 episodios, política determinista)
    grid_val = v.get('mean_grid_import_kwh', 0)
    reward_val = v['mean_reward']
    
    # ─── CO₂ INDIRECTO (red diésel) ────────────────────────────────────────
    # El agente reduce la importación de grid → menos kWh diesel → menos CO₂
    co2_ind_agent = grid_val * CO2_GRID
    
    # ─── CO₂ DIRECTO (desplazamiento combustible fósil) ──────────────────
    # Depende de CUÁNTOS VEHÍCULOS realmente carga el agente
    # Método 1: proporcional a energía cargada usando el factor implícito del JSON
    co2_dir_prop = ev_ep50 * FACTOR_DIR_REAL
    
    # Método 2: usando mezcla de vehículos reales del agente
    if (mc_ep50 + mt_ep50) > 0:
        frac_motos = mc_ep50 / (mc_ep50 + mt_ep50)
        frac_taxis = mt_ep50 / (mc_ep50 + mt_ep50)
    else:
        frac_motos = N_MOTOS / N_TOTAL
        frac_taxis = N_TAXIS / N_TOTAL
    factor_agent = frac_motos * CO2_MOTO + frac_taxis * CO2_TAXI
    co2_dir_vmix  = ev_ep50 * factor_agent
    
    # Datos extra
    delta_ind  = CO2_IND_BL - co2_ind_agent   # CO₂ indirecto evitado (vs BL)
    delta_dir  = CO2_DIR_BL - co2_dir_vmix     # Diferencia directo vs BL (BL tiene max fleet)
    red_pct    = (CO2_BL - co2_ind_agent) / CO2_BL * 100
    dur_min    = j['training']['duration_seconds'] / 60

    print(f"=== {name} (ep50 política convergida) ===")
    print(f"  Motos/día        = {mc_ep50}    Mototaxis/día = {mt_ep50}")
    print(f"  EV cargada ep50  = {ev_ep50:,.0f} kWh/año   ({ev_ep50/EV_BL*100:.1f}% del target)")
    print(f"  Mezcla vehicular = {frac_motos:.3f} motos / {frac_taxis:.3f} taxis")
    print(f"  Factor CO2_dir   = {frac_motos:.3f}×{CO2_MOTO} + {frac_taxis:.3f}×{CO2_TAXI} = {factor_agent:.4f}")
    print()
    print(f"  CO2 DIRECTO (combustible fósil desplazado):")
    print(f"    Método proporcional EV:  {co2_dir_prop:,.1f} kg/año")
    print(f"    Método mezcla vehicular: {co2_dir_vmix:,.1f} kg/año  ← USAR ESTE")
    print(f"    Baseline referencia:     {CO2_DIR_BL:,.1f} kg/año")
    print(f"    Diferencia BL-agente:    {delta_dir:,.1f} kg/año  (si >0, BL desplaza más porque carga más vehículos)")
    print()
    print(f"  CO2 INDIRECTO (grid diésel importado) [validación]:")
    print(f"    grid_import_val = {grid_val:,.0f} kWh/año")
    print(f"    CO2_ind_agent   = {grid_val:,.0f} × {CO2_GRID} = {co2_ind_agent:,.0f} kg/año")
    print(f"    CO2_ind_BL      = {CO2_IND_BL:,.0f} kg/año")
    print(f"    CO2 reducido    = {delta_ind:,.0f} kg/año  ({delta_ind/CO2_IND_BL*100:.1f}% reducción)")
    print()
    print(f"  CO2 TOTAL EVITADO (vs BL completo):")
    total_ev = delta_ind + co2_dir_vmix  # indirecto evitado + directo (lo que no quema el vehículo)
    system_co2 = co2_ind_agent   # lo que emite el sistema con RL
    print(f"    CO2 sistema actual = {system_co2:,.0f} kg/año (solo red)")
    print(f"    Reducción red      = {delta_ind:,.0f} kg/año ({delta_ind/CO2_IND_BL*100:.1f}%)")
    print(f"    Directo evitado    = {co2_dir_vmix:,.0f} kg/año (fossil desplazado)")
    print(f"    Reward validación  = {reward_val:.2f}")
    print(f"    Duración           = {dur_min:.1f} min")
    print()

    results[name] = {
        'motos': mc_ep50, 'taxis': mt_ep50,
        'ev_kwh': ev_ep50, 'ev_pct': ev_ep50/EV_BL*100,
        'frac_motos': frac_motos, 'frac_taxis': frac_taxis,
        'factor_dir': factor_agent,
        'co2_dir': co2_dir_vmix,
        'co2_dir_prop': co2_dir_prop,
        'co2_ind': co2_ind_agent,
        'grid_val': grid_val,
        'delta_ind': delta_ind,
        'delta_dir': CO2_DIR_BL - co2_dir_vmix,
        'red_pct_ind': delta_ind/CO2_IND_BL*100,
        'reward': reward_val,
        'dur': dur_min,
    }

print("=== TABLA RESUMEN: CO2 DIRECTO E INDIRECTO POR ESCENARIO ===")
print(f"{'Escenario':<20} {'CO2 Directo':>18} {'CO2 Indirecto':>18} {'Red CO2 ind%':>14}")
print("-"*72)
print(f"{'BASELINE (sin RL)':.<20} {CO2_DIR_BL:>18,.1f} {CO2_IND_BL:>18,.1f} {'0.0%':>14}")
for name, r in results.items():
    print(f"{name:<20} {r['co2_dir']:>18,.1f} {r['co2_ind']:>18,.1f} {r['red_pct_ind']:>13.1f}%")
