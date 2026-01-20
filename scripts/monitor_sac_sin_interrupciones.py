#!/usr/bin/env python
"""Monitor de entrenamiento SAC en tiempo real sin interrumpir el proceso"""

import os
import json
import time
import glob
from pathlib import Path
from datetime import datetime
from collections import deque

def get_latest_checkpoint_info():
    """Obtener info del último checkpoint sin interrumpir"""
    checkpoint_dir = Path("analyses/oe3/training/checkpoints/sac")
    if not checkpoint_dir.exists():
        return None
    
    zips = list(checkpoint_dir.glob("sac_step_*.zip"))
    if not zips:
        return None
    
    latest = max(zips, key=lambda p: p.stat().st_mtime)
    stat = latest.stat()
    
    # Extraer número de paso del nombre
    step_num = int(latest.stem.split("_")[-1])
    
    return {
        "file": latest.name,
        "step": step_num,
        "size_mb": stat.st_size / (1024*1024),
        "time": datetime.fromtimestamp(stat.st_mtime).strftime("%H:%M:%S")
    }

def get_baseline_data():
    """Obtener datos baseline para comparación"""
    try:
        baseline_pv_bess = Path("analyses/oe3/simulations/uncontrolled_pv_bess.json")
        if baseline_pv_bess.exists():
            with open(baseline_pv_bess) as f:
                data = json.load(f)
                if "uncontrolled" in data:
                    unc = data["uncontrolled"]
                    return {
                        "co2_kg": unc.get("total_co2_kg", 0),
                        "grid_kwh": unc.get("grid_electricity_consumption_kWh", 0),
                        "reward": unc.get("reward", 0)
                    }
    except:
        pass
    return None

def parse_latest_logs(n_lines=20):
    """Leer últimas líneas del log sin interrumpir"""
    log_file = Path("analyses/oe3/training/sac_training.log")
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return lines[-n_lines:] if lines else []
    except:
        return []

def extract_metrics_from_log():
    """Extraer última métrica de SAC del log"""
    lines = parse_latest_logs(100)
    
    metrics = None
    for line in reversed(lines):
        if "[SAC] paso" in line and "reward_avg" in line:
            try:
                # Ejemplo: "[SAC] paso 56150 | ep~9 | pasos_global=73670 | reward_avg=44.7415"
                parts = line.split("|")
                paso = int(parts[0].split()[-1])
                reward_avg = float(parts[-2].split("=")[-1].strip())
                episode = parts[2].split("~")[-1].strip()
                
                metrics = {
                    "paso": paso,
                    "episode": episode,
                    "reward_avg": reward_avg,
                    "last_update": datetime.now().strftime("%H:%M:%S")
                }
                break
            except:
                continue
    
    return metrics

def print_header():
    """Encabezado bonito"""
    print("\n" + "="*80)
    print("📊 MONITOR SAC - ENTRENAMIENTO EN VIVO".center(80))
    print("="*80 + "\n")

def print_checkpoint_status():
    """Mostrar estado del checkpoint"""
    print("📁 CHECKPOINT ACTUAL")
    print("-" * 80)
    
    info = get_latest_checkpoint_info()
    if info:
        print(f"  Archivo:      {info['file']}")
        print(f"  Paso:         {info['step']:,} steps")
        print(f"  Tamaño:       {info['size_mb']:.2f} MB")
        print(f"  Actualizado:  {info['time']}")
    else:
        print("  ⚠️  No checkpoints encontrados")
    print()

def print_metrics_status():
    """Mostrar métricas de entrenamiento"""
    print("📈 MÉTRICAS ENTRENAMIENTO")
    print("-" * 80)
    
    metrics = extract_metrics_from_log()
    if metrics:
        print(f"  Paso Actual:      {metrics['paso']:,} steps")
        print(f"  Episodio:         {metrics['episode']}/10")
        print(f"  Reward Promedio:  {metrics['reward_avg']:.4f}")
        print(f"  Última lectura:   {metrics['last_update']}")
    else:
        print("  ⚠️  Esperando datos de entrenamiento...")
    print()

def print_baseline_comparison():
    """Comparación con baseline"""
    print("🎯 COMPARACIÓN SAC vs BASELINE")
    print("-" * 80)
    
    baseline = get_baseline_data()
    metrics = extract_metrics_from_log()
    
    if baseline and metrics:
        # Datos aproximados (el reward es promedio durante entrenamiento)
        estimated_co2 = baseline["co2_kg"] * (1 - metrics['reward_avg']/100)  # Estimación rough
        co2_reduction = (baseline["co2_kg"] - estimated_co2) / baseline["co2_kg"] * 100
        
        print(f"  Baseline CO₂:       {baseline['co2_kg']:.1f} kg")
        print(f"  Est. SAC CO₂:       {estimated_co2:.1f} kg")
        print(f"  Reducción:          {co2_reduction:.1f}%")
        print(f"  Baseline Grid:      {baseline['grid_kwh']:.1f} kWh")
        print(f"  Reward Baseline:    {baseline['reward']:.1f}")
        print(f"  Reward SAC Avg:     {metrics['reward_avg']:.4f}")
    else:
        print("  ⚠️  Datos insuficientes para comparación")
    print()

def print_progress_bar():
    """Barra de progreso de episodios"""
    metrics = extract_metrics_from_log()
    if not metrics:
        return
    
    print("⏳ PROGRESO DE EPISODIOS")
    print("-" * 80)
    
    try:
        ep_num = int(metrics['episode'])
        bar_length = 40
        filled = int(bar_length * ep_num / 10)
        bar = "█" * filled + "░" * (bar_length - filled)
        percentage = (ep_num / 10) * 100
        
        print(f"  [{bar}] {percentage:.0f}% ({ep_num}/10)")
        print()
    except:
        pass

def print_checkpoint_history():
    """Mostrar historial de checkpoints"""
    print("📜 ÚLTIMOS CHECKPOINTS")
    print("-" * 80)
    
    checkpoint_dir = Path("analyses/oe3/training/checkpoints/sac")
    if checkpoint_dir.exists():
        zips = sorted(checkpoint_dir.glob("sac_step_*.zip"), 
                     key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        
        for i, z in enumerate(zips, 1):
            step = int(z.stem.split("_")[-1])
            time_str = datetime.fromtimestamp(z.stat().st_mtime).strftime("%H:%M:%S")
            size_mb = z.stat().st_size / (1024*1024)
            print(f"  {i}. Step {step:,} ({time_str}) - {size_mb:.1f}MB")
    else:
        print("  ⚠️  Carpeta de checkpoints no encontrada")
    print()

def print_footer():
    """Pie del reporte"""
    print("-" * 80)
    print(f"🔄 Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("💡 El entrenamiento continúa en background. Este reporte no interrumpe el proceso.")
    print("="*80 + "\n")

def main():
    """Main monitor loop"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')  # Limpiar pantalla
        
        print_header()
        print_checkpoint_status()
        print_metrics_status()
        print_progress_bar()
        print_baseline_comparison()
        print_checkpoint_history()
        print_footer()
        
        print("⏸️  Presiona Ctrl+C para detener el monitor (el entrenamiento continuará)")
        print("🔁 Actualizando en 10 segundos...\n")
        
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print("\n✅ Monitor detenido. El entrenamiento continúa en background.")
            break

if __name__ == "__main__":
    main()
