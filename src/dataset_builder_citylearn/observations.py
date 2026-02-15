"""
Modulo canonico de observaciones para CityLearn v2 (SSOT - Single Source of Truth).

Unifica todas las versiones de construccion de observaciones dispersas en multiples scripts.

Versiones soportadas:
  - 156-dim (v5.3 estandar - default)
  - 246-dim (v6.0 cascada, comunicacion avanzada)
  - 66-dim (experimental expandido)
  - 50-dim (legacy simple)

Autor: Unificacion v6.0 - Consolidacion de observaciones
Fecha: 2026-02-14
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import numpy as np
import gymnasium as gym
from gymnasium import spaces


# ================================================================================
# CONSTANTES GLOBALES - OE2 v5.3
# ================================================================================

SOLAR_MAX_KW = 4050.0              # 4,050 kWp solar
MALL_MAX_KW = 100.0                # 100 kW baseline mall
BESS_MAX_KWH = 1700.0              # 1,700 kWh capacity
BESS_MAX_POWER_KW = 400.0          # 400 kW discharge power
CHARGER_MAX_KW = 7.4               # 7.4 kW @ 32A
CHARGER_MEAN_KW = 4.6              # 4.6 kW promedio
NUM_CHARGERS = 38                  # 19 chargers × 2 sockets
MOTOS_SOCKETS = 30                 # 15 motos × 2
TAXIS_SOCKETS = 8                  # 4 taxis × 2
CO2_FACTOR_IQUITOS = 0.4521        # kg CO₂/kWh (grid diesel Iquitos)

HOURS_PER_YEAR = 8760              # 365 × 24


# ================================================================================
# CLASE OBSERVATIONBUILDER - UNIFIED OBSERVATION FACTORY
# ================================================================================

class ObservationBuilder:
    """
    Constructor canonico de observaciones para CityLearn v2.
    
    Unifica todas las construcciones dispersas en un solo modulo reutilizable.
    Soporta multiples versiones & facil agregacion de nuevas versiones.
    
    Ejemplo:
        >>> obs_builder = ObservationBuilder(version="156_standard")
        >>> obs_dim = obs_builder.obs_dim
        >>> observation_space = obs_builder.observation_space
        >>> obs = obs_builder.make_observation(hour_idx=0, data={...})
    """
    
    # Versiones disponibles
    OBS_156_STANDARD = "156_standard"      # v5.3 - Estandar (DEFAULT)
    OBS_246_CASCADA = "246_cascada"        # v6.0 - Con cascada de comunicacion
    OBS_66_EXPANDED = "66_expanded"        # Experimental expandido
    OBS_50_SIMPLE = "50_simple"            # Legacy simple (deprecado)
    
    AVAILABLE_VERSIONS = [OBS_156_STANDARD, OBS_246_CASCADA, OBS_66_EXPANDED, OBS_50_SIMPLE]
    
    def __init__(self, version: str = OBS_156_STANDARD):
        """
        Inicializa builder de observaciones.
        
        Args:
            version: Version de observacion ("156_standard", "246_cascada", etc.)
            
        Raises:
            ValueError: Si version no es soportada
        """
        if version not in self.AVAILABLE_VERSIONS:
            raise ValueError(
                f"Version '{version}' no soportada. "
                f"Disponibles: {self.AVAILABLE_VERSIONS}"
            )
        
        self.version = version
        self.obs_dim = self._get_obs_dim(version)
        self.observation_space = self._get_observation_space(version)
        
        # Estado para rastreo entre pasos
        self._last_state: Dict[str, Any] = {}
    
    def _get_obs_dim(self, version: str) -> int:
        """Retorna dimension de observacion para version."""
        dims = {
            self.OBS_156_STANDARD: 156,
            self.OBS_246_CASCADA: 246,
            self.OBS_66_EXPANDED: 66,
            self.OBS_50_SIMPLE: 50,
        }
        return dims[version]
    
    def _get_observation_space(self, version: str) -> spaces.Box:
        """Retorna gymnasium observation space para version."""
        obs_dim = self._get_obs_dim(version)
        return spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_dim,),
            dtype=np.float32
        )
    
    def make_observation(
        self, 
        hour_idx: int, 
        data: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """
        Construye observacion segun version seleccionada.
        
        Args:
            hour_idx: Indice horario (0-8759)
            data: Diccionario con datos OE2 (solar, chargers, bess, mall, etc.)
            state: Estado opcional para rastreo interno
            
        Returns:
            Observacion normalizada [obs_dim, dtype=float32]
        """
        if self.version == self.OBS_156_STANDARD:
            return self._make_obs_156(hour_idx, data, state)
        elif self.version == self.OBS_246_CASCADA:
            return self._make_obs_246(hour_idx, data, state)
        elif self.version == self.OBS_66_EXPANDED:
            return self._make_obs_66(hour_idx, data, state)
        elif self.version == self.OBS_50_SIMPLE:
            return self._make_obs_50(hour_idx, data, state)
        else:
            raise RuntimeError(f"Version no implementada: {self.version}")
    
    # ============================================================================
    # VERSION 156-DIM (v5.3 ESTANDAR - DEFAULT)
    # ============================================================================
    
    def _make_obs_156(
        self, 
        hour_idx: int, 
        data: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """
        Construccion 156-dim v5.3 estandar.
        
        Estructura:
        [0-7]       = Energia del sistema (8)
        [8-45]      = Demanda por socket (38)
        [46-83]     = Potencia actual por socket (38)
        [84-121]    = Ocupacion por socket (38)
        [122-137]   = Estado de vehiculos (16)
        [138-143]   = Time features (6)
        [144-155]   = Comunicacion inter-sistema (12)
        
        Total: 156 features
        """
        obs = np.zeros(156, dtype=np.float32)
        
        # Extraer datos con validacion
        solar_hourly = data.get("solar_hourly", np.zeros(HOURS_PER_YEAR))
        chargers_hourly = data.get("chargers_hourly", np.zeros((HOURS_PER_YEAR, NUM_CHARGERS)))
        mall_hourly = data.get("mall_hourly", np.zeros(HOURS_PER_YEAR))
        bess_soc_hourly = data.get("bess_soc_hourly", np.ones(HOURS_PER_YEAR) * 50.0)
        
        h = hour_idx % HOURS_PER_YEAR
        hour_24 = h % 24
        day_of_year = (h // 24) % 365
        
        # --- [0-7] ENERGIA DEL SISTEMA ---
        solar_kw = float(solar_hourly[h] if h < len(solar_hourly) else 0.0)
        mall_kw = float(mall_hourly[h] if h < len(mall_hourly) else 0.0)
        bess_soc = float(bess_soc_hourly[h] if h < len(bess_soc_hourly) else 50.0) / 100.0
        
        # Estimador de demanda EV
        if chargers_hourly.shape[1] >= NUM_CHARGERS:
            raw_demands = chargers_hourly[h, :NUM_CHARGERS]
        else:
            raw_demands = np.zeros(NUM_CHARGERS, dtype=np.float32)
            if chargers_hourly.shape[1] > 0:
                raw_demands[:chargers_hourly.shape[1]] = chargers_hourly[h]
        
        ev_demand_estimate = float(np.sum(raw_demands))
        total_demand = mall_kw + ev_demand_estimate
        solar_surplus = max(0.0, solar_kw - total_demand)
        grid_import_needed = max(0.0, total_demand - solar_kw)
        bess_energy_available = bess_soc * BESS_MAX_KWH * 0.90
        
        obs[0] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)
        obs[1] = np.clip(mall_kw / MALL_MAX_KW, 0.0, 1.0)
        obs[2] = np.clip(bess_soc, 0.0, 1.0)
        obs[3] = np.clip(bess_energy_available / BESS_MAX_KWH, 0.0, 1.0)
        obs[4] = np.clip(solar_surplus / SOLAR_MAX_KW, 0.0, 1.0)
        obs[5] = np.clip(grid_import_needed / 500.0, 0.0, 1.0)
        obs[6] = np.clip((solar_kw - total_demand) / SOLAR_MAX_KW + 0.5, 0.0, 1.0)
        obs[7] = np.clip(1.0 - ev_demand_estimate / (NUM_CHARGERS * CHARGER_MAX_KW), 0.0, 1.0)
        
        # --- [8-45] DEMANDA POR SOCKET ---
        obs[8:46] = np.clip(raw_demands / CHARGER_MAX_KW, 0.0, 1.0)
        
        # --- [46-83] POTENCIA ACTUAL ---
        efficiency_factor = 0.7 if 6 <= hour_24 <= 22 else 0.5
        obs[46:84] = obs[8:46] * efficiency_factor
        
        # --- [84-121] OCUPACION ---
        occupancy = (raw_demands > 0.1).astype(np.float32)
        obs[84:122] = occupancy
        
        # --- [122-137] ESTADO VEHICULOS ---
        motos_sockets = occupancy[:MOTOS_SOCKETS]
        taxis_sockets = occupancy[MOTOS_SOCKETS:]
        motos_charging = int(np.sum(motos_sockets))
        taxis_charging = int(np.sum(taxis_sockets))
        
        motos_power = obs[8:38]
        taxis_power = obs[38:46]
        motos_soc_avg = float(np.mean(motos_power)) if motos_charging > 0 else 0.0
        taxis_soc_avg = float(np.mean(taxis_power)) if taxis_charging > 0 else 0.0
        
        motos_time = (1.0 - motos_soc_avg) * 0.76
        taxis_time = (1.0 - taxis_soc_avg) * 1.2
        
        motos_available = MOTOS_SOCKETS - motos_charging
        taxis_available = TAXIS_SOCKETS - taxis_charging
        
        obs[122] = motos_charging / MOTOS_SOCKETS
        obs[123] = taxis_charging / TAXIS_SOCKETS
        obs[124] = 0.0  # Motos waiting (placeholer)
        obs[125] = 0.0  # Taxis waiting (placeholder)
        obs[126] = motos_soc_avg
        obs[127] = taxis_soc_avg
        obs[128] = np.clip(motos_time / 2.0, 0.0, 1.0)
        obs[129] = np.clip(taxis_time / 2.0, 0.0, 1.0)
        obs[130] = motos_available / MOTOS_SOCKETS
        obs[131] = taxis_available / TAXIS_SOCKETS
        obs[132] = 0.0  # Motos charged today (placeholder)
        obs[133] = 0.0  # Taxis charged today (placeholder)
        obs[134] = float(np.sum(obs[46:84])) / max(1.0, float(np.sum(obs[8:46])))  # Eficiencia
        obs[135] = min(1.0, solar_kw / max(1.0, ev_demand_estimate)) if ev_demand_estimate > 0 else 0.0
        
        co2_potential = (motos_available + taxis_available) * CHARGER_MEAN_KW * CO2_FACTOR_IQUITOS
        obs[136] = 0.0  # CO2 evitado hoy (placeholder)
        obs[137] = np.clip(co2_potential / 100.0, 0.0, 1.0)
        
        # --- [138-143] TIME FEATURES ---
        obs[138] = float(hour_24) / 24.0
        obs[139] = float(day_of_year % 7) / 7.0
        obs[140] = float((day_of_year // 30) % 12) / 12.0
        obs[141] = 1.0 if 6 <= hour_24 <= 22 else 0.0
        obs[142] = CO2_FACTOR_IQUITOS
        obs[143] = 0.15  # Tarifa
        
        # --- [144-155] COMUNICACION INTER-SISTEMA ---
        bess_can_supply = 1.0 if bess_energy_available > total_demand else bess_energy_available / max(1.0, total_demand)
        solar_sufficient = 1.0 if solar_kw >= total_demand else solar_kw / max(1.0, total_demand)
        grid_ratio = grid_import_needed / max(1.0, total_demand) if total_demand > 0 else 0.0
        urgency = max(0, motos_available + taxis_available) / max(1, NUM_CHARGERS) if NUM_CHARGERS > 0 else 0.0
        solar_opp = solar_surplus / max(1.0, total_demand) if total_demand > 0 else 1.0
        charge_bess = 1.0 if (solar_surplus > 100 and bess_soc < 0.8) else 0.0
        discharge_bess = 1.0 if (solar_kw < total_demand * 0.5 and bess_soc > 0.3) else 0.0
        saturation = (motos_charging + taxis_charging) / NUM_CHARGERS
        system_eff = min(1.0, total_demand / max(1.0, solar_kw + bess_energy_available / 10.0))
        
        obs[144] = np.clip(bess_can_supply, 0.0, 1.0)
        obs[145] = np.clip(solar_sufficient, 0.0, 1.0)
        obs[146] = np.clip(grid_ratio, 0.0, 1.0)
        obs[147] = 0.5  # Priority (placeholder)
        obs[148] = np.clip(urgency, 0.0, 1.0)
        obs[149] = np.clip(solar_opp, 0.0, 1.0)
        obs[150] = charge_bess
        obs[151] = discharge_bess
        obs[152] = np.clip(co2_potential, 0.0, 1.0)
        obs[153] = saturation
        obs[154] = system_eff
        obs[155] = 0.0  # Daily progress (placeholder)
        
        return obs
    
    # ============================================================================
    # VERSION 246-DIM (v6.0 CASCADA - COMUNICACION AVANZADA)
    # ============================================================================
    
    def _make_obs_246(
        self, 
        hour_idx: int, 
        data: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """
        Construccion 246-dim v6.0 con cascada de comunicacion.
        
        Estructura:
        [0-155]     = v5.3 basica (156)
        [156-193]   = SOC por socket (38)
        [194-231]   = Tiempo carga par socket (38)
        [232-233]   = BESS dispatch signals (2)
        [234-235]   = Solar bypass signals (2)
        [236-237]   = Grid import signals (2)
        [238-245]   = Agregados criticos (8)
        
        Total: 246 features
        """
        # Inicio con v5.3
        obs = self._make_obs_156(hour_idx, data, state)
        obs_extended = np.zeros(246, dtype=np.float32)
        obs_extended[:156] = obs
        
        # Extraer datos
        solar_hourly = data.get("solar_hourly", np.zeros(HOURS_PER_YEAR))
        chargers_hourly = data.get("chargers_hourly", np.zeros((HOURS_PER_YEAR, NUM_CHARGERS)))
        bess_soc_hourly = data.get("bess_soc_hourly", np.ones(HOURS_PER_YEAR) * 50.0)
        
        h = hour_idx % HOURS_PER_YEAR
        hour_24 = h % 24
        
        solar_kw = float(solar_hourly[h] if h < len(solar_hourly) else 0.0)
        bess_soc = float(bess_soc_hourly[h] if h < len(bess_soc_hourly) else 50.0) / 100.0
        
        if chargers_hourly.shape[1] >= NUM_CHARGERS:
            raw_demands = chargers_hourly[h, :NUM_CHARGERS]
        else:
            raw_demands = np.zeros(NUM_CHARGERS, dtype=np.float32)
            if chargers_hourly.shape[1] > 0:
                raw_demands[:chargers_hourly.shape[1]] = chargers_hourly[h]
        
        # --- [156-193] SOC POR SOCKET ---
        occupancy = (raw_demands > 0.1).astype(np.float32)
        obs_extended[156:194] = np.clip(obs[46:84] * 100, 0.0, 100.0)  # SOC en porcentaje
        
        # --- [194-231] TIEMPO CARGA RESTANTE ---
        for i in range(NUM_CHARGERS):
            remaining_soc = 100.0 - (obs[46 + i] * 100.0)
            hours_to_charge = remaining_soc / 20.0 if occupancy[i] > 0.5 else 0.0
            obs_extended[194 + i] = np.clip(hours_to_charge / 8.0, 0.0, 1.0)
        
        # --- [232-233] BESS DISPATCH SIGNALS ---
        bess_avail = bess_soc * BESS_MAX_KWH
        obs_extended[232] = np.clip(bess_avail / BESS_MAX_POWER_KW, 0.0, 1.0)  # Motos
        obs_extended[233] = np.clip(bess_avail / BESS_MAX_POWER_KW, 0.0, 1.0)  # Taxis
        
        # --- [234-235] SOLAR BYPASS ---
        obs_extended[234] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)  # Motos
        obs_extended[235] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)  # Taxis
        
        # --- [236-237] GRID IMPORT ---
        motos_demand = np.sum(obs[8:38])
        taxis_demand = np.sum(obs[38:46])
        total_avail = solar_kw + bess_avail / 10.0
        obs_extended[236] = np.clip(motos_demand / max(1.0, total_avail), 0.0, 1.0)
        obs_extended[237] = np.clip(taxis_demand / max(1.0, total_avail), 0.0, 1.0)
        
        # --- [238-245] AGREGADOS CRITICOS ---
        obs_extended[238] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)          # Solar now
        obs_extended[239] = bess_soc                                             # BESS SOC
        obs_extended[240] = float(np.sum(occupancy)) / NUM_CHARGERS             # Ocupacion total
        obs_extended[241] = float(np.mean(obs[46:84]))                          # Potencia promedio
        obs_extended[242] = float(hour_24) / 24.0                               # Hora
        obs_extended[243] = 1.0 if 6 <= hour_24 <= 22 else 0.0                 # Pico
        obs_extended[244] = CO2_FACTOR_IQUITOS                                  # CO2 factor
        obs_extended[245] = float(np.sum(obs[144:156])) / 12.0                 # Promedio comunicacion
        
        return obs_extended
    
    # ============================================================================
    # VERSION 66-DIM (EXPERIMENTAL EXPANDIDO)
    # ============================================================================
    
    def _make_obs_66(
        self, 
        hour_idx: int, 
        data: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """
        Construccion 66-dim experimental.
        
        [0-38]   = Base (39)
        [39-65]  = Observables reales (27)
        """
        obs = np.zeros(66, dtype=np.float32)
        
        solar_hourly = data.get("solar_hourly", np.zeros(HOURS_PER_YEAR))
        mall_hourly = data.get("mall_hourly", np.zeros(HOURS_PER_YEAR))
        bess_soc_hourly = data.get("bess_soc_hourly", np.ones(HOURS_PER_YEAR) * 50.0)
        
        h = hour_idx % HOURS_PER_YEAR
        
        # Base (39)
        solar_kw = float(solar_hourly[h] if h < len(solar_hourly) else 0.0)
        mall_kw = float(mall_hourly[h] if h < len(mall_hourly) else 0.0)
        bess_soc = float(bess_soc_hourly[h] if h < len(bess_soc_hourly) else 50.0)
        
        obs[0] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)
        obs[1] = np.clip(mall_kw / MALL_MAX_KW, 0.0, 1.0)
        obs[2] = np.clip(bess_soc / 100.0, 0.0, 1.0)
        obs[3:39] = np.random.uniform(-0.1, 0.1, 36)  # Dummy
        
        # Observables (27)
        observable_variables = data.get("observable_variables", {})
        for i, col in enumerate(observable_variables.keys()):
            if i >= 27:
                break
            arr = observable_variables[col]
            val = float(arr[h] if h < len(arr) else 0.0)
            if 'percent' in col.lower():
                obs[39 + i] = np.clip(val / 100.0, 0.0, 1.0)
            else:
                obs[39 + i] = np.clip(val / 1000.0, 0.0, 1.0)
        
        return obs
    
    # ============================================================================
    # VERSION 50-DIM (LEGACY SIMPLE)
    # ============================================================================
    
    def _make_obs_50(
        self, 
        hour_idx: int, 
        data: Dict[str, Any],
        state: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """
        Construccion 50-dim legacy simple. (DEPRECADO)
        
        Nota: Esta version esta deprecada. Usar 156-dim para nuevos desarrollos.
        """
        obs = np.zeros(50, dtype=np.float32)
        
        solar_hourly = data.get("solar_hourly", np.zeros(HOURS_PER_YEAR))
        mall_hourly = data.get("mall_hourly", np.zeros(HOURS_PER_YEAR))
        bess_soc_hourly = data.get("bess_soc_hourly", np.ones(HOURS_PER_YEAR) * 50.0)
        
        h = hour_idx % HOURS_PER_YEAR
        hour_24 = h % 24
        
        solar_kw = float(solar_hourly[h] if h < len(solar_hourly) else 0.0)
        mall_kw = float(mall_hourly[h] if h < len(mall_hourly) else 0.0)
        bess_soc = float(bess_soc_hourly[h] if h < len(bess_soc_hourly) else 50.0)
        
        # [0-7] Energia
        obs[0] = np.clip(solar_kw / SOLAR_MAX_KW, 0.0, 1.0)
        obs[1] = np.clip(mall_kw / MALL_MAX_KW, 0.0, 1.0)
        obs[2] = np.clip(bess_soc / 100.0, 0.0, 1.0)
        obs[3] = np.clip((solar_kw - mall_kw) / SOLAR_MAX_KW + 0.5, 0.0, 1.0)
        obs[4:8] = np.random.uniform(-0.1, 0.1, 4)
        
        # [8-37] Chargers (30)
        chargers_hourly = data.get("chargers_hourly", np.zeros((HOURS_PER_YEAR, NUM_CHARGERS)))
        if chargers_hourly.shape[1] >= 30:
            obs[8:38] = np.clip(chargers_hourly[h, :30] / CHARGER_MAX_KW, 0.0, 1.0)
        
        # [38-49] Time + misc (12)
        obs[38] = float(hour_24) / 24.0
        obs[39] = float((h // 24) % 7) / 7.0
        obs[40] = float(((h // 24) // 30) % 12) / 12.0
        obs[41:50] = np.random.uniform(-0.1, 0.1, 9)
        
        return obs


# ================================================================================
# FUNCIONES AUXILIARES DE VALIDACION
# ================================================================================

def validate_observation(obs: np.ndarray, obs_builder: ObservationBuilder) -> bool:
    """Valida que observacion tenga forma correcta."""
    if obs.shape[0] != obs_builder.obs_dim:
        return False
    if obs.dtype != np.float32:
        return False
    if np.any(np.isnan(obs)):
        return False
    return True


def get_observation_stats(
    obs: np.ndarray,
    name: str = "Observation"
) -> Dict[str, float]:
    """Retorna estadisticas de observacion."""
    return {
        "name": name,
        "dim": obs.shape[0],
        "dtype": str(obs.dtype),
        "mean": float(np.mean(obs)),
        "std": float(np.std(obs)),
        "min": float(np.min(obs)),
        "max": float(np.max(obs)),
        "has_nan": bool(np.any(np.isnan(obs))),
        "has_inf": bool(np.any(np.isinf(obs))),
    }


# ================================================================================
# EXPORTS
# ================================================================================

__all__ = [
    "ObservationBuilder",
    "validate_observation",
    "get_observation_stats",
    "SOLAR_MAX_KW",
    "MALL_MAX_KW",
    "BESS_MAX_KWH",
    "BESS_MAX_POWER_KW",
    "CHARGER_MAX_KW",
    "NUM_CHARGERS",
    "HOURS_PER_YEAR",
    "CO2_FACTOR_IQUITOS",
]
