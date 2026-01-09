"""Pydantic models for API."""

from datetime import datetime
from pydantic import BaseModel, Field


class ChargingSessionBase(BaseModel):
    """Base model for charging session."""

    charger_id: int = Field(..., ge=1, le=128, description="ID del cargador (1-128)")
    vehicle_type: str = Field(..., pattern="^(moto|mototaxi)$")
    playa: str = Field(..., pattern="^(Playa_Motos|Playa_Mototaxis)$")
    energy_kwh: float = Field(..., ge=0, description="Energía consumida en kWh")
    duration_minutes: int = Field(..., ge=0, description="Duración en minutos")


class ChargingSessionCreate(ChargingSessionBase):
    """Model for creating charging session."""

    pass


class ChargingSession(ChargingSessionBase):
    """Model for charging session response."""

    id: str = Field(..., alias="_id")
    timestamp: datetime
    co2_kg: float = Field(..., description="Emisiones CO2 en kg")

    class Config:
        populate_by_name = True


class SimulationResult(BaseModel):
    """Model for simulation results."""

    agent: str = Field(..., description="Nombre del agente RL")
    episodes: int
    total_reward: float
    co2_emissions_kg: float
    solar_utilization_pct: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentMetrics(BaseModel):
    """Metrics for RL agent performance."""

    agent_name: str
    episode: int
    reward: float
    steps: int
    co2_kg: float
    cost_usd: float
    solar_kwh: float
    grid_kwh: float
