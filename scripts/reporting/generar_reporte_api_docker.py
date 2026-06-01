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
        "co2_baseline_kg": detail["co2_baseline_kg"],
        "co2_control_kg": detail["co2_control_kg"],
        "co2_direct_kg": detail["co2_direct_kg"],
        "co2_indirect_kg": detail["co2_indirect_kg"],
        "co2_total_avoided_kg": sim["mean_co2_avoided_kg"],
        "co2_f2_residual_kg_yr": sim["mean_f2_kg_yr"],
        "co2_reduction_vs_f0_pct": sim["mean_reduction_pct"],
        "co2_f6a_solar_ev_kg": detail["co2_f6a_solar_ev_kg"],
        "co2_f6b_solar_mall_kg": detail["co2_f6b_solar_mall_kg"],
        "co2_f6c_solar_bess_kg": detail["co2_f6c_solar_bess_kg"],
        "co2_f6d_solar_export_kg": detail["co2_f6d_solar_export_kg"],
        "co2_f6_solar_total_kg": detail["co2_f6_solar_total_kg"],
        "co2_f7_bess_discharge_kg": detail["co2_f7_bess_discharge_kg"],
        "reward": sim["mean_reward"],
        "ev_motos_kwh": detail["ev_motos_kwh"],
        "ev_mototaxis_kwh": detail["ev_mototaxis_kwh"],
        "ev_total_kwh": sim["mean_ev_total_kwh"],
        "ev_demand_kwh": detail["ev_demand_kwh"],
        "ev_unserved_kwh": detail["ev_unserved_kwh"],
        "debt_violations": detail["debt_violations"],
        "mean_active_sockets": detail["mean_active_sockets"],
        "max_active_sockets": detail["max_active_sockets"],
        "solar_kwh": detail["solar_kwh"],
        "mall_kwh": detail["mall_kwh"],
        "grid_import_kwh": detail["grid_import_kwh"],
        "grid_export_kwh": detail["grid_export_kwh"],
        "bess_discharge_kwh": detail["bess_discharge_kwh"],
        "bess_charge_kwh": detail["bess_charge_kwh"],
        "bess_soc_min": detail["bess_soc_min"],
        "bess_soc_max": detail["bess_soc_max"],
        "bess_soc_final": detail["bess_soc_final"],
        "dispatch_pv_to_ev_kwh": detail["dispatch_pv_to_ev_kwh"],
        "dispatch_bess_to_ev_kwh": detail["dispatch_bess_to_ev_kwh"],
        "dispatch_grid_to_ev_kwh": detail["dispatch_grid_to_ev_kwh"],
        "cost_total_soles": sim["mean_cost_total_soles"],
        "cost_mecanismo_comp_soles": detail["cost_mecanismo_comp_soles"],
        "ahorro_social_total_soles": detail["ahorro_social_total_soles"],
        "cost_usd": detail["cost_usd"],
        "mean_bess_action": detail["mean_bess_action"],
        "mean_ev_motos_frac": detail["mean_ev_motos_frac"],
        "mean_ev_mototaxis_frac": detail["mean_ev_mototaxis_frac"],
    }
    for key, value in sim.get("objective_weights", {}).items():
        row[f"peso_{key}"] = value
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def _save_trace_csv(sim: dict[str, Any], path: Path) -> None:
    trace = sim["detail"][0].get("trace") or []
    if not trace:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(trace[0]))
        writer.writeheader()
        writer.writerows(trace)


def _save_figure(sim: dict[str, Any], metrics: dict[str, Any], path: Path) -> None:
    detail = sim["detail"][0]
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("Prueba operativa API Docker - A2C PVBESSCAR", fontsize=16, fontweight="bold")

    ax = axes[0, 0]
    co2_labels = ["Directa", "Indirecta", "F2 residual"]
    co2_values = [
        detail["co2_direct_kg"] / 1e6,
        detail["co2_indirect_kg"] / 1e6,
        sim["mean_f2_kg_yr"] / 1e6,
    ]
    ax.bar(co2_labels, co2_values, color=["#2f8f5b", "#4b79a1", "#d06c3f"])
    ax.set_ylabel("Mt CO2/año")
    ax.set_title(f"CO2 directo/indirecto - reduccion vs F0: {sim['mean_reduction_pct']:.2f}%")
    ax.grid(axis="y", alpha=0.25)

    ax = axes[0, 1]
    energy_labels = ["EV motos", "EV mototaxis", "Solar", "BESS desc.", "Grid import"]
    energy_values = [
        detail["ev_motos_kwh"] / 1e3,
        detail["ev_mototaxis_kwh"] / 1e3,
        detail["solar_kwh"] / 1e3,
        detail["bess_discharge_kwh"] / 1e3,
        detail["grid_import_kwh"] / 1e3,
    ]
    ax.bar(energy_labels, energy_values, color=["#4b79a1", "#8f6bb3", "#d2a24c", "#2f8f5b", "#c55252"])
    ax.set_ylabel("MWh")
    ax.set_title("Balance energetico anual")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[0, 2]
    flow_labels = ["PV->EV", "BESS->EV", "Grid->EV"]
    flow_values = [
        detail["dispatch_pv_to_ev_kwh"] / 1e3,
        detail["dispatch_bess_to_ev_kwh"] / 1e3,
        detail["dispatch_grid_to_ev_kwh"] / 1e3,
    ]
    ax.bar(flow_labels, flow_values, color=["#d2a24c", "#2f8f5b", "#c55252"])
    ax.set_ylabel("MWh")
    ax.set_title("Fuentes que alimentan las tomas EV")
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1, 0]
    f_labels = ["F6a\nSolar-EV", "F6b\nSolar-Mall", "F6c\nSolar-BESS", "F6d\nExport", "F7\nBESS"]
    f_values = [
        detail["co2_f6a_solar_ev_kg"] / 1e6,
        detail["co2_f6b_solar_mall_kg"] / 1e6,
        detail["co2_f6c_solar_bess_kg"] / 1e6,
        detail["co2_f6d_solar_export_kg"] / 1e6,
        detail["co2_f7_bess_discharge_kg"] / 1e6,
    ]
    ax.bar(f_labels, f_values, color=["#2f8f5b", "#8f6bb3", "#d2a24c", "#4b79a1", "#68717b"])
    ax.set_ylabel("Mt CO2/año")
    ax.set_title("Reduccion indirecta por solar y BESS")
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1, 1]
    service_labels = ["Demanda EV", "Carga EV", "No atendida"]
    service_values = [
        detail["ev_demand_kwh"] / 1e3,
        detail["ev_total_kwh"] / 1e3,
        detail["ev_unserved_kwh"] / 1e3,
    ]
    ax.bar(service_labels, service_values, color=["#68717b", "#2f8f5b", "#c55252"])
    ax.set_ylabel("MWh")
    ax.set_title(f"Tomas: media {detail['mean_active_sockets']:.1f}/38, max {detail['max_active_sockets']:.0f}/38")
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1, 2]
    ax.axis("off")
    text = "\n".join(
        [
            f"run_id: {sim['run_id']}",
            f"episodios: {sim['episodes']}",
            f"pasos: {detail['steps']}",
            f"tiempo episodio: {detail['elapsed_s']} s",
            f"BESS SOC min/max/final: {detail['bess_soc_min']:.2f}/{detail['bess_soc_max']:.2f}/{detail['bess_soc_final']:.2f}",
            f"debt violations: {detail['debt_violations']:.0f}",
            f"costo: S/ {_fmt(sim['mean_cost_total_soles'])}",
            f"Mongo total episodios: {metrics.get('total_episodes', 'n/d')}",
            f"generado: {datetime.now().isoformat(timespec='seconds')}",
        ]
    )
    ax.text(0.0, 0.85, text, fontsize=11, family="monospace", va="top")
    ax.set_title("Trazabilidad")

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _save_realtime_figure(sim: dict[str, Any], path: Path) -> None:
    detail = sim["detail"][0]
    trace = detail.get("trace") or []
    if not trace:
        return
    x = [row["step"] / 24.0 for row in trace]
    fig, axes = plt.subplots(4, 1, figsize=(17, 13), sharex=True)
    fig.suptitle("Traza temporal de control A2C - BESS, tomas, solar, energia y CO2", fontsize=15, fontweight="bold")

    ax = axes[0]
    ax.plot(x, [row["bess_soc"] for row in trace], color="#2f8f5b", linewidth=1.0, label="SOC BESS")
    ax.plot(x, [row["bess_action"] for row in trace], color="#4b79a1", linewidth=0.8, alpha=0.8, label="accion BESS [-1,1]")
    ax.set_ylabel("SOC / accion")
    ax.set_title("Control del BESS")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", ncol=2)

    ax = axes[1]
    ax.plot(x, [row["active_sockets"] for row in trace], color="#4b79a1", linewidth=0.9, label="tomas activas")
    ax.set_ylabel("Tomas")
    ax2 = ax.twinx()
    ax2.plot(x, [row["ev_total_kwh"] for row in trace], color="#2f8f5b", linewidth=0.7, alpha=0.75, label="EV kWh")
    ax2.plot(x, [row["solar_kwh"] for row in trace], color="#d2a24c", linewidth=0.7, alpha=0.75, label="solar kWh")
    ax2.set_ylabel("kWh/h")
    ax.set_title("Uso de tomas y generacion solar")
    ax.grid(alpha=0.25)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper right", ncol=3)

    ax = axes[2]
    ax.plot(x, [row["solar_kwh"] for row in trace], color="#d2a24c", linewidth=0.8, label="solar")
    ax.plot(x, [row["mall_kwh"] for row in trace], color="#8f6bb3", linewidth=0.8, label="mall")
    ax.plot(x, [row["grid_import_kwh"] for row in trace], color="#c55252", linewidth=0.8, label="grid import")
    ax.plot(x, [row["grid_export_kwh"] for row in trace], color="#2f8f5b", linewidth=0.8, label="grid export")
    ax.set_ylabel("kWh/h")
    ax.set_title("Balance de energia")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", ncol=4)

    ax = axes[3]
    ax.plot(x, [row["co2_direct_kg"] for row in trace], color="#2f8f5b", linewidth=0.8, label="CO2 directa")
    ax.plot(x, [row["co2_indirect_kg"] for row in trace], color="#4b79a1", linewidth=0.8, label="CO2 indirecta")
    ax.plot(x, [row["co2_f6_solar_total_kg"] for row in trace], color="#d2a24c", linewidth=0.8, label="F6 solar")
    ax.plot(x, [row["co2_f7_bess_discharge_kg"] for row in trace], color="#8f6bb3", linewidth=0.8, label="F7 BESS")
    ax.set_ylabel("kg CO2/h")
    ax.set_xlabel("Dia del anio simulado")
    ax.set_title("Reduccion de CO2 directa e indirecta")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", ncol=4)

    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=170, bbox_inches="tight")
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
| CO2 baseline F1 | {_fmt(detail["co2_baseline_kg"])} kg |
| CO2 control F2 | {_fmt(detail["co2_control_kg"])} kg |
| CO2 directo evitado | {_fmt(detail["co2_direct_kg"])} kg |
| CO2 indirecto evitado | {_fmt(detail["co2_indirect_kg"])} kg |
| CO2 evitado | {_fmt(sim["mean_co2_avoided_kg"])} kg |
| F2 residual | {_fmt(sim["mean_f2_kg_yr"])} kg/año |
| Reduccion vs F0 | {_fmt(sim["mean_reduction_pct"], 4)} % |
| Reward | {_fmt(sim["mean_reward"], 4)} |
| Energia EV total | {_fmt(sim["mean_ev_total_kwh"])} kWh |
| Demanda EV | {_fmt(detail["ev_demand_kwh"])} kWh |
| EV no atendida | {_fmt(detail["ev_unserved_kwh"])} kWh |
| Violaciones/deuda | {_fmt(detail["debt_violations"], 0)} |
| Tomas activas media/max | {_fmt(detail["mean_active_sockets"], 2)} / {_fmt(detail["max_active_sockets"], 0)} |
| Solar generada | {_fmt(detail["solar_kwh"])} kWh |
| Mall | {_fmt(detail["mall_kwh"])} kWh |
| Grid import | {_fmt(detail["grid_import_kwh"])} kWh |
| Grid export | {_fmt(detail["grid_export_kwh"])} kWh |
| BESS discharge | {_fmt(detail["bess_discharge_kwh"])} kWh |
| BESS charge | {_fmt(detail["bess_charge_kwh"])} kWh |
| BESS SOC min/max/final | {_fmt(detail["bess_soc_min"], 4)} / {_fmt(detail["bess_soc_max"], 4)} / {_fmt(detail["bess_soc_final"], 4)} |
| PV→EV | {_fmt(detail["dispatch_pv_to_ev_kwh"])} kWh |
| BESS→EV | {_fmt(detail["dispatch_bess_to_ev_kwh"])} kWh |
| Grid→EV | {_fmt(detail["dispatch_grid_to_ev_kwh"])} kWh |
| Costo total | S/ {_fmt(sim["mean_cost_total_soles"])} |

## Valores multiobjetivo

| Objetivo / componente | Peso | Valor anual |
|---|---:|---:|
| CO2 directa (ICE→EV) | {sim["objective_weights"].get("co2_directa", 0):.2f} | {_fmt(detail["co2_direct_kg"])} kg |
| CO2 indirecta grid | {sim["objective_weights"].get("co2_indirecta_grid", 0):.2f} | {_fmt(detail["co2_indirect_kg"])} kg |
| Servicio EV sin deuda | {sim["objective_weights"].get("servicio_ev_sin_deuda", 0):.2f} | EV no atendida {_fmt(detail["ev_unserved_kwh"])} kWh; deuda {_fmt(detail["debt_violations"], 0)} |
| BESS carga solar | {sim["objective_weights"].get("bess_carga_solar", 0):.2f} | BESS carga {_fmt(detail["bess_charge_kwh"])} kWh; descarga {_fmt(detail["bess_discharge_kwh"])} kWh |
| Autoconsumo solar | {sim["objective_weights"].get("autoconsumo_solar", 0):.2f} | Solar {_fmt(detail["solar_kwh"])} kWh; export {_fmt(detail["grid_export_kwh"])} kWh |
| Estabilidad grid | {sim["objective_weights"].get("estabilidad_grid", 0):.2f} | Grid import {_fmt(detail["grid_import_kwh"])} kWh |
| Costo OSINERGMIN | {sim["objective_weights"].get("costo_osinergmin", 0):.2f} | S/ {_fmt(detail["cost_total_soles"])} |

## Desglose CO2 indirecto

| Formula | Valor |
|---|---:|
| F6a Solar→EV | {_fmt(detail["co2_f6a_solar_ev_kg"])} kg |
| F6b Solar→Mall | {_fmt(detail["co2_f6b_solar_mall_kg"])} kg |
| F6c Solar→BESS | {_fmt(detail["co2_f6c_solar_bess_kg"])} kg |
| F6d Solar→Export | {_fmt(detail["co2_f6d_solar_export_kg"])} kg |
| F6 Solar total | {_fmt(detail["co2_f6_solar_total_kg"])} kg |
| F7 BESS descarga | {_fmt(detail["co2_f7_bess_discharge_kg"])} kg |

## Persistencia

- Total de episodios en MongoDB: `{metrics.get("total_episodes", "n/d")}`
- Figura: `figuras/resumen_operativo.png`
- Figura temporal: `figuras/control_tiempo_real.png`
- Dashboard WebSocket: `{BASE_URL}/dashboard/realtime`
- JSON completo: `simulacion_prueba.json`
- Trace horario JSON: `trace_simulacion.json`
- CSV: `simulacion_prueba.csv`
- Trace horario CSV: `trace_simulacion.csv`
"""
    path.write_text(content, encoding="utf-8")


def _save_html(sim: dict[str, Any], metrics: dict[str, Any], path: Path) -> None:
    detail = sim["detail"][0]
    rows = [
        ("Run ID", sim["run_id"]),
        ("Agente", sim["agent"]),
        ("Episodios", sim["episodes"]),
        ("Pasos", detail["steps"]),
        ("CO2 baseline F1", f"{_fmt(detail['co2_baseline_kg'])} kg"),
        ("CO2 control F2", f"{_fmt(detail['co2_control_kg'])} kg"),
        ("CO2 directo evitado", f"{_fmt(detail['co2_direct_kg'])} kg"),
        ("CO2 indirecto evitado", f"{_fmt(detail['co2_indirect_kg'])} kg"),
        ("CO2 evitado", f"{_fmt(sim['mean_co2_avoided_kg'])} kg"),
        ("F2 residual", f"{_fmt(sim['mean_f2_kg_yr'])} kg/año"),
        ("Reduccion vs F0", f"{_fmt(sim['mean_reduction_pct'], 4)} %"),
        ("Reward", _fmt(sim["mean_reward"], 4)),
        ("Energia EV total", f"{_fmt(sim['mean_ev_total_kwh'])} kWh"),
        ("Demanda EV", f"{_fmt(detail['ev_demand_kwh'])} kWh"),
        ("EV no atendida", f"{_fmt(detail['ev_unserved_kwh'])} kWh"),
        ("Violaciones/deuda", _fmt(detail["debt_violations"], 0)),
        ("Tomas activas media/max", f"{_fmt(detail['mean_active_sockets'], 2)} / {_fmt(detail['max_active_sockets'], 0)}"),
        ("Solar generada", f"{_fmt(detail['solar_kwh'])} kWh"),
        ("Mall", f"{_fmt(detail['mall_kwh'])} kWh"),
        ("Grid import", f"{_fmt(detail['grid_import_kwh'])} kWh"),
        ("Grid export", f"{_fmt(detail['grid_export_kwh'])} kWh"),
        ("BESS descarga", f"{_fmt(detail['bess_discharge_kwh'])} kWh"),
        ("BESS carga", f"{_fmt(detail['bess_charge_kwh'])} kWh"),
        ("BESS SOC min/max/final", f"{_fmt(detail['bess_soc_min'], 4)} / {_fmt(detail['bess_soc_max'], 4)} / {_fmt(detail['bess_soc_final'], 4)}"),
        ("PV→EV", f"{_fmt(detail['dispatch_pv_to_ev_kwh'])} kWh"),
        ("BESS→EV", f"{_fmt(detail['dispatch_bess_to_ev_kwh'])} kWh"),
        ("Grid→EV", f"{_fmt(detail['dispatch_grid_to_ev_kwh'])} kWh"),
        ("Costo total", f"S/ {_fmt(sim['mean_cost_total_soles'])}"),
        ("Costo mecanismo compensacion", f"S/ {_fmt(detail['cost_mecanismo_comp_soles'])}"),
        ("Ahorro social", f"S/ {_fmt(detail['ahorro_social_total_soles'])}"),
        ("Mongo episodios", metrics.get("total_episodes", "n/d")),
    ]
    tr = "\n".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>" for k, v in rows)
    weights = sim.get("objective_weights", {})
    objective_rows = [
        ("CO2 directa (ICE→EV)", weights.get("co2_directa", 0), f"{_fmt(detail['co2_direct_kg'])} kg"),
        ("CO2 indirecta grid", weights.get("co2_indirecta_grid", 0), f"{_fmt(detail['co2_indirect_kg'])} kg"),
        ("Servicio EV sin deuda", weights.get("servicio_ev_sin_deuda", 0), f"EV no atendida {_fmt(detail['ev_unserved_kwh'])} kWh; deuda {_fmt(detail['debt_violations'], 0)}"),
        ("BESS carga solar", weights.get("bess_carga_solar", 0), f"carga {_fmt(detail['bess_charge_kwh'])} kWh; descarga {_fmt(detail['bess_discharge_kwh'])} kWh"),
        ("Autoconsumo solar", weights.get("autoconsumo_solar", 0), f"solar {_fmt(detail['solar_kwh'])} kWh; export {_fmt(detail['grid_export_kwh'])} kWh"),
        ("Estabilidad grid", weights.get("estabilidad_grid", 0), f"grid import {_fmt(detail['grid_import_kwh'])} kWh"),
        ("Costo OSINERGMIN", weights.get("costo_osinergmin", 0), f"S/ {_fmt(detail['cost_total_soles'])}"),
    ]
    objective_tr = "\n".join(
        f"<tr><th>{html.escape(str(k))}</th><td>{float(w):.2f}</td><td>{html.escape(str(v))}</td></tr>"
        for k, w, v in objective_rows
    )
    co2_rows = [
        ("F6a Solar→EV", detail["co2_f6a_solar_ev_kg"]),
        ("F6b Solar→Mall", detail["co2_f6b_solar_mall_kg"]),
        ("F6c Solar→BESS", detail["co2_f6c_solar_bess_kg"]),
        ("F6d Solar→Export", detail["co2_f6d_solar_export_kg"]),
        ("F6 Solar total", detail["co2_f6_solar_total_kg"]),
        ("F7 BESS descarga", detail["co2_f7_bess_discharge_kg"]),
    ]
    co2_tr = "\n".join(
        f"<tr><th>{html.escape(name)}</th><td>{_fmt(value)} kg</td></tr>"
        for name, value in co2_rows
    )
    content = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Prueba API Docker A2C</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; background: #f7f9fb; }}
    h1 {{ margin-bottom: 4px; }}
    h2 {{ margin-top: 28px; }}
    .meta {{ color: #5b6773; margin-bottom: 24px; }}
    table {{ border-collapse: collapse; min-width: 760px; margin-bottom: 24px; background: white; }}
    th, td {{ border: 1px solid #d8dee4; padding: 10px 12px; text-align: left; }}
    th {{ background: #f3f6f8; width: 240px; }}
    img {{ max-width: 1300px; width: 100%; border: 1px solid #d8dee4; background: white; margin-bottom: 18px; }}
    a {{ color: #1b6ca8; }}
  </style>
</head>
<body>
  <h1>Prueba operativa API Docker - A2C</h1>
  <div class="meta">Generado: {datetime.now().isoformat(timespec='seconds')} | Endpoint: {html.escape(BASE_URL)}</div>
  <p><a href="{html.escape(BASE_URL)}/dashboard/realtime">Abrir dashboard en tiempo real por WebSocket</a></p>
  <h2>Resumen operativo</h2>
  <table>{tr}</table>
  <h2>Valores multiobjetivo</h2>
  <table><tr><th>Objetivo</th><th>Peso</th><th>Valor anual</th></tr>{objective_tr}</table>
  <h2>Desglose CO2 indirecto</h2>
  <table>{co2_tr}</table>
  <h2>Figura resumen</h2>
  <img src="figuras/resumen_operativo.png" alt="Figura resumen operativo">
  <h2>Figura temporal: BESS, tomas, solar, energia y CO2</h2>
  <img src="figuras/control_tiempo_real.png" alt="Figura temporal de control">
  <p>
    Archivos:
    <a href="simulacion_prueba.json">JSON completo</a> |
    <a href="simulacion_prueba.csv">CSV</a> |
    <a href="trace_simulacion.json">Trace JSON</a> |
    <a href="trace_simulacion.csv">Trace CSV</a> |
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
        "include_trace": True,
        "label": f"prueba_visible_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    }
    started = time.perf_counter()
    sim = _request("POST", "/simulate", api_key, body)
    api_elapsed = round(time.perf_counter() - started, 2)
    metrics = _request("GET", "/metrics", api_key)
    history = _request("GET", "/history?page=1&per_page=10", api_key)

    (OUT / "health.json").write_text(json.dumps(health, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "simulacion_prueba.json").write_text(json.dumps(sim, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "trace_simulacion.json").write_text(
        json.dumps(sim["detail"][0].get("trace") or [], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "history.json").write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "tiempo_api.txt").write_text(f"{api_elapsed} s\n", encoding="utf-8")

    _save_csv(sim, OUT / "simulacion_prueba.csv")
    _save_trace_csv(sim, OUT / "trace_simulacion.csv")
    _save_figure(sim, metrics, FIG_DIR / "resumen_operativo.png")
    _save_realtime_figure(sim, FIG_DIR / "control_tiempo_real.png")
    _save_markdown(sim, metrics, OUT / "resumen_simulacion.md")
    _save_html(sim, metrics, OUT / "index.html")

    print(f"OK run_id={sim['run_id']} api_elapsed_s={api_elapsed}")
    print(f"HTML: {OUT / 'index.html'}")
    print(f"Figura: {FIG_DIR / 'resumen_operativo.png'}")
    print(f"Figura temporal: {FIG_DIR / 'control_tiempo_real.png'}")
    print(f"Dashboard tiempo real: {BASE_URL}/dashboard/realtime")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
