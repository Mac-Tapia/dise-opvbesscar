#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oe2_metadata.py — Lector automático de metadatos reales OE2.

Lee los JSONs generados por solar_pvlib.py, bess.py y chargers.py
para derivar constantes del sistema en tiempo de ejecución.
Cada vez que los scripts OE2 regeneran datos, este módulo lee los
valores actualizados automáticamente — eliminando constantes hardcoded
que pueden quedar obsoletas.

Jerarquía de fuentes (prioridad decreciente):
  1. CERTIFICACION_SOLAR_DATASET_2024.json  → kWp DC, energía solar
  2. data/oe2/bess/bess_results.json        → BESS capacity, power, SOC, tariffs, CO2
  3. ESPECIFICACION_CARGADORES_COMPLETA_v52.json → chargers, sockets, EV battery
  4. CSV reales (validación y fallback)      → max(soc_kwh), sum(energia_kwh)
  5. Valores canónicos _constants.py         → último recurso

Uso:
    from src.dimensionamiento.oe2.oe2_metadata import OE2Metadata
    m = OE2Metadata()            # Lee y valida al instanciar
    pv_kwp  = m.pv_kwp_dc       # 4162.0
    bess_kwh = m.bess_capacity_kwh  # 2000.0
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[3]

# Rutas canónicas de los JSONs generados por OE2
_SOLAR_CERT_JSON    = _ROOT / "data" / "oe2" / "Generacionsolar" / "CERTIFICACION_SOLAR_DATASET_2024.json"
_BESS_RESULTS_JSON  = _ROOT / "data" / "oe2" / "bess" / "bess_results.json"
_CHARGERS_SPEC_JSON = _ROOT / "data" / "oe2" / "chargers" / "ESPECIFICACION_CARGADORES_COMPLETA_v52.json"

# CSV OE2 para validación
_SOLAR_CSV   = _ROOT / "data" / "oe2" / "Generacionsolar" / "pv_generation_citylearn2024.csv"
_BESS_CSV    = _ROOT / "data" / "oe2" / "bess" / "bess_ano_2024.csv"

# Valores de respaldo (última instancia)
_FALLBACK_PV_KWP      = 4162.0
_FALLBACK_BESS_KWH    = 2000.0
_FALLBACK_BESS_KW     = 400.0
_FALLBACK_CO2_FACTOR  = 0.4521
_FALLBACK_N_CHARGERS  = 19
_FALLBACK_N_SOCKETS   = 38
_FALLBACK_CHARGER_KW  = 7.4


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        logger.warning("JSON OE2 no encontrado: %s", path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Error leyendo %s: %s", path, exc)
        return {}


@dataclass
class OE2Metadata:
    """Metadatos reales del sistema OE2 leídos de los JSONs generados."""

    # ── PV Solar ──────────────────────────────────────────────────────────────
    pv_kwp_dc:              float = field(init=False)  # kWp DC (PVWatts pdc0)
    pv_annual_kwh:          float = field(init=False)  # kWh/año reales del CSV
    pv_specific_yield:      float = field(init=False)  # kWh/kWp/año
    pv_max_kw:              float = field(init=False)  # kW pico horario

    # ── BESS ─────────────────────────────────────────────────────────────────
    bess_capacity_kwh:      float = field(init=False)  # kWh capacidad nominal
    bess_nominal_power_kw:  float = field(init=False)  # kW potencia nominal
    bess_efficiency:        float = field(init=False)  # round-trip efficiency
    bess_soc_min:           float = field(init=False)  # fracción SOC mínimo
    bess_soc_max:           float = field(init=False)  # fracción SOC máximo

    # ── Red y tarifas ────────────────────────────────────────────────────────
    co2_factor_kg_kwh:      float = field(init=False)  # kg CO2/kWh red Iquitos
    tarifa_hp_soles_kwh:    float = field(init=False)  # S./kWh hora punta
    tarifa_hfp_soles_kwh:   float = field(init=False)  # S./kWh fuera punta

    # ── Cargadores EV ────────────────────────────────────────────────────────
    n_chargers:             int   = field(init=False)  # número de cargadores
    n_sockets:              int   = field(init=False)  # sockets totales
    n_sockets_motos:        int   = field(init=False)  # sockets motos
    n_sockets_mototaxis:    int   = field(init=False)  # sockets mototaxis
    charger_power_kw:       float = field(init=False)  # kW por socket
    ev_moto_bat_kwh:        float = field(init=False)  # kWh batería moto
    ev_mototaxi_bat_kwh:    float = field(init=False)  # kWh batería mototaxi
    ev_soc_min:             float = field(init=False)  # SOC mínimo EV (frac)
    ev_soc_max:             float = field(init=False)  # SOC máximo EV (frac)

    # ── Fuentes usadas (para trazabilidad) ───────────────────────────────────
    sources_used:           list  = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._load_all()

    def _load_all(self) -> None:
        solar_cert  = _load_json(_SOLAR_CERT_JSON)
        bess_data   = _load_json(_BESS_RESULTS_JSON)
        chargers    = _load_json(_CHARGERS_SPEC_JSON)

        self._load_solar(solar_cert)
        self._load_bess(bess_data)
        self._load_chargers(chargers)
        self._load_grid(bess_data)
        self._validate_against_csv()

    # ─────────────────────────────────────────────────────────────────────────

    def _load_solar(self, cert: dict) -> None:
        sistema = cert.get("sistema_pv", {})
        if sistema.get("nominal_power_kwp_dc"):
            self.pv_kwp_dc = float(sistema["nominal_power_kwp_dc"])
            self.sources_used.append(f"pv_kwp_dc={self.pv_kwp_dc} ← CERTIFICACION_SOLAR.sistema_pv")
        else:
            self.pv_kwp_dc = _FALLBACK_PV_KWP
            self.sources_used.append(f"pv_kwp_dc={self.pv_kwp_dc} ← FALLBACK (_constants.py)")

        raw_kwh = cert.get("energia_kwh", 0.0)
        if raw_kwh > 0:
            self.pv_annual_kwh = float(raw_kwh)
            self.sources_used.append(f"pv_annual_kwh={self.pv_annual_kwh:,.0f} ← CERTIFICACION_SOLAR.energia_kwh")
        else:
            # Derivar del CSV directamente
            self.pv_annual_kwh = self._solar_kwh_from_csv()
            self.sources_used.append(f"pv_annual_kwh={self.pv_annual_kwh:,.0f} ← pv_generation_citylearn2024.csv")

        self.pv_specific_yield = (
            cert.get("rendimiento_especifico_kwh_kwp")
            or (self.pv_annual_kwh / self.pv_kwp_dc if self.pv_kwp_dc > 0 else 0.0)
        )
        self.pv_max_kw = self._solar_max_kw_from_csv()

    def _solar_kwh_from_csv(self) -> float:
        if not _SOLAR_CSV.exists():
            return 0.0
        try:
            df = pd.read_csv(_SOLAR_CSV, usecols=["energia_kwh"])
            return float(df["energia_kwh"].sum())
        except Exception:
            return 0.0

    def _solar_max_kw_from_csv(self) -> float:
        if not _SOLAR_CSV.exists():
            return 3245.95
        try:
            df = pd.read_csv(_SOLAR_CSV, usecols=["potencia_kw"])
            return float(df["potencia_kw"].max())
        except Exception:
            return 3245.95

    # ─────────────────────────────────────────────────────────────────────────

    def _load_bess(self, bess: dict) -> None:
        if bess.get("capacity_kwh"):
            self.bess_capacity_kwh = float(bess["capacity_kwh"])
            self.sources_used.append(f"bess_capacity_kwh={self.bess_capacity_kwh} ← bess_results.json")
        else:
            self.bess_capacity_kwh = self._bess_capacity_from_csv()
            self.sources_used.append(f"bess_capacity_kwh={self.bess_capacity_kwh} ← bess_ano_2024.csv max(soc_kwh)")

        self.bess_nominal_power_kw = float(bess.get("nominal_power_kw") or _FALLBACK_BESS_KW)
        self.bess_efficiency = float(bess.get("efficiency_roundtrip") or 0.95)
        self.bess_soc_min = float((bess.get("soc_min_percent") or 20.0) / 100.0)
        self.bess_soc_max = float((bess.get("soc_max_percent") or 100.0) / 100.0)

    def _bess_capacity_from_csv(self) -> float:
        if not _BESS_CSV.exists():
            return _FALLBACK_BESS_KWH
        try:
            df = pd.read_csv(_BESS_CSV, usecols=["soc_kwh"])
            return float(df["soc_kwh"].max())
        except Exception:
            return _FALLBACK_BESS_KWH

    # ─────────────────────────────────────────────────────────────────────────

    def _load_chargers(self, spec: dict) -> None:
        infra = spec.get("infraestructura_instalada", {})
        tecn  = spec.get("especificaciones_tecnicas", {})
        bats  = tecn.get("baterias", {})

        self.n_chargers        = int(infra.get("total_cargadores")       or _FALLBACK_N_CHARGERS)
        self.n_sockets         = int(infra.get("sockets_totales")        or _FALLBACK_N_SOCKETS)
        self.n_sockets_motos   = int(infra.get("sockets_motos")          or 30)
        self.n_sockets_mototaxis = int(infra.get("sockets_mototaxis")    or 8)
        self.charger_power_kw  = float(infra.get("potencia_por_socket_kw") or _FALLBACK_CHARGER_KW)

        moto_bat    = bats.get("moto",     {})
        taxi_bat    = bats.get("mototaxi", {})
        self.ev_moto_bat_kwh     = float(moto_bat.get("capacidad_nominal_kwh")    or 4.6)
        self.ev_mototaxi_bat_kwh = float(taxi_bat.get("capacidad_nominal_kwh")    or 7.4)
        self.ev_soc_min = 0.20  # fijo por diseño EV
        self.ev_soc_max = 0.80  # fijo por diseño EV

        if infra:
            self.sources_used.append(
                f"chargers: {self.n_chargers} cargadores, {self.n_sockets} sockets "
                f"← ESPECIFICACION_CARGADORES.json"
            )

    # ─────────────────────────────────────────────────────────────────────────

    def _load_grid(self, bess: dict) -> None:
        tariff = bess.get("osinergmin_tariff", {})
        self.tarifa_hp_soles_kwh  = float(tariff.get("energia_hp_soles_kwh")  or 0.45)
        self.tarifa_hfp_soles_kwh = float(tariff.get("energia_hfp_soles_kwh") or 0.28)
        # CO2 factor: from bess results or from CSV if available
        self.co2_factor_kg_kwh    = float(bess.get("factor_co2_kg_kwh") or _FALLBACK_CO2_FACTOR)
        if "factor_co2_kg_kwh" in bess:
            self.sources_used.append(f"co2_factor={self.co2_factor_kg_kwh} ← bess_results.json")

    # ─────────────────────────────────────────────────────────────────────────

    def _validate_against_csv(self) -> None:
        """Valida los valores leídos contra los CSV reales y advierte si hay discrepancias."""
        # Validar energía solar
        csv_kwh = self._solar_kwh_from_csv()
        if csv_kwh > 0 and abs(csv_kwh - self.pv_annual_kwh) > 1.0:
            logger.warning(
                "pv_annual_kwh: JSON=%.0f vs CSV=%.0f kWh — usando CSV",
                self.pv_annual_kwh, csv_kwh,
            )
            self.pv_annual_kwh = csv_kwh

        # Validar capacidad BESS
        csv_bess = self._bess_capacity_from_csv()
        if csv_bess > 0 and abs(csv_bess - self.bess_capacity_kwh) > 1.0:
            logger.warning(
                "bess_capacity: JSON=%.0f vs CSV max(soc_kwh)=%.0f — usando CSV",
                self.bess_capacity_kwh, csv_bess,
            )
            self.bess_capacity_kwh = csv_bess

    # ─────────────────────────────────────────────────────────────────────────

    def summary(self) -> str:
        lines = [
            "OE2Metadata — valores leídos de JSONs reales:",
            f"  PV DC:          {self.pv_kwp_dc:.0f} kWp  | {self.pv_annual_kwh:,.0f} kWh/año"
            f"  | yield={self.pv_specific_yield:.0f} kWh/kWp",
            f"  BESS:           {self.bess_capacity_kwh:.0f} kWh / {self.bess_nominal_power_kw:.0f} kW"
            f"  | eff={self.bess_efficiency:.0%} | SOC[{self.bess_soc_min:.0%}-{self.bess_soc_max:.0%}]",
            f"  CO₂ factor:     {self.co2_factor_kg_kwh} kg/kWh",
            f"  Tarifa HP/HFP:  {self.tarifa_hp_soles_kwh}/{self.tarifa_hfp_soles_kwh} S./kWh",
            f"  Chargers:       {self.n_chargers} cargadores / {self.n_sockets} sockets"
            f"  ({self.n_sockets_motos} motos + {self.n_sockets_mototaxis} mototaxis)",
            f"  EV baterías:    moto={self.ev_moto_bat_kwh} kWh | mototaxi={self.ev_mototaxi_bat_kwh} kWh",
            "  Fuentes:",
        ] + [f"    • {s}" for s in self.sources_used]
        return "\n".join(lines)


# ── Singleton cargado una vez por proceso ─────────────────────────────────────
_metadata: OE2Metadata | None = None


def get_metadata() -> OE2Metadata:
    """Devuelve el singleton OE2Metadata (se carga la primera vez que se llama)."""
    global _metadata
    if _metadata is None:
        _metadata = OE2Metadata()
        logger.info("OE2Metadata cargado:\n%s", _metadata.summary())
    return _metadata


def reload_metadata() -> OE2Metadata:
    """Fuerza recarga desde disco (útil cuando los scripts OE2 regeneraron datos)."""
    global _metadata
    _metadata = OE2Metadata()
    return _metadata
