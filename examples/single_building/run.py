"""examples/single_building/run.py — Ejemplo reproducible: Iquitos BESS Mall.
# -*- coding: utf-8 -*-

Demuestra el uso del framework universal PVBESSCAR con el sitio validado de
Iquitos. Ejecuta 3 episodios con un agente SAC preentrenado (o aleatorio si
no hay checkpoint) y reporta métricas de CO₂ y satisfacción EV.

Uso:
    python examples/single_building/run.py [--episodes 3] [--random-agent]

Referencia de resultados validados:
    SAC ep48: CO₂ = 2,622,735 kg/año, reducción = 62.8% vs F₀
    Kruskal-Wallis H = 81.65, p = 1.86×10⁻¹⁸ (SAC > PPO > A2C)
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# Force UTF-8 stdout on Windows so CO2 subscript characters render correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.core import load_site_config
from src.rl import UniversalPVBESSEnv
from src.core.reward import RewardWeights


def load_iquitos_data() -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Load OE2 canonical datasets for Iquitos site."""
    solar = pd.read_csv(_ROOT / "data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
    chargers = pd.read_csv(_ROOT / "data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    mall = pd.read_csv(_ROOT / "data/oe2/demandamallkwh/demandamallhorakwh.csv")

    # Extract per-type EV demand from chargers CSV
    ev_dfs = {
        "moto":     chargers["ev_energia_motos_kwh"],
        "mototaxi": chargers["ev_energia_mototaxis_kwh"],
    }
    return solar, ev_dfs, mall


def run_episode(env: UniversalPVBESSEnv, agent=None, episode: int = 1) -> dict:
    """Run one episode and return summary metrics."""
    obs, _ = env.reset()
    total_reward = 0.0
    total_co2_avoided = 0.0
    total_ev_served = 0.0
    total_ev_demand = 0.0
    total_grid_import = 0.0
    steps = 0

    while True:
        if agent is not None:
            action, _ = agent.predict(obs, deterministic=True)
        else:
            # Random baseline agent
            action = env.action_space.sample()

        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        total_co2_avoided += info["co2_avoided_kg"]
        total_ev_served += sum(info.get("ev_satisfaction", [1.0])) / max(env.n_types, 1)
        total_grid_import += info["grid_import_kwh"]
        steps += 1

        if terminated or truncated:
            break

    ev_sat_avg = total_ev_served / max(steps, 1)
    return {
        "episode": episode,
        "steps": steps,
        "total_reward": total_reward,
        "co2_avoided_kg": total_co2_avoided,
        "co2_avoided_annual_kg": total_co2_avoided * (8760 / steps),
        "ev_satisfaction_avg": ev_sat_avg,
        "grid_import_kwh": total_grid_import,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejemplo reproducible Iquitos BESS Mall")
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--random-agent", action="store_true", default=False,
                        help="Usar agente aleatorio (sin checkpoint SAC)")
    args = parser.parse_args()

    print("=" * 70)
    print("  PVBESSCAR — Ejemplo reproducible: Iquitos BESS Mall")
    print("  Framework universal PVBESS-EV con agente SAC")
    print("=" * 70)

    # ── 1. Cargar configuración de sitio ──────────────────────────────────
    site = load_site_config(_ROOT / "configs/sites/iquitos_bess_mall.yaml")
    print(f"\nSitio: {site.name}")
    print(f"  Ubicación: {site.latitude}°, {site.longitude}° | TZ: {site.timezone}")
    print(f"  PV total: {site.total_pv_kwp:.0f} kWp | BESS: {site.total_bess_kwh:.0f} kWh")
    print(f"  Flota: {site.total_ev_vehicles} vehículos ({', '.join(site.all_vehicle_types)})")
    b = site.buildings[0]
    fleet = b.ev_fleet
    print(f"  Sockets totales: {fleet.total_sockets} | Cargadores: {fleet.total_chargers}")

    # ── 2. Cargar datos OE2 ───────────────────────────────────────────────
    print("\nCargando datasets OE2...")
    try:
        solar_df, ev_dfs, mall_df = load_iquitos_data()
        print(f"  Solar: {len(solar_df)} filas | Columnas: {list(solar_df.columns[:4])}")
        print(f"  EV types: {list(ev_dfs.keys())}")
    except FileNotFoundError as e:
        print(f"  [ERROR] Datos OE2 no encontrados: {e}")
        print("  Ejecutar primero: python scripts/generate_oe2_datasets.py --loader-only")
        sys.exit(1)

    # ── 3. Construir entorno ───────────────────────────────────────────────
    weights = RewardWeights.co2_dual_focus()
    env = UniversalPVBESSEnv.from_dataframes(
        site=site,
        building_idx=0,
        solar_df=solar_df,
        ev_dfs=ev_dfs,
        fixed_load_df=mall_df,
        reward_weights=weights,
        seed=42,
    )
    print(f"\nEntorno construido:")
    print(f"  obs_dim = {env.obs_dim}  (15 base + {env.n_types} tipos × 3)")
    print(f"  action_dim = {env.action_dim}  (1 BESS + {env.n_types} EV fracciones)")
    print(f"  Reward: CO2_DUAL_FOCUS (w_direct={weights.w_direct_co2}, "
          f"w_co2={weights.w_co2}, w_ev={weights.w_ev}, "
          f"w_solar={weights.w_solar}, w_grid={weights.w_grid})")

    # ── 4. Cargar agente SAC (o usar agente aleatorio) ────────────────────
    agent = None
    if not args.random_agent:
        try:
            from stable_baselines3 import SAC
            ckpt_dir = _ROOT / "checkpoints" / "SAC"
            ckpts = sorted(ckpt_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime) if ckpt_dir.exists() else []
            if ckpts:
                latest = ckpts[-1]
                agent = SAC.load(latest)
                print(f"\nAgente SAC cargado: {latest.name}")
            else:
                print("\nNo se encontró checkpoint SAC — usando agente aleatorio")
        except ImportError:
            print("\nstable-baselines3 no disponible — usando agente aleatorio")

    # ── 5. Ejecutar episodios ──────────────────────────────────────────────
    print(f"\nEjecutando {args.episodes} episodios{'  [SAC]' if agent else '  [ALEATORIO]'}...")
    print("-" * 70)
    results = []
    for ep in range(1, args.episodes + 1):
        t0 = time.time()
        r = run_episode(env, agent, ep)
        elapsed = time.time() - t0
        results.append(r)
        print(
            f"  Ep{ep:2d}: reward={r['total_reward']:+8.1f}  "
            f"CO₂_evitado={r['co2_avoided_annual_kg']/1e3:7.1f} t/año  "
            f"EV_sat={r['ev_satisfaction_avg']:.3f}  "
            f"grid={r['grid_import_kwh']:7.0f} kWh  ({elapsed:.1f}s)"
        )

    # ── 6. Resumen ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RESUMEN")
    print("=" * 70)
    mean_co2 = np.mean([r["co2_avoided_annual_kg"] for r in results])
    mean_ev = np.mean([r["ev_satisfaction_avg"] for r in results])
    mean_reward = np.mean([r["total_reward"] for r in results])

    baseline_co2_kg = 7_054_000  # F₀: sin solar, sin BESS, sin RL
    reduction_pct = (mean_co2 / baseline_co2_kg) * 100

    print(f"  CO₂ evitado (media): {mean_co2/1e3:.1f} t/año  ({reduction_pct:.1f}% de baseline F₀)")
    print(f"  EV satisfacción (media): {mean_ev:.3f}")
    print(f"  Reward (media): {mean_reward:.2f}")
    print()
    print("  Baseline de referencia (validado PVBESSCAR 2024):")
    print(f"    F₀ (sin control):    7,054 t CO₂/año")
    print(f"    F₂ SAC ep48:        2,622 t CO₂/año  (62.8% reducción)")
    print()
    print("  Para entrenar: python scripts/train/train_sac_citylearn.py")
    print("  Para otros sitios: editar configs/sites/ y repetir este script")
    print("=" * 70)


if __name__ == "__main__":
    main()
