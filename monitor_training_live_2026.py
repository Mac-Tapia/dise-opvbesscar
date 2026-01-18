#!/usr/bin/env python3
"""
Monitor de Entrenamiento en Vivo - Iquitos EV Smart Charging
Muestra progreso de SAC → PPO → A2C en tiempo real
"""

import time
import json
from pathlib import Path
from datetime import datetime

def get_checkpoint_info(agent_name):
    """Obtiene información de checkpoints de un agente"""
    checkpoint_dir = Path(f"outputs/oe3/checkpoints/{agent_name.lower()}")
    
    if not checkpoint_dir.exists():
        return None
    
    # Buscar el checkpoint más reciente
    checkpoints = list(checkpoint_dir.glob("*.zip"))
    if not checkpoints:
        return None
    
    latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
    file_size_mb = latest.stat().st_size / (1024 * 1024)
    
    # Extraer número de pasos del nombre
    try:
        if "step_" in latest.name:
            steps = int(latest.name.split("step_")[1].split(".")[0])
        elif "final" in latest.name:
            steps = 43800  # Asume entrenamiento completo
        else:
            steps = 0
        return {
            "name": latest.name,
            "size_mb": round(file_size_mb, 2),
            "steps": steps,
            "progress_pct": round((steps / 43800) * 100, 1),
            "modified": latest.stat().st_mtime
        }
    except:
        return None

def get_simulation_results():
    """Obtiene resultados de simulación si existen"""
    results_file = Path("outputs/oe3/simulations/summary.json")
    if results_file.exists():
        try:
            with open(results_file) as f:
                return json.load(f)
        except:
            return None
    return None

def display_progress():
    """Muestra progreso de entrenamiento"""
    print("\n" + "="*80)
    print("🚀 ENTRENAMIENTO SERIAL - MONITOR EN VIVO")
    print("="*80)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    agents = ["SAC", "PPO", "A2C"]
    total_progress = 0
    
    for i, agent in enumerate(agents, 1):
        print(f"[{i}/3] {agent} Agent")
        print("-" * 40)
        
        info = get_checkpoint_info(agent)
        
        if info:
            print(f"  📦 Checkpoint: {info['name']}")
            print(f"  📊 Progreso: {info['progress_pct']}% ({info['steps']}/43,800 pasos)")
            print(f"  💾 Tamaño: {info['size_mb']} MB")
            total_progress += info['progress_pct'] / 3
            
            # Barra de progreso visual
            bar_length = 30
            filled = int((info['progress_pct'] / 100) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"  [{bar}] {info['progress_pct']}%")
        else:
            print(f"  ⏳ Esperando inicio de entrenamiento...")
            print(f"  [{'░'*30}] 0%")
        
        print()
    
    print("="*80)
    print(f"📈 PROGRESO GENERAL: {total_progress:.1f}%")
    
    # Mostrar resultados si existen
    results = get_simulation_results()
    if results:
        print("\n✅ RESULTADOS DISPONIBLES:")
        if "agents" in results:
            for agent_name, metrics in results["agents"].items():
                if "co2_total" in metrics:
                    co2 = metrics["co2_total"]
                    print(f"  • {agent_name}: {co2:,.0f} kg CO₂/año")
    
    print("="*80 + "\n")

def main():
    """Ejecuta el monitor"""
    print("📡 Iniciando monitor de entrenamiento...")
    print("Presiona Ctrl+C para salir\n")
    
    try:
        while True:
            display_progress()
            time.sleep(5)  # Actualizar cada 5 segundos
    except KeyboardInterrupt:
        print("\n🛑 Monitor detenido")

if __name__ == "__main__":
    main()
