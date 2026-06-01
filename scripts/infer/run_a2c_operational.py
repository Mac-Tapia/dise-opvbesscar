#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_a2c_operational.py
Script de inferencia operativa del agente A2C seleccionado (pvbesscar OE3).

Carga el checkpoint final A2C + VecNormalize y ejecuta episodios deterministas
reportando CO₂ evitado, carga EV, BESS y costos tarifarios.

Uso:
    python scripts/infer/run_a2c_operational.py --episodes 1
    python scripts/infer/run_a2c_operational.py --episodes 5 --output results.json
    python scripts/infer/run_a2c_operational.py --checkpoint checkpoints/A2C_CityLearn/a2c_final
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("a2c_operational")

CO2_FACTOR   = 0.4521          # kg CO2/kWh — red aislada Iquitos (MINEM 2024)
F0_REFERENCE = 7_053_999.0     # kg CO2/año — baseline sin RL
TARIFA_HP    = 0.46            # S./kWh — OSINERGMIN Res. 047-2024-OS/CD
TARIFA_HFP   = 0.29            # S./kWh


# ─── Carga del modelo ─────────────────────────────────────────────────────────

def load_a2c_model(checkpoint_path: str):
    """Carga el modelo A2C + VecNormalize desde checkpoint SB3."""
    from stable_baselines3 import A2C
    from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv

    ckpt = Path(checkpoint_path)
    if not ckpt.suffix:
        ckpt = ckpt.with_suffix(".zip")
    if not ckpt.exists():
        raise FileNotFoundError(f"Checkpoint no encontrado: {ckpt}")

    log.info("Cargando modelo A2C: %s", ckpt)
    model = A2C.load(str(ckpt.with_suffix("")))
    log.info("  obs_space=%s  action_space=%s", model.observation_space, model.action_space)
    return model


def load_vecnormalize(pkl_path: str | None, env):
    """Carga estadísticas VecNormalize si existen."""
    from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv

    if pkl_path and Path(pkl_path).exists():
        vec_env = DummyVecEnv([lambda: env])
        vec_env = VecNormalize.load(str(pkl_path), vec_env)
        vec_env.training = False
        vec_env.norm_reward = False
        log.info("VecNormalize cargado: %s", pkl_path)
        return vec_env
    log.warning("VecNormalize no encontrado — usando entorno sin normalizar")
    from stable_baselines3.common.vec_env import DummyVecEnv
    return DummyVecEnv([lambda: env])


# ─── Creación del entorno ─────────────────────────────────────────────────────

def build_env():
    """Crea el entorno CityLearn v2 IquitosEV en modo inferencia."""
    try:
        from citylearnv2.env_factory import create_iquitos_env_for_sb3
        env = create_iquitos_env_for_sb3()
        log.info("Entorno CityLearn v2 creado — obs_dim=19, action_dim=3")
        return env
    except Exception as exc:
        log.error("Error creando entorno CityLearn: %s", exc)
        raise


# ─── Episodio de inferencia ───────────────────────────────────────────────────

def run_episode(model, vec_env) -> dict[str, Any]:
    """Ejecuta 1 episodio completo (8,760 steps) de forma determinista."""
    obs = vec_env.reset()
    done = False
    step = 0
    t0 = time.time()

    co2_direct_kg   = 0.0
    co2_indirect_kg = 0.0
    ev_motos_kwh    = 0.0
    ev_mototaxis_kwh = 0.0
    grid_import_kwh = 0.0
    bess_discharge_kwh = 0.0
    solar_kwh       = 0.0
    cost_soles      = 0.0
    total_reward    = 0.0
    n_steps         = 0

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done_arr, info = vec_env.step(action)
        done = bool(done_arr[0]) if hasattr(done_arr, "__len__") else bool(done_arr)

        if info:
            i = info[0] if isinstance(info, (list, tuple)) else info
            # Claves reales devueltas por IquitosEVChargingWrapper.step()
            co2_direct_kg   += float(i.get("co2_reduccion_directa_kg",    0.0))
            co2_indirect_kg += float(i.get("co2_reduccion_indirecta_kg",  0.0))
            ev_motos_kwh    += float(i.get("ev_motos_actual_kwh",          0.0))
            ev_mototaxis_kwh += float(i.get("ev_mototaxis_actual_kwh",     0.0))
            grid_import_kwh += float(i.get("grid_import_kwh",              0.0))
            bess_discharge_kwh += float(i.get("bess_discharge_kwh",        0.0))
            solar_kwh       += float(i.get("solar_generation_kwh",         0.0))
            cost_soles      += float(i.get("cost_soles",                   0.0))

        total_reward += float(reward[0]) if hasattr(reward, "__len__") else float(reward)
        step += 1
        n_steps += 1

    elapsed = time.time() - t0
    co2_total_kg  = co2_direct_kg + co2_indirect_kg
    co2_f2_kg_yr  = F0_REFERENCE - co2_total_kg
    reduction_pct = co2_total_kg / F0_REFERENCE * 100.0
    ev_total_kwh  = ev_motos_kwh + ev_mototaxis_kwh

    return {
        "steps":                  n_steps,
        "elapsed_s":              round(elapsed, 2),
        "total_reward":           round(total_reward, 4),
        "co2_direct_kg":          round(co2_direct_kg,    2),
        "co2_indirect_kg":        round(co2_indirect_kg,  2),
        "co2_total_avoided_kg":   round(co2_total_kg,     2),
        "co2_f2_residual_kg_yr":  round(co2_f2_kg_yr,     2),
        "co2_reduction_vs_f0_pct": round(reduction_pct,   4),
        "ev_motos_kwh":           round(ev_motos_kwh,     2),
        "ev_mototaxis_kwh":       round(ev_mototaxis_kwh, 2),
        "ev_total_kwh":           round(ev_total_kwh,     2),
        "grid_import_kwh":        round(grid_import_kwh,  2),
        "bess_discharge_kwh":     round(bess_discharge_kwh, 2),
        "solar_kwh":              round(solar_kwh,        2),
        "cost_total_soles":       round(cost_soles,       2),
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Inferencia operativa A2C — pvbesscar OE3")
    parser.add_argument("--checkpoint", default=str(ROOT / "checkpoints/A2C_CityLearn/a2c_final"),
                        help="Ruta al checkpoint SB3 (sin extensión .zip)")
    parser.add_argument("--vecnormalize", default=None,
                        help="Ruta al .pkl VecNormalize (auto-detectado si None)")
    parser.add_argument("--episodes", type=int, default=1,
                        help="Número de episodios a evaluar")
    parser.add_argument("--output", default=None,
                        help="Archivo JSON de salida (opcional)")
    args = parser.parse_args()

    # Auto-detectar vecnormalize
    vec_pkl = args.vecnormalize
    if vec_pkl is None:
        ckpt_dir = Path(args.checkpoint).parent
        candidates = [
            ckpt_dir / "vecnormalize.pkl",
            ckpt_dir / "a2c_vecnormalize_438000_steps.pkl",
        ]
        for c in candidates:
            if c.exists():
                vec_pkl = str(c)
                break

    log.info("=" * 60)
    log.info("PVBESSCAR — Inferencia Operativa A2C")
    log.info("Checkpoint: %s", args.checkpoint)
    log.info("VecNormalize: %s", vec_pkl or "N/A")
    log.info("Episodios: %d", args.episodes)
    log.info("=" * 60)

    env   = build_env()
    model = load_a2c_model(args.checkpoint)
    vec_env = load_vecnormalize(vec_pkl, env)

    results = []
    for ep in range(1, args.episodes + 1):
        log.info("Episodio %d/%d ...", ep, args.episodes)
        r = run_episode(model, vec_env)
        r["episode"] = ep
        results.append(r)
        log.info(
            "  CO2 evitado=%.0f kg | F2=%.0f kg/año | Red=%.2f%% | "
            "Reward=%.2f | EV=%.0f kWh | Costo=%.0f S.",
            r["co2_total_avoided_kg"], r["co2_f2_residual_kg_yr"],
            r["co2_reduction_vs_f0_pct"], r["total_reward"],
            r["ev_total_kwh"], r["cost_total_soles"],
        )

    summary = {
        "agent":           "A2C",
        "checkpoint":      args.checkpoint,
        "obs_dim":         19,
        "reward_version":  "CO2_DUAL_FOCUS v8.1",
        "episodes":        args.episodes,
        "co2_factor_kg_kwh": CO2_FACTOR,
        "f0_reference_kg_yr": F0_REFERENCE,
        "mean_co2_avoided_kg":    round(np.mean([r["co2_total_avoided_kg"]  for r in results]), 2),
        "mean_f2_kg_yr":          round(np.mean([r["co2_f2_residual_kg_yr"] for r in results]), 2),
        "mean_reduction_pct":     round(np.mean([r["co2_reduction_vs_f0_pct"] for r in results]), 4),
        "mean_reward":            round(np.mean([r["total_reward"]           for r in results]), 4),
        "mean_ev_total_kwh":      round(np.mean([r["ev_total_kwh"]           for r in results]), 2),
        "mean_cost_total_soles":  round(np.mean([r["cost_total_soles"]       for r in results]), 2),
        "episodes_detail":        results,
    }

    log.info("=" * 60)
    log.info("RESUMEN — %d episodios", args.episodes)
    log.info("  CO2 evitado medio:  %.0f kg/año", summary["mean_co2_avoided_kg"])
    log.info("  F2 residual medio:  %.0f kg/año", summary["mean_f2_kg_yr"])
    log.info("  Reducción vs F0:    %.2f%%",       summary["mean_reduction_pct"])
    log.info("  Reward medio:       %.2f",          summary["mean_reward"])
    log.info("  EV total medio:     %.0f kWh",      summary["mean_ev_total_kwh"])
    log.info("  Costo OSINERGMIN:   %.0f S./año",   summary["mean_cost_total_soles"])
    log.info("=" * 60)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("Resultados guardados: %s", out)
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
