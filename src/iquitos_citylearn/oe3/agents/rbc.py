from __future__ import annotations

from typing import Any

def make_basic_ev_rbc(env: Any) -> Any:
    """Return CityLearn's reference RBC that considers EV + battery."""
    from citylearn.agents.rbc import BasicElectricVehicleRBC_ReferenceController  # type: ignore
    try:
        return BasicElectricVehicleRBC_ReferenceController(env)
    except TypeError:
        return BasicElectricVehicleRBC_ReferenceController(env=env)
