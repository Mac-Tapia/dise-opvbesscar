#!/usr/bin/env python3.11
"""
API FastAPI para PVBESSCAR - Robusta y Persistente
"""

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
from datetime import datetime
import random
from typing import List

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="PVBESSCAR API", version="3.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Estado global
agent_episodes = 2847
agent_reward = 12548.3
agent_action = "IDLE"
objectives = {"cost": 0, "co2": 0, "avail": 95.2, "conv": 47.8}
ws_clients: List[WebSocket] = []

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}

@app.get("/api/metrics")
async def metrics():
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
async def agent_state():
    return {
        "status": "running",
        "action": agent_action,
        "episodes": agent_episodes,
        "total_reward": round(agent_reward, 2),
        "learning_rate": 0.0045,
        "convergence_percent": 47.8,
        "loss": 0.0234
    }

@app.get("/api/objectives")
async def get_objectives():
    return {
        "reduccion_costo": {"target": 75, "current": objectives["cost"]},
        "reduccion_co2": {"target": 50, "current": objectives["co2"]},
        "disponibilidad": {"target": 99, "current": objectives["avail"]},
        "convergencia_ia": {"target": 100, "current": objectives["conv"]}
    }

@app.post("/api/control/{action}")
async def control(action: str):
    global agent_episodes, agent_reward, agent_action, objectives
    
    action = action.upper()
    if action not in ["CHARGE", "DISCHARGE", "IDLE"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    agent_action = action
    agent_episodes += 1
    agent_reward += random.uniform(10, 50)
    
    if action == "CHARGE":
        objectives["cost"] = min(75, objectives["cost"] + 0.5)
        objectives["conv"] = min(100, objectives["conv"] + 0.3)
    elif action == "DISCHARGE":
        objectives["co2"] = min(50, objectives["co2"] + 0.4)
    else:
        objectives["avail"] = min(99, objectives["avail"] + 0.1)
    
    for client in ws_clients[:]:
        try:
            await client.send_json({"type": "action", "action": action})
        except:
            ws_clients.remove(client)
    
    return {
        "status": "ok",
        "action": action,
        "episodes": agent_episodes,
        "reward": round(agent_reward, 2)
    }

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    logger.info(f"WS conectado: {len(ws_clients)} clientes")
    try:
        while True:
            await asyncio.sleep(2)
            await websocket.send_json({"type": "metrics", "time": datetime.now().isoformat()})
    except:
        if websocket in ws_clients:
            ws_clients.remove(websocket)

@app.get("/")
async def root():
    return {"service": "PVBESSCAR API", "version": "3.0", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor...")
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())
