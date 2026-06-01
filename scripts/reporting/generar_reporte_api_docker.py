#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera evidencia visible de una simulacion A2C ejecutada por la API Docker."""
from __future__ import annotations

import csv
import html
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "api_docker_test" / "latest"
FIG_DIR = OUT / "figuras"
BASE_URL = os.getenv("PVBESSCAR_API_URL", "http://localhost:8000")


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _request(method: str, path: str, api_key: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fmt(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def _save_csv(sim: dict[str, Any], path: Path) -> None:
    detail = sim["detail"][0]
    row = {
        "run_id": sim["run_id"],
        "agent": sim["agent"],
        "obs_dim": sim["obs_dim"],
        "episodes": sim["episodes"],
        "steps": detail["steps"],
        "elapsed_s": detail["elapsed_s"],
        "co2_total_avoided_kg": sim["mean_co2_avoided_kg"],
        "co2_f2_residual_kg_yr": sim["mean_f2_kg_yr"],
        "co2_reduction_vs_f0_pct": sim["mean_reduction_pct"],
        "reward": sim["mean_reward"],
        "ev_motos_kwh": detail["ev_motos_kwh"],
        "ev_mototaxis_kwh": detail["ev_mototaxis_kwh"],
        "ev_total_kwh": sim["mean_ev_total_kwh"],
        "grid_import_kwh": detail["grid_import_kwh"],
        "bess_discharge_kwh": detail["bess_discharge_kwh"],
        "cost_total_soles": sim["mean_cost_total_soles"],
    }
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def _save_figure(sim: dict[str, Any], metrics: dict[str, Any], path: Path) -> None:
    detail = sim["detail"][0]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle("Prueba operativa API Docker - A2C PVBESSCAR", fontsize=16, fontweight="bold")

    ax = axes[0][0]
    co2_labels = ["CO2 evitado", "F2 residual"]
    co2_values = [sim["mean_co2_avoided_kg"] / 1e6, sim["mean_f2_kg_yr"] / 1e6]
    ax.bar(co2_labels, co2_values, color=["#2f8f5b", "#d06c3f"])
    ax.set_ylabel("Mt CO2/año")
    ax.set_title(f"Reduccion vs F0: {sim['mean_reduction_pct']:.2f}%")
    ax.grid(axis="y", alpha=0.25)

    ax = axes[0][1]
    energy_labels = ["EV motos", "EV mototaxis", "BESS descarga", "Grid import"]
    energy_values = [
        detail["ev_motos_kwh"] / 1e3,
        detail["ev_mototaxis_kwh"] / 1e3,
        detail["bess_discharge_kwh"] / 1e3,
        detail["grid_import_kwh"] / 1e3,
    ]
    ax.bar(energy_labels, energy_values, color=["#4b79a1", "#8f6bb3", "#2f8f5b", "#c55252"])
    ax.set_ylabel("MWh")
    ax.set_title("Energia anual simulada")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1][0]
    cost_reward_labels = ["Costo total\n(M S/)", "Reward"]
    cost_reward_values = [sim["mean_cost_total_soles"] / 1e6, sim["mean_reward"]]
    ax.bar(cost_reward_labels, cost_reward_values, color=["#d2a24c", "#4b79a1"])
    ax.set_title("Costo y recompensa")
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1][1]
    ax.axis("off")
    text = "\n".join(
        [
            f"run_id: {sim['run_id']}",
            f"episodios: {sim['episodes']}",
            f"pasos: {detail['steps']}",
            f"tiempo episodio: {detail['elapsed_s']} s",
            f"Mongo total episodios: {metrics.get('total_episodes', 'n/d')}",
            f"generado: {datetime.now().isoformat(timespec='seconds')}",
        ]
    )
    ax.text(0.0, 0.85, text, fontsize=11, family="monospace", va="top")
    ax.set_title("Trazabilidad")

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _save_markdown(sim: dict[str, Any], metrics: dict[str, Any], path: Path) -> None:
    detail = sim["detail"][0]
    content = f"""# Simulacion de prueba API Docker

- Endpoint: `{BASE_URL}/simulate`
- Run ID: `{sim["run_id"]}`
- Agente: `{sim["agent"]}`
- Episodios: `{sim["episodes"]}`
- Pasos simulados: `{detail["steps"]}`
- Tiempo de episodio: `{detail["elapsed_s"]} s`

## Resultados

| Indicador | Valor |
|---|---:|
| CO2 evitado | {_fmt(sim["mean_co2_avoided_kg"])} kg |
| F2 residual | {_fmt(sim["mean_f2_kg_yr"])} kg/año |
| Reduccion vs F0 | {_fmt(sim["mean_reduction_pct"], 4)} % |
| Reward | {_fmt(sim["mean_reward"], 4)} |
| Energia EV total | {_fmt(sim["mean_ev_total_kwh"])} kWh |
| Grid import | {_fmt(detail["grid_import_kwh"])} kWh |
| BESS discharge | {_fmt(detail["bess_discharge_kwh"])} kWh |
| Costo total | S/ {_fmt(sim["mean_cost_total_soles"])} |

## Persistencia

- Total de episodios en MongoDB: `{metrics.get("total_episodes", "n/d")}`
- Figura: `figuras/resumen_operativo.png`
- JSON completo: `simulacion_prueba.json`
- CSV: `simulacion_prueba.csv`
"""
    path.write_text(content, encoding="utf-8")


def _save_html(sim: dict[str, Any], metrics: dict[str, Any], path: Path) -> None:
    detail = sim["detail"][0]
    rows = [
        ("Run ID", sim["run_id"]),
        ("Agente", sim["agent"]),
        ("Episodios", sim["episodes"]),
        ("Pasos", detail["steps"]),
        ("CO2 evitado", f"{_fmt(sim['mean_co2_avoided_kg'])} kg"),
        ("F2 residual", f"{_fmt(sim['mean_f2_kg_yr'])} kg/año"),
        ("Reduccion vs F0", f"{_fmt(sim['mean_reduction_pct'], 4)} %"),
        ("Reward", _fmt(sim["mean_reward"], 4)),
        ("Energia EV total", f"{_fmt(sim['mean_ev_total_kwh'])} kWh"),
        ("Costo total", f"S/ {_fmt(sim['mean_cost_total_soles'])}"),
        ("Mongo episodios", metrics.get("total_episodes", "n/d")),
    ]
    tr = "\n".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>" for k, v in rows)
    content = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Prueba API Docker A2C</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #5b6773; margin-bottom: 24px; }}
    table {{ border-collapse: collapse; min-width: 680px; margin-bottom: 24px; }}
    th, td {{ border: 1px solid #d8dee4; padding: 10px 12px; text-align: left; }}
    th {{ background: #f3f6f8; width: 240px; }}
    img {{ max-width: 1100px; width: 100%; border: 1px solid #d8dee4; }}
    a {{ color: #1b6ca8; }}
  </style>
</head>
<body>
  <h1>Prueba operativa API Docker - A2C</h1>
  <div class="meta">Generado: {datetime.now().isoformat(timespec='seconds')} | Endpoint: {html.escape(BASE_URL)}</div>
  <table>{tr}</table>
  <img src="figuras/resumen_operativo.png" alt="Figura resumen operativo">
  <p>
    Archivos:
    <a href="simulacion_prueba.json">JSON completo</a> |
    <a href="simulacion_prueba.csv">CSV</a> |
    <a href="resumen_simulacion.md">Resumen Markdown</a>
  </p>
</body>
</html>
"""
    path.write_text(content, encoding="utf-8")


def main() -> int:
    env = _read_env(ROOT / ".env.local")
    api_key = env.get("API_KEY", "")

    OUT.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    health = _request("GET", "/health", api_key)
    if not health.get("model_ready"):
        raise RuntimeError(f"API no esta lista: {health}")

    body = {
        "episodes": 1,
        "deterministic": True,
        "label": f"prueba_visible_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    }
    started = time.perf_counter()
    sim = _request("POST", "/simulate", api_key, body)
    api_elapsed = round(time.perf_counter() - started, 2)
    metrics = _request("GET", "/metrics", api_key)
    history = _request("GET", "/history?page=1&per_page=10", api_key)

    (OUT / "health.json").write_text(json.dumps(health, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "simulacion_prueba.json").write_text(json.dumps(sim, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "history.json").write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "tiempo_api.txt").write_text(f"{api_elapsed} s\n", encoding="utf-8")

    _save_csv(sim, OUT / "simulacion_prueba.csv")
    _save_figure(sim, metrics, FIG_DIR / "resumen_operativo.png")
    _save_markdown(sim, metrics, OUT / "resumen_simulacion.md")
    _save_html(sim, metrics, OUT / "index.html")

    print(f"OK run_id={sim['run_id']} api_elapsed_s={api_elapsed}")
    print(f"HTML: {OUT / 'index.html'}")
    print(f"Figura: {FIG_DIR / 'resumen_operativo.png'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
