"""
Módulo de Cálculo de Emisiones de CO2: Directas e Indirectas.

Define metodología para que agentes RL minimicen:
- Emisiones Directas (Scope 2): Importación desde red (0.4521 kg CO2/kWh)
- Emisiones Indirectas (Scope 1): Uso eficiente de BESS (conversión, degradación)

Sin cambiar BESS capacity: 2000 kWh fijo, solo optimizar operación.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class CO2EmissionFactors:
    """Factores de emisión para diferentes fuentes de energía."""
    
    # Emisiones Directas (Scope 2)
    grid_import_kg_per_kwh: float = 0.4521  # Matriz Iquitos (térmica)
    diesel_kg_per_kwh: float = 0.2667       # Si hay backup diesel
    
    # Emisiones Indirectas (Scope 1)
    bess_charging_efficiency: float = 0.95   # 5% pérdidas en carga
    bess_discharging_efficiency: float = 0.95 # 5% pérdidas en descarga
    bess_standby_loss_kg_per_kwh_day: float = 0.001  # Autodescarga diaria
    
    # Emisiones por degradación de BESS
    bess_cycling_co2_per_cycle: float = 0.05  # kg CO2 por ciclo completo
    bess_calendar_aging_kg_per_day: float = 0.01  # Degradación por tiempo
    
    # Solar (cero emisiones operacionales)
    solar_operational_kg_per_kwh: float = 0.0
    solar_embodied_kg_per_kwh: float = 0.041  # Fabricación (amortizado)


@dataclass(frozen=True)
class CO2EmissionBreakdown:
    """Desglose de emisiones en un timestep."""
    
    # Emisiones Directas (Scope 2)
    grid_import_kg: float = 0.0       # Importación desde red
    diesel_backup_kg: float = 0.0     # Si hay generación diesel
    
    # Emisiones Indirectas (Scope 1)
    bess_charging_loss_kg: float = 0.0     # Pérdidas carga
    bess_discharging_loss_kg: float = 0.0  # Pérdidas descarga
    bess_standby_loss_kg: float = 0.0      # Autodescarga
    bess_cycling_degradation_kg: float = 0.0  # Degradación por ciclos
    bess_calendar_aging_kg: float = 0.0    # Envejecimiento
    
    # Beneficios (negativos = reducción)
    solar_utilization_avoided_kg: float = 0.0  # CO2 evitado por usar solar
    
    @property
    def total_direct_kg(self) -> float:
        """Total emisiones Scope 2 (grid + diesel)."""
        return self.grid_import_kg + self.diesel_backup_kg
    
    @property
    def total_indirect_kg(self) -> float:
        """Total emisiones Scope 1 (BESS + degradación)."""
        return (
            self.bess_charging_loss_kg +
            self.bess_discharging_loss_kg +
            self.bess_standby_loss_kg +
            self.bess_cycling_degradation_kg +
            self.bess_calendar_aging_kg
        )
    
    @property
    def total_kg(self) -> float:
        """Total emisiones (directas + indirectas - beneficios)."""
        return (
            self.total_direct_kg +
            self.total_indirect_kg -
            self.solar_utilization_avoided_kg
        )


class CO2EmissionCalculator:
    """
    Calcula emisiones directas e indirectas en operación de sistema.
    
    Metodología:
    
    1. EMISIONES DIRECTAS (Scope 2)
       - Importación grid: grid_import_kw × factor_grid
       - Generación diesel: diesel_kw × factor_diesel
    
    2. EMISIONES INDIRECTAS (Scope 1)
       a) Pérdidas de conversión BESS:
          - Carga: pv_to_bess_kw × (1 - eff_charge)
          - Descarga: bess_to_load_kw × (1 - eff_discharge)
       
       b) Autodescarga BESS:
          - bess_soc_kwh × standby_loss_rate
       
       c) Degradación por ciclado:
          - num_cycles × co2_per_cycle
       
       d) Envejecimiento calendario:
          - age_days × co2_per_day
    
    3. BENEFICIOS (Reducción de CO2)
       - Solar utilizado: pv_to_ev_kw × factor_grid
       - Descripción: Evita importación que tendría ese factor
    
    Restricción: BESS capacity fijo 2000 kWh, solo optimizar control
    """
    
    def __init__(self, factors: Optional[CO2EmissionFactors] = None):
        """
        Args:
            factors: Factores de emisión (usa defaults si None)
        """
        self.factors = factors or CO2EmissionFactors()
        self.cycle_counter = 0.0  # Tracking de ciclos BESS
        self.bess_age_days = 0
    
    def calculate_timestep_emissions(
        self,
        pv_power_kw: float,
        pv_to_ev_kw: float,
        pv_to_bess_kw: float,
        pv_to_mall_kw: float,
        bess_to_ev_kw: float,
        bess_to_mall_kw: float,
        grid_import_ev_kw: float,
        grid_import_mall_kw: float,
        bess_soc_kwh: float,
        bess_soc_previous_kwh: float,
        bess_capacity_kwh: float = 2000.0,
        diesel_kw: float = 0.0,
    ) -> CO2EmissionBreakdown:
        """
        Calcula emisiones para un timestep de 1 hora.
        
        Args:
            pv_power_kw: Potencia solar generada
            pv_to_ev_kw: Solar enviada a EVs
            pv_to_bess_kw: Solar enviada a BESS
            pv_to_mall_kw: Solar enviada a mall
            bess_to_ev_kw: BESS descargada a EVs
            bess_to_mall_kw: BESS descargada a mall
            grid_import_ev_kw: Grid importada para EVs
            grid_import_mall_kw: Grid importada para mall
            bess_soc_kwh: SOC actual BESS
            bess_soc_previous_kwh: SOC anterior BESS
            bess_capacity_kwh: Capacidad BESS (default 2000)
            diesel_kw: Potencia diesel (si aplica)
        
        Returns:
            CO2EmissionBreakdown con desglose completo
        """
        
        emissions = CO2EmissionBreakdown()
        
        # ============ EMISIONES DIRECTAS (Scope 2) ============
        
        # Importación grid
        total_grid_import = grid_import_ev_kw + grid_import_mall_kw
        grid_import_kg = total_grid_import * self.factors.grid_import_kg_per_kwh
        
        # Diesel (si aplica)
        diesel_kg = diesel_kw * self.factors.diesel_kg_per_kwh
        
        # Pérdidas por carga BESS
        bess_charging_loss = pv_to_bess_kw * (1 - self.factors.bess_charging_efficiency)
        bess_charging_loss_kg = bess_charging_loss * self.factors.grid_import_kg_per_kwh
        
        # Pérdidas por descarga BESS
        total_bess_discharge = bess_to_ev_kw + bess_to_mall_kw
        bess_discharging_loss = total_bess_discharge * (1 - self.factors.bess_discharging_efficiency)
        bess_discharging_loss_kg = bess_discharging_loss * self.factors.grid_import_kg_per_kwh
        
        # Autodescarga (standby loss) BESS
        standby_loss = bess_soc_kwh * self.factors.bess_standby_loss_kg_per_kwh_day / 24
        bess_standby_loss_kg = standby_loss * self.factors.grid_import_kg_per_kwh
        
        # Degradación por ciclado
        soc_change = abs(bess_soc_kwh - bess_soc_previous_kwh) / bess_capacity_kwh
        cycles_this_timestep = soc_change / 2.0
        bess_cycling_degradation_kg = cycles_this_timestep * self.factors.bess_cycling_co2_per_cycle
        self.cycle_counter += cycles_this_timestep
        
        # Envejecimiento calendario
        bess_calendar_aging_kg = self.factors.bess_calendar_aging_kg_per_day / 24
        self.bess_age_days += 1/24
        
        # Solar utilizado evita importación
        total_solar_used = pv_to_ev_kw + pv_to_mall_kw
        solar_utilization_avoided_kg = total_solar_used * self.factors.grid_import_kg_per_kwh
        
        # Crear instancia con todos los valores calculados
        emissions = CO2EmissionBreakdown(
            grid_import_kg=grid_import_kg,
            diesel_backup_kg=diesel_kg,
            bess_charging_loss_kg=bess_charging_loss_kg,
            bess_discharging_loss_kg=bess_discharging_loss_kg,
            bess_standby_loss_kg=bess_standby_loss_kg,
            bess_cycling_degradation_kg=bess_cycling_degradation_kg,
            bess_calendar_aging_kg=bess_calendar_aging_kg,
            solar_utilization_avoided_kg=solar_utilization_avoided_kg,
        )
        
        return emissions
    
    def calculate_annual_emissions(
        self,
        daily_metrics: list[Dict[str, float]],  # 365 days of metrics
    ) -> Dict[str, float]:
        """
        Calcula emisiones anuales agregadas.
        
        Args:
            daily_metrics: Lista de métricas diarias (8760 timesteps/día)
        
        Returns:
            Dict con totales anuales
        """
        
        total_direct = 0.0
        total_indirect = 0.0
        total_avoided = 0.0
        
        for metric in daily_metrics:
            emissions = self.calculate_timestep_emissions(
                pv_power_kw=metric.get("pv_power_kw", 0),
                pv_to_ev_kw=metric.get("pv_to_ev_kw", 0),
                pv_to_bess_kw=metric.get("pv_to_bess_kw", 0),
                pv_to_mall_kw=metric.get("pv_to_mall_kw", 0),
                bess_to_ev_kw=metric.get("bess_to_ev_kw", 0),
                bess_to_mall_kw=metric.get("bess_to_mall_kw", 0),
                grid_import_ev_kw=metric.get("grid_import_ev_kw", 0),
                grid_import_mall_kw=metric.get("grid_import_mall_kw", 0),
                bess_soc_kwh=metric.get("bess_soc_kwh", 1000),
                bess_soc_previous_kwh=metric.get("bess_soc_previous_kwh", 1000),
                diesel_kw=metric.get("diesel_kw", 0),
            )
            
            total_direct += emissions.total_direct_kg
            total_indirect += emissions.total_indirect_kg
            total_avoided += emissions.solar_utilization_avoided_kg
        
        return {
            "annual_direct_kg": total_direct,
            "annual_indirect_kg": total_indirect,
            "annual_avoided_kg": total_avoided,
            "annual_net_kg": total_direct + total_indirect - total_avoided,
            "annual_cycles": self.cycle_counter,
            "avg_daily_direct_kg": total_direct / 365,
            "avg_daily_indirect_kg": total_indirect / 365,
        }


def create_co2_reward_component(
    emissions: CO2EmissionBreakdown,
    carbon_budget_annual_kg: Optional[float] = None,
    direct_weight: float = 0.6,
    indirect_weight: float = 0.4,
) -> float:
    """
    Convierte emisiones a componente de recompensa para RL.
    
    Estrategia:
    - Penalizar emisiones directas (grid import, diesel) con peso 0.6
    - Penalizar emisiones indirectas (BESS ineficiencia) con peso 0.4
    - Recompensar uso solar (negativo = beneficio)
    
    Args:
        emissions: Desglose de emisiones
        carbon_budget_annual_kg: Presupuesto CO2 anual (para normalizar)
        direct_weight: Peso relativo emisiones directas
        indirect_weight: Peso relativo emisiones indirectas
    
    Returns:
        Reward component (negativo = penalidad por CO2)
    """
    
    # Penalidad normalizada (variable usado dentro del retorno)
    # total_emissions = emissions.total_kg (ya se usa indirectamente en direct_penalty y indirect_penalty)
    
    # Convertir a penalidad (-1.0 a 0.0 range)
    # Asumir presupuesto annual de 7M kg CO2 → 8.2 kg/timestep promedio
    budget_per_timestep = (carbon_budget_annual_kg or 8.2e6) / 8760
    
    # Componentes ponderadas
    direct_penalty = -(emissions.total_direct_kg / budget_per_timestep) * direct_weight
    indirect_penalty = -(emissions.total_indirect_kg / budget_per_timestep) * indirect_weight
    solar_bonus = (emissions.solar_utilization_avoided_kg / budget_per_timestep) * 0.1
    
    return direct_penalty + indirect_penalty + solar_bonus


def get_co2_reduction_strategies() -> Dict[str, Dict[str, Any]]:
    """
    Define estrategias de reducción CO2 para agentes.
    
    Retorna configuración de múltiples estrategias:
    1. Maximizar solar directo (P1 despacho)
    2. Minimizar grid import
    3. Optimizar ciclos BESS
    4. Minimizar degradación BESS
    5. Balance multi-objetivo
    """
    
    return {
        "direct_reduction": {
            "description": "Maximizar uso directo de FV para EVs",
            "objective": "Maximizar pv_to_ev_kw",
            "constraints": ["ev_power_limit_kw <= 150", "pv_available > 0"],
            "co2_avoided_per_kwh": 0.4521,  # Grid factor
            "priority": 1,
        },
        "indirect_reduction": {
            "description": "Minimizar ineficiencias BESS",
            "objective": "Minimizar ciclos innecesarios + degradación",
            "constraints": [
                "bess_cycles_min <= cycles <= bess_cycles_max",
                "20% <= soc <= 95%",
            ],
            "co2_per_cycle": 0.05,
            "co2_per_day": 0.01,
            "priority": 2,
        },
        "import_reduction": {
            "description": "Minimizar importación desde grid",
            "objective": "Reducir grid_import_kw en horas pico",
            "constraints": ["peak_hours: 18-21"],
            "co2_per_kwh": 0.4521,
            "penalty_multiplier_peak": 2.0,
            "priority": 1,
        },
        "bess_optimization": {
            "description": "Optimizar carga/descarga BESS",
            "objective": "Pre-carga en valle, descarga en pico",
            "constraints": [
                "pre_charge_hours: 9-17",
                "discharge_hours: 18-22",
            ],
            "co2_avoided_per_kwh_pico": 0.9042,  # 2x factor
            "priority": 2,
        },
        "multi_objective_balance": {
            "description": "Balance entre todas estrategias",
            "weights": {
                "direct_solar": 0.50,
                "grid_import_reduction": 0.30,
                "bess_efficiency": 0.15,
                "cost_reduction": 0.05,
            },
            "priority": 3,
        },
    }
