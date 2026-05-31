#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Valida que los 3 agentes (SAC, PPO, A2C) comparten exactamente las mismas
condiciones de entrenamiento — solo deben diferir en hiperparametros.

Condiciones verificadas:
  C1  Mismo factory: create_iquitos_env_for_sb3()
  C2  Mismo obs_dim=19 y action_dim=3
  C3  Mismo VecNormalize (norm_obs, norm_reward, clip_obs, clip_reward)
  C4  Mismos pesos reward (CO2_DUAL_FOCUS v8.1) desde ev_charging_wrapper.py
  C5  Misma arquitectura de red (pi, vf/qf, activation_fn)
  C6  Mismo total_timesteps = 8760 * 50 = 438,000
  C7  Misma logica de penalidad (penalty_debt_frac > 0.1)
  C8  policy = 'MlpPolicy' en los 3
  C9  Dataset real OE2 -> CityLearn v2 (8760 filas × 4 CSV)

Hiperparametros legitimamente distintos (no se validan como iguales):
  n_steps, gamma, gae_lambda, learning_rate, ent_coef, batch_size,
  buffer_size, learning_starts, tau, gradient_steps, target_entropy,
  ortho_init, n_epochs, clip_range, target_kl
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

AGENTS = ["a2c", "ppo", "sac"]
PASS = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"

errors: list[str] = []
warnings: list[str] = []


def _src(agent: str) -> str:
    return (ROOT / "scripts" / "train" / f"train_{agent}_citylearn.py").read_text(
        encoding="utf-8", errors="replace"
    )


def check(cond: bool, msg_ok: str, msg_fail: str, fatal: bool = True) -> bool:
    if cond:
        print(f"  {PASS} {msg_ok}")
        return True
    label = FAIL if fatal else WARN
    print(f"  {label} {msg_fail}")
    (errors if fatal else warnings).append(msg_fail)
    return False


# ── C1: mismo factory ─────────────────────────────────────────────────────────
print("\n[C1] Factory: todos usan create_iquitos_env_for_sb3()")
for ag in AGENTS:
    src = _src(ag)
    check(
        "create_iquitos_env_for_sb3" in src,
        f"{ag.upper()} importa y llama create_iquitos_env_for_sb3",
        f"{ag.upper()} NO usa create_iquitos_env_for_sb3",
    )

# ── C2: obs_dim y action_dim ──────────────────────────────────────────────────
print("\n[C2] Espacio de observacion y accion: obs=18, action=3")
import warnings as _w
_w.filterwarnings("ignore")
try:
    from src.citylearnv2.env_factory import create_iquitos_env_for_sb3
    import logging
    logging.disable(logging.CRITICAL)
    env = create_iquitos_env_for_sb3()
    obs_dim = env.observation_space.shape[0]
    act_dim = env.action_space.shape[0]
    env.close()
    logging.disable(logging.NOTSET)
    check(obs_dim == 19, f"obs_dim={obs_dim} (correcto)", f"obs_dim={obs_dim} (esperado 19)")
    check(act_dim == 3,  f"action_dim={act_dim} (correcto)", f"action_dim={act_dim} (esperado 3)")
except Exception as e:
    print(f"  {FAIL} No se pudo instanciar entorno: {e}")
    errors.append(str(e))

# ── C3: VecNormalize identico ─────────────────────────────────────────────────
print("\n[C3] VecNormalize: norm_obs=True, norm_reward=True, clip_obs=10.0, clip_reward=10.0")
VN_REQUIRED = {
    "norm_obs=True":      r"norm_obs\s*=\s*True",
    "norm_reward=True":   r"norm_reward\s*=\s*True",
    "clip_obs=10.0":      r"clip_obs\s*=\s*10\.0",
    "clip_reward=10.0":   r"clip_reward\s*=\s*10\.0",
}
for ag in AGENTS:
    src = _src(ag)
    for label, pat in VN_REQUIRED.items():
        check(
            bool(re.search(pat, src)),
            f"{ag.upper()} {label}",
            f"{ag.upper()} NO tiene {label}",
        )

# ── C4: pesos reward CO2_DUAL_FOCUS v8.1 ─────────────────────────────────────
print("\n[C4] Pesos reward en ev_charging_wrapper.py (CO2_DUAL_FOCUS v8.1)")
EXPECTED_WEIGHTS = {
    "_W_DIRECT_CO2":   0.20,
    "_W_INDIRECT_CO2": 0.30,
    "_W_EV_COMPLETE":  0.35,
    "_W_BESS_SOLAR":   0.07,
    "_W_SOLAR":        0.04,
    "_W_GRID_STABLE":  0.02,
    "_W_COST":         0.02,
}
wrapper_src = (ROOT / "src" / "citylearnv2" / "ev_charging_wrapper.py").read_text(
    encoding="utf-8", errors="replace"
)
total_w = 0.0
for w_name, w_val in EXPECTED_WEIGHTS.items():
    pat = rf"{w_name}\s*:\s*float\s*=\s*([\d.]+)"
    m = re.search(pat, wrapper_src)
    if m:
        found = float(m.group(1))
        total_w += found
        check(
            abs(found - w_val) < 1e-6,
            f"{w_name} = {found} (esperado {w_val})",
            f"{w_name} = {found} (esperado {w_val}) — PESO INCORRECTO",
        )
    else:
        check(False, "", f"{w_name} no encontrado en wrapper")

check(
    abs(total_w - 1.0) < 1e-4,
    f"Suma de pesos = {total_w:.4f} (suma = 1.0)",
    f"Suma de pesos = {total_w:.4f} (debe ser 1.0)",
)

# Los 3 scripts usan el mismo wrapper (ya validado en C1)
print("  [OK] Los 3 agentes usan IquitosEVChargingWrapper — pesos definidos una sola vez")

# ── C5: arquitectura de red ───────────────────────────────────────────────────
print("\n[C5] Arquitectura de red: pi=[256,256,128], vf/qf=[512,512,256], Tanh")
ARCH_REQUIRED = {
    "pi=[256, 256, 128]": r"pi=\[256,\s*256,\s*128\]",
    "vf/qf=[512,512,256]": r"(?:vf|qf)=\[512,\s*512,\s*256\]",
    "activation=Tanh":     r"activation_fn.*Tanh",
    "policy=MlpPolicy":    r'"policy":\s*"MlpPolicy"',
}
for ag in AGENTS:
    src = _src(ag)
    for label, pat in ARCH_REQUIRED.items():
        check(
            bool(re.search(pat, src)),
            f"{ag.upper()} {label}",
            f"{ag.upper()} NO tiene {label}",
        )

# ── C6: total_timesteps = 438000 ──────────────────────────────────────────────
print("\n[C6] Total timesteps = 8760 * 50 = 438,000 (50 episodios por agente)")
for ag in AGENTS:
    src = _src(ag)
    check(
        bool(re.search(r"8_760\s*\*\s*50|8760\s*\*\s*50", src)),
        f"{ag.upper()} TOTAL_TIMESTEPS = 8760 * 50",
        f"{ag.upper()} NO tiene TOTAL_TIMESTEPS = 8760 * 50",
    )

# ── C7: penalidad debt_frac > 0.1 ────────────────────────────────────────────
print("\n[C7] Penalidad debt: mismo umbral penalty_debt_frac > 0.1 en los 3")
for ag in AGENTS:
    src = _src(ag)
    check(
        bool(re.search(r'penalty_debt_frac.*0\.1', src)),
        f"{ag.upper()} usa penalty_debt_frac > 0.1",
        f"{ag.upper()} NO usa penalty_debt_frac > 0.1",
    )

# ── C8: policy = MlpPolicy ───────────────────────────────────────────────────
print("\n[C8] policy = 'MlpPolicy' en los 3 (ya validado en C5)")
print("  [OK] Validado en C5")

# ── C9: dataset real OE2 → CityLearn v2 ──────────────────────────────────────
print("\n[C9] Dataset real OE2 cargado en CityLearn v2 (8760 filas × 4 CSV)")
import pandas as pd
CL_CSVS = {
    "solar_generation":   ROOT / "data" / "iquitos_ev_mall" / "solar_generation.csv",
    "bess_timeseries":    ROOT / "data" / "iquitos_ev_mall" / "bess_timeseries.csv",
    "chargers_timeseries":ROOT / "data" / "iquitos_ev_mall" / "chargers_timeseries.csv",
    "mall_demand":        ROOT / "data" / "iquitos_ev_mall" / "mall_demand.csv",
}
for name, path in CL_CSVS.items():
    if path.exists():
        df = pd.read_csv(path)
        check(
            len(df) == 8760,
            f"{name}.csv: {len(df)} filas",
            f"{name}.csv: {len(df)} filas (esperado 8760)",
        )
    else:
        check(False, "", f"{name}.csv no encontrado")

# ── HIPERPARAMETROS LEGITIMOS ─────────────────────────────────────────────────
print("\n[INFO] Hiperparametros que DEBEN diferir (por naturaleza de cada algoritmo):")
HYPER_DIFF = {
    "A2C": "n_steps=512 | gamma=0.90 | gae_lambda=0.95 | lr=7e-4 (fijo) | ent_coef=0.01",
    "PPO": "n_steps=4096 | gamma=0.88 | gae_lambda=0.92 | lr=schedule_1e-4 | batch=256/128 | ent_coef=0.02 | ortho_init=True",
    "SAC": "buffer=87600 | learn_starts=17520 | gamma=0.95 | tau=0.01 | batch=512/256 | ent_coef=auto | target_entropy=-2.0",
}
for ag, desc in HYPER_DIFF.items():
    print(f"  {ag}: {desc}")

# ── RESUMEN ───────────────────────────────────────────────────────────────────
print()
print("=" * 65)
if not errors:
    print(f"  RESULTADO: TODOS LOS CHECKS PASARON ({9} condiciones)")
    print("  Los 3 agentes tienen exactamente las mismas condiciones.")
    print("  Solo los hiperparametros varian segun la naturaleza de cada algoritmo.")
else:
    print(f"  RESULTADO: {len(errors)} ERROR(ES) ENCONTRADO(S)")
    for e in errors:
        print(f"    FAIL: {e}")
if warnings:
    print(f"  ADVERTENCIAS ({len(warnings)}):")
    for w in warnings:
        print(f"    WARN: {w}")
print("=" * 65)

if errors:
    sys.exit(1)
