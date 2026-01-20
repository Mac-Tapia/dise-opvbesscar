"""Recompensa dinámica con gradientes fuertes para PPO/A2C/SAC.

Características:
- Varía con hora pico (18-21h: penalización 4x más fuerte)
- Penaliza importación en pico, bonus en off-peak
- Bonus por SOC/reserva para pico
- Penaliza exceso de potencia
- Gradientes claros para Q-learning
"""
from __future__ import annotations
from typing import Tuple, Dict, Any, Optional
import numpy as np


class DynamicReward:
    """Recompensa dinámica con variación horaria y de carga."""
    
    def __init__(
        self,
        weight_co2: float = 0.50,
        weight_cost: float = 0.15,
        weight_solar: float = 0.20,
        weight_ev: float = 0.10,
        weight_grid: float = 0.05,
    ):
        """
        Args:
            weight_co2: Peso minimizar importación/CO2
            weight_cost: Peso minimizar costo
            weight_solar: Peso maximizar autoconsumo solar
            weight_ev: Peso satisfacción EV
            weight_grid: Peso estabilidad de red (picos)
        """
        self.w_co2 = weight_co2
        self.w_cost = weight_cost
        self.w_solar = weight_solar
        self.w_ev = weight_ev
        self.w_grid = weight_grid
        
        # Iquitos context
        self.peak_hours = [18, 19, 20, 21]  # 6pm-10pm (hora pico)
        self.off_peak_hours = list(range(0, 17)) + [22, 23]  # Resto
        self.pre_peak_hours = [16, 17]  # Preparación para pico
        
        # Baselines reales Iquitos (validados con datos históricos)
        self.import_baseline_offpeak = 130.0  # kWh/hora típico fuera pico
        self.import_baseline_peak = 250.0     # kWh/hora target en pico (CON BESS)
        self.import_baseline_prepeak = 150.0  # kWh/hora en preparación
        
        self.soc_target_prepeak = 0.70  # 70% SOC antes de pico
        self.soc_target_peak = 0.40    # 40% SOC durante pico (inyectar)
        
        self.power_limit_peak = 200.0   # kW máximo en pico
        self.power_limit_offpeak = 150.0  # kW máximo fuera pico
        
        # Co2 y tarifas
        self.co2_factor = 0.4521  # kg CO2/kWh (Perú)
        self.tariff_usd_per_kwh = 0.1500  # Tarifa eléctrica promedio
        
    def _hour_type(self, hour: int) -> str:
        """Clasifica hora del día."""
        if hour in self.peak_hours:
            return "peak"
        elif hour in self.pre_peak_hours:
            return "prepeak"
        else:
            return "offpeak"
    
    def _r_import(self, grid_import_kwh: float, hour: int) -> float:
        """Recompensa por importación (penaliza import alto).
        
        Returns [-1, 1]:
        - En pico: -1 si import=250 (baseline), +1 si import=0
        - En off-peak: -0.5 si import=130, +1 si import=0
        """
        hour_type = self._hour_type(hour)
        
        if hour_type == "peak":
            # En pico: penalización 4x más fuerte
            # r = 1 - 4*(import/baseline) clipped [-1, 1]
            baseline = self.import_baseline_peak  # 250 kWh
            ratio = min(1.0, grid_import_kwh / baseline)
            r = 1.0 - 4.0 * ratio
            r = np.clip(r, -1.0, 1.0)
        
        elif hour_type == "prepeak":
            # Pre-pico: penalización moderada para preparación
            baseline = self.import_baseline_prepeak
            ratio = min(1.0, grid_import_kwh / baseline)
            r = 1.0 - 2.0 * ratio
            r = np.clip(r, -1.0, 1.0)
        
        else:  # offpeak
            # Off-peak: menos penalización, pero aún hay gradiente
            baseline = self.import_baseline_offpeak
            ratio = min(1.0, grid_import_kwh / baseline)
            r = 1.0 - 1.5 * ratio
            r = np.clip(r, -1.0, 1.0)
        
        return float(r)
    
    def _r_power(self, power_kw: float, hour: int) -> float:
        """Recompensa por potencia pico (penaliza exceso de potencia).
        
        Returns [-1, 1]:
        - Si power > limit: penalización progresiva
        - Si power <= limit: bonus
        """
        hour_type = self._hour_type(hour)
        
        if hour_type == "peak":
            limit = self.power_limit_peak  # 200 kW
        else:
            limit = self.power_limit_offpeak  # 150 kW
        
        if power_kw <= limit:
            # Dentro de límite: bonus [0, 1]
            r = power_kw / limit
        else:
            # Exceso: penalización [-1, 0]
            excess_ratio = (power_kw - limit) / limit
            r = -excess_ratio
            r = np.clip(r, -1.0, 0.0)
        
        return float(r)
    
    def _r_soc(self, bess_soc: float, hour: int) -> float:
        """Recompensa por SOC/reserva (bonus si SOC alineado con hora).
        
        Returns [-1, 1]:
        - Pre-pico: bonus si SOC >= target (70%), penaliza si < target
        - Pico: bonus si SOC >= 40% (para inyectar)
        - Off-peak: neutral
        """
        hour_type = self._hour_type(hour)
        
        if hour_type == "prepeak":
            # Pre-pico: target 70%
            target = self.soc_target_prepeak
            if bess_soc >= target:
                # Bonus: [0, 1]
                r = 0.5 + 0.5 * (bess_soc - target) / (1.0 - target)
            else:
                # Penalización: [-1, 0]
                deficit = target - bess_soc
                r = -deficit / target  # [-1, 0]
            r = np.clip(r, -1.0, 1.0)
        
        elif hour_type == "peak":
            # Pico: target 40% (inyectar)
            target = self.soc_target_peak
            if bess_soc >= target:
                # Bonus por tener reserva: [0, 1]
                r = 0.5 + 0.5 * (bess_soc - target) / (1.0 - target)
            else:
                # Penalización leve si no hay reserva
                deficit = target - bess_soc
                r = -0.5 * (deficit / target)
            r = np.clip(r, -1.0, 1.0)
        
        else:  # offpeak
            # Off-peak: neutral (no penalidad por SOC)
            r = 0.0
        
        return float(r)
    
    def _r_solar(self, solar_gen_kwh: float, ev_charging_kwh: float, grid_import_kwh: float) -> float:
        """Recompensa por autoconsumo solar (maximiza uso de solar en carga).
        
        Returns [-1, 1]:
        - Bonus si usa solar para cargar
        - Penaliza si importa cuando hay solar
        """
        if solar_gen_kwh < 1.0:
            return 0.0
        
        # Idealmente: ev_charging debe venir de solar
        solar_used = min(solar_gen_kwh, ev_charging_kwh)
        solar_ratio = solar_used / solar_gen_kwh
        
        # Penaliza importación cuando hay solar disponible
        if solar_ratio < 1.0:
            # Hay solar no utilizada
            unused_solar = solar_gen_kwh - solar_used
            # Si importas cuando hay solar: penalización
            import_when_solar = min(grid_import_kwh, unused_solar)
            penalty = import_when_solar / solar_gen_kwh
            r = solar_ratio - penalty
        else:
            r = solar_ratio
        
        r = np.clip(r, -1.0, 1.0)
        return float(r)
    
    def _r_ev(self, ev_soc_avg: float, ev_demand_kwh: float) -> float:
        """Recompensa por satisfacción EV (carga EVs adecuadamente).
        
        Returns [-1, 1]:
        - Bonus si EV SOC alto (>80%)
        - Penaliza si EV SOC bajo cuando hay demanda
        """
        target_soc = 0.85
        
        if ev_demand_kwh < 1.0:
            # Sin demanda: no penalizar
            return 0.0
        
        # Si hay demanda y SOC bajo: penalización
        if ev_soc_avg < 0.5:
            # Insatisfacción: penalización [-1, 0]
            r = -1.0 + (ev_soc_avg / 0.5)  # [-1, 0]
        elif ev_soc_avg >= target_soc:
            # Satisfecho: bonus [0.5, 1]
            r = 0.5 + 0.5 * min(1.0, ev_soc_avg / 1.0)
        else:
            # Parcialmente satisfecho: [0, 0.5]
            r = (ev_soc_avg - 0.5) / (target_soc - 0.5) * 0.5
        
        r = np.clip(r, -1.0, 1.0)
        return float(r)
    
    def _r_cost(self, grid_net_kwh: float) -> float:
        """Recompensa por costo (minimizar importación neta).
        
        Returns [-1, 1]:
        - Penaliza importación neta
        - Bonus por exportación/autosuficiencia
        """
        if grid_net_kwh <= 0:
            # Exportando o autoabastecido: bonus [0, 1]
            return 0.5
        
        # Importando: penalización basada en cantidad
        baseline = 100.0  # kWh/hora baseline
        ratio = min(1.0, grid_net_kwh / baseline)
        r = 1.0 - 2.0 * ratio  # [-1, 1]
        r = np.clip(r, -1.0, 1.0)
        
        return float(r)
    
    def compute(
        self,
        hour: int,
        grid_import_kwh: float,
        grid_export_kwh: float,
        solar_generation_kwh: float,
        ev_charging_kwh: float,
        ev_soc_avg: float,
        bess_soc: float,
        ev_demand_kwh: float = 0.0,
    ) -> Tuple[float, Dict[str, float]]:
        """Compute dynamic reward with clear gradients.
        
        Args:
            hour: Hora del día [0-23]
            grid_import_kwh: Importación neta (kWh)
            grid_export_kwh: Exportación (kWh)
            solar_generation_kwh: Generación solar (kWh)
            ev_charging_kwh: Carga entregada a EVs (kWh)
            ev_soc_avg: SOC promedio de EVs [0-1]
            bess_soc: SOC de BESS [0-1]
            ev_demand_kwh: Demanda solicitada (kWh)
        
        Returns:
            (reward_total, components_dict)
        """
        # Potencia pico
        power_kw = grid_import_kwh  # Aproximación (podría ser paso temporal)
        grid_net_kwh = grid_import_kwh - grid_export_kwh
        
        # Componentes
        r_import = self._r_import(grid_import_kwh, hour)
        r_power = self._r_power(power_kw, hour)
        r_soc = self._r_soc(bess_soc, hour)
        r_solar = self._r_solar(solar_generation_kwh, ev_charging_kwh, grid_import_kwh)
        r_ev = self._r_ev(ev_soc_avg, ev_demand_kwh)
        r_cost = self._r_cost(grid_net_kwh)
        
        # Recompensa total ponderada
        reward = (
            self.w_co2 * r_import +      # Minimizar importación
            self.w_grid * r_power +      # Evitar picos
            0.15 * r_soc +               # SOC alineado
            self.w_solar * r_solar +     # Maximizar solar
            self.w_ev * r_ev +           # Satisfacción EV
            self.w_cost * r_cost         # Minimizar costo
        )
        
        # Normalizar a [-1, 1]
        reward = np.clip(reward, -1.0, 1.0)
        
        components = {
            "reward_total": reward,
            "r_import": r_import,
            "r_power": r_power,
            "r_soc": r_soc,
            "r_solar": r_solar,
            "r_ev": r_ev,
            "r_cost": r_cost,
            "hour": hour,
            "is_peak": float(self._hour_type(hour) == "peak"),
            "grid_import_kwh": grid_import_kwh,
            "solar_generation_kwh": solar_generation_kwh,
            "bess_soc": bess_soc,
            "ev_soc_avg": ev_soc_avg,
        }
        
        return reward, components
