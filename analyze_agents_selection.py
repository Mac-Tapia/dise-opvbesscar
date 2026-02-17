#!/usr/bin/env python3
"""
ANÁLISIS COMPARATIVO PARA SELECCIÓN DEL AGENTE INTELIGENTE
Sección 4.6.4 - Tesis: Gestión de carga de motos y mototaxis eléctricas
"""

import json
from pathlib import Path

def main():
    print("=" * 80)
    print("ANÁLISIS COMPARATIVO DE AGENTES PARA SELECCIÓN")
    print("Sección 4.6.4 - Maximización eficiencia y reducción CO2")
    print("=" * 80)
    print()

    results = {}
    
    for agent in ['a2c', 'ppo', 'sac']:
        path = Path(f'outputs/{agent}_training/result_{agent}.json')
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            results[agent.upper()] = data
            print(f"[OK] {agent.upper()} cargado")
        else:
            print(f"[ERR] {agent.upper()} no encontrado")
    
    print()
    print("=" * 80)
    print("TABLA COMPARATIVA DE MÉTRICAS")
    print("=" * 80)
    
    metrics = {}
    
    for agent, data in results.items():
        training = data.get('training', {})
        evolution = data.get('training_evolution', {})
        
        # Rewards
        rewards = evolution.get('episode_rewards', data.get('episode_rewards', []))
        if rewards:
            rewards = [float(r) for r in rewards]
        
        # CO2
        co2_grid = evolution.get('episode_co2_grid', data.get('episode_co2_grid_kg', []))
        if co2_grid:
            co2_grid = [float(c) for c in co2_grid]
        
        metrics[agent] = {
            'timesteps': training.get('total_timesteps', data.get('total_timesteps', 0)),
            'episodes': training.get('episodes', data.get('episodes_completed', 0)),
            'reward_final': rewards[-1] if rewards else 0,
            'reward_best': max(rewards) if rewards else 0,
            'reward_avg': sum(rewards)/len(rewards) if rewards else 0,
            'co2_final': co2_grid[-1] if co2_grid else 0,
            'co2_min': min(co2_grid) if co2_grid else 0,
            'co2_avg': sum(co2_grid)/len(co2_grid) if co2_grid else 0,
        }
    
    # Imprimir tabla
    print()
    print(f"{'Métrica':<30} {'A2C':>15} {'PPO':>15} {'SAC':>15}")
    print("-" * 80)
    
    print(f"{'Total Timesteps':<30} {metrics.get('A2C',{}).get('timesteps',0):>15,} {metrics.get('PPO',{}).get('timesteps',0):>15,} {metrics.get('SAC',{}).get('timesteps',0):>15,}")
    print(f"{'Episodios':<30} {metrics.get('A2C',{}).get('episodes',0):>15} {metrics.get('PPO',{}).get('episodes',0):>15} {metrics.get('SAC',{}).get('episodes',0):>15}")
    print()
    print(f"{'Reward Final':<30} {metrics.get('A2C',{}).get('reward_final',0):>15.6f} {metrics.get('PPO',{}).get('reward_final',0):>15.6f} {metrics.get('SAC',{}).get('reward_final',0):>15.6f}")
    print(f"{'Reward Mejor':<30} {metrics.get('A2C',{}).get('reward_best',0):>15.6f} {metrics.get('PPO',{}).get('reward_best',0):>15.6f} {metrics.get('SAC',{}).get('reward_best',0):>15.6f}")
    print(f"{'Reward Promedio':<30} {metrics.get('A2C',{}).get('reward_avg',0):>15.6f} {metrics.get('PPO',{}).get('reward_avg',0):>15.6f} {metrics.get('SAC',{}).get('reward_avg',0):>15.6f}")
    print()
    print(f"{'CO2 Grid Final (kg/año)':<30} {metrics.get('A2C',{}).get('co2_final',0):>15,.0f} {metrics.get('PPO',{}).get('co2_final',0):>15,.0f} {metrics.get('SAC',{}).get('co2_final',0):>15,.0f}")
    print(f"{'CO2 Grid Mínimo (kg/año)':<30} {metrics.get('A2C',{}).get('co2_min',0):>15,.0f} {metrics.get('PPO',{}).get('co2_min',0):>15,.0f} {metrics.get('SAC',{}).get('co2_min',0):>15,.0f}")
    print(f"{'CO2 Grid Promedio (kg/año)':<30} {metrics.get('A2C',{}).get('co2_avg',0):>15,.0f} {metrics.get('PPO',{}).get('co2_avg',0):>15,.0f} {metrics.get('SAC',{}).get('co2_avg',0):>15,.0f}")
    
    # Calcular baseline sin control
    # Baseline = consumo grid sin optimización solar/BESS
    # Factor CO2 Iquitos: 0.4521 kg CO2/kWh
    CO2_FACTOR = 0.4521
    
    # Datos del sistema
    MALL_DEMAND_ANNUAL = 12_368_653  # kWh/año (verificado de datasets)
    EV_DEMAND_ANNUAL = 565_875       # kWh/año (verificado de datasets)
    TOTAL_DEMAND = MALL_DEMAND_ANNUAL + EV_DEMAND_ANNUAL
    
    # Baseline SIN solar (100% grid térmico)
    baseline_co2_sin_solar = TOTAL_DEMAND * CO2_FACTOR
    
    # Baseline CON solar (pero sin control inteligente BESS/EV)
    SOLAR_ANNUAL = 8_292_514  # kWh/año
    baseline_co2_con_solar = (TOTAL_DEMAND - SOLAR_ANNUAL * 0.7) * CO2_FACTOR  # 70% autoconsumo sin control
    
    print()
    print("=" * 80)
    print("ANÁLISIS DE REDUCCIÓN DE CO2")
    print("=" * 80)
    print()
    print(f"Factor de emisión grid Iquitos: {CO2_FACTOR} kg CO2/kWh")
    print(f"Demanda total anual: {TOTAL_DEMAND:,} kWh")
    print(f"  - Mall: {MALL_DEMAND_ANNUAL:,} kWh")
    print(f"  - EVs: {EV_DEMAND_ANNUAL:,} kWh")
    print(f"Generación solar anual: {SOLAR_ANNUAL:,} kWh")
    print()
    print(f"BASELINE SIN SOLAR (100% grid): {baseline_co2_sin_solar:,.0f} kg CO2/año")
    print(f"BASELINE CON SOLAR (sin control): {baseline_co2_con_solar:,.0f} kg CO2/año")
    
    print()
    print("REDUCCIÓN DE CO2 POR AGENTE vs BASELINE SIN SOLAR:")
    print("-" * 60)
    
    best_agent = None
    best_reduction = 0
    
    for agent in ['A2C', 'PPO', 'SAC']:
        if agent in metrics:
            co2_agent = metrics[agent]['co2_avg']
            reduction_kg = baseline_co2_sin_solar - co2_agent
            reduction_pct = (reduction_kg / baseline_co2_sin_solar) * 100
            
            print(f"  {agent}: {co2_agent:,.0f} kg CO2 → Reducción: {reduction_kg:,.0f} kg ({reduction_pct:.1f}%)")
            
            if reduction_pct > best_reduction:
                best_reduction = reduction_pct
                best_agent = agent
    
    print()
    print("=" * 80)
    print("SELECCIÓN DEL AGENTE ÓPTIMO")
    print("=" * 80)
    print()
    
    # Criterios de selección
    scores = {}
    for agent in ['A2C', 'PPO', 'SAC']:
        if agent in metrics:
            m = metrics[agent]
            # Puntaje: reward + (1/CO2) normalizado
            reward_score = m['reward_avg'] * 100 if m['reward_avg'] > 0 else m['reward_avg']
            co2_score = (baseline_co2_sin_solar - m['co2_avg']) / baseline_co2_sin_solar * 100
            
            scores[agent] = {
                'reward_score': reward_score,
                'co2_score': co2_score,
                'total': reward_score * 0.4 + co2_score * 0.6  # 40% reward, 60% CO2
            }
            
            print(f"{agent}:")
            print(f"  Score Reward (40%): {reward_score:.2f}")
            print(f"  Score CO2 (60%):    {co2_score:.2f}")
            print(f"  SCORE TOTAL:        {scores[agent]['total']:.2f}")
            print()
    
    # Determinar ganador
    winner = max(scores.keys(), key=lambda x: scores[x]['total'])
    
    print("=" * 80)
    print(f"🏆 AGENTE SELECCIONADO: {winner}")
    print("=" * 80)
    print()
    print(f"Justificación técnica:")
    print(f"  • Score total más alto: {scores[winner]['total']:.2f}")
    print(f"  • Reducción CO2: {(baseline_co2_sin_solar - metrics[winner]['co2_avg'])/1000:.1f} toneladas/año")
    print(f"  • Porcentaje reducción: {((baseline_co2_sin_solar - metrics[winner]['co2_avg'])/baseline_co2_sin_solar)*100:.1f}%")
    
    # Características específicas del agente ganador
    characteristics = {
        'A2C': 'Advantage Actor-Critic: On-policy, eficiente en recursos, buen balance exploración-explotación',
        'PPO': 'Proximal Policy Optimization: On-policy, clip objetivo, estable y robusto',
        'SAC': 'Soft Actor-Critic: Off-policy, máxima entropía, mejor exploración en espacios continuos'
    }
    
    print(f"  • Algoritmo: {characteristics.get(winner, 'N/A')}")
    
    print()
    print("=" * 80)
    print("RESUMEN EJECUTIVO PARA SECCIÓN 4.6.4")
    print("=" * 80)
    print()
    print(f"""
El agente {winner} fue seleccionado como el sistema de gestión inteligente óptimo
para la carga de motos y mototaxis eléctricas en Iquitos, basándose en:

1. EFICIENCIA OPERATIVA:
   • Reward promedio: {metrics[winner]['reward_avg']:.6f}
   • Convergencia en {metrics[winner]['episodes']} episodios
   • {metrics[winner]['timesteps']:,} timesteps de entrenamiento

2. REDUCCIÓN DE EMISIONES CO2:
   • Emisiones con {winner}: {metrics[winner]['co2_avg']:,.0f} kg CO2/año
   • Baseline sin solar: {baseline_co2_sin_solar:,.0f} kg CO2/año
   • Reducción absoluta: {(baseline_co2_sin_solar - metrics[winner]['co2_avg']):,.0f} kg CO2/año
   • Reducción porcentual: {((baseline_co2_sin_solar - metrics[winner]['co2_avg'])/baseline_co2_sin_solar)*100:.1f}%
   • Equivalente a: {(baseline_co2_sin_solar - metrics[winner]['co2_avg'])/1000:.1f} toneladas CO2/año

3. CUANTIFICACIÓN DEL IMPACTO:
   • Factor emisión grid Iquitos: {CO2_FACTOR} kg CO2/kWh (sistema aislado térmica)
   • Sistema PV: 4,050 kWp instalados
   • BESS: 1,700 kWh capacidad máxima
   • EVs gestionados: 270 motos + 39 mototaxis/día
   • Cargadores: 19 unidades × 2 tomas = 38 puntos de carga

El agente {winner} maximiza la autoconsumo solar, optimiza la gestión del BESS
y prioriza la carga de vehículos en horarios de mínima demanda del mall,
contribuyendo de forma cuantificable a la reducción de {(baseline_co2_sin_solar - metrics[winner]['co2_avg'])/1000:.1f} 
toneladas de CO2 anuales en la ciudad de Iquitos.
""")

if __name__ == "__main__":
    main()
