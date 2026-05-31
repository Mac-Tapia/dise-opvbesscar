#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Actualiza todos los archivos del proyecto con los pesos CO2_DUAL_FOCUS v8.1.

Pesos activos en src/citylearnv2/ev_charging_wrapper.py (fuente unica):
  direct_co2:     0.20   (OE3-1 CO2 directa ICE->EV)
  indirect_co2:   0.30   (OE3-2 CO2 indirecta grid import)
  ev_complete:    0.35   (OE3-3 satisfaccion/cantidad carga EV)
  bess_solar:     0.07   (regla BESS carga solar, no diesel)
  solar:          0.04   (autoconsumo PV)
  grid_stability: 0.02   (estabilidad red)
  cost:           0.02   (tarifa OSINERGMIN)
  suma:           1.00

Archivos actualizados:
  configs/agents/{sac,ppo,a2c,agents}_config.yaml
  configs/default.yaml
  configs/default_optimized.yaml
  src/dataset_builder_citylearn/rewards.py (docstrings/comentarios)
  src/core/reward.py (preset co2_dual_focus)
  reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md
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

V81_WEIGHTS = {
    "direct_co2":     0.20,
    "indirect_co2":   0.30,
    "ev_complete":    0.35,
    "bess_solar_timing": 0.07,
    "solar":          0.04,
    "grid_stability": 0.02,
    "cost":           0.02,
}

# Bloque YAML de pesos v8.1 (para insertar en configs)
YAML_WEIGHTS_BLOCK = """\
      # CO2_DUAL_FOCUS v8.1 — fuente activa: src/citylearnv2/ev_charging_wrapper.py
      # Los 3 agentes (SAC/PPO/A2C) usan EXACTAMENTE estos pesos. Suma = 1.00
      direct_co2:          0.20  # OE3-1: CO2 directa (ICE->EV electrificacion vehicular)
      indirect_co2:        0.30  # OE3-2: CO2 indirecta (grid import x 0.4521 kg CO2/kWh)
      ev_complete:         0.35  # OE3-3: satisfaccion/cantidad carga EV (motos+mototaxis)
      bess_solar_timing:   0.07  # regla op: BESS carga solar(6-18h), NO diesel nocturno
      solar:               0.04  # autoconsumo PV
      grid_stability:      0.02  # estabilidad red (suavizado rampas)
      cost:                0.02  # costo OSINERGMIN HP/HFP"""

YAML_WEIGHTS_BLOCK_TOP = """\
    # CO2_DUAL_FOCUS v8.1 — fuente activa: src/citylearnv2/ev_charging_wrapper.py
    # Los 3 agentes (SAC/PPO/A2C) usan EXACTAMENTE estos pesos. Suma = 1.00
    direct_co2:          0.20  # OE3-1: CO2 directa (ICE->EV electrificacion vehicular)
    indirect_co2:        0.30  # OE3-2: CO2 indirecta (grid import x 0.4521 kg CO2/kWh)
    ev_complete:         0.35  # OE3-3: satisfaccion/cantidad carga EV (motos+mototaxis)
    bess_solar_timing:   0.07  # regla op: BESS carga solar(6-18h), NO diesel nocturno
    solar:               0.04  # autoconsumo PV
    grid_stability:      0.02  # estabilidad red (suavizado rampas)
    cost:                0.02  # costo OSINERGMIN HP/HFP"""


updated: list[str] = []


def _rewrite(path: Path, new_text: str, original: str) -> None:
    if new_text != original:
        path.write_text(new_text, encoding="utf-8")
        updated.append(str(path.relative_to(ROOT)))
        print(f"  ACTUALIZADO: {path.relative_to(ROOT)}")
    else:
        print(f"  sin cambios:  {path.relative_to(ROOT)}")


# ── YAML: sustituir bloque multi_objective_weights ────────────────────────────

OLD_WEIGHT_PATS = [
    # v7.4 / v7.5 block con 6 lineas (sin ev_complete)
    (
        r"(multi_objective_weights:\s*\n)"
        r"(\s*#.*?v7\.[0-9].*?\n)?"
        r"(\s*direct_co2:\s*0\.25.*?\n)"
        r"(\s*indirect_co2:\s*0\.30.*?\n)"
        r"(\s*bess_solar_timing:\s*0\.10.*?\n)"
        r"(\s*solar:\s*0\.05.*?\n)"
        r"(\s*grid_stability:\s*0\.03.*?\n)"
        r"(\s*cost:\s*0\.02.*?\n)",
        "multi_objective_weights:\n" + YAML_WEIGHTS_BLOCK + "\n",
    ),
    # default.yaml: direct_co2_weight style
    (
        r"(rewards:\s*\n)"
        r"(\s*#.*?v7\.[0-9].*?\n)?"
        r"(\s*direct_co2_weight:\s*0\.25.*?\n)"
        r"(\s*indirect_co2_weight:\s*0\.30.*?\n)"
        r"(\s*ev_satisfaction_weight:\s*0\.25.*?\n)"
        r"(\s*bess_solar_timing_weight:\s*0\.10.*?\n)"
        r"(\s*solar_weight:\s*0\.05.*?\n)"
        r"(\s*grid_stability_weight:\s*0\.03.*?\n)"
        r"(\s*cost_weight:\s*0\.02.*?\n)",
        "rewards:\n"
        "    # CO2_DUAL_FOCUS v8.1 — fuente activa: src/citylearnv2/ev_charging_wrapper.py\n"
        "    # Suma = 1.00. Los 3 agentes usan EXACTAMENTE estos pesos.\n"
        "    direct_co2_weight:          0.20  # OE3-1: CO2 directa (ICE->EV)\n"
        "    indirect_co2_weight:        0.30  # OE3-2: CO2 indirecta (grid import)\n"
        "    ev_satisfaction_weight:     0.35  # OE3-3: satisfaccion/cantidad carga EV\n"
        "    bess_solar_timing_weight:   0.07  # regla BESS: carga solar, no diesel\n"
        "    solar_weight:               0.04  # autoconsumo PV\n"
        "    grid_stability_weight:      0.02  # estabilidad red\n"
        "    cost_weight:                0.02  # costo OSINERGMIN HP/HFP\n",
    ),
]


def update_yaml(path: Path) -> None:
    if not path.exists():
        print(f"  no existe: {path.relative_to(ROOT)}")
        return
    txt = orig = path.read_text(encoding="utf-8", errors="replace")
    for pat, replacement in OLD_WEIGHT_PATS:
        txt = re.sub(pat, replacement, txt, flags=re.MULTILINE | re.DOTALL)
    # Reemplazar version references
    txt = re.sub(r"Pesos v7\.[0-9]+\s*[—-]", "Pesos v8.1 —", txt)
    txt = re.sub(r"CO2_DUAL_FOCUS v7\.[0-9]+", "CO2_DUAL_FOCUS v8.1", txt)
    txt = re.sub(r"v7\.[0-9]+ OE3", "v8.1 OE3", txt)
    _rewrite(path, txt, orig)


# ── src/dataset_builder_citylearn/rewards.py ─────────────────────────────────

def update_rewards_py() -> None:
    path = ROOT / "src" / "dataset_builder_citylearn" / "rewards.py"
    if not path.exists():
        return
    txt = orig = path.read_text(encoding="utf-8", errors="replace")

    # Actualizar docstring de MultiObjectiveWeights
    txt = re.sub(
        r'"""Pesos para funcion de recompensa multiobjetivo - CO2_DUAL_FOCUS v7\.[0-9]+ OE3\.',
        '"""Pesos para funcion de recompensa multiobjetivo - CO2_DUAL_FOCUS v8.1 OE3.',
        txt,
    )
    txt = re.sub(
        r"Pesos v7\.[0-9]+\s*[—-]\s*tres objetivos OE3",
        "Pesos v8.1 — siete componentes OE3",
        txt,
    )
    # Actualizar descripcion de pesos en docstring
    old_doc = (
        r"OE3-1: direct_co2\s+0\.25\s*[—-][^\n]*\n"
        r"\s*OE3-2: indirect_co2\s+0\.30\s*[—-][^\n]*\n"
        r"\s*OE3-3: ev_satisfaction\s+0\.25\s*[—-][^\n]*\n"
        r"\s*bess_solar_timing\s+0\.10\s*[—-][^\n]*\n"
        r"\s*solar\s+0\.05\s*[—-][^\n]*\n"
        r"\s*grid_stability\s+0\.03\s*[—-][^\n]*\n"
        r"\s*cost\s+0\.02\s*[—-][^\n]*"
    )
    new_doc = (
        "OE3-1: direct_co2        0.20 — CO2 directa (ICE->EV electrificacion)\n"
        "      OE3-2: indirect_co2       0.30 — CO2 indirecta (grid import x 0.4521 kg CO2/kWh)\n"
        "      OE3-3: ev_complete        0.35 — satisfaccion/cantidad carga EV (motos+mototaxis)\n"
        "             bess_solar_timing  0.07 — regla BESS: carga solar, NO diesel nocturno\n"
        "             solar              0.04 — autoconsumo PV\n"
        "             grid_stability     0.02 — estabilidad red (suavizado rampas)\n"
        "             cost               0.02 — costo OSINERGMIN HP/HFP"
    )
    txt = re.sub(old_doc, new_doc, txt, flags=re.MULTILINE)

    # Actualizar valores en MultiObjectiveWeights dataclass
    replacements = [
        (r"direct_co2:\s*float\s*=\s*0\.25", "direct_co2: float = 0.20"),
        (r"ev_satisfaction:\s*float\s*=\s*0\.25", "ev_satisfaction: float = 0.35"),
        (r"bess_solar_timing:\s*float\s*=\s*0\.10", "bess_solar_timing: float = 0.07"),
        (r"solar:\s*float\s*=\s*0\.05", "solar: float = 0.04"),
        (r"grid_stability:\s*float\s*=\s*0\.03", "grid_stability: float = 0.02"),
    ]
    for pat, rep in replacements:
        txt = re.sub(pat, rep, txt)

    # Actualizar create_iquitos_reward_weights co2_focus preset
    txt = re.sub(
        r'direct_co2=0\.25,\s*co2=0\.30,\s*ev_satisfaction=0\.25,\s*\n'
        r'\s*bess_solar_timing=0\.10,\s*solar=0\.05,\s*grid_stability=0\.03,\s*cost=0\.02\)',
        "direct_co2=0.20, co2=0.30, ev_satisfaction=0.35,\n"
        "              bess_solar_timing=0.07, solar=0.04, grid_stability=0.02, cost=0.02)",
        txt,
        flags=re.MULTILINE,
    )
    # Actualizar version comments
    txt = re.sub(r"CO2_DUAL_FOCUS v7\.[0-9]+", "CO2_DUAL_FOCUS v8.1", txt)
    txt = re.sub(r"v7\.[0-9]+ canonical", "v8.1 canonical", txt)
    txt = re.sub(
        r"direct_co2\(0\.25\)\+indirect_co2\(0\.30\)\+ev\(0\.25\)\+bess_solar\(0\.10\)\+solar\(0\.05",
        "direct_co2(0.20)+indirect_co2(0.30)+ev_complete(0.35)+bess_solar(0.07)+solar(0.04",
        txt,
    )
    _rewrite(path, txt, orig)


# ── src/core/reward.py ────────────────────────────────────────────────────────

def update_core_reward() -> None:
    path = ROOT / "src" / "core" / "reward.py"
    if not path.exists():
        return
    txt = orig = path.read_text(encoding="utf-8", errors="replace")

    # Actualizar co2_dual_focus preset
    txt = re.sub(
        r"(def co2_dual_focus.*?return cls\()w_direct_co2=0\.25,\s*w_co2=0\.30,\s*w_ev=0\.25,\s*w_solar=0\.05,\s*w_grid=0\.15\)",
        r"\1w_direct_co2=0.20, w_co2=0.30, w_ev=0.35, w_solar=0.04, w_grid=0.11)",
        txt,
        flags=re.DOTALL,
    )
    # Actualizar docstring del preset
    txt = re.sub(
        r'"""v7\.5 OE3: Iquitos isolated thermal grid — direct_co2=0\.25, indirect_co2=0\.30\."""',
        '"""v8.1 OE3: Iquitos isolated thermal grid — direct_co2=0.20, ev_complete=0.35, indirect=0.30."""',
        txt,
    )
    # Actualizar version comments en docstring general
    txt = re.sub(
        r"CO2_DUAL_FOCUS reward model \(v8\.0 universal\)",
        "CO2_DUAL_FOCUS reward model (v8.1 universal)",
        txt,
    )
    txt = re.sub(
        r"Validated weight sets \(v7\.5 OE3 — tres objetivos equilibrados\):",
        "Validated weight sets (v8.1 OE3 — siete componentes equilibrados):",
        txt,
    )
    txt = re.sub(
        r"CO2_DUAL_FOCUS v7\.5 \(Iquitos isolated thermal grid\):",
        "CO2_DUAL_FOCUS v8.1 (Iquitos isolated thermal grid):",
        txt,
    )
    txt = re.sub(
        r"w_direct=0\.25 \(OE3-1: CO2 directa ICE→EV\)",
        "w_direct=0.20 (OE3-1: CO2 directa ICE→EV)",
        txt,
    )
    txt = re.sub(
        r"w_ev=0\.25\s+\(OE3-3: satisfacción/cantidad carga EV\)",
        "w_ev=0.35     (OE3-3: satisfaccion/cantidad carga EV)",
        txt,
    )
    txt = re.sub(
        r"w_grid=0\.15\s+\(bess_solar_timing=0\.10 \+ grid_stability=0\.03 \+ cost=0\.02\)",
        "w_grid=0.11   (bess_solar_timing=0.07 + grid_stability=0.02 + cost=0.02)",
        txt,
    )
    _rewrite(path, txt, orig)


# ── reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md ───────────────────────────

def update_canonical_md() -> None:
    path = ROOT / "reports" / "oe3" / "AGENTES_RL_COMPARATIVA_CANONICA.md"
    if not path.exists():
        return
    txt = orig = path.read_text(encoding="utf-8", errors="replace")
    txt = re.sub(r"CO2_DUAL_FOCUS v7\.[0-9]+", "CO2_DUAL_FOCUS v8.1", txt)
    txt = re.sub(r"`CO2_DUAL_FOCUS v7\.[0-9]+`", "`CO2_DUAL_FOCUS v8.1`", txt)
    _rewrite(path, txt, orig)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "=" * 65)
    print("ACTUALIZAR PESOS CO2_DUAL_FOCUS v8.1 EN TODOS LOS ARCHIVOS")
    print()
    print("  Pesos v8.1 activos (fuente: ev_charging_wrapper.py):")
    for k, v in V81_WEIGHTS.items():
        print(f"    {k:<20} = {v}")
    print(f"    {'suma':<20} = {sum(V81_WEIGHTS.values()):.2f}")
    print("=" * 65 + "\n")

    print("[1] Configs YAML agentes...")
    for f in ["configs/agents/sac_config.yaml",
              "configs/agents/ppo_config.yaml",
              "configs/agents/a2c_config.yaml",
              "configs/agents/agents_config.yaml"]:
        update_yaml(ROOT / f)

    print("\n[2] Configs YAML globales...")
    for f in ["configs/default.yaml", "configs/default_optimized.yaml"]:
        update_yaml(ROOT / f)

    print("\n[3] src/dataset_builder_citylearn/rewards.py ...")
    update_rewards_py()

    print("\n[4] src/core/reward.py ...")
    update_core_reward()

    print("\n[5] reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md ...")
    update_canonical_md()

    print("\n" + "=" * 65)
    if updated:
        print(f"  {len(updated)} archivo(s) actualizados:")
        for f in updated:
            print(f"  -> {f}")
    else:
        print("  Sin cambios (todos los archivos ya estaban en v8.1).")
    print("=" * 65)


if __name__ == "__main__":
    main()
