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
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING
import json
import math
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    pass


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
    """Carga el perfil de demanda EV."""
    df = pd.read_csv(ev_profile_path)
    
    # Verificar columnas
    if 'hour' in df.columns and 'energy_kwh' in df.columns:
        # Perfil de 24 horas, expandir a año
        hourly_profile = df.set_index('hour')['energy_kwh']
        idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
        df_full = pd.DataFrame(index=idx)
        df_full['hour'] = pd.to_datetime(df_full.index).hour  # type: ignore[union-attr]
        df_full['ev_kwh'] = df_full['hour'].map(hourly_profile)
        df_full = df_full.drop(columns=['hour'])
        return df_full
    
    return df


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
    power = capacity * 0.5

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
    """
    import matplotlib.pyplot as plt
    
    plots_dir = out_dir / "plots"
    if reports_dir is not None:
        plots_dir = reports_dir / "oe2" / "bess"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    def save_plot(filename: str):
        """Guarda plot en un solo directorio."""
        plt.savefig(plots_dir / filename, dpi=150, bbox_inches='tight')
    
    # Obtener datos de un día representativo (promedio)
    df_day = df_sim.groupby('hour').mean().reset_index()
    hours = df_day['hour'].values
    
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
    grid_export = np.asarray(df_day['grid_export_kwh'].values)
    mall_grid = np.asarray(df_day['mall_grid_import_kwh'].values) if 'mall_grid_import_kwh' in df_day else np.maximum(mall_h - mall_solar_used, 0)
    ev_grid = np.asarray(df_day['ev_grid_import_kwh'].values) if 'ev_grid_import_kwh' in df_day else np.maximum(grid_import - mall_grid, 0)
    mall_solar_used_plot = np.asarray(df_day['mall_pv_used_kwh'].values) if 'mall_pv_used_kwh' in df_day else mall_solar_used
    
    # ===== Panel 1: Demanda Total =====
    ax1 = axes[0]
    ax1.bar(hours, mall_h, color='steelblue', label='Mall', alpha=0.9)
    ax1.bar(hours, ev_h, bottom=mall_h, color='salmon', label='Vehículos Eléctricos', alpha=0.9)
    ax1.plot(hours, load, 'r-', linewidth=2, marker='o', markersize=4, label='Demanda Total')
    ax1.set_xlabel('Hora del Día', fontsize=10)
    ax1.set_ylabel('Energía (kWh)', fontsize=10)
    ax1.set_title(f'Demanda Energética Total: {load.sum():.1f} kWh/día', fontsize=12, fontweight='bold')
    ax1.set_xlim(-0.5, 23.5)
    ax1.set_xticks(range(24))
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # ===== Panel 2: Balance Energético (PV vs Demanda) =====
    ax2 = axes[1]
    mall_pv_used = np.minimum(pv, mall_h)
    surplus_pv_mall = np.maximum(pv - mall_h, 0.0)
    ax2.fill_between(hours, 0, pv, color='yellow', alpha=0.45, label=f'Generación FV {pv.sum():.1f} kWh/día')
    ax2.fill_between(hours, 0, load, color='salmon', alpha=0.3, label=f'Demanda Total {load.sum():.1f} kWh/día')
    ax2.fill_between(hours, 0, mall_pv_used, color='yellowgreen', alpha=0.5, label='FV usada por mall')
    ax2.fill_between(hours, mall_h, mall_h + surplus_pv_mall, color='gold', alpha=0.45, label='Excedente FV sobre demanda mall')
    ax2.plot(hours, pv, 'g-', linewidth=2, label='Generación FV')
    ax2.plot(hours, load, 'r-', linewidth=2, label='Demanda Total')
    ax2.plot(hours, ev_h, 'm-.', linewidth=1.5, label='Carga EV (motos/mototaxis)')
    ax2.plot(hours, mall_h, 'c:', linewidth=1.5, label='Demanda mall')
    surplus_day = surplus_pv_mall.sum()
    surplus_max = surplus_pv_mall.max()
    mall_pv_used_day = mall_pv_used.sum()
    ax2.annotate(f'FV → mall: {mall_pv_used_day:.0f} kWh/día\nExcedente FV diario: {surplus_day:.0f} kWh\nExcedente horario máx: {surplus_max:.0f} kWh',
                 xy=(0.02, 0.98), xycoords='axes fraction', ha='left', va='top',
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
    ax2.set_xlabel('Hora del Día', fontsize=10)
    ax2.set_ylabel('Energía (kWh)', fontsize=10)
    ax2.set_title(f'Balance Energético - Generación FV Iquitos: {pv.sum():.1f} kWh/día', fontsize=12, fontweight='bold')
    ax2.set_xlim(-0.5, 23.5)
    ax2.set_xticks(range(24))
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
    
    ax3.set_xlabel('Hora del Día', fontsize=10)
    ax3.set_ylabel('Estado de Carga (%)', fontsize=10)
    ax3.set_title(f'Estado de Carga Batería - {capacity_kwh:.0f} kWh / {power_kw:.0f} kW (DoD {dod*100:.0f}%, {c_rate}C)', 
                  fontsize=12, fontweight='bold')
    ax3.set_xlim(-0.5, 23.5)
    ax3.set_ylim(0, 110)
    ax3.set_xticks(range(24))
    ax3.legend(loc='upper left', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # Agregar anotaciones de SOC
    soc_min_val = soc.min()
    soc_max_val = soc.max()
    cycles_day = charge.sum() / capacity_kwh if capacity_kwh > 0 else 0
    ax3.annotate(f'SOC min: {soc_min_val:.1f}%\nSOC máx: {soc_max_val:.1f}%\nCiclos/día: {cycles_day:.2f}',
                 xy=(0.02, 0.98), xycoords='axes fraction', ha='left', va='top',
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    # ===== Panel 4: Flujos de Energía =====
    ax4 = axes[3]
    
    # Barras para carga/descarga BESS
    ax4.bar(hours, charge, color='green', alpha=0.7, label='Carga BESS')
    ax4.bar(hours, -discharge, color='orange', alpha=0.7, label='Descarga BESS')

    # Líneas de contexto: FV y demanda mall
    ax4.plot(hours, pv, 'g-', linewidth=1.8, label='FV')
    ax4.plot(hours, mall_h, 'c-', linewidth=1.5, label='Demanda mall')
    # Áreas mall: solar vs red (la transición ocurre donde PV intercepta la demanda)
    ax4.fill_between(hours, 0, mall_solar_used_plot, color='yellow', alpha=0.35, label='Solar al Mall')
    ax4.fill_between(hours, mall_solar_used_plot, mall_h, color='cyan', alpha=0.45, label='Toma de Red Mall')

    # Línea de red EV
    ax4.plot(hours, -ev_grid, 'm:', linewidth=1.5, label='Toma de Red EV')
    # Importación y exportación total
    ax4.plot(hours, grid_import, 'k--', linewidth=1.2, label='Importación red')
    ax4.bar(hours, -grid_export, color='gray', alpha=0.6, label='Exportación red')

    ax4.axhline(y=0, color='black', linewidth=0.5)
    ax4.set_xlabel('Hora del Día', fontsize=10)
    ax4.set_ylabel('Energía (kWh)', fontsize=10)
    ax4.set_title('Flujos de Energía: BESS y Red Eléctrica', fontsize=12, fontweight='bold')
    ax4.set_xlim(-0.5, 23.5)
    ax4.set_xticks(range(24))
    ax4.legend(loc='upper right', fontsize=9)
    ax4.grid(True, alpha=0.3)
    
    # Métricas de red
    grid_total = grid_import.sum()
    grid_mall_total = mall_grid.sum()
    grid_ev_total = ev_grid.sum()
    self_suff = 1.0 - (grid_total / max(load.sum(), 1e-9))
    ax4.annotate(f'Red total: {grid_total:.1f} kWh\n  Mall: {grid_mall_total:.1f} kWh\n  EV: {grid_ev_total:.1f} kWh\nAutosuficiencia: {self_suff*100:.1f}%',
                 xy=(0.98, 0.98), xycoords='axes fraction', ha='right', va='top',
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
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
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
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
    ev_kwh_day = df_ev['ev_kwh'].sum() / (len(df_ev) / 24)
    print(f"   Demanda EV: {ev_kwh_day:.0f} kWh/dia")

    # ===========================================
    # 2. Alinear series temporales
    # ===========================================
    min_len = min(len(df_pv), len(df_mall), len(df_ev))
    if min_len < 8760:
        print(f"   Ajustando a {min_len} horas")

    pv_kwh = np.asarray(df_pv['pv_kwh'].values[:min_len])
    pv_shift_hours = 0
    if tz:
        try:
            from zoneinfo import ZoneInfo
            offset = ZoneInfo(tz).utcoffset(pd.Timestamp(year, 6, 1))
            if offset is not None:
                pv_shift_hours = int(offset.total_seconds() / 3600)
        except Exception:
            pv_shift_hours = 0
    if pv_shift_hours:
        pv_kwh = np.roll(pv_kwh, pv_shift_hours)

    mall_kwh = np.asarray(df_mall['mall_kwh'].values[:min_len])
    ev_kwh = np.asarray(df_ev['ev_kwh'].values[:min_len])

    total_load_kwh = mall_kwh + ev_kwh

    bess_load_scope = str(load_scope).lower()
    mall_grid_import = np.zeros_like(mall_kwh)
    if bess_load_scope not in ("total", "ev_priority", "ev_only"):
        print(f"   load_scope desconocido: {load_scope}. Usando total")
        bess_load_scope = "total"

    hours = np.arange(min_len) % 24

    pv_hourly_mean = pd.Series(pv_kwh).groupby(hours).mean()
    night_hours = set(pv_hourly_mean[pv_hourly_mean <= pv_night_threshold_kwh].index.astype(int).tolist())
    night_mask = np.isin(hours, list(night_hours))
    discharge_hours_set = set(discharge_hours) if discharge_hours else None
    sizing_mask = night_mask
    if discharge_hours_set is not None:
        sizing_mask = sizing_mask & np.isin(hours, list(discharge_hours_set))

    # Horario de apertura de mall para EV (9 a 22)
    open_start = 9
    open_end = 22
    open_mask = (hours >= open_start) & (hours < open_end)
    ev_shortfall = np.maximum(ev_kwh - pv_kwh, 0.0)
    ev_shortfall_open_day = float((ev_shortfall * open_mask).sum() / (min_len / 24))
    peak_ev_shortfall_kw = float(ev_shortfall[open_mask].max()) if np.any(open_mask) else 0.0

    # ===========================================
    # 3. Calcular balance energetico
    # ===========================================
    print("")
    print("Calculando balance energetico...")

    bess_load = total_load_kwh
    surplus = np.maximum(pv_kwh - total_load_kwh, 0)
    deficit = np.maximum(total_load_kwh - pv_kwh, 0)

    surplus_day = float(surplus.sum() / (min_len / 24))
    deficit_day = float(deficit.sum() / (min_len / 24))
    night_deficit_day = float((deficit * sizing_mask).sum() / (min_len / 24))
    pv_day = float(pv_kwh.sum() / (min_len / 24))
    pv_available_day = float(pv_kwh.sum() / (min_len / 24))
    load_day = float(total_load_kwh.sum() / (min_len / 24))
    bess_load_day = float(total_load_kwh.sum() / (min_len / 24))

    print(f"   Generacion PV: {pv_day:.0f} kWh/dia")
    if bess_load_scope in ("ev_only", "ev_priority"):
        print(f"   PV disponible BESS: {pv_available_day:.0f} kWh/dia")
        print(f"   Demanda BESS (EV): {bess_load_day:.0f} kWh/dia")
    print(f"   Demanda Total: {load_day:.0f} kWh/dia")
    print(f"   Excedente PV (BESS):  {surplus_day:.0f} kWh/dia")
    print(f"   Deficit (BESS):       {deficit_day:.0f} kWh/dia")
    if night_hours:
        print(f"   Horas sin solar: {sorted(night_hours)}")
        print(f"   Deficit EV nocturno: {night_deficit_day:.0f} kWh/dia")
    print(f"   Deficit EV horario abierto ({open_start}-{open_end}h): {ev_shortfall_open_day:.0f} kWh/dia")
    print(f"   Pico deficit EV horario abierto: {peak_ev_shortfall_kw:.1f} kW")

    # ===========================================
    # 4. Dimensionar BESS
    # ===========================================
    print("")
    print("Dimensionando BESS...")

    effective_dod = dod
    soc_min = None
    # Para modo EV horario abierto, forzar reserva del 20% si no se especifica
    mode_lower = str(sizing_mode).lower()
    if soc_min_percent is None and mode_lower == "ev_open_hours":
        soc_min_percent = 20.0
    if soc_min_percent is not None:
        soc_min = soc_min_percent / 100.0
        effective_dod = min(dod, 1.0 - soc_min)

    # Seleccionar deficit y pico según modo
    peak_load = float(bess_load.max()) if len(bess_load) > 0 else 0.0
    if mode_lower in ("ev_night_deficit", "night_deficit"):
        sizing_deficit = night_deficit_day
    elif mode_lower == "ev_open_hours":
        sizing_deficit = ev_shortfall_open_day
        peak_load = peak_ev_shortfall_kw
    else:
        sizing_deficit = deficit_day
    # Limitar excedente usado para dimensionamiento si se indica (p.ej., capturar export diario)
    surplus_for_sizing = min(surplus_day, surplus_target_kwh_day) if surplus_target_kwh_day > 0 else surplus_day

    capacity_kwh, power_kw = calculate_bess_capacity(
        surplus_kwh_day=surplus_for_sizing,
        deficit_kwh_day=sizing_deficit,
        dod=effective_dod,
        efficiency=efficiency_roundtrip,
        autonomy_hours=autonomy_hours,
        peak_load_kw=peak_load,
        round_kwh=round_kwh,
        sizing_mode=sizing_mode,
        fixed_capacity_kwh=fixed_capacity_kwh,
        fixed_power_kw=fixed_power_kw,
    )

    power_kw = capacity_kwh * c_rate if capacity_kwh > 0 else 0.0

    print(f"   Capacidad: {capacity_kwh:.0f} kWh")
    print(f"   Potencia:  {power_kw:.0f} kW")
    print(f"   DoD:       {effective_dod*100:.0f}%")
    print(f"   C-rate:    {c_rate}")

    # ===========================================
    # 5. Simular operacion
    # ===========================================
    print("")
    print("Simulando operacion del sistema...")

    if discharge_only_no_solar:
        night_set = set(night_hours)
        if discharge_hours_set is None:
            discharge_hours_set = night_set
        else:
            discharge_hours_set = discharge_hours_set.intersection(night_set)
    if discharge_hours_set is not None and len(discharge_hours_set) == 0:
        print("   Aviso: no hay horas de descarga disponibles; BESS no descargara.")
    ev_load_kwh = ev_kwh
    mall_load_kwh = mall_kwh

    df_bess, metrics = simulate_bess_operation(
        pv_kwh=pv_kwh,
        ev_kwh=ev_load_kwh,
        mall_kwh=mall_load_kwh,
        capacity_kwh=capacity_kwh,
        power_kw=power_kw,
        dod=effective_dod,
        efficiency=efficiency_roundtrip,
        initial_soc=0.5,
        soc_min=soc_min,
        discharge_hours=discharge_hours_set,
        hours=hours,
        discharge_to_mall=(bess_load_scope != "ev_only"),
    )

    if bess_load_scope == "ev_only":
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
        total_grid_import = float(grid_import_total.sum())
        total_grid_export = float(df_sim['grid_export_kwh'].sum())
        self_sufficiency = 1.0 - (total_grid_import / max(total_load, 1e-9))

        metrics = metrics.copy()
        metrics['total_pv_kwh'] = total_pv
        metrics['total_load_kwh'] = total_load
        metrics['total_grid_import_kwh'] = total_grid_import
        metrics['total_grid_export_kwh'] = total_grid_export
        metrics['self_sufficiency'] = self_sufficiency
    elif bess_load_scope == "ev_priority":
        grid_import_total = df_bess['grid_import_ev_kwh'].values + df_bess['grid_import_mall_kwh'].values
        grid_export_total = df_bess['grid_export_kwh'].values

        df_sim = df_bess.copy()
        df_sim['pv_kwh'] = pv_kwh
        df_sim['load_kwh'] = total_load_kwh
        df_sim['net_balance_kwh'] = pv_kwh - total_load_kwh
        df_sim['grid_import_kwh'] = grid_import_total
        df_sim['grid_export_kwh'] = grid_export_total
        df_sim['mall_grid_import_kwh'] = df_bess['grid_import_mall_kwh'].values
        df_sim['ev_grid_import_kwh'] = df_bess['grid_import_ev_kwh'].values

        total_pv = float(pv_kwh.sum())
        total_load = float(total_load_kwh.sum())
        total_grid_import = float(grid_import_total.sum())
        total_grid_export = float(grid_export_total.sum())
        self_sufficiency = 1.0 - (total_grid_import / max(total_load, 1e-9))

        metrics = metrics.copy()
        metrics['total_pv_kwh'] = total_pv
        metrics['total_load_kwh'] = total_load
        metrics['total_grid_import_kwh'] = total_grid_import
        metrics['total_grid_export_kwh'] = total_grid_export
        metrics['self_sufficiency'] = self_sufficiency
    else:
        df_sim = df_bess
        df_sim['load_kwh'] = total_load_kwh

    df_sim['mall_kwh'] = mall_kwh
    df_sim['ev_kwh'] = ev_kwh
    if 'grid_import_kwh' not in df_sim.columns:
        df_sim['grid_import_kwh'] = 0.0
    if 'grid_import_ev_kwh' in df_sim.columns and 'grid_import_mall_kwh' in df_sim.columns:
        df_sim['grid_import_kwh'] = df_sim['grid_import_ev_kwh'] + df_sim['grid_import_mall_kwh']

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
        night_deficit_kwh_day=night_deficit_day,
        pv_generation_kwh_day=pv_day,
        total_demand_kwh_day=load_day,
        mall_demand_kwh_day=mall_kwh_day,
        ev_demand_kwh_day=ev_kwh_day,
        bess_load_scope=bess_load_scope,
        pv_available_kwh_day=pv_available_day,
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

    citylearn_params = prepare_citylearn_data(
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
        )

    print("")
    print("=" * 60)
    print(f"Resultados guardados en: {out_dir}")
    print("=" * 60)

    return result_dict
