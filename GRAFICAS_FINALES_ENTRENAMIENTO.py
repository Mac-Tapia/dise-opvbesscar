#!/usr/bin/env python
"""
GRÁFICAS FINALES: Resumen completo del entrenamiento
Genera reportes visuales comparativos PPO vs A2C vs SAC
"""
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import re
from collections import defaultdict
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("analyses/logs/GRAFICAS_FINALES.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def extract_metrics_from_log(log_file, agent_name):
    """Extrae métricas del archivo de log"""
    
    if not Path(log_file).exists():
        logger.warning(f"No encontrado: {log_file}")
        return None
    
    metrics = {
        'timesteps': [],
        'policy_loss': [],
        'value_loss': [],
        'entropy_loss': [],
        'learning_rate': [],
        'explained_variance': [],
        'fps': []
    }
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Timesteps
                if 'total_timesteps' in line:
                    match = re.search(r'total_timesteps\s*\|\s*(\d+)', line)
                    if match:
                        metrics['timesteps'].append(int(match.group(1)))
                
                # FPS
                if 'fps' in line and '|' in line:
                    match = re.search(r'fps\s*\|\s*(\d+)', line)
                    if match:
                        metrics['fps'].append(int(match.group(1)))
                
                # Policy Loss
                if 'policy_loss' in line:
                    match = re.search(r'policy_loss\s*\|\s*([\d\.e+-]+)', line)
                    if match:
                        try:
                            metrics['policy_loss'].append(float(match.group(1)))
                        except:
                            pass
                
                # Value Loss
                if 'value_loss' in line:
                    match = re.search(r'value_loss\s*\|\s*([\d\.e+-]+)', line)
                    if match:
                        try:
                            metrics['value_loss'].append(float(match.group(1)))
                        except:
                            pass
                
                # Entropy Loss
                if 'entropy_loss' in line:
                    match = re.search(r'entropy_loss\s*\|\s*([-\d\.e+-]+)', line)
                    if match:
                        try:
                            metrics['entropy_loss'].append(float(match.group(1)))
                        except:
                            pass
                
                # Learning Rate
                if 'learning_rate' in line:
                    match = re.search(r'learning_rate\s*\|\s*([\d\.e+-]+)', line)
                    if match:
                        try:
                            metrics['learning_rate'].append(float(match.group(1)))
                        except:
                            pass
                
                # Explained Variance
                if 'explained_variance' in line:
                    match = re.search(r'explained_variance\s*\|\s*([-\d\.e+-]+)', line)
                    if match:
                        try:
                            metrics['explained_variance'].append(float(match.group(1)))
                        except:
                            pass
        
        if metrics['timesteps']:
            logger.info(f"✅ {agent_name}: {len(metrics['timesteps'])} updates, "
                       f"final timesteps: {metrics['timesteps'][-1]}")
            return metrics
        else:
            logger.warning(f"No data found for {agent_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error extrayendo métricas: {e}")
        return None


def create_comparison_plots(output_dir):
    """Crea gráficas comparativas"""
    
    # Extraer datos
    ppo_metrics = extract_metrics_from_log("analyses/logs/ppo_gpu_fixed.log", "PPO")
    a2c_metrics = extract_metrics_from_log("analyses/logs/a2c_gpu_fixed.log", "A2C")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Figura 1: Progreso de entrenamiento (4 subplots)
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Comparativa de Entrenamiento: PPO vs A2C (17,520 timesteps)', 
                 fontsize=16, fontweight='bold')
    
    # 1. Timesteps
    ax = axes[0, 0]
    if ppo_metrics and ppo_metrics['timesteps']:
        ax.plot(ppo_metrics['timesteps'], 'b-', linewidth=2, label='PPO', marker='o', markersize=4)
    if a2c_metrics and a2c_metrics['timesteps']:
        ax.plot(a2c_metrics['timesteps'], 'g-', linewidth=2, label='A2C', marker='s', markersize=4)
    ax.axhline(y=17520, color='r', linestyle='--', linewidth=2, alpha=0.7, label='Target')
    ax.set_xlabel('Update #', fontweight='bold')
    ax.set_ylabel('Timesteps', fontweight='bold')
    ax.set_title('Progreso en Timesteps', fontweight='bold', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # 2. FPS
    ax = axes[0, 1]
    if ppo_metrics and ppo_metrics['fps']:
        ax.plot(ppo_metrics['fps'], 'b-', linewidth=2, label='PPO', marker='o', markersize=4)
    if a2c_metrics and a2c_metrics['fps']:
        ax.plot(a2c_metrics['fps'], 'g-', linewidth=2, label='A2C', marker='s', markersize=4)
    ax.set_xlabel('Update #', fontweight='bold')
    ax.set_ylabel('Frames/sec', fontweight='bold')
    ax.set_title('Velocidad de Entrenamiento', fontweight='bold', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # 3. Policy Loss
    ax = axes[1, 0]
    if ppo_metrics and ppo_metrics['policy_loss']:
        ax.plot(ppo_metrics['policy_loss'], 'b-', linewidth=2, label='PPO', alpha=0.8)
    if a2c_metrics and a2c_metrics['policy_loss']:
        ax.plot(a2c_metrics['policy_loss'], 'g-', linewidth=2, label='A2C', alpha=0.8)
    ax.set_xlabel('Update #', fontweight='bold')
    ax.set_ylabel('Loss', fontweight='bold')
    ax.set_title('Policy Loss (Convergencia)', fontweight='bold', fontsize=12)
    ax.set_yscale('symlog')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # 4. Explained Variance
    ax = axes[1, 1]
    if ppo_metrics and ppo_metrics['explained_variance']:
        ax.plot(ppo_metrics['explained_variance'], 'b-', linewidth=2, label='PPO', alpha=0.8)
    if a2c_metrics and a2c_metrics['explained_variance']:
        ax.plot(a2c_metrics['explained_variance'], 'g-', linewidth=2, label='A2C', alpha=0.8)
    ax.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax.set_xlabel('Update #', fontweight='bold')
    ax.set_ylabel('Explained Variance', fontweight='bold')
    ax.set_title('Calidad de Predicción del Value Network', fontweight='bold', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(str(output_dir / "01_COMPARATIVA_ENTRENAMIENTO.png"), dpi=150, bbox_inches='tight')
    logger.info(f"✅ Gráfica guardada: 01_COMPARATIVA_ENTRENAMIENTO.png")
    plt.close()
    
    # Figura 2: Pérdidas detalladas
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('Análisis de Pérdidas: PPO vs A2C', fontsize=14, fontweight='bold')
    
    # Value Loss
    ax = axes[0]
    if ppo_metrics and ppo_metrics['value_loss']:
        ax.plot(ppo_metrics['value_loss'], 'b-', linewidth=2, label='PPO', alpha=0.8)
    if a2c_metrics and a2c_metrics['value_loss']:
        ax.plot(a2c_metrics['value_loss'], 'g-', linewidth=2, label='A2C', alpha=0.8)
    ax.set_xlabel('Update #', fontweight='bold')
    ax.set_ylabel('Value Loss', fontweight='bold')
    ax.set_title('Value Loss', fontweight='bold', fontsize=12)
    ax.set_yscale('symlog')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Entropy Loss
    ax = axes[1]
    if ppo_metrics and ppo_metrics['entropy_loss']:
        ax.plot(ppo_metrics['entropy_loss'], 'b-', linewidth=2, label='PPO', alpha=0.8)
    if a2c_metrics and a2c_metrics['entropy_loss']:
        ax.plot(a2c_metrics['entropy_loss'], 'g-', linewidth=2, label='A2C', alpha=0.8)
    ax.set_xlabel('Update #', fontweight='bold')
    ax.set_ylabel('Entropy Loss', fontweight='bold')
    ax.set_title('Entropy Loss (Exploración)', fontweight='bold', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Learning Rate
    ax = axes[2]
    if ppo_metrics and ppo_metrics['learning_rate']:
        ax.plot(ppo_metrics['learning_rate'], 'b-', linewidth=2, label='PPO', alpha=0.8)
    if a2c_metrics and a2c_metrics['learning_rate']:
        ax.plot(a2c_metrics['learning_rate'], 'g-', linewidth=2, label='A2C', alpha=0.8)
    ax.set_xlabel('Update #', fontweight='bold')
    ax.set_ylabel('Learning Rate', fontweight='bold')
    ax.set_title('Learning Rate', fontweight='bold', fontsize=12)
    ax.set_yscale('log')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(str(output_dir / "02_ANALISIS_PERDIDAS.png"), dpi=150, bbox_inches='tight')
    logger.info(f"✅ Gráfica guardada: 02_ANALISIS_PERDIDAS.png")
    plt.close()
    
    # Figura 3: Resumen de estadísticas
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('off')
    
    stats_text = """
╔════════════════════════════════════════════════════════════════════════════════╗
║                     RESUMEN DE ENTRENAMIENTO - ESTADÍSTICAS                    ║
╚════════════════════════════════════════════════════════════════════════════════╝

┌─ PPO ──────────────────────────────────────────────────────────────────────────┐
"""
    
    if ppo_metrics:
        stats_text += f"""│ Total Timesteps:      {ppo_metrics['timesteps'][-1]:>8} / 17520
│ Total Updates:        {len(ppo_metrics['timesteps']):>8}
│ Avg FPS:              {np.mean(ppo_metrics['fps']) if ppo_metrics['fps'] else 0:>8.1f}
│ Policy Loss Final:    {ppo_metrics['policy_loss'][-1]:>8.4e if ppo_metrics['policy_loss'] else 'N/A':>8}
│ Value Loss Final:     {ppo_metrics['value_loss'][-1]:>8.4e if ppo_metrics['value_loss'] else 'N/A':>8}
│ Entropy Loss Final:   {ppo_metrics['entropy_loss'][-1]:>8.4f if ppo_metrics['entropy_loss'] else 'N/A':>8}
│ Explained Var Final:  {ppo_metrics['explained_variance'][-1]:>8.4f if ppo_metrics['explained_variance'] else 'N/A':>8}
└────────────────────────────────────────────────────────────────────────────────┘

┌─ A2C ──────────────────────────────────────────────────────────────────────────┐
"""
    else:
        stats_text += """│ [NO DATA]
└────────────────────────────────────────────────────────────────────────────────┘

┌─ A2C ──────────────────────────────────────────────────────────────────────────┐
"""
    
    if a2c_metrics:
        stats_text += f"""│ Total Timesteps:      {a2c_metrics['timesteps'][-1]:>8} / 17520
│ Total Updates:        {len(a2c_metrics['timesteps']):>8}
│ Avg FPS:              {np.mean(a2c_metrics['fps']) if a2c_metrics['fps'] else 0:>8.1f}
│ Policy Loss Final:    {a2c_metrics['policy_loss'][-1]:>8.4e if a2c_metrics['policy_loss'] else 'N/A':>8}
│ Value Loss Final:     {a2c_metrics['value_loss'][-1]:>8.4e if a2c_metrics['value_loss'] else 'N/A':>8}
│ Entropy Loss Final:   {a2c_metrics['entropy_loss'][-1]:>8.4f if a2c_metrics['entropy_loss'] else 'N/A':>8}
│ Explained Var Final:  {a2c_metrics['explained_variance'][-1]:>8.4f if a2c_metrics['explained_variance'] else 'N/A':>8}
└────────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════════╗
║ Generado: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """                              ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""
    else:
        stats_text += """│ [NO DATA]
└────────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════════╗
║ Generado: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """                              ║
╚════════════════════════════════════════════════════════════════════════════════╝
"""
    
    ax.text(0.05, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(str(output_dir / "03_ESTADISTICAS_RESUMEN.png"), dpi=150, bbox_inches='tight')
    logger.info(f"✅ Gráfica guardada: 03_ESTADISTICAS_RESUMEN.png")
    plt.close()


def main():
    logger.info("\n" + "="*80)
    logger.info("GENERADOR DE GRÁFICAS FINALES".center(80))
    logger.info("="*80 + "\n")
    
    output_dir = "analyses/oe3/training/graficas_finales"
    
    try:
        create_comparison_plots(output_dir)
        logger.info("\n" + "="*80)
        logger.info("✅ TODAS LAS GRÁFICAS GENERADAS EXITOSAMENTE".center(80))
        logger.info(f"📁 Ubicación: {output_dir}".center(80))
        logger.info("="*80 + "\n")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
