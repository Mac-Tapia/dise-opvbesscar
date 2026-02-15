"""
MULTI-OBJECTIVE REWARD FUNCTION
Integra objetivos de entrenamiento con device controllers y energy dispatch

Componente recompensa basada en:
1. Cumplimiento de objetivos (motos, mototaxis, BESS, mall, CO2)
2. Energy prioritization (EVs > BESS > MALL)
3. BESS intelligent cutoff (>2000kW mall = 0% supply)
4. Solar maximization (avoid curtailment)
5. Grid minimization (reduce import)
"""

from typing import Dict, Tuple, Any
import numpy as np
from dataclasses import dataclass


@dataclass
class MultiObjectiveRewardCalculator:
    """Calcula reward basado en múltiples objetivos en tiempo real"""
    
    # Pesos por componente (suman a 1.0)
    weight_motos: float = 0.20
    weight_mototaxis: float = 0.15
    weight_bess: float = 0.20
    weight_mall: float = 0.20
    weight_co2: float = 0.25
    
    # Pesos secundarios para energía y dispatch
    weight_energy_priority: float = 0.10
    weight_solar_maximum: float = 0.10
    
    # Estado acumulativo para cálculos
    episode_motos_charged_100: int = 0
    episode_mototaxis_charged_100: int = 0
    episode_co2_kg: float = 0.0
    episode_bess_discharged_kwh: float = 0.0
    episode_solar_curtailed_kwh: float = 0.0
    episode_grid_import_kwh: float = 0.0
    timestep_count: int = 0
    
    def __post_init__(self):
        """Validar que pesos sumen a 1.0"""
        total_weight = (self.weight_motos + self.weight_mototaxis + 
                       self.weight_bess + self.weight_mall + self.weight_co2)
        if not (0.99 < total_weight < 1.01):
            print(f"[ADVERTENCIA] Pesos no suman a 1.0: {total_weight:.3f}")
    
    def calculate_timestep_reward(
        self,
        obs: Dict[str, Any],
        action: np.ndarray,
        info: Dict[str, Any],
        timestep: int,
        is_peak_hour: bool,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calcular reward para timestep actual
        
        Args:
            obs: Observation dict con métricas de dispositivos
            action: Control actions [1 BESS + 38 EVs]
            info: Additional info (solar, demand, etc)
            timestep: Hora del año (0-8759)
            is_peak_hour: True si es 18:00-22:00
        
        Returns:
            (reward, components_dict)
        """
        
        self.timestep_count += 1
        reward_components = {}
        
        # ===== COMPONENT 1: MOTOS (30 sockets) =====
        motos_soc = obs.get('motos_avg_soc', 0.5)
        motos_charging_now = obs.get('motos_charging_count', 0)
        motos_urgent = obs.get('motos_urgent_count', 0)
        
        # Reward por SOC alto y urgencias resueltas
        motos_soc_reward = (motos_soc - 0.3) / 0.5  # Normalizar [0.3, 0.8] → [0, 1]
        motos_soc_reward = np.clip(motos_soc_reward, 0, 1)
        
        # Penalti si hay urgencias sin resolver
        motos_urgent_penalty = motos_urgent * 0.05
        
        r_motos = (motos_soc_reward * 0.7 - motos_urgent_penalty * 0.3)
        reward_components['motos'] = float(r_motos)
        
        # ===== COMPONENT 2: MOTOTAXIS (8 sockets) =====
        mototaxis_soc = obs.get('mototaxis_avg_soc', 0.5)
        mototaxis_charging_now = obs.get('mototaxis_charging_count', 0)
        mototaxis_urgent = obs.get('mototaxis_urgent_count', 0)
        
        # Mototaxis requiere SOC >70% (viajes largos)
        mototaxis_soc_target = 0.70
        mototaxis_soc_diff = abs(mototaxis_soc - mototaxis_soc_target)
        mototaxis_soc_reward = max(0, 1.0 - (mototaxis_soc_diff / 0.3))
        
        mototaxis_urgent_penalty = mototaxis_urgent * 0.10  # Más crítico
        
        r_mototaxis = (mototaxis_soc_reward * 0.7 - mototaxis_urgent_penalty * 0.3)
        reward_components['mototaxis'] = float(r_mototaxis)
        
        # ===== COMPONENT 3: BESS (940 kWh, intelligent cutoff) =====
        bess_soc = obs.get('bess_soc', 50) / 100.0  # Convertir a [0, 1]
        mall_demand_kw = obs.get('mall_demand_kw', 1500)
        
        if is_peak_hour:
            # PICOS: Mantener SOC >30%
            bess_peak_target = 0.30
            bess_peak_diff = abs(bess_soc - bess_peak_target)
            r_bess_peak = max(0, 1.0 - (bess_peak_diff / 0.5))
            
            # CRITICAL: Si mall >2000kW, BESS debe estar disponible para corte
            if mall_demand_kw > 2000:
                # Reward extra si BESS está disponible para ayudar
                bess_available_reward = 0.5 if bess_soc > bess_peak_target else -0.5
            else:
                bess_available_reward = 0.0
            
            r_bess = r_bess_peak * 0.6 + bess_available_reward * 0.4
        else:
            # HORAS NORMALES: Cargar desde solar excedente
            # Reward por SOC en rango de carga óptima (50-80%)
            bess_charging_target_min = 0.50
            bess_charging_target_max = 0.80
            
            if bess_charging_target_min <= bess_soc <= bess_charging_target_max:
                r_bess = 0.8  # Rango óptimo
            elif bess_soc < bess_charging_target_min:
                r_bess = 0.5 + (bess_soc / bess_charging_target_min) * 0.3
            else:
                r_bess = 0.8 - ((bess_soc - bess_charging_target_max) / 0.2) * 0.3
        
        reward_components['bess'] = float(r_bess)
        
        # ===== COMPONENT 4: MALL (Intelligent cutoff strategy) =====
        mall_supply_ratio = obs.get('mall_supply_ratio', 1.0)
        
        if is_peak_hour and mall_demand_kw > 2000:
            # PICOS ALTOS: CORTE inteligente = 0% supply
            # Reward si se logra corte (acción debe ser 0%)
            bess_action = action[0]  # Primer elemento es BESS
            mall_charger_actions = action[1:]  # 38 acciones de chargers
            
            # Si BESS = 0 y chargers prioritarios a EVs, es correcto
            cutoff_success = (bess_action < 0.1) and (np.mean(mall_charger_actions) > 0.7)
            r_mall = 1.0 if cutoff_success else -0.5
        else:
            # HORAS NORMALES: 100% suministro mall
            # Reward si supply_ratio está cercano a 1.0
            r_mall = max(0, 1.0 - abs(mall_supply_ratio - 1.0))
        
        reward_components['mall'] = float(r_mall)
        
        # ===== COMPONENT 5: CO2 Minimization =====
        grid_import_kwh = obs.get('grid_import_kwh', 0)
        solar_available_kwh = obs.get('solar_available_kwh', 0)
        total_demand_kwh = obs.get('total_demand_kwh', 100)
        
        # Calcular ratio import grid
        if total_demand_kwh > 0:
            grid_import_ratio = grid_import_kwh / total_demand_kwh
            co2_emission_kg = grid_import_kwh * 0.4521  # kg CO2/kWh Iquitos thermal
        else:
            grid_import_ratio = 0.0
            co2_emission_kg = 0.0
        
        # Reward inversamente proporcional a import grid
        target_import_ratio = 0.30  # Objetivo: <30%
        import_ratio_diff = (grid_import_ratio - target_import_ratio) / target_import_ratio
        r_co2 = max(-1.0, 1.0 - import_ratio_diff)
        
        reward_components['co2'] = float(r_co2)
        
        # Acumular CO2 del año
        self.episode_co2_kg += co2_emission_kg
        self.episode_grid_import_kwh += grid_import_kwh
        
        # ===== SECONDARY: Energy Priority =====
        # Penalti si hay energía desperdiciada
        solar_curtailed_kwh = obs.get('solar_curtailed_kwh', 0)
        self.episode_solar_curtailed_kwh += solar_curtailed_kwh
        
        r_energy_priority = max(-1.0, 1.0 - (solar_curtailed_kwh / max(1, solar_available_kwh)))
        reward_components['energy_priority'] = float(r_energy_priority)
        
        # ===== COMBINED REWARD =====
        # Weighted sum of all components
        combined_reward = (
            self.weight_motos * r_motos +
            self.weight_mototaxis * r_mototaxis +
            self.weight_bess * r_bess +
            self.weight_mall * r_mall +
            self.weight_co2 * r_co2 +
            self.weight_energy_priority * r_energy_priority
        )
        
        # Clip reward para evitar extremos
        combined_reward = np.clip(combined_reward, -1.0, 1.0)
        reward_components['combined'] = float(combined_reward)
        
        return combined_reward, reward_components
    
    def get_episode_summary(self) -> Dict[str, float]:
        """Resumen de métricas del episodio completo"""
        
        avg_co2_kg = self.episode_co2_kg / max(1, self.timestep_count)
        annual_co2_kg = avg_co2_kg * 8760
        
        avg_grid_import = self.episode_grid_import_kwh / max(1, self.timestep_count)
        annual_grid_import = avg_grid_import * 8760
        
        return {
            'timesteps': self.timestep_count,
            'annual_co2_kg': annual_co2_kg,
            'annual_grid_import_kwh': annual_grid_import,
            'total_solar_curtailed_kwh': self.episode_solar_curtailed_kwh,
            'motos_charged_100_total': self.episode_motos_charged_100,
            'mototaxis_charged_100_total': self.episode_mototaxis_charged_100,
            'bess_discharged_kwh': self.episode_bess_discharged_kwh,
        }
    
    def reset_episode(self):
        """Reset acumuladores para nuevo episodio"""
        self.episode_motos_charged_100 = 0
        self.episode_mototaxis_charged_100 = 0
        self.episode_co2_kg = 0.0
        self.episode_bess_discharged_kwh = 0.0
        self.episode_solar_curtailed_kwh = 0.0
        self.episode_grid_import_kwh = 0.0
        self.timestep_count = 0


if __name__ == "__main__":
    # Test del reward calculator
    calc = MultiObjectiveRewardCalculator()
    
    # Simular timestep típico
    obs = {
        'motos_avg_soc': 0.65,
        'motos_charging_count': 5,
        'motos_urgent_count': 0,
        'mototaxis_avg_soc': 0.72,
        'mototaxis_charging_count': 2,
        'mototaxis_urgent_count': 1,
        'bess_soc': 60,
        'mall_demand_kw': 1800,
        'mall_supply_ratio': 0.95,
        'grid_import_kwh': 20,
        'solar_available_kwh': 100,
        'total_demand_kwh': 150,
        'solar_curtailed_kwh': 5,
    }
    
    action = np.array([0.7] + [0.5]*38)  # BESS 70%, chargers moderate
    
    reward, components = calc.calculate_timestep_reward(
        obs=obs,
        action=action,
        info={},
        timestep=500,
        is_peak_hour=False
    )
    
    print(f"\nTest Reward Calculation:")
    print(f"  Combined Reward: {reward:.4f}")
    print(f"  Components:")
    for key, val in components.items():
        print(f"    {key}: {val:.4f}")
    
    print(f"\nWeights:")
    print(f"  Motos: {calc.weight_motos:.2f}")
    print(f"  Mototaxis: {calc.weight_mototaxis:.2f}")
    print(f"  BESS: {calc.weight_bess:.2f}")
    print(f"  Mall: {calc.weight_mall:.2f}")
    print(f"  CO2: {calc.weight_co2:.2f}")
