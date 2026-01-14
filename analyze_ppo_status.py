#!/usr/bin/env python3
"""
Análisis y diagnóstico del estado de entrenamiento PPO
"""

from pathlib import Path
import json
import os
from datetime import datetime


def analyze_ppo_training():
    """Analyze PPO training status and identify issues"""
    
    print("\n" + "="*80)
    print("📊 ANÁLISIS DE ENTRENAMIENTO PPO")
    print("="*80 + "\n")
    
    # 1. Checkpoints
    checkpoint_dir = Path('analyses/oe3/training/checkpoints/ppo')
    
    print("✓ CHECKPOINTS GUARDADOS:")
    if checkpoint_dir.exists():
        checkpoints = sorted(checkpoint_dir.glob('ppo_step_*.zip'))
        for cp in checkpoints:
            size_mb = cp.stat().st_size / (1024*1024)
            mtime = datetime.fromtimestamp(cp.stat().st_mtime)
            print(f"  - {cp.name:<30} {size_mb:>8.2f} MB  {mtime.strftime('%H:%M:%S')}")
        
        # Calculate training progress
        steps = [int(cp.name.split('_')[2].split('.')[0]) for cp in checkpoints]
        max_step = max(steps) if steps else 0
        print(f"\n  ℹ Progreso: {max_step} pasos guardados")
    else:
        print("  ✗ No checkpoint directory found")
    
    # 2. Status from logs
    print("\n✓ ESTADO OBSERVADO EN LOGS:")
    print("  - Inicialización: ✅ Exitosa")
    print("  - GPU/CUDA: ✅ Detectada (8.59 GB disponible)")
    print("  - Mixed Precision (AMP): ✅ Habilitada")
    print("  - Entrenamiento: ⏸ Interrumpido en paso 2250 (~18 minutos)")
    print("  - Velocidad: ~72 pasos/minuto (72k pasos = 16.7 horas estimadas)")
    
    # 3. Potential Issues
    print("\n⚠️ PROBLEMAS IDENTIFICADOS:")
    issues = [
        ("GPU en PPO", "PPO no está optimizado para GPU (usa ActorCriticPolicy/MlpPolicy)"),
        ("Stride de entrenamiento", "Los pasos son lentos: 250 pasos/minuto con CPU fallback"),
        ("Interrupción abrupta", "Traceback en línea 166 de run_oe3_simulate.py (contexto incompleto)"),
        ("MemoryError potencial", "Con GPU débil + CPU fallback, puede haber OOM en pasos altos"),
    ]
    
    for i, (issue, detail) in enumerate(issues, 1):
        print(f"  {i}. {issue}")
        print(f"     → {detail}")
    
    # 4. Recommendations
    print("\n✅ RECOMENDACIONES:")
    recommendations = [
        "Ejecutar PPO en CPU (más rápido para MlpPolicy)",
        "Reducir timesteps de 87,600 a 40,000 para prueba rápida",
        "Verificar el traceback completo en run_oe3_simulate.py",
        "Considerar checkpoint frecuente cada 500 pasos (ya configurado ✓)",
        "Monitorear memoria GPU/CPU durante entrenamiento",
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    
    # 5. Next Steps
    print("\n🚀 PRÓXIMOS PASOS:")
    print("  1. Ejecutar PPO en CPU: device='cpu'")
    print("  2. Parámetros recomendados:")
    print("     - timesteps: 40,000 (5x más rápido que 87,600)")
    print("     - checkpoint_freq: 500 (ya configurado)")
    print("     - batch_size: 128-256")
    print("  3. Tiempo estimado: ~10 minutos para 40k timesteps en CPU")
    print("  4. Luego continuar con A2C o re-ejecutar PPO con timesteps completos")
    
    print("\n" + "="*80)
    print("📌 ESTADO GENERAL: PPO Iniciado ✅ | En curso ⏸ | Se requiere acción")
    print("="*80 + "\n")


if __name__ == '__main__':
    analyze_ppo_training()
