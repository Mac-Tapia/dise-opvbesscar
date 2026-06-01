#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fastapi_websocket_server.py
API REST + WebSocket para despliegue operativo del agente A2C — pvbesscar.

Arquitectura:
  - FastAPI (REST + WebSocket)
  - MongoDB (persistencia de episodios y métricas)
  - Auth: API Key por header X-API-Key
  - CORS restringido a orígenes configurados
  - Rate limiting por IP (slowapi)

Endpoints:
  GET  /health                — estado del servicio y modelo
  GET  /model/status          — info del checkpoint cargado
  POST /simulate              — ejecuta 1 episodio completo determinista
  GET  /metrics               — métricas agregadas históricas (MongoDB)
  GET  /history               — historial de episodios paginado
  WS   /ws/realtime           — stream step-by-step en tiempo real

Variables de entorno:
  API_KEY           — clave de acceso (requerida)
  MONGODB_URL       — mongodb://host:27017 (default: localhost)
  MONGODB_DB        — nombre de la base de datos (default: pvbesscar)
  CHECKPOINT_PATH   — ruta al .zip A2C (default: checkpoints/A2C_CityLearn/a2c_final)
  VECNORM_PATH      — ruta al .pkl VecNormalize (auto-detectado si vacío)
  CORS_ORIGINS      — orígenes permitidos separados por coma (default: *)
  MAX_CONCURRENT    — máx. simulaciones simultáneas (default: 2)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
from fastapi import (
    Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect,
    status, Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security.api_key import APIKeyHeader
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pvbesscar.api")

# ─── Configuración desde variables de entorno ─────────────────────────────────

API_KEY_VALUE    = os.getenv("API_KEY", "")
MONGODB_URL      = os.getenv("MONGODB_URL",     "mongodb://localhost:27017")
MONGODB_DB       = os.getenv("MONGODB_DB",      "pvbesscar")
CHECKPOINT_PATH  = os.getenv("CHECKPOINT_PATH", str(ROOT / "checkpoints/A2C_CityLearn/a2c_final"))
VECNORM_PATH     = os.getenv("VECNORM_PATH",    "")
CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS",   "*")
MAX_CONCURRENT   = int(os.getenv("MAX_CONCURRENT", "2"))

CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()] or ["*"]
CO2_FACTOR   = 0.4521
F0_REFERENCE = 7_053_999.0

# ─── Estado global (cargado una sola vez en startup) ──────────────────────────

class AppState:
    model        = None
    vec_env      = None
    base_env     = None
    db           = None
    ready        = False
    checkpoint   = ""
    obs_dim      = 19
    semaphore: asyncio.Semaphore | None = None
    load_error   = ""

state = AppState()


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=" * 60)
    log.info("PVBESSCAR API — Iniciando")
    log.info("Checkpoint: %s", CHECKPOINT_PATH)
    log.info("MongoDB: %s / %s", MONGODB_URL, MONGODB_DB)
    log.info("=" * 60)

    state.semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # MongoDB
    try:
        client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        state.db = client[MONGODB_DB]
        await state.db["episodes"].create_index("run_id", unique=True)
        await state.db["episodes"].create_index("timestamp")
        log.info("MongoDB conectado: %s/%s", MONGODB_URL, MONGODB_DB)
    except Exception as exc:
        log.warning("MongoDB no disponible: %s — operando sin persistencia", exc)
        state.db = None

    # Cargar modelo A2C (bloqueante, solo en startup)
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load_model_sync)
        state.ready = True
        log.info("Modelo A2C listo — obs_dim=%d", state.obs_dim)
    except Exception as exc:
        state.load_error = str(exc)
        log.error("Error cargando modelo: %s", exc)

    yield

    log.info("Cerrando pvbesscar API")


def _load_model_sync() -> None:
    """Carga el modelo en hilo separado (no bloquea el event loop)."""
    from stable_baselines3 import A2C
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

    ckpt = Path(CHECKPOINT_PATH)
    if not ckpt.suffix:
        ckpt = ckpt.with_suffix(".zip")
    if not ckpt.exists():
        raise FileNotFoundError(f"Checkpoint no encontrado: {ckpt}")

    state.model     = A2C.load(str(ckpt.with_suffix("")))
    state.checkpoint = str(ckpt)
    state.obs_dim   = int(state.model.observation_space.shape[0])

    # Entorno
    from citylearnv2.env_factory import create_iquitos_env_for_sb3
    base_env = create_iquitos_env_for_sb3()
    state.base_env = base_env

    # VecNormalize
    pkl = VECNORM_PATH or _autodetect_vecnorm(ckpt.parent)
    if pkl and Path(pkl).exists():
        vec_env = DummyVecEnv([lambda: base_env])
        vec_env = VecNormalize.load(pkl, vec_env)
        vec_env.training = False
        vec_env.norm_reward = False
        state.vec_env = vec_env
        log.info("VecNormalize cargado: %s", pkl)
    else:
        state.vec_env = DummyVecEnv([lambda: base_env])
        log.warning("VecNormalize no encontrado — obs sin normalizar")


def _autodetect_vecnorm(ckpt_dir: Path) -> str | None:
    for name in ["vecnormalize.pkl", "a2c_vecnormalize_438000_steps.pkl"]:
        p = ckpt_dir / name
        if p.exists():
            return str(p)
    return None


# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="pvbesscar — A2C Operational API",
    description=(
        "API operativa del agente A2C seleccionado para optimización de carga EV "
        "con solar PV + BESS en la red aislada de Iquitos, Perú. OE3 — obs_dim=19."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type", "Authorization"],
)


# ─── Auth ─────────────────────────────────────────────────────────────────────

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str | None = Depends(api_key_header)) -> str:
    if not API_KEY_VALUE:
        return "no-auth"
    if api_key != API_KEY_VALUE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o ausente",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


# ─── Modelos Pydantic ─────────────────────────────────────────────────────────

class SimulateRequest(BaseModel):
    episodes: int = Field(default=1, ge=1, le=10, description="Número de episodios (1-10)")
    deterministic: bool = Field(default=True, description="Inferencia determinista vs estocástica")
    label: Optional[str] = Field(default=None, max_length=64, description="Etiqueta para la corrida")


class EpisodeResult(BaseModel):
    run_id:               str
    episode:              int
    timestamp:            str
    steps:                int
    elapsed_s:            float
    total_reward:         float
    co2_total_avoided_kg: float
    co2_f2_residual_kg_yr: float
    co2_reduction_vs_f0_pct: float
    ev_motos_kwh:         float
    ev_mototaxis_kwh:     float
    ev_total_kwh:         float
    grid_import_kwh:      float
    bess_discharge_kwh:   float
    cost_total_soles:     float


class SimulateResponse(BaseModel):
    run_id:         str
    agent:          str
    obs_dim:        int
    episodes:       int
    mean_co2_avoided_kg:    float
    mean_f2_kg_yr:          float
    mean_reduction_pct:     float
    mean_reward:            float
    mean_ev_total_kwh:      float
    mean_cost_total_soles:  float
    detail:                 list[EpisodeResult]


# ─── Lógica de simulación ─────────────────────────────────────────────────────

TARIFA_HP  = 0.46
TARIFA_HFP = 0.29

def _run_episode_sync(ep_num: int, deterministic: bool) -> dict[str, Any]:
    """Ejecuta 1 episodio completo. Llamado desde hilo executor."""
    obs = state.vec_env.reset()
    done = False
    step = 0
    t0   = time.time()

    co2_direct = co2_indirect = ev_motos = ev_mototaxis = 0.0
    grid_kwh = bess_kwh = solar_kwh = cost_hp = cost_hfp = total_reward = 0.0

    while not done:
        action, _ = state.model.predict(obs, deterministic=deterministic)
        obs, reward, done_arr, info = state.vec_env.step(action)
        done = bool(done_arr[0]) if hasattr(done_arr, "__len__") else bool(done_arr)
        r    = float(reward[0]) if hasattr(reward, "__len__") else float(reward)
        total_reward += r

        if info:
            i = info[0] if isinstance(info, (list, tuple)) else info
            co2_direct   += float(i.get("co2_direct_kg",   0.0))
            co2_indirect += float(i.get("co2_indirect_kg", 0.0))
            ev_motos     += float(i.get("ev_motos_kwh",    0.0))
            ev_mototaxis += float(i.get("ev_mototaxis_kwh",0.0))
            g_kwh         = float(i.get("grid_import_kwh", 0.0))
            grid_kwh     += g_kwh
            bess_kwh     += float(i.get("bess_discharge_kwh", 0.0))
            solar_kwh    += float(i.get("solar_kwh",       0.0))
            hour = step % 24
            if 18 <= hour < 23:
                cost_hp  += g_kwh * TARIFA_HP
            else:
                cost_hfp += g_kwh * TARIFA_HFP
        step += 1

    co2_total = co2_direct + co2_indirect
    return {
        "episode":               ep_num,
        "timestamp":             datetime.now(timezone.utc).isoformat(),
        "steps":                 step,
        "elapsed_s":             round(time.time() - t0, 2),
        "total_reward":          round(total_reward, 4),
        "co2_direct_kg":         round(co2_direct,    2),
        "co2_indirect_kg":       round(co2_indirect,  2),
        "co2_total_avoided_kg":  round(co2_total,     2),
        "co2_f2_residual_kg_yr": round(F0_REFERENCE - co2_total, 2),
        "co2_reduction_vs_f0_pct": round(co2_total / F0_REFERENCE * 100, 4),
        "ev_motos_kwh":          round(ev_motos,      2),
        "ev_mototaxis_kwh":      round(ev_mototaxis,  2),
        "ev_total_kwh":          round(ev_motos + ev_mototaxis, 2),
        "grid_import_kwh":       round(grid_kwh,      2),
        "bess_discharge_kwh":    round(bess_kwh,      2),
        "solar_kwh":             round(solar_kwh,     2),
        "cost_hp_soles":         round(cost_hp,       2),
        "cost_hfp_soles":        round(cost_hfp,      2),
        "cost_total_soles":      round(cost_hp + cost_hfp, 2),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Sistema"])
async def health():
    """Estado del servicio y del modelo A2C."""
    return {
        "status":    "ok" if state.ready else "degraded",
        "model_ready": state.ready,
        "load_error": state.load_error or None,
        "checkpoint": state.checkpoint,
        "obs_dim":   state.obs_dim,
        "mongodb":   state.db is not None,
        "utc":       datetime.now(timezone.utc).isoformat(),
    }


@app.get("/model/status", tags=["Modelo"])
async def model_status(_: str = Depends(verify_api_key)):
    """Información detallada del modelo cargado."""
    if not state.ready:
        raise HTTPException(503, detail=f"Modelo no disponible: {state.load_error}")
    return {
        "agent":           "A2C",
        "checkpoint":      state.checkpoint,
        "obs_dim":         state.obs_dim,
        "action_dim":      3,
        "action_labels":   ["bess_action [-1,1]", "ev_motos_frac [0,1]", "ev_mototaxis_frac [0,1]"],
        "reward_version":  "CO2_DUAL_FOCUS v8.1",
        "co2_factor":      CO2_FACTOR,
        "f0_reference_kg": F0_REFERENCE,
        "location":        "Iquitos, Peru — red aislada",
        "system": {
            "solar_kwp_dc":    4162,
            "solar_kwh_year":  5_819_332,
            "bess_kwh":        2000,
            "bess_kw":         400,
            "chargers":        19,
            "sockets":         38,
            "daily_motos":     270,
            "daily_mototaxis": 39,
        },
    }


@app.post("/simulate", response_model=SimulateResponse, tags=["Inferencia"])
async def simulate(
    req: SimulateRequest,
    _: str = Depends(verify_api_key),
):
    """Ejecuta N episodios de inferencia determinista con el agente A2C."""
    if not state.ready:
        raise HTTPException(503, detail=f"Modelo no disponible: {state.load_error}")

    async with state.semaphore:
        run_id  = str(uuid.uuid4())
        loop    = asyncio.get_event_loop()
        results = []

        for ep in range(1, req.episodes + 1):
            log.info("simulate run_id=%s ep=%d/%d", run_id, ep, req.episodes)
            result = await loop.run_in_executor(
                None, _run_episode_sync, ep, req.deterministic
            )
            result["run_id"] = run_id
            result["label"]  = req.label or ""
            results.append(result)

            if state.db is not None:
                try:
                    doc = {**result, "agent": "A2C", "obs_dim": state.obs_dim}
                    await state.db["episodes"].insert_one(doc)
                except Exception as exc:
                    log.warning("MongoDB insert error: %s", exc)

        arr = lambda k: [r[k] for r in results]
        resp = SimulateResponse(
            run_id=run_id,
            agent="A2C",
            obs_dim=state.obs_dim,
            episodes=req.episodes,
            mean_co2_avoided_kg=   round(float(np.mean(arr("co2_total_avoided_kg"))),  2),
            mean_f2_kg_yr=         round(float(np.mean(arr("co2_f2_residual_kg_yr"))), 2),
            mean_reduction_pct=    round(float(np.mean(arr("co2_reduction_vs_f0_pct"))), 4),
            mean_reward=           round(float(np.mean(arr("total_reward"))),           4),
            mean_ev_total_kwh=     round(float(np.mean(arr("ev_total_kwh"))),           2),
            mean_cost_total_soles= round(float(np.mean(arr("cost_total_soles"))),       2),
            detail=[EpisodeResult(**{k: r[k] for k in EpisodeResult.__fields__}) for r in results],
        )
        return resp


@app.get("/metrics", tags=["Métricas"])
async def metrics(_: str = Depends(verify_api_key)):
    """Métricas agregadas de todos los episodios en MongoDB."""
    if state.db is None:
        raise HTTPException(503, detail="MongoDB no disponible")
    pipeline = [
        {"$group": {
            "_id": None,
            "total_episodes":          {"$sum": 1},
            "mean_co2_avoided_kg":     {"$avg": "$co2_total_avoided_kg"},
            "mean_f2_kg_yr":           {"$avg": "$co2_f2_residual_kg_yr"},
            "mean_reduction_pct":      {"$avg": "$co2_reduction_vs_f0_pct"},
            "mean_reward":             {"$avg": "$total_reward"},
            "mean_ev_total_kwh":       {"$avg": "$ev_total_kwh"},
            "mean_cost_total_soles":   {"$avg": "$cost_total_soles"},
            "sum_co2_avoided_kg":      {"$sum": "$co2_total_avoided_kg"},
            "sum_ev_total_kwh":        {"$sum": "$ev_total_kwh"},
        }}
    ]
    cursor = state.db["episodes"].aggregate(pipeline)
    docs = await cursor.to_list(length=1)
    if not docs:
        return {"total_episodes": 0, "message": "Sin episodios registrados"}
    d = docs[0]
    d.pop("_id", None)
    return {k: round(v, 4) if isinstance(v, float) else v for k, v in d.items()}


@app.get("/history", tags=["Métricas"])
async def history(
    page: int = 1,
    per_page: int = 20,
    _: str = Depends(verify_api_key),
):
    """Historial de episodios paginado (más reciente primero)."""
    if state.db is None:
        raise HTTPException(503, detail="MongoDB no disponible")
    per_page = min(per_page, 100)
    skip = (page - 1) * per_page
    cursor = state.db["episodes"].find(
        {}, {"_id": 0, "co2_total_avoided_kg": 1, "co2_f2_residual_kg_yr": 1,
             "co2_reduction_vs_f0_pct": 1, "total_reward": 1, "ev_total_kwh": 1,
             "cost_total_soles": 1, "timestamp": 1, "run_id": 1, "label": 1}
    ).sort("timestamp", -1).skip(skip).limit(per_page)
    docs = await cursor.to_list(length=per_page)
    total = await state.db["episodes"].count_documents({})
    return {"page": page, "per_page": per_page, "total": total, "results": docs}


# ─── WebSocket — stream step-a-step ──────────────────────────────────────────

@app.websocket("/ws/realtime")
async def ws_realtime(websocket: WebSocket):
    """
    WebSocket para stream en tiempo real de cada step del agente.
    Protocolo:
      Cliente envía: {"api_key": "...", "deterministic": true}
      Servidor envía: {"type": "step", "step": N, "action": [...], "reward": R, ...}
                      {"type": "done", "summary": {...}}
                      {"type": "error", "message": "..."}
    """
    await websocket.accept()
    try:
        init = await websocket.receive_json()
        if API_KEY_VALUE and init.get("api_key") != API_KEY_VALUE:
            await websocket.send_json({"type": "error", "message": "API Key inválida"})
            await websocket.close(code=4401)
            return

        if not state.ready:
            await websocket.send_json({"type": "error", "message": "Modelo no disponible"})
            await websocket.close(code=4503)
            return

        deterministic = bool(init.get("deterministic", True))
        loop  = asyncio.get_event_loop()
        obs   = await loop.run_in_executor(None, lambda: state.vec_env.reset())
        done  = False
        step  = 0
        total_reward = 0.0
        co2_total = 0.0

        while not done:
            action, _ = await loop.run_in_executor(
                None, lambda: state.model.predict(obs, deterministic=deterministic)
            )
            obs, reward, done_arr, info = await loop.run_in_executor(
                None, lambda: state.vec_env.step(action)
            )
            done = bool(done_arr[0]) if hasattr(done_arr, "__len__") else bool(done_arr)
            r    = float(reward[0]) if hasattr(reward, "__len__") else float(reward)
            total_reward += r
            i = info[0] if (info and isinstance(info, (list, tuple))) else (info or {})
            co2_step = float(i.get("co2_direct_kg", 0)) + float(i.get("co2_indirect_kg", 0))
            co2_total += co2_step

            msg = {
                "type":    "step",
                "step":    step,
                "action":  action[0].tolist() if hasattr(action[0], "tolist") else list(action[0]),
                "reward":  round(r, 4),
                "co2_kg":  round(co2_step, 4),
                "ev_kwh":  round(float(i.get("ev_motos_kwh", 0)) + float(i.get("ev_mototaxis_kwh", 0)), 4),
                "bess_kwh": round(float(i.get("bess_discharge_kwh", 0)), 4),
                "grid_kwh": round(float(i.get("grid_import_kwh",    0)), 4),
            }
            await websocket.send_json(msg)
            step += 1
            await asyncio.sleep(0)  # yield al event loop

        await websocket.send_json({
            "type": "done",
            "summary": {
                "steps":               step,
                "total_reward":        round(total_reward, 4),
                "co2_total_avoided_kg": round(co2_total, 2),
                "co2_f2_kg_yr":        round(F0_REFERENCE - co2_total, 2),
                "reduction_pct":       round(co2_total / F0_REFERENCE * 100, 4),
            },
        })

    except WebSocketDisconnect:
        log.info("WebSocket cliente desconectado en step %d", step if 'step' in dir() else 0)
    except Exception as exc:
        log.error("WebSocket error: %s", exc)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "fastapi_websocket_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
        workers=1,
        log_level="info",
    )
