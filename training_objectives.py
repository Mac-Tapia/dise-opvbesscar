"""
OBJETIVOS DE ENTRENAMIENTO PARA AGENTE SAC
Basados en análisis real de datasets OE2 2024

Agente debe cumplir estos objetivos simultaneamente:
- MOTOS: Cargar 25/día a 100% (9,125/año), SOC >60%
- MOTOTAXIS: Cargar 7.5/día a 100% (2,737/año), SOC >70%
- BESS: SOC >30% picos, descargar >1.2 GWh/año
- MALL: 100% normal, CORTE a 0% si >2000kW
- CO2: <350k kg/año (-46% vs baseline)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import numpy as np


@dataclass(frozen=True)
class MotosObjective:
    """Objetivos para 30 sockets de motos personales"""
    charged_100_per_day: float = 25.0
    charged_100_per_year: float = 9125.0
    avg_soc_target: float = 0.60  # 60%
    urgent_resolution_rate: float = 0.95
    energy_efficiency: float = 0.85
    
    # Tracking
    name: str = "MOTOS (30 sockets)"
    socket_count: int = 30
    max_soc: float = 0.80  # 80% (baterías de 48 kWh típico)
    min_charge_power_kw: float = 5.0


@dataclass(frozen=True)
class MototaxisObjective:
    """Objetivos para 8 sockets de mototaxis"""
    charged_100_per_day: float = 7.5
    charged_100_per_year: float = 2737.0
    avg_soc_target: float = 0.70  # 70%
    urgent_resolution_rate: float = 0.99  # Viajes largos prioritarios
    energy_efficiency: float = 0.88
    
    # Tracking
    name: str = "MOTOTAXIS (8 sockets)"
    socket_count: int = 8
    max_soc: float = 1.0  # 100% (baterías de 60 kWh)
    min_charge_power_kw: float = 7.4


@dataclass(frozen=True)
class BESSObjective:
    """Objetivos para batería (940 kWh)"""
    peak_min_soc: float = 0.30  # 30% en picos (18:00-22:00)
    discharge_target_kwh: float = 1_200_000  # 1.2 GWh/año
    charge_from_solar_ratio: float = 0.50  # 50% de carga desde solar
    max_cycles_per_year: int = 500
    solar_curtailment_avoided_kwh: float = 500_000
    
    # Tracking
    name: str = "BESS (940 kWh)"
    capacity_kwh: float = 940.0
    roundtrip_efficiency: float = 0.92


@dataclass(frozen=True)
class MallObjective:
    """Objetivos para demanda del mall"""
    normal_hours_supply_100: float = 1.0  # 100% en horas normales
    peak_hours_cutoff_to_zero: float = 0.0  # CORTAR completamente >2000kW
    solar_penetration_normal: float = 0.40  # 40% desde solar
    bess_penetration_normal: float = 0.20  # 20% desde BESS
    grid_import_ratio_max: float = 0.80
    
    # Tracking
    name: str = "MALL (demanda)"
    peak_hour_start: int = 18
    peak_hour_end: int = 22
    peak_demand_cutoff_kw: float = 2000.0


@dataclass(frozen=True)
class CO2Objective:
    """Objetivo global: reducción de CO2"""
    grid_import_ratio_max: float = 0.30  # <30% import grid
    annual_co2_kg_max: float = 350_000  # <350k kg/año
    solar_utilization_ratio: float = 0.90  # >90% solar utilizado
    ev_co2_displacement_kg: float = 2_000_000  # EV desplaza generation térmica
    
    # Baseline
    baseline_grid_import_ratio: float = 0.70  # 70% sin control
    baseline_annual_co2_kg: float = 640_000  # 640k kg/año sin solar
    baseline_solar_utilization_ratio: float = 0.40
    
    # Tracking
    name: str = "CO2 (Reducción)"
    grid_co2_factor_kg_per_kwh: float = 0.4521  # Iquitos thermal grid


@dataclass
class TrainingObjectives:
    """Contenedor de todos los objetivos"""
    motos: MotosObjective = field(default_factory=MotosObjective)
    mototaxis: MototaxisObjective = field(default_factory=MototaxisObjective)
    bess: BESSObjective = field(default_factory=BESSObjective)
    mall: MallObjective = field(default_factory=MallObjective)
    co2: CO2Objective = field(default_factory=CO2Objective)
    
    def get_all_objectives(self) -> List[Tuple[str, Dict]]:
        """Retorna lista de todos objetivos para tracking"""
        return [
            ("MOTOS", self.motos.__dict__),
            ("MOTOTAXIS", self.mototaxis.__dict__),
            ("BESS", self.bess.__dict__),
            ("MALL", self.mall.__dict__),
            ("CO2", self.co2.__dict__),
        ]
    
    def print_summary(self):
        """Imprime resumen de objetivos"""
        print("\n" + "="*80)
        print("OBJETIVOS DE ENTRENAMIENTO SAC")
        print("="*80)
        
        print(f"\n{self.motos.name}:")
        print(f"  • Cargar {self.motos.charged_100_per_day}/día a 100% ({self.motos.charged_100_per_year:,.0f}/año)")
        print(f"  • Mantener SOC promedio >{self.motos.avg_soc_target*100:.0f}%")
        print(f"  • Resolver {self.motos.urgent_resolution_rate*100:.0f}% urgencias")
        
        print(f"\n{self.mototaxis.name}:")
        print(f"  • Cargar {self.mototaxis.charged_100_per_day}/día a 100% ({self.mototaxis.charged_100_per_year:,.0f}/año)")
        print(f"  • Mantener SOC promedio >{self.mototaxis.avg_soc_target*100:.0f}%")
        print(f"  • Resolver {self.mototaxis.urgent_resolution_rate*100:.0f}% urgencias")
        
        print(f"\n{self.bess.name}:")
        print(f"  • Mantener SOC >{self.bess.peak_min_soc*100:.0f}% en picos (18:00-22:00)")
        print(f"  • Descargar >{self.bess.discharge_target_kwh/1e6:.1f} GWh/año")
        print(f"  • {self.bess.charge_from_solar_ratio*100:.0f}% de carga desde solar")
        
        print(f"\n{self.mall.name}:")
        print(f"  • {self.mall.normal_hours_supply_100*100:.0f}% suministro horas normales")
        print(f"  • CORTE a {self.mall.peak_hours_cutoff_to_zero*100:.0f}% en picos (>2000kW)")
        print(f"  • {self.mall.solar_penetration_normal*100:.0f}% solar + {self.mall.bess_penetration_normal*100:.0f}% BESS")
        
        print(f"\n{self.co2.name}:")
        print(f"  • <{self.co2.annual_co2_kg_max/1000:.0f}k kg CO2/año (-46% vs {self.co2.baseline_annual_co2_kg/1000:.0f}k baseline)")
        print(f"  • <{self.co2.grid_import_ratio_max*100:.0f}% import grid (vs {self.co2.baseline_grid_import_ratio*100:.0f}% baseline)")
        print(f"  • >{self.co2.solar_utilization_ratio*100:.0f}% solar utilizado")
        print("\n" + "="*80)


# Instancia global de objetivos
objectives = TrainingObjectives()


class ObjectiveTracker:
    """Rastrear cumplimiento de objetivos durante entrenamiento"""
    
    def __init__(self, objectives: TrainingObjectives):
        self.objectives = objectives
        self.episode_stats: Dict[str, List[float]] = {
            'motos_charged_100': [],
            'mototaxis_charged_100': [],
            'motos_avg_soc': [],
            'mototaxis_avg_soc': [],
            'bess_peak_soc': [],
            'bess_discharged_kwh': [],
            'mall_supply_normal': [],
            'mall_supply_peak': [],
            'grid_import_ratio': [],
            'annual_co2_kg': [],
            'episode_reward': [],
        }
    
    def log_episode_result(self, episode_num: int, stats: Dict) -> Dict[str, float]:
        """Registrar resultado de episodio y calcular puntuación de objetivos"""
        
        # Lógica de cumplimiento de objetivos
        fulfillment = {}
        
        # MOTOS
        motos_charged = stats.get('motos_charged_100', 0)
        motos_pct = min(1.0, motos_charged / self.objectives.motos.charged_100_per_day)
        fulfillment['motos_fulfillment'] = motos_pct
        self.episode_stats['motos_charged_100'].append(motos_charged)
        
        # MOTOTAXIS
        mototaxis_charged = stats.get('mototaxis_charged_100', 0)
        mototaxis_pct = min(1.0, mototaxis_charged / self.objectives.mototaxis.charged_100_per_day)
        fulfillment['mototaxis_fulfillment'] = mototaxis_pct
        self.episode_stats['mototaxis_charged_100'].append(mototaxis_charged)
        
        # BESS
        bess_soc_picos = stats.get('bess_peak_soc', 0.30)
        bess_soc_pct = min(1.0, bess_soc_picos / self.objectives.bess.peak_min_soc) if self.objectives.bess.peak_min_soc > 0 else 1.0
        fulfillment['bess_fulfillment'] = bess_soc_pct
        self.episode_stats['bess_peak_soc'].append(bess_soc_picos)
        
        # MALL
        mall_cutoff = stats.get('mall_peak_cutoff_success', 0.0)
        fulfillment['mall_fulfillment'] = mall_cutoff
        
        # CO2
        co2_kg = stats.get('annual_co2_kg', self.objectives.co2.baseline_annual_co2_kg)
        co2_pct = max(0.0, 1.0 - (co2_kg / self.objectives.co2.annual_co2_kg_max))
        fulfillment['co2_fulfillment'] = co2_pct
        self.episode_stats['annual_co2_kg'].append(co2_kg)
        
        # Reward total
        episode_reward = stats.get('episode_reward', 0)
        self.episode_stats['episode_reward'].append(episode_reward)
        
        return fulfillment
    
    def get_current_progress(self) -> Dict[str, float]:
        """Obtener progreso actual como promedio de últimos 10 episodios"""
        if not self.episode_stats['episode_reward']:
            return {}
        
        n = min(10, len(self.episode_stats['motos_charged_100']))
        progress = {
            'motos_avg_last_10': np.mean(self.episode_stats['motos_charged_100'][-n:]),
            'mototaxis_avg_last_10': np.mean(self.episode_stats['mototaxis_charged_100'][-n:]),
            'bess_soc_avg_last_10': np.mean(self.episode_stats['bess_peak_soc'][-n:]),
            'co2_kg_avg_last_10': np.mean(self.episode_stats['annual_co2_kg'][-n:]),
            'reward_avg_last_10': np.mean(self.episode_stats['episode_reward'][-n:]),
        }
        return progress


if __name__ == "__main__":
    objectives = TrainingObjectives()
    objectives.print_summary()
    
    print("\nDisponibles para importar:")
    print("  from training_objectives import TrainingObjectives, ObjectiveTracker")
    print("  from training_objectives import objectives  # Instancia global")
