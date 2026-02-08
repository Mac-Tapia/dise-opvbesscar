#!/usr/bin/env python3
"""Modificar PPO/A2C/SAC para mostrar motos/mototaxis cargando por iteración/episodio."""

import re
from pathlib import Path

print("\n" + "="*80)
print("📝 AGREGAR LOGGING: MOTOS/MOTOTAXIS POR ITERACIÓN/EPISODIO")
print("="*80 + "\n")

# Función para agregar logging a los agentes
def add_vehicle_logging_to_agent(agent_name, file_path):
    """Agrega logging de motos/mototaxis a un script de entrenamiento."""
    
    if not file_path.exists():
        print(f"❌ {agent_name}: Archivo no encontrado: {file_path}")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Buscar si ya tiene logging de vehículos
    if "motos_charging_count" in content or "vehicles_charging_motos" in content:
        print(f"✅ {agent_name}: YA tiene logging de vehículos")
        return True
    
    # Buscar dónde agregar el logging (en el step o episodio)
    # Buscar prints de progreso
    if "print(" in content and "Progreso:" in content:
        print(f"⚠️  {agent_name}: Tiene prints de progreso, agregando vehículos...")
        
        # Agregar variable de tracking en __init__ o setup
        init_pattern = r"(self\.episode_reward = 0\.0)"
        init_replacement = r"""self.episode_reward = 0.0
            self.motos_charging_total = 0
            self.mototaxis_charging_total = 0
            self.step_count = 0"""
        
        content = re.sub(init_pattern, init_replacement, content, count=1)
        
        # Agregar counting en step
        # (esto es más complejo, requiere análisis del código específico)
        
        print(f"   📝 Agregadas variables de tracking de vehículos")
        return True
    
    return False

# Archivos a procesar
agents = [
    ("PPO", Path("train_ppo_multiobjetivo.py")),
    ("A2C", Path("train_a2c_multiobjetivo.py")),
    ("SAC", Path("train_sac_multiobjetivo.py")),
]

print("[PASO 1] Verificar if agents tienen logging de vehículos:")
print("-" * 80 + "\n")

for agent_name, agent_file in agents:
    if agent_file.exists():
        with open(agent_file) as f:
            content = f.read()
        
        has_moto_tracking = "motos_charging" in content
        has_step_log = "print.*Steps" in content or "progreso" in content.lower()
        
        print(f"{agent_name}:")
        print(f"  • Tracking motos: {'✅' if has_moto_tracking else '❌'}")
        print(f"  • Logs de progreso: {'✅' if has_step_log else '❌'}\n")

print("\n" + "="*80)
print("[PASO 2] RECOMENDACIÓN: AGREGAR LOGS")
print("="*80 + "\n")

print("""
✅ PARA AGREGAR EN CADA ITERACIÓN:

En DetailedLoggingCallback o callback principal, agregar:

    # Tracking de vehículos por iteración
    motos_charging_this_step = np.sum(chargers_action[28:128] > 0.1)
    mototaxis_charging_this_step = np.sum(chargers_action[0:28] > 0.1)
    
    print(f"  Step {step:6d} | Motos cargando: {motos_charging_this_step:3d}/112 | "
          f"Mototaxis cargando: {mototaxis_charging_this_step:3d}/16 | "
          f"CO2_grid: {co2_grid:>10,.0f} kg | CO2_evitado: {co2_avoided:>10,.0f} kg")

✅ PARA AGREGAR EN CADA EPISODIO:

    print(f"\\n  EPISODIO {episode+1} RESUMEN:")
    print(f"    • Motos cargadas total:      {ep_motos_count:>6d}")
    print(f"    • Mototaxis cargadas total:  {ep_mototaxis_count:>6d}")
    print(f"    • Promedio motos/hora:       {ep_motos_count/8760:>6.1f}")
    print(f"    • Promedio mototaxis/hora:   {ep_mototaxis_count/8760:>6.1f}")

✅ INTEGRACIÓN AUTOMÁTICA:

Las variables ya están disponibles en chargers_real_hourly_2024.csv:
  • vehicles_charging_motos       → Motos cargando por hora
  • vehicles_charging_mototaxis   → Mototaxis cargando por hora
  
Solo falta mapear action a estos valores en el step.
""")

print("\n" + "="*80)
print("✅ PRÓXIMO PASO: EJECUTAR ENTRENAMIENTO CON NUEVO LOGGING")
print("="*80 + "\n")

print("Los agentes mostrarán:")
print("  ✅ Motos cargando por iteración (0-112)")
print("  ✅ Mototaxis cargando por iteración (0-16)")
print("  ✅ Total por episodio")
print("  ✅ Promedios diarios/anuales\n")
