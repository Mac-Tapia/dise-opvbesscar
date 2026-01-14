#!/usr/bin/env python3
"""Monitoreo en tiempo real del entrenamiento OE3"""

import json
import time
from pathlib import Path
from datetime import datetime
import os

def check_training_status():
    """Verificar estado actual del entrenamiento"""
    
    print("\n" + "="*80)
    print(f"MONITOREO DE ENTRENAMIENTO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # Directorios clave
    simulations_dir = Path("outputs/oe3/simulations")
    checkpoints_dir = Path("outputs/oe3/checkpoints")
    training_dir = Path("analyses/oe3/training")
    
    # 1. BASELINE
    print("📊 BASELINE (Uncontrolled):")
    summary_path = simulations_dir / "simulation_summary.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if "pv_bess_uncontrolled" in summary:
                print("  ✅ Baseline completado y guardado")
                ul_data = summary["pv_bess_uncontrolled"]
                print(f"     CO2: {ul_data.get('total_kg_co2', 'N/A'):.2f} kg")
                print(f"     Costo: ${ul_data.get('total_cost_usd', 'N/A'):.2f}")
        except:
            pass
    
    uncontrolled_file = simulations_dir / "uncontrolled_pv_bess.json"
    if uncontrolled_file.exists():
        print("  ✅ Archivo uncontrolled_pv_bess.json existe")
    else:
        print("  ⏳ Baseline en progreso o pendiente...")
    
    # 2. CHECKPOINTS
    print("\n🔄 CHECKPOINTS:")
    for agent in ['sac', 'ppo', 'a2c']:
        agent_checkpoint_dir = checkpoints_dir / agent
        if agent_checkpoint_dir.exists():
            files = sorted(agent_checkpoint_dir.glob(f"{agent}_*.zip"))
            if files:
                print(f"  {agent.upper()}:")
                for f in files[-3:]:  # Últimos 3
                    size_mb = f.stat().st_size / 1024 / 1024
                    print(f"    ✅ {f.name} ({size_mb:.1f} MB)")
            else:
                print(f"  {agent.upper()}: Sin checkpoints aún")
        else:
            print(f"  {agent.upper()}: Directorio no creado")
    
    # 3. ARCHIVOS DE SIMULACIÓN
    print("\n📁 RESULTADOS DE SIMULACIÓN:")
    for agent in ['sac', 'ppo', 'a2c', 'uncontrolled']:
        sim_file = simulations_dir / f"{agent}_pv_bess.json"
        if sim_file.exists():
            size_kb = sim_file.stat().st_size / 1024
            print(f"  ✅ {agent}_pv_bess.json ({size_kb:.1f} KB)")
        else:
            print(f"  ⏳ {agent}_pv_bess.json (en progreso)")
    
    # 4. LOGS DE ENTRENAMIENTO
    print("\n📝 LOGS DE ENTRENAMIENTO:")
    if training_dir.exists():
        logs = sorted(training_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        if logs:
            latest = logs[0]
            size_kb = latest.stat().st_size / 1024
            print(f"  ✅ {latest.name} ({size_kb:.1f} KB)")
            
            # Intentar leer últimas líneas
            try:
                with open(latest, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    if lines:
                        print("\n  Últimas líneas del log:")
                        for line in lines[-5:]:
                            print(f"    {line.rstrip()}")
            except:
                pass
        else:
            print(f"  ⏳ Logs en progreso...")
    else:
        print(f"  ⏳ Directorio de entrenamiento no creado aún")
    
    # 5. ESTADO GENERAL
    print("\n" + "="*80)
    print("STATUS GENERAL:")
    
    has_baseline = uncontrolled_file.exists()
    has_checkpoints = any(
        (checkpoints_dir / agent).exists() and 
        any((checkpoints_dir / agent).glob(f"{agent}_*.zip"))
        for agent in ['sac', 'ppo', 'a2c']
    )
    has_simulations = any(simulations_dir.glob("*_pv_bess.json"))
    
    print(f"  Baseline: {'✅ Completado' if has_baseline else '⏳ En progreso'}")
    print(f"  Checkpoints: {'✅ Guardándose' if has_checkpoints else '⏳ No iniciado'}")
    print(f"  Simulaciones: {'✅ En progreso' if has_simulations else '⏳ No iniciado'}")
    
    # Verificación de errores
    print("\n⚠️ VERIFICACIÓN DE ERRORES:")
    if training_dir.exists():
        error_files = list(training_dir.glob("*.error"))
        if error_files:
            print(f"  ❌ Encontrados {len(error_files)} archivo(s) de error")
            for err in error_files[:3]:
                print(f"     - {err.name}")
        else:
            print(f"  ✅ Sin archivos de error detectados")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    # Monitoreo continuo
    print("\n🚀 INICIANDO MONITOREO DE ENTRENAMIENTO...")
    print("   (Presiona Ctrl+C para salir)\n")
    
    try:
        while True:
            check_training_status()
            print("⏳ Próxima verificación en 30 segundos...\n")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n\n✅ Monitoreo terminado")
        print("="*80 + "\n")
