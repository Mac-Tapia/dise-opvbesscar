"""Agente Baseline: Carga horaria fija para motos y mototaxis.

PROPÓSITO:
Baseline que carga EVs (motos y mototaxis) con PERFILES HORARIOS FIJOS,
sin control inteligente (RL). Comparación entre:

1. NoControl (todo cero) → Demanda pura
2. UncontrolledCharging (máximo siempre) → Carga descontrolada
3. FixedScheduleAgent (perfiles horarios) → Carga planificada fija (NEW)
4. RBC (rule-based) → Carga inteligente por reglas
5. SAC/PPO/A2C (RL) → Carga optimizada por RL
"""

from __future__ import annotations

from typing import Any, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class FixedScheduleAgent:
    """Agente baseline con perfiles horarios fijos.

    ESTRATEGIA:
    - Motos: Cargan en horario laboral (9AM-6PM) al 60% de potencia
    - Mototaxis: Cargan en horario extendido (9AM-10PM) al 70% de potencia
    - Otros actuadores (BESS, etc.): Cero (sin control)

    PROPÓSITO:
    Comparación entre:
    - Uncontrolled (RL control) → Decisión por agente
    - FixedSchedule (perfil fijo) → Decisión por humano/regla fija

    Esto mide: ¿Cuánto aprenden los agentes RL comparado con perfil óptimo fijo?
    """

    def __init__(self, env: Any, config: Optional[dict] = None):
        """
        Args:
            env: CityLearn environment
            config: Dict opcional con claves:
                - moto_schedule_power: potencia normalizada [0-1] para motos (default 0.6)
                - mototaxi_schedule_power: potencia normalizada [0-1] para mototaxis (default 0.7)
                - moto_hours: tuple de horas para motos (default (9, 10, ..., 17))
                - mototaxi_hours: tuple de horas para mototaxis (default (9, 10, ..., 21))
        """
        self.env = env
        self.config = config or {}

        # Potencias planificadas (0-1, normalizadas)
        self.moto_power = self.config.get("moto_schedule_power", 0.6)
        self.mototaxi_power = self.config.get("mototaxi_schedule_power", 0.7)

        # Horarios de carga (horas del día)
        self.moto_hours = self.config.get("moto_hours", tuple(range(9, 18)))  # 9AM-5PM (9-17)
        self.mototaxi_hours = self.config.get("mototaxi_hours", tuple(range(9, 22)))  # 9AM-9PM (9-21)

        # Setup
        self._setup_action_space()
        self._identify_charger_indices()

        logger.info(
            f"FixedScheduleAgent inicializado:\n"
            f"  Motos: {self.moto_power:.1%} potencia, horas {min(self.moto_hours)}-{max(self.moto_hours)}\n"
            f"  Mototaxis: {self.mototaxi_power:.1%} potencia, horas {min(self.mototaxi_hours)}-{max(self.mototaxi_hours)}\n"
            f"  BESS y otros: 0 (sin control)"
        )

    def _setup_action_space(self):
        """Configura espacios de acción."""
        self.action_space = getattr(self.env, "action_space", None)
        self.action_names = getattr(self.env, "action_names", None)

        if self.action_space is None:
            try:
                if hasattr(self.env, 'action_dimension'):
                    self.action_dimension = self.env.action_dimension
                else:
                    self.action_dimension = [(1,)]
            except ImportError:
                self.action_dimension = [(1,)]
        else:
            if isinstance(self.action_space, list):
                self.action_dimension = [sp.shape for sp in self.action_space]
            else:
                self.action_dimension = [self.action_space.shape]

    def _identify_charger_indices(self):
        """Identifica qué índices corresponden a motos vs mototaxis en las acciones.

        SCHEMA DE ACCIONES (CityLearn v2.5.0):
        action[0] = BESS setpoint (0-1)
        action[1:129] = charger_mall_1 to charger_mall_128 setpoints

        MAPEO DE CHARGERS:
        - charger_mall_1 to charger_mall_112: Motos (112 chargers)
        - charger_mall_113 to charger_mall_128: Mototaxis (16 chargers)

        Esto deja action_index:
        - index 0: BESS (NO tocar)
        - indices 1-112: Motos (aplicar moto_power si en moto_hours)
        - indices 113-128: Mototaxis (aplicar mototaxi_power si en mototaxi_hours)
        """
        self._moto_indices = list(range(1, 113))  # 1-112 (chargers 1-112)
        self._mototaxi_indices = list(range(113, 129))  # 113-128 (chargers 113-128)
        self._bess_index = 0  # No tocar

    def predict(self, observations: Any = None, deterministic: bool = True) -> List[List[float]]:
        """Devuelve acciones basadas en horario fijo.

        ESTRATEGIA:
        1. Extraer hora actual del estado de observación
        2. Si en moto_hours → motos = moto_power, else = 0
        3. Si en mototaxi_hours → mototaxis = mototaxi_power, else = 0
        4. BESS y otros = 0
        """
        # Extraer hora actual
        hour = self._get_current_hour(observations)

        actions: List[List[float]] = []

        if isinstance(self.action_space, list):
            for i, sp in enumerate(self.action_space):
                action = np.zeros(sp.shape[0], dtype=np.float32)

                # Aplicar perfiles horarios
                if hour in self.moto_hours:
                    for idx in self._moto_indices:
                        if idx < len(action):
                            action[idx] = self.moto_power

                if hour in self.mototaxi_hours:
                    for idx in self._mototaxi_indices:
                        if idx < len(action):
                            action[idx] = self.mototaxi_power

                # Clip a límites del espacio de acción
                action = np.clip(
                    action,
                    getattr(sp, "low", 0.0),
                    getattr(sp, "high", 1.0)
                )
                actions.append(action.tolist())

        elif self.action_space is not None:
            action = np.zeros(self.action_space.shape[0], dtype=np.float32)

            # Aplicar perfiles horarios
            if hour in self.moto_hours:
                for idx in self._moto_indices:
                    if idx < len(action):
                        action[idx] = self.moto_power

            if hour in self.mototaxi_hours:
                for idx in self._mototaxi_indices:
                    if idx < len(action):
                        action[idx] = self.mototaxi_power

            action = np.clip(
                action,
                getattr(self.action_space, "low", 0.0),
                getattr(self.action_space, "high", 1.0)
            )
            actions.append(action.tolist())

        else:
            # Fallback
            for dim in self.action_dimension:
                action = np.zeros(dim[0] if isinstance(dim, tuple) else dim, dtype=np.float32)

                if hour in self.moto_hours:
                    for idx in self._moto_indices:
                        if idx < len(action):
                            action[idx] = self.moto_power

                if hour in self.mototaxi_hours:
                    for idx in self._mototaxi_indices:
                        if idx < len(action):
                            action[idx] = self.mototaxi_power

                actions.append(np.clip(action, 0.0, 1.0).tolist())

        return actions

    def act(self, observations: Any = None) -> List[List[float]]:
        """Alias para predict (compatibilidad con SB3)."""
        return self.predict(observations)

    def _get_current_hour(self, observations: Any) -> int:
        """Extrae la hora actual del estado de observación.

        LAYOUT DE OBSERVACIÓN (CityLearn v2.5.0 - 394 dimensiones):
        Las últimas dimensiones contienen características temporales:
        - month (1-12)
        - hour (0-23)
        - day_of_week (0-6)
        - day_of_year (0-364)

        Asumimos que hour está en índice -2 o similar (depende de dataset).
        Fallback: usar hora del sistema si no se puede extraer.
        """
        if observations is None:
            return 12  # Default mediodía

        try:
            # Aplanar observaciones si es lista/tuple
            if isinstance(observations, (list, tuple)):
                obs_flat = np.concatenate([np.array(o).ravel() for o in observations])
            else:
                obs_flat = np.array(observations).ravel()

            # Buscar índice de hora (típicamente cerca del final)
            # CityLearn coloca time features al final del vector de obs
            if len(obs_flat) >= 4:
                # Índices típicos de características temporales
                # Asumir: [..., month, hour, day_of_week, day_of_year]
                # Índice del hour = -3
                potential_hour = int(obs_flat[-3])
                if 0 <= potential_hour < 24:
                    return potential_hour

                # Fallback: índice -2
                potential_hour = int(obs_flat[-2])
                if 0 <= potential_hour < 24:
                    return potential_hour

        except (IndexError, ValueError, TypeError):
            pass

        # Si no se puede extraer, retornar hora actual del sistema
        from datetime import datetime
        return datetime.now().hour

    def learn(self, episodes: int = 0):
        """Baseline no requiere entrenamiento."""
        logger.info(
            f"FixedScheduleAgent - no requiere entrenamiento.\n"
            f"Carga según perfiles horarios fijos:\n"
            f"  Motos: {self.moto_power:.1%} en horas {self.moto_hours}\n"
            f"  Mototaxis: {self.mototaxi_power:.1%} en horas {self.mototaxi_hours}"
        )


def make_fixed_schedule(
    env: Any,
    moto_power: float = 0.6,
    mototaxi_power: float = 0.7,
    moto_hours: Optional[tuple] = None,
    mototaxi_hours: Optional[tuple] = None,
) -> FixedScheduleAgent:
    """Factory function para crear agente FixedSchedule.

    Args:
        env: CityLearn environment
        moto_power: Potencia normalizada [0-1] para motos
        mototaxi_power: Potencia normalizada [0-1] para mototaxis
        moto_hours: Tuple de horas para carga de motos
        mototaxi_hours: Tuple de horas para carga de mototaxis

    Returns:
        FixedScheduleAgent configurado
    """
    config = {
        "moto_schedule_power": moto_power,
        "mototaxi_schedule_power": mototaxi_power,
    }
    if moto_hours is not None:
        config["moto_hours"] = moto_hours
    if mototaxi_hours is not None:
        config["mototaxi_hours"] = mototaxi_hours

    return FixedScheduleAgent(env, config=config)
