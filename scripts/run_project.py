#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lanzador maestro del proyecto pvbesscar.

Modos de ejecucion:
  quick    — verifica datos + cadena OE3 (usa checkpoints existentes)  ~2 min
  analysis — solo cadena OE3: estadisticas, figuras, tablas             ~1 min
  train    — entrena los 3 agentes (A2C recomendado primero)            ~4 h CPU
  full     — pipeline completo: OE2 + train + OE3                       ~5 h CPU
  test     — suite de 106 tests unitarios e integracion                 ~5 s

Uso:
  python scripts/run_project.py --mode quick
  python scripts/run_project.py --mode analysis
  python scripts/run_project.py --mode train --agent A2C
  python scripts/run_project.py --mode full
  python scripts/run_project.py --mode test
"""
from __future__ import annotations

import argparse
import runpy
import subprocess
import sys
import time
import traceback
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SEP  = "-" * 65
SEP2 = "=" * 65

AGENT_TRAIN_SCRIPTS = {
    "A2C": ROOT / "scripts" / "train" / "train_a2c_citylearn.py",
    "PPO": ROOT / "scripts" / "train" / "train_ppo_citylearn.py",
    "SAC": ROOT / "scripts" / "train" / "train_sac_citylearn.py",
}

STEPS: dict[str, list[tuple[str, Path | list[str]]]] = {
    "verify_data": [
        ("Verificar datos OE2 y CityLearn", ROOT / "scripts" / "verification" / "verify_citylearn_data.py"),
    ],
    "oe2_pipeline": [
        ("Generar dataset CityLearn v2 desde OE2", ROOT / "scripts" / "generate_oe2_datasets.py"),
    ],
    "train_baseline": [
        ("Baseline sin RL (despacho pasivo)", ROOT / "scripts" / "train" / "run_baseline.py"),
    ],
    "train_a2c": [
        ("Entrenar A2C (agente seleccionado, ~22 min CPU)", ROOT / "scripts" / "train" / "train_a2c_citylearn.py"),
    ],
    "train_ppo": [
        ("Entrenar PPO (~23 min CPU)", ROOT / "scripts" / "train" / "train_ppo_citylearn.py"),
    ],
    "train_sac": [
        ("Entrenar SAC (~172 min CPU)", ROOT / "scripts" / "train" / "train_sac_citylearn.py"),
    ],
    "oe3_analysis": [
        ("Cadena OE3: estadisticas + figuras + tablas", ROOT / "scripts" / "reporting" / "run_all_oe3.py"),
    ],
    "tests": [
        ("Suite de tests (106 unitarios + integracion)", ["pytest", "tests/", "-q", "--tb=short"]),
    ],
}

PIPELINES: dict[str, list[str]] = {
    "quick":    ["verify_data", "oe3_analysis"],
    "analysis": ["oe3_analysis"],
    "train":    [],  # dinámico segun --agent
    "full":     ["oe2_pipeline", "train_baseline", "train_a2c", "train_ppo", "train_sac", "oe3_analysis"],
    "test":     ["tests"],
}


def run_script(label: str, target: Path | list[str]) -> bool:
    print(f"\n{SEP}")
    print(f"[PASO] {label}")
    if isinstance(target, Path):
        print(f"       {target.relative_to(ROOT)}")
    print(SEP)
    t0 = time.time()
    try:
        if isinstance(target, list):
            result = subprocess.run(
                [sys.executable, "-m"] + target if target[0] == "pytest" else [sys.executable] + target,
                cwd=str(ROOT),
            )
            ok = result.returncode == 0
        else:
            runpy.run_path(str(target), run_name="__main__")
            ok = True
        elapsed = time.time() - t0
        status = "OK" if ok else "FALLO"
        print(f"\n  {status} completado en {elapsed:.1f}s")
        return ok
    except Exception:  # noqa: BLE001
        print("\n  ERROR:")
        traceback.print_exc()
        return False


def run_pytest() -> bool:
    print(f"\n{SEP}")
    print("[PASO] Suite de tests (106 unitarios + integracion)")
    print(SEP)
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
        cwd=str(ROOT),
    )
    elapsed = time.time() - t0
    ok = result.returncode == 0
    print(f"\n  {'OK' if ok else 'FALLO'} en {elapsed:.1f}s")
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Lanzador maestro pvbesscar")
    parser.add_argument(
        "--mode",
        choices=["quick", "analysis", "train", "full", "test"],
        default="quick",
        help="Modo de ejecucion (default: quick)",
    )
    parser.add_argument(
        "--agent",
        choices=["A2C", "PPO", "SAC", "all"],
        default="all",
        help="Agente a entrenar en modo train (default: all)",
    )
    args = parser.parse_args()

    print(f"\n{SEP2}")
    print(f"PVBESSCAR — LANZADOR MAESTRO")
    print(f"Modo: {args.mode.upper()}")
    if args.mode == "train":
        print(f"Agente: {args.agent}")
    print(f"Raiz: {ROOT}")
    print(SEP2)

    # Construir lista de pasos
    if args.mode == "train":
        if args.agent == "all":
            steps_keys = ["train_baseline", "train_a2c", "train_ppo", "train_sac"]
        else:
            steps_keys = [f"train_{args.agent.lower()}"]
    else:
        steps_keys = PIPELINES[args.mode]

    if not steps_keys:
        print("Nada que ejecutar.")
        return

    print(f"\nPasos a ejecutar ({len(steps_keys)}):")
    for k in steps_keys:
        for label, _ in STEPS[k]:
            print(f"  - {label}")

    t_start = time.time()
    results: list[tuple[str, bool]] = []

    for key in steps_keys:
        for label, target in STEPS[key]:
            if key == "tests":
                ok = run_pytest()
            else:
                ok = run_script(label, target)
            results.append((label, ok))
            if not ok and args.mode != "full":
                print(f"\n  Detenido por error en: {label}")
                break

    # Resumen
    print(f"\n{SEP2}")
    print("RESUMEN")
    print(SEP2)
    for label, ok in results:
        print(f"  {'OK  ' if ok else 'FALLO'} {label}")

    n_ok   = sum(1 for _, ok in results if ok)
    n_fail = len(results) - n_ok
    elapsed_total = time.time() - t_start
    print(f"\n  {n_ok}/{len(results)} pasos completados | Tiempo total: {elapsed_total/60:.1f} min")

    if n_fail:
        print(f"  {n_fail} paso(s) con error")
        sys.exit(1)
    else:
        print(f"\n  Pipeline '{args.mode}' completado exitosamente.")
        if args.mode in ("quick", "full", "analysis"):
            print("  Agente seleccionado: A2C (score multiobjetivo 50 episodios)")
            print("  Reportes: reports/oe3/ | Estadisticas: outputs/estadistica_oe3/")
            print("  Figuras:  outputs/docx/graficas/")
    print(SEP2)


if __name__ == "__main__":
    main()
