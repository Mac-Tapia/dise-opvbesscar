#!/usr/bin/env python
"""
Script para continuar entrenamiento de A2C, SAC, PPO
Con estrategia realista dentro de limitaciones físicas
"""

import subprocess
import sys
import time
from pathlib import Path

def run_training(agent_name: str, config_path: str) -> None:
    """Ejecutar entrenamiento de agente específico."""
    cmd = [sys.executable, "-m", f"scripts.continue_{agent_name.lower()}_training", "--config", config_path]
    
    print(f"\n{'='*100}")
    print(f"🚀 Iniciando entrenamiento: {agent_name}")
    print(f"{'='*100}")
    print(f"Comando: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ {agent_name} completado exitosamente")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {agent_name} falló con código {e.returncode}")
        raise

def main():
    config_path = "configs/default.yaml"
    config = Path(config_path)
    
    if not config.exists():
        print(f"❌ Archivo de config no encontrado: {config_path}")
        sys.exit(1)
    
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║          🎯 PLAN DE ENTRENAMIENTO: A2C + SAC HASTA CONVERGENCIA               ║
║                                                                               ║
║  LIMITACIONES ACEPTADAS:                                                      ║
║    • Red térmica: 0.4521 kg CO₂/kWh (inevitable)                              ║
║    • Demanda Mall: 24.7 GWh/año (fija)                                        ║
║    • PV generación: 8.0 GWh/año (física)                                      ║
║    • BESS capacidad: 2000 kWh (instalado)                                     ║
║                                                                               ║
║  OBJETIVO REALISTA:                                                           ║
║    ✓ Reducir CO₂: 15-20% (baseline 11.3M kg → target < 10.3M kg)             ║
║    ✓ Optimizar grid: 20% menos importación (24.96 → 20 GWh)                  ║
║    ✓ Autoconsumo solar: 50%+ del PV                                           ║
║    ✓ EVs satisfechos: >90% SOC requerido                                      ║
║                                                                               ║
║  TIMELINE:                                                                    ║
║    • A2C: ~9 horas (8,759 → 87,600 pasos)                                     ║
║    • SAC: ~10 horas (1,873 → 100,000 pasos)                                   ║
║    • PPO: SKIP (40 horas demasiado largo)                                     ║
║                                                                               ║
║  GANADOR: SAC (predicción: mejor balance estabilidad+velocidad)              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")
    
    print("\n⏳ OPCIÓN 1: Ejecutar A2C + SAC secuencialmente")
    print("   (Tarda ~19 horas total, pero usa menos CPU)")
    print("\n⏳ OPCIÓN 2: Ejecutar A2C + SAC en paralelo (en backgrounds separadas)")
    print("   (Tarda ~10 horas total, pero usa más CPU)")
    print("\n⏳ OPCIÓN 3: Solo A2C (rápido, verificar convergencia)")
    print("\n⏳ OPCIÓN 4: Solo SAC (predicción ganador)")
    
    choice = input("\n¿Qué opción deseas? (1/2/3/4, default=2): ").strip() or "2"
    
    if choice == "1":
        print("\n📊 OPCIÓN 1: Secuencial (A2C → SAC)")
        run_training("A2C", config_path)
        time.sleep(2)
        run_training("SAC", config_path)
        
    elif choice == "2":
        print("\n📊 OPCIÓN 2: Paralelo (A2C + SAC en backgrounds)")
        print("\n⚠️  Nota: Esto abrirá DOS procesos en paralelo")
        print("    Cada uno usará ~2-4 GB RAM + 100% CPU")
        print("    Total RAM: ~4-8 GB")
        
        import os
        os.system("echo Starting A2C in background... && python -m scripts.continue_a2c_training --config configs/default.yaml &")
        time.sleep(3)
        os.system("echo Starting SAC in background... && python -m scripts.continue_sac_training --config configs/default.yaml &")
        
        print("\n✅ A2C y SAC iniciados en background")
        print("   Monitorear con: python monitor_checkpoints.py")
        
    elif choice == "3":
        print("\n📊 OPCIÓN 3: Solo A2C")
        run_training("A2C", config_path)
        
    elif choice == "4":
        print("\n📊 OPCIÓN 4: Solo SAC (predicción ganador)")
        run_training("SAC", config_path)
    else:
        print(f"❌ Opción inválida: {choice}")
        sys.exit(1)
    
    print("\n" + "="*100)
    print("📈 PRÓXIMAS ACCIONES:")
    print("="*100)
    print("""
    1. Esperar a que terminen entrenamientos (~10-20 horas)
    
    2. Revisar resultados:
       python check_a2c_training.py        # Análisis A2C
       cat outputs/oe3/simulations/co2_comparison.md
    
    3. Seleccionar ganador (probable: SAC por estabilidad)
    
    4. Ejecutar simulación final 20 años:
       python -m scripts.run_oe3_co2_table --config configs/default.yaml
    
    5. Generar reporte final:
       python analyze_final_results.py
""")

if __name__ == "__main__":
    main()
