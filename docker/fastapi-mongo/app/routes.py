"""API routes."""

from pathlib import Path
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.database import get_database
from app.models import (
    ChargingSessionCreate,
    SimulationResult,
    AgentMetrics,
)

router = APIRouter()

# Carbon intensity for Iquitos thermal grid (kg CO2/kWh)
CARBON_INTENSITY = 0.4521

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