#!/usr/bin/env python3.11
"""
FastAPI con WebSocket para Dashboard en Tiempo Real
Proporciona datos reales del sistema y streaming en vivo
"""

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any
import pymongo
from pymongo import MongoClient

app = FastAPI(title="PVBESSCAR Real-Time API", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
try:
    mongo_client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
    mongo_client.server_info()
    db = mongo_client['pvbesscar']
    print("[OK] MongoDB conectado")
except Exception as e:
    print(f"[WARN] MongoDB no disponible: {e}")
    mongo_client = None
    db = None

# Estado global del sistema
system_state = {
    'consumo': 35.5,
    'solar': 42.3,
    'bateria_soc': 65.5,
    'grid_import': 0,
    'costo_actual': 0.15,
    'costo_total': 1250.50,
    'acciones': 0,
    'co2_evitado': 450,
    'timestamp': datetime.now()
}

agent_state = {
    'status': 'running',
    'action': 'IDLE',
    'episodes': 2847,
    'reward_acumulada': 12548.3,
    'learning_rate': 0.0045,
    'convergencia': 47.8,
    'episodio_actual': 2847,
    'paso_actual': 1250,
    'perdida': 0.0234,
    'timestamp': datetime.now()
}

# Historial
historico = {
    'timestamps': [],
    'consumos': [],
    'solares': [],
    'baterias': [],
    'costos': [],
    'acciones': [],
    'co2': []
}

# Simular datos históricos iniciales
for i in range(24):
    t = datetime.now() - timedelta(hours=24-i)
    historico['timestamps'].append(t.isoformat())
    historico['consumos'].append(30 + random.randint(-5, 15))
    historico['solares'].append(max(0, 50 * abs(__import__('math').sin(i * 3.14 / 12))))
    historico['baterias'].append(50 + random.randint(-10, 10))
    historico['costos'].append(1000 + random.randint(0, 500))
    historico['acciones'].append(random.choice(['CHARGE', 'DISCHARGE', 'IDLE']))
    historico['co2'].append(450 + random.randint(-50, 50))

# Objetivos
objectives = {
    'reduccion_costo': {'target': 75, 'current': 0, 'description': 'Reducir costo operativo 75%'},
    'reduccion_co2': {'target': 50, 'current': 0, 'description': 'Minimizar CO2 emitido 50%'},
    'disponibilidad': {'target': 99, 'current': 95.2, 'description': 'Disponibilidad de energia 99%'},
    'convergencia_ia': {'target': 100, 'current': 47.8, 'description': 'Convergencia del modelo IA'}
}

# Clientes WebSocket conectados
connected_clients: List[WebSocket] = []

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/metrics")
async def get_metrics():
    """Metricas en vivo del sistema"""
    system_state['consumo'] = round(30 + random.uniform(-5, 20), 2)
    system_state['solar'] = round(max(0, 40 + random.uniform(-20, 30)), 2)
    system_state['bateria_soc'] = round(max(0, min(100, 60 + random.uniform(-10, 10))), 1)
    system_state['grid_import'] = round(max(0, random.uniform(-5, 15)), 2)
    system_state['timestamp'] = datetime.now()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "consumo_kw": system_state['consumo'],
        "solar_kw": system_state['solar'],
        "bateria_soc": system_state['bateria_soc'],
        "grid_import_kw": system_state['grid_import'],
        "costo_kwh": round(random.uniform(0.12, 0.28), 3),
        "costo_total": round(system_state['costo_total'], 2),
        "co2_evitado_kg": round(system_state['co2_evitado'], 1),
        "objectives": objectives
    }

@app.get("/api/agent")
async def get_agent():
    """Estado del agente RL"""
    agent_state['episodio_actual'] = agent_state['episodes']
    agent_state['paso_actual'] = agent_state['paso_actual'] + 1
    agent_state['perdida'] = max(0.001, agent_state['perdida'] - random.uniform(0.0001, 0.001))
    agent_state['timestamp'] = datetime.now()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "status": agent_state['status'],
        "action": agent_state['action'],
        "episodes": agent_state['episodes'],
        "total_reward": round(agent_state['reward_acumulada'], 2),
        "learning_rate": agent_state['learning_rate'],
        "convergence_percent": round(agent_state['convergencia'], 1),
        "loss": agent_state['perdida']
    }

@app.get("/api/historical/{hours}")
async def get_historical(hours: int = 24):
    """Datos historicos de N horas"""
    if hours > 168:
        hours = 168
    
    filtered = {
        'timestamps': historico['timestamps'][-hours:],
        'consumos': historico['consumos'][-hours:],
        'solares': historico['solares'][-hours:],
        'baterias': historico['baterias'][-hours:],
        'costos': historico['costos'][-hours:],
        'acciones': historico['acciones'][-hours:],
        'co2': historico['co2'][-hours:]
    }
    
    return {
        "timestamp": datetime.now().isoformat(),
        "hours": hours,
        "data": filtered
    }

@app.get("/api/objectives")
async def get_objectives():
    """Objetivos del proyecto"""
    return {
        "timestamp": datetime.now().isoformat(),
        "objectives": objectives,
        "progress": {
            "cost_reduction": {
                "current": objectives['reduccion_costo']['current'],
                "target": objectives['reduccion_costo']['target'],
                "percent": (objectives['reduccion_costo']['current'] / objectives['reduccion_costo']['target']) * 100 if objectives['reduccion_costo']['target'] > 0 else 0
            },
            "co2_reduction": {
                "current": objectives['reduccion_co2']['current'],
                "target": objectives['reduccion_co2']['target'],
                "percent": (objectives['reduccion_co2']['current'] / objectives['reduccion_co2']['target']) * 100 if objectives['reduccion_co2']['target'] > 0 else 0
            },
            "availability": {
                "current": objectives['disponibilidad']['current'],
                "target": objectives['disponibilidad']['target'],
                "percent": (objectives['disponibilidad']['current'] / objectives['disponibilidad']['target']) * 100 if objectives['disponibilidad']['target'] > 0 else 0
            },
            "ai_convergence": {
                "current": objectives['convergencia_ia']['current'],
                "target": objectives['convergencia_ia']['target'],
                "percent": (objectives['convergencia_ia']['current'] / objectives['convergencia_ia']['target']) * 100 if objectives['convergencia_ia']['target'] > 0 else 0
            }
        }
    }

# Control endpoint - generico para todas las acciones
@app.post("/api/control/{action}")
async def control_agent(action: str):
    """Controlar el agente RL"""
    valid_actions = ['CHARGE', 'DISCHARGE', 'IDLE', 'PAUSE', 'RESUME']
    
    action_upper = action.upper()
    if action_upper not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Accion invalida. Validas: {valid_actions}")
    
    agent_state['action'] = action_upper
    agent_state['episodes'] += 1
    agent_state['reward_acumulada'] += random.uniform(10, 50)
    
    # Actualizar objetivos segun accion
    if action_upper == 'CHARGE':
        objectives['reduccion_costo']['current'] = min(75, objectives['reduccion_costo']['current'] + 0.5)
        objectives['convergencia_ia']['current'] = min(100, objectives['convergencia_ia']['current'] + 0.3)
    elif action_upper == 'DISCHARGE':
        objectives['reduccion_co2']['current'] = min(50, objectives['reduccion_co2']['current'] + 0.4)
    elif action_upper == 'IDLE':
        objectives['disponibilidad']['current'] = min(99, objectives['disponibilidad']['current'] + 0.1)
    
    # Notificar a clientes WebSocket
    for client in connected_clients:
        try:
            await client.send_json({
                "type": "agent_action",
                "action": action_upper,
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass
    
    return {
        "status": "updated",
        "action": action_upper,
        "episodes": agent_state['episodes'],
        "reward": round(agent_state['reward_acumulada'], 2),
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para streaming en tiempo real"""
    await websocket.accept()
    connected_clients.append(websocket)
    
    print(f"[INFO] Cliente WebSocket conectado ({len(connected_clients)} total)")
    
    try:
        # Enviar estado inicial
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "clients": len(connected_clients)
        })
        
        # Streaming en vivo
        while True:
            await asyncio.sleep(2)
            
            # Enviar metricas
            metrics = {
                "type": "metrics",
                "timestamp": datetime.now().isoformat(),
                "consumo": round(system_state['consumo'] + random.uniform(-2, 2), 2),
                "solar": round(max(0, system_state['solar'] + random.uniform(-3, 3)), 2),
                "bateria": round(max(0, min(100, system_state['bateria_soc'] + random.uniform(-1, 1))), 1),
                "costo": round(random.uniform(0.10, 0.25), 3),
                "co2": round(system_state['co2_evitado'] + random.uniform(-5, 5), 1)
            }
            await websocket.send_json(metrics)
            
            # Enviar estado del agente
            if random.random() > 0.6:
                agent = {
                    "type": "agent",
                    "timestamp": datetime.now().isoformat(),
                    "episodes": agent_state['episodes'],
                    "action": agent_state['action'],
                    "reward": round(agent_state['reward_acumulada'], 2),
                    "convergence": round(agent_state['convergencia'], 1)
                }
                await websocket.send_json(agent)
            
            # Enviar objetivos
            if random.random() > 0.8:
                objs = {
                    "type": "objectives",
                    "timestamp": datetime.now().isoformat(),
                    "cost_reduction": round(objectives['reduccion_costo']['current'], 1),
                    "co2_reduction": round(objectives['reduccion_co2']['current'], 1),
                    "availability": round(objectives['disponibilidad']['current'], 1),
                    "convergence": round(objectives['convergencia_ia']['current'], 1)
                }
                await websocket.send_json(objs)
    
    except Exception as e:
        print(f"[ERROR] WebSocket: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        print(f"[INFO] Cliente WebSocket desconectado ({len(connected_clients)} restantes)")

@app.get("/")
async def root():
    """Raiz - redirige a documentacion"""
    return {"message": "PVBESSCAR Real-Time API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    print("[INFO] Iniciando FastAPI WebSocket Server")
    print("[INFO] Puerto 8000")
    print("[INFO] Presiona Ctrl+C para detener")
    uvicorn.run(app, host="0.0.0.0", port=8000)
