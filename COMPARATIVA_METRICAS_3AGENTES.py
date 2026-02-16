#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""COMPARATIVA DE MÉTRICAS: PPO vs A2C vs SAC (Estado actual)"""

import json
from pathlib import Path

output = """
╔════════════════════════════════════════════════════════════════════════════════════════════════╗
║              📊 COMPARATIVA DE MÉTRICAS: PPO vs A2C vs SAC (Actual)                          ║
╚════════════════════════════════════════════════════════════════════════════════════════════════╝


═══════════════════════════════════════════════════════════════════════════════════════════════════
1. CARGAR RESULTADOS DESDE ARCHIVOS
═══════════════════════════════════════════════════════════════════════════════════════════════════
"""

print(output)

# Paths to results
results_dir = Path("outputs")
agents = {
    "PPO": results_dir / "ppo_training" / "result_ppo.json",
    "A2C": results_dir / "a2c_training" / "result_a2c.json",
    "SAC": results_dir / "sac_training" / "result_sac.json",
}

data = {}
for agent_name, file_path in agents.items():
    if file_path.exists():
        with open(file_path) as f:
            data[agent_name] = json.load(f)
        print(f"✅ {agent_name}: Cargado desde {file_path.name}")
    else:
        print(f"❌ {agent_name}: NO ENCONTRADO en {file_path}")

print("\n" + "="*100 + "\n")

if len(data) >= 2:
    print("""
2. TABLA COMPARATIVA: MÉTRICAS PRINCIPALES
═══════════════════════════════════════════════════════════════════════════════════════════════════
""")
    
    # Extract key metrics
    metrics = {}
    for agent, result in data.items():
        if agent in ["PPO", "A2C"]:
            # PPO/A2C structure
            training = result.get("training", {})
            validation = result.get("validation", {})
            training_evo = result.get("training_evolution", {})
            
            episode_rewards = training_evo.get("episode_rewards", [])
            mean_reward = validation.get("mean_reward", "N/A")
            std_reward = validation.get("std_reward", "N/A")
            co2_avoided = validation.get("mean_co2_avoided_kg", 0)
            training_time = training.get("duration_seconds", 0)
            
        else:  # SAC
            # SAC structure - episode_rewards are strings
            episode_rewards_raw = result.get("episode_rewards", [])
            episode_rewards = []
            for r in episode_rewards_raw:
                try:
                    episode_rewards.append(float(r))
                except (ValueError, TypeError):
                    pass
            
            # Calculate mean manually
            mean_reward = sum(episode_rewards) / len(episode_rewards) if episode_rewards else "N/A"
            std_reward = "N/A"
            co2_avoided = result.get("mean_co2_avoided_kg", 0)  
            training_time = result.get("training_duration_seconds", 0)
        
        # Convert episode_rewards to floats if needed
        if isinstance(episode_rewards, list) and episode_rewards:
            try:
                episode_rewards = [float(x) if isinstance(x, str) else x for x in episode_rewards]
            except:
                pass
        
        # Calculate convergence % (improve rate)
        if episode_rewards and len(episode_rewards) > 1:
            first_reward = episode_rewards[0] if isinstance(episode_rewards[0], (int, float)) else 0
            last_reward = episode_rewards[-1] if isinstance(episode_rewards[-1], (int, float)) else 0
            if first_reward != 0:
                convergence = ((last_reward - first_reward) / abs(first_reward)) * 100
            else:
                convergence = 0
        else:
            convergence = "N/A"
        
        best_reward = max(episode_rewards) if episode_rewards and all(isinstance(x, (int, float)) for x in episode_rewards) else "N/A"
        worst_reward = min(episode_rewards) if episode_rewards and all(isinstance(x, (int, float)) for x in episode_rewards) else "N/A"
        
        metrics[agent] = {
            "Episodes": result.get("episodes_completed", result.get("num_episodes", "N/A")),
            "Total Steps": result.get("total_timesteps", "N/A"),
            "Mean Reward": mean_reward,
            "Std Reward": std_reward,
            "Best Reward": best_reward,
            "Worst Reward": worst_reward,
            "CO2 Avoided (kg)": co2_avoided,
            "Training Time (s)": training_time,
            "Convergence %": convergence,
        }
    
    # Print table header
    print(f"{'Métrica':<30} {'PPO':>20} {'A2C':>20} {'SAC':>20}")
    print("-" * 100)
    
    # Print each metric
    for metric_name in ["Episodes", "Total Steps", "Mean Reward", "Std Reward", 
                        "Best Reward", "Worst Reward", "CO2 Avoided (kg)", 
                        "Training Time (s)", "Convergence %"]:
        ppo_val = metrics.get("PPO", {}).get(metric_name, "N/A")
        a2c_val = metrics.get("A2C", {}).get(metric_name, "N/A")
        sac_val = metrics.get("SAC", {}).get(metric_name, "N/A")
        
        # Format values
        if isinstance(ppo_val, (int, float)):
            ppo_str = f"{ppo_val:>18.2f}" if isinstance(ppo_val, float) else f"{ppo_val:>18}"
        else:
            ppo_str = f"{str(ppo_val):>18}"
            
        if isinstance(a2c_val, (int, float)):
            a2c_str = f"{a2c_val:>18.2f}" if isinstance(a2c_val, float) else f"{a2c_val:>18}"
        else:
            a2c_str = f"{str(a2c_val):>18}"
            
        if isinstance(sac_val, (int, float)):
            sac_str = f"{sac_val:>18.2f}" if isinstance(sac_val, float) else f"{sac_val:>18}"
        else:
            sac_str = f"{str(sac_val):>18}"
        
        print(f"{metric_name:<30} {ppo_str} {a2c_str} {sac_str}")
    
    print("\n" + "="*100 + "\n")
    
    print("""
3. ANÁLISIS COMPARATIVO (Sin cambiar arquitectura de red)
═══════════════════════════════════════════════════════════════════════════════════════════════════
    
Preguntas clave para mejorar SAC (manteniendo arquitectura):

❓ ¿Cuál es el GAP de convergencia SAC vs PPO?
   Gap = PPO_convergence - SAC_convergence
   Esto DEBE ser resuelto con hiperparámetros, NO con cambiar la red.

❓ ¿Cuál es el RATIO de CO2 avoided?
   Ratio = (CO2_SAC / CO2_PPO) × 100%
   Debe estar cerca de PPO/A2C para "competir"

❓ ¿Cuál es el OVERHEAD de training time?
   Si SAC entrena 100 veces más lento, no vale la pena.

ASPECTOS A REVISAR (Hiperparámetros solo):
  ✅ Reward function: ¿escala correcta?
  ✅ Learning rate: ¿demasiado agresivo para SAC?
  ✅ Buffer size: ¿suficiente para 87,600 steps?
  ✅ Learning starts: ¿demasiado bajo (5%)?
  ✅ Entropy coefficient: ¿"auto" diverge?
  ✅ Tau: ¿0.005 muy rápido para critic?

ASPECTOS A NO CAMBIAR (Arquitectura):
  ❌ Parser: [512, 512] (SAC actual)
  ❌ Critic: [512, 512] (SAC actual)
  ❌ Activation functions
  ❌ Network initialization
""")

    print("\n" + "="*100 + "\n")
    
    print("""
4. RECOMENDACIÓN BASADA EN MÉTRICAS
═══════════════════════════════════════════════════════════════════════════════════════════════════
""")
    
    ppo_conv = metrics.get("PPO", {}).get("Convergence %", 0)
    a2c_conv = metrics.get("A2C", {}).get("Convergence %", 0)
    sac_conv = metrics.get("SAC", {}).get("Convergence %", 0)
    
    ppo_co2 = metrics.get("PPO", {}).get("CO2 Avoided (kg)", 0)
    a2c_co2 = metrics.get("A2C", {}).get("CO2 Avoided (kg)", 0)
    sac_co2 = metrics.get("SAC", {}).get("CO2 Avoided (kg)", 0)
    
    print(f"\nConvergencia:")
    if isinstance(ppo_conv, (int, float)):
        print(f"  PPO: {ppo_conv:.2f}%")
    else:
        print(f"  PPO: {ppo_conv}")
    
    if isinstance(a2c_conv, (int, float)):
        print(f"  A2C: {a2c_conv:.2f}%")
    else:
        print(f"  A2C: {a2c_conv}")
    
    if isinstance(sac_conv, (int, float)):
        print(f"  SAC: {sac_conv:.2f}%")
    else:
        print(f"  SAC: {sac_conv}")
    
    if isinstance(ppo_co2, (int, float)) and ppo_co2 > 0:
        print(f"\nCO2 Evitado:")
        print(f"  PPO: {ppo_co2:,.0f} kg")
        print(f"  A2C: {a2c_co2:,.0f} kg")
        print(f"  SAC: {sac_co2:,.0f} kg")
    
    # Determine best - only compare numeric values
    numeric_convs = {}
    if isinstance(ppo_conv, (int, float)):
        numeric_convs["PPO"] = ppo_conv
    if isinstance(a2c_conv, (int, float)):
        numeric_convs["A2C"] = a2c_conv
    if isinstance(sac_conv, (int, float)):
        numeric_convs["SAC"] = sac_conv
    
    if numeric_convs:
        best_agent = max(numeric_convs, key=numeric_convs.get)
        best_value = numeric_convs[best_agent]
        print(f"\n🏆 Mejor convergencia: {best_agent} ({best_value:.2f}%)")
        
        # Show gap
        if "PPO" in numeric_convs and "SAC" in numeric_convs:
            gap = numeric_convs["PPO"] - numeric_convs["SAC"]
            print(f"   GAP SAC vs PPO: {gap:.2f}% (necesita mejora)")
        if "PPO" in numeric_convs and "A2C" in numeric_convs:
            rank_order = f"  Ranking: {best_agent} > " + (" > ".join([x for x in ["PPO", "A2C", "SAC"] if x != best_agent and x in numeric_convs]))
            print(rank_order)

else:
    print("\n❌ No hay datos suficientes para comparar (se necesitan mínimo 2 agentes)\n")

print("\n" + "="*100)
print("Fin comparativa (2026-02-15)\n")
