#!/usr/bin/env python
"""
MONITOR EN TIEMPO REAL: Gráficas de entrenamiento PPO y A2C
Visualiza progreso, pérdidas y métricas mientras se entrenan
"""
import os
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from pathlib import Path
from collections import deque
import json
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

class TrainingMonitor:
    """Monitor en tiempo real de entrenamiento"""
    
    def __init__(self, log_file, agent_name, max_points=200):
        self.log_file = Path(log_file)
        self.agent_name = agent_name
        self.max_points = max_points
        
        # Almacenamiento de datos
        self.timesteps = deque(maxlen=max_points)
        self.fps = deque(maxlen=max_points)
        self.policy_loss = deque(maxlen=max_points)
        self.value_loss = deque(maxlen=max_points)
        self.entropy_loss = deque(maxlen=max_points)
        self.learning_rate = deque(maxlen=max_points)
        self.explained_variance = deque(maxlen=max_points)
        
        self.last_pos = 0
        self.start_time = time.time()
        
    def read_new_logs(self):
        """Lee nuevas líneas del archivo de log"""
        if not self.log_file.exists():
            return False
        
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_pos)
                lines = f.readlines()
                self.last_pos = f.tell()
            
            updated = False
            for line in lines:
                # Extraer timesteps
                if 'total_timesteps' in line:
                    match = re.search(r'total_timesteps\s*\|\s*(\d+)', line)
                    if match:
                        ts = int(match.group(1))
                        self.timesteps.append(ts)
                        updated = True
                
                # Extraer FPS
                if 'fps' in line and '|' in line:
                    match = re.search(r'fps\s*\|\s*(\d+)', line)
                    if match:
                        f = int(match.group(1))
                        self.fps.append(f)
                
                # Extraer pérdidas
                if 'policy_loss' in line:
                    match = re.search(r'policy_loss\s*\|\s*([\d\.e+-]+)', line)
                    if match:
                        try:
                            self.policy_loss.append(float(match.group(1)))
                        except:
                            pass
                
                if 'value_loss' in line:
                    match = re.search(r'value_loss\s*\|\s*([\d\.e+-]+)', line)
                    if match:
                        try:
                            self.value_loss.append(float(match.group(1)))
                        except:
                            pass
                
                if 'entropy_loss' in line:
                    match = re.search(r'entropy_loss\s*\|\s*([-\d\.e+-]+)', line)
                    if match:
                        try:
                            self.entropy_loss.append(float(match.group(1)))
                        except:
                            pass
                
                if 'learning_rate' in line:
                    match = re.search(r'learning_rate\s*\|\s*([\d\.e+-]+)', line)
                    if match:
                        try:
                            self.learning_rate.append(float(match.group(1)))
                        except:
                            pass
                
                if 'explained_variance' in line:
                    match = re.search(r'explained_variance\s*\|\s*([-\d\.e+-]+)', line)
                    if match:
                        try:
                            self.explained_variance.append(float(match.group(1)))
                        except:
                            pass
            
            return updated
        except Exception as e:
            logger.error(f"Error leyendo logs: {e}")
            return False
    
    def get_status(self):
        """Retorna estado actual"""
        elapsed = time.time() - self.start_time
        
        return {
            'agent': self.agent_name,
            'timesteps': list(self.timesteps)[-1] if self.timesteps else 0,
            'fps': list(self.fps)[-1] if self.fps else 0,
            'elapsed': elapsed,
            'has_data': len(self.timesteps) > 0
        }


def create_dashboard(ppo_monitor, a2c_monitor):
    """Crea dashboard con todas las gráficas"""
    
    fig = plt.figure(figsize=(18, 12))
    fig.suptitle('Monitor de Entrenamiento: PPO vs A2C (17,520 timesteps)', 
                 fontsize=16, fontweight='bold')
    
    # 1. Timesteps (arriba izquierda)
    ax1 = plt.subplot(3, 3, 1)
    ax1.set_title('Progreso (Timesteps)', fontweight='bold')
    ax1.set_ylabel('Timesteps')
    ax1.grid(True, alpha=0.3)
    
    # 2. FPS (arriba centro)
    ax2 = plt.subplot(3, 3, 2)
    ax2.set_title('Velocidad (FPS)', fontweight='bold')
    ax2.set_ylabel('Frames/sec')
    ax2.grid(True, alpha=0.3)
    
    # 3. Policy Loss (arriba derecha)
    ax3 = plt.subplot(3, 3, 3)
    ax3.set_title('Policy Loss', fontweight='bold')
    ax3.set_ylabel('Loss')
    ax3.set_yscale('symlog')
    ax3.grid(True, alpha=0.3)
    
    # 4. Value Loss (medio izquierda)
    ax4 = plt.subplot(3, 3, 4)
    ax4.set_title('Value Loss', fontweight='bold')
    ax4.set_ylabel('Loss')
    ax4.set_yscale('symlog')
    ax4.grid(True, alpha=0.3)
    
    # 5. Entropy Loss (medio centro)
    ax5 = plt.subplot(3, 3, 5)
    ax5.set_title('Entropy Loss', fontweight='bold')
    ax5.set_ylabel('Loss')
    ax5.grid(True, alpha=0.3)
    
    # 6. Learning Rate (medio derecha)
    ax6 = plt.subplot(3, 3, 6)
    ax6.set_title('Learning Rate', fontweight='bold')
    ax6.set_ylabel('Learning Rate')
    ax6.set_yscale('log')
    ax6.grid(True, alpha=0.3)
    
    # 7. Explained Variance (abajo izquierda)
    ax7 = plt.subplot(3, 3, 7)
    ax7.set_title('Explained Variance', fontweight='bold')
    ax7.set_ylabel('Variance')
    ax7.set_xlabel('Timesteps')
    ax7.grid(True, alpha=0.3)
    ax7.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    
    # 8. Tiempo transcurrido (abajo centro)
    ax8 = plt.subplot(3, 3, 8)
    ax8.set_title('Tiempo Transcurrido', fontweight='bold')
    ax8.axis('off')
    
    # 9. Status/Log (abajo derecha)
    ax9 = plt.subplot(3, 3, 9)
    ax9.set_title('Estado', fontweight='bold')
    ax9.axis('off')
    
    axes = {
        'timesteps': ax1,
        'fps': ax2,
        'policy_loss': ax3,
        'value_loss': ax4,
        'entropy_loss': ax5,
        'learning_rate': ax6,
        'explained_variance': ax7,
        'time': ax8,
        'status': ax9
    }
    
    plt.tight_layout()
    
    return fig, axes


def update_plots(frame, ppo_monitor, a2c_monitor, fig, axes, output_dir):
    """Actualiza todas las gráficas"""
    
    # Leer nuevos datos
    ppo_updated = ppo_monitor.read_new_logs()
    a2c_updated = a2c_monitor.read_new_logs()
    
    if not (ppo_updated or a2c_updated):
        return
    
    # Limpiar ejes
    for ax in axes.values():
        ax.clear()
    
    # 1. Timesteps
    ax = axes['timesteps']
    if ppo_monitor.timesteps:
        ax.plot(list(ppo_monitor.timesteps), 'b-', label='PPO', linewidth=2, marker='o', markersize=3)
    if a2c_monitor.timesteps:
        ax.plot(list(a2c_monitor.timesteps), 'g-', label='A2C', linewidth=2, marker='s', markersize=3)
    ax.axhline(y=17520, color='r', linestyle='--', alpha=0.5, label='Target')
    ax.set_title('Progreso (Timesteps)', fontweight='bold')
    ax.set_ylabel('Timesteps')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 2. FPS
    ax = axes['fps']
    if ppo_monitor.fps:
        ax.plot(list(ppo_monitor.fps), 'b-', label='PPO', linewidth=2, marker='o', markersize=3)
    if a2c_monitor.fps:
        ax.plot(list(a2c_monitor.fps), 'g-', label='A2C', linewidth=2, marker='s', markersize=3)
    ax.set_title('Velocidad (FPS)', fontweight='bold')
    ax.set_ylabel('Frames/sec')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 3. Policy Loss
    ax = axes['policy_loss']
    if ppo_monitor.policy_loss:
        ax.plot(list(ppo_monitor.policy_loss), 'b-', label='PPO', linewidth=2, alpha=0.7)
    if a2c_monitor.policy_loss:
        ax.plot(list(a2c_monitor.policy_loss), 'g-', label='A2C', linewidth=2, alpha=0.7)
    ax.set_title('Policy Loss', fontweight='bold')
    ax.set_ylabel('Loss')
    ax.set_yscale('symlog')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 4. Value Loss
    ax = axes['value_loss']
    if ppo_monitor.value_loss:
        ax.plot(list(ppo_monitor.value_loss), 'b-', label='PPO', linewidth=2, alpha=0.7)
    if a2c_monitor.value_loss:
        ax.plot(list(a2c_monitor.value_loss), 'g-', label='A2C', linewidth=2, alpha=0.7)
    ax.set_title('Value Loss', fontweight='bold')
    ax.set_ylabel('Loss')
    ax.set_yscale('symlog')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 5. Entropy Loss
    ax = axes['entropy_loss']
    if ppo_monitor.entropy_loss:
        ax.plot(list(ppo_monitor.entropy_loss), 'b-', label='PPO', linewidth=2, alpha=0.7)
    if a2c_monitor.entropy_loss:
        ax.plot(list(a2c_monitor.entropy_loss), 'g-', label='A2C', linewidth=2, alpha=0.7)
    ax.set_title('Entropy Loss', fontweight='bold')
    ax.set_ylabel('Loss')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 6. Learning Rate
    ax = axes['learning_rate']
    if ppo_monitor.learning_rate:
        ax.plot(list(ppo_monitor.learning_rate), 'b-', label='PPO', linewidth=2, alpha=0.7)
    if a2c_monitor.learning_rate:
        ax.plot(list(a2c_monitor.learning_rate), 'g-', label='A2C', linewidth=2, alpha=0.7)
    ax.set_title('Learning Rate', fontweight='bold')
    ax.set_ylabel('Learning Rate')
    ax.set_yscale('log')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 7. Explained Variance
    ax = axes['explained_variance']
    if ppo_monitor.explained_variance:
        ax.plot(list(ppo_monitor.explained_variance), 'b-', label='PPO', linewidth=2, alpha=0.7)
    if a2c_monitor.explained_variance:
        ax.plot(list(a2c_monitor.explained_variance), 'g-', label='A2C', linewidth=2, alpha=0.7)
    ax.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax.set_title('Explained Variance', fontweight='bold')
    ax.set_ylabel('Variance')
    ax.set_xlabel('Updates')
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # 8. Tiempo transcurrido
    ax = axes['time']
    ax.axis('off')
    ppo_status = ppo_monitor.get_status()
    a2c_status = a2c_monitor.get_status()
    
    time_str = f"""TIEMPO TRANSCURRIDO
    PPO: {ppo_status['elapsed']/60:.1f} min
    A2C: {a2c_status['elapsed']/60:.1f} min
    
    Actualizado: {datetime.now().strftime('%H:%M:%S')}"""
    
    ax.text(0.1, 0.5, time_str, fontsize=10, family='monospace',
            verticalalignment='center', transform=ax.transAxes)
    
    # 9. Status
    ax = axes['status']
    ax.axis('off')
    
    status_str = f"""ESTADO
    PPO:
      Timesteps: {ppo_status['timesteps']}/17520
      FPS: {ppo_status['fps']}
      Progreso: {ppo_status['timesteps']/17520*100:.1f}%
    
    A2C:
      Timesteps: {a2c_status['timesteps']}/17520
      FPS: {a2c_status['fps']}
      Progreso: {a2c_status['timesteps']/17520*100:.1f}%"""
    
    ax.text(0.1, 0.5, status_str, fontsize=10, family='monospace',
            verticalalignment='center', transform=ax.transAxes)
    
    # Guardar gráfica cada 10 actualizaciones
    if frame % 10 == 0 and (ppo_updated or a2c_updated):
        output_path = Path(output_dir) / f"entrenamiento_frame_{frame:04d}.png"
        fig.savefig(str(output_path), dpi=100, bbox_inches='tight')
        logger.info(f"✅ Gráfica guardada: {output_path}")


def main():
    logger.info("\n" + "="*80)
    logger.info("MONITOR EN TIEMPO REAL - PPO vs A2C".center(80))
    logger.info("="*80 + "\n")
    
    # Crear directorio de salida
    output_dir = Path("analyses/oe3/training/graficas_monitor")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Directorio de gráficas: {output_dir}\n")
    
    # Crear monitores
    ppo_log = "analyses/logs/ppo_gpu_fixed.log"
    a2c_log = "analyses/logs/a2c_gpu_fixed.log"
    
    ppo_monitor = TrainingMonitor(ppo_log, "PPO")
    a2c_monitor = TrainingMonitor(a2c_log, "A2C")
    
    logger.info(f"📊 Monitoreando:")
    logger.info(f"   PPO: {ppo_log}")
    logger.info(f"   A2C: {a2c_log}\n")
    
    # Crear dashboard
    fig, axes = create_dashboard(ppo_monitor, a2c_monitor)
    
    # Crear animación
    logger.info("▶️  Iniciando actualización de gráficas cada 5 segundos...\n")
    
    frame_count = 0
    try:
        while True:
            update_plots(frame_count, ppo_monitor, a2c_monitor, fig, axes, output_dir)
            plt.pause(5)  # Actualizar cada 5 segundos
            frame_count += 1
            
            # Guardar cada 30 iteraciones también
            if frame_count % 30 == 0:
                logger.info(f"📈 Actualización #{frame_count}...")
            
    except KeyboardInterrupt:
        logger.info("\n\n✅ Monitor detenido por usuario")
        plt.close()
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
