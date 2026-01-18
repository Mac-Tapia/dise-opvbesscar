#!/usr/bin/env python3
"""
Entrenamiento SERIAL de agentes RL con GPU máximo.
SAC (GPU) → PPO (CPU) → A2C (GPU)

Optimizaciones:
- SAC: 65536 batch_size, use_amp=true, learning_starts=50
- A2C: 32768 n_steps, use_amp=true, learning_rate=0.001
- PPO: Fallback a CPU para estabilidad
- Monitoreo de checkpoints en tiempo real
"""

import torch
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def check_environment():
    """Verificar Python y dependencias."""
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DE ENTORNO")
    print("=" * 70)
    
    # Python version
    py_version = sys.version.split()[0]
    print(f"✓ Python: {py_version}")
    
    # GPU Check
    cuda_available = torch.cuda.is_available()
    print(f"✓ CUDA Disponible: {cuda_available}")
    
    if cuda_available:
        device_count = torch.cuda.device_count()
        print(f"✓ Número de GPUs: {device_count}")
        
        for i in range(device_count):
            props = torch.cuda.get_device_properties(i)
            mem_gb = props.total_memory / 1e9
            print(f"  GPU {i}: {props.name} ({mem_gb:.1f} GB)")
        
        # Current device info
        current_idx = torch.cuda.current_device()
        current_props = torch.cuda.get_device_properties(current_idx)
        print(f"\n✓ GPU Actual: {current_props.name}")
        print(f"✓ Memoria Total: {current_props.total_memory / 1e9:.1f} GB")
        print(f"✓ Compute Capability: {current_props.major}.{current_props.minor}")
    else:
        print("⚠ CUDA NO disponible - usando CPU (entrenamiento lento)")
    
    # Check project files
    print("\n✓ Verificando archivos del proyecto...")
    required = [
        "configs/default.yaml",
        "data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json",
        "data/processed/citylearn/iquitos_ev_mall/schema_grid_only.json",
    ]
    
    for path in required:
        p = Path(path)
        if p.exists():
            print(f"  ✓ {path}")
        else:
            print(f"  ✗ FALTA: {path}")
            return False
    
    return True

def configure_gpu():
    """Configurar GPU para máximo rendimiento."""
    print("\n" + "=" * 70)
    print("CONFIGURACIÓN GPU")
    print("=" * 70)
    
    # Variables de entorno para máximo rendimiento
    os.environ['CUDA_LAUNCH_BLOCKING'] = '0'  # Async GPU operations
    os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    os.environ['OMP_NUM_THREADS'] = '8'
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':16:8'  # cuBLAS workspace
    
    print("✓ Variables de entorno configuradas:")
    print("  - CUDA_LAUNCH_BLOCKING=0 (async operations)")
    print("  - OMP_NUM_THREADS=8")
    print("  - CUBLAS_WORKSPACE_CONFIG=:16:8")

def train_agent_serial(agent_name, config_path="configs/default.yaml"):
    """Entrenar un agente de forma serial."""
    print("\n" + "=" * 70)
    print(f"ENTRENANDO: {agent_name}")
    print("=" * 70)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Inicio: {timestamp}")
    
    cmd = [
        sys.executable,
        "-m",
        "scripts.run_oe3_simulate",
        "--config",
        config_path,
        "--skip-dataset",
    ]
    
    # Skip previous baselines si existen
    if agent_name != "SAC":  # SAC es el primero, no skip
        cmd.append("--skip-uncontrolled")
    
    print(f"\nComando: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✓ {agent_name} completado exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ ERROR en {agent_name}: {e}")
        return False

def monitor_checkpoints():
    """Monitorear progreso de checkpoints."""
    checkpoint_base = Path("outputs/oe3/checkpoints")
    
    if not checkpoint_base.exists():
        print("\nℹ No hay checkpoints aún (entrenamiento en progreso)")
        return
    
    print("\n" + "=" * 70)
    print("ESTADO DE CHECKPOINTS")
    print("=" * 70)
    
    for agent_dir in sorted(checkpoint_base.iterdir()):
        if agent_dir.is_dir():
            agent_name = agent_dir.name
            checkpoints = list(agent_dir.glob("*.zip"))
            
            if checkpoints:
                latest = sorted(checkpoints, key=lambda x: x.stat().st_mtime)[-1]
                size_mb = latest.stat().st_size / 1e6
                timestamp = datetime.fromtimestamp(latest.stat().st_mtime)
                print(f"\n{agent_name}:")
                print(f"  Último: {latest.name}")
                print(f"  Tamaño: {size_mb:.1f} MB")
                print(f"  Actualizado: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"\n{agent_name}: Sin checkpoints aún")

def generate_report():
    """Generar reporte de resultados."""
    summary_path = Path("outputs/oe3/simulations/simulation_summary.json")
    
    if not summary_path.exists():
        print("\nℹ Resumen no disponible (entrenamiento en progreso)")
        return
    
    print("\n" + "=" * 70)
    print("RESUMEN DE RESULTADOS")
    print("=" * 70)
    
    with open(summary_path) as f:
        summary = json.load(f)
    
    # Best agent
    best = summary.get("best_agent", "N/A")
    print(f"\n✓ Mejor agente: {best}")
    
    # CO2 comparison
    if "pv_bess_results" in summary:
        results = summary["pv_bess_results"]
        print("\nCO2 por agente (kg/año):")
        
        baseline = summary.get("pv_bess_uncontrolled", {})
        if baseline:
            base_co2 = baseline.get("carbon_kg", 0)
            print(f"  Uncontrolled (baseline): {base_co2:.0f}")
        
        for agent, result in sorted(results.items()):
            co2 = result.get("carbon_kg", 0)
            reduction = (base_co2 - co2) / max(base_co2, 1e-9) * 100 if base_co2 else 0
            print(f"  {agent}: {co2:.0f} (↓ {reduction:.2f}% vs baseline)")
    
    # Reductions
    reductions = summary.get("reductions", {})
    if reductions:
        print("\nReducciones vs Grid-only (con tailpipe):")
        oe2_red_pct = reductions.get("oe2_reduction_pct", 0) * 100
        print(f"  OE2 (PV+BESS): {oe2_red_pct:.2f}%")

def main():
    """Orquesta el entrenamiento serial con GPU máximo."""
    print("\n" + "=" * 70)
    print("ENTRENAMIENTO SERIAL DE AGENTES RL")
    print("GPU MÁXIMO - SAC → PPO → A2C")
    print("=" * 70)
    
    # Verificaciones
    if not check_environment():
        print("\n✗ ERROR: Entorno no válido")
        sys.exit(1)
    
    # Configurar GPU
    configure_gpu()
    
    # Orden serial optimizado
    agents = ["SAC", "PPO", "A2C"]
    results = {}
    
    print("\n" + "=" * 70)
    print("INICIANDO ENTRENAMIENTO SERIAL")
    print("=" * 70)
    
    for agent in agents:
        success = train_agent_serial(agent)
        results[agent] = "✓ OK" if success else "✗ FALLÓ"
        
        # Monitor after each agent
        monitor_checkpoints()
        
        if not success:
            print(f"\n⚠ {agent} falló - continuando con siguiente...")
    
    # Reporte final
    print("\n" + "=" * 70)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 70)
    
    for agent, status in results.items():
        print(f"{agent}: {status}")
    
    # Resultados finales
    generate_report()
    
    # Final status
    all_ok = all("✓" in v for v in results.values())
    print("\n" + "=" * 70)
    if all_ok:
        print("✓ ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
    else:
        print("⚠ ENTRENAMIENTO COMPLETADO CON ERRORES")
    print("=" * 70 + "\n")
    
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
