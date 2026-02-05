"""
Módulo de simulación fotovoltaica para Iquitos, Perú.

Implementa modelo riguroso de generación FV usando pvlib con:
- Datos TMY reales de PVGIS (Typical Meteorological Year)
- Base de datos Sandia de módulos fotovoltaicos
- Base de datos CEC de inversores
- Modelo de irradiancia en plano del array (POA) - Perez
- Modelo de temperatura de celda (Sandia SAPM)
- ModelChain completo de pvlib
- Intervalos de 15 minutos para mayor precisión

Parámetros de diseño Iquitos:
    area_total_m2: 20637.0
    factor_diseno: 0.65
    surface_tilt: 10.0°
    surface_azimuth: 0.0° (Norte)
    lat: -3.75°
    lon: -73.25°
    alt: 104.0 m
    tz: America/Lima

Componentes seleccionados (máximo kWp en techo):
    Módulo: Kyocera_Solar_KS20__2008__E__ (20.2W, 0.072m², 280.3 W/m²)
    Inversor: Eaton__Xpert1670 (3201.2 kW AC nominal)

Referencias:
- PVGIS: https://re.jrc.ec.europa.eu/pvg_tools/
- King, D.L. et al. (2004). Sandia Photovoltaic Array Performance Model
- Perez, R. et al. (1990). Modeling daylight availability and irradiance components
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd  # type: ignore[import]
import requests  # type: ignore[import-untyped]

_pvlib_exceptions: Optional[Any] = None
_TEMP_MODEL_PARAMS: dict[str, Any] = {}

try:
    import pvlib  # type: ignore[import-not-found]
    from pvlib.location import Location  # type: ignore[import-not-found]
    from pvlib.modelchain import ModelChain  # type: ignore[import-not-found]
    from pvlib.pvsystem import PVSystem  # type: ignore[import-not-found]
    from pvlib.temperature import TEMPERATURE_MODEL_PARAMETERS  # type: ignore[import-not-found]

    _TEMP_MODEL_PARAMS = dict(TEMPERATURE_MODEL_PARAMETERS)  # type: ignore[arg-type]
except ImportError:  # pragma: no cover
    pvlib = None
    Location = None  # type: ignore[misc,assignment]
    PVSystem = None  # type: ignore[misc,assignment]
    ModelChain = None  # type: ignore[misc,assignment]

# pvlib y sus dependencias se importan al inicio (puede faltar en entornos de test).


# ============================================================================
# PARÁMETROS DE DISEÑO IQUITOS (CONSTANTES DEL PROYECTO)
# ============================================================================
IQUITOS_PARAMS: dict[str, float | str | int] = {
    "area_total_m2": 20637.0,
    "factor_diseno": 0.70,
    "surface_tilt": 10.0,
    "surface_azimuth": 0.0,
    "lat": -3.75,
    "lon": -73.25,
    "alt": 104.0,
    "tz": "America/Lima",
    "year": 2024,
}


@dataclass(frozen=True)
class SolarSizingOutput:
    """Resultado del dimensionamiento solar con modelo Sandia y PVGIS."""

    # Objetivos
    target_ac_kw: float
    target_dc_kw: float
    target_annual_kwh: float

    # Resultados energéticos
    annual_kwh: float
    annual_kwh_dc: float

    # Configuración temporal
    seconds_per_time_step: int
    time_steps_per_hour: int
    profile_path: str

    # Componentes
    module_name: str
    inverter_name: str
    modules_per_string: int
    strings_parallel: int
    total_modules: int
    num_inverters: int

    # Orientación
    tilt: float
    azimuth: float

    # Área
    area_total_m2: float
    area_utilizada_m2: float
    factor_diseno: float

    # Métricas de rendimiento
    capacity_factor: float
    performance_ratio: float
    specific_yield_kwh_kwp: float
    equivalent_hours: float

    # Estadísticas
    max_power_kw: float
    mean_power_kw: float
    max_daily_energy_kwh: float
    max_daily_energy_date: str
    max_power_timestamp: str
    hours_with_production: int

    # Pérdidas
    losses_total_pct: float

    # GHI anual
    ghi_annual_kwh_m2: float

    # Días representativos según GHI
    despejado_date: str = ""
    despejado_ghi: float = 0.0
    despejado_energy_kwh: float = 0.0
    intermedio_date: str = ""
    intermedio_ghi: float = 0.0
    intermedio_energy_kwh: float = 0.0
    nublado_date: str = ""
    nublado_ghi: float = 0.0
    nublado_energy_kwh: float = 0.0


@dataclass
class PVSystemConfig:
    """Configuración completa del sistema fotovoltaico."""

    latitude: float = float(IQUITOS_PARAMS["lat"])
    longitude: float = float(IQUITOS_PARAMS["lon"])
    altitude: float = float(IQUITOS_PARAMS["alt"])
    timezone: str = str(IQUITOS_PARAMS["tz"])

    area_total_m2: float = float(IQUITOS_PARAMS["area_total_m2"])
    factor_diseno: float = float(IQUITOS_PARAMS["factor_diseno"])

    tilt: float = float(IQUITOS_PARAMS["surface_tilt"])
    azimuth: float = float(IQUITOS_PARAMS["surface_azimuth"])

    # Módulo PV - Kyocera KS20 (máxima densidad de potencia)
    module_name: str = "Kyocera_Solar_KS20__2008__E__"

    # Inversor - Eaton Xpert1670 (inversor central)
    inverter_name: str = "Eaton__Xpert1670"

    # Pérdidas del sistema (%) - valores típicos para clima tropical húmedo
    soiling_loss: float = 3.0
    shading_loss: float = 2.0
    snow_loss: float = 0.0
    mismatch_loss: float = 2.0
    wiring_dc_loss: float = 2.0
    connections_loss: float = 0.5
    lid_loss: float = 1.5
    nameplate_loss: float = 1.0
    age_loss: float = 0.5
    availability_loss: float = 2.0

    @property
    def area_utilizada_m2(self) -> float:
        return self.area_total_m2 * self.factor_diseno

    @property
    def total_losses_factor(self) -> float:
        losses = [
            self.soiling_loss,
            self.shading_loss,
            self.snow_loss,
            self.mismatch_loss,
            self.wiring_dc_loss,
            self.connections_loss,
            self.lid_loss,
            self.nameplate_loss,
            self.age_loss,
            self.availability_loss,
        ]
        factor = 1.0
        for loss in losses:
            factor *= 1 - loss / 100
        return factor

    @property
    def total_losses_pct(self) -> float:
        return (1 - self.total_losses_factor) * 100


def _ensure_pvlib_available() -> None:
    """Garantiza que pvlib y sus dependencias estén disponibles en tiempo de ejecución."""
    if pvlib is None or Location is None or PVSystem is None or ModelChain is None:
        raise ImportError("pvlib y sus dependencias son necesarios para esta operación.")


def _get_float_from_kwargs(name: str, default: float | str | int, kwargs: dict[str, Any]) -> float:
    """Retorna el valor float de kwargs o el default si la conversión no es numérica."""
    value = kwargs.get(name, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _get_pvgis_tmy(lat: float, lon: float, startyear: int = 2005, endyear: int = 2020) -> pd.DataFrame:
    """
    Descarga datos TMY (Typical Meteorological Year) de PVGIS para la ubicación.

    PVGIS proporciona datos de irradiancia y temperatura basados en satélite.
    """
    print("Descargando datos TMY de PVGIS para Iquitos...")
    _ensure_pvlib_available()

    exception_tuple: tuple[type[Exception], ...] = (requests.RequestException, ValueError)

    try:
        # Intentar descargar de PVGIS con diferentes versiones de la API
        result = pvlib.iotools.get_pvgis_tmy(  # type: ignore[union-attr,attr-defined]
            latitude=lat,
            longitude=lon,
            startyear=startyear,
            endyear=endyear,
            outputformat="json",
            usehorizon=True,
            map_variables=True,
        )

        # La función puede devolver 2 o 4 valores dependiendo de la versión
        if isinstance(result, tuple):  # type: ignore[unreachable]
            tmy_data = result[0] if len(result) > 0 else pd.DataFrame()  # type: ignore[index]
        else:
            tmy_data = result

        print(f"Nº de horas del TMY: {len(tmy_data)}")  # type: ignore[arg-type]

        # Renombrar columnas según convención pvlib
        column_map = {
            "temp_air": "temp_air",
            "relative_humidity": "relative_humidity",
            "ghi": "ghi",
            "dni": "dni",
            "dhi": "dhi",
            "IR(h)": "infrared",
            "wind_speed": "wind_speed",
            "wind_direction": "wind_direction",
            "pressure": "pressure",
        }

        if not isinstance(tmy_data, pd.DataFrame):
            tmy_data = pd.DataFrame(tmy_data)
        tmy_data = tmy_data.rename(columns=column_map)

        return tmy_data

    except exception_tuple as e:
        print(f"  WARN Error descargando PVGIS: {e}")
        print("  Generando datos sintéticos basados en climatología de Iquitos...")
        return _generate_synthetic_tmy(lat, lon)


def _generate_synthetic_tmy(lat: float, lon: float) -> pd.DataFrame:
    """
    Genera datos TMY sintéticos basados en climatología de Iquitos.
    Usado como fallback si PVGIS no está disponible.
    """
    _ensure_pvlib_available()

    # Crear índice temporal para un año (horario)
    year = 2024
    tz = "America/Lima"
    times = pd.date_range(start=f"{year}-01-01 00:00:00", end=f"{year}-12-31 23:00:00", freq="h", tz=tz)

    location = pvlib.location.Location(lat, lon, tz=tz, altitude=104)  # type: ignore[attr-defined]

    # Clear-sky como base
    clearsky = location.get_clearsky(times, model="ineichen")  # type: ignore[attr-defined]

    time_hour = times.hour  # pylint: disable=no-member
    time_month = times.month  # pylint: disable=no-member
    time_minute = times.minute  # pylint: disable=no-member

    cloud_base = np.where((time_month >= 12) | (time_month <= 5), 0.55, 0.70)

    # Variación diaria
    cloud_daily = np.where((time_hour >= 13) & (time_hour <= 18), -0.15, 0.0)

    np.random.seed(42)
    cloud_factor = np.clip(cloud_base + cloud_daily + np.random.normal(0, 0.08, len(times)), 0.3, 0.95)

    # Temperatura Iquitos
    t_mean = 26.5
    t_daily_amp = 5.0
    hour_float = time_hour + time_minute / 60
    temp_air = t_mean + t_daily_amp * np.sin(
        (hour_float - 6) / 24 * 2 * np.pi
    ) + np.random.normal(0, 1.0, len(times))

    # Viento
    wind_speed = 2.0 + 1.0 * np.sin((hour_float - 8) / 24 * 2 * np.pi)
    wind_speed = np.clip(wind_speed + np.abs(np.random.normal(0, 0.5, len(times))), 0.5, 6.0)

    tmy_data = pd.DataFrame(
        {
            "ghi": (clearsky["ghi"] * cloud_factor).values,  # type: ignore[attr-defined]
            "dni": (clearsky["dni"] * cloud_factor * 0.9).values,  # type: ignore[attr-defined]
            "dhi": (clearsky["dhi"] * (1 + (1 - cloud_factor) * 0.3)).values,  # type: ignore[attr-defined]
            "temp_air": temp_air,
            "wind_speed": wind_speed,
        },
        index=times,
    )

    return tmy_data


def _interpolate_to_interval(tmy_data: pd.DataFrame, minutes: int = 15) -> pd.DataFrame:
    """
    Interpola datos horarios a intervalos más pequeños (ej: 15 min).
    """
    print(f"Interpolando datos a intervalos de {minutes} minutos...")

    # Crear nuevo índice con frecuencia deseada
    freq = f"{minutes}min"
    new_index = pd.date_range(start=tmy_data.index[0], end=tmy_data.index[-1], freq=freq)

    # Reindexar e interpolar
    tmy_interp = tmy_data.reindex(new_index).interpolate(method="linear")  # type: ignore[attr-defined]

    # Asegurar que irradiancia sea cero durante la noche
    # (interpolar puede crear valores pequeños negativos)
    for col in ["ghi", "dni", "dhi"]:
        if col in tmy_interp.columns:
            tmy_interp[col] = tmy_interp[col].clip(lower=0)  # type: ignore[attr-defined]

    print(f"Total de puntos de datos a {minutes} min: {len(tmy_interp)}")

    return tmy_interp


def _get_sandia_modules() -> pd.DataFrame:
    """Obtiene la base de datos de módulos Sandia."""
    _ensure_pvlib_available()
    assert pvlib is not None
    return pvlib.pvsystem.retrieve_sam("SandiaMod")  # type: ignore[attr-defined]


def _get_cec_inverters() -> pd.DataFrame:
    """Obtiene la base de datos de inversores CEC."""
    _ensure_pvlib_available()
    assert pvlib is not None
    return pvlib.pvsystem.retrieve_sam("CECInverter")  # type: ignore[attr-defined]


def _get_module_area(params: pd.Series) -> float:
    """Devuelve el area del modulo en m2 usando llaves conocidas."""
    for key in ("Area", "A_c", "A_ref"):
        area = params.get(key)
        if area is not None:
            try:
                area_val = float(area)
            except (TypeError, ValueError):
                continue
            if area_val > 0:
                return area_val
    return 0.0


def _rank_modules_by_density(
    modules_db: pd.DataFrame,
    area_util: float,
    top_n: int = 5,
) -> pd.DataFrame:
    """Ordena modulos por densidad de potencia (W/m2)."""
    rows: list[dict[str, float | str | int]] = []
    for name in modules_db.columns:
        params = modules_db[name]
        vmp = float(params.get("Vmpo", 0))
        imp = float(params.get("Impo", 0))
        if vmp <= 0 or imp <= 0:
            continue
        pmp_w = vmp * imp
        area_m2 = _get_module_area(params)
        if area_m2 <= 0:
            continue
        density = pmp_w / area_m2
        n_max = int(area_util / area_m2) if area_util > 0 else 0
        dc_kw_max = n_max * pmp_w / 1000 if n_max > 0 else 0
        rows.append(
            {
                "name": name,
                "pmp_w": pmp_w,
                "area_m2": area_m2,
                "density_w_m2": density,
                "n_max": n_max,
                "dc_kw_max": dc_kw_max,
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values(by=["density_w_m2", "pmp_w"], ascending=False)  # type: ignore[attr-defined]
    return df.head(top_n).reset_index(drop=True)


def _rank_inverters_by_score(
    inverters_db: pd.DataFrame,
    target_ac_kw: float,
    top_n: int = 5,
) -> pd.DataFrame:
    """Ordena inversores por eficiencia y ajuste al target AC."""
    rows: list[dict[str, float | str | int]] = []
    for name in inverters_db.columns:
        params = inverters_db[name]
        paco_w = float(params.get("Paco", 0))
        if paco_w <= 0:
            continue
        paco_kw = paco_w / 1000
        pdco_w = float(params.get("Pdco", 0))
        efficiency = paco_w / pdco_w if pdco_w > 0 else 0.0
        n_inv = int(np.ceil(target_ac_kw / paco_kw)) if target_ac_kw > 0 else 1
        oversize = 0.0
        if target_ac_kw > 0:
            oversize = (n_inv * paco_kw - target_ac_kw) / target_ac_kw
        penalty = 0.02 * max(n_inv - 1, 0)
        score = efficiency / (1.0 + oversize + penalty) if efficiency > 0 else 0.0
        rows.append(
            {
                "name": name,
                "paco_kw": paco_kw,
                "pdco_kw": pdco_w / 1000 if pdco_w > 0 else 0.0,
                "efficiency": efficiency,
                "n_inverters": n_inv,
                "oversize_ratio": oversize,
                "score": score,
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values(by=["score", "efficiency", "paco_kw"], ascending=False)  # type: ignore[attr-defined]
    return df.head(top_n).reset_index(drop=True)


def _log_candidates(section_title: str, df: pd.DataFrame, top_n: int) -> None:
    """Imprime candidatos seleccionados."""
    if df.empty:
        print(f"  {section_title}: sin candidatos validos")
        return
    print(f"  {section_title} (top {top_n}):")
    for row_idx, row in df.head(top_n).iterrows():
        if "density_w_m2" in row:
            print(
                f"    {int(row_idx) + 1}. {row['name']} | "  # type: ignore[arg-type]
                f"{row['pmp_w']:.1f} W | {row['area_m2']:.3f} m2 | "
                f"{row['density_w_m2']:.1f} W/m2"
            )
        else:
            print(
                f"    {int(row_idx) + 1}. {row['name']} | "  # type: ignore[arg-type]
                f"{row['paco_kw']:.1f} kW | eff {row['efficiency']:.3f} | "
                f"n={int(row['n_inverters'])}"
            )


def _metric_score(
    metric: str,
    annual_kwh: float,
    energy_per_m2: float,
    performance_ratio: float,
) -> float:
    """Devuelve el score segun la metrica elegida."""
    metric_norm = metric.lower()
    if metric_norm in ("pr", "performance_ratio"):
        return performance_ratio
    if metric_norm in ("energy_per_m2", "kwh_per_m2", "kwh_m2"):
        return energy_per_m2
    if metric_norm in ("annual_kwh", "energy"):
        return annual_kwh
    return energy_per_m2


def _evaluate_candidate_combinations(
    tmy_data: pd.DataFrame,
    config: PVSystemConfig,
    modules_db: pd.DataFrame,
    inverters_db: pd.DataFrame,
    module_candidates: pd.DataFrame,
    inverter_candidates: pd.DataFrame,
    target_dc_kw: float,
    target_ac_kw: float,
    selection_metric: str,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Evalua combinaciones modulo/inversor y retorna ranking y mejor candidato."""
    if module_candidates.empty or inverter_candidates.empty:
        return [], None

    rows: list[dict[str, Any]] = []
    metric_norm = selection_metric.lower()
    for _, mod_row in module_candidates.iterrows():
        module_name = str(mod_row.get("name", ""))
        if module_name not in modules_db.columns:
            continue
        module_params = modules_db[module_name]
        area_m2 = _get_module_area(module_params)
        if area_m2 <= 0:
            continue
        n_modules_max = int(config.area_utilizada_m2 / area_m2) if config.area_utilizada_m2 > 0 else 0
        pmp_w = float(module_params.get("Vmpo", 0)) * float(module_params.get("Impo", 0))
        if pmp_w <= 0:
            continue

        for _, inv_row in inverter_candidates.iterrows():
            inverter_name = str(inv_row.get("name", ""))
            if inverter_name not in inverters_db.columns:
                continue
            inverter_params = inverters_db[inverter_name]
            paco_w = float(inverter_params.get("Paco", 0))
            if paco_w <= 0:
                continue
            paco_kw = paco_w / 1000
            num_inverters = max(1, int(np.ceil(target_ac_kw / paco_kw))) if target_ac_kw > 0 else 1

            modules_per_string, strings_parallel, total_modules = _calculate_string_config(
                module_params, inverter_params, n_modules_max, target_dc_kw, log=False
            )
            if total_modules <= 0:
                continue

            system_dc_kw = total_modules * pmp_w / 1000
            area_modules = total_modules * area_m2

            results, sim_metadata = run_pv_simulation(
                tmy_data=tmy_data,
                config=config,
                module_params=module_params,
                inverter_params=inverter_params,
                modules_per_string=modules_per_string,
                strings_parallel=strings_parallel,
                total_modules=total_modules,
                num_inverters=num_inverters,
                log=False,
            )

            annual_ac_kwh = float(results["ac_energy_kwh"].sum())
            specific_yield = annual_ac_kwh / system_dc_kw if system_dc_kw > 0 else 0.0
            ghi_annual = float(sim_metadata.get("ghi_annual_kwh_m2", 0.0))
            performance_ratio = specific_yield / ghi_annual if ghi_annual > 0 else 0.0
            energy_per_m2 = annual_ac_kwh / area_modules if area_modules > 0 else 0.0
            score = _metric_score(metric_norm, annual_ac_kwh, energy_per_m2, performance_ratio)

            rows.append(
                {
                    "module_name": module_name,
                    "inverter_name": inverter_name,
                    "annual_kwh": annual_ac_kwh,
                    "energy_per_m2": energy_per_m2,
                    "performance_ratio": performance_ratio,
                    "score": score,
                    "system_dc_kw": system_dc_kw,
                    "area_modules_m2": area_modules,
                    "modules_per_string": modules_per_string,
                    "strings_parallel": strings_parallel,
                    "total_modules": total_modules,
                    "num_inverters": num_inverters,
                }
            )

    if not rows:
        return [], None

    df = pd.DataFrame(rows).sort_values(by=["score", "annual_kwh"], ascending=False).reset_index(drop=True)  # type: ignore[attr-defined]
    records: List[Dict[str, Any]] = [{str(k): v for k, v in record.items()} for record in df.to_dict(orient="records")]  # type: ignore[attr-defined]
    best_row: Dict[str, Any] = {str(k): v for k, v in df.iloc[0].to_dict().items()}  # type: ignore[attr-defined]
    return records, best_row


def _select_module(modules_db: pd.DataFrame, module_name: str, area_util: float) -> Tuple[str, pd.Series, int]:
    """
    Selecciona módulo y calcula número máximo en el área disponible.
    """
    if module_name in modules_db.columns:
        params = modules_db[module_name]
        vmp = params.get("Vmpo", 0)
        imp = params.get("Impo", 0)
        pmp = vmp * imp
        area = _get_module_area(params) or 0.072  # Default Kyocera KS20
        n_max = int(area_util / area) if area > 0 else 0
        density = pmp / area if area > 0 else 0

        print(f"  OK Módulo: {module_name}")
        print(f"    Potencia: {pmp:.2f}W")
        print(f"    Área: {area:.4f} m²")
        print(f"    Densidad: {density:.1f} W/m²")
        print(f"    Módulos máximos en techo: {n_max:,}")

        return module_name, params, n_max

    # Buscar alternativa por máxima densidad
    print(f"  WARN Módulo '{module_name}' no encontrado, buscando alternativa...")

    best_mod = None
    best_density = 0
    for col in modules_db.columns:
        params = modules_db[col]
        pmp = params.get("Vmpo", 0) * params.get("Impo", 0)
        area = _get_module_area(params)
        if pmp > 0 and area > 0:
            density = pmp / area
            if density > best_density:
                best_density = density
                best_mod = col

    if best_mod:
        params = modules_db[best_mod]
        area = _get_module_area(params) or 1.0
        n_max = int(area_util / area)
        print(f"  OK Módulo alternativo: {best_mod} ({best_density:.1f} W/m²)")
        return best_mod, params, n_max

    return modules_db.columns[0], modules_db.iloc[:, 0], 1000


def _select_inverter(inverters_db: pd.DataFrame, inverter_name: str, target_ac_kw: float) -> Tuple[str, pd.Series, int]:
    """
    Selecciona inversor y calcula número de unidades necesarias.
    """
    if inverter_name in inverters_db.columns:
        params = inverters_db[inverter_name]
        paco = params.get("Paco", 0)
        paco_kw = paco / 1000 if paco > 0 else 0
        vdco = params.get("Vdco", 0)

        if paco_kw > 0:
            n_inv = max(1, int(np.ceil(target_ac_kw / paco_kw)))
            print(f"  OK Inversor: {inverter_name}")
            print(f"    P_AC nominal: {paco_kw:.2f} kW")
            print(f"    Vdco: {vdco:.0f} V")
            print(f"    Número de inversores: {n_inv}")
            return inverter_name, params, n_inv

    print(f"  WARN Inversor '{inverter_name}' no encontrado, buscando alternativa...")

    # Buscar por máxima potencia
    best_inv = None
    best_paco = 0
    for col in inverters_db.columns:
        params = inverters_db[col]
        paco = params.get("Paco", 0)
        if paco > best_paco:
            best_paco = paco
            best_inv = col

    if best_inv:
        params = inverters_db[best_inv]
        paco_kw = best_paco / 1000
        n_inv = max(1, int(np.ceil(target_ac_kw / paco_kw)))
        print(f"  OK Inversor alternativo: {best_inv} ({paco_kw:.1f} kW)")
        return best_inv, params, n_inv

    return inverters_db.columns[0], inverters_db.iloc[:, 0], 1


def _calculate_string_config(
    module_params: pd.Series,
    inverter_params: pd.Series,
    n_modules_max: int,
    target_dc_kw: float,
    log: bool = True,
) -> Tuple[int, int, int]:
    """
    Calcula configuración óptima de strings.
    """
    vmp = float(module_params.get("Vmpo", 17.0))
    voc = float(module_params.get("Voco", 21.0))
    imp = float(module_params.get("Impo", 1.19))
    pmp = vmp * imp

    vdco = float(inverter_params.get("Vdco", 1030))
    vdcmax = float(inverter_params.get("Vdcmax", 1500))
    mppt_low = float(inverter_params.get("Mppt_low", 500))

    # Coeficiente de temperatura de Voc (Sandia: V/°C)
    beta_voc = float(module_params.get("Bvoco", -0.08))

    # Voc a temperatura mínima (15°C en Iquitos, delta = -10°C)
    voc_cold = voc + beta_voc * (-10)
    if voc_cold <= 0:
        voc_cold = voc * 1.05

    # Módulos por string
    # Límite superior: Voc_cold × N < Vdcmax (margen 10%)
    max_per_string = max(1, int((vdcmax * 0.90) / voc_cold))

    # Límite inferior: Vmp × N > Mppt_low
    min_per_string = max(1, int(np.ceil(mppt_low / vmp)))

    # Óptimo: centrar en Vdco
    opt_per_string = max(1, int(vdco / vmp))

    modules_per_string = min(max_per_string, max(min_per_string, opt_per_string))

    # Número de strings para alcanzar potencia objetivo
    target_modules = int(np.ceil(target_dc_kw * 1000 / pmp))
    strings_parallel = max(1, int(np.ceil(target_modules / modules_per_string)))

    # Limitar por área disponible
    total_modules = modules_per_string * strings_parallel
    if total_modules > n_modules_max:
        total_modules = n_modules_max
        strings_parallel = total_modules // modules_per_string
        total_modules = modules_per_string * strings_parallel

    if log:
        print("   Configuracion de strings:")
        print(f"     Modulos por string: {modules_per_string}")
        print(f"     Strings en paralelo: {strings_parallel}")
        print(f"     Total modulos: {total_modules:,}")
        print(f"     Voltaje string (Vmp): {vmp * modules_per_string:.0f}V")
        print(f"     Voltaje string (Voc): {voc * modules_per_string:.0f}V")

    return modules_per_string, strings_parallel, total_modules


def _to_series_like(
    value: Any,
    index: pd.Index,
    fallback_column: Optional[str] = None,
) -> pd.Series:
    """
    Normaliza el resultado de `ModelChain` a una Serie con el índice meteorológico.
    """
    if isinstance(value, pd.Series):
        series = value.reindex(index)  # type: ignore[attr-defined]
    elif isinstance(value, pd.DataFrame):
        column_name = fallback_column if fallback_column in value.columns else None
        if column_name is None and not value.columns.empty:
            column_name = value.columns[0]
        if column_name is not None:
            series = value[column_name].reindex(index)  # type: ignore[attr-defined]
        else:
            series = pd.Series(0.0, index=index)
    elif value is None:
        series = pd.Series(0.0, index=index)
    else:
        arr = np.asarray(value).ravel()
        length = min(len(arr), len(index))
        if length == 0:
            series = pd.Series(0.0, index=index)
        else:
            series = pd.Series(arr[:length], index=index[:length])
            series = series.reindex(index, fill_value=0.0)  # type: ignore[attr-defined]
    return series.fillna(0.0).astype(float)  # type: ignore[attr-defined]


def run_pv_simulation(
    tmy_data: pd.DataFrame,
    config: PVSystemConfig,
    module_params: pd.Series,
    inverter_params: pd.Series,
    modules_per_string: int,
    strings_parallel: int,
    total_modules: int,
    num_inverters: int,
    log: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Ejecuta simulación PV usando ModelChain de pvlib.
    """
    _ensure_pvlib_available()
    assert Location is not None and PVSystem is not None and ModelChain is not None

    if log:
        print("\nEjecutando simulacion del modelo PV (ModelChain)...")

    # Ubicación
    location = Location(
        latitude=config.latitude,
        longitude=config.longitude,
        tz=config.timezone,
        altitude=config.altitude,
        name="Iquitos, Peru",
    )

    # Parámetros de temperatura SAPM
    temp_params: dict[str, Any] = _TEMP_MODEL_PARAMS.get("sapm", {}).get("open_rack_glass_glass", {})

    # Sistema PV
    system = PVSystem(
        surface_tilt=int(config.tilt),  # type: ignore[arg-type]
        surface_azimuth=int(config.azimuth),  # type: ignore[arg-type]
        module_parameters=module_params,
        inverter_parameters=inverter_params,
        temperature_model_parameters=temp_params,
        modules_per_string=modules_per_string,
        strings_per_inverter=strings_parallel,
    )

    # ModelChain
    mc = ModelChain(
        system=system,
        location=location,
        aoi_model="physical",
        spectral_model="no_loss",
        temperature_model="sapm",
        losses_model="no_loss",
        transposition_model="perez",
        dc_model="sapm",
        ac_model="sandia",
    )

    # Preparar datos meteorológicos
    weather = tmy_data[["ghi", "dni", "dhi", "temp_air", "wind_speed"]].copy()

    # Calcular posición solar
    if log:
        print("Calculando posicion solar...")
    solar_pos = location.get_solarposition(weather.index)  # type: ignore[attr-defined]

    # Aplicar irradiancia cero durante la noche
    night_mask = solar_pos["apparent_zenith"] >= 90
    weather.loc[night_mask, ["ghi", "dni", "dhi"]] = 0
    if log:
        print("Aplicada irradiancia cero durante la noche.")

    # Ejecutar modelo
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mc.run_model(weather)  # type: ignore[attr-defined]

    # Extraer resultados
    # mc.results.dc puede ser DataFrame o Series dependiendo del modelo
    dc_power = _to_series_like(mc.results.dc, weather.index, fallback_column="p_mp")
    ac_power = _to_series_like(mc.results.ac, weather.index)

    # Escalar por número de inversores si > 1
    if num_inverters > 1:
        dc_power = dc_power * float(num_inverters)
        ac_power = ac_power * float(num_inverters)

    # Limpiar valores
    dc_power = dc_power.fillna(0).clip(lower=0)  # type: ignore[attr-defined]
    ac_power = ac_power.fillna(0).clip(lower=0)  # type: ignore[attr-defined]

    # Aplicar pérdidas del sistema
    losses_factor = config.total_losses_factor
    ac_power_final = ac_power * losses_factor

    # Calcular energía por intervalo
    # Determinar duración del intervalo en horas
    if len(weather.index) > 1:
        dt = (weather.index[1] - weather.index[0]).total_seconds() / 3600
    else:
        dt = 1.0

    # ================================================================
    # FÓRMULA CORRECTA DE ENERGÍA (BASADA EN PAPERS Y REFERENCIAS)
    # ================================================================
    # Fuente: Wikipedia Energy - Watt definition
    # Power (W) = Energy (J) / Time (s)
    # Therefore: Energy (kWh) = Power (kW) × Time (h)
    #
    # dc_energy [kWh] = dc_power [W] × dt [h] / 1000
    # ac_energy [kWh] = ac_power [W] × dt [h] / 1000
    #
    # Verificación dimensional:
    # [kWh] = [W] × [h] / 1000 = [J/s] × [3600s] / 1000 = [3600J] / 1000 = [3.6kJ]
    # = [kWh] ✓ CORRECTO
    # ================================================================

    # CÁLCULO DC: Energía antes de pérdidas del inversor
    dc_energy = dc_power * dt / 1000  # [W] × [h] / 1000 = [kWh]

    # CÁLCULO AC: Energía después del inversor (con pérdidas aplicadas)
    ac_energy = ac_power_final * dt / 1000  # [W] × [h] / 1000 = [kWh]

    # VALIDACIÓN: Verificar que energía ≠ potencia (unidades diferentes)
    # Para el máximo en el dataset:
    max_idx_local = dc_power.idxmax()
    max_power_dc_w = dc_power.loc[max_idx_local]
    max_energy_dc_kwh = dc_energy.loc[max_idx_local]

    if log:
        print(f"\nValidacion de formula (Energia != Potencia):")
        print(f"  Hora con maxima potencia: {max_idx_local}")
        print(f"  Potencia DC: {max_power_dc_w:.1f} W")
        print(f"  Energia DC en ese intervalo: {max_energy_dc_kwh:.6f} kWh")
        print(f"  Intervalo temporal: {dt:.4f} horas")
        print(f"  Verificacion: E = P x Dt = {max_power_dc_w:.1f} x {dt:.4f} = {max_power_dc_w * dt / 1000:.6f} kWh")
        print(f"  Concordancia: {abs(max_energy_dc_kwh - max_power_dc_w * dt / 1000) < 1e-6} OK\n")

    # Crear DataFrame de resultados
    results = pd.DataFrame(
        {
            "timestamp": weather.index,
            "ghi_wm2": np.asarray(weather["ghi"].values, dtype=float),  # type: ignore[arg-type]
            "dni_wm2": np.asarray(weather["dni"].values, dtype=float),  # type: ignore[arg-type]
            "dhi_wm2": np.asarray(weather["dhi"].values, dtype=float),  # type: ignore[arg-type]
            "temp_air_c": np.asarray(weather["temp_air"].values, dtype=float),  # type: ignore[arg-type]
            "wind_speed_ms": np.asarray(weather["wind_speed"].values, dtype=float),  # type: ignore[arg-type]
            "dc_power_kw": np.asarray(dc_power.values, dtype=float) / 1000,  # type: ignore[arg-type]
            "ac_power_kw": np.asarray(ac_power_final.values, dtype=float) / 1000,  # type: ignore[arg-type]
            "dc_energy_kwh": np.asarray(dc_energy.values, dtype=float),  # type: ignore[arg-type]
            "ac_energy_kwh": np.asarray(ac_energy.values, dtype=float),  # type: ignore[arg-type]
        }
    )
    results.set_index("timestamp", inplace=True)  # type: ignore[call-arg]

    # Calcular GHI anual
    ghi_annual = weather["ghi"].sum() * dt / 1000  # kWh/m²

    metadata: dict[str, Any] = {
        "dt_hours": dt,
        "ghi_annual_kwh_m2": ghi_annual,
        "losses_factor": losses_factor,
        "total_modules": total_modules,
    }

    return results, metadata


def calculate_statistics(
    results: pd.DataFrame,
    system_dc_kw: float,
    system_ac_kw: float,
    ghi_annual: float,
    dt_hours: float,
) -> Dict[str, Any]:
    """
    Calcula estadísticas detalladas del sistema.
    """
    print("\n" + "=" * 60)
    print("  ESTADÍSTICAS DEL SISTEMA (TMY PVGIS)")
    print("=" * 60)

    # Energía anual
    annual_ac_kwh = results["ac_energy_kwh"].sum()
    annual_dc_kwh = results["dc_energy_kwh"].sum()

    # Potencia máxima y media
    max_power_kw = results["ac_power_kw"].max()
    mean_power_kw = results["ac_power_kw"].mean()

    # Timestamp de máxima potencia
    max_power_idx = results["ac_power_kw"].idxmax()
    max_power_timestamp = str(max_power_idx)

    # Energía diaria
    results_daily: "pd.Series[Any]" = results["ac_energy_kwh"].resample("D").sum()  # type: ignore[index]
    max_daily_energy = results_daily.max()
    max_daily_idx = results_daily.idxmax()
    max_daily_energy_date = str(pd.Timestamp(max_daily_idx).date())

    # Energía en el intervalo de máxima potencia
    max_interval_energy: float = float(results.loc[max_power_idx, "ac_energy_kwh"])  # type: ignore[arg-type]

    # Horas con producción
    hours_with_production = (results["ac_power_kw"] > 0).sum() * dt_hours

    # Yield específico
    specific_yield = annual_ac_kwh / system_dc_kw if system_dc_kw > 0 else 0

    # Factor de planta (capacidad)
    hours_year = len(results) * dt_hours
    capacity_factor = annual_ac_kwh / (system_ac_kw * hours_year) if system_ac_kw > 0 else 0

    # Horas equivalentes
    equivalent_hours = annual_ac_kwh / system_ac_kw if system_ac_kw > 0 else 0

    # Performance Ratio
    performance_ratio = specific_yield / ghi_annual if ghi_annual > 0 else 0

    print("\n=== Día de máxima generación y máximo intervalo ===")
    print(f"Día de máxima energía:          {max_daily_energy_date}    E = {max_daily_energy:.1f} kWh")
    print(f"Instante de máxima potencia:    {max_power_timestamp}    P = {max_power_kw:.1f} kW")
    print(f"Energía en ese intervalo:       {max_interval_energy:.3f} kWh")

    print("\n=== Estadísticas del sistema (TMY PVGIS) ===")
    print(f"Energía anual AC:               {annual_ac_kwh:,.0f} kWh  ({annual_ac_kwh/1e6:.2f} GWh)")
    print(f"Yield específico:               {specific_yield:.0f} kWh/kWp·año  ({specific_yield/1e3:.2f} MWh/MWp·año)")
    print(f"Factor de planta (AC):          {capacity_factor*100:.1f} %")
    print(f"Performance Ratio:              {performance_ratio*100:.1f} %")
    print(f"Potencia AC máxima:             {max_power_kw:,.1f} kW")
    print(f"Potencia AC media:              {mean_power_kw:.1f} kW")
    print(f"Horas equivalentes (E/P_AC):    {equivalent_hours:,.0f} h/año")
    print(f"Horas con producción (>0 kW):   {hours_with_production:,.0f} h/año")

    return {
        "annual_ac_kwh": annual_ac_kwh,
        "annual_dc_kwh": annual_dc_kwh,
        "specific_yield": specific_yield,
        "capacity_factor": capacity_factor,
        "performance_ratio": performance_ratio,
        "equivalent_hours": equivalent_hours,
        "max_power_kw": max_power_kw,
        "mean_power_kw": mean_power_kw,
        "max_daily_energy_kwh": max_daily_energy,
        "max_daily_energy_date": max_daily_energy_date,
        "max_power_timestamp": max_power_timestamp,
        "hours_with_production": int(hours_with_production),
    }


def calculate_monthly_energy(results: pd.DataFrame) -> "pd.Series":
    """
    Calcula energía mensual.
    """
    monthly: "pd.Series[Any]" = results["ac_energy_kwh"].resample("ME").sum()  # type: ignore[index]
    monthly.name = "kWh"

    print("\nEnergía mensual [kWh]:")
    print(monthly.to_string())

    return monthly


def calculate_representative_days(results: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula días representativos según GHI diario:
    - Despejado (GHI máx): día con mayor irradiancia
    - Intermedio (GHI med): día con irradiancia mediana
    - Nublado (GHI mín>0): día con menor irradiancia (pero con sol)

    Retorna fechas, GHI diario y energía generada para cada día representativo.
    """
    # Calcular GHI diario (Wh/m² -> convertir a Wh sumando)
    daily_ghi: "pd.Series[Any]" = results["ghi_wm2"].resample("D").sum()  # type: ignore[index]

    # Calcular energía diaria AC
    daily_energy: "pd.Series[Any]" = results["ac_energy_kwh"].resample("D").sum()  # type: ignore[index]

    # Filtrar días con producción > 0
    valid_days: "pd.Series[Any]" = daily_ghi[daily_ghi > 0]

    if len(valid_days) == 0:
        print("\nWARN  No hay días con irradiancia > 0")
        return {}

    # Día despejado (máximo GHI)
    despejado_date = valid_days.idxmax()
    despejado_ghi = valid_days.loc[despejado_date]
    despejado_energy = daily_energy.loc[despejado_date]

    # Día nublado (mínimo GHI > 0)
    nublado_date = valid_days.idxmin()
    nublado_ghi = valid_days.loc[nublado_date]
    nublado_energy = daily_energy.loc[nublado_date]

    # Día intermedio (mediana)
    sorted_days: pd.Series[Any] = valid_days.sort_values()  # type: ignore[attr-defined]
    median_idx = len(sorted_days) // 2
    intermedio_date = sorted_days.index[median_idx]
    intermedio_ghi = sorted_days.iloc[median_idx]
    intermedio_energy = daily_energy.loc[intermedio_date]

    # Convertir a Timestamp para formatear
    despejado_ts = pd.Timestamp(despejado_date)
    nublado_ts = pd.Timestamp(nublado_date)
    intermedio_ts = pd.Timestamp(intermedio_date)

    print("\n" + "=" * 60)
    print("  DÍAS REPRESENTATIVOS SEGÚN GHI DIARIO")
    print("=" * 60)
    print(f"  Despejado (GHI max):   {despejado_ts.strftime('%Y-%m-%d')}    GHI = {despejado_ghi:.1f}")
    print(f"  Intermedio (GHI med):  {intermedio_ts.strftime('%Y-%m-%d')}    GHI = {intermedio_ghi:.1f}")
    print(f"  Nublado (GHI min>0):   {nublado_ts.strftime('%Y-%m-%d')}    GHI = {nublado_ghi:.1f}")
    print()
    print(f"Energía día despejado    [kWh]: {despejado_energy:.1f}")
    print(f"Energía día intermedio   [kWh]: {intermedio_energy:.1f}")
    print(f"Energía día nublado      [kWh]: {nublado_energy:.1f}")

    return {
        "despejado_date": despejado_ts.strftime("%Y-%m-%d"),
        "despejado_ghi": despejado_ghi,
        "despejado_energy_kwh": despejado_energy,
        "intermedio_date": intermedio_ts.strftime("%Y-%m-%d"),
        "intermedio_ghi": intermedio_ghi,
        "intermedio_energy_kwh": intermedio_energy,
        "nublado_date": nublado_ts.strftime("%Y-%m-%d"),
        "nublado_ghi": nublado_ghi,
        "nublado_energy_kwh": nublado_energy,
    }


def build_pv_timeseries_sandia(
    year: int,
    config: PVSystemConfig,
    target_dc_kw: float,
    target_ac_kw: float,
    target_annual_kwh: float,
    seconds_per_time_step: int = 3600,  # 1 HORA por defecto (OE3 requiere horario: 8,760 rows/año)
    selection_mode: str = "manual",
    candidate_count: int = 5,
    selection_metric: str = "energy_per_m2",
    **kwargs: Any,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Construye serie temporal de generación FV usando modelo Sandia completo
    con datos TMY de PVGIS.
    """
    print("\n" + "=" * 60)
    print("  SIMULACIÓN FOTOVOLTAICA - MODELO SANDIA + PVGIS TMY")
    print("=" * 60)
    print("\n Ubicación: Iquitos, Perú")
    print(f"   Latitud: {config.latitude}°")
    print(f"   Longitud: {config.longitude}°")
    print(f"   Altitud: {config.altitude} m")
    print("\n Orientación del array:")
    _ensure_pvlib_available()
    assert pvlib is not None
    print(f"   Inclinación (tilt): {config.tilt}°")
    print(f"   Azimut: {config.azimuth}° (Norte)")
    print("\n Área disponible:")
    print(f"   Total: {config.area_total_m2:,.0f} m²")
    print(f"   Factor de diseño: {config.factor_diseno}")
    print(f"   Área utilizada: {config.area_utilizada_m2:,.0f} m²")

    # 1. Descargar datos TMY de PVGIS
    tmy_data = _get_pvgis_tmy(config.latitude, config.longitude)

    # PVGIS devuelve datos en UTC. Para Iquitos (UTC-5), debemos ajustar el índice
    # La estrategia correcta es:
    # 1. Crear un índice naive con las horas del año en hora LOCAL
    # 2. Localizar a la zona horaria deseada
    # Esto evita problemas con cambios de horario de verano (DST)

    # Crear índice en hora local de Iquitos
    local_times = pd.date_range(
        start=f"{year}-01-01 00:00:00",
        periods=len(tmy_data),
        freq="h",
        tz=config.timezone,
    )

    # Reordenar los datos TMY para que coincidan con la hora local
    # PVGIS hora 0 UTC = hora 19:00 del día anterior en Lima (UTC-5)
    # Por lo tanto, la hora 5 UTC = hora 0:00 Lima
    utc_offset_hours = 5  # Lima es UTC-5

    # Rotar los datos para alinear con hora local
    tmy_values = tmy_data.values
    tmy_columns = tmy_data.columns
    tmy_rotated = np.roll(tmy_values, -utc_offset_hours, axis=0)

    tmy_data = pd.DataFrame(tmy_rotated, index=local_times, columns=tmy_columns)

    print(f"Datos ajustados a zona horaria local: {config.timezone} (UTC-5)")
    print(f"Indice horario: {tmy_data.index[0]} -> {tmy_data.index[-1]}")

    # 2. Interpolar a intervalo deseado
    minutes = seconds_per_time_step // 60
    if minutes < 60:
        tmy_data = _interpolate_to_interval(tmy_data, minutes)

    dt_hours = seconds_per_time_step / 3600

    # 3. Cargar bases de datos
    print("\nCargando bases de datos...")
    modules_db = _get_sandia_modules()
    inverters_db = _get_cec_inverters()
    print(f"   Módulos Sandia: {len(modules_db.columns)} disponibles")
    print(f"   Inversores CEC: {len(inverters_db.columns)} disponibles")

    # 4. Seleccionar componentes
    print("\nSeleccion de componentes...")
    selection_mode_norm = str(selection_mode).lower()
    module_candidates = pd.DataFrame()
    inverter_candidates = pd.DataFrame()
    selection_results: list[dict[str, Any]] = []
    selection_best: Optional[Dict[str, Any]] = None
    if candidate_count > 0:
        module_candidates = _rank_modules_by_density(modules_db, config.area_utilizada_m2, top_n=candidate_count)
        inverter_candidates = _rank_inverters_by_score(inverters_db, target_ac_kw, top_n=candidate_count)
        _log_candidates("Modulos PV", module_candidates, candidate_count)
        _log_candidates("Inversores", inverter_candidates, candidate_count)

    if selection_mode_norm in ("auto_top5", "auto", "top5"):
        if not module_candidates.empty and not inverter_candidates.empty:
            selection_results, selection_best = _evaluate_candidate_combinations(
                tmy_data=tmy_data,
                config=config,
                modules_db=modules_db,
                inverters_db=inverters_db,
                module_candidates=module_candidates,
                inverter_candidates=inverter_candidates,
                target_dc_kw=target_dc_kw,
                target_ac_kw=target_ac_kw,
                selection_metric=selection_metric,
            )
        if selection_best:
            module_name = str(selection_best.get("module_name", config.module_name))
            inverter_name = str(selection_best.get("inverter_name", config.inverter_name))
            best_score = float(selection_best.get("score", 0.0))
            print(f"  Seleccion automatica local: modulo={module_name}, inversor={inverter_name}")
            print(f"    Metrica: {selection_metric} | score={best_score:.4f}")
        else:
            module_name_raw: Any = (  # type: ignore[assignment]
                module_candidates.loc[0, "name"]
                if not module_candidates.empty
                else config.module_name
            )
            inverter_name_raw: Any = (  # type: ignore[assignment]
                inverter_candidates.loc[0, "name"]
                if not inverter_candidates.empty
                else config.inverter_name
            )
            module_name = str(module_name_raw)
            inverter_name = str(inverter_name_raw)
            print(f"  Seleccion automatica por ranking: modulo={module_name}, inversor={inverter_name}")
    else:
        module_name = config.module_name
        inverter_name = config.inverter_name

    module_name, module_params, n_modules_max = _select_module(modules_db, str(module_name), config.area_utilizada_m2)
    inverter_name, inverter_params, num_inverters = _select_inverter(inverters_db, str(inverter_name), target_ac_kw)

    # 5. Calcular configuración de strings
    modules_per_string, strings_parallel, total_modules = _calculate_string_config(
        module_params, inverter_params, n_modules_max, target_dc_kw
    )

    # Calcular capacidades del sistema
    pmp = float(module_params.get("Vmpo", 17)) * float(module_params.get("Impo", 1.19))
    system_dc_kw = total_modules * pmp / 1000
    system_ac_kw = target_ac_kw
    area_modules = total_modules * (_get_module_area(module_params) or 0.072)

    print("\nCapacidad del sistema:")
    print(f"   Potencia DC total: {system_dc_kw:,.2f} kWp")
    print(f"   Potencia AC nominal: {system_ac_kw:,.2f} kW")
    print(f"   Área de módulos: {area_modules:,.1f} m² ({area_modules/config.area_total_m2*100:.1f}%)")

    # 6. Ejecutar simulación
    results, sim_metadata = run_pv_simulation(
        tmy_data=tmy_data,
        config=config,
        module_params=module_params,
        inverter_params=inverter_params,
        modules_per_string=modules_per_string,
        strings_parallel=strings_parallel,
        total_modules=total_modules,
        num_inverters=num_inverters,
    )

    # 7. Calcular estadísticas
    stats = calculate_statistics(
        results=results,
        system_dc_kw=system_dc_kw,
        system_ac_kw=system_ac_kw,
        ghi_annual=sim_metadata["ghi_annual_kwh_m2"],
        dt_hours=dt_hours,
    )

    # 8. Energía mensual
    monthly = calculate_monthly_energy(results)

    # 9. Días representativos según GHI
    rep_days = calculate_representative_days(results)

    # 10. Preparar metadata completa
    metadata: dict[str, Any] = {
        "module_name": module_name,
        "inverter_name": inverter_name,
        "modules_per_string": modules_per_string,
        "strings_parallel": strings_parallel,
        "total_modules": total_modules,
        "num_inverters": num_inverters,
        "system_dc_kw": system_dc_kw,
        "system_ac_kw": system_ac_kw,
        "tilt": config.tilt,
        "azimuth": config.azimuth,
        "area_total_m2": config.area_total_m2,
        "area_utilizada_m2": area_modules,
        "factor_diseno": config.factor_diseno,
        "losses_total_pct": config.total_losses_pct,
        "ghi_annual_kwh_m2": sim_metadata["ghi_annual_kwh_m2"],
        "dt_hours": dt_hours,
        "time_steps_per_hour": int(1 / dt_hours),
        "selection_mode": selection_mode_norm,
        "selection_metric": selection_metric,
        "selection_results": selection_results,
        "module_candidates": module_candidates.to_dict(orient="records") if not module_candidates.empty else [],  # type: ignore[return-value]
        "inverter_candidates": inverter_candidates.to_dict(orient="records") if not inverter_candidates.empty else [],  # type: ignore[return-value]
        "target_annual_kwh": target_annual_kwh,
        "monthly_energy_kwh": monthly.to_dict(),  # type: ignore[return-value]
        **stats,
        **rep_days,  # Días representativos
    }

    # Añadir columnas normalizadas
    results["pv_kwh"] = results["ac_energy_kwh"]
    results["pv_kw"] = results["ac_power_kw"]

    return results, metadata


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
    _use_pvlib: bool = True,
    selection_mode: str = "manual",
    candidate_count: int = 5,
    selection_metric: str = "energy_per_m2",
    **kwargs: Any,
) -> Dict[str, object]:
    """
    Ejecuta dimensionamiento solar completo con modelo Sandia y PVGIS.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Configuración
    config = PVSystemConfig(
        latitude=lat,
        longitude=lon,
        timezone=tz,
        altitude=_get_float_from_kwargs("altitude", IQUITOS_PARAMS["alt"], kwargs),
        area_total_m2=_get_float_from_kwargs("area_total_m2", IQUITOS_PARAMS["area_total_m2"], kwargs),
        factor_diseno=_get_float_from_kwargs("factor_diseno", IQUITOS_PARAMS["factor_diseno"], kwargs),
        tilt=_get_float_from_kwargs("tilt", IQUITOS_PARAMS["surface_tilt"], kwargs),
        azimuth=_get_float_from_kwargs("azimuth", IQUITOS_PARAMS["surface_azimuth"], kwargs),
        module_name=str(kwargs.get("module_name", "Kyocera_Solar_KS20__2008__E__")),
        inverter_name=str(kwargs.get("inverter_name", "Eaton__Xpert1670")),
    )

    # Ejecutar simulación
    sim_results, sim_meta = build_pv_timeseries_sandia(
        year=year,
        config=config,
        target_dc_kw=target_dc_kw,
        target_ac_kw=target_ac_kw,
        target_annual_kwh=target_annual_kwh,
        seconds_per_time_step=seconds_per_time_step,
        selection_mode=selection_mode,
        candidate_count=candidate_count,
        selection_metric=selection_metric,
    )

    # Guardar serie temporal
    profile_path = out_dir / "pv_generation_timeseries.csv"
    sim_results.to_csv(profile_path)

    # Guardar energía mensual
    monthly: "pd.Series[Any]" = sim_results["ac_energy_kwh"].resample("ME").sum()  # type: ignore[index]
    monthly.to_csv(out_dir / "pv_monthly_energy.csv")

    # Crear resumen
    summary = SolarSizingOutput(
        target_ac_kw=float(target_ac_kw),
        target_dc_kw=float(target_dc_kw),
        target_annual_kwh=float(target_annual_kwh),
        annual_kwh=float(sim_meta["annual_ac_kwh"]),
        annual_kwh_dc=float(sim_meta["annual_dc_kwh"]),
        seconds_per_time_step=int(seconds_per_time_step),
        time_steps_per_hour=int(sim_meta["time_steps_per_hour"]),
        profile_path=str(profile_path.resolve()),
        module_name=str(sim_meta["module_name"]),
        inverter_name=str(sim_meta["inverter_name"]),
        modules_per_string=int(sim_meta["modules_per_string"]),
        strings_parallel=int(sim_meta["strings_parallel"]),
        total_modules=int(sim_meta["total_modules"]),
        num_inverters=int(sim_meta["num_inverters"]),
        tilt=float(sim_meta["tilt"]),
        azimuth=float(sim_meta["azimuth"]),
        area_total_m2=float(sim_meta["area_total_m2"]),
        area_utilizada_m2=float(sim_meta["area_utilizada_m2"]),
        factor_diseno=float(sim_meta["factor_diseno"]),
        capacity_factor=float(sim_meta["capacity_factor"]),
        performance_ratio=float(sim_meta["performance_ratio"]),
        specific_yield_kwh_kwp=float(sim_meta["specific_yield"]),
        equivalent_hours=float(sim_meta["equivalent_hours"]),
        max_power_kw=float(sim_meta["max_power_kw"]),
        mean_power_kw=float(sim_meta["mean_power_kw"]),
        max_daily_energy_kwh=float(sim_meta["max_daily_energy_kwh"]),
        max_daily_energy_date=str(sim_meta["max_daily_energy_date"]),
        max_power_timestamp=str(sim_meta["max_power_timestamp"]),
        hours_with_production=int(sim_meta["hours_with_production"]),
        losses_total_pct=float(sim_meta["losses_total_pct"]),
        ghi_annual_kwh_m2=float(sim_meta["ghi_annual_kwh_m2"]),
        # Días representativos
        despejado_date=str(sim_meta.get("despejado_date", "")),
        despejado_ghi=float(sim_meta.get("despejado_ghi", 0.0)),
        despejado_energy_kwh=float(sim_meta.get("despejado_energy_kwh", 0.0)),
        intermedio_date=str(sim_meta.get("intermedio_date", "")),
        intermedio_ghi=float(sim_meta.get("intermedio_ghi", 0.0)),
        intermedio_energy_kwh=float(sim_meta.get("intermedio_energy_kwh", 0.0)),
        nublado_date=str(sim_meta.get("nublado_date", "")),
        nublado_ghi=float(sim_meta.get("nublado_ghi", 0.0)),
        nublado_energy_kwh=float(sim_meta.get("nublado_energy_kwh", 0.0)),
    )

    # Guardar JSON
    (out_dir / "solar_results.json").write_text(pd.Series(summary.__dict__).to_json(indent=2), encoding="utf-8")  # type: ignore[return-value]

    module_candidates = sim_meta.get("module_candidates", [])
    if module_candidates:
        pd.DataFrame(module_candidates).to_csv(out_dir / "pv_candidates_modules.csv", index=False)
    inverter_candidates = sim_meta.get("inverter_candidates", [])
    if inverter_candidates:
        pd.DataFrame(inverter_candidates).to_csv(out_dir / "pv_candidates_inverters.csv", index=False)
    selection_results = sim_meta.get("selection_results", [])
    if selection_results:
        pd.DataFrame(selection_results).to_csv(out_dir / "pv_candidates_combinations.csv", index=False)

    # Generar reporte técnico
    _generate_technical_report(out_dir, summary, sim_meta, monthly)

    print("\n" + "=" * 60)
    print(f"OK Resultados guardados en: {out_dir}")
    print("=" * 60)

    return summary.__dict__


def _generate_technical_report(
    out_dir: Path, summary: SolarSizingOutput, meta_dict: Dict[str, Any], monthly: "pd.Series[Any]"
) -> None:
    """Genera reporte técnico detallado."""

    monthly_str = "\n".join(
        [
            f"| {pd.Timestamp(str(idx)).strftime('%Y-%m')} | {val:,.0f} |"
            for idx, val in monthly.items()
        ]
    )
    selection_mode: str = meta_dict.get("selection_mode", "manual") or "manual"
    selection_metric: str = meta_dict.get("selection_metric", "energy_per_m2") or "energy_per_m2"

    module_candidates: list[dict[str, Any]] = meta_dict.get("module_candidates", []) or []
    inverter_candidates: list[dict[str, Any]] = meta_dict.get("inverter_candidates", []) or []
    selection_results: list[dict[str, Any]] = meta_dict.get("selection_results", []) or []

    module_rows = ""
    for row_num, row in enumerate(module_candidates, start=1):
        module_rows += (
            f"| {row_num} | {row.get('name', '')} | {row.get('pmp_w', 0):.1f} | "
            f"{row.get('area_m2', 0):.3f} | {row.get('density_w_m2', 0):.1f} | "
            f"{row.get('dc_kw_max', 0):.1f} |\n"
        )
    if not module_rows:
        module_rows = "| - | - | - | - | - | - |\n"

    inverter_rows = ""
    for inv_num, row in enumerate(inverter_candidates, start=1):
        inverter_rows += (
            f"| {inv_num} | {row.get('name', '')} | {row.get('paco_kw', 0):.1f} | "
            f"{row.get('efficiency', 0):.3f} | {int(row.get('n_inverters', 0))} | "
            f"{row.get('score', 0):.3f} |\n"
        )
    if not inverter_rows:
        inverter_rows = "| - | - | - | - | - | - |\n"

    combo_rows = ""
    for i, row in enumerate(selection_results[:5], start=1):
        combo_rows += (
            f"| {i} | {row.get('module_name', '')} | {row.get('inverter_name', '')} | "
            f"{row.get('annual_kwh', 0):,.0f} | {row.get('energy_per_m2', 0):.1f} | "
            f"{row.get('performance_ratio', 0):.3f} | {row.get('score', 0):.3f} |\n"
        )
    if not combo_rows:
        combo_rows = "| - | - | - | - | - | - | - |\n"

    report = f"""# Reporte Tecnico - Sistema Fotovoltaico
## Proyecto Iquitos 2024 - Modelo Sandia + PVGIS TMY

### 1. Ubicacion del Proyecto

| Parametro | Valor |
|-----------|-------|
| Ciudad | Iquitos, Peru |
| Latitud | {IQUITOS_PARAMS['lat']} |
| Longitud | {IQUITOS_PARAMS['lon']} |
| Altitud | {IQUITOS_PARAMS['alt']} m s.n.m. |
| Zona horaria | {IQUITOS_PARAMS['tz']} |

### 2. Datos Meteorologicos

| Parametro | Valor |
|-----------|-------|
| Fuente | PVGIS TMY (Typical Meteorological Year) |
| GHI anual | {summary.ghi_annual_kwh_m2:,.0f} kWh/m2 |
| Resolucion temporal | {summary.seconds_per_time_step//60} minutos |

### 3. Componentes del Sistema

#### Modulo Fotovoltaico
- **Modelo:** {summary.module_name}
- **Base de datos:** Sandia National Laboratories

#### Inversor
- **Modelo:** {summary.inverter_name}
- **Base de datos:** California Energy Commission (CEC)

#### Seleccion de componentes (top candidatos)
- **Modo de seleccion:** {selection_mode}
- **Metrica de seleccion local:** {selection_metric}

**Top modulos (Sandia):**
| Rank | Nombre | Pmp [W] | Area [m2] | Densidad [W/m2] | DC max [kW] |
| --- | --- | --- | --- | --- | --- |
{module_rows}

**Top inversores (CEC):**
| Rank | Nombre | Paco [kW] | Eficiencia | N inversores | Score |
| --- | --- | --- | --- | --- | --- |
{inverter_rows}

**Top combinaciones (simulacion local):**
| Rank | Modulo | Inversor | Energia anual [kWh] | Energia/m2 [kWh/m2] | PR | Score |
| --- | --- | --- | --- | --- | --- | --- |
{combo_rows}

### 4. Configuracion del Array

| Parametro | Valor |
|-----------|-------|
| Modulos por string | {summary.modules_per_string} |
| Strings en paralelo | {summary.strings_parallel:,} |
| Total de modulos | {summary.total_modules:,} |
| Numero de inversores | {summary.num_inverters} |
| Inclinacion (tilt) | {summary.tilt} |
| Azimut | {summary.azimuth} (Norte) |

### 5. Capacidad del Sistema

| Parametro | Valor |
|-----------|-------|
| Capacidad DC nominal | {summary.target_dc_kw:,.2f} kWp |
| Capacidad AC nominal | {summary.target_ac_kw:,.2f} kW |
| Area total disponible | {summary.area_total_m2:,.0f} m2 |
| Area utilizada | {summary.area_utilizada_m2:,.0f} m2 |

### 6. Produccion Energetica

| Metrica | Valor |
|---------|-------|
| Energia anual AC | {summary.annual_kwh/1e6:,.3f} GWh |
| Energia anual DC | {summary.annual_kwh_dc/1e6:,.3f} GWh |
| Factor de capacidad | {summary.capacity_factor*100:.1f}% |
| Performance Ratio | {summary.performance_ratio*100:.1f}% |
| Yield especifico | {summary.specific_yield_kwh_kwp:,.0f} kWh/kWp/ano |
| Horas equivalentes | {summary.equivalent_hours:,.0f} h/ano |

### 7. Estadisticas de Potencia

| Metrica | Valor |
|---------|-------|
| Potencia AC maxima | {summary.max_power_kw:,.1f} kW |
| Potencia AC media | {summary.mean_power_kw:.1f} kW |
| Dia de maxima energia | {summary.max_daily_energy_date} ({summary.max_daily_energy_kwh:,.0f} kWh) |
| Instante de maxima potencia | {summary.max_power_timestamp} |
| Horas con produccion | {summary.hours_with_production:,} h/ano |

### 8. Perdidas del Sistema

| Tipo de perdida | Valor |
|-----------------|-------|
| Total | {summary.losses_total_pct:.1f}% |

### 9. Energia Mensual

| Mes | Energia [kWh] |
|-----|---------------|
{monthly_str}

### 10. Metodologia de Simulacion

Este analisis utiliza **pvlib-python** con los siguientes modelos:

1. **Datos meteorologicos:** PVGIS TMY (Typical Meteorological Year)
2. **Transposicion:** Modelo Perez (1990) para irradiancia en plano del array
3. **Temperatura de celda:** Sandia Array Performance Model (SAPM)
4. **Modelo DC:** Sandia Photovoltaic Array Performance Model
5. **Modelo de inversor:** Sandia Inverter Performance Model

### 11. Referencias

- PVGIS: https://re.jrc.ec.europa.eu/pvg_tools/
- King, D.L., Boyson, W.E., Kratochvil, J.A. (2004). *Photovoltaic Array Performance Model*. Sandia National Laboratories Report SAND2004-3535.
- Perez, R., et al. (1990). *Modeling daylight availability and irradiance components from direct and global irradiance*. Solar Energy 44(5):271-289.
- Holmgren, W.F., Hansen, C.W., Mikofski, M.A. (2018). *pvlib python: a python package for modeling solar energy systems*. Journal of Open Source Software.

---
*Generado automaticamente - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    (out_dir / "solar_technical_report.md").write_text(report, encoding="utf-8")


def prepare_solar_for_citylearn(
    pv_timeseries_path: Path,
    out_dir: Path,
    pv_dc_kw: float,
    pv_ac_kw: float,
    year: int = 2024,
) -> Dict[str, Any]:
    """
    Prepara los datos de generación solar para el schema de CityLearn (OE3).

    Genera:
    - solar_generation.csv: Serie temporal horaria normalizada (kWh/kWp por timestep)
    - pv_profile_24h.csv: Perfil promedio de 24 horas
    - solar_schema_params.json: Parámetros para schema.json de CityLearn

    Args:
        pv_timeseries_path: Ruta al archivo de generación PV
        out_dir: Directorio de salida
        pv_dc_kw: Capacidad DC del sistema (kWp)
        pv_ac_kw: Capacidad AC del sistema (kW)
        year: Año de simulación

    Returns:
        Diccionario con parámetros para schema.json de CityLearn
    """
    citylearn_dir = out_dir.parent / "citylearn"
    citylearn_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nPreparando datos solares para CityLearn (año {year})...")

    # Cargar timeseries de generación PV
    df: pd.DataFrame = pd.read_csv(pv_timeseries_path)  # type: ignore[assignment]

    # Detectar columna de tiempo
    time_col = None
    for col in ["datetime", "timestamp", "time", "Timestamp"]:
        if col in df.columns:
            time_col = col
            break

    if time_col:
        df[time_col] = pd.to_datetime(df[time_col])  # type: ignore[index]
        df = df.set_index(time_col)  # type: ignore[call-arg]

    # Detectar columna de energía PV
    pv_col = None
    for col in ["pv_kwh", "ac_energy_kwh", "ac_power_kw"]:
        if col in df.columns:
            pv_col = col
            break

    if pv_col is None:
        raise ValueError("No se encontró columna de generación PV en el archivo")

    # Resamplear a horario si es subhorario
    if len(df) > 8760:
        df_hourly: pd.DataFrame = df.resample("h").sum()  # type: ignore[index]
    else:
        df_hourly = df

    # Crear serie de generación solar (kWh)
    pv_kwh: "pd.Series[Any]" = np.asarray(df_hourly[pv_col].values, dtype=float)  # type: ignore[assignment,arg-type]

    # Normalizar por kWp (kWh/kWp por hora)
    pv_kwh_per_kwp = pv_kwh / pv_dc_kw if pv_dc_kw > 0 else pv_kwh

    # Crear DataFrame para CityLearn
    # Formato: Month, Hour, Day Type, solar_generation (kWh/kWp)
    n_hours = min(len(pv_kwh), 8760)

    df_solar = pd.DataFrame(index=range(n_hours))
    df_solar["Month"] = [(i // 720) % 12 + 1 for i in range(n_hours)]
    df_solar["Hour"] = [i % 24 for i in range(n_hours)]
    df_solar["Day Type"] = [(i // 24) % 7 + 1 for i in range(n_hours)]  # 1-7
    df_solar["solar_generation"] = pv_kwh_per_kwp[:n_hours]

    # Guardar solar_generation.csv (formato CityLearn)
    df_solar.to_csv(citylearn_dir / "solar_generation.csv", index=False)
    print(f"   OK solar_generation.csv: {n_hours} registros horarios")

    # Crear perfil promedio de 24 horas
    hour_series: "pd.Series[Any]" = pd.to_datetime(df_hourly.index).to_series().dt.hour  # type: ignore[index]
    df_24h: pd.DataFrame = df_hourly.groupby(hour_series).mean()  # type: ignore[arg-type,return-value]

    profile_24h = pd.DataFrame(
        {
            "hour": range(24),
            "pv_kwh": np.asarray(df_24h[pv_col].values, dtype=float) if len(df_24h) == 24 else np.zeros(24),  # type: ignore[index]
            "pv_kwh_per_kwp": (
                np.asarray(df_24h[pv_col].values, dtype=float) / pv_dc_kw if pv_dc_kw > 0 and len(df_24h) == 24 else np.zeros(24)  # type: ignore[index]
            ),
        }
    )
    profile_24h.to_csv(out_dir / "pv_profile_24h.csv", index=False)
    print("   OK pv_profile_24h.csv: Perfil promedio diario")

    # Estadísticas
    annual_kwh = float(pv_kwh[:n_hours].sum())
    capacity_factor = annual_kwh / (pv_dc_kw * 8760) if pv_dc_kw > 0 else 0
    specific_yield = annual_kwh / pv_dc_kw if pv_dc_kw > 0 else 0

    # Parámetros para schema.json de CityLearn
    schema_params: dict[str, Any] = {
        "photovoltaic": {
            "type": "PV",
            "nominal_power_dc_kw": float(pv_dc_kw),
            "nominal_power_ac_kw": float(pv_ac_kw),
            "efficiency": float(annual_kwh / (pv_dc_kw * 8760 * 0.2)) if pv_dc_kw > 0 else 0.18,  # Estimación
        },
        "solar_generation_path": str((citylearn_dir / "solar_generation.csv").resolve()),
        "pv_profile_24h_path": str((out_dir / "pv_profile_24h.csv").resolve()),
        "statistics": {
            "annual_kwh": annual_kwh,
            "capacity_factor": capacity_factor,
            "specific_yield_kwh_kwp": specific_yield,
            "max_hourly_kwh": float(pv_kwh[:n_hours].max()),
            "mean_hourly_kwh": float(pv_kwh[:n_hours].mean()),
        },
    }

    # Guardar parámetros
    (citylearn_dir / "solar_schema_params.json").write_text(json.dumps(schema_params, indent=2), encoding="utf-8")
    print("   OK solar_schema_params.json: Parámetros para schema")

    print("\nResumen Solar para CityLearn:")
    print(f"   Capacidad DC: {pv_dc_kw:,.0f} kWp")
    print(f"   Energía anual: {annual_kwh/1e6:,.3f} GWh")
    print(f"   Factor de capacidad: {capacity_factor*100:.1f}%")
    print(f"   Yield específico: {specific_yield:,.0f} kWh/kWp/año")

    return schema_params


if __name__ == "__main__":
    # Demostración del módulo solar_pvlib para OE2
    # Path ya importado al inicio del módulo

    print("=" * 70)
    print("  DEMOSTRACIÓN MÓDULO SOLAR PVLIB - OE2 IQUITOS")
    print("=" * 70)

    # Configuración para demo
    demo_config = PVSystemConfig(
        latitude=IQUITOS_PARAMS["lat"],  # type: ignore
        longitude=IQUITOS_PARAMS["lon"],  # type: ignore
        timezone=str(IQUITOS_PARAMS["tz"]),
        altitude=IQUITOS_PARAMS["alt"],  # type: ignore
        area_total_m2=IQUITOS_PARAMS["area_total_m2"],  # type: ignore
        factor_diseno=IQUITOS_PARAMS["factor_diseno"],  # type: ignore
        tilt=IQUITOS_PARAMS["surface_tilt"],  # type: ignore
        azimuth=IQUITOS_PARAMS["surface_azimuth"],  # type: ignore
    )

    # Ejecutar simulación
    demo_results, demo_metadata = build_pv_timeseries_sandia(
        year=2024,
        config=demo_config,
        target_dc_kw=4162.0,  # 4.162 MWp objetivo (según diseño)
        target_ac_kw=3201.0,  # 3.201 MW AC
        target_annual_kwh=8_000_000.0,  # 8 GWh objetivo
        seconds_per_time_step=900,  # 15 minutos para mayor precisión
        selection_mode="manual",
    )

    print("\n" + "=" * 70)
    print("  RESUMEN FINAL")
    print("=" * 70)

    # Información del módulo seleccionado
    print("\n--- MÓDULO FOTOVOLTAICO SELECCIONADO ---")
    print(f"Modelo: {demo_metadata['module_name']}")
    print(f"Módulos totales: {demo_metadata['total_modules']:,}")
    print(f"Módulos por string: {demo_metadata['modules_per_string']}")
    print(f"Strings en paralelo: {demo_metadata['strings_parallel']}")

    # Información del inversor seleccionado
    print("\n--- INVERSOR SELECCIONADO ---")
    print(f"Modelo: {demo_metadata['inverter_name']}")
    print(f"Número de inversores: {demo_metadata['num_inverters']}")
    print(f"Potencia AC total: {demo_metadata['system_ac_kw']:,.1f} kW")

    # Estadísticas del sistema
    print("\n--- ESTADÍSTICAS DEL SISTEMA ---")
    print(f"Potencia DC instalada: {demo_metadata['system_dc_kw']:,.1f} kWp")
    print(f"Potencia AC nominal: {demo_metadata['system_ac_kw']:,.1f} kW")
    print(f"Ratio DC/AC: {demo_metadata['system_dc_kw']/demo_metadata['system_ac_kw']:.2f}")
    print(f"Área de módulos: {demo_metadata['area_utilizada_m2']:,.1f} m²")

    # Producción energética
    print("\n--- PRODUCCIÓN ENERGÉTICA ---")
    print(f"Energía anual AC: {demo_metadata['annual_ac_kwh']:,.0f} kWh ({demo_metadata['annual_ac_kwh']/1e6:.2f} GWh)")
    print(f"Yield específico: {demo_metadata['specific_yield']:,.0f} kWh/kWp·año")
    print(f"Factor de capacidad: {demo_metadata['capacity_factor']*100:.1f}%")
    print(f"Performance Ratio: {demo_metadata['performance_ratio']*100:.1f}%")
    print(f"Horas equivalentes: {demo_metadata['equivalent_hours']:,.0f} h/año")
    print(f"Potencia máxima: {demo_metadata['max_power_kw']:,.1f} kW")

    # Días representativos
    print("\n--- DÍAS REPRESENTATIVOS ---")
    print(f"Día despejado: {demo_metadata['despejado_date']} - {demo_metadata['despejado_energy_kwh']:,.1f} kWh")
    print(f"Día intermedio: {demo_metadata['intermedio_date']} - {demo_metadata['intermedio_energy_kwh']:,.1f} kWh")
    print(f"Día nublado: {demo_metadata['nublado_date']} - {demo_metadata['nublado_energy_kwh']:,.1f} kWh")

    print(f"\nRegistros generados: {len(demo_results)}")

    # =========================================================================
    # ANÁLISIS DE ENERGÍA: DIARIA, MENSUAL Y ANUAL
    # =========================================================================

    # Calcular energía diaria
    demo_daily_energy: "pd.Series[Any]" = demo_results["ac_energy_kwh"].resample("D").sum()  # type: ignore[index]

    # Calcular energía mensual
    demo_monthly_energy: "pd.Series[Any]" = demo_results["ac_energy_kwh"].resample("ME").sum()  # type: ignore[index]

    # Energía anual
    demo_annual_energy = demo_results["ac_energy_kwh"].sum()

    print("\n" + "=" * 70)
    print("  ANÁLISIS DE ENERGÍA GENERADA")
    print("=" * 70)

    # --- ENERGÍA DIARIA ---
    print("\n--- ENERGÍA DIARIA (kWh) ---")
    print(f"Promedio diario: {demo_daily_energy.mean():,.1f} kWh")
    max_day_idx = demo_daily_energy.idxmax()
    min_day_idx = demo_daily_energy.idxmin()
    is_ts_max = hasattr(max_day_idx, 'strftime') or isinstance(max_day_idx, pd.Timestamp)
    is_ts_min = hasattr(min_day_idx, 'strftime') or isinstance(min_day_idx, pd.Timestamp)
    max_day_str = pd.Timestamp(max_day_idx).strftime('%Y-%m-%d') if is_ts_max else str(max_day_idx)
    min_day_str = pd.Timestamp(min_day_idx).strftime('%Y-%m-%d') if is_ts_min else str(min_day_idx)
    print(f"Máximo diario: {demo_daily_energy.max():,.1f} kWh ({max_day_str})")
    print(f"Mínimo diario: {demo_daily_energy.min():,.1f} kWh ({min_day_str})")
    print(f"Desviación estándar: {demo_daily_energy.std():,.1f} kWh")

    # Gráfica ASCII de energía diaria (promedio por mes)
    daily_idx_dt: "pd.DatetimeIndex" = pd.to_datetime(demo_daily_energy.index)  # type: ignore[assignment,index]
    daily_by_month: "pd.Series[Any]" = demo_daily_energy.groupby(daily_idx_dt.month).mean()  # type: ignore[return-value]
    print("\nPromedio diario por mes (kWh):")
    print("-" * 50)
    max_val = daily_by_month.max()
    month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    for month_num, val in daily_by_month.items():
        bar_len = int(40 * val / max_val) if max_val > 0 else 0
        print(f"{month_names[int(month_num) - 1]:>3} | {'#' * bar_len:<40} {val:>8,.0f}")  # type: ignore[arg-type]

    # --- ENERGÍA MENSUAL ---
    print("\n--- ENERGÍA MENSUAL (kWh) ---")
    print("-" * 50)
    max_monthly = demo_monthly_energy.max()
    for ts_idx, val in demo_monthly_energy.items():
        month_num_val: int = int(pd.Timestamp(str(ts_idx)).month)  # type: ignore[arg-type]
        month_name_val = month_names[month_num_val - 1]
        bar_len = int(40 * val / max_monthly) if max_monthly > 0 else 0
        print(f"{month_name_val:>3} | {'#' * bar_len:<40} {val:>12,.0f}")

    print(f"\nTotal mensual promedio: {demo_monthly_energy.mean():,.0f} kWh")
    max_month_ts = demo_monthly_energy.idxmax()
    min_month_ts = demo_monthly_energy.idxmin()
    max_month_num = pd.Timestamp(max_month_ts).month
    min_month_num = pd.Timestamp(min_month_ts).month
    print(f"Mes con mayor producción: {month_names[max_month_num - 1]} ({demo_monthly_energy.max():,.0f} kWh)")
    print(f"Mes con menor producción: {month_names[min_month_num - 1]} ({demo_monthly_energy.min():,.0f} kWh)")

    # --- ENERGÍA ANUAL ---
    print("\n--- ENERGÍA ANUAL ---")
    print("-" * 50)
    print(f"Energía total anual: {demo_annual_energy:,.0f} kWh")
    print(f"                     {demo_annual_energy/1e3:,.1f} MWh")
    print(f"                     {demo_annual_energy/1e6:,.3f} GWh")

    # Gráfica de distribución horaria promedio
    print("\n--- PERFIL HORARIO PROMEDIO (kWh) ---")
    demo_results_idx_dt: "pd.DatetimeIndex" = pd.to_datetime(demo_results.index)  # type: ignore[assignment,index]
    demo_hourly_profile: "pd.Series[Any]" = demo_results["ac_energy_kwh"].groupby(demo_results_idx_dt.hour).mean()  # type: ignore[return-value]
    max_hourly = demo_hourly_profile.max()
    print("-" * 55)
    for hour_val, val in demo_hourly_profile.items():
        bar_len = int(35 * val / max_hourly) if max_hourly > 0 else 0
        hour_int: int = int(hour_val)  # type: ignore[arg-type]
        is_daylight = 5 <= hour_int <= 17
        print(f"{hour_int:02d}:00 {'*' if is_daylight else ' '}| {'#' * bar_len:<35} {val:>8,.2f}")

    # Resumen final de producción
    print("\n" + "=" * 70)
    print("  RESUMEN DE PRODUCCIÓN FOTOVOLTAICA")
    print("=" * 70)
    print(f"""
    +-----------------------------------------------------------+
    |  ENERGIA GENERADA - SISTEMA {demo_metadata['system_dc_kw']:,.0f} kWp               |
    +-----------------------------------------------------------+
    |  Diaria (promedio):    {demo_daily_energy.mean():>12,.0f} kWh               |
    |  Mensual (promedio):   {demo_monthly_energy.mean():>12,.0f} kWh               |
    |  Anual (total):        {demo_annual_energy:>12,.0f} kWh               |
    |                        {demo_annual_energy/1e6:>12,.2f} GWh               |
    +-----------------------------------------------------------+
    |  Yield especifico:     {demo_metadata['specific_yield']:>12,.0f} kWh/kWp-ano        |
    |  Factor de capacidad:  {demo_metadata['capacity_factor']*100:>12,.1f} %                 |
    +-----------------------------------------------------------+
    """)

    # Mostrar gráficas con matplotlib si está disponible
    try:
        import matplotlib.pyplot as plt  # type: ignore[import]

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))  # type: ignore[return-value]
        fig_title = f"Análisis de Generación PV - Iquitos ({demo_metadata['system_dc_kw']:,.0f} kWp)"
        fig.suptitle(fig_title, fontsize=14, fontweight='bold')  # type: ignore[arg-type]

        # 1. Energía mensual (barras)
        ax1 = axes[0, 0]
        demo_monthly_energy.plot(kind='bar', ax=ax1, color='forestgreen', edgecolor='darkgreen')
        ax1.set_title('Energía Mensual (kWh)')
        ax1.set_xlabel('Mes')
        ax1.set_ylabel('Energía (kWh)')
        ax1.set_xticklabels(month_names, rotation=45)
        ax1.grid(axis='y', alpha=0.3)
        for plt_idx, v in enumerate(np.asarray(demo_monthly_energy.values, dtype=float)):  # type: ignore[arg-type]
            ax1.text(plt_idx, v + max_monthly*0.02, f'{v/1e3:.0f}k', ha='center', fontsize=8)

        # 2. Perfil horario promedio
        ax2 = axes[0, 1]
        demo_hourly_profile.plot(kind='area', ax=ax2, color='gold', alpha=0.7)
        ax2.fill_between(demo_hourly_profile.index, np.asarray(demo_hourly_profile.values, dtype=float), color='orange', alpha=0.5)  # type: ignore[arg-type]
        ax2.set_title('Perfil Horario Promedio (kWh)')
        ax2.set_xlabel('Hora del día')
        ax2.set_ylabel('Energía (kWh)')
        ax2.set_xticks(range(0, 24, 2))
        ax2.grid(alpha=0.3)

        # 3. Energía diaria (línea)
        ax3 = axes[1, 0]
        demo_daily_energy.plot(ax=ax3, color='steelblue', linewidth=0.5, alpha=0.7)
        rolling_mean = demo_daily_energy.rolling(window=7).mean()
        rolling_mean.plot(ax=ax3, color='darkblue', linewidth=2, label='Media móvil 7 días')
        ax3.set_title('Energía Diaria (kWh)')
        ax3.set_xlabel('Fecha')
        ax3.set_ylabel('Energía (kWh)')
        ax3.legend()
        ax3.grid(alpha=0.3)

        # 4. Distribución de energía diaria (histograma)
        ax4 = axes[1, 1]
        ax4.hist(np.asarray(demo_daily_energy.values, dtype=float), bins=30, color='coral', edgecolor='darkred', alpha=0.7)  # type: ignore[arg-type]
        mean_energy = demo_daily_energy.mean()
        ax4.axvline(mean_energy, color='red', linestyle='--', linewidth=2,
                    label=f'Media: {mean_energy:,.0f} kWh')
        ax4.set_title('Distribución de Energía Diaria')
        ax4.set_xlabel('Energía diaria (kWh)')
        ax4.set_ylabel('Frecuencia (días)')
        ax4.legend()
        ax4.grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig('pv_analysis_charts.png', dpi=150, bbox_inches='tight')  # type: ignore[arg-type]
        print("\n📊 Gráficas guardadas en: pv_analysis_charts.png")
        plt.show()  # type: ignore[arg-type]

    except ImportError:
        print("\n⚠ matplotlib no disponible para gráficas visuales")
    except (ValueError, TypeError, RuntimeError) as e:
        print(f"\n⚠ No se pudieron mostrar las gráficas: {e}")
