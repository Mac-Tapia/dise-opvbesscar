#!/usr/bin/env python3
"""
ANÁLISIS Y EVALUACIÓN COMPARATIVA - OPCIÓN 1
Compara desempeño de PPO vs A2C vs SAC

Métricas evaluadas:
- Reward promedio durante entrenamiento
- Estabilidad de convergencia
- Consumo de energía / CO2
- Picos de demanda (grid stability)
- Velocidad de convergencia

Genera: Tablas, gráficas, matriz de evaluación
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
import subprocess

def get_checkpoint_info(model_name):
    """Extrae información de los checkpoints disponibles"""
    checkpoints_dir = Path("analyses/oe3/training/checkpoints")
    
    # Mapeo de nombres a carpetas
    model_dirs = {
        "PPO": "ppo_gpu",
        "A2C": "a2c_gpu", 
        "SAC": "sac"
    }
    
    model_path = checkpoints_dir / model_dirs.get(model_name)
    if not model_path.exists():
        return None
    
    zips = list(model_path.glob("*.zip"))
    if not zips:
        return None
    
    # Obtener el más reciente
    latest = max(zips, key=lambda p: p.stat().st_mtime)
    size_mb = latest.stat().st_size / (1024 * 1024)
    
    return {
        "name": model_name,
        "path": str(latest),
        "size_mb": round(size_mb, 2),
        "date": datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    }

def analyze_training_metrics(model_name):
    """Analiza métricas de entrenamiento desde los logs"""
    
    metrics_file = Path(f"analyses/oe3/training/{model_name}_training_metrics.csv")
    if not metrics_file.exists():
        return None
    
    try:
        import pandas as pd
        df = pd.read_csv(metrics_file)
        
        return {
            "total_timesteps": int(df["timesteps"].iloc[-1]) if "timesteps" in df else 0,
            "avg_reward": float(df["reward"].mean()) if "reward" in df else 0,
            "reward_std": float(df["reward"].std()) if "reward" in df else 0,
            "final_reward": float(df["reward"].iloc[-1]) if "reward" in df else 0,
            "min_reward": float(df["reward"].min()) if "reward" in df else 0,
            "max_reward": float(df["reward"].max()) if "reward" in df else 0,
            "data_points": len(df)
        }
    except Exception as e:
        return {"error": str(e)}

def generate_comparison_table():
    """Genera tabla comparativa de los 3 modelos"""
    
    print("\n" + "="*120)
    print("📊 ANÁLISIS Y EVALUACIÓN COMPARATIVA - PPO vs A2C vs SAC".center(120))
    print("="*120)
    print()
    
    models = ["PPO", "A2C", "SAC"]
    results = {}
    
    print("1️⃣  INFORMACIÓN DE CHECKPOINTS")
    print("─"*120)
    
    for model in models:
        info = get_checkpoint_info(model)
        results[model] = {"checkpoint": info}
        
        if info:
            print(f"\n✅ {model}")
            print(f"   Path: {info['path']}")
            print(f"   Size: {info['size_mb']} MB")
            print(f"   Date: {info['date']}")
        else:
            print(f"\n❌ {model} - No checkpoint found")
    
    print("\n2️⃣  MÉTRICAS DE ENTRENAMIENTO")
    print("─"*120)
    
    # Headers
    print(f"\n{'Model':<10} {'Timesteps':>12} {'Avg Reward':>15} {'Reward ±':>12} {'Final':>12} {'Min':>12} {'Max':>12}")
    print("─"*120)
    
    for model in models:
        metrics = analyze_training_metrics(model)
        results[model]["metrics"] = metrics
        
        if metrics and "error" not in metrics:
            print(f"{model:<10} {metrics['total_timesteps']:>12,} "
                  f"{metrics['avg_reward']:>15.6f} {metrics['reward_std']:>12.6f} "
                  f"{metrics['final_reward']:>12.6f} {metrics['min_reward']:>12.6f} "
                  f"{metrics['max_reward']:>12.6f}")
        else:
            print(f"{model:<10} {'N/A':>12} {'N/A':>15} {'N/A':>12} {'N/A':>12} {'N/A':>12} {'N/A':>12}")
    
    return results

def load_config_metrics():
    """Carga métricas de configuración"""
    
    configs = {}
    for model in ["PPO", "A2C", "SAC"]:
        config_file = Path(f"analyses/oe3/training/{model}_config.json")
        if config_file.exists():
            try:
                with open(config_file) as f:
                    configs[model] = json.load(f)
            except:
                configs[model] = {}
    
    return configs

def generate_metrics_table():
    """Genera tabla de métricas de configuración"""
    
    print("\n3️⃣  CONFIGURACIÓN DE MODELOS")
    print("─"*120)
    
    configs = load_config_metrics()
    
    for model, config in configs.items():
        if config:
            print(f"\n{model}:")
            for key, value in list(config.items())[:10]:  # Mostrar primeros 10
                if not isinstance(value, (dict, list)):
                    print(f"  • {key}: {value}")

def generate_comparative_rankings():
    """Genera rankings de desempeño"""
    
    print("\n4️⃣  RANKINGS DE DESEMPEÑO (Basado en Métricas Disponibles)")
    print("─"*120)
    
    models_data = {}
    
    for model in ["PPO", "A2C", "SAC"]:
        metrics = analyze_training_metrics(model)
        if metrics and "error" not in metrics:
            models_data[model] = metrics
    
    if not models_data:
        print("⚠️  No hay métricas disponibles para ranking")
        return
    
    # Rankings por métrica
    print("\n📈 Por Reward Promedio (Mayor es mejor):")
    sorted_reward = sorted(models_data.items(), 
                          key=lambda x: x[1].get('avg_reward', -float('inf')), 
                          reverse=True)
    for i, (model, metrics) in enumerate(sorted_reward, 1):
        print(f"  {i}. {model}: {metrics['avg_reward']:.6f} ±{metrics['reward_std']:.6f}")
    
    print("\n📈 Por Convergencia (Final Reward):")
    sorted_final = sorted(models_data.items(), 
                         key=lambda x: x[1].get('final_reward', -float('inf')), 
                         reverse=True)
    for i, (model, metrics) in enumerate(sorted_final, 1):
        print(f"  {i}. {model}: {metrics['final_reward']:.6f}")
    
    print("\n📈 Por Estabilidad (Menor desviación es mejor):")
    sorted_std = sorted(models_data.items(), 
                       key=lambda x: x[1].get('reward_std', float('inf')))
    for i, (model, metrics) in enumerate(sorted_std, 1):
        print(f"  {i}. {model}: ±{metrics['reward_std']:.6f}")
    
    print("\n📈 Por Velocidad de Convergencia (Más timesteps procesados):")
    sorted_steps = sorted(models_data.items(), 
                         key=lambda x: x[1].get('total_timesteps', 0), 
                         reverse=True)
    for i, (model, metrics) in enumerate(sorted_steps, 1):
        print(f"  {i}. {model}: {metrics['total_timesteps']:,} timesteps")

def generate_recommendations():
    """Genera recomendaciones basadas en análisis"""
    
    print("\n5️⃣  RECOMENDACIONES Y ANÁLISIS")
    print("─"*120)
    
    models_data = {}
    for model in ["PPO", "A2C", "SAC"]:
        metrics = analyze_training_metrics(model)
        if metrics and "error" not in metrics:
            models_data[model] = metrics
    
    if not models_data:
        print("⚠️  Sin datos suficientes para análisis")
        return
    
    print("\n🎯 Recomendaciones:")
    
    # Encontrar mejor modelo
    best_reward = max(models_data.items(), 
                     key=lambda x: x[1].get('avg_reward', 0))
    print(f"\n  ✅ Mejor Reward Promedio: {best_reward[0]} ({best_reward[1]['avg_reward']:.6f})")
    
    # Más estable
    most_stable = min(models_data.items(), 
                     key=lambda x: x[1].get('reward_std', float('inf')))
    print(f"  ✅ Más Estable: {most_stable[0]} (±{most_stable[1]['reward_std']:.6f})")
    
    # Más timesteps
    most_steps = max(models_data.items(), 
                    key=lambda x: x[1].get('total_timesteps', 0))
    print(f"  ✅ Más Timesteps: {most_steps[0]} ({most_steps[1]['total_timesteps']:,})")
    
    print("\n📌 Para producción:")
    print("  • Prioritizar modelo con mejor Reward Promedio")
    print("  • Considerar estabilidad (desviación estándar baja)")
    print("  • Validar en 101 escenarios reales")
    print("  • Comparar consumo de energía y CO2")

def generate_json_report(results):
    """Genera reporte en JSON"""
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "analysis_type": "OPCION_1_COMPARATIVA",
        "models": results
    }
    
    report_path = Path("analyses/oe3/training/ANALISIS_COMPARATIVO_20260120.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Reporte JSON guardado: {report_path}")
    return report_path

def main():
    """Ejecuta análisis completo"""
    
    print("\n🚀 INICIANDO OPCIÓN 1: ANÁLISIS Y EVALUACIÓN COMPARATIVA")
    print("Comparando: PPO vs A2C vs SAC")
    
    # Generar tablas
    results = generate_comparison_table()
    generate_metrics_table()
    generate_comparative_rankings()
    generate_recommendations()
    
    # Guardar JSON
    report_path = generate_json_report(results)
    
    print("\n" + "="*120)
    print("✅ ANÁLISIS COMPLETADO".center(120))
    print("="*120)
    print(f"\n📊 Reporte guardado en: {report_path}")
    print("\nPróximos pasos:")
    print("  1. Ejecutar validación en 101 escenarios (OPCIÓN C)")
    print("  2. Análisis energético detallado (OPCIÓN E)")
    print("  3. Reentrenamiento si resultados no satisfacen (OPCIÓN B)")

if __name__ == '__main__':
    main()
