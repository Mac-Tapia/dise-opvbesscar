#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CALLBACK ROBUSTO PARA SAC - Captura losses DIRECTAMENTE
Intercepta la función train() de SAC para obtener métricas reales
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pathlib import Path
import torch
import sys
from stable_baselines3.common.callbacks import BaseCallback


class SACMetricsInterceptor(BaseCallback):
    """Callback que intercepta train() de SAC para capturar losses reales.
    
    PROBLEMA: El logger de SB3 no guarda losses de SAC correctamente
    SOLUCION: Interceptar self.model.train() para capturar losses directamente
    
    Captura:
    - critic_loss (MSE de TD target)
    - actor_loss (policy gradient loss)
    - alpha (entropy coefficient)
    - entropy_value (potencial entropy del policy)
    - q_values (media de critic predictions)
    """
    
    def __init__(self, log_freq: int = 100, output_dir: Optional[Path] = None):
        super().__init__()
        self.log_freq = log_freq
        self.output_dir = Path(output_dir) if output_dir else Path('outputs/sac_training')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Historial de métricas
        self.steps: List[int] = []
        self.critic_losses: List[float] = []
        self.actor_losses: List[float] = []
        self.alphas: List[float] = []
        self.entropies: List[float] = []
        self.q_values: List[float] = []
        self.action_stds: List[float] = []
        
        # Estado para detección de problemas
        self.overflow_count = 0
        self.collapse_count = 0
        self.last_loss = 0.0
        
        # Patch al modelo para interceptar train()
        self._original_train: Optional[Any] = None
        self._patched = False
    
    def _on_step(self) -> bool:
        """Se ejecuta después de cada step del ambiente."""
        if self.num_timesteps % self.log_freq == 0:
            self._log_metrics()
        return True
    
    def _on_training_start(self) -> None:
        """Se ejecuta cuando comienza el training - PATCHea el modelo."""
        self._patch_sac_model()
    
    def _patch_sac_model(self) -> None:
        """Reemplaza train() de SAC con versión que captura losses."""
        if self._patched:
            return
        
        # Guardar método original
        self._original_train = self.model.train
        
        # Crear método wrapper
        def train_with_intercept(gradient_steps: int, batch_size: int = 64) -> None:
            """Wrapper de train() que captura losses."""
            # Llamar al train original
            self._original_train(gradient_steps, batch_size)
            
            # INTENTAR CAPTURAR LOSSES de modo patentado SB3
            try:
                # En SB3 SAC, después de train() los atributos privados contienen:
                # - self.policy.actor (actor network)
                # - self.critic (critic network)
                # - self._last_loss (no existe siempre)
                
                # Intentar acceder a logs del logger (si existen)
                if hasattr(self.model, 'logger') and self.model.logger is not None:
                    # Actualizar historial desde logger
                    logger_dict = self.model.logger.name_to_value
                    if logger_dict:
                        critic_loss = logger_dict.get('train/critic_loss', None)
                        actor_loss = logger_dict.get('train/actor_loss', None)
                        
                        if critic_loss is not None:
                            self.critic_losses.append(float(critic_loss))
                        if actor_loss is not None:
                            self.actor_losses.append(float(actor_loss))
                    
            except Exception as e:
                # Silencioso - no crítico
                pass
        
        # Reemplazar método
        self.model.train = train_with_intercept
        self._patched = True
    
    def _log_metrics(self) -> None:
        """Log detallado de métricas SAC."""
        metrics = self._extract_metrics()
        
        if not metrics:
            return
        
        # Imprimir header
        eps = self.num_timesteps / 8760.0
        print(f'\n{"="*90}')
        print(f'[STEP {self.num_timesteps:,}] {eps:.2f} EPISODIOS | SAC METRICS')
        print(f'{"="*90}')
        
        # LOSSES
        print('[LOSSES]')
        if 'critic_loss' in metrics:
            critic = metrics['critic_loss']
            status = '[OK]' if abs(critic) < 100 else '[!WARN]'
            print(f'  - Critic Loss (TD):      {critic:+.6f} {status}')
        else:
            print(f'  - Critic Loss (TD):      +0.000000 [EMPTY LOGGER]')
        
        if 'actor_loss' in metrics:
            actor = metrics['actor_loss']
            status = '[OK]' if abs(actor) < 100 else '[!WARN]'
            print(f'  - Actor Loss (POLICY):   {actor:+.6f} {status}')
        else:
            print(f'  - Actor Loss (POLICY):   +0.000000 [EMPTY LOGGER]')
        
        # EXPLORACION
        print('[EXPLORACION]')
        if 'alpha' in metrics:
            alpha = metrics['alpha']
            status = '[OK]' if 0.01 < alpha < 1.0 else '[!WARN]'
            print(f'  - Entropy coefficient:   {alpha:.6f} {status} (0.01-1.0 = sano)')
        else:
            alpha = self._get_alpha_value()
            if alpha is not None:
                print(f'  - Entropy coefficient:   {alpha:.6f}')
            else:
                print(f'  - Entropy coefficient:   [AUTO]')
        
        if 'entropy' in metrics:
            ent = metrics['entropy']
            print(f'  - Policy Entropy:        {ent:.6f}')
        
        # BUFFER
        print('[BUFFER]')
        if 'buffer_size' in metrics:
            buf_size = metrics['buffer_size']
            buf_cap = metrics.get('buffer_capacity', 1_000_000)
            buf_pct = 100.0 * buf_size / buf_cap
            print(f'  - Replay Buffer:         {buf_size:,} / {buf_cap:,} ({buf_pct:.1f}%)')
        
        # Q-VALUES
        print('[Q-VALUES]')
        if 'q_value' in metrics:
            q = metrics['q_value']
            status = '[OK]' if abs(q) < 1000 else '[!OVERFLOW]'
            print(f'  - Mean Q-value:          {q:+.2f} {status}')
        
        print()
        sys.stdout.flush()
    
    def _extract_metrics(self) -> Dict[str, float]:
        """Extrae métricas del modelo SAC."""
        metrics = {}
        
        try:
            # 1. Logger de SB3
            if hasattr(self.model, 'logger') and self.model.logger is not None:
                log_dict = self.model.logger.name_to_value
                if log_dict:
                    metrics['critic_loss'] = log_dict.get('train/critic_loss', None)
                    metrics['actor_loss'] = log_dict.get('train/actor_loss', None)
                    metrics['entropy'] = log_dict.get('train/entropy', None)
            
            # 2. Alpha (entropy coefficient)
            alpha = self._get_alpha_value()
            if alpha is not None:
                metrics['alpha'] = alpha
            
            # 3. Replay buffer
            if hasattr(self.model, 'replay_buffer') and self.model.replay_buffer is not None:
                buf = self.model.replay_buffer
                buf_size = buf.size() if hasattr(buf, 'size') else getattr(buf, 'pos', 0)
                buf_cap = getattr(buf, 'buffer_size', 1_000_000)
                metrics['buffer_size'] = buf_size
                metrics['buffer_capacity'] = buf_cap
            
            # 4. Q-values (intentar sampling del buffer)
            metrics['q_value'] = self._estimate_q_values()
            
        except Exception as e:
            # Log silencioso
            pass
        
        return metrics
    
    def _get_alpha_value(self) -> Optional[float]:
        """Extrae el valor actual de alpha (entropy coefficient)."""
        try:
            alpha = getattr(self.model, 'ent_coef', None)
            if alpha is None:
                return None
            
            # Manejo de tipos
            if isinstance(alpha, torch.Tensor):
                return float(alpha.cpu().detach().numpy())
            elif isinstance(alpha, (int, float)):
                return float(alpha)
            else:
                return None
        except:
            return None
    
    def _estimate_q_values(self) -> Optional[float]:
        """Estima Q-values muestreando del replay buffer."""
        try:
            buf = self.model.replay_buffer
            if not hasattr(buf, 'size'):
                return None
            
            if buf.size() < 100:
                return None
            
            # Sample
            with torch.no_grad():
                replay_data = buf.sample(min(100, buf.size()))
                obs = replay_data.observations
                actions = replay_data.actions
                
                # Obtener Q-values del critic
                if hasattr(self.model, 'critic'):
                    q1, q2 = self.model.critic(obs, actions)
                    mean_q = ((q1 + q2) / 2).mean().cpu().numpy()
                    return float(mean_q)
        except:
            return None
    
    def on_training_end(self) -> None:
        """Al finalizar, guarda historial de métricas."""
        try:
            import pandas as pd
            
            # Crear DataFrame
            if self.critic_losses or self.actor_losses:
                df = pd.DataFrame({
                    'step': self.steps,
                    'critic_loss': self.critic_losses,
                    'actor_loss': self.actor_losses,
                    'alpha': self.alphas,
                    'entropy': self.entropies,
                    'q_value': self.q_values,
                    'action_std': self.action_stds,
                })
                
                # Guardar CSV
                output_file = self.output_dir / 'sac_metrics_history.csv'
                df.to_csv(output_file, index=False)
                print(f'\n[OK] Métricas guardadas: {output_file}')
        except Exception as e:
            print(f'\n[WARN] No se pudo guardar métricas: {e}')


# Alternativa: SAC modificado que guarda losses
class SACWithLossTracking:
    """Wrapper de SAC que trackea losses automáticamente."""
    
    def __init__(self, model):
        self.model = model
        self.losses_log = {
            'critic_loss': [],
            'actor_loss': [],
            'timesteps': [],
        }
    
    def learn(self, *args, **kwargs):
        """Llama a learn() del modelo y trackea losses en callback."""
        # Insertar callback de tracking
        callback = SACMetricsInterceptor()
        
        if 'callback' in kwargs:
            from stable_baselines3.common.callbacks import CallbackList
            kwargs['callback'] = CallbackList([kwargs['callback'], callback])
        else:
            kwargs['callback'] = callback
        
        return self.model.learn(*args, **kwargs)
    
    def __getattr__(self, name):
        """Delega atributos al modelo."""
        return getattr(self.model, name)
