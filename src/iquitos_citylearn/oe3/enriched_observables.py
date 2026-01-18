"""
Observables enriquecidos para OE3 con control operativo avanzado.

Añade:
- Flags de hora pico (18-21h) y hora valle
- SOC actual y SOC reserva (target dinámico)
- Colas/sesiones pendientes por playa
- Potencia disponible FV
- Limitaciones operacionales por playa
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class OperationalConstraints:
    """Límites operacionales por playa (sin cambiar capacidad)."""
    
    peak_hours: List[int]                          # [18, 19, 20, 21]
    valley_hours: List[int]                        # [9, 10, 11, 12]
    power_limits_kw: Dict[str, float]              # playa_motos, playa_mototaxis, total_aggregate
    
    bess_soc_target: Dict[str, float]              # normal_hours, pre_peak_hours, during_peak_hours
    peak_cost_multiplier: float                    # 1.5
    import_penalty_weight: float                   # 0.30
    fairness_penalty_weight: float                 # 0.15
    soc_reserve_penalty: float                     # 0.20
    
    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> OperationalConstraints:
        """Crea desde config de default.yaml."""
        op_ctrl = cfg.get("oe2", {}).get("operational_control", {})
        return cls(
            peak_hours=op_ctrl.get("peak_hours", [18, 19, 20, 21]),
            valley_hours=op_ctrl.get("valley_hours", [9, 10, 11, 12]),
            power_limits_kw=op_ctrl.get("power_limits_kw", {
                "playa_motos": 120.0,
                "playa_mototaxis": 48.0,
                "total_aggregate": 150.0,
            }),
            bess_soc_target=op_ctrl.get("bess_soc_target", {
                "normal_hours": 0.60,
                "pre_peak_hours": 0.85,
                "during_peak_hours": 0.40,
            }),
            peak_cost_multiplier=op_ctrl.get("peak_cost_multiplier", 1.5),
            import_penalty_weight=op_ctrl.get("import_penalty_weight", 0.30),
            fairness_penalty_weight=op_ctrl.get("fairness_penalty_weight", 0.15),
            soc_reserve_penalty=op_ctrl.get("soc_reserve_penalty", 0.20),
        )


class EnrichedObservableWrapper:
    """
    Wrapper que enriquece los observables de CityLearn con:
    - Flags de hora pico/valle
    - SOC target dinámico y nivel de reserva
    - Potencia disponible FV
    - Colas/sesiones pendientes
    """
    
    def __init__(
        self,
        env: Any,
        constraints: OperationalConstraints,
        n_playas: int = 2,
    ):
        """
        Args:
            env: CityLearnEnv
            constraints: OperationalConstraints
            n_playas: Número de playas (típicamente 2: motos y mototaxis)
        """
        self.env = env
        self.constraints = constraints
        self.n_playas = n_playas
        
        # Metadatos
        self.hour_of_year = 0  # 0-8759
        self.hour_of_day = 0   # 0-23
        
        # Estado interno (colas, sesiones)
        self._pending_sessions = [0.0] * n_playas  # por playa
        self._pv_available_kw = 0.0
        
    def reset(self):
        """Reset de estado interno."""
        self._pending_sessions = [0.0] * self.n_playas
        self._pv_available_kw = 0.0
        self.hour_of_year = 0
        self.hour_of_day = 0
        
    def step(self, hour_of_year: int = None):
        """Actualiza hora actual."""
        if hour_of_year is not None:
            self.hour_of_year = hour_of_year
            self.hour_of_day = hour_of_year % 24
        
    def get_enriched_state(
        self,
        base_observation: Dict[str, Any],
        bess_soc: float,  # 0-1
        pv_power_kw: float,
        grid_import_kw: float,
        ev_power_motos_kw: float,
        ev_power_mototaxis_kw: float,
    ) -> Dict[str, Any]:
        """
        Enriquece el estado base con observables operacionales.
        
        Returns:
            Dict con claves:
            - base_obs: observables originales
            - is_peak_hour: 1 si es hora pico, 0 c.c.
            - is_valley_hour: 1 si es hora valle, 0 c.c.
            - hour_of_day: hora del día (0-23)
            - bess_soc_current: SOC actual [0-1]
            - bess_soc_target: SOC objetivo dinámico [0-1]
            - bess_soc_reserve_deficit: max(0, soc_target - soc_actual)
            - pv_power_available_kw: potencia FV disponible [kW]
            - pv_power_ratio: pv_power / ev_power_total (ratio de cobertura)
            - grid_import_kw: importación actual [kW]
            - ev_power_total_kw: suma playas [kW]
            - ev_power_motos_kw: potencia motos [kW]
            - ev_power_mototaxis_kw: potencia mototaxis [kW]
            - ev_power_fairness: ratio máximo/mínimo entre playas
            - pending_sessions_motos: sesiones pendientes (playa motos)
            - pending_sessions_mototaxis: sesiones pendientes (playa mototaxis)
        """
        
        # Flags de hora
        is_peak = 1 if self.hour_of_day in self.constraints.peak_hours else 0
        is_valley = 1 if self.hour_of_day in self.constraints.valley_hours else 0
        
        # SOC target dinámico
        if is_peak:
            soc_target = self.constraints.bess_soc_target["during_peak_hours"]
        elif self.hour_of_day in [16, 17]:  # Pre-pico
            soc_target = self.constraints.bess_soc_target["pre_peak_hours"]
        else:
            soc_target = self.constraints.bess_soc_target["normal_hours"]
        
        # Déficit de reserva (penalizar si bess_soc < soc_target)
        soc_reserve_deficit = max(0.0, soc_target - bess_soc)
        
        # Ratio FV: cobertura solar
        ev_power_total = ev_power_motos_kw + ev_power_mototaxis_kw
        pv_power_ratio = pv_power_kw / max(ev_power_total, 0.1)  # Evitar división por cero
        
        # Fairness entre playas
        ev_powers = [ev_power_motos_kw, ev_power_mototaxis_kw]
        max_ev = max(ev_powers) if any(p > 0 for p in ev_powers) else 1.0
        min_ev = min(p for p in ev_powers if p > 0) if any(p > 0 for p in ev_powers) else 1.0
        fairness_ratio = max_ev / max(min_ev, 1.0)
        
        return {
            "is_peak_hour": is_peak,
            "is_valley_hour": is_valley,
            "hour_of_day": float(self.hour_of_day),
            "bess_soc_current": float(bess_soc),
            "bess_soc_target": float(soc_target),
            "bess_soc_reserve_deficit": float(soc_reserve_deficit),
            "pv_power_available_kw": float(pv_power_kw),
            "pv_power_ratio": float(pv_power_ratio),
            "grid_import_kw": float(grid_import_kw),
            "ev_power_total_kw": float(ev_power_total),
            "ev_power_motos_kw": float(ev_power_motos_kw),
            "ev_power_mototaxis_kw": float(ev_power_mototaxis_kw),
            "ev_power_fairness_ratio": float(fairness_ratio),
            "pending_sessions_motos": self._pending_sessions[0],
            "pending_sessions_mototaxis": self._pending_sessions[1],
        }
    
    
def compute_operational_penalties(
    state: Dict[str, Any],
    constraints: OperationalConstraints,
) -> Dict[str, float]:
    """
    Calcula penalizaciones para recompensa por incumplimiento de restricciones operacionales.
    
    Returns dict con:
    - soc_reserve_penalty: penalidad por incumplimiento de SOC target
    - peak_power_penalty: penalidad si potencia > límite en pico
    - fairness_penalty: penalidad por desequilibrio entre playas
    - import_peak_penalty: penalidad si importación en pico
    """
    
    penalties = {}
    
    # 1. Penalidad por reserva SOC incumplida
    soc_deficit = state.get("bess_soc_reserve_deficit", 0.0)
    penalties["soc_reserve"] = soc_deficit * constraints.soc_reserve_penalty
    
    # 2. Penalidad por potencia agregada > límite en pico
    is_peak = state.get("is_peak_hour", 0)
    ev_power_total = state.get("ev_power_total_kw", 0.0)
    power_limit = constraints.power_limits_kw.get("total_aggregate", 150.0)
    
    if is_peak and ev_power_total > power_limit:
        overage = ev_power_total - power_limit
        penalties["peak_power"] = (overage / power_limit) * 0.2
    else:
        penalties["peak_power"] = 0.0
    
    # 3. Penalidad por desequilibrio fairness
    fairness_ratio = state.get("ev_power_fairness_ratio", 1.0)
    if fairness_ratio > 1.5:  # Desequilibrio significativo
        penalties["fairness"] = ((fairness_ratio - 1.0) / 2.0) * constraints.fairness_penalty_weight
    else:
        penalties["fairness"] = 0.0
    
    # 4. Penalidad por importación en pico
    if is_peak:
        grid_import = state.get("grid_import_kw", 0.0)
        if grid_import > 50.0:  # Umbral de importación "alta"
            penalties["import_peak"] = (grid_import / 150.0) * constraints.import_penalty_weight
        else:
            penalties["import_peak"] = 0.0
    else:
        penalties["import_peak"] = 0.0
    
    penalties["total"] = sum(penalties.values())
    
    return penalties
