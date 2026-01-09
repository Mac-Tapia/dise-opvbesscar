"""API routes."""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.database import get_database
from app.models import (
    ChargingSessionCreate,
    SimulationResult,
    AgentMetrics,
)
from app.inference import get_controller, load_controller
from app.ev_simulator import EVChargerSimulator

router = APIRouter()

# Carbon intensity for Iquitos thermal grid (kg CO2/kWh)
CARBON_INTENSITY = 0.4521

# Global simulator instance for demo mode
_simulator: Optional[EVChargerSimulator] = None


def get_simulator() -> EVChargerSimulator:
    """Get or create the global EV simulator."""
    global _simulator
    if _simulator is None:
        _simulator = EVChargerSimulator()
    return _simulator


# =============================================
# Real-Time Control Models
# =============================================

class ControlObservations(BaseModel):
    """Current observations for real-time control."""
    hour: int  # 0-23
    month: int  # 1-12
    carbon_intensity: float = 0.4521  # kg CO2/kWh
    solar_generation_kw: float = 0.0
    bess_soc: float = 0.5  # 0-1
    grid_price: float = 0.20  # USD/kWh
    ev_socs: Optional[Dict[str, float]] = None  # Charger ID -> SOC


class ControlAction(BaseModel):
    """Single control action."""
    device: str
    action: float  # -1 to 1
    power_kw: float
    recommendation: str


class ControlResponse(BaseModel):
    """Response from control endpoint."""
    timestamp: datetime
    bess: Dict
    ev_chargers: List[Dict]
    total_charge_power_kw: float
    total_discharge_power_kw: float
    model_loaded: bool

# Paths to OE3 results (mounted from host)
OE3_ANALYSES_PATH = Path("/data/analyses/oe3")
OE3_TRAINING_PATH = Path("/data/analyses/oe3/training")
OE3_OUTPUTS_PATH = Path("/data/outputs/oe3")


@router.post("/sessions", response_model=dict)
async def create_charging_session(session: ChargingSessionCreate):
    """Create a new charging session."""
    db = get_database()
    
    session_dict = session.model_dump()
    session_dict["timestamp"] = datetime.utcnow()
    session_dict["co2_kg"] = session.energy_kwh * CARBON_INTENSITY
    
    result = await db.charging_sessions.insert_one(session_dict)
    
    return {
        "id": str(result.inserted_id),
        "message": "Charging session created",
        "co2_kg": session_dict["co2_kg"],
    }


@router.get("/sessions", response_model=List[dict])
async def get_charging_sessions(
    playa: str = None,
    vehicle_type: str = None,
    limit: int = 100,
):
    """Get charging sessions with optional filters."""
    db = get_database()
    
    query = {}
    if playa:
        query["playa"] = playa
    if vehicle_type:
        query["vehicle_type"] = vehicle_type
    
    cursor = db.charging_sessions.find(query).limit(limit)
    sessions = []
    
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        sessions.append(doc)
    
    return sessions


@router.get("/sessions/stats")
async def get_session_stats():
    """Get aggregated statistics for charging sessions."""
    db = get_database()
    
    pipeline = [
        {
            "$group": {
                "_id": "$playa",
                "total_sessions": {"$sum": 1},
                "total_energy_kwh": {"$sum": "$energy_kwh"},
                "total_co2_kg": {"$sum": "$co2_kg"},
                "avg_duration_min": {"$avg": "$duration_minutes"},
            }
        }
    ]
    
    results = []
    async for doc in db.charging_sessions.aggregate(pipeline):
        results.append(doc)
    
    return {
        "stats_by_playa": results,
        "carbon_intensity_kg_kwh": CARBON_INTENSITY,
    }


@router.post("/simulations", response_model=dict)
async def store_simulation_result(result: SimulationResult):
    """Store RL agent simulation result."""
    db = get_database()
    
    result_dict = result.model_dump()
    inserted = await db.simulations.insert_one(result_dict)
    
    return {
        "id": str(inserted.inserted_id),
        "message": f"Simulation result for {result.agent} stored",
    }


@router.get("/simulations")
async def get_simulations(agent: str = None):
    """Get simulation results."""
    db = get_database()
    
    query = {"agent": agent} if agent else {}
    cursor = db.simulations.find(query).sort("timestamp", -1)
    
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    
    return results


@router.get("/agents/comparison")
async def compare_agents():
    """Compare all RL agents performance."""
    db = get_database()
    
    pipeline = [
        {
            "$group": {
                "_id": "$agent",
                "runs": {"$sum": 1},
                "avg_reward": {"$avg": "$total_reward"},
                "avg_co2_kg": {"$avg": "$co2_emissions_kg"},
                "avg_solar_pct": {"$avg": "$solar_utilization_pct"},
            }
        },
        {"$sort": {"avg_co2_kg": 1}},  # Sort by lowest CO2
    ]
    
    results = []
    async for doc in db.simulations.aggregate(pipeline):
        results.append(doc)
    
    return {
        "comparison": results,
        "best_agent": results[0]["_id"] if results else None,
    }


@router.post("/metrics", response_model=dict)
async def store_agent_metrics(metrics: AgentMetrics):
    """Store detailed agent metrics per episode."""
    db = get_database()
    
    metrics_dict = metrics.model_dump()
    metrics_dict["timestamp"] = datetime.utcnow()
    
    await db.agent_metrics.insert_one(metrics_dict)
    
    return {"message": "Metrics stored", "agent": metrics.agent_name}


@router.get("/infrastructure")
async def get_infrastructure_info():
    """Get infrastructure configuration."""
    return {
        "location": {
            "city": "Iquitos",
            "country": "Peru",
            "lat": -3.75,
            "lon": -73.25,
            "timezone": "America/Lima",
        },
        "playas": {
            "Playa_Motos": {
                "chargers": 112,
                "charger_power_kw": 2,
                "total_power_kw": 224,
                "pv_kwp": 3641.8,
                "bess_kwh": 1750,
            },
            "Playa_Mototaxis": {
                "chargers": 16,
                "charger_power_kw": 3,
                "total_power_kw": 48,
                "pv_kwp": 520.2,
                "bess_kwh": 250,
            },
        },
        "totals": {
            "chargers": 128,
            "power_kw": 272,
            "pv_kwp": 4162,
            "bess_kwh": 2000,
        },
        "carbon_intensity_kg_kwh": CARBON_INTENSITY,
    }


# =============================================
# OE3 Results Endpoints - Training & Simulation
# =============================================

@router.get("/oe3/status")
async def get_oe3_status():
    """Get current OE3 training and simulation status."""
    import csv
    
    status = {
        "training": {},
        "checkpoints": {},
        "results_available": False,
    }
    
    # Helper to safely convert to float/int (handles empty strings)
    def safe_float(val, default=0.0):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default
    
    def safe_int(val, default=0):
        try:
            return int(float(val)) if val else default
        except (ValueError, TypeError):
            return default
    
    # Check training progress files
    progress_dir = OE3_TRAINING_PATH / "progress"
    if progress_dir.exists():
        for agent in ["sac", "ppo", "a2c"]:
            progress_file = progress_dir / f"{agent}_progress.csv"
            if progress_file.exists():
                with open(progress_file, 'r') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if rows:
                        last_row = rows[-1]
                        status["training"][agent.upper()] = {
                            "episodes": len(rows),
                            "last_step": safe_int(last_row.get("global_step")),
                            "last_reward": safe_float(last_row.get("episode_reward")),
                        }
    
    # Check checkpoints
    checkpoint_dir = OE3_TRAINING_PATH / "checkpoints"
    if checkpoint_dir.exists():
        for agent in ["sac", "ppo", "a2c"]:
            agent_ckpt = checkpoint_dir / agent
            if agent_ckpt.exists():
                ckpts = list(agent_ckpt.glob(f"{agent}_step_*.zip"))
                final = agent_ckpt / f"{agent}_final.zip"
                status["checkpoints"][agent.upper()] = {
                    "count": len(ckpts),
                    "has_final": final.exists(),
                    "latest_step": max([int(p.stem.split("_")[-1]) for p in ckpts], default=0) if ckpts else 0,
                }
    
    # Check if CO2 comparison results exist
    co2_table = OE3_ANALYSES_PATH / "co2_comparison_table.csv"
    status["results_available"] = co2_table.exists()
    
    return status


@router.get("/oe3/co2-comparison")
async def get_co2_comparison():
    """Get CO2 emissions comparison between agents."""
    import csv
    
    csv_file = OE3_ANALYSES_PATH / "co2_comparison_table.csv"
    if not csv_file.exists():
        raise HTTPException(status_code=404, detail="CO2 comparison not available. Run OE3 simulation first.")
    
    results = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    
    return {
        "comparison": results,
        "carbon_intensity_kg_kwh": CARBON_INTENSITY,
        "source": "OE3 Simulation Results",
    }


@router.get("/oe3/agent-summary")
async def get_agent_summary():
    """Get agent episode summary from OE3 training."""
    import csv
    
    csv_file = OE3_ANALYSES_PATH / "agent_episode_summary.csv"
    if not csv_file.exists():
        raise HTTPException(status_code=404, detail="Agent summary not available.")
    
    results = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    
    return {"episodes": results}


@router.get("/oe3/training-progress/{agent}")
async def get_training_progress(agent: str):
    """Get training progress for a specific agent (SAC, PPO, A2C)."""
    import csv
    
    # Safe conversion helpers
    def safe_float(val, default=0.0):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default
    
    def safe_int(val, default=0):
        try:
            return int(float(val)) if val else default
        except (ValueError, TypeError):
            return default
    
    agent_lower = agent.lower()
    if agent_lower not in ["sac", "ppo", "a2c"]:
        raise HTTPException(status_code=400, detail="Agent must be SAC, PPO, or A2C")
    
    progress_file = OE3_TRAINING_PATH / "progress" / f"{agent_lower}_progress.csv"
    if not progress_file.exists():
        raise HTTPException(status_code=404, detail=f"No training progress for {agent}")
    
    results = []
    with open(progress_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                "episode": safe_int(row.get("episode")),
                "global_step": safe_int(row.get("global_step")),
                "reward": safe_float(row.get("episode_reward")),
                "length": safe_int(row.get("episode_length")),
            })
    
    return {
        "agent": agent.upper(),
        "total_episodes": len(results),
        "progress": results,
    }


@router.get("/oe3/training-graph/{agent}")
async def get_training_graph(agent: str):
    """Get training progress graph image for an agent."""
    agent_upper = agent.upper()
    
    # Try different naming conventions
    possible_names = [
        f"{agent_upper}_training_updated.png",
        f"{agent_upper}_training.png",
        f"{agent.lower()}_training.png",
    ]
    
    for name in possible_names:
        graph_file = OE3_TRAINING_PATH / name
        if graph_file.exists():
            return FileResponse(graph_file, media_type="image/png")
    
    raise HTTPException(status_code=404, detail=f"Training graph for {agent} not found")


@router.get("/oe3/comparison-graph")
async def get_comparison_graph():
    """Get agents comparison graph."""
    graph_file = OE3_TRAINING_PATH / "plots" / "training_comparison.png"
    if not graph_file.exists():
        raise HTTPException(status_code=404, detail="Comparison graph not available")
    
    return FileResponse(graph_file, media_type="image/png")


@router.get("/oe3/co2-breakdown")
async def get_co2_breakdown():
    """Get detailed CO2 breakdown by source."""
    import csv
    
    csv_file = OE3_ANALYSES_PATH / "co2_breakdown.csv"
    if not csv_file.exists():
        raise HTTPException(status_code=404, detail="CO2 breakdown not available")
    
    results = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    
    return {"breakdown": results}


# =============================================
# REAL-TIME CONTROL ENDPOINTS
# =============================================

@router.post("/control/load-model")
async def load_control_model():
    """
    Load the trained A2C model for real-time control.
    Call this endpoint once at system startup.
    """
    success = load_controller()
    if success:
        return {
            "status": "ok",
            "message": "A2C model loaded successfully",
            "model": "a2c_final.zip",
            "ready_for_control": True,
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to load A2C model. Check if model file exists."
        )


@router.get("/control/status")
async def get_control_status():
    """Check if the real-time controller is ready."""
    controller = get_controller()
    return {
        "model_loaded": controller.model_loaded,
        "model_path": str(controller.model_path),
        "ready_for_control": controller.model_loaded,
    }


@router.post("/control/get-actions", response_model=ControlResponse)
async def get_control_actions(observations: ControlObservations):
    """
    Get real-time control actions for BESS and all 128 EV chargers.
    
    This is the main endpoint for production control.
    Send current observations, receive optimal actions.
    
    Example request:
    ```json
    {
        "hour": 14,
        "month": 6,
        "carbon_intensity": 0.4521,
        "solar_generation_kw": 2500.0,
        "bess_soc": 0.65,
        "grid_price": 0.20
    }
    ```
    """
    controller = get_controller()
    
    if not controller.model_loaded:
        raise HTTPException(
            status_code=503,
            detail="Controller not ready. Call /control/load-model first."
        )
    
    try:
        obs_dict = observations.model_dump()
        
        # Get BESS command
        bess_cmd = controller.get_bess_command(obs_dict)
        
        # Get EV charger commands
        ev_cmds = controller.get_ev_charging_commands(obs_dict)
        
        # Calculate totals
        total_charge = sum(c["power_kw"] for c in ev_cmds if c["power_kw"] > 0)
        total_discharge = abs(sum(c["power_kw"] for c in ev_cmds if c["power_kw"] < 0))
        
        if bess_cmd["power_kw"] > 0:
            total_charge += bess_cmd["power_kw"]
        else:
            total_discharge += abs(bess_cmd["power_kw"])
        
        # Store decision in database for audit trail
        db = get_database()
        await db.control_decisions.insert_one({
            "timestamp": datetime.utcnow(),
            "observations": obs_dict,
            "bess_action": bess_cmd,
            "total_charge_kw": total_charge,
            "total_discharge_kw": total_discharge,
        })
        
        return ControlResponse(
            timestamp=datetime.utcnow(),
            bess=bess_cmd,
            ev_chargers=ev_cmds,
            total_charge_power_kw=round(total_charge, 2),
            total_discharge_power_kw=round(total_discharge, 2),
            model_loaded=True,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Control error: {str(e)}")


@router.get("/control/bess")
async def get_bess_status():
    """Get BESS configuration and control info."""
    return {
        "device": "BESS",
        "capacity_kwh": 2000,
        "max_power_kw": 1200,
        "location": "Centralized (serves both playas)",
        "control": "Managed by A2C agent",
        "action_range": {"min": -1, "max": 1},
        "action_meaning": {
            "+1": "Charge at max power (1200 kW)",
            "0": "Hold / No action",
            "-1": "Discharge at max power (1200 kW)",
        },
    }


@router.get("/control/chargers")
async def get_chargers_info():
    """Get charger configuration."""
    return {
        "total_chargers": 128,
        "playas": {
            "Playa_Motos": {
                "chargers": 112,
                "power_per_charger_kw": 2,
                "total_power_kw": 224,
                "charger_ids": [f"MOTO_CH_{i:03d}" for i in range(1, 113)],
            },
            "Playa_Mototaxis": {
                "chargers": 16,
                "power_per_charger_kw": 3,
                "total_power_kw": 48,
                "charger_ids": [f"MOTOTAXI_CH_{i:03d}" for i in range(1, 17)],
            },
        },
        "total_power_kw": 272,
        "control": "Individual control per charger by A2C agent",
    }


@router.get("/control/decisions")
async def get_control_decisions(limit: int = 100):
    """Get recent control decisions for audit."""
    db = get_database()
    
    cursor = db.control_decisions.find().sort("timestamp", -1).limit(limit)
    
    decisions = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        decisions.append(doc)
    
    return {"decisions": decisions, "count": len(decisions)}


# =============================================
# SIMULATION MODE ENDPOINTS (for demo without hardware)
# =============================================

@router.post("/simulation/reset")
async def reset_simulation():
    """
    Reset the EV charger simulator to initial state.
    Use this to start a fresh simulation.
    """
    global _simulator
    _simulator = EVChargerSimulator()
    return {
        "status": "ok",
        "message": "Simulator reset to initial state",
        "chargers": 128,
    }


@router.post("/simulation/step")
async def simulation_step(
    hour: int = 12,
    month: int = 1,
    bess_soc: float = 0.5,
    solar_generation_kw: float = 0.0,
):
    """
    Advance simulation by one timestep and get control actions.
    
    This endpoint:
    1. Updates simulated EV arrivals/departures based on hour
    2. Generates synthetic sensor data
    3. Gets control actions from A2C agent
    4. Returns complete state and actions
    
    Use this for demo/testing without real hardware.
    """
    simulator = get_simulator()
    controller = get_controller()
    
    # Update simulator state
    simulator.update(hour=hour)
    
    # Get synthetic observations
    obs = simulator.get_current_state(
        hour=hour,
        month=month,
        bess_soc=bess_soc,
        solar_generation_kw=solar_generation_kw,
    )
    
    # Get summary
    summary = simulator.get_summary()
    
    # Get actions if model loaded
    actions = None
    bess_cmd = None
    if controller.model_loaded:
        try:
            bess_cmd = controller.get_bess_command(obs)
            ev_cmds = controller.get_ev_charging_commands(obs)
            
            # Only include connected chargers in response
            actions = [
                cmd for cmd in ev_cmds 
                if obs["ev_connected"].get(cmd["charger_id"], False)
            ]
        except Exception as e:
            actions = {"error": str(e)}
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "hour": hour,
        "simulation_summary": summary,
        "bess_command": bess_cmd,
        "ev_commands": actions,
        "observations_sample": {
            "connected_evs": sum(obs["ev_connected"].values()),
            "avg_soc": (
                sum(obs["ev_socs"].values()) / max(1, len(obs["ev_socs"]))
                if obs["ev_socs"] else 0
            ),
            "solar_kw": obs["solar_generation_kw"],
            "bess_soc": obs["bess_soc"],
        },
        "model_loaded": controller.model_loaded,
    }


@router.get("/simulation/state")
async def get_simulation_state():
    """Get current state of the EV charger simulator."""
    simulator = get_simulator()
    summary = simulator.get_summary()
    
    # Get detailed charger states
    charger_states = []
    for charger in simulator.chargers:
        if charger.connected:
            charger_states.append({
                "charger_id": charger.charger_id,
                "type": charger.charger_type,
                "connected": True,
                "soc": round(charger.ev_soc, 3),
                "capacity_kwh": round(charger.ev_capacity_kwh, 2),
                "departure_hour": round(charger.departure_hour, 2),
                "required_soc": round(charger.required_soc, 2),
            })
    
    return {
        "summary": summary,
        "connected_chargers": charger_states,
    }


@router.post("/simulation/run-24h")
async def run_24h_simulation(
    month: int = 6,
    initial_bess_soc: float = 0.5,
):
    """
    Run a complete 24-hour simulation with A2C agent control.
    
    Returns hourly results including:
    - Occupancy at each hour
    - Control actions taken
    - Energy flows
    """
    simulator = get_simulator()
    controller = get_controller()
    
    # Reset simulator
    global _simulator
    _simulator = EVChargerSimulator()
    simulator = _simulator
    
    results = []
    bess_soc = initial_bess_soc
    
    for hour in range(24):
        # Update simulator
        simulator.update(hour=hour)
        
        # Estimate solar generation
        if 6 <= hour <= 18:
            hour_from_noon = abs(hour - 12)
            solar_factor = max(0, 1 - (hour_from_noon / 6) ** 2)
            solar_kw = 4162 * solar_factor * 0.8  # 80% of max
        else:
            solar_kw = 0
        
        # Get state and actions
        obs = simulator.get_current_state(
            hour=hour,
            month=month,
            bess_soc=bess_soc,
            solar_generation_kw=solar_kw,
        )
        
        summary = simulator.get_summary()
        
        hour_result = {
            "hour": hour,
            "occupancy": summary["total_connected"],
            "moto_connected": summary["moto_connected"],
            "mototaxi_connected": summary["mototaxi_connected"],
            "solar_kw": round(solar_kw, 1),
            "bess_soc": round(bess_soc, 3),
        }
        
        if controller.model_loaded:
            try:
                bess_cmd = controller.get_bess_command(obs)
                hour_result["bess_action"] = bess_cmd["recommendation"]
                hour_result["bess_power_kw"] = bess_cmd["power_kw"]
                
                # Simulate BESS SOC change
                bess_soc += bess_cmd["power_kw"] / 2000 * 0.95  # 95% efficiency
                bess_soc = max(0.1, min(0.95, bess_soc))
            except Exception as e:
                hour_result["error"] = str(e)
        
        results.append(hour_result)
    
    # Calculate summary stats
    peak_occupancy = max(r["occupancy"] for r in results)
    peak_hour = next(r["hour"] for r in results if r["occupancy"] == peak_occupancy)
    
    return {
        "simulation_complete": True,
        "hours_simulated": 24,
        "peak_occupancy": peak_occupancy,
        "peak_hour": peak_hour,
        "hourly_results": results,
        "model_used": controller.model_loaded,
    }