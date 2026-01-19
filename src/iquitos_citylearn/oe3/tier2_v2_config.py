"""
Configuración TIER 2 V2 MEJORADA - Con hiperparámetros ajustados para estabilidad crítica.

Cambios:
1. Entropy coef FIJO en 0.01 (no dinámico)
2. Learning rate REDUCIDO a 1.5e-4 en hora pico (estabilidad)
3. Normalización de observables HABILITADA
4. Clipping de observables establecido
5. Penalizaciones de recompensa normalizadas
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class TIER2V2Config:
    """Configuración unificada TIER 2 V2 para A2C, PPO, SAC."""
    
    # ===== LEARNING =====
    learning_rate_base: float = 2.5e-4      # Base de aprendizaje
    learning_rate_peak: float = 1.5e-4      # Reducido en pico (estabilidad)
    
    # ===== EXPLORACIÓN =====
    entropy_coef_fixed: float = 0.01        # FIJO: no adaptativo
    entropy_coef_init: float = 0.01         # Para compat. backward
    entropy_coef_final: float = 0.01        # No decae
    
    # ===== RED NEURONAL =====
    hidden_sizes: tuple = (512, 512)        # Capacidad
    activation: str = "relu"                # ReLU > tanh
    
    # ===== NORMALIZACIÓN =====
    normalize_observations: bool = True     # HABILITADA
    normalize_rewards: bool = True          # HABILITADA
    clip_observations: float = 10.0         # Clipping obs
    reward_scale: float = 0.01              # Factor escala
    
    # ===== BATCH/STEPS (Según agente) =====
    # PPO
    ppo_batch_size: int = 256
    ppo_n_epochs: int = 15
    ppo_n_steps: int = 2048
    ppo_clip_range: float = 0.2
    
    # A2C
    a2c_n_steps: int = 1024                 # Recolección
    a2c_gae_lambda: float = 0.95
    
    # SAC
    sac_batch_size: int = 256
    sac_learning_starts: int = 100
    sac_train_freq: int = 2
    sac_target_update_interval: int = 1
    
    # ===== MULTIOBJETIVO MEJORADO =====
    co2_weight: float = 0.55                # PRIMARY
    solar_weight: float = 0.20              # SECONDARY
    cost_weight: float = 0.10               # REDUCIDO
    ev_satisfaction_weight: float = 0.10    # BÁSICA
    grid_stability_weight: float = 0.05     # REDUCIDO (en CO₂)
    
    # Penalizaciones explícitas
    peak_power_penalty: float = 0.30        # Si excedes límite en pico
    soc_reserve_penalty: float = 0.20       # Si SOC pre-pico < target
    import_peak_penalty: float = 0.25       # Si importación en pico
    fairness_penalty: float = 0.10          # Desequilibrio playas
    
    # ===== CONTROL DE HORA PICO =====
    peak_hours: tuple = (18, 19, 20, 21)
    pre_peak_hours: tuple = (16, 17)
    valley_hours: tuple = (9, 10, 11, 12)
    
    peak_demand_limit_kw: float = 150.0     # Límite HARD pico
    normal_demand_limit_kw: float = 200.0   # Límite suave
    
    bess_soc_target_normal: float = 0.60
    bess_soc_target_prepeak: float = 0.85
    bess_soc_target_peak: float = 0.40
    
    # ===== GPU =====
    use_cuda: bool = True
    use_amp: bool = True                    # Mixed precision
    pin_memory: bool = True
    
    # ===== REPRODUCIBILIDAD =====
    seed: int = 2022
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TIER2V2Config":
        """Crea desde diccionario."""
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in field_names}
        return cls(**filtered)
    
    def get_adjusted_lr(self, hour: int) -> float:
        """Retorna LR según hora."""
        if hour in self.peak_hours:
            return self.learning_rate_peak
        return self.learning_rate_base
    
    def get_entropy_coef(self) -> float:
        """Retorna entropy coef (siempre fijo)."""
        return self.entropy_coef_fixed
    
    def get_soc_target(self, hour: int) -> float:
        """Retorna SOC target dinámico."""
        if hour in self.peak_hours:
            return self.bess_soc_target_peak
        elif hour in self.pre_peak_hours:
            return self.bess_soc_target_prepeak
        return self.bess_soc_target_normal
    
    def is_peak_hour(self, hour: int) -> bool:
        return hour in self.peak_hours
    
    def is_pre_peak_hour(self, hour: int) -> bool:
        return hour in self.pre_peak_hours


# Instancia global por conveniencia
DEFAULT_TIER2V2 = TIER2V2Config()
