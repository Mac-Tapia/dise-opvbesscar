from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import json


@dataclass(frozen=True)
class LocationSummary:
    site_name: str
    area_techada_m2: float
    area_estacionamiento_m2: float
    area_techada_util_m2: float
    coverage_required_pct: float
    distance_to_substation_m: float
    vehicles_peak_motos: int
    vehicles_peak_mototaxis: int
    dwell_hours_min: float
    area_per_moto_m2: float
    area_per_mototaxi_m2: float
    parking_capacity_motos: int
    parking_capacity_mototaxis: int
    parking_capacity_total: int
    access_notes: str
    security_notes: str
    restrictions_notes: str
    grid_continuity: str
    power_factor: float
    available_capacity_kva: Optional[float]
    required_capacity_kva: Optional[float]
    capacity_source: str
    chargers_peak_kw: Optional[float]
    chargers_installed_kw: Optional[float]
    results_path: str
    report_path: str


def _normalize_fraction(value: float) -> float:
    if value <= 0:
        return 0.0
    if value > 1.0:
        return value / 100.0
    return value


def _load_chargers_results(chargers_path: Optional[Path]) -> Dict[str, Any]:
    if chargers_path is None or not chargers_path.exists():
        return {}
    return json.loads(chargers_path.read_text(encoding="utf-8"))


def build_location_summary(
    cfg: Dict[str, Any],
    chargers_results_path: Optional[Path],
    out_dir: Path,
    reports_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    site_cfg = cfg.get("oe1", {}).get("site", {})
    grid_cfg = cfg.get("oe1", {}).get("grid_connection", {})
    ev_cfg = cfg.get("oe2", {}).get("ev_fleet", {})

    site_name = str(site_cfg.get("name", "Mall de Iquitos"))
    area_techada_m2 = float(site_cfg.get("area_techada_m2", 0.0))
    area_estacionamiento_m2 = float(site_cfg.get("area_estacionamiento_m2", 0.0))
    coverage_required_pct = float(site_cfg.get("coverage_required_pct", 0.0))
    coverage_factor = _normalize_fraction(coverage_required_pct)
    area_techada_util_m2 = area_techada_m2 * coverage_factor

    distance_to_substation_m = float(site_cfg.get("distance_to_substation_m", 0.0))
    vehicles_peak_motos = int(site_cfg.get("vehicles_peak_motos", 0))
    vehicles_peak_mototaxis = int(site_cfg.get("vehicles_peak_mototaxis", 0))
    dwell_hours_min = float(site_cfg.get("dwell_hours_min", 0.0))

    area_per_moto_m2 = float(site_cfg.get("area_per_moto_m2", 0.0))
    area_per_mototaxi_m2 = float(site_cfg.get("area_per_mototaxi_m2", 0.0))

    parking_capacity_motos = int(area_estacionamiento_m2 / area_per_moto_m2) if area_per_moto_m2 > 0 else 0
    parking_capacity_mototaxis = int(area_estacionamiento_m2 / area_per_mototaxi_m2) if area_per_mototaxi_m2 > 0 else 0

    total_vehicles = vehicles_peak_motos + vehicles_peak_mototaxis
    if total_vehicles > 0:
        weighted_area = (
            vehicles_peak_motos * area_per_moto_m2 +
            vehicles_peak_mototaxis * area_per_mototaxi_m2
        ) / total_vehicles
    else:
        weighted_area = area_per_moto_m2 or area_per_mototaxi_m2
    parking_capacity_total = int(area_estacionamiento_m2 / weighted_area) if weighted_area > 0 else 0

    access_notes = str(site_cfg.get("access_notes", "")).strip()
    security_notes = str(site_cfg.get("security_notes", "")).strip()
    restrictions_notes = str(site_cfg.get("restrictions_notes", "")).strip()

    grid_continuity = str(grid_cfg.get("continuity", "")).strip()
    power_factor = float(grid_cfg.get("power_factor", 0.95))
    available_capacity_kva = grid_cfg.get("available_capacity_kva")
    available_capacity_kva = float(available_capacity_kva) if available_capacity_kva is not None else None

    chargers_data = _load_chargers_results(chargers_results_path)
    chargers_peak_kw = float(chargers_data.get("peak_power_kw", 0.0)) if chargers_data else None
    chargers_installed_kw = float(chargers_data.get("potencia_total_instalada_kw", 0.0)) if chargers_data else None

    if (chargers_installed_kw is None or chargers_installed_kw <= 0) and ev_cfg:
        motos_count = float(ev_cfg.get("motos_count", 0))
        mototaxis_count = float(ev_cfg.get("mototaxis_count", 0))
        moto_kw = float(ev_cfg.get("charger_power_kw_moto", 0))
        mototaxi_kw = float(ev_cfg.get("charger_power_kw_mototaxi", 0))
        fallback_installed_kw = motos_count * moto_kw + mototaxis_count * mototaxi_kw
        if fallback_installed_kw > 0:
            chargers_installed_kw = fallback_installed_kw
        if chargers_peak_kw is None or chargers_peak_kw <= 0:
            utilization = float(ev_cfg.get("utilization", 1.0))
            chargers_peak_kw = fallback_installed_kw * utilization if fallback_installed_kw > 0 else None

    required_capacity_kva = None
    capacity_source = "config"
    if chargers_peak_kw is not None and chargers_peak_kw > 0 and power_factor > 0:
        required_capacity_kva = chargers_peak_kw / power_factor
        capacity_source = "estimated_from_peak_power"
    elif chargers_installed_kw is not None and chargers_installed_kw > 0 and power_factor > 0:
        required_capacity_kva = chargers_installed_kw / power_factor
        capacity_source = "estimated_from_installed_power"

    summary = LocationSummary(
        site_name=site_name,
        area_techada_m2=area_techada_m2,
        area_estacionamiento_m2=area_estacionamiento_m2,
        area_techada_util_m2=area_techada_util_m2,
        coverage_required_pct=coverage_required_pct,
        distance_to_substation_m=distance_to_substation_m,
        vehicles_peak_motos=vehicles_peak_motos,
        vehicles_peak_mototaxis=vehicles_peak_mototaxis,
        dwell_hours_min=dwell_hours_min,
        area_per_moto_m2=area_per_moto_m2,
        area_per_mototaxi_m2=area_per_mototaxi_m2,
        parking_capacity_motos=parking_capacity_motos,
        parking_capacity_mototaxis=parking_capacity_mototaxis,
        parking_capacity_total=parking_capacity_total,
        access_notes=access_notes,
        security_notes=security_notes,
        restrictions_notes=restrictions_notes,
        grid_continuity=grid_continuity,
        power_factor=power_factor,
        available_capacity_kva=available_capacity_kva,
        required_capacity_kva=required_capacity_kva,
        capacity_source=capacity_source,
        chargers_peak_kw=chargers_peak_kw,
        chargers_installed_kw=chargers_installed_kw,
        results_path=str((out_dir / "location_summary.json").resolve()),
        report_path=str((reports_dir / "oe1" / "location_summary.md").resolve()) if reports_dir else "",
    )

    return summary.__dict__


def write_location_outputs(
    summary: Dict[str, Any],
    out_dir: Path,
    reports_dir: Optional[Path] = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "location_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    if reports_dir is None:
        return

    report_dir = reports_dir / "oe1"
    report_dir.mkdir(parents=True, exist_ok=True)

    md = []
    md.append("# OE1 - Location Summary\n")
    md.append("## Site Selection (Table 9)\n")
    md.append("| Item | Value | Unit |\n")
    md.append("| --- | --- | --- |\n")
    md.append(f"| Site | {summary.get('site_name', '')} | - |\n")
    md.append(f"| Area techada | {summary.get('area_techada_m2', 0):,.1f} | m2 |\n")
    md.append(f"| Area techada util | {summary.get('area_techada_util_m2', 0):,.1f} | m2 |\n")
    md.append(f"| Area estacionamiento | {summary.get('area_estacionamiento_m2', 0):,.1f} | m2 |\n")
    md.append(f"| Distancia a subestacion | {summary.get('distance_to_substation_m', 0):,.1f} | m |\n")
    md.append(f"| Motos en hora pico | {summary.get('vehicles_peak_motos', 0):,} | unidades |\n")
    md.append(f"| Mototaxis en hora pico | {summary.get('vehicles_peak_mototaxis', 0):,} | unidades |\n")
    md.append(f"| Permanencia minima | {summary.get('dwell_hours_min', 0):.1f} | horas |\n")
    md.append(f"| Capacidad estacionamiento (motos) | {summary.get('parking_capacity_motos', 0):,} | plazas |\n")
    md.append(f"| Capacidad estacionamiento (mototaxis) | {summary.get('parking_capacity_mototaxis', 0):,} | plazas |\n")
    md.append(f"| Capacidad estacionamiento (total) | {summary.get('parking_capacity_total', 0):,} | plazas |\n")

    md.append("\n## Accesibilidad y seguridad\n")
    md.append(f"- Access: {summary.get('access_notes', '')}\n")
    md.append(f"- Security: {summary.get('security_notes', '')}\n")
    md.append(f"- Restrictions: {summary.get('restrictions_notes', '')}\n")

    md.append("\n## Grid Connection\n")
    md.append("| Item | Value | Unit |\n")
    md.append("| --- | --- | --- |\n")
    md.append(f"| Continuity | {summary.get('grid_continuity', '')} | - |\n")
    md.append(f"| Power factor | {summary.get('power_factor', 0):.2f} | - |\n")
    md.append(f"| Required capacity | {summary.get('required_capacity_kva', 0) or 0:.1f} | kVA |\n")
    md.append(f"| Available capacity | {summary.get('available_capacity_kva', 0) or 0:.1f} | kVA |\n")
    md.append(f"| Capacity source | {summary.get('capacity_source', '')} | - |\n")

    (report_dir / "location_summary.md").write_text("".join(md), encoding="utf-8")
