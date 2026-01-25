#!/usr/bin/env python3.11
"""
PVBESSCAR FastAPI - Servidor Robusto y Definitivo
"""
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from datetime import datetime
import random
from typing import List

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# App
app = FastAPI(title="PVBESSCAR API", version="3.0", docs_url="/docs")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado Global
class State:
    episodes = 2847
    reward = 12548.3
    action = "IDLE"
    cost = 0.0
    co2 = 0.0
    avail = 95.2
    conv = 47.8

state = State()
ws_clients: List[WebSocket] = []

# ========== GET ENDPOINTS ==========

@app.get("/health")
async def health():
    return {"status": "healthy", "time": datetime.now().isoformat()}

@app.get("/api/metrics")
async def get_metrics():
    return {
        "consumo_kw": round(30 + random.uniform(-5, 20), 2),
        "solar_kw": round(max(0, 40 + random.uniform(-20, 30)), 2),
        "bateria_soc": round(max(0, min(100, 60 + random.uniform(-10, 10))), 1),
        "grid_import_kw": round(max(0, random.uniform(-5, 15)), 2),
        "costo_kwh": round(random.uniform(0.12, 0.28), 3),
        "costo_total": 1250.50,
        "co2_evitado_kg": 450
    }

@app.get("/api/agent")
async def get_agent():
    return {
        "status": "running",
        "action": state.action,
        "episodes": state.episodes,
        "total_reward": round(state.reward, 2),
        "learning_rate": 0.0045,
        "convergence_percent": 47.8,
        "loss": 0.0234
    }

@app.get("/api/objectives")
async def get_objectives():
    return {
        "reduccion_costo": {"target": 75, "current": state.cost},
        "reduccion_co2": {"target": 50, "current": state.co2},
        "disponibilidad": {"target": 99, "current": state.avail},
        "convergencia_ia": {"target": 100, "current": state.conv}
    }

@app.get("/api/historical/{hours}")
async def get_historical(hours: int = 24):
    return {
        "hours": hours,
        "data": {
            "timestamps": [datetime.now().isoformat()] * hours,
            "consumos": [30 + random.randint(-5, 15) for _ in range(hours)],
            "solares": [50 * abs(__import__('math').sin(i * 3.14 / 12)) for i in range(hours)],
            "baterias": [50 + random.randint(-10, 10) for _ in range(hours)],
            "costos": [1000 + random.randint(0, 500) for _ in range(hours)],
            "acciones": [random.choice(["CHARGE", "DISCHARGE", "IDLE"]) for _ in range(hours)],
            "co2": [450 + random.randint(-50, 50) for _ in range(hours)]
        }
    }

# ========== POST ENDPOINTS ==========

@app.post("/api/control/{action}")
async def control(action: str):
    action_upper = action.upper()
    
    if action_upper not in ["CHARGE", "DISCHARGE", "IDLE", "PAUSE", "RESUME"]:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    
    state.action = action_upper
    state.episodes += 1
    state.reward += random.uniform(10, 50)
    
    if action_upper == "CHARGE":
        state.cost = min(75, state.cost + 0.5)
        state.conv = min(100, state.conv + 0.3)
    elif action_upper == "DISCHARGE":
        state.co2 = min(50, state.co2 + 0.4)
    elif action_upper == "IDLE":
        state.avail = min(99, state.avail + 0.1)
    
    # Notify WS clients
    for client in ws_clients[:]:
        try:
            await client.send_json({
                "type": "action",
                "action": action_upper,
                "time": datetime.now().isoformat()
            })
        except:
            if client in ws_clients:
                ws_clients.remove(client)
    
    return {
        "status": "success",
        "action": action_upper,
        "episodes": state.episodes,
        "reward": round(state.reward, 2),
        "timestamp": datetime.now().isoformat()
    }

# ========== WEBSOCKET ==========

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    logger.info(f"WS connected: {len(ws_clients)}")
    
    try:
        while True:
            await asyncio.sleep(2)
            await websocket.send_json({
                "type": "metrics",
                "time": datetime.now().isoformat(),
                "episodes": state.episodes
            })
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        if websocket in ws_clients:
            ws_clients.remove(websocket)
        logger.info(f"WS disconnected: {len(ws_clients)}")

# ========== ROOT ==========

@app.get("/")
async def root():
    return {
        "service": "PVBESSCAR Real-Time API",
        "version": "3.0",
        "status": "running"
    }

# ========== MAIN ==========

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting PVBESSCAR API v3.0")
    logger.info("Listen on http://0.0.0.0:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
