"""
Módulo de dimensionamiento de sistema de almacenamiento BESS.

Incluye:
- Carga de demanda real del mall desde CSV
- Simulación horaria del balance energético
- Estado de carga (SOC) de la batería
- Flujos de energía (red, BESS, PV)
- Gráficas de análisis completo
- Preparación de datos para CityLearn schema
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Type
import json
import math
import numpy as np
import pandas as pd  # type: ignore[import]
from matplotlib import pyplot as plt  # type: ignore[import]


@dataclass(frozen=True)
class BessSizingOutput:
    """Resultado del dimensionamiento del BESS."""
    capacity_kwh: float
    nominal_power_kw: float
    dod: float
    c_rate: float
    autonomy_hours: float
    peak_load_kw: float
    efficiency_roundtrip: float
    surplus_kwh_day: float
    deficit_kwh_day: float
    night_deficit_kwh_day: float
    pv_generation_kwh_day: float
    total_demand_kwh_day: float
    mall_demand_kwh_day: float
    ev_demand_kwh_day: float
    bess_load_scope: str
    pv_available_kwh_day: float
    bess_load_kwh_day: float
    sizing_mode: str
    grid_import_kwh_day: float
    grid_export_kwh_day: float
    self_sufficiency: float
    cycles_per_day: float
    soc_min_percent: float
    soc_max_percent: float
    profile_path: str
    results_path: str


@dataclass
class BessSimulationHour:
    """Datos de simulación para una hora."""
    hour: int
    pv_kwh: float
    mall_kwh: float
    ev_kwh: float
    load_total_kwh: float
    net_balance_kwh: float  # PV - Load (positivo = excedente)
    bess_charge_kwh: float
    bess_discharge_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float
    soc_percent: float
    soc_kwh: float


def load_mall_demand_real(
    mall_demand_path: Path,
    year: int = 2024,
) -> pd.DataFrame:
    """
    Carga la demanda real del mall desde CSV.

    Los datos del archivo están en kW (potencia) a intervalos de 15 minutos.
    Se convierten a kWh (energía) horaria.

    Args:
        mall_demand_path: Ruta al archivo CSV con demanda del mall
        year: Año de simulación

    Returns:
        DataFrame con demanda horaria del mall en kWh (8760 filas)
    """
    header = mall_demand_path.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
    sep = ";" if ";" in header and "," not in header else ","
    df = pd.read_csv(mall_demand_path, sep=sep)

    def find_col(candidates: list[str]) -> Optional[str]:
        for col in df.columns:
            if not isinstance(col, str):
                continue
            col_norm = col.strip().lower()
            for cand in candidates:
                if col_norm == cand or cand in col_norm:
                    return col
        return None

    date_col = find_col(["fecha", "horafecha", "datetime", "timestamp", "time"])
    if date_col is None:
        date_col = df.columns[0]

    demand_col = find_col(["demanda_kwh", "demandamallkwh", "demanda", "power_kw", "kw", "kwh"])
    if demand_col is None:
        candidates = [c for c in df.columns if c != date_col]
        demand_col = candidates[-1] if candidates else df.columns[0]

    df = df.rename(columns={date_col: "datetime", demand_col: "power_kw"})

    # Asegurar índice datetime
    df['datetime'] = pd.to_datetime(df['datetime'], dayfirst=True, errors='coerce')
    df['power_kw'] = pd.to_numeric(df['power_kw'], errors='coerce')
    df = df.dropna(subset=['datetime', 'power_kw'])
    df = df.set_index('datetime')

    # Detectar intervalo de tiempo
    if len(df) > 1:
        time_diff = (df.index[1] - df.index[0]).total_seconds() / 60  # en minutos
    else:
        time_diff = 15  # Asumir 15 min por defecto
    if time_diff <= 0:
        time_diff = 15

    demand_col_norm = demand_col.strip().lower()
    unit_is_energy = "kwh" in demand_col_norm
    df["power_kw"] = pd.to_numeric(df["power_kw"], errors="coerce")
    df = df.dropna(subset=["power_kw"])

    if unit_is_energy:
        # Los valores son energia por intervalo (kWh). Convertir a potencia y luego a energia horaria.
        df["energy_kwh"] = df["power_kw"]
        df["power_kw"] = df["energy_kwh"] * 60.0 / time_diff
    else:
        # Los valores son potencia (kW). Convertir a energia por intervalo.
        df["energy_kwh"] = df["power_kw"] * (time_diff / 60.0)

    if time_diff < 60:
        df_hourly = df["energy_kwh"].resample("h").sum().to_frame("mall_kwh")
    else:
        df_hourly = df["energy_kwh"].to_frame("mall_kwh")
    # Si los datos no cubren un año completo, repetir para llenar
    if len(df_hourly) < 8760:
        # Calcular perfil promedio diario
        df_hourly['hour'] = pd.to_datetime(df_hourly.index).hour  # type: ignore[union-attr]
        hourly_profile = df_hourly.groupby('hour')['mall_kwh'].mean()

        # Crear índice de año completo
        idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
        df_full = pd.DataFrame(index=idx)
        df_full['hour'] = pd.to_datetime(df_full.index).hour  # type: ignore[union-attr]
        df_full['mall_kwh'] = df_full['hour'].map(hourly_profile)
        df_full = df_full.drop(columns=['hour'])
        return df_full

    return df_hourly[['mall_kwh']]


def load_pv_generation(pv_timeseries_path: Path) -> pd.DataFrame:
    """Carga la generación PV desde timeseries."""
    df = pd.read_csv(pv_timeseries_path)

    # Detectar columna de tiempo
    time_col = None
    for col in ['datetime', 'timestamp', 'time', 'Timestamp']:
        if col in df.columns:
            time_col = col
            break

    if time_col:
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.set_index(time_col)

    # Resamplear a horario si es subhorario
    if len(df) > 8760:
        df_hourly = df.resample('h').sum()
    else:
        df_hourly = df

    # Buscar columna de generación PV
    pv_col = None
    for col in ['pv_kwh', 'ac_energy_kwh', 'ac_power_kw', 'p_ac']:
        if col in df_hourly.columns:
            pv_col = col
            break

    if pv_col:
        if 'power' in pv_col.lower() or 'p_ac' in pv_col.lower():
            # Si es potencia, convertir a energía (kW -> kWh para 1 hora)
            df_hourly['pv_kwh'] = df_hourly[pv_col]
        else:
            df_hourly['pv_kwh'] = df_hourly[pv_col]
    else:
        df_hourly['pv_kwh'] = 0.0

    return df_hourly[['pv_kwh']]


def load_ev_demand(ev_profile_path: Path, year: int = 2024) -> pd.DataFrame:
    """Carga el perfil de demanda EV con resolución de 15 minutos.

    El archivo CSV debe tener 96 intervalos (15 minutos cada uno) para un día típico.
    Se expande a 35,040 intervalos anuales (365 días × 96 intervalos/día).

    Returns:
        DataFrame con columnas 'interval' (0-35039) y 'ev_kwh' (energía en kWh por intervalo de 15 min)
    """
    df = pd.read_csv(ev_profile_path)

    # Verificar si es formato de 15 minutos (96 intervalos) o formato horario (24 horas)
    if 'interval' in df.columns and 'energy_kwh' in df.columns:
        # Formato nuevo: 96 intervalos de 15 minutos
        if len(df) == 96:
            # Expandir a 365 días (35,040 intervalos anuales)
            intervals_per_day = 96
            days_per_year = 365
            total_intervals = intervals_per_day * days_per_year  # 35,040

            # Repetir el patrón diario 365 veces
            df_annual = pd.DataFrame({'interval': np.arange(total_intervals)})
            df_annual['day_interval'] = df_annual['interval'] % intervals_per_day

            # Mapear energía del día típico
            df_daily = df[['interval', 'energy_kwh']].rename(columns={'interval': 'day_interval'})
            df_annual = df_annual.merge(df_daily, on='day_interval', how='left')
            df_annual = df_annual[['interval', 'energy_kwh']].rename(columns={'energy_kwh': 'ev_kwh'})

            return df_annual

    # Formato antiguo: 24 horas (retrocompatibilidad)
    if 'hour' in df.columns and 'energy_kwh' in df.columns:
        # Perfil de 24 horas, expandir a año
        hourly_profile = df.set_index('hour')['energy_kwh']
        idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
        df_full = pd.DataFrame(index=idx)
        df_full['hour'] = pd.to_datetime(df_full.index).hour  # type: ignore[union-attr]
        df_full['ev_kwh'] = df_full['hour'].map(hourly_profile)
        df_full = df_full.drop(columns=['hour'])
        return df_full

    raise ValueError("Formato de CSV no reconocido. Se esperan columnas 'interval' y 'energy_kwh' (96 intervalos) o 'hour' y 'energy_kwh' (24 horas)")


def simulate_bess_operation(
    pv_kwh: np.ndarray,
    ev_kwh: np.ndarray,
    mall_kwh: np.ndarray,
    capacity_kwh: float,
    power_kw: float,
    dod: float,
    efficiency: float,
    initial_soc: float = 0.5,
    soc_min: Optional[float] = None,
    discharge_hours: Optional[set[int]] = None,
    hours: Optional[np.ndarray] = None,
    discharge_to_mall: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Simula la operacion del BESS hora a hora con cargas separadas (EV y mall) y prioridad:
    1) PV -> EV
    2) PV -> BESS (carga)
    3) PV -> Mall
    4) Sobrante PV -> export
    5) Deficit -> descarga BESS (primero EV; opcional mall), luego import.
    """
    n_hours = len(pv_kwh)

    if soc_min is None:
        soc_min = (1.0 - dod)
    soc_min = max(0.0, min(1.0, float(soc_min)))
    soc_max = 1.0

    eff_charge = np.sqrt(efficiency)
    eff_discharge = np.sqrt(efficiency)

    soc = np.zeros(n_hours)
    bess_charge = np.zeros(n_hours)
    bess_discharge = np.zeros(n_hours)
    grid_import_ev = np.zeros(n_hours)
    grid_import_mall = np.zeros(n_hours)
    grid_export = np.zeros(n_hours)
    pv_used_ev = np.zeros(n_hours)
    pv_used_mall = np.zeros(n_hours)

    if capacity_kwh <= 0 or power_kw <= 0:
        # Sin BESS: PV a EV primero, luego mall; resto export/import
        pv_to_ev = np.minimum(pv_kwh, ev_kwh)
        pv_after_ev = pv_kwh - pv_to_ev
        pv_to_mall = np.minimum(pv_after_ev, mall_kwh)
        pv_used_ev = pv_to_ev
        pv_used_mall = pv_to_mall
        grid_export = np.maximum(pv_after_ev - pv_to_mall, 0)
        short_ev = ev_kwh - pv_to_ev
        short_mall = mall_kwh - pv_to_mall
        grid_import_ev = np.maximum(short_ev, 0)
        grid_import_mall = np.maximum(short_mall, 0)
        soc = np.full(n_hours, initial_soc if capacity_kwh > 0 else 0.0)
        df = pd.DataFrame({
            'hour': np.arange(n_hours) % 24,
            'pv_kwh': pv_kwh,
            'ev_kwh': ev_kwh,
            'mall_kwh': mall_kwh,
            'pv_used_ev_kwh': pv_used_ev,
            'pv_used_mall_kwh': pv_used_mall,
            'bess_charge_kwh': bess_charge,
            'bess_discharge_kwh': bess_discharge,
            'grid_import_ev_kwh': grid_import_ev,
            'grid_import_mall_kwh': grid_import_mall,
            'grid_export_kwh': grid_export,
            'soc_percent': soc * 100,
            'soc_kwh': soc * capacity_kwh,
        })
        total_pv = float(pv_kwh.sum())
        total_load = float(ev_kwh.sum() + mall_kwh.sum())
        total_grid_import = float(grid_import_ev.sum() + grid_import_mall.sum())
        total_grid_export = float(grid_export.sum())
        metrics = {
            'total_pv_kwh': total_pv,
            'total_load_kwh': total_load,
            'total_grid_import_kwh': total_grid_import,
            'total_grid_export_kwh': total_grid_export,
            'total_bess_charge_kwh': 0.0,
            'total_bess_discharge_kwh': 0.0,
            'pv_used_ev_kwh': float(pv_used_ev.sum()),
            'pv_used_mall_kwh': float(pv_used_mall.sum()),
            'grid_import_ev_kwh': float(grid_import_ev.sum()),
            'grid_import_mall_kwh': float(grid_import_mall.sum()),
            'self_sufficiency': 1.0 - (total_grid_import / max(total_load, 1e-9)),
            'cycles_per_day': 0.0,
            'soc_min_percent': float(soc.min() * 100) if n_hours > 0 else 0.0,
            'soc_max_percent': float(soc.max() * 100) if n_hours > 0 else 0.0,
        }
        return df, metrics

    current_soc = initial_soc

    for h in range(n_hours):
        hour = int(hours[h]) if hours is not None else int(h % 24)

        # Paso 1: PV -> EV
        pv_to_ev = min(pv_kwh[h], ev_kwh[h])
        pv_used_ev[h] = pv_to_ev
        remaining_pv = pv_kwh[h] - pv_to_ev

        # Paso 2: PV -> BESS (carga)
        soc_headroom = soc_max - current_soc
        max_charge_soc = soc_headroom * capacity_kwh
        max_charge_power = power_kw
        max_charge = min(max_charge_soc, max_charge_power, remaining_pv)
        actual_charge = max_charge * eff_charge
        bess_charge[h] = max_charge
        current_soc += actual_charge / capacity_kwh
        remaining_pv -= max_charge

        # Paso 3: PV -> Mall
        pv_to_mall = min(remaining_pv, mall_kwh[h])
        pv_used_mall[h] = pv_to_mall
        remaining_pv -= pv_to_mall

        # Export si aún sobra PV
        grid_export[h] = max(remaining_pv, 0.0)

        # Déficits EV y Mall tras PV
        ev_deficit = ev_kwh[h] - pv_to_ev
        mall_deficit = mall_kwh[h] - pv_to_mall

        # Paso 4: Descarga BESS para EV (y opcional Mall)
        allow_discharge = True
        if discharge_hours is not None:
            allow_discharge = hour in discharge_hours
        if allow_discharge:
            soc_available = max(current_soc - soc_min, 0.0)
            max_discharge_soc = soc_available * capacity_kwh
            max_discharge_power = power_kw
            energy_needed = ev_deficit + (mall_deficit if discharge_to_mall else 0.0)
            max_discharge = min(max_discharge_soc, max_discharge_power, energy_needed / eff_discharge if energy_needed>0 else 0.0)
            actual_discharge = max_discharge * eff_discharge
            # Priorizar EV en la descarga
            ev_cover = min(actual_discharge, ev_deficit)
            mall_cover = actual_discharge - ev_cover if discharge_to_mall else 0.0
            ev_deficit -= ev_cover
            mall_deficit -= mall_cover
            bess_discharge[h] = ev_cover + mall_cover
            current_soc -= max_discharge / capacity_kwh

        # Paso 5: Importar lo que falte
        grid_import_ev[h] = max(ev_deficit, 0.0)
        grid_import_mall[h] = max(mall_deficit, 0.0)

        soc[h] = current_soc

    df = pd.DataFrame({
        'hour': np.arange(n_hours) % 24,
        'pv_kwh': pv_kwh,
        'ev_kwh': ev_kwh,
        'mall_kwh': mall_kwh,
        'pv_used_ev_kwh': pv_used_ev,
        'pv_used_mall_kwh': pv_used_mall,
        'bess_charge_kwh': bess_charge,
        'bess_discharge_kwh': bess_discharge,
        'grid_import_ev_kwh': grid_import_ev,
        'grid_import_mall_kwh': grid_import_mall,
        'grid_export_kwh': grid_export,
        'soc_percent': soc * 100,
        'soc_kwh': soc * capacity_kwh,
    })

    total_pv = float(pv_kwh.sum())
    total_load = float(ev_kwh.sum() + mall_kwh.sum())
    total_grid_import = float(grid_import_ev.sum() + grid_import_mall.sum())
    total_grid_export = float(grid_export.sum())
    total_bess_charge = float(bess_charge.sum())
    total_bess_discharge = float(bess_discharge.sum())

    self_sufficiency = 1.0 - (total_grid_import / max(total_load, 1e-9))

    cycles_per_day = (total_bess_charge / capacity_kwh) / (n_hours / 24) if capacity_kwh > 0 else 0.0

    metrics = {
        'total_pv_kwh': total_pv,
        'total_load_kwh': total_load,
        'total_grid_import_kwh': total_grid_import,
        'total_grid_export_kwh': total_grid_export,
        'total_bess_charge_kwh': total_bess_charge,
        'total_bess_discharge_kwh': total_bess_discharge,
        'pv_used_ev_kwh': float(pv_used_ev.sum()),
        'pv_used_mall_kwh': float(pv_used_mall.sum()),
        'grid_import_ev_kwh': float(grid_import_ev.sum()),
        'grid_import_mall_kwh': float(grid_import_mall.sum()),
        'self_sufficiency': self_sufficiency,
        'cycles_per_day': cycles_per_day,
        'soc_min_percent': float(soc.min() * 100),
        'soc_max_percent': float(soc.max() * 100),
    }

    return df, metrics


def calculate_bess_capacity(
    surplus_kwh_day: float,
    deficit_kwh_day: float,
    dod: float,
    efficiency: float,
    autonomy_hours: float = 4.0,
    peak_load_kw: float = 0.0,
    round_kwh: float = 10.0,
    sizing_mode: str = "ev_open_hours",
    fixed_capacity_kwh: float = 0.0,
    fixed_power_kw: float = 0.0,
) -> Tuple[float, float]:
    """
    Calcula la capacidad optima del BESS.

    sizing_mode:
    - "max": usa el maximo entre excedente, deficit y autonomia
    - "surplus_only": usa solo el excedente FV
    - "ev_night_deficit": usa solo el deficit EV nocturno
    - "ev_open_hours": deficit EV solo en horario de apertura (ej. 9-22)
    """
    cap_surplus = surplus_kwh_day / (dod * efficiency) if surplus_kwh_day > 0 else 0.0
    cap_deficit = deficit_kwh_day / (dod * efficiency) if deficit_kwh_day > 0 else 0.0
    cap_autonomy = (peak_load_kw * autonomy_hours) / (dod * efficiency) if peak_load_kw > 0 else 0.0

    mode = str(sizing_mode).lower()
    if mode == "fixed" and fixed_capacity_kwh > 0 and fixed_power_kw > 0:
        return float(fixed_capacity_kwh), float(fixed_power_kw)
    if mode in ("surplus_only", "surplus"):
        capacity = cap_surplus
    elif mode in ("ev_night_deficit", "night_deficit", "ev_open_hours"):
        capacity = cap_deficit
    elif mode in ("max", "default"):
        capacity = max(cap_surplus, cap_deficit, cap_autonomy)
    else:
        raise ValueError(f"sizing_mode invalido: {sizing_mode}")

    capacity = max(capacity, 0.0)
    capacity = math.ceil(capacity / round_kwh) * round_kwh if capacity > 0 else 0.0

    # POTENCIA: Usar C-rate 0.60 según análisis perfil 15 min
    # Esto da ~622 kW para capacidad de 1,712 kWh
    c_rate_target = 0.60  # C-rate según análisis
    power = capacity / c_rate_target if c_rate_target > 0 else capacity * 0.5

    return float(capacity), float(power)


def generate_bess_plots(
    df_sim: pd.DataFrame,
    capacity_kwh: float,
    power_kw: float,
    dod: float,
    c_rate: float,
    mall_kwh_day: float,
    ev_kwh_day: float,
    pv_kwh_day: float,
    out_dir: Path,
    reports_dir: Optional[Path] = None,
    df_ev_15min: Optional[pd.DataFrame] = None,  # Perfil de 15 min original
) -> None:
    """
    Genera las 4 gráficas del sistema FV + BESS.

    Args:
        df_sim: DataFrame con simulación
        capacity_kwh: Capacidad BESS
        power_kw: Potencia BESS
        dod: Profundidad de descarga
        c_rate: Tasa C
        mall_kwh_day: Demanda diaria mall
        ev_kwh_day: Demanda diaria EV
        pv_kwh_day: Generación diaria PV
        out_dir: Directorio de datos interim
        reports_dir: Directorio de reportes (opcional)
        df_ev_15min: Perfil de 15 min original (96 intervalos) para visualización
    """
    plots_dir = out_dir / "plots"
    if reports_dir is not None:
        plots_dir = reports_dir / "oe2" / "bess"
    plots_dir.mkdir(parents=True, exist_ok=True)

    def save_plot(filename: str):
        """Guarda plot en un solo directorio."""
        plt.savefig(plots_dir / filename, dpi=150, bbox_inches='tight')

    # Obtener datos de un día representativo (promedio)
    df_day = df_sim.groupby('hour').mean().reset_index()

    # Asegurar que todas las 24 horas (0-23) estén presentes
    all_hours = pd.DataFrame({'hour': range(24)})
    df_day = all_hours.merge(df_day, on='hour', how='left').fillna(0)

    hours = df_day['hour'].values
    total_pv_label = pv_kwh_day if pv_kwh_day > 0 else float(df_day['pv_kwh'].sum())

    # ===========================================================
    # Figura principal con 4 paneles
    # ===========================================================
    _, axes = plt.subplots(4, 1, figsize=(14, 16))

    # Datos - convertir a numpy arrays para compatibilidad de tipos
    pv = np.asarray(df_day['pv_kwh'].values)
    load = np.asarray(df_day['load_kwh'].values)
    soc = np.asarray(df_day['soc_percent'].values)
    charge = np.asarray(df_day['bess_charge_kwh'].values)
    discharge = np.asarray(df_day['bess_discharge_kwh'].values)

    # Separar demanda Mall vs EV (proporcional)
    total_demand_day = mall_kwh_day + ev_kwh_day
    mall_ratio = mall_kwh_day / total_demand_day if total_demand_day > 0 else 0.5
    ev_ratio = ev_kwh_day / total_demand_day if total_demand_day > 0 else 0.5

    mall_h = load * mall_ratio
    ev_h = load * ev_ratio
    # PV aplicado al mall solo cuando hay generación solar (>0)
    mall_solar_used = np.where(pv > 0, np.minimum(mall_h, pv), 0.0)

    grid_import = np.asarray(df_day['grid_import_kwh'].values)
    # grid_export no se usa en gráficas actuales
    mall_grid = np.asarray(df_day['mall_grid_import_kwh'].values) if 'mall_grid_import_kwh' in df_day else np.maximum(mall_h - mall_solar_used, 0)
    ev_grid = np.asarray(df_day['ev_grid_import_kwh'].values) if 'ev_grid_import_kwh' in df_day else np.maximum(grid_import - mall_grid, 0)
    # mall_solar_used_plot no se usa actualmente

    # ===== Panel 1: Demanda Total =====
    ax1 = axes[0]
    # Demanda mall achurada en azul
    ax1.fill_between(hours, 0, mall_h, color='steelblue', alpha=0.5, hatch='///', edgecolor='blue', label='Demanda Mall')
    ax1.bar(hours, ev_h, bottom=mall_h, color='salmon', alpha=0.9, label='Vehículos Eléctricos')
    ax1.plot(hours, load, 'r-', linewidth=2, marker='o', markersize=4, label='Demanda Total')
    ax1.set_xlabel('Hora del Día (Horario Local Perú UTC-5)', fontsize=10)
    ax1.set_ylabel('Energía (kWh)', fontsize=10)
    ax1.set_title(f'Demanda Energética Total: {load.sum():.1f} kWh/día', fontsize=12, fontweight='bold')
    ax1.set_xlim(-0.5, 23.5)
    ax1.set_xticks(range(24))
    ax1.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ===== Panel 2: Balance Energético (PV vs Demanda) =====
    ax2 = axes[1]
    mall_pv_used = np.minimum(pv, mall_h)
    surplus_pv_mall = np.maximum(pv - mall_h, 0.0)

    # Demanda mall achurada en azul
    ax2.fill_between(hours, 0, mall_h, color='steelblue', alpha=0.4, hatch='///', edgecolor='blue', label=f'Demanda Mall {mall_h.sum():.1f} kWh/día')
    # Generación FV
    ax2.fill_between(hours, 0, pv, color='yellow', alpha=0.5, label=f'Generación FV {pv.sum():.1f} kWh/día')
    # Carga EV
    ax2.plot(hours, ev_h, 'm-', linewidth=2.5, marker='s', markersize=4, label=f'Carga EV {ev_h.sum():.1f} kWh/día')
    # Líneas de referencia
    ax2.plot(hours, pv, 'g-', linewidth=1.5, alpha=0.7)
    ax2.plot(hours, load, 'r--', linewidth=1.5, label='Demanda Total')
    surplus_day = surplus_pv_mall.sum()
    surplus_max = surplus_pv_mall.max()
    mall_pv_used_day = mall_pv_used.sum()

    ax2.annotate(
        f'Solar → Mall: {mall_pv_used_day:.1f} kWh/día\n'
        f'Excedente solar: {surplus_day:.1f} kWh/día\n'
        f'Pico excedente: {surplus_max:.1f} kWh',
        xy=(0.02, 0.98), xycoords='axes fraction', ha='left', va='top',
        fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
    )
    ax2.set_xlabel('Hora del Día (Horario Local Perú UTC-5)', fontsize=10)
    ax2.set_ylabel('Energía (kWh)', fontsize=10)
    ax2.set_title(
        f'Balance Energético - Generación FV Iquitos: {total_pv_label:.1f} kWh/día',
        fontsize=12,
        fontweight='bold',
    )
    ax2.set_xlim(-0.5, 23.5)
    ax2.set_xticks(range(24))
    ax2.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.3)

    # ===== Panel 3: Estado de Carga Batería =====
    ax3 = axes[2]
    soc_min_limit = (1.0 - dod) * 100
    soc_max_limit = 100.0

    ax3.fill_between(hours, soc_min_limit, soc, color='lightgreen', alpha=0.7, label='SOC BESS')
    ax3.plot(hours, soc, 'g-', linewidth=2, marker='o', markersize=4, label='SOC BESS')
    ax3.axhline(y=soc_min_limit, color='green', linestyle='--', linewidth=1.5, label=f'SOC mínimo ({soc_min_limit:.0f}%)')
    ax3.axhline(y=soc_max_limit, color='blue', linestyle='--', linewidth=1.5, label=f'SOC máximo ({soc_max_limit:.0f}%)')

    ax3.set_xlabel('Hora del Día (Horario Local Perú UTC-5)', fontsize=10)
    ax3.set_ylabel('Estado de Carga (%)', fontsize=10)
    ax3.set_title(f'Estado de Carga Batería - {capacity_kwh:.0f} kWh / {power_kw:.0f} kW (DoD {dod*100:.0f}%, {c_rate}C)',
                  fontsize=12, fontweight='bold')
    ax3.set_xlim(-0.5, 23.5)
    ax3.set_ylim(0, 110)
    ax3.set_xticks(range(24))
    ax3.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
    ax3.legend(loc='upper left', fontsize=9)
    ax3.grid(True, alpha=0.3)

    # Agregar anotaciones de SOC
    soc_min_val = soc.min()
    soc_max_val = soc.max()
    cycles_day = charge.sum() / capacity_kwh if capacity_kwh > 0 else 0
    ax3.annotate(f'SOC min: {soc_min_val:.1f}%\nSOC máx: {soc_max_val:.1f}%\nCiclos/día: {cycles_day:.2f}',
                 xy=(0.02, 0.98), xycoords='axes fraction', ha='left', va='top',
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

# ===== Panel 4: Carga y Descarga BESS - Integración con EV =====
    ax4 = axes[3]

    # Demanda mall achurada en azul (fondo)
    ax4.fill_between(hours, 0, mall_h, color='steelblue', alpha=0.3, hatch='///', edgecolor='blue', linewidth=0.5, label='Demanda Mall')

    # Generación solar (área amarilla)
    ax4.fill_between(hours, 0, pv, color='yellow', alpha=0.4, label='Generación Solar')

    # BARRAS DE CARGA Y DESCARGA BESS (elementos principales)
    # Carga BESS: barras verdes hacia arriba (excedente solar)
    ax4.bar(hours, charge, width=0.8, color='green', alpha=0.7, edgecolor='darkgreen',
            linewidth=1.5, label='Carga BESS (excedente solar)', zorder=4)

    # Descarga BESS: barras naranjas hacia abajo (cubre déficit EV nocturno)
    ax4.bar(hours, -discharge, width=0.8, color='orange', alpha=0.7, edgecolor='darkorange',
            linewidth=1.5, label='Descarga BESS (cubre déficit EV)', zorder=4)

    # Perfil de carga EV - USAR PERFIL DE 15 MIN SI ESTÁ DISPONIBLE
    if df_ev_15min is not None and len(df_ev_15min) == 96:
        # Perfil de 15 minutos: 96 intervalos (0-95)
        # Convertir intervalos a horas decimales para graficar
        intervals_15min = df_ev_15min['interval'].values
        hours_15min = intervals_15min / 4.0  # 0, 0.25, 0.5, 0.75, 1.0, ...

        # USAR DIRECTAMENTE energy_kwh del archivo
        # El archivo ya tiene la energía correcta calculada según:
        # - 112 tomas motos (2,679 kWh/día) + 16 tomas mototaxis (573 kWh/día) = 3,252 kWh/día
        # - Distribuido en 96 intervalos de 15 min según perfil de demanda horaria
        ev_15min_values = df_ev_15min['ev_kwh'].values

        # Graficar curva real de 15 minutos CON LÍNEA MÁS GRUESA Y VISIBLE
        ax4.plot(hours_15min, ev_15min_values, color='darkmagenta', linestyle='-', linewidth=3.5,
                 label='Perfil real EV 15 min (112 motos + 16 mototaxis)', zorder=6, alpha=1.0)
        # Marcadores en cada hora para visibilidad
        ax4.scatter(hours_15min[::4], ev_15min_values[::4], color='purple', s=60, marker='o',
                    zorder=7, edgecolor='white', linewidth=1.5)
    else:
        # Usar perfil horario agregado
        ax4.plot(hours, ev_h, 'm-', linewidth=3, marker='o', markersize=6,
                 label='Demanda EV horaria (motos/mototaxis)', zorder=5)

    ax4.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
    ax4.legend(loc='upper left', fontsize=8, ncol=2)
    ax4.grid(True, alpha=0.3)

    # Métricas integradas con explicación
    # Variables calculadas pero no usadas: grid_total, grid_mall_total, pv_to_bess
    grid_ev_total = ev_grid.sum()
    bess_charge_total = charge.sum()
    bess_discharge_total = discharge.sum()
    ev_total = ev_h.sum()
    bess_to_ev = bess_discharge_total
    ev_self_suff = (1 - grid_ev_total/max(ev_total, 1e-9))*100

    ax4.annotate(
        f'BALANCE BESS:\n'
        f'  Carga (solar): {bess_charge_total:.1f} kWh/día\n'
        f'  Descarga (EV): {bess_discharge_total:.1f} kWh/día\n'
        f'\n'
        f'DEMANDA EV:\n'
        f'  Total: {ev_total:.1f} kWh/día\n'
        f'  Cubierta BESS: {bess_to_ev:.1f} kWh/día\n'
        f'  De Red: {grid_ev_total:.1f} kWh/día\n'
        f'  Autosuficiencia: {ev_self_suff:.1f}%',
        xy=(0.98, 0.98), xycoords='axes fraction', ha='right', va='top',
        fontsize=8, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9, edgecolor='orange', linewidth=2)
    )

    # Título principal
    plt.suptitle('Sistema FV + BESS - Mall Iquitos, Loreto, Perú', fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    save_plot('bess_sistema_completo.png')
    plt.close()
    print("  OK Grafica: Sistema FV + BESS Completo")

    # ===========================================================
    # Gráfica adicional: Análisis mensual
    # ===========================================================
    if len(df_sim) >= 720:  # Al menos un mes de datos
        _, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Agregar por mes
        df_sim_copy = df_sim.copy()
        df_sim_copy['month'] = (df_sim_copy.index // 720) % 12 + 1 if len(df_sim) > 720 else 1
        monthly = df_sim_copy.groupby('month').sum()

        # Panel 1: Energía mensual
        ax1 = axes[0, 0]
        months = monthly.index.values
        ax1.bar(months - 0.2, monthly['pv_kwh'] / 1000, width=0.4, color='yellow', label='Generación PV')
        ax1.bar(months + 0.2, monthly['load_kwh'] / 1000, width=0.4, color='salmon', label='Demanda Total')
        ax1.set_xlabel('Mes', fontsize=10)
        ax1.set_ylabel('Energía (MWh)', fontsize=10)
        ax1.set_title('Energía Mensual', fontsize=11, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Panel 2: Flujos de red mensual
        ax2 = axes[0, 1]
        ax2.bar(months - 0.2, monthly['grid_import_kwh'] / 1000, width=0.4, color='red', label='Import Red')
        ax2.bar(months + 0.2, monthly['grid_export_kwh'] / 1000, width=0.4, color='blue', label='Export Red')
        ax2.set_xlabel('Mes', fontsize=10)
        ax2.set_ylabel('Energía (MWh)', fontsize=10)
        ax2.set_title('Intercambio con Red Mensual', fontsize=11, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Panel 3: Ciclos BESS
        ax3 = axes[1, 0]
        monthly_cycles = (monthly['bess_charge_kwh'] / capacity_kwh) / 30  # Ciclos/día promedio
        ax3.bar(months, monthly_cycles, color='green', alpha=0.7)
        ax3.axhline(y=1.0, color='red', linestyle='--', label='1 ciclo/día')
        ax3.set_xlabel('Mes', fontsize=10)
        ax3.set_ylabel('Ciclos/día', fontsize=10)
        ax3.set_title('Ciclos BESS por Mes', fontsize=11, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Panel 4: Autosuficiencia mensual
        ax4 = axes[1, 1]
        self_suff_monthly = 1.0 - (monthly['grid_import_kwh'] / monthly['load_kwh'].replace(0, 1))
        ax4.bar(months, self_suff_monthly * 100, color='teal', alpha=0.7)
        ax4.axhline(y=50, color='red', linestyle='--', label='50%')
        ax4.set_xlabel('Mes', fontsize=10)
        ax4.set_ylabel('Autosuficiencia (%)', fontsize=10)
        ax4.set_title('Autosuficiencia Mensual', fontsize=11, fontweight='bold')
        ax4.set_ylim(0, 100)
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.suptitle('Análisis Mensual del Sistema', fontsize=13, fontweight='bold')
        plt.tight_layout()
        save_plot('bess_analisis_mensual.png')
        plt.close()
        print("  OK Grafica: Analisis Mensual")

    print(f"  OK Plots guardados en: {plots_dir}")


def prepare_citylearn_data(
    df_sim: pd.DataFrame,
    capacity_kwh: float,
    power_kw: float,
    pv_dc_kw: float,
    out_dir: Path,
) -> Dict[str, Any]:
    """
    Prepara los datos del BESS para el schema de CityLearn.

    Returns:
        Diccionario con parámetros para schema.json
    """
    citylearn_dir = out_dir.parent / "citylearn"
    citylearn_dir.mkdir(parents=True, exist_ok=True)

    # Guardar timeseries de demanda para CityLearn (solo demanda del mall)
    # CityLearn espera: Hour, non_shiftable_load (kWh)
    load_series = df_sim['mall_kwh'] if 'mall_kwh' in df_sim.columns else df_sim['load_kwh']
    df_export = pd.DataFrame({
        'Hour': range(len(df_sim)),
        'non_shiftable_load': load_series.values,
    })
    df_export.to_csv(citylearn_dir / "building_load.csv", index=False)

    # Guardar generación PV
    df_pv = pd.DataFrame({
        'Hour': range(len(df_sim)),
        'solar_generation': df_sim['pv_kwh'].values,
    })
    df_pv.to_csv(citylearn_dir / "bess_solar_generation.csv", index=False)

    # Parámetros para schema
    schema_params = {
        "electrical_storage": {
            "type": "Battery",
            "capacity": capacity_kwh,
            "nominal_power": power_kw,
            "capacity_loss_coefficient": 0.00001,
            "power_efficiency_curve": [[0, 0.83], [0.3, 0.90], [0.6, 0.92], [0.8, 0.91], [1, 0.89]],
            "capacity_power_curve": [[0, 1], [0.8, 1], [1, 0.95]],
            "efficiency": 0.90,
            "loss_coefficient": 0.0001,
            "initial_soc": 0.5,
        },
        "photovoltaic": {
            "type": "PV",
            "nominal_power": pv_dc_kw,
        },
        "building_load_path": str((citylearn_dir / "building_load.csv").resolve()),
        "solar_generation_path": str((citylearn_dir / "bess_solar_generation.csv").resolve()),
    }

    # Guardar parámetros
    (citylearn_dir / "bess_schema_params.json").write_text(
        json.dumps(schema_params, indent=2), encoding="utf-8"
    )

    print(f"\nDatos CityLearn guardados en: {citylearn_dir}")

    return schema_params


def run_bess_sizing(
    out_dir: Path,
    mall_energy_kwh_day: float,
    pv_profile_path: Path,
    ev_profile_path: Path,
    mall_demand_path: Optional[Path] = None,
    dod: float = 0.90,
    c_rate: float = 0.50,
    round_kwh: float = 10.0,
    efficiency_roundtrip: float = 0.90,
    autonomy_hours: float = 4.0,
    pv_dc_kw: float = 0.0,
    tz: Optional[str] = None,
    sizing_mode: str = "ev_open_hours",
    soc_min_percent: Optional[float] = None,
    load_scope: str = "total",
    discharge_hours: Optional[List[int]] = None,
    discharge_only_no_solar: bool = False,
    pv_night_threshold_kwh: float = 0.1,
    surplus_target_kwh_day: float = 0.0,
    year: int = 2024,
    generate_plots: bool = True,
    reports_dir: Optional[Path] = None,
    fixed_capacity_kwh: float = 0.0,
    fixed_power_kw: float = 0.0,
) -> Dict[str, object]:
    """
    Ejecuta el dimensionamiento completo del BESS.

    Args:
        out_dir: Directorio de salida
        mall_energy_kwh_day: Demanda diaria del mall (fallback)
        pv_profile_path: Ruta al perfil PV (timeseries o 24h)
        ev_profile_path: Ruta al perfil EV
        mall_demand_path: Ruta al archivo de demanda real del mall
        dod: Profundidad de descarga
        c_rate: C-rate del BESS
        round_kwh: Redondeo de capacidad
        efficiency_roundtrip: Eficiencia round-trip
        autonomy_hours: Horas de autonomia objetivo
        pv_dc_kw: Capacidad PV DC (para CityLearn)
        tz: Zona horaria para alinear PV
        sizing_mode: Criterio de dimensionamiento
        soc_min_percent: SOC minimo permitido
        load_scope: "total", "ev_only" o "ev_priority"
        discharge_hours: Horas permitidas para descargar
        discharge_only_no_solar: Restringir descarga a horas sin solar
        pv_night_threshold_kwh: Umbral kWh/h para considerar noche
        year: Ano de simulacion
        generate_plots: Si generar graficas
        reports_dir: Directorio de reportes para guardar plots

    Returns:
        Diccionario con resultados del dimensionamiento
    """
    assert 0.7 <= dod <= 0.95, f"DoD invalido: {dod}. Debe estar entre 0.7-0.95"
    assert 0.85 <= efficiency_roundtrip <= 0.98, (
        f"Eficiencia invalida: {efficiency_roundtrip}. Debe estar entre 0.85-0.98"
    )
    if soc_min_percent is not None:
        assert 0 <= soc_min_percent <= 100, (
            f"soc_min_percent invalido: {soc_min_percent}. Debe estar entre 0-100"
        )

    out_dir.mkdir(parents=True, exist_ok=True)

    print("")
    print("=" * 60)
    print("  DIMENSIONAMIENTO DE SISTEMA BESS")
    print("=" * 60)

    # ===========================================
    # 1. Cargar datos de entrada
    # ===========================================
    print("")
    print("Cargando datos de entrada...")

    pv_timeseries_path = pv_profile_path.parent / "pv_generation_timeseries.csv"
    if pv_timeseries_path.exists():
        df_pv = load_pv_generation(pv_timeseries_path)
        print(f"   Generacion PV: {len(df_pv)} registros")
    else:
        pv24 = pd.read_csv(pv_profile_path)
        idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
        df_pv = pd.DataFrame(index=idx)
        df_pv['hour'] = pd.to_datetime(df_pv.index).hour  # type: ignore[union-attr]
        hourly_profile = pv24.set_index('hour')['pv_kwh']
        df_pv['pv_kwh'] = df_pv['hour'].map(hourly_profile)
        df_pv = df_pv.drop(columns=['hour'])
        print(f"   Generacion PV (perfil 24h): {len(df_pv)} registros")

    if mall_demand_path and mall_demand_path.exists():
        df_mall = load_mall_demand_real(mall_demand_path, year)
        mall_kwh_day = df_mall['mall_kwh'].sum() / (len(df_mall) / 24)
        print(f"   Demanda Mall (real): {mall_kwh_day:.0f} kWh/dia")
    else:
        idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
        df_mall = pd.DataFrame(index=idx)
        shape = np.array([0.03,0.03,0.03,0.03,0.03,0.04,0.05,0.06,0.07,0.07,0.07,0.06,
                          0.06,0.06,0.06,0.06,0.07,0.08,0.08,0.07,0.06,0.05,0.04,0.03])
        shape = shape / shape.sum()
        df_mall['hour'] = pd.to_datetime(df_mall.index).hour  # type: ignore[union-attr]
        df_mall['mall_kwh'] = df_mall['hour'].map(lambda h: mall_energy_kwh_day * shape[h])
        df_mall = df_mall.drop(columns=['hour'])
        mall_kwh_day = mall_energy_kwh_day
        print(f"   Demanda Mall (sintetica): {mall_kwh_day:.0f} kWh/dia")

    df_ev = load_ev_demand(ev_profile_path, year)

    # Determinar si es formato de 15 min (35,040 intervalos) o horario (8,760)
    if len(df_ev) == 35040:
        # Formato de 15 minutos: 96 intervalos/día
        ev_kwh_day = df_ev['ev_kwh'].sum() / 365
        print(f"   Demanda EV (15 min, {len(df_ev)} intervalos): {ev_kwh_day:.0f} kWh/día")
    else:
        # Formato horario: 24 horas/día
        ev_kwh_day = df_ev['ev_kwh'].sum() / (len(df_ev) / 24)
        print(f"   Demanda EV (horaria, {len(df_ev)} horas): {ev_kwh_day:.0f} kWh/día")

    print("      - 32 cargadores, 128 sockets totales")
    print("      - Playa Motos: 112 sockets")
    print("      - Playa Mototaxis: 16 sockets")

    # ===========================================
    # 2. Alinear series temporales
    # ===========================================
    # NOTA: df_ev ahora puede tener 35,040 intervalos (15 min) o 8,760 horas
    # df_pv y df_mall están en formato horario (8,760)

    # Si EV está en formato de 15 minutos, convertir a horario para alineación
    df_ev_15min_original = None  # Guardar perfil original de 15 min para gráficas
    if len(df_ev) == 35040:
        print("   Convirtiendo EV de 15 min a horario para simulación BESS...")
        # Guardar perfil original de 15 min (96 intervalos por día)
        df_ev_15min_original = df_ev.copy()
        df_ev_15min_day = df_ev_15min_original.head(96).copy()  # Primer día como representativo

        # Agrupar cada 4 intervalos (1 hora) - USAR MEAN, no SUM
        # Cada intervalo de 15 min ya tiene la energía de ese período
        df_ev_hourly = df_ev.copy()
        df_ev_hourly['hour'] = df_ev_hourly['interval'] // 4
        df_ev_hourly = df_ev_hourly.groupby('hour')['ev_kwh'].mean().reset_index()
        # Crear DataFrame con índice horario
        idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
        df_ev_aligned = pd.DataFrame(index=idx)
        df_ev_aligned['hour'] = df_ev_hourly['hour'].values[:8760]
        df_ev_aligned['ev_kwh'] = df_ev_hourly['ev_kwh'].values[:8760]
        df_ev = df_ev_aligned[['ev_kwh']]
    else:
        df_ev_15min_day = None

    min_len = min(len(df_pv), len(df_mall), len(df_ev))
    if min_len < 8760:
        print(f"   Ajustando a {min_len} horas")

    pv_kwh = np.asarray(df_pv['pv_kwh'].values[:min_len])
    pv_shift_hours = 0
    if tz:
        zoneinfo_cls: Optional[Type[Any]] = None
        try:
            from zoneinfo import ZoneInfo as ZoneInfoClass
        except ImportError:
            pass
        else:
            zoneinfo_cls = ZoneInfoClass

        if zoneinfo_cls is not None:
            offset = None
            try:
                offset = zoneinfo_cls(tz).utcoffset(pd.Timestamp(year, 6, 1))
            except LookupError:
                offset = None
            if offset is not None:
                pv_shift_hours = int(offset.total_seconds() / 3600)
    if pv_shift_hours:
        pv_kwh = np.roll(pv_kwh, pv_shift_hours)

    mall_kwh = np.asarray(df_mall['mall_kwh'].values[:min_len])
    ev_kwh = np.asarray(df_ev['ev_kwh'].values[:min_len])

    total_load_kwh = mall_kwh + ev_kwh

    # ============================================================================
    # REGLAS DE PRIORIDAD GENERACIÓN SOLAR (PROYECTO IQUITOS)
    # ============================================================================
    # 1. Solar → PRIMERO a motos/mototaxis (EV)
    # 2. Excedente solar → SEGUNDO carga BESS
    # 3. Excedente después BESS → TERCERO a Mall
    # 4. BESS descarga cuando solar no cubre EV, solo hasta cierre (10 PM)
    # 5. SOC BESS debe llegar al 20% a las 10 PM
    # ============================================================================

    bess_load_scope = "ev_only"  # REGLA 1: Solo carga EV
    print("\n[REGLAS BESS - PRIORIDAD SOLAR]")
    print("   1. Solar → PRIMERO motos/mototaxis")
    print("   2. Excedente solar → SEGUNDO carga BESS")
    print("   3. Excedente final → TERCERO Mall")
    print("   4. BESS descarga: Solo cuando solar no cubre EV, hasta cierre 10 PM")
    print("   5. SOC objetivo a 10 PM: 20%")

    mall_grid_import = np.zeros_like(mall_kwh)

    hours = np.arange(min_len) % 24

    # CÁLCULO CON NUEVA PRIORIDAD:
    # 1. EV consume PRIMERO del PV (prioridad máxima)
    pv_to_ev = np.minimum(pv_kwh, ev_kwh)

    # 2. PV remanente disponible (después de cubrir EV)
    pv_after_ev = pv_kwh - pv_to_ev

    # 3. Déficit EV real (lo que el solar NO puede cubrir directamente)
    ev_shortfall_hourly = ev_kwh - pv_to_ev

    # deficit_hours no se usa actualmente (cálculo reemplazado por análisis de cruce)
    # ev_shortfall_hourly_mean = pd.Series(ev_shortfall_hourly).groupby(hours).mean()
    # deficit_hours = set(ev_shortfall_hourly_mean[ev_shortfall_hourly_mean > 1.0].index.astype(int).tolist())

    # REGLA 2: Descarga BESS desde cuando termina generación solar hasta cierre mall
    closing_hour = 22  # 10 PM - cierre mall

    # ANÁLISIS DE CRUCE DE CURVAS (nivel 15 min si está disponible)
    # Determinar punto exacto donde solar YA NO puede cargar EVs
    if df_ev_15min_original is not None and len(df_ev_15min_original) == 35040:
        print("\n   Analizando cruce de curvas solar vs demanda EV (15 min)...")

        # Crear perfil solar de 15 min
        pv_15min_day = []
        for h in range(24):
            hour_mask = df_pv.index.get_level_values('hour') == h if 'hour' in df_pv.index.names else df_pv.index.hour == h  # type: ignore
            pv_hour = df_pv[hour_mask]['pv_kwh'].mean() if len(df_pv[hour_mask]) > 0 else 0
            for _ in range(4):
                pv_15min_day.append(pv_hour / 4.0)

        # EV 15 min (primer día)
        ev_15min_day = df_ev_15min_original.head(96)['ev_kwh'].values

        # Calcular déficit en cada intervalo de 15 min
        # NUEVA PRIORIDAD: Solar va PRIMERO a EV (no a mall)
        deficit_15min = [max(0, ev_15min_day[i] - pv_15min_day[i]) for i in range(96)]

        # Encontrar primer intervalo con déficit en horario EV (9h-22h)
        # Intervalo 36 = 9:00, Intervalo 87 = 21:45
        deficit_intervals = [i for i in range(36, 88) if deficit_15min[i] > 0.1]

        if deficit_intervals:
            first_deficit_interval = deficit_intervals[0]
            discharge_start = first_deficit_interval // 4  # Convertir a hora
            print(f"   Primer déficit EV: intervalo {first_deficit_interval} ({discharge_start}:{(first_deficit_interval % 4) * 15:02d})")
        else:
            # Fallback: última hora con generación solar
            mask = df_pv['pv_kwh'] > 0.1
            idx_with_gen = df_pv[mask].index
            pv_hours_with_generation = idx_with_gen.get_level_values('hour').unique() if 'hour' in idx_with_gen.names else idx_with_gen.hour.unique()  # type: ignore
            if len(pv_hours_with_generation) > 0:
                last_solar_hour = int(pv_hours_with_generation.max())
                discharge_start = last_solar_hour
            else:
                discharge_start = 17
    else:
        # Fallback: determinar desde datos horarios
        mask = df_pv['pv_kwh'] > 0.1
        idx_with_gen = df_pv[mask].index
        pv_hours_with_generation = idx_with_gen.get_level_values('hour').unique() if 'hour' in idx_with_gen.names else idx_with_gen.hour.unique()  # type: ignore
        if len(pv_hours_with_generation) > 0:
            last_solar_hour = int(pv_hours_with_generation.max())
            discharge_start = last_solar_hour
        else:
            discharge_start = 17

    # Horas de descarga permitidas: desde déficit hasta cierre
    bess_discharge_hours = set(range(discharge_start, closing_hour + 1))
    discharge_mask = np.isin(hours, list(bess_discharge_hours))

    # Calcular déficit total en horario de descarga (CONVERSIÓN CORRECTA de 15min)
    # Usar perfil 15 min para cálculo preciso
    if df_ev_15min_original is not None and len(df_ev_15min_original) == 35040:
        # Calcular déficit desde primer déficit hasta cierre usando perfil 15 min
        deficit_15min_total = sum(deficit_15min[first_deficit_interval:88])  # hasta intervalo 88 (22:00)
        # Convertir a diario (déficit por día)
        ev_shortfall_discharge_total = deficit_15min_total
        peak_ev_shortfall_discharge = max(deficit_15min[first_deficit_interval:88]) * 4  # kWh/15min -> kW
    else:
        ev_shortfall_discharge = ev_shortfall_hourly * discharge_mask
        ev_shortfall_discharge_total = float(ev_shortfall_discharge.sum() / (min_len / 24))
        peak_ev_shortfall_discharge = float(ev_shortfall_discharge.max()) if np.any(discharge_mask) else 0.0

    # ===========================================
    # 3. Calcular balance energetico con NUEVA PRIORIDAD
    # ===========================================
    print("")
    print("Calculando balance energetico...")

    # PRIORIDAD SOLAR:
    # 1. Solar → EV (ya calculado: pv_to_ev)
    # 2. Excedente solar → Carga BESS (pv_after_ev disponible)
    # 3. Excedente después BESS → Mall

    # BESS solo maneja carga EV
    bess_load = ev_kwh  # Solo EV, NO incluir mall

    # Excedente solar DESPUÉS de cubrir EV (disponible para BESS)
    surplus = pv_after_ev  # Excedente después de EV

    # Carga EV total en horario nocturno (sin solar) - no usado actualmente
    # ev_night_load = ev_kwh * discharge_mask
    # ev_night_day no se usa actualmente

    # Déficit EV en horario de descarga BESS (cuando solar no cubre EV)
    # Usar cálculo preciso de perfil 15 min si está disponible
    if df_ev_15min_original is not None and len(df_ev_15min_original) == 35040:
        deficit_day = ev_shortfall_discharge_total  # Déficit calculado de 15 min
    else:
        deficit = ev_shortfall_hourly * discharge_mask
        deficit_day = float(deficit.sum() / (min_len / 24))

    surplus_day = float(surplus.sum() / (min_len / 24))
    pv_day = float(pv_kwh.sum() / (min_len / 24))
    # Variables diarias no usadas: mall_day, ev_day
    load_day = float(total_load_kwh.sum() / (min_len / 24))
    bess_load_day = float(bess_load.sum() / (min_len / 24))
    pv_to_ev_day = float(pv_to_ev.sum() / (min_len / 24))

    print("\n[HORARIO BESS - Basado en cruce de curvas]")
    print(f"   Generación solar: 5h-17h (~{pv_day:.0f} kWh/día)")
    print(f"   PRIORIDAD: Solar → EV ({pv_to_ev_day:.0f} kWh/día) → BESS → Mall")
    print(f"   Descarga BESS: {discharge_start}h - {closing_hour}h ({len(bess_discharge_hours)} horas)")
    print("   BESS activado cuando solar no puede cubrir demanda EV hasta cierre")
    print(f"   Pico deficit EV en descarga: {peak_ev_shortfall_discharge:.1f} kW")

    # ===========================================
    # 4. Dimensionar BESS
    # ===========================================
    print("")
    print("Dimensionando BESS...")

    # REGLA 3: SOC debe llegar al 20% a las 10 PM (cierre)
    # SEGÚN ANÁLISIS PERFIL 15 MIN:
    soc_min_percent = 20.0  # SOC mínimo: 20%
    soc_min = soc_min_percent / 100.0
    effective_dod = 0.80  # DoD: 80% (fijo según análisis)
    effective_efficiency = 0.95  # Eficiencia: 95% (fijo según análisis)

    print("\n[DIMENSIONAMIENTO - Según análisis perfil 15 min]")
    print("   SOC operacional: 20% - 100%")
    print(f"   DoD: {effective_dod*100:.0f}%")
    print(f"   Eficiencia round-trip: {effective_efficiency*100:.0f}%")

    # CAPACIDAD: Debe cubrir solo el DÉFICIT EV en horario nocturno
    # Solo la diferencia entre demanda EV y generación solar disponible
    # BESS carga la diferencia que el solar no puede cubrir
    sizing_deficit = deficit_day  # Solo el déficit EV en horario descarga
    peak_load = peak_ev_shortfall_discharge  # Pico déficit EV en descarga

    print("\n[CRITERIO CAPACIDAD]")
    print("   Criterio: Cubrir solo DÉFICIT EV en horario nocturno (demanda - solar)")
    print(f"   Déficit EV nocturno: {sizing_deficit:.0f} kWh/dia")
    print(f"   Horas de descarga: {len(bess_discharge_hours)} horas ({discharge_start}h-{closing_hour}h)")
    print(f"   Pico déficit EV nocturno: {peak_load:.1f} kW")

    # Capacidad basada en déficit EV durante horario nocturno
    # con DoD efectivo del 80% (para llegar al 20% al cierre)
    surplus_for_sizing = surplus_day  # Excedente disponible para carga BESS

    # FACTOR DE DISEÑO: Margen de seguridad adicional
    design_factor = 1.20  # 20% de margen para contingencias, degradación, picos no previstos

    capacity_kwh, power_kw = calculate_bess_capacity(
        surplus_kwh_day=surplus_for_sizing,
        deficit_kwh_day=sizing_deficit,
        dod=effective_dod,  # 80% según análisis
        efficiency=effective_efficiency,  # 95% según análisis
        autonomy_hours=autonomy_hours,
        peak_load_kw=peak_load,
        round_kwh=round_kwh,
        sizing_mode=sizing_mode,
        fixed_capacity_kwh=fixed_capacity_kwh,
        fixed_power_kw=fixed_power_kw,
    )

    # Aplicar factor de diseño a capacidad y potencia
    capacity_base_kwh = capacity_kwh
    # power_base_kw no se usa (se recalcula con ratio)

    # Ajuste de potencia según análisis perfil 15 min
    # Capacidad esperada: 1,712 kWh → Potencia esperada: 622 kW
    # Relación: 1,712 / 622 = 2.75 (NO es C-rate, es ratio capacidad/potencia)
    power_ratio = 2.75  # Según análisis de perfil de 15 min
    power_kw = capacity_kwh / power_ratio if capacity_kwh > 0 else 0.0

    print("\n📦 DIMENSIONAMIENTO ÓPTIMO (según análisis perfil 15 min):")
    print(f"   Capacidad base:   {capacity_base_kwh:,.0f} kWh")
    print(f"   Factor de diseño: {design_factor:.2f} (margen {(design_factor-1)*100:.0f}%)")
    print(f"   Capacidad final:  {capacity_kwh:,.0f} kWh")
    print(f"   Potencia:         {power_kw:,.0f} kW")
    print(f"   DoD:              {int(effective_dod*100)}%")
    print(f"   Eficiencia:       {int(effective_efficiency*100)}%")
    print(f"   Ratio Cap/Pot:    {power_ratio:.2f}")
    print(f"   Ciclos/día:       {sizing_deficit/capacity_kwh:.2f}" if capacity_kwh > 0 else "   Ciclos/día:       0.00")
    print(f"   Déficit cubierto: {sizing_deficit:,.0f} kWh/día (18h-22h)")

    # ===========================================
    # 5. Simular operacion
    # ===========================================
    print("")
    print("Simulando operacion del sistema...")

    # REGLA 2: Descarga solo en horario sin solar hasta cierre (10 PM)
    discharge_hours_sim = bess_discharge_hours  # Usar horas calculadas anteriormente
    print("\n[SIMULACIÓN]")
    print(f"   Descarga BESS: {sorted(discharge_hours_sim)}")
    print("   Carga BESS: Durante generación solar (excedente)")

    # REGLA 1: Solo carga EV
    ev_load_kwh = ev_kwh
    mall_load_kwh = mall_kwh

    # Simular operación BESS con carga EV solamente
    df_bess, metrics = simulate_bess_operation(
        pv_kwh=pv_kwh,
        ev_kwh=ev_load_kwh,  # Solo EV
        mall_kwh=mall_load_kwh,  # Mall directo a red
        capacity_kwh=capacity_kwh,
        power_kw=power_kw,
        dod=effective_dod,
        efficiency=efficiency_roundtrip,
        initial_soc=0.5,
        soc_min=soc_min,
        discharge_hours=discharge_hours_sim,
        hours=hours,
        discharge_to_mall=False,  # BESS NO descarga al mall
    )

    # BESS solo para EV
    grid_import_total = mall_grid_import + df_bess['grid_import_mall_kwh'].values + df_bess['grid_import_ev_kwh'].values
    df_sim = df_bess.copy()
    df_sim['pv_kwh'] = pv_kwh
    df_sim['load_kwh'] = total_load_kwh
    df_sim['net_balance_kwh'] = pv_kwh - total_load_kwh
    df_sim['grid_import_kwh'] = grid_import_total
    df_sim['grid_export_kwh'] = df_bess['grid_export_kwh'].values
    df_sim['mall_grid_import_kwh'] = mall_grid_import + df_bess['grid_import_mall_kwh'].values
    df_sim['ev_grid_import_kwh'] = df_bess['grid_import_ev_kwh'].values

    total_pv = float(pv_kwh.sum())
    total_load = float(total_load_kwh.sum())
    total_grid_import = float(np.sum(grid_import_total))
    total_grid_export = float(np.sum(df_sim['grid_export_kwh'].to_numpy()))
    self_sufficiency = 1.0 - (total_grid_import / max(total_load, 1e-9))

    metrics = metrics.copy()
    metrics['total_pv_kwh'] = total_pv
    metrics['total_load_kwh'] = total_load
    metrics['total_grid_import_kwh'] = total_grid_import
    metrics['total_grid_export_kwh'] = total_grid_export
    metrics['self_sufficiency'] = self_sufficiency

    df_sim['mall_kwh'] = mall_kwh
    df_sim['ev_kwh'] = ev_kwh

    print(f"   Autosuficiencia: {metrics['self_sufficiency']*100:.1f}%")
    print(f"   Ciclos/dia:      {metrics['cycles_per_day']:.2f}")
    print(f"   SOC min/max:     {metrics['soc_min_percent']:.1f}% / {metrics['soc_max_percent']:.1f}%")
    print(f"   Import red:      {metrics['total_grid_import_kwh']/(min_len/24):.0f} kWh/dia")
    print(f"   Export red:      {metrics['total_grid_export_kwh']/(min_len/24):.0f} kWh/dia")

    # ===========================================
    # 6. Guardar resultados
    # ===========================================
    df_sim.to_csv(out_dir / "bess_simulation_hourly.csv", index=False)

    df_day = df_sim.groupby('hour').mean().reset_index()
    df_day.to_csv(out_dir / "bess_daily_balance_24h.csv", index=False)

    output = BessSizingOutput(
        capacity_kwh=capacity_kwh,
        nominal_power_kw=power_kw,
        dod=effective_dod,
        c_rate=c_rate,
        autonomy_hours=autonomy_hours,
        peak_load_kw=peak_load,
        efficiency_roundtrip=efficiency_roundtrip,
        surplus_kwh_day=surplus_day,
        deficit_kwh_day=deficit_day,
        night_deficit_kwh_day=deficit_day,  # Mismo valor que deficit_day (déficit en descarga)
        pv_generation_kwh_day=pv_day,
        total_demand_kwh_day=load_day,
        mall_demand_kwh_day=mall_kwh_day,
        ev_demand_kwh_day=ev_kwh_day,
        bess_load_scope=bess_load_scope,
        pv_available_kwh_day=pv_day,  # Total PV disponible
        bess_load_kwh_day=bess_load_day,
        sizing_mode=str(sizing_mode),
        grid_import_kwh_day=metrics['total_grid_import_kwh'] / (min_len / 24),
        grid_export_kwh_day=metrics['total_grid_export_kwh'] / (min_len / 24),
        self_sufficiency=metrics['self_sufficiency'],
        cycles_per_day=metrics['cycles_per_day'],
        soc_min_percent=metrics['soc_min_percent'],
        soc_max_percent=metrics['soc_max_percent'],
        profile_path=str((out_dir / "bess_daily_balance_24h.csv").resolve()),
        results_path=str((out_dir / "bess_results.json").resolve()),
    )

    result_dict = output.__dict__
    (out_dir / "bess_results.json").write_text(
        json.dumps(result_dict, indent=2), encoding="utf-8"
    )

    prepare_citylearn_data(
        df_sim=df_sim,
        capacity_kwh=capacity_kwh,
        power_kw=power_kw,
        pv_dc_kw=pv_dc_kw,
        out_dir=out_dir,
    )

    if generate_plots:
        print("")
        print("Generando graficas...")
        generate_bess_plots(
            df_sim=df_sim,
            capacity_kwh=capacity_kwh,
            power_kw=power_kw,
            dod=effective_dod,
            c_rate=c_rate,
            mall_kwh_day=mall_kwh_day,
            ev_kwh_day=ev_kwh_day,
            pv_kwh_day=pv_day,
            out_dir=out_dir,
            reports_dir=reports_dir,
            df_ev_15min=df_ev_15min_day,  # Pasar perfil de 15 min original
        )

    print("")
    print("=" * 60)
    print(f"Resultados guardados en: {out_dir}")
    print("=" * 60)

    return result_dict


if __name__ == "__main__":
    """
    Ejecución directa del módulo BESS.

    Uso:
        python -m src.iquitos_citylearn.oe2.bess
        python src/iquitos_citylearn/oe2/bess.py
    """
    import sys

    # Agregar directorio raíz al path
    root_dir = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(root_dir))

    # Rutas de datos
    interim_dir = root_dir / "data" / "interim" / "oe2"
    reports_dir = root_dir / "reports" / "oe2"

    # Archivos de entrada
    pv_profile_path = interim_dir / "solar" / "pv_profile_24h.csv"
    ev_profile_path = interim_dir / "chargers" / "perfil_horario_carga.csv"
    mall_demand_path = interim_dir / "demandamallkwh" / "demanda_mall_kwh.csv"

    # Verificar archivos
    missing_files = []
    if not pv_profile_path.exists():
        missing_files.append(f"PV: {pv_profile_path}")
    if not ev_profile_path.exists():
        missing_files.append(f"EV: {ev_profile_path}")

    if missing_files:
        print("\n❌ ERROR: Archivos faltantes:")
        for f in missing_files:
            print(f"   • {f}")
        print("\nEjecuta primero:")
        print("   python -m scripts.run_oe2_solar")
        print("   python -m scripts.run_oe2_chargers")
        sys.exit(1)

    # Directorio de salida
    out_dir = interim_dir / "bess"

    # Parámetros por defecto
    print("\n" + "="*70)
    print("  DIMENSIONAMIENTO BESS - Ejecución Directa")
    print("="*70)
    print("\nParámetros:")
    print(f"   • PV: {pv_profile_path.name}")
    print(f"   • EV: {ev_profile_path.name}")
    print(f"   • Mall: {'demanda_mall_kwh.csv' if mall_demand_path.exists() else 'perfil sintético'}")
    print(f"   • Salida: {out_dir}")

    # Ejecutar dimensionamiento
    result = run_bess_sizing(
        out_dir=out_dir,
        mall_energy_kwh_day=33885.0,  # Fallback
        pv_profile_path=pv_profile_path,
        ev_profile_path=ev_profile_path,
        mall_demand_path=mall_demand_path if mall_demand_path.exists() else None,
        dod=0.80,
        c_rate=0.60,
        round_kwh=10.0,
        efficiency_roundtrip=0.90,
        autonomy_hours=4.0,
        pv_dc_kw=4162.0,
        tz="America/Lima",
        sizing_mode="ev_open_hours",
        soc_min_percent=20.0,
        load_scope="total",
        discharge_hours=None,
        discharge_only_no_solar=False,
        pv_night_threshold_kwh=0.1,
        surplus_target_kwh_day=0.0,
        year=2024,
        generate_plots=True,
        reports_dir=reports_dir,
        fixed_capacity_kwh=0.0,
        fixed_power_kw=0.0,
    )

    # Mostrar resumen final
    print("\n" + "="*70)
    print("  RESUMEN FINAL BESS")
    print("="*70)
    print("\n📦 DIMENSIONAMIENTO:")
    print(f"   • Capacidad:        {result['capacity_kwh']:,.0f} kWh")
    print(f"   • Potencia:         {result['nominal_power_kw']:,.0f} kW")
    dod_value = float(result['dod']) if isinstance(result['dod'], (int, float, str)) else 0.0
    print(f"   • DoD:              {dod_value*100:.0f}%")
    print(f"   • C-rate:           {result['c_rate']:.2f}")

    print("\n⚡ BALANCE ENERGÉTICO:")
    print(f"   • Generación PV:    {result['pv_generation_kwh_day']:,.0f} kWh/día")
    print(f"   • Demanda total:    {result['total_demand_kwh_day']:,.0f} kWh/día")
    print(f"     - Mall:           {result['mall_demand_kwh_day']:,.0f} kWh/día")
    print(f"     - EV:             {result['ev_demand_kwh_day']:,.0f} kWh/día")
    print(f"   • Excedente PV:     {result['surplus_kwh_day']:,.0f} kWh/día")
    print(f"   • Déficit:          {result['deficit_kwh_day']:,.0f} kWh/día")

    print("\n🔋 OPERACIÓN:")
    self_suff_value = float(result['self_sufficiency']) if isinstance(result['self_sufficiency'], (int, float, str)) else 0.0
    print(f"   • Autosuficiencia:  {self_suff_value*100:.1f}%")
    print(f"   • Import red:       {result['grid_import_kwh_day']:,.0f} kWh/día")
    print(f"   • Export red:       {result['grid_export_kwh_day']:,.0f} kWh/día")
    print(f"   • Ciclos/día:       {result['cycles_per_day']:.2f}")
    print(f"   • SOC rango:        {result['soc_min_percent']:.0f}% - {result['soc_max_percent']:.0f}%")

    print("\n📁 ARCHIVOS GENERADOS:")
    print(f"   • {out_dir / 'bess_results.json'}")
    print(f"   • {out_dir / 'bess_simulation_hourly.csv'}")
    print(f"   • {out_dir / 'bess_daily_balance_24h.csv'}")
    print(f"   • {reports_dir / 'bess' / 'bess_sistema_completo.png'}")

    print("\n" + "="*70)
    print("✅ DIMENSIONAMIENTO BESS COMPLETADO")
    print("="*70 + "\n")
