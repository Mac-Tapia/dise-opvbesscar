#!/usr/bin/env python
"""
MONITOR GRÁFICO EN TIEMPO REAL - Versión Simplificada
Monitorea PPO y A2C con gráficas en vivo
"""
import sys
import os
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend no-GUI para Windows
import matplotlib.pyplot as plt
from pathlib import Path
from collections import deque
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

class TrainingMonitor:
    """Monitor simplificado de entrenamiento"""
    
    def __init__(self, log_file, agent_name, max_points=200):
        self.log_file = Path(log_file)
        self.agent_name = agent_name
        self.max_points = max_points
        
        self.timesteps = deque(maxlen=max_points)
        self.fps = deque(maxlen=max_points)
        self.policy_loss = deque(maxlen=max_points)
        self.value_loss = deque(maxlen=max_points)
        
        self.last_pos = 0
        
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
                if 'total_timesteps' in line:
                    match = re.search(r'total_timesteps\s*\|\s*(\d+)', line)
                    if match:
                        self.timesteps.append(int(match.group(1)))
                        updated = True
                
                if 'fps' in line and '|' in line:
                    match = re.search(r'fps\s*\|\s*(\d+)', line)
                    if match:
                        self.fps.append(int(match.group(1)))
                
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
            
            return updated
        except Exception as e:
            logger.warning(f"Error leyendo logs: {e}")
            return False


def main():
    logger.info("\n" + "="*80)
    logger.info("MONITOR GRÁFICO EN TIEMPO REAL - PPO vs A2C".center(80))
    logger.info("="*80 + "\n")
    
    output_dir = Path("analyses/oe3/training/graficas_monitor")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Guardando gráficas en: {output_dir}\n")
    
    ppo_monitor = TrainingMonitor("analyses/logs/ppo_gpu_fixed.log", "PPO")
    a2c_monitor = TrainingMonitor("analyses/logs/a2c_gpu_fixed.log", "A2C")
    
    logger.info("▶️  Monitoreando cada 5 segundos...\n")
    
    frame = 0
    try:
        while True:
            ppo_updated = ppo_monitor.read_new_logs()
            a2c_updated = a2c_monitor.read_new_logs()
            
            if ppo_updated or a2c_updated:
                # Crear figura
                fig, axes = plt.subplots(2, 2, figsize=(14, 10))
                fig.suptitle(f'Monitor de Entrenamiento - {datetime.now().strftime("%H:%M:%S")}', 
                           fontsize=14, fontweight='bold')
                
                # Timesteps
                ax = axes[0, 0]
                if ppo_monitor.timesteps:
                    ax.plot(list(ppo_monitor.timesteps), 'b-o', linewidth=2, label='PPO', markersize=4)
                if a2c_monitor.timesteps:
                    ax.plot(list(a2c_monitor.timesteps), 'g-s', linewidth=2, label='A2C', markersize=4)
                ax.axhline(y=17520, color='r', linestyle='--', alpha=0.5, label='Target')
                ax.set_xlabel('Update #')
                ax.set_ylabel('Timesteps')
                ax.set_title('Progreso')
                ax.legend()
                ax.grid(True, alpha=0.3)
                
                # FPS
                ax = axes[0, 1]
                if ppo_monitor.fps:
                    ax.plot(list(ppo_monitor.fps), 'b-o', linewidth=2, label='PPO', markersize=4)
                if a2c_monitor.fps:
                    ax.plot(list(a2c_monitor.fps), 'g-s', linewidth=2, label='A2C', markersize=4)
                ax.set_xlabel('Update #')
                ax.set_ylabel('FPS')
                ax.set_title('Velocidad')
                ax.legend()
                ax.grid(True, alpha=0.3)
                
                # Policy Loss
                ax = axes[1, 0]
                if ppo_monitor.policy_loss:
                    ax.plot(list(ppo_monitor.policy_loss), 'b-o', linewidth=2, label='PPO', markersize=4)
                if a2c_monitor.policy_loss:
                    ax.plot(list(a2c_monitor.policy_loss), 'g-s', linewidth=2, label='A2C', markersize=4)
                ax.set_xlabel('Update #')
                ax.set_ylabel('Loss')
                ax.set_title('Policy Loss')
                ax.set_yscale('symlog')
                ax.legend()
                ax.grid(True, alpha=0.3)
                
                # Value Loss
                ax = axes[1, 1]
                if ppo_monitor.value_loss:
                    ax.plot(list(ppo_monitor.value_loss), 'b-o', linewidth=2, label='PPO', markersize=4)
                if a2c_monitor.value_loss:
                    ax.plot(list(a2c_monitor.value_loss), 'g-s', linewidth=2, label='A2C', markersize=4)
                ax.set_xlabel('Update #')
                ax.set_ylabel('Loss')
                ax.set_title('Value Loss')
                ax.set_yscale('symlog')
                ax.legend()
                ax.grid(True, alpha=0.3)
                
                plt.tight_layout()
                
                # Guardar
                output_file = output_dir / f"monitor_frame_{frame:04d}.png"
                plt.savefig(str(output_file), dpi=100, bbox_inches='tight')
                plt.close()
                
                frame += 1
                logger.info(f"✅ Frame {frame}: PPO={list(ppo_monitor.timesteps)[-1] if ppo_monitor.timesteps else 0}/17520, "
                          f"A2C={list(a2c_monitor.timesteps)[-1] if a2c_monitor.timesteps else 0}/17520")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("\n\n✅ Monitor detenido")
        logger.info(f"📊 {frame} gráficas generadas")


if __name__ == "__main__":
    main()
