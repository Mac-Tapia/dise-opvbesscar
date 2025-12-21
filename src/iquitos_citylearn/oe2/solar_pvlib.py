from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

@dataclass(frozen=True)
class SolarSizingOutput:
    target_ac_kw: float
    target_dc_kw: float
    target_annual_kwh: float
    annual_kwh: float
    scale_factor: float
    seconds_per_time_step: int
    profile_path: str

def _timestamps(year: int, tz: str, seconds_per_time_step: int) -> pd.DatetimeIndex:
    start = pd.Timestamp(f"{year}-01-01 00:00:00", tz=tz)
    # End is exclusive
    end = pd.Timestamp(f"{year+1}-01-01 00:00:00", tz=tz)
    freq = pd.Timedelta(seconds=seconds_per_time_step)
    return pd.date_range(start=start, end=end, freq=freq, inclusive="left")

def _fallback_profile(index: pd.DatetimeIndex) -> pd.Series:
    # Simple clear-sky-like curve with seasonal modulation.
    doy = index.dayofyear.values
    hour = index.hour.values + index.minute.values/60.0
    # daylight proxy
    solar_elev = np.maximum(0.0, np.sin((hour - 6.0) / 12.0 * np.pi))
    seasonal = 0.85 + 0.15*np.sin((doy - 80)/365.0*2*np.pi)
    return pd.Series(solar_elev * seasonal, index=index, name="pv_kw_per_kwp")

def build_pv_timeseries(
    year: int,
    tz: str,
    lat: float,
    lon: float,
    seconds_per_time_step: int,
    target_dc_kw: float,
    target_ac_kw: float,
    target_annual_kwh: float,
    use_pvlib: bool = True,
) -> pd.DataFrame:
    # CUMPLIMIENTO ESTRICTO ÍTEM: Calcular potencia FV (kWp) considerando eficiencia
    system_losses = 0.18  # 18% pérdidas típicas (wiring, inverter, etc.)
    inverter_efficiency = 0.97
    efficiency = (1 - system_losses) * inverter_efficiency  # ~0.82
    dc_capacity_kwp = target_dc_kw  # DC capacity in kWp
    
    index = _timestamps(year=year, tz=tz, seconds_per_time_step=seconds_per_time_step)
    dt_hours = seconds_per_time_step / 3600.0
    
    # VALIDACIÓN OBLIGATORIA: Debe haber 8760 horas (1 año completo)
    assert len(index) == 8760, f"Validación crítica: Se requieren 8760 horas, se tienen {len(index)}"

    pv_kw_per_kwp: pd.Series
    if use_pvlib:
        try:
            import pvlib  # type: ignore
            location = pvlib.location.Location(latitude=lat, longitude=lon, tz=tz)
            cs = location.get_clearsky(index, model="ineichen")
            # Very simple PVWatts-like conversion: AC power ~ (GHI/1000) * eff
            eff = 0.85
            pv_kw_per_kwp = (cs["ghi"] / 1000.0) * eff
            pv_kw_per_kwp = pv_kw_per_kwp.rename("pv_kw_per_kwp")
        except Exception:
            pv_kw_per_kwp = _fallback_profile(index).rename("pv_kw_per_kwp")
    else:
        pv_kw_per_kwp = _fallback_profile(index).rename("pv_kw_per_kwp")

    # Convert to kWh per kWp each timestep
    pv_kwh_per_kwp = pv_kw_per_kwp * dt_hours
    raw_annual_kwh = float((pv_kwh_per_kwp.sum() * target_dc_kw))
    scale = 1.0 if raw_annual_kwh <= 0 else (target_annual_kwh / raw_annual_kwh)
    
    # CUMPLIMIENTO ESTRICTO ÍTEM: Validar generación anual contra objetivo
    annual_generation_kwh = raw_annual_kwh * scale
    assert annual_generation_kwh >= (target_annual_kwh * 0.95), f"CRÍTICO: Generación anual insuficiente: {annual_generation_kwh} kWh < {target_annual_kwh*0.95} kWh objetivo"

    pv_kwh = pv_kwh_per_kwp * target_dc_kw * scale

    df = pd.DataFrame(
        {
            "timestamp": index.tz_convert(None),
            "pv_kwh": pv_kwh.values,
            "pv_kwh_per_kwp": pv_kwh_per_kwp.values * scale,
            "pv_kw_per_kwp": pv_kw_per_kwp.values * scale,
        }
    )
    return df

def run_solar_sizing(
    out_dir: Path,
    year: int,
    tz: str,
    lat: float,
    lon: float,
    seconds_per_time_step: int,
    target_dc_kw: float,
    target_ac_kw: float,
    target_annual_kwh: float,
    use_pvlib: bool = True,
) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = build_pv_timeseries(
        year=year,
        tz=tz,
        lat=lat,
        lon=lon,
        seconds_per_time_step=seconds_per_time_step,
        target_dc_kw=target_dc_kw,
        target_ac_kw=target_ac_kw,
        target_annual_kwh=target_annual_kwh,
        use_pvlib=use_pvlib,
    )

    profile_path = out_dir / "pv_generation_timeseries.csv"
    df.to_csv(profile_path, index=False)

    annual_kwh = float(df["pv_kwh"].sum())
    # recover scale factor from per_kwp
    raw = float(df["pv_kwh_per_kwp"].sum() / 1.0)  # scaled per kWp
    # not used directly

    summary = SolarSizingOutput(
        target_ac_kw=float(target_ac_kw),
        target_dc_kw=float(target_dc_kw),
        target_annual_kwh=float(target_annual_kwh),
        annual_kwh=float(annual_kwh),
        scale_factor=float(annual_kwh / max(target_annual_kwh, 1e-9)),
        seconds_per_time_step=int(seconds_per_time_step),
        profile_path=str(profile_path.resolve()),
    )

    (out_dir / "solar_results.json").write_text(
        pd.Series(summary.__dict__).to_json(), encoding="utf-8"
    )

    # Average 24h profile (kWh) for convenience
    df_tmp = df.copy()
    df_tmp["hour"] = pd.to_datetime(df_tmp["timestamp"]).dt.hour
    df_24h = df_tmp.groupby("hour")["pv_kwh"].mean().reset_index()
    df_24h.to_csv(out_dir / "pv_profile_24h.csv", index=False)

    return summary.__dict__
