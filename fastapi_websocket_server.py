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
from fastapi.responses import HTMLResponse, JSONResponse
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
OBJECTIVE_WEIGHTS: dict[str, float] = {
    "co2_directa": 0.20,
    "co2_indirecta_grid": 0.30,
    "servicio_ev_sin_deuda": 0.35,
    "bess_carga_solar": 0.07,
    "autoconsumo_solar": 0.04,
    "estabilidad_grid": 0.02,
    "costo_osinergmin": 0.02,
}


def _mask_url_credentials(url: str) -> str:
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    _, host = rest.split("@", 1)
    return f"{scheme}://***:***@{host}"

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


def _install_numpy_pickle_compat() -> None:
    """Map NumPy 2 pickle module paths when running with NumPy 1.x."""
    try:
        import numpy.core as np_core
        import numpy.core.numeric as np_numeric
        import numpy.core.multiarray as np_multiarray
        import numpy.core.umath as np_umath
        import numpy.core._multiarray_umath as np_multiarray_umath

        if not hasattr(np, "_core"):
            setattr(np, "_core", np_core)
        sys.modules.setdefault("numpy._core", np_core)
        sys.modules.setdefault("numpy._core.numeric", np_numeric)
        sys.modules.setdefault("numpy._core.multiarray", np_multiarray)
        sys.modules.setdefault("numpy._core.umath", np_umath)
        sys.modules.setdefault("numpy._core._multiarray_umath", np_multiarray_umath)
    except Exception as exc:
        log.debug("No se pudo instalar compatibilidad NumPy pickle: %s", exc)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("=" * 60)
    log.info("PVBESSCAR API — Iniciando")
    log.info("Checkpoint: %s", CHECKPOINT_PATH)
    log.info("MongoDB: %s / %s", _mask_url_credentials(MONGODB_URL), MONGODB_DB)
    log.info("=" * 60)

    state.semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # MongoDB
    try:
        client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        state.db = client[MONGODB_DB]
        await state.db["episodes"].create_index("run_id", unique=True, sparse=True)
        await state.db["episodes"].create_index([("timestamp", -1)])
        log.info("MongoDB conectado: %s/%s", _mask_url_credentials(MONGODB_URL), MONGODB_DB)
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
    _install_numpy_pickle_compat()

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
    include_trace: bool = Field(
        default=False,
        description="Incluye traza horaria para graficar BESS, tomas, solar, balance y CO2.",
    )


class EpisodeResult(BaseModel):
    run_id:               str
    episode:              int
    timestamp:            str
    steps:                int
    elapsed_s:            float
    total_reward:         float
    co2_baseline_kg:      float
    co2_control_kg:       float
    co2_direct_kg:        float
    co2_indirect_kg:      float
    co2_total_avoided_kg: float
    co2_f2_residual_kg_yr: float
    co2_reduction_vs_f0_pct: float
    co2_f6a_solar_ev_kg:       float
    co2_f6b_solar_mall_kg:     float
    co2_f6c_solar_bess_kg:     float
    co2_f6d_solar_export_kg:   float
    co2_f6_solar_total_kg:     float
    co2_f7_bess_discharge_kg:  float
    ev_motos_kwh:         float
    ev_mototaxis_kwh:     float
    ev_total_kwh:         float
    ev_demand_kwh:        float
    ev_unserved_kwh:      float
    debt_violations:      float
    mean_active_sockets:  float
    max_active_sockets:   float
    solar_kwh:            float
    mall_kwh:             float
    grid_import_kwh:      float
    grid_export_kwh:      float
    bess_discharge_kwh:   float
    bess_charge_kwh:      float
    bess_soc_min:         float
    bess_soc_max:         float
    bess_soc_final:       float
    dispatch_pv_to_ev_kwh:   float
    dispatch_bess_to_ev_kwh: float
    dispatch_grid_to_ev_kwh: float
    cost_total_soles:     float
    cost_mecanismo_comp_soles: float
    ahorro_social_total_soles: float
    cost_usd:             float
    mean_bess_action:     float
    mean_ev_motos_frac:   float
    mean_ev_mototaxis_frac: float
    trace:                Optional[list[dict[str, float]]] = None


class SimulateResponse(BaseModel):
    run_id:         str
    agent:          str
    obs_dim:        int
    episodes:       int
    objective_weights:      dict[str, float]
    mean_co2_avoided_kg:    float
    mean_co2_baseline_kg:   float
    mean_co2_control_kg:    float
    mean_co2_direct_kg:     float
    mean_co2_indirect_kg:   float
    mean_f2_kg_yr:          float
    mean_reduction_pct:     float
    mean_reward:            float
    mean_ev_total_kwh:      float
    mean_ev_unserved_kwh:   float
    mean_debt_violations:   float
    mean_grid_import_kwh:   float
    mean_grid_export_kwh:   float
    mean_solar_kwh:         float
    mean_bess_discharge_kwh: float
    mean_cost_total_soles:  float
    detail:                 list[EpisodeResult]


# ─── Lógica de simulación ─────────────────────────────────────────────────────

TARIFA_HP  = 0.46
TARIFA_HFP = 0.29


def _info_float(info: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = info.get(key, default)
    try:
        if isinstance(value, np.ndarray):
            return float(np.asarray(value, dtype=np.float64).sum())
        return float(value)
    except (TypeError, ValueError):
        return default


def _step_snapshot(info: dict[str, Any], reward: float, step: int) -> dict[str, float]:
    ev_motos = _info_float(info, "ev_motos_actual_kwh")
    ev_mototaxis = _info_float(info, "ev_mototaxis_actual_kwh")
    ev_motos_demand = _info_float(info, "ev_motos_demand_kwh")
    ev_mototaxis_demand = _info_float(info, "ev_mototaxis_demand_kwh")
    active_sockets = (
        _info_float(info, "ev_motos_active_sockets")
        + _info_float(info, "ev_mototaxis_active_sockets")
    )
    ev_total = ev_motos + ev_mototaxis
    ev_demand = ev_motos_demand + ev_mototaxis_demand
    ev_unserved = max(ev_demand - ev_total, 0.0)
    co2_direct = _info_float(info, "co2_reduccion_directa_kg")
    co2_indirect = _info_float(info, "co2_reduccion_indirecta_kg")

    return {
        "step": float(step),
        "timestep": _info_float(info, "timestep", float(step)),
        "hour": float(int(_info_float(info, "timestep", float(step))) % 24),
        "reward": reward,
        "co2_baseline_kg": _info_float(info, "co2_total_baseline_kg"),
        "co2_control_kg": _info_float(info, "co2_total_control_kg"),
        "co2_direct_kg": co2_direct,
        "co2_indirect_kg": co2_indirect,
        "co2_total_avoided_kg": co2_direct + co2_indirect,
        "co2_f6a_solar_ev_kg": _info_float(info, "co2_ctrl_reduc_solar_ev_kg"),
        "co2_f6b_solar_mall_kg": _info_float(info, "co2_ctrl_reduc_solar_mall_kg"),
        "co2_f6c_solar_bess_kg": _info_float(info, "co2_ctrl_reduc_solar_bess_kg"),
        "co2_f6d_solar_export_kg": _info_float(info, "co2_ctrl_reduc_solar_exp_kg"),
        "co2_f6_solar_total_kg": _info_float(info, "co2_ctrl_reduc_solar_total_kg"),
        "co2_f7_bess_discharge_kg": _info_float(info, "co2_ctrl_reduc_bess_desc_kg"),
        "ev_motos_kwh": ev_motos,
        "ev_mototaxis_kwh": ev_mototaxis,
        "ev_total_kwh": ev_total,
        "ev_demand_kwh": ev_demand,
        "ev_unserved_kwh": ev_unserved,
        "penalty_debt_frac": _info_float(info, "penalty_debt_frac"),
        "active_sockets": active_sockets,
        "solar_kwh": _info_float(info, "solar_generation_kwh"),
        "mall_kwh": _info_float(info, "mall_demand_kwh"),
        "grid_import_kwh": _info_float(info, "grid_import_kwh"),
        "grid_export_kwh": _info_float(info, "grid_export_kwh"),
        "bess_discharge_kwh": _info_float(info, "bess_discharge_kwh"),
        "bess_charge_kwh": _info_float(info, "bess_charge_kwh"),
        "bess_soc": _info_float(info, "bess_soc"),
        "bess_action": _info_float(info, "bess_action"),
        "ev_motos_frac": _info_float(info, "ev_motos_frac"),
        "ev_mototaxis_frac": _info_float(info, "ev_mototaxis_frac"),
        "dispatch_pv_to_ev_kwh": _info_float(info, "dispatch_pv_to_ev_kwh"),
        "dispatch_bess_to_ev_kwh": _info_float(info, "dispatch_bess_to_ev_kwh"),
        "dispatch_grid_to_ev_kwh": _info_float(info, "dispatch_grid_to_ev_kwh"),
        "cost_soles": _info_float(info, "cost_soles"),
        "cost_mecanismo_comp_soles": _info_float(info, "cost_mecanismo_comp_soles"),
        "ahorro_social_total_soles": _info_float(info, "ahorro_social_total_soles"),
        "cost_usd": _info_float(info, "cost_usd"),
    }


def _round_trace_row(row: dict[str, float]) -> dict[str, float]:
    rounded: dict[str, float] = {}
    for key, value in row.items():
        decimals = 4 if key in {"reward", "bess_soc", "bess_action", "ev_motos_frac", "ev_mototaxis_frac"} else 2
        rounded[key] = round(float(value), decimals)
    return rounded


def _episode_result_fields() -> list[str]:
    fields = getattr(EpisodeResult, "model_fields", None)
    if fields is None:
        fields = getattr(EpisodeResult, "__fields__")
    return list(fields)


def _run_episode_sync(ep_num: int, deterministic: bool, include_trace: bool = False) -> dict[str, Any]:
    """Ejecuta 1 episodio completo. Llamado desde hilo executor."""
    obs = state.vec_env.reset()
    done = False
    step = 0
    t0   = time.time()

    co2_baseline = co2_control = co2_direct = co2_indirect = 0.0
    co2_f6a = co2_f6b = co2_f6c = co2_f6d = co2_f6_total = co2_f7 = 0.0
    ev_motos = ev_mototaxis = ev_demand = ev_unserved = debt_violations = 0.0
    active_sockets_sum = max_active_sockets = 0.0
    grid_kwh = grid_export_kwh = bess_kwh = bess_charge_kwh = solar_kwh = mall_kwh = 0.0
    dispatch_pv_to_ev = dispatch_bess_to_ev = dispatch_grid_to_ev = 0.0
    cost_total = cost_mecanismo = ahorro_social = cost_usd = total_reward = 0.0
    bess_action_sum = ev_motos_frac_sum = ev_mototaxis_frac_sum = 0.0
    bess_soc_min = 1.0
    bess_soc_max = 0.0
    bess_soc_final = 0.0
    trace: list[dict[str, float]] = []

    while not done:
        action, _ = state.model.predict(obs, deterministic=deterministic)
        obs, reward, done_arr, info = state.vec_env.step(action)
        done = bool(done_arr[0]) if hasattr(done_arr, "__len__") else bool(done_arr)
        r    = float(reward[0]) if hasattr(reward, "__len__") else float(reward)
        total_reward += r

        if info:
            i = info[0] if isinstance(info, (list, tuple)) else info
            snap = _step_snapshot(i, r, step)
            co2_baseline += snap["co2_baseline_kg"]
            co2_control += snap["co2_control_kg"]
            co2_direct += snap["co2_direct_kg"]
            co2_indirect += snap["co2_indirect_kg"]
            co2_f6a += snap["co2_f6a_solar_ev_kg"]
            co2_f6b += snap["co2_f6b_solar_mall_kg"]
            co2_f6c += snap["co2_f6c_solar_bess_kg"]
            co2_f6d += snap["co2_f6d_solar_export_kg"]
            co2_f6_total += snap["co2_f6_solar_total_kg"]
            co2_f7 += snap["co2_f7_bess_discharge_kg"]
            ev_motos += snap["ev_motos_kwh"]
            ev_mototaxis += snap["ev_mototaxis_kwh"]
            ev_demand += snap["ev_demand_kwh"]
            ev_unserved += snap["ev_unserved_kwh"]
            debt_violations += 1.0 if snap["penalty_debt_frac"] > 1e-9 else 0.0
            active_sockets_sum += snap["active_sockets"]
            max_active_sockets = max(max_active_sockets, snap["active_sockets"])
            grid_kwh += snap["grid_import_kwh"]
            grid_export_kwh += snap["grid_export_kwh"]
            bess_kwh += snap["bess_discharge_kwh"]
            bess_charge_kwh += snap["bess_charge_kwh"]
            solar_kwh += snap["solar_kwh"]
            mall_kwh += snap["mall_kwh"]
            dispatch_pv_to_ev += snap["dispatch_pv_to_ev_kwh"]
            dispatch_bess_to_ev += snap["dispatch_bess_to_ev_kwh"]
            dispatch_grid_to_ev += snap["dispatch_grid_to_ev_kwh"]
            cost_total += snap["cost_soles"]
            cost_mecanismo += snap["cost_mecanismo_comp_soles"]
            ahorro_social += snap["ahorro_social_total_soles"]
            cost_usd += snap["cost_usd"]
            bess_action_sum += snap["bess_action"]
            ev_motos_frac_sum += snap["ev_motos_frac"]
            ev_mototaxis_frac_sum += snap["ev_mototaxis_frac"]
            bess_soc_final = snap["bess_soc"]
            bess_soc_min = min(bess_soc_min, snap["bess_soc"])
            bess_soc_max = max(bess_soc_max, snap["bess_soc"])
            if include_trace:
                trace.append(_round_trace_row(snap))
        step += 1

    co2_total = co2_direct + co2_indirect
    denom = max(step, 1)
    result: dict[str, Any] = {
        "episode":               ep_num,
        "timestamp":             datetime.now(timezone.utc).isoformat(),
        "steps":                 step,
        "elapsed_s":             round(time.time() - t0, 2),
        "total_reward":          round(total_reward, 4),
        "co2_baseline_kg":       round(co2_baseline, 2),
        "co2_control_kg":        round(co2_control, 2),
        "co2_direct_kg":         round(co2_direct,    2),
        "co2_indirect_kg":       round(co2_indirect,  2),
        "co2_total_avoided_kg":  round(co2_total,     2),
        "co2_f2_residual_kg_yr": round(F0_REFERENCE - co2_total, 2),
        "co2_reduction_vs_f0_pct": round(co2_total / F0_REFERENCE * 100, 4),
        "co2_f6a_solar_ev_kg":      round(co2_f6a, 2),
        "co2_f6b_solar_mall_kg":    round(co2_f6b, 2),
        "co2_f6c_solar_bess_kg":    round(co2_f6c, 2),
        "co2_f6d_solar_export_kg":  round(co2_f6d, 2),
        "co2_f6_solar_total_kg":    round(co2_f6_total, 2),
        "co2_f7_bess_discharge_kg": round(co2_f7, 2),
        "ev_motos_kwh":          round(ev_motos,      2),
        "ev_mototaxis_kwh":      round(ev_mototaxis,  2),
        "ev_total_kwh":          round(ev_motos + ev_mototaxis, 2),
        "ev_demand_kwh":         round(ev_demand, 2),
        "ev_unserved_kwh":       round(ev_unserved, 2),
        "debt_violations":       round(debt_violations, 2),
        "mean_active_sockets":   round(active_sockets_sum / denom, 2),
        "max_active_sockets":    round(max_active_sockets, 2),
        "solar_kwh":             round(solar_kwh,     2),
        "mall_kwh":              round(mall_kwh,      2),
        "grid_import_kwh":       round(grid_kwh,      2),
        "grid_export_kwh":       round(grid_export_kwh, 2),
        "bess_discharge_kwh":    round(bess_kwh,      2),
        "bess_charge_kwh":       round(bess_charge_kwh, 2),
        "bess_soc_min":          round(bess_soc_min, 4),
        "bess_soc_max":          round(bess_soc_max, 4),
        "bess_soc_final":        round(bess_soc_final, 4),
        "dispatch_pv_to_ev_kwh":   round(dispatch_pv_to_ev, 2),
        "dispatch_bess_to_ev_kwh": round(dispatch_bess_to_ev, 2),
        "dispatch_grid_to_ev_kwh": round(dispatch_grid_to_ev, 2),
        "cost_total_soles":      round(cost_total,       2),
        "cost_mecanismo_comp_soles": round(cost_mecanismo, 2),
        "ahorro_social_total_soles": round(ahorro_social, 2),
        "cost_usd":              round(cost_usd, 2),
        "mean_bess_action":      round(bess_action_sum / denom, 4),
        "mean_ev_motos_frac":    round(ev_motos_frac_sum / denom, 4),
        "mean_ev_mototaxis_frac": round(ev_mototaxis_frac_sum / denom, 4),
    }
    if include_trace:
        result["trace"] = trace
    return result


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
        "objective_weights": OBJECTIVE_WEIGHTS,
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
                None, _run_episode_sync, ep, req.deterministic, req.include_trace
            )
            result["run_id"] = run_id
            result["label"]  = req.label or ""
            results.append(result)

            if state.db is not None:
                try:
                    doc = {
                        **{k: v for k, v in result.items() if k != "trace"},
                        "trace_steps": len(result.get("trace", [])),
                        "agent": "A2C",
                        "obs_dim": state.obs_dim,
                    }
                    await state.db["episodes"].insert_one(doc)
                except Exception as exc:
                    log.warning("MongoDB insert error: %s", exc)

        arr = lambda k: [r[k] for r in results]
        resp = SimulateResponse(
            run_id=run_id,
            agent="A2C",
            obs_dim=state.obs_dim,
            episodes=req.episodes,
            objective_weights=OBJECTIVE_WEIGHTS,
            mean_co2_avoided_kg=   round(float(np.mean(arr("co2_total_avoided_kg"))),  2),
            mean_co2_baseline_kg=  round(float(np.mean(arr("co2_baseline_kg"))),       2),
            mean_co2_control_kg=   round(float(np.mean(arr("co2_control_kg"))),        2),
            mean_co2_direct_kg=    round(float(np.mean(arr("co2_direct_kg"))),         2),
            mean_co2_indirect_kg=  round(float(np.mean(arr("co2_indirect_kg"))),       2),
            mean_f2_kg_yr=         round(float(np.mean(arr("co2_f2_residual_kg_yr"))), 2),
            mean_reduction_pct=    round(float(np.mean(arr("co2_reduction_vs_f0_pct"))), 4),
            mean_reward=           round(float(np.mean(arr("total_reward"))),           4),
            mean_ev_total_kwh=     round(float(np.mean(arr("ev_total_kwh"))),           2),
            mean_ev_unserved_kwh=  round(float(np.mean(arr("ev_unserved_kwh"))),        2),
            mean_debt_violations=  round(float(np.mean(arr("debt_violations"))),        2),
            mean_grid_import_kwh=  round(float(np.mean(arr("grid_import_kwh"))),        2),
            mean_grid_export_kwh=  round(float(np.mean(arr("grid_export_kwh"))),        2),
            mean_solar_kwh=        round(float(np.mean(arr("solar_kwh"))),              2),
            mean_bess_discharge_kwh= round(float(np.mean(arr("bess_discharge_kwh"))),   2),
            mean_cost_total_soles= round(float(np.mean(arr("cost_total_soles"))),       2),
            detail=[
                EpisodeResult(**{k: r[k] for k in _episode_result_fields() if k in r})
                for r in results
            ],
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
            "mean_co2_baseline_kg":    {"$avg": "$co2_baseline_kg"},
            "mean_co2_control_kg":     {"$avg": "$co2_control_kg"},
            "mean_co2_direct_kg":      {"$avg": "$co2_direct_kg"},
            "mean_co2_indirect_kg":    {"$avg": "$co2_indirect_kg"},
            "mean_f2_kg_yr":           {"$avg": "$co2_f2_residual_kg_yr"},
            "mean_reduction_pct":      {"$avg": "$co2_reduction_vs_f0_pct"},
            "mean_reward":             {"$avg": "$total_reward"},
            "mean_ev_total_kwh":       {"$avg": "$ev_total_kwh"},
            "mean_ev_unserved_kwh":    {"$avg": "$ev_unserved_kwh"},
            "mean_debt_violations":    {"$avg": "$debt_violations"},
            "mean_grid_import_kwh":    {"$avg": "$grid_import_kwh"},
            "mean_grid_export_kwh":    {"$avg": "$grid_export_kwh"},
            "mean_solar_kwh":          {"$avg": "$solar_kwh"},
            "mean_bess_discharge_kwh": {"$avg": "$bess_discharge_kwh"},
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
             "co2_reduction_vs_f0_pct": 1, "co2_direct_kg": 1, "co2_indirect_kg": 1,
             "total_reward": 1, "ev_total_kwh": 1, "ev_unserved_kwh": 1,
             "debt_violations": 1, "grid_import_kwh": 1, "solar_kwh": 1,
             "bess_discharge_kwh": 1, "cost_total_soles": 1, "trace_steps": 1,
             "timestamp": 1, "run_id": 1, "label": 1}
    ).sort("timestamp", -1).skip(skip).limit(per_page)
    docs = await cursor.to_list(length=per_page)
    total = await state.db["episodes"].count_documents({})
    return {"page": page, "per_page": per_page, "total": total, "results": docs}


@app.get("/dashboard/realtime", response_class=HTMLResponse, tags=["Sistema"])
async def realtime_dashboard():
    """Dashboard local para observar una simulación en tiempo real por WebSocket."""
    return HTMLResponse("""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PVBESSCAR - Dashboard A2C tiempo real</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f9fb;
      --panel: #ffffff;
      --line: #d8dee4;
      --text: #17202a;
      --muted: #5d6975;
      --accent: #1b6ca8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 5;
    }
    h1 { font-size: 20px; margin: 0; }
    .controls {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
    }
    input {
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 10px;
      min-width: 260px;
    }
    button {
      height: 36px;
      border: 1px solid #155e8f;
      background: var(--accent);
      color: white;
      border-radius: 6px;
      padding: 0 14px;
      cursor: pointer;
      font-weight: 600;
    }
    button.secondary {
      background: white;
      color: var(--accent);
    }
    main {
      padding: 18px 24px 28px;
      display: grid;
      gap: 16px;
    }
    .status {
      color: var(--muted);
      min-height: 20px;
      font-size: 14px;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(6, minmax(140px, 1fr));
      gap: 10px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      min-height: 74px;
    }
    .label { color: var(--muted); font-size: 12px; }
    .value { font-size: 19px; font-weight: 700; margin-top: 6px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(320px, 1fr));
      gap: 16px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }
    .panel h2 {
      font-size: 15px;
      margin: 0 0 8px;
    }
    canvas {
      width: 100%;
      height: 260px;
      display: block;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      color: var(--muted);
      font-size: 12px;
      margin-top: 8px;
    }
    .swatch {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 2px;
      margin-right: 4px;
      vertical-align: -1px;
    }
    @media (max-width: 980px) {
      header { align-items: flex-start; flex-direction: column; }
      .controls { justify-content: flex-start; }
      .cards { grid-template-columns: repeat(2, minmax(140px, 1fr)); }
      .grid { grid-template-columns: 1fr; }
      input { min-width: min(100%, 320px); }
    }
  </style>
</head>
<body>
  <header>
    <h1>PVBESSCAR - Simulación A2C en tiempo real</h1>
    <div class="controls">
      <input id="apiKey" type="password" autocomplete="off" placeholder="X-API-Key">
      <button id="startBtn">Iniciar</button>
      <button id="stopBtn" class="secondary">Detener</button>
    </div>
  </header>
  <main>
    <div id="status" class="status">Listo para conectar con /ws/realtime.</div>
    <section class="cards">
      <div class="card"><div class="label">Paso</div><div id="mStep" class="value">0</div></div>
      <div class="card"><div class="label">CO2 total evitado</div><div id="mCo2" class="value">0 kg</div></div>
      <div class="card"><div class="label">EV cargado</div><div id="mEv" class="value">0 kWh</div></div>
      <div class="card"><div class="label">Grid import</div><div id="mGrid" class="value">0 kWh</div></div>
      <div class="card"><div class="label">BESS SOC</div><div id="mSoc" class="value">0%</div></div>
      <div class="card"><div class="label">Tomas activas</div><div id="mSockets" class="value">0/38</div></div>
    </section>
    <section class="grid">
      <div class="panel">
        <h2>Control BESS</h2>
        <canvas id="chartBess"></canvas>
        <div id="legendBess" class="legend"></div>
      </div>
      <div class="panel">
        <h2>Tomas, EV y generación solar</h2>
        <canvas id="chartSockets"></canvas>
        <div id="legendSockets" class="legend"></div>
      </div>
      <div class="panel">
        <h2>Balance de energía</h2>
        <canvas id="chartEnergy"></canvas>
        <div id="legendEnergy" class="legend"></div>
      </div>
      <div class="panel">
        <h2>Reducción CO2 directa e indirecta</h2>
        <canvas id="chartCo2"></canvas>
        <div id="legendCo2" class="legend"></div>
      </div>
    </section>
  </main>
  <script>
    const maxPoints = 720;
    const state = { ws: null, totals: { co2: 0, ev: 0, grid: 0 } };
    const colors = {
      blue: "#1b6ca8", green: "#2f8f5b", red: "#c55252", amber: "#d2a24c",
      purple: "#7b61a8", gray: "#68717b", teal: "#087f8c"
    };
    const series = {
      bess: [
        { name: "acción BESS [-1,1]", color: colors.blue, values: [] },
        { name: "SOC BESS [0,1]", color: colors.green, values: [] },
        { name: "descarga/400", color: colors.red, values: [] },
        { name: "carga/400", color: colors.amber, values: [] }
      ],
      sockets: [
        { name: "tomas activas", color: colors.blue, values: [] },
        { name: "EV kWh", color: colors.green, values: [] },
        { name: "solar kWh", color: colors.amber, values: [] },
        { name: "PV→EV kWh", color: colors.teal, values: [] }
      ],
      energy: [
        { name: "solar", color: colors.amber, values: [] },
        { name: "mall", color: colors.purple, values: [] },
        { name: "grid import", color: colors.red, values: [] },
        { name: "grid export", color: colors.green, values: [] }
      ],
      co2: [
        { name: "directa", color: colors.green, values: [] },
        { name: "indirecta", color: colors.blue, values: [] },
        { name: "F6 solar", color: colors.amber, values: [] },
        { name: "F7 BESS", color: colors.purple, values: [] }
      ]
    };

    function fmt(n, digits = 0) {
      return Number(n || 0).toLocaleString("es-PE", { maximumFractionDigits: digits });
    }
    function pushBounded(arr, value) {
      arr.push(Number(value || 0));
      if (arr.length > maxPoints) arr.shift();
    }
    function setStatus(text) {
      document.getElementById("status").textContent = text;
    }
    function renderLegend(id, items) {
      document.getElementById(id).innerHTML = items.map(s =>
        `<span><span class="swatch" style="background:${s.color}"></span>${s.name}</span>`
      ).join("");
    }
    function draw(canvasId, items, fixedMin = null, fixedMax = null) {
      const canvas = document.getElementById(canvasId);
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      const ctx = canvas.getContext("2d");
      ctx.scale(dpr, dpr);
      const w = rect.width;
      const h = rect.height;
      const pad = { left: 46, right: 12, top: 12, bottom: 28 };
      const xs = Math.max(...items.map(s => s.values.length), 1);
      let all = items.flatMap(s => s.values);
      if (!all.length) all = [0, 1];
      let min = fixedMin ?? Math.min(...all, 0);
      let max = fixedMax ?? Math.max(...all, 1);
      if (Math.abs(max - min) < 1e-9) max = min + 1;
      ctx.clearRect(0, 0, w, h);
      ctx.strokeStyle = "#e2e8f0";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let i = 0; i <= 4; i++) {
        const y = pad.top + (h - pad.top - pad.bottom) * i / 4;
        ctx.moveTo(pad.left, y);
        ctx.lineTo(w - pad.right, y);
      }
      ctx.stroke();
      ctx.fillStyle = "#68717b";
      ctx.font = "11px Arial";
      ctx.textAlign = "right";
      for (let i = 0; i <= 4; i++) {
        const val = max - (max - min) * i / 4;
        const y = pad.top + (h - pad.top - pad.bottom) * i / 4 + 4;
        ctx.fillText(fmt(val, Math.abs(max) <= 2 ? 2 : 0), pad.left - 8, y);
      }
      for (const s of items) {
        ctx.strokeStyle = s.color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        s.values.forEach((v, i) => {
          const x = pad.left + (w - pad.left - pad.right) * (xs <= 1 ? 0 : i / (xs - 1));
          const y = pad.top + (h - pad.top - pad.bottom) * (1 - (v - min) / (max - min));
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
      }
      ctx.fillStyle = "#68717b";
      ctx.textAlign = "center";
      ctx.fillText(`${xs} muestras recientes`, (pad.left + w - pad.right) / 2, h - 8);
    }
    function redraw() {
      draw("chartBess", series.bess, -1, 1);
      draw("chartSockets", series.sockets);
      draw("chartEnergy", series.energy);
      draw("chartCo2", series.co2);
    }
    function handleStep(msg) {
      state.totals.co2 += Number(msg.co2_total_avoided_kg || 0);
      state.totals.ev += Number(msg.ev_total_kwh || 0);
      state.totals.grid += Number(msg.grid_import_kwh || 0);
      pushBounded(series.bess[0].values, msg.bess_action);
      pushBounded(series.bess[1].values, msg.bess_soc);
      pushBounded(series.bess[2].values, Number(msg.bess_discharge_kwh || 0) / 400);
      pushBounded(series.bess[3].values, -Number(msg.bess_charge_kwh || 0) / 400);
      pushBounded(series.sockets[0].values, msg.active_sockets);
      pushBounded(series.sockets[1].values, msg.ev_total_kwh);
      pushBounded(series.sockets[2].values, msg.solar_kwh);
      pushBounded(series.sockets[3].values, msg.dispatch_pv_to_ev_kwh);
      pushBounded(series.energy[0].values, msg.solar_kwh);
      pushBounded(series.energy[1].values, msg.mall_kwh);
      pushBounded(series.energy[2].values, msg.grid_import_kwh);
      pushBounded(series.energy[3].values, msg.grid_export_kwh);
      pushBounded(series.co2[0].values, msg.co2_direct_kg);
      pushBounded(series.co2[1].values, msg.co2_indirect_kg);
      pushBounded(series.co2[2].values, msg.co2_f6_solar_total_kg);
      pushBounded(series.co2[3].values, msg.co2_f7_bess_discharge_kg);
      document.getElementById("mStep").textContent = fmt(msg.step);
      document.getElementById("mCo2").textContent = `${fmt(state.totals.co2)} kg`;
      document.getElementById("mEv").textContent = `${fmt(state.totals.ev)} kWh`;
      document.getElementById("mGrid").textContent = `${fmt(state.totals.grid)} kWh`;
      document.getElementById("mSoc").textContent = `${fmt(Number(msg.bess_soc || 0) * 100, 1)}%`;
      document.getElementById("mSockets").textContent = `${fmt(msg.active_sockets, 1)}/38`;
      if (Number(msg.step || 0) % 3 === 0) redraw();
    }
    function resetData() {
      state.totals = { co2: 0, ev: 0, grid: 0 };
      Object.values(series).flat().forEach(s => { s.values.length = 0; });
      redraw();
    }
    function start() {
      if (state.ws && state.ws.readyState === WebSocket.OPEN) return;
      resetData();
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${location.host}/ws/realtime`);
      state.ws = ws;
      ws.onopen = () => {
        const apiKey = document.getElementById("apiKey").value || "";
        setStatus("Conectado. Ejecutando episodio A2C determinista...");
        ws.send(JSON.stringify({ api_key: apiKey, deterministic: true }));
      };
      ws.onmessage = event => {
        const msg = JSON.parse(event.data);
        if (msg.type === "step") handleStep(msg);
        if (msg.type === "done") {
          redraw();
          setStatus(`Finalizado: ${fmt(msg.summary.steps)} pasos, CO2 evitado ${fmt(msg.summary.co2_total_avoided_kg)} kg, reducción ${fmt(msg.summary.reduction_pct, 4)}%.`);
        }
        if (msg.type === "error") setStatus(`Error: ${msg.message}`);
      };
      ws.onerror = () => setStatus("Error de conexión WebSocket.");
      ws.onclose = () => {
        if (state.ws === ws) state.ws = null;
      };
    }
    function stop() {
      if (state.ws) state.ws.close();
      setStatus("Ejecución detenida.");
    }
    for (const [id, items] of [["legendBess", series.bess], ["legendSockets", series.sockets], ["legendEnergy", series.energy], ["legendCo2", series.co2]]) {
      renderLegend(id, items);
    }
    document.getElementById("startBtn").addEventListener("click", start);
    document.getElementById("stopBtn").addEventListener("click", stop);
    const keyFromUrl = new URLSearchParams(location.search).get("api_key");
    if (keyFromUrl) document.getElementById("apiKey").value = keyFromUrl;
    window.addEventListener("resize", redraw);
    redraw();
  </script>
</body>
</html>""")


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
        co2_direct_total = 0.0
        co2_indirect_total = 0.0
        ev_total = 0.0
        grid_total = 0.0
        bess_total = 0.0
        solar_total = 0.0

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
            snap = _step_snapshot(i, r, step)
            co2_direct_total += snap["co2_direct_kg"]
            co2_indirect_total += snap["co2_indirect_kg"]
            ev_total += snap["ev_total_kwh"]
            grid_total += snap["grid_import_kwh"]
            bess_total += snap["bess_discharge_kwh"]
            solar_total += snap["solar_kwh"]

            msg = {
                "type":    "step",
                "step":    step,
                "action":  action[0].tolist() if hasattr(action[0], "tolist") else list(action[0]),
                "reward":  round(r, 4),
                **_round_trace_row(snap),
            }
            await websocket.send_json(msg)
            step += 1
            await asyncio.sleep(0)  # yield al event loop

        co2_total = co2_direct_total + co2_indirect_total
        await websocket.send_json({
            "type": "done",
            "summary": {
                "steps":               step,
                "total_reward":        round(total_reward, 4),
                "co2_direct_kg":       round(co2_direct_total, 2),
                "co2_indirect_kg":     round(co2_indirect_total, 2),
                "co2_total_avoided_kg": round(co2_total, 2),
                "co2_f2_kg_yr":        round(F0_REFERENCE - co2_total, 2),
                "reduction_pct":       round(co2_total / F0_REFERENCE * 100, 4),
                "ev_total_kwh":        round(ev_total, 2),
                "grid_import_kwh":     round(grid_total, 2),
                "bess_discharge_kwh":  round(bess_total, 2),
                "solar_kwh":           round(solar_total, 2),
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
