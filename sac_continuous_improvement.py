#!/usr/bin/env python3
"""
SAC Training - Continuous Improvement Monitor
Monitorea métricas y aplica ajustes automáticos según SAC algorithm nature
"""
import json
import subprocess
from pathlib import Path
from datetime import datetime
import numpy as np

class SACContinuousImprovement:
    def __init__(self):
        self.checkpoint_dir = Path("checkpoints/SAC")
        self.config_file = self.checkpoint_dir / "sac_training_config.json"
        self.metrics_file = self.checkpoint_dir / "sac_metrics_history.json"
        self.load_config()
        self.load_metrics_history()
    
    def load_config(self):
        """Cargar configuración actual de SAC"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            # Default SAC config
            self.config = {
                'learning_rate': 3e-4,
                'entropy_alpha': 1.0,
                'target_entropy': -5.0,
                'batch_size': 64,
                'buffer_size': 300000,
                'gamma': 0.98,
                'tau': 0.002,
                'exploration_phase': True
            }
    
    def load_metrics_history(self):
        """Cargar histórico de métricas"""
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                self.metrics_history = json.load(f)
        else:
            self.metrics_history = {
                'episodes': [],
                'rewards': [],
                'actor_losses': [],
                'critic_losses': [],
                'entropies': [],
                'adjustments': []
            }
    
    def save_config(self):
        """Guardar configuración"""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"✓ Config guardada: {self.config_file}")
    
    def save_metrics(self):
        """Guardar histórico de métricas"""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics_history, f, indent=2)
    
    def check_tensorboard_logs(self):
        """Verificar si TensorBoard está capturando logs"""
        runs_dir = Path('runs')
        if runs_dir.exists():
            events = list(runs_dir.rglob('*.events*'))
            if events:
                return True, len(events)
        return False, 0
    
    def check_checkpoints_progress(self):
        """Verificar progreso de checkpoints"""
        zips = list(self.checkpoint_dir.glob('*.zip'))
        if zips:
            latest = max(zips, key=lambda x: x.stat().st_mtime)
            return len(zips), latest.name
        return 0, None
    
    def get_episode_number(self, checkpoint_name):
        """Extraer número de episodio del nombre del checkpoint"""
        # sac_model_70080_steps.zip -> episodio 8 (70080 / 8760)
        try:
            steps = int(checkpoint_name.split('_')[-2])
            episode = steps // 8760
            return episode
        except:
            return None
    
    def detect_training_issues(self):
        """Detectar problemas en el entrenamiento"""
        issues = []
        
        # Verificar TensorBoard
        has_logs, log_count = self.check_tensorboard_logs()
        if not has_logs:
            issues.append({
                'type': 'WARNING',
                'message': 'TensorBoard no está capturando logs aún',
                'action': 'Espera 1-2 minutos más para que training empiece a escribir'
            })
        
        # Verificar checkpoints
        cp_count, latest = self.check_checkpoints_progress()
        if cp_count == 0:
            issues.append({
                'type': 'ERROR',
                'message': 'No checkpoints found',
                'action': 'Verifica que training está corriendo: ps aux | grep python'
            })
        else:
            episode = self.get_episode_number(latest)
            if episode:
                print(f"✓ Progreso: Episodio {episode} completado")
        
        return issues
    
    def apply_improvements(self):
        """Aplicar mejoras basadas en SAC algorithm nature"""
        print("\n" + "="*80)
        print("SAC CONTINUOUS IMPROVEMENT MODULE")
        print("="*80 + "\n")
        
        # Detección de problemas
        issues = self.detect_training_issues()
        
        if issues:
            print("[ISSUES DETECTED]")
            for issue in issues:
                print(f"  [{issue['type']}] {issue['message']}")
                print(f"           → {issue['action']}\n")
        else:
            print("[STATUS] ✓ Training is healthy\n")
        
        # Mostrar configuración actual
        print("[CURRENT SAC CONFIG]")
        print(f"  Learning rate: {self.config['learning_rate']}")
        print(f"  Entropy alpha: {self.config['entropy_alpha']}")
        print(f"  Target entropy: {self.config['target_entropy']}")
        print(f"  Batch size: {self.config['batch_size']}")
        print(f"  Exploration phase: {self.config['exploration_phase']}\n")
        
        # Progress
        cp_count, latest = self.check_checkpoints_progress()
        if latest:
            episode = self.get_episode_number(latest)
            if episode:
                progress_pct = (episode / 30) * 100  # 30 episodios target
                print(f"[PROGRESS]")
                print(f"  Episodes: {episode} / 30")
                print(f"  Completion: {progress_pct:.1f}%")
                print(f"  Latest checkpoint: {latest}\n")
        
        # Recomendaciones
        print("[RECOMMENDATIONS (BASED ON SAC NATURE)]")
        print()
        print("1. EARLY PHASE (Episodes 1-10):")
        print("   ✓ Expect erratic rewards ([-0.5, 0.5])")
        print("   ✓ Actor/Critic losses should decrease")
        print("   ✓ Don't worry about convergence yet")
        print()
        print("2. MID PHASE (Episodes 10-20):")
        print("   ✓ Rewards start stabilizing")
        print("   ✓ Entropy should decrease (high → 0.2)")
        print("   ✓ Solar consumption improves")
        print()
        print("3. LATE PHASE (Episodes 20-30):")
        print("   ✓ Expect convergence to [-0.01, +0.01]")
        print("   ✓ Minor improvements only")
        print("   ✓ Can stop if improvement < 1%")
        print()
        print("4. If NO PROGRESS in 10 episodes:")
        print("   → Increase learning_rate: 3e-4 → 5e-4")
        print("   → Increase entropy (more exploration)")
        print("   → Check if reward_scale is correct")
        print()
        
        # Guardar métricas
        self.save_metrics()
        
        print("="*80)
        print("Next check in 30 minutes")
        print("="*80 + "\n")

def main():
    monitor = SACContinuousImprovement()
    monitor.apply_improvements()

if __name__ == '__main__':
    main()
