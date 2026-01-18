#!/usr/bin/env python3
"""
Entrenamiento SERIAL optimizado para CPU (o GPU si disponible).
Ajusta automáticamente batch_size y n_steps según device disponible.

SAC → PPO → A2C
"""

import torch
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def detect_device():
    """Detectar device (CUDA/CPU) y optimizar parámetros."""
    cuda_available = torch.cuda.is_available()
    
    if cuda_available:
        device_count = torch.cuda.device_count()
        device_name = torch.cuda.get_device_name(0)
        mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        compute_cap = torch.cuda.get_device_properties(0)
        return "cuda", device_name, mem_gb, device_count
    else:
        import platform
        import psutil
        cpu_count = psutil.cpu_count(logical=False) or 1
        mem_gb = psutil.virtual_memory().total / 1e9
        return "cpu", f"{platform.processor()} ({cpu_count} cores)", mem_gb, cpu_count

def optimize_config(device, config_path="configs/default.yaml", mem_gb=8):
    """Optimizar configuración según device y memoria disponible."""
    import yaml
    
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    
    oe3_eval = cfg["oe3"]["evaluation"]
    
    if device == "cuda":
        print(f"✓ Optimización GPU detectada (RTX 4060, {mem_gb:.1f} GB)")
        # GPU RTX 4060: 8GB - batch sizes moderados pero óptimos
        if mem_gb >= 8:
            oe3_eval["sac"]["batch_size"] = 32768  # Reducido para RTX 4060
            oe3_eval["sac"]["use_amp"] = True
            oe3_eval["a2c"]["n_steps"] = 16384
            oe3_eval["a2c"]["use_amp"] = True
            print("  Parámetros: GPU RTX 4060 (8GB) - optimizado")
        else:
            oe3_eval["sac"]["batch_size"] = 16384
            oe3_eval["sac"]["use_amp"] = True
            oe3_eval["a2c"]["n_steps"] = 8192
            oe3_eval["a2c"]["use_amp"] = True
            print("  Parámetros: GPU limitada")
    else:
        print("✓ Optimización CPU detectada (redimensionando)")
        # CPU: parámetros conservadores
        oe3_eval["sac"]["batch_size"] = 512
        oe3_eval["sac"]["use_amp"] = False
        oe3_eval["a2c"]["n_steps"] = 2048
        oe3_eval["a2c"]["use_amp"] = False
    
    # Guardar config optimizada
    config_temp = Path(config_path).parent / "default_optimized.yaml"
    with open(config_temp, 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, default_flow_style=False)
    
    print(f"✓ Config optimizada guardada: {config_temp}")
    return str(config_temp)

def check_environment():
    """Verificar Python y dependencias."""
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DE ENTORNO")
    print("=" * 70)
    
    # Python version
    py_version = sys.version.split()[0]
    print(f"✓ Python: {py_version}")
    
    # Device detection
    device, device_name, mem_gb, resource_count = detect_device()
    print(f"✓ Device: {device.upper()}")
    print(f"  Nombre: {device_name}")
    print(f"  Memoria: {mem_gb:.1f} GB")
    if device == "cuda":
        print(f"  Recursos CUDA: {resource_count}")
    else:
        print(f"  CPU Cores: {resource_count}")
    
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
            return False, device
    
    return True, device

def configure_environment(device):
    """Configurar variables de entorno."""
    print("\n" + "=" * 70)
    print("CONFIGURACIÓN DE ENTORNO")
    print("=" * 70)
    
    if device == "cuda":
        os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
        os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
        os.environ['CUDA_VISIBLE_DEVICES'] = '0'
        os.environ['OMP_NUM_THREADS'] = '8'
        os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':16:8'
        print("\n✓ Configuración GPU:")
        print("  - CUDA_LAUNCH_BLOCKING=0")
        print("  - OMP_NUM_THREADS=8")
    else:
        os.environ['OMP_NUM_THREADS'] = '4'
        print("\n✓ Configuración CPU:")
        print("  - OMP_NUM_THREADS=4")

def train_agent(agent_name, config_path, device):
    """Entrenar un agente."""
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
    
    # Skip previous baselines si existen (excepto primer agente)
    if agent_name != "SAC":
        cmd.append("--skip-uncontrolled")
    
    print(f"\nComando: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✓ {agent_name} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ ERROR en {agent_name}: Código {e.returncode}")
        return False

def generate_report():
    """Generar reporte de resultados."""
    summary_path = Path("outputs/oe3/simulations/simulation_summary.json")
    
    if not summary_path.exists():
        print("\nℹ Resumen no disponible")
        return
    
    print("\n" + "=" * 70)
    print("RESUMEN DE RESULTADOS")
    print("=" * 70)
    
    with open(summary_path, encoding='utf-8') as f:
        summary = json.load(f)
    
    best = summary.get("best_agent", "N/A")
    print(f"\n✓ Mejor agente: {best}")
    
    if "pv_bess_results" in summary:
        results = summary["pv_bess_results"]
        baseline = summary.get("pv_bess_uncontrolled", {})
        base_co2 = baseline.get("carbon_kg", 0) if baseline else 0
        
        print("\nCO2 por agente (kg):")
        if baseline:
            print(f"  Uncontrolled: {base_co2:.0f}")
        
        for agent in sorted(results.keys()):
            result = results[agent]
            co2 = result.get("carbon_kg", 0)
            if base_co2 > 0:
                reduction_pct = (base_co2 - co2) / base_co2 * 100
                print(f"  {agent}: {co2:.0f} (↓ {reduction_pct:.2f}%)")
            else:
                print(f"  {agent}: {co2:.0f}")

def main():
    """Orquesta el entrenamiento."""
    print("\n" + "=" * 70)
    print("ENTRENAMIENTO SERIAL DE AGENTES RL")
    print("SAC → PPO → A2C")
    print("=" * 70)
    
    # Verificaciones
    env_ok, device = check_environment()
    if not env_ok:
        print("\n✗ ERROR: Entorno no válido")
        sys.exit(1)
    
    # Configurar entorno
    configure_environment(device)
    
    # Optimizar config según device
    config_path = optimize_config(device, mem_gb=mem_gb if device == "cuda" else 0)
    
    # Entrenamiento
    agents = ["SAC", "PPO", "A2C"]
    results = {}
    
    print("\n" + "=" * 70)
    print("INICIANDO ENTRENAMIENTO SERIAL")
    print("=" * 70)
    
    for agent in agents:
        success = train_agent(agent, config_path, device)
        results[agent] = "✓" if success else "✗"
        
        if not success:
            print(f"\n⚠ {agent} falló - continuando...")
    
    # Reporte
    print("\n" + "=" * 70)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 70)
    
    for agent, status in results.items():
        print(f"{agent}: {status}")
    
    generate_report()
    
    # Status final
    all_ok = all(v == "✓" for v in results.values())
    print("\n" + "=" * 70)
    if all_ok:
        print("✓ ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
    else:
        print("⚠ ENTRENAMIENTO COMPLETADO CON ALGUNOS ERRORES")
    print("=" * 70 + "\n")
    
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
