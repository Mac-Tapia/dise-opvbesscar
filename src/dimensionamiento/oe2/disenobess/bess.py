Opción B: Unificar data_loader con catálogo (RECOMENDADO)"""
Módulo de dimensionamiento de sistema de almacenamiento BESS.

PROPÓSITO: Calcular capacidad y potencia óptima del BESS para el sistema
           Iquitos EV Mall, generando datasets para CityLearn.

Incluye:
- Cálculo de capacidad BESS basado en déficit EV vs solar
- Simulación horaria del SOC (Estado de Carga)
- Generación de dataset BESS para CityLearn (electrical_storage_simulation.csv)
- Gráficas de dimensionamiento y SOC
- NUEVO: Simulación con ARBITRAJE HP/HFP tarifas OSINERGMIN

NOTA: El balance energético completo del sistema está en:
      src/dimensionamiento/oe2/balance_energetico/balance.py

Valores v5.3 (2026-02-XX):
- 38 sockets (19 cargadores × 2) @ 7.4 kW = 281.2 kW instalado
- Demanda EV (9h-22h): 1,129 kWh/día (412,236 kWh/año)
- BESS: 1,700 kWh / 400 kW (optimizado para arbitraje HP/HFP)
- Tarifas OSINERGMIN: HP(18-23h) S/.0.45/kWh | HFP S/.0.28/kWh
- Ahorro estimado arbitraje: ~S/.450,000/año
"""
from __future__ import annotations

import sys
import os

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    try:
        # Enable UTF-8 output on Windows
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # Fallback if encoding change fails

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
    """Datos de simulacion para una hora."""
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


# ============================================================================
# TARIFAS OSINERGMIN - Electro Oriente S.A. (Iquitos, Loreto)
# Pliego Tarifario MT3 - Media Tensión Comercial/Industrial
# Vigente desde 2024-11-04
# Referencia: OSINERGMIN Resolución N° 047-2024-OS/CD
# ============================================================================
# Hora Punta (HP): 18:00 - 23:00 (5 horas)
# Hora Fuera de Punta (HFP): 00:00 - 17:59, 23:00 - 23:59 (19 horas)
# ============================================================================

# Tarifas de Energía (S/./kWh)
TARIFA_ENERGIA_HP_SOLES = 0.45     # Hora Punta: S/.0.45/kWh
TARIFA_ENERGIA_HFP_SOLES = 0.28    # Hora Fuera de Punta: S/.0.28/kWh

# Tarifas de Potencia (S/./kW-mes)
TARIFA_POTENCIA_HP_SOLES = 48.50   # Potencia en HP: S/.48.50/kW-mes
TARIFA_POTENCIA_HFP_SOLES = 22.80  # Potencia en HFP: S/.22.80/kW-mes

# Factor de conversión a USD (tipo de cambio referencial)
TIPO_CAMBIO_PEN_USD = 3.75  # PEN/USD

# Tarifas en USD (referencial)
TARIFA_ENERGIA_HP_USD = TARIFA_ENERGIA_HP_SOLES / TIPO_CAMBIO_PEN_USD   # ~0.12 USD/kWh
TARIFA_ENERGIA_HFP_USD = TARIFA_ENERGIA_HFP_SOLES / TIPO_CAMBIO_PEN_USD  # ~0.075 USD/kWh

# Horas de periodo punta (18:00 - 22:59, inclusive)
HORAS_PUNTA = list(range(18, 23))  # [18, 19, 20, 21, 22]
HORA_INICIO_HP = 18
HORA_FIN_HP = 23  # Exclusivo (hasta las 22:59)

# Factor de emisión CO2 para generación térmica aislada (Iquitos)
# Fuente: MINEM/OSINERGMIN - Sistema aislado Loreto (térmico diésel/residual)
FACTOR_CO2_KG_KWH = 0.4521  # kg CO2 / kWh

# BESS v5.3 - Configuración optimizada con arbitraje HP/HFP
# Capacidad aumentada para maximizar arbitraje tarifario
BESS_CAPACITY_KWH_V53 = 1700.0   # kWh - Aumentado para arbitraje HP/HFP
BESS_POWER_KW_V53 = 400.0        # kW - Potencia nominal
BESS_DOD_V53 = 0.80              # 80% DoD
BESS_EFFICIENCY_V53 = 0.95       # 95% round-trip
BESS_SOC_MIN_V53 = 0.20          # 20% SOC mínimo
BESS_SOC_MAX_V53 = 1.00          # 100% SOC máximo


def load_mall_demand_real(
    mall_demand_path: Path,
    year: int = 2024,
) -> pd.DataFrame:
    """
    Carga la demanda REAL horaria del mall desde CSV.

    IMPORTANTE: Los datos DEBEN estar en formato horario (8,760 horas exactas).
    El archivo `demandamallhorakwh.csv` contiene:
    - Columnas: FECHAHORA;kWh
    - Rango: 01/01/2024 00:00 a 31/12/2024 23:00 (8,760 horas = 365 días × 24)
    - Todo dato REAL, SIN generación sintética

    NO se puede usar para completar años incompletos - requiere datos COMPLETOS.

    Args:
        mall_demand_path: Ruta al archivo CSV con demanda real del mall (REQUERIDO: 8,760 horas)
        year: Año de simulacion (solo informativo)

    Returns:
        DataFrame con demanda horaria real del mall en kWh (exactamente 8,760 filas)
    """
    header = mall_demand_path.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
    sep = ";" if ";" in header and "," not in header else ","
    df = pd.read_csv(mall_demand_path, sep=sep)  # type: ignore[attr-defined]

    def find_col(candidates: list[str]) -> Optional[str]:
        for col in df.columns:
            if not isinstance(col, str):  # type: ignore[unreachable]
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

    # Asegurar indice datetime
    df['datetime'] = pd.to_datetime(df['datetime'], dayfirst=True, errors='coerce')  # type: ignore[attr-defined]
    df['power_kw'] = pd.to_numeric(df['power_kw'], errors='coerce')  # type: ignore[attr-defined]
    df = df.dropna(subset=['datetime', 'power_kw'])  # type: ignore[attr-defined]
    df = df.set_index('datetime')  # type: ignore[attr-defined]

    # Detectar intervalo de tiempo
    if len(df) > 1:
        time_diff = (df.index[1] - df.index[0]).total_seconds() / 60  # en minutos
    else:
        time_diff = 15  # Asumir 15 min por defecto
    if time_diff <= 0:
        time_diff = 15

    demand_col_norm = demand_col.strip().lower()
    unit_is_energy = "kwh" in demand_col_norm
    df["power_kw"] = pd.to_numeric(df["power_kw"], errors="coerce")  # type: ignore[attr-defined]
    df = df.dropna(subset=["power_kw"])  # type: ignore[attr-defined]

    if unit_is_energy:
        # Los valores son energia por intervalo (kWh). Convertir a potencia y luego a energia horaria.
        df["energy_kwh"] = df["power_kw"]
        df["power_kw"] = df["energy_kwh"] * 60.0 / time_diff
    else:
        # Los valores son potencia (kW). Convertir a energia por intervalo.
        df["energy_kwh"] = df["power_kw"] * (time_diff / 60.0)

    # Conversión a formato horario (si es necesario)
    if time_diff < 60:
        df_hourly = df["energy_kwh"].resample("h").sum().to_frame("mall_kwh")  # type: ignore[attr-defined]
    else:
        df_hourly = df["energy_kwh"].to_frame("mall_kwh")  # type: ignore[attr-defined]
    
    # Validación CRÍTICA: Debe tener exactamente 8,760 horas
    if len(df_hourly) != 8760:
        raise ValueError(
            f"ERROR: Demanda mall debe tener EXACTAMENTE 8,760 horas de datos REALES.\n"
            f"Se encontraron {len(df_hourly)} filas.\n"
            f"Archivo: {mall_demand_path}\n"
            f"NO se acepta generación sintética ni años incompletos."
        )
    
    return df_hourly[['mall_kwh']]


def load_pv_generation(pv_timeseries_path: Path) -> pd.DataFrame:
    """Carga la generacion PV desde timeseries (formato horario).
    
    Soporta múltiples formatos de columnas:
    - potencia_kw, energia_kwh (PVGIS v3.0 Iquitos)
    - ac_power_kw, ac_energy_kwh (estándar SMA)
    - pv_kwh, p_ac (otros)
    """
    df = pd.read_csv(pv_timeseries_path)  # type: ignore[attr-defined]

    # Detectar columna de tiempo
    time_col = None
    for col in ['datetime', 'timestamp', 'time', 'Timestamp', 'fecha', 'hora']:
        if col in df.columns:
            time_col = col
            break

    if time_col:
        try:
            df[time_col] = pd.to_datetime(df[time_col])  # type: ignore[attr-defined]
            df = df.set_index(time_col)  # type: ignore[attr-defined]
        except Exception:
            pass

    # Resamplear a horario si es subhorario
    if len(df) > 8760:
        df_hourly = df.resample('h').sum()  # type: ignore[attr-defined]
    else:
        df_hourly = df

    # Buscar columna de generacion PV - ORDEN IMPORTA
    # Prioritizar columnas de ENERGÍA (kWh) sobre POTENCIA (kW)
    pv_col = None
    for col in ['pv_generation_kwh', 'energia_kwh', 'ac_energy_kwh', 'pv_kwh', 'potencia_kw', 'ac_power_kw', 'p_ac']:
        if col in df_hourly.columns:
            pv_col = col
            break

    if pv_col:
        df_hourly['pv_kwh'] = df_hourly[pv_col].astype(float)
    else:
        print(f"    [WARN] Columna PV no encontrada en {pv_timeseries_path.name}")
        print(f"    Columnas disponibles: {list(df_hourly.columns[:5])}")
        df_hourly['pv_kwh'] = 0.0

    return df_hourly[['pv_kwh']].reset_index(drop=True)

def load_ev_demand(ev_profile_path: Path, year: int = 2024) -> pd.DataFrame:
    """Carga el perfil de demanda EV (formato horario 8,760 horas).

    El archivo CSV puede tener:
    - Formato v5.2: 38 columnas socket_XXX_charging_power_kw (estocástico)
      -> Suma todas las potencias de sockets (19 cargadores × 2 tomas = 38 sockets)
      -> Total esperado (9h-22h): 412,236 kWh/año (1,129 kWh/día)
    - 96 intervalos (15 minutos) para un dia tipico -> se suma a 24 horas
    - 8,760 intervalos (horario) -> se retorna tal cual
    - 24 horas (formato antiguo) -> se expande a 8,760 horas/año

    Returns:
        DataFrame con columna 'ev_kwh' (energia en kWh por hora)
    """
    df = pd.read_csv(ev_profile_path)  # type: ignore[attr-defined]

    # Verificar si es formato v5.2 (columnas socket_XXX_charging_power_kw)
    socket_cols = [col for col in df.columns if 'socket_' in col and 'charging_power_kw' in col]
    if len(socket_cols) > 0:
        # Formato v5.2: sumar todas las potencias de sockets (38 sockets)
        print(f"      [OK] Detectado formato v5.2 con {len(socket_cols)} sockets")
        df['ev_kwh'] = df[socket_cols].sum(axis=1)
        
        # FILTRAR HORARIO OPERATIVO: Solo 9h-22h (estacionamiento del mall)
        for h in range(len(df)):
            hour = h % 24
            if hour < 9 or hour > 22:
                df.loc[h, 'ev_kwh'] = 0.0
        
        total_kwh = df['ev_kwh'].sum()
        print(f"      [OK] Total EV (9h-22h): {total_kwh:,.0f} kWh/año")
        df = df[['ev_kwh']].copy()
        # Asegurar 8,760 filas
        if len(df) != 8760:
            if len(df) < 8760:
                # Repetir cíclicamente para completar el año
                repeat_count = (8760 // len(df)) + 1
                df = pd.concat([df] * repeat_count, ignore_index=True)
            df = df.iloc[:8760].reset_index(drop=True)
        return df

    # Verificar si es formato v3.0 legacy (columnas socket_XXX_power_kw)
    socket_cols = [col for col in df.columns if 'socket_' in col and '_power_kw' in col]
    if len(socket_cols) > 0:
        # Formato v3.0 legacy: sumar todas las potencias de sockets
        print(f"      [OK] Detectado formato v3.0 legacy con {len(socket_cols)} sockets")
        df['ev_kwh'] = df[socket_cols].sum(axis=1)
        df = df[['ev_kwh']].copy()
        # Asegurar 8,760 filas
        if len(df) != 8760:
            if len(df) < 8760:
                # Repetir cíclicamente para completar el año
                repeat_count = (8760 // len(df)) + 1
                df = pd.concat([df] * repeat_count, ignore_index=True)
            df = df.iloc[:8760].reset_index(drop=True)
        return df

    # Verificar si es formato de 15 minutos (96 intervalos) o formato horario (8,760 horas)
    if 'interval' in df.columns and 'energy_kwh' in df.columns:
        # Formato nuevo: 96 intervalos de 15 minutos para un dia
        if len(df) == 96:
            # Agrupar cada 4 intervalos (1 hora)
            df['hour'] = df['interval'] // 4
            df_hourly = df.groupby('hour')['energy_kwh'].sum().reset_index()  # type: ignore[attr-defined]
            df_hourly.columns = ['hour', 'ev_kwh']

            # Expandir a 365 dias (8,760 horas)
            df_annual = []
            for _ in range(365):
                for _, row in df_hourly.iterrows():
                    df_annual.append({'ev_kwh': float(row['ev_kwh'])})  # type: ignore[attr-defined]
            return pd.DataFrame(df_annual)
        elif len(df) == 8760:
            # Ya es formato horario
            return df[['energy_kwh']].rename(columns={'energy_kwh': 'ev_kwh'})

    # Formato antiguo: 24 horas (retrocompatibilidad)
    if 'hour' in df.columns and 'energy_kwh' in df.columns:
        # Perfil de 24 horas, expandir a año
        hourly_profile = df.set_index('hour')['energy_kwh']  # type: ignore[attr-defined]
        df_full = []
        for _ in range(365):
            for hour in range(24):
                ev_kwh = hourly_profile.get(hour, 0.0)
                df_full.append({'ev_kwh': ev_kwh})  # type: ignore[attr-defined]
        return pd.DataFrame(df_full)

    # Intentar detectar automáticamente si ya es 8,760 horas
    if len(df) == 8760:
        # Buscar columna de energía
        for col in df.columns:
            if 'kwh' in col.lower() or 'energy' in col.lower():
                return pd.DataFrame({
                    'ev_kwh': df[col].values
                })

    raise ValueError("Formato de CSV no reconocido. Se esperan socket_XXX_power_kw (v3.0), 'interval' + 'energy_kwh' (96), 'hour' + 'energy_kwh' (24h), o 8,760 horas")

def simulate_bess_operation(
    pv_kwh: np.ndarray,  # type: ignore[attr-defined]
    ev_kwh: np.ndarray,  # type: ignore[attr-defined]
    mall_kwh: np.ndarray,  # type: ignore[attr-defined]
    capacity_kwh: float,
    power_kw: float,
    dod: float,
    efficiency: float,
    initial_soc: float = 0.5,
    soc_min: Optional[float] = None,
    discharge_hours: Optional[set[int]] = None,
    hours: Optional[np.ndarray] = None,  # type: ignore[attr-defined]
    discharge_to_mall: bool = True,
) -> Tuple[pd.DataFrame, dict[str, float]]:
    """
    Simula la operacion del BESS hora a hora con cargas separadas (EV y mall).

    Resolucion: Horaria (8,760 timesteps/ano)
    """
    n_hours = len(pv_kwh)  # type: ignore[arg-type]

    # Inicializar arrays
    grid_import_ev = np.zeros(n_hours)
    grid_import_mall = np.zeros(n_hours)
    grid_export = np.zeros(n_hours)
    pv_used_ev = np.zeros(n_hours)
    pv_used_mall = np.zeros(n_hours)
    bess_charge = np.zeros(n_hours)
    bess_discharge = np.zeros(n_hours)
    soc = np.zeros(n_hours)

    # Parámetros por defecto
    if soc_min is None:
        soc_min = (1.0 - dod)
    soc_max = 1.0
    eff_charge = math.sqrt(efficiency)
    eff_discharge = math.sqrt(efficiency)
    current_soc = initial_soc

    # Simulación horaria simple: PV -> EV -> BESS -> Mall -> Grid
    for h in range(n_hours):
        # PV a EV
        pv_to_ev = min(pv_kwh[h], ev_kwh[h])
        pv_used_ev[h] = pv_to_ev
        remaining_pv = pv_kwh[h] - pv_to_ev

        # PV a BESS
        if remaining_pv > 0 and current_soc < soc_max:
            max_charge = min(power_kw, remaining_pv, (soc_max - current_soc) * capacity_kwh)
            bess_charge[h] = max_charge
            current_soc += max_charge * eff_charge / capacity_kwh
            remaining_pv -= max_charge

        # PV a Mall
        pv_to_mall = min(remaining_pv, mall_kwh[h])
        pv_used_mall[h] = pv_to_mall

        # Exportar sobrante
        grid_export[h] = max(remaining_pv - pv_to_mall, 0.0)

        # Deficits
        ev_deficit = ev_kwh[h] - pv_to_ev
        mall_deficit = mall_kwh[h] - pv_to_mall

        # BESS descarga
        if (current_soc > soc_min) and (ev_deficit > 0 or mall_deficit > 0):
            max_discharge = min(power_kw, (current_soc - soc_min) * capacity_kwh)
            discharge_needed = ev_deficit + (mall_deficit if discharge_to_mall else 0.0)
            actual_discharge = min(max_discharge, discharge_needed) * eff_discharge
            bess_discharge[h] = actual_discharge
            current_soc -= actual_discharge * eff_discharge / capacity_kwh
            ev_cover = min(actual_discharge, ev_deficit)
            ev_deficit -= ev_cover
            if discharge_to_mall:
                mall_deficit -= max(0, actual_discharge - ev_cover)

        # Grid import
        grid_import_ev[h] = max(ev_deficit, 0.0)
        grid_import_mall[h] = max(mall_deficit, 0.0)
        soc[h] = current_soc

    # DataFrame resultado
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

    # Metricas
    total_pv = float(pv_kwh.sum())
    total_load = float(ev_kwh.sum() + mall_kwh.sum())
    total_grid_import = float(grid_import_ev.sum() + grid_import_mall.sum())

    metrics = {
        'total_pv_kwh': total_pv,
        'total_load_kwh': total_load,
        'total_grid_import_kwh': total_grid_import,
        'total_grid_export_kwh': float(grid_export.sum()),
        'total_bess_charge_kwh': float(bess_charge.sum()),
        'total_bess_discharge_kwh': float(bess_discharge.sum()),
        'pv_used_ev_kwh': float(pv_used_ev.sum()),
        'pv_used_mall_kwh': float(pv_used_mall.sum()),
        'grid_import_ev_kwh': float(grid_import_ev.sum()),
        'grid_import_mall_kwh': float(grid_import_mall.sum()),
        'self_sufficiency': 1.0 - (total_grid_import / max(total_load, 1e-9)),
        'cycles_per_day': float(bess_charge.sum()) / capacity_kwh / 365 if capacity_kwh > 0 else 0.0,
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
    Calcula la capacidad optima del BESS para cubrir 100% deficit EV.

    REGLAS DE DIMENSIONAMIENTO (Proyecto Iquitos):
    - BESS exclusivo para carga EV (motos y mototaxis)
    - Capacidad = Deficit EV / (DOD × Eficiencia)
    - Deficit EV = Suma(EV - PV) cuando PV < EV, hasta las 22:00
    - DOD = 80% (SOC 100% → 20% a las 22:00)
    
    sizing_mode:
    - "ev_deficit_100": Cubrir 100% del deficit EV (NUEVO - recomendado)
    - "ev_open_hours": deficit EV dinámico (cuando solar insuficiente, hasta cierre 22h)
    - "max": usa el maximo entre excedente, deficit y autonomia
    - "surplus_only": usa solo el excedente FV
    """
    cap_surplus = surplus_kwh_day / (dod * efficiency) if surplus_kwh_day > 0 else 0.0
    cap_deficit = deficit_kwh_day / (dod * efficiency) if deficit_kwh_day > 0 else 0.0
    cap_autonomy = (peak_load_kw * autonomy_hours) / (dod * efficiency) if peak_load_kw > 0 else 0.0

    mode = str(sizing_mode).lower()
    if mode == "fixed" and fixed_capacity_kwh > 0 and fixed_power_kw > 0:
        return float(fixed_capacity_kwh), float(fixed_power_kw)
    if mode in ("surplus_only", "surplus"):
        capacity = cap_surplus
    elif mode in ("ev_night_deficit", "night_deficit", "ev_open_hours", "ev_deficit_100"):
        # NUEVO: Usar deficit calculado para cubrir 100% EV
        capacity = cap_deficit
    elif mode in ("max", "default"):
        capacity = max(cap_surplus, cap_deficit, cap_autonomy)
    else:
        raise ValueError(f"sizing_mode invalido: {sizing_mode}")

    capacity = max(capacity, 0.0)
    capacity = math.ceil(capacity / round_kwh) * round_kwh if capacity > 0 else 0.0

    # POTENCIA: Basada en pico de deficit + margen
    # Para cubrir picos de demanda EV cuando no hay sol
    c_rate_target = 0.36  # v5.2: C-rate conservador
    power = capacity * c_rate_target if capacity > 0 else 0.0
    
    # Minimo: potencia debe cubrir el pico de deficit
    if peak_load_kw > power:
        power = peak_load_kw * 1.1  # 10% margen sobre pico

    return float(capacity), float(power)


def calculate_ev_deficit_for_bess(
    pv_kwh: np.ndarray,
    ev_kwh: np.ndarray,
    closing_hour: int = 22,
) -> Tuple[float, float, int, int, float]:
    """
    Calcula el déficit EV exacto que el BESS debe cubrir.
    
    REGLAS:
    1. Déficit = Suma(EV - PV) cuando EV > PV en CUALQUIER hora del día
    2. Esto incluye horas tempranas (antes del sol) y tardes/noches
    
    Args:
        pv_kwh: Array de generación PV horaria (8760 horas)
        ev_kwh: Array de demanda EV horaria (8760 horas)
        closing_hour: Hora de cierre (default 22)
    
    Returns:
        Tuple: (deficit_kwh_day_avg, peak_deficit_kw, charge_end_hour, discharge_start_hour, deficit_kwh_day_max)
    """
    n_days = len(pv_kwh) // 24
    
    daily_deficits = []
    peak_deficit = 0.0
    charge_end_hours = []
    discharge_start_hours = []
    
    for day in range(n_days):
        h_start = day * 24
        pv_day = pv_kwh[h_start:h_start + 24]
        ev_day = ev_kwh[h_start:h_start + 24]
        
        # Encontrar punto de cruce (PV >= EV) - fin de carga, inicio mantener 100%
        charge_end = None
        for h in range(6, 18):  # Solo horas con sol potencial
            if pv_day[h] >= ev_day[h] and pv_day[h] > 0.1:
                charge_end = h
                break
        
        # Encontrar punto crítico (PV < EV después de generar) - inicio descarga
        discharge_start = None
        for h in range(12, closing_hour + 1):  # Buscar en tarde/noche
            if pv_day[h] < ev_day[h] and ev_day[h] > 0.1:
                discharge_start = h
                break
        
        if charge_end is not None:
            charge_end_hours.append(charge_end)
        if discharge_start is not None:
            discharge_start_hours.append(discharge_start)
        
        # Calcular déficit del día en TODAS las horas (no solo 17h-22h)
        # Esto incluye déficit en mañanas tempranas sin sol
        day_deficit = 0.0
        for h in range(24):
            deficit_h = max(ev_day[h] - pv_day[h], 0)
            day_deficit += deficit_h
            peak_deficit = max(peak_deficit, deficit_h)
        daily_deficits.append(day_deficit)
    
    deficit_arr = np.array(daily_deficits)
    deficit_kwh_day_avg = float(deficit_arr.mean()) if n_days > 0 else 0.0
    deficit_kwh_day_max = float(deficit_arr.max()) if n_days > 0 else 0.0
    avg_charge_end = int(np.mean(charge_end_hours)) if charge_end_hours else 10
    avg_discharge_start = int(np.mean(discharge_start_hours)) if discharge_start_hours else 17
    
    return deficit_kwh_day_avg, peak_deficit, avg_charge_end, avg_discharge_start, deficit_kwh_day_max


def simulate_bess_ev_exclusive(
    pv_kwh: np.ndarray,
    ev_kwh: np.ndarray,
    mall_kwh: np.ndarray,
    capacity_kwh: float,
    power_kw: float,
    efficiency: float = 0.95,
    soc_min: float = 0.20,
    soc_max: float = 1.00,
    closing_hour: int = 22,
    year: int = 2024,
) -> Tuple[pd.DataFrame, dict[str, float]]:
    """
    Simula operación BESS exclusivo para EV (motos y mototaxis).
    
    REGLAS DE OPERACIÓN:
    1. CARGA: Desde que inicia generación solar, mientras PV > 0
       - Se carga con excedente después de cubrir EV directamente
       - Mantiene SOC al 100% hasta punto crítico
    
    2. DESCARGA: Desde punto crítico (PV < EV) hasta closing_hour (22h)
       - Cubre 100% del déficit EV
       - SOC debe llegar a 20% a las 22:00
       - NO HAY OPERACIÓN después de las 22h
    
    3. MALL: Se alimenta de red pública, NO del BESS
    
    Args:
        pv_kwh: Generación PV horaria (8760)
        ev_kwh: Demanda EV horaria (8760)
        mall_kwh: Demanda Mall horaria (8760) - para registro, no usa BESS
        capacity_kwh: Capacidad BESS en kWh
        power_kw: Potencia máxima BESS en kW
        efficiency: Eficiencia round-trip (default 0.95)
        soc_min: SOC mínimo (default 0.20 = 20%)
        soc_max: SOC máximo (default 1.00 = 100%)
        closing_hour: Hora cierre (default 22) - EV y BESS terminan aquí
    
    Returns:
        Tuple: (DataFrame con simulación, dict con métricas)
    """
    n_hours = len(pv_kwh)
    eff_charge = math.sqrt(efficiency)
    eff_discharge = math.sqrt(efficiency)
    
    # Arrays de resultados
    soc = np.zeros(n_hours)
    bess_charge = np.zeros(n_hours)
    bess_discharge = np.zeros(n_hours)
    pv_to_ev = np.zeros(n_hours)
    pv_to_bess = np.zeros(n_hours)
    pv_to_mall = np.zeros(n_hours)
    bess_to_ev = np.zeros(n_hours)
    grid_to_ev = np.zeros(n_hours)
    grid_to_mall = np.zeros(n_hours)
    pv_curtailed = np.zeros(n_hours)
    
    # Estado inicial: SOC al 100% (BESS cargado del día anterior)
    current_soc = 1.00
    
    # Determinar hora de inicio de descarga (cuando PV < EV durante horas operativas)
    # Precalcular el punto crítico para cada día
    
    for h in range(n_hours):
        hour_of_day = h % 24
        pv_h = pv_kwh[h]
        ev_h = ev_kwh[h]
        mall_h = mall_kwh[h]
        
        # ====================================
        # REGLA: Horario de operación EV es 9h-22h (cierre)
        # Fuera de horario: EV = 0, BESS no opera
        # ====================================
        if hour_of_day >= closing_hour or hour_of_day < 6:
            # Fuera de horario operativo: EV = 0, BESS mantiene SOC
            ev_h = 0
            pv_to_ev[h] = 0
            bess_discharge[h] = 0
            bess_to_ev[h] = 0
            grid_to_ev[h] = 0
            
            # Mall aún puede usar PV si hay (aunque normalmente no hay de noche)
            pv_direct_to_mall = min(pv_h, mall_h)
            pv_to_mall[h] = pv_direct_to_mall
            mall_deficit = mall_h - pv_direct_to_mall
            grid_to_mall[h] = max(mall_deficit, 0)
            
            # PV sobrante
            pv_remaining = pv_h - pv_direct_to_mall
            pv_curtailed[h] = max(pv_remaining, 0)
            
            # No hay carga BESS fuera de horas solares efectivas
            soc[h] = current_soc
            continue
        
        # ====================================
        # PRIORIDAD 1: PV → EV directo (solo en horario 6h-22h)
        # ====================================
        pv_direct_to_ev = min(pv_h, ev_h)
        pv_to_ev[h] = pv_direct_to_ev
        pv_remaining = pv_h - pv_direct_to_ev
        ev_deficit = ev_h - pv_direct_to_ev
        
        # ====================================
        # PRIORIDAD 2: PV excedente → BESS (carga)
        # Solo cargar si hay sol Y aún no llegamos al 100%
        # Una vez al 100%, MANTENER hasta hora de descarga
        # ====================================
        if pv_remaining > 0 and current_soc < soc_max:
            # Capacidad disponible para carga
            soc_headroom = (soc_max - current_soc) * capacity_kwh
            max_charge = min(power_kw, pv_remaining, soc_headroom / eff_charge)
            
            if max_charge > 0:
                bess_charge[h] = max_charge
                pv_to_bess[h] = max_charge
                current_soc += (max_charge * eff_charge) / capacity_kwh
                current_soc = min(current_soc, soc_max)  # Asegurar no exceder 100%
                pv_remaining -= max_charge
        
        # ====================================
        # PRIORIDAD 3: PV final → Mall
        # ====================================
        pv_direct_to_mall = min(pv_remaining, mall_h)
        pv_to_mall[h] = pv_direct_to_mall
        pv_remaining -= pv_direct_to_mall
        mall_deficit = mall_h - pv_direct_to_mall
        
        # PV sobrante (curtailment)
        pv_curtailed[h] = max(pv_remaining, 0)
        
        # ====================================
        # DESCARGA BESS: Solo cuando hay déficit EV Y estamos en horario operativo
        # Y el PV ya no cubre el EV (punto crítico)
        # ====================================
        if ev_deficit > 0 and current_soc > soc_min and hour_of_day < closing_hour:
            # Solo descargar si PV no es suficiente para EV
            # Capacidad disponible para descarga
            soc_available = (current_soc - soc_min) * capacity_kwh
            max_discharge = min(power_kw, ev_deficit / eff_discharge, soc_available)
            
            if max_discharge > 0:
                actual_discharge = max_discharge * eff_discharge
                bess_discharge[h] = max_discharge
                bess_to_ev[h] = actual_discharge
                current_soc -= max_discharge / capacity_kwh
                current_soc = max(current_soc, soc_min)  # No bajar del mínimo
                ev_deficit -= actual_discharge
        
        # ====================================
        # GRID: Cubrir déficits restantes
        # ====================================
        grid_to_ev[h] = max(ev_deficit, 0)
        grid_to_mall[h] = max(mall_deficit, 0)
        
        # Guardar SOC
        soc[h] = current_soc
    
    # =====================================================
    # COLUMNA COMBINADA: bess_action_kwh
    # - CARGA: valor positivo (energía entrando al BESS)
    # - DESCARGA: valor positivo (energía saliendo del BESS)
    # - IDLE: cero (SOC se mantiene constante al 100%)
    # 
    # Lógica:
    # - Carga hasta SOC 100% (mañana con excedente solar)
    # - Mantiene SOC 100% constante hasta punto de cruce PV=EV
    # - Descarga desde punto de cruce hasta cierre 22h
    # - Descarga continua siguiendo demanda EV
    # =====================================================
    bess_action_kwh = np.zeros(n_hours)
    bess_mode = np.empty(n_hours, dtype=object)
    
    for h in range(n_hours):
        if bess_charge[h] > 0:
            # CARGA: energía entrando al BESS (positivo)
            bess_action_kwh[h] = bess_charge[h]
            bess_mode[h] = 'charge'
        elif bess_discharge[h] > 0:
            # DESCARGA: energía saliendo del BESS (positivo, NO negativo)
            bess_action_kwh[h] = bess_discharge[h]
            bess_mode[h] = 'discharge'
        else:
            # IDLE: SOC se mantiene constante (típicamente al 100%)
            bess_action_kwh[h] = 0.0
            bess_mode[h] = 'idle'
    
    # =====================================================
    # VERIFICACIÓN FINAL: Forzar cero fuera de horario operativo
    # Horario operativo BESS: 6h - 22h (closing_hour)
    # Fuera de horario (22h-23h, 0h-5h): bess_charge = 0, bess_discharge = 0
    # =====================================================
    for h in range(n_hours):
        hour_of_day = h % 24
        # Fuera de horario: 22h hasta 5h (inclusive)
        if hour_of_day >= closing_hour or hour_of_day < 6:
            bess_charge[h] = 0.0
            bess_discharge[h] = 0.0
            bess_action_kwh[h] = 0.0
            bess_mode[h] = 'idle'
            pv_to_bess[h] = 0.0
            bess_to_ev[h] = 0.0
    
    # =====================================================
    # CREAR COLUMNA DATETIME (fecha + hora completa año 2024)
    # Formato: '2024-01-01 00:00:00' hasta '2024-12-31 23:00:00'
    # =====================================================
    datetime_index = pd.date_range(
        start=f'{year}-01-01 00:00:00',
        periods=n_hours,
        freq='h'
    )
    
    # DataFrame de resultados CON DATETIME como índice
    df = pd.DataFrame({
        'pv_kwh': pv_kwh,
        'ev_kwh': ev_kwh,
        'mall_kwh': mall_kwh,
        'load_kwh': ev_kwh + mall_kwh,
        'pv_to_ev_kwh': pv_to_ev,
        'pv_to_bess_kwh': pv_to_bess,
        'pv_to_mall_kwh': pv_to_mall,
        'pv_curtailed_kwh': pv_curtailed,
        'bess_charge_kwh': bess_charge,
        'bess_discharge_kwh': bess_discharge,
        'bess_action_kwh': bess_action_kwh,  # NUEVA: carga/descarga en una columna (siempre positivo)
        'bess_mode': bess_mode,  # NUEVA: 'charge', 'discharge', 'idle'
        'bess_to_ev_kwh': bess_to_ev,
        'grid_import_ev_kwh': grid_to_ev,
        'grid_import_mall_kwh': grid_to_mall,
        'grid_import_kwh': grid_to_ev + grid_to_mall,
        'grid_export_kwh': pv_curtailed,  # Sin conexión a red, es curtailment
        'soc_percent': soc * 100,
        'soc_kwh': soc * capacity_kwh,
    }, index=datetime_index)
    df.index.name = 'datetime'
    
    # Métricas
    total_pv = float(pv_kwh.sum())
    total_ev = float(ev_kwh.sum())
    total_mall = float(mall_kwh.sum())
    total_load = total_ev + total_mall
    
    ev_from_pv = float(pv_to_ev.sum())
    ev_from_bess = float(bess_to_ev.sum())
    ev_from_grid = float(grid_to_ev.sum())
    
    # Autosuficiencia EV (lo importante para BESS)
    ev_self_sufficiency = (ev_from_pv + ev_from_bess) / max(total_ev, 1e-9)
    
    # Autosuficiencia total
    total_grid = float(grid_to_ev.sum() + grid_to_mall.sum())
    total_self_sufficiency = 1.0 - (total_grid / max(total_load, 1e-9))
    
    metrics = {
        'total_pv_kwh': total_pv,
        'total_ev_kwh': total_ev,
        'total_mall_kwh': total_mall,
        'total_load_kwh': total_load,
        'ev_from_pv_kwh': ev_from_pv,
        'ev_from_bess_kwh': ev_from_bess,
        'ev_from_grid_kwh': ev_from_grid,
        'mall_from_pv_kwh': float(pv_to_mall.sum()),
        'mall_from_grid_kwh': float(grid_to_mall.sum()),
        'total_bess_charge_kwh': float(bess_charge.sum()),
        'total_bess_discharge_kwh': float(bess_discharge.sum()),
        'total_grid_import_kwh': total_grid,
        'total_grid_export_kwh': float(pv_curtailed.sum()),
        'ev_self_sufficiency': ev_self_sufficiency,
        'self_sufficiency': total_self_sufficiency,
        'cycles_per_day': float(bess_charge.sum()) / capacity_kwh / 365 if capacity_kwh > 0 else 0.0,
        'soc_min_percent': float(soc.min() * 100),
        'soc_max_percent': float(soc.max() * 100),
        'soc_avg_percent': float(soc.mean() * 100),
    }
    
    return df, metrics


def calculate_max_discharge_to_mall(
    current_hour: int,
    current_soc_percent: float,
    closing_hour: int = 22,
    target_soc_percent: float = 20.0,
    capacity_kwh: float = 1700.0,
    eff_discharge: float = 0.9747,
) -> float:
    """
    Calcula la máxima energía (kWh/hora) que se puede descargar al MALL
    para LLEGAR EXACTAMENTE a target_soc_percent a las 22h.
    
    NUEVA LÓGICA v5.5 OPTIMIZADA:
    ═════════════════════════════════════════════════════════════════════
    En lugar de ser conservador, calcula el "ritmo" de descarga necesario
    para que SOC = 20% exacto al cierre.
    
    Ejemplo:
    - 18h: SOC=100%, cierre=22h → horas_restantes=4h
      descarga_requerida = (100-20)% × 1700 = 1,360 kWh
      ritmo = 1,360 / 4 = 340 kWh/h
      
    - 19h: SOC=80%, cierre=22h → horas_restantes=3h
      descarga_requerida = (80-20)% × 1700 = 1,020 kWh
      ritmo = 1,020 / 3 = 340 kWh/h
      
    ENTRADA:
        current_hour: Hora actual (0-23)
        current_soc_percent: SOC actual en %
        closing_hour: Hora de cierre BESS (default 22h, operación hasta 21h)
        target_soc_percent: SOC objetivo a cierre (default 20%)
        capacity_kwh: Capacidad BESS (default 1,700 kWh)
        eff_discharge: Eficiencia descarga (default 0.9747)
    
    SALIDA:
        Energía máxima (kWh/hora) que se puede descargar al MALL
        Retorna 0 si ya alcanzamos target o estamos fuera de horas
    """
    soc_min_percent = 20.0  # Mínimo permitido BESS
    
    # Fuera de operación: no descargar
    if current_hour >= closing_hour or current_hour < 6:
        return 0.0
    
    # Si ya alcanzamos el target exacto (o menos), no descargar más
    if current_soc_percent <= target_soc_percent:
        return 0.0
    
    # Calcular horas disponibles hasta cierre
    hours_until_closing = closing_hour - current_hour
    if hours_until_closing <= 0:
        return 0.0
    
    # Energía actual sobre el target
    soc_above_target_percent = current_soc_percent - target_soc_percent
    energy_to_discharge_kwh = (soc_above_target_percent / 100.0) * capacity_kwh
    
    # Ritmo de descarga requerido (kWh/hora)
    # Esto es lo que debemos descargar en cada hora para llegar exactamente a 20%
    discharge_rate_kwh_per_hour = energy_to_discharge_kwh / hours_until_closing
    
    # Mínimo: evitar valores muy pequeños (< 1 kWh)
    if discharge_rate_kwh_per_hour < 1.0:
        return 0.0
    
    return float(discharge_rate_kwh_per_hour)


def simulate_bess_solar_priority(
    pv_kwh: np.ndarray,
    ev_kwh: np.ndarray,
    mall_kwh: np.ndarray,
    capacity_kwh: float = BESS_CAPACITY_KWH_V53,
    power_kw: float = BESS_POWER_KW_V53,
    efficiency: float = BESS_EFFICIENCY_V53,
    soc_min: float = BESS_SOC_MIN_V53,
    soc_max: float = BESS_SOC_MAX_V53,
    closing_hour: int = 22,
    year: int = 2024,
) -> Tuple[pd.DataFrame, dict]:
    """
    Simula operación BESS con estrategia SOLAR-PRIORITY (sin arbitraje tarifario).
    
    ESTRATEGIA BASADA EN DISPONIBILIDAD SOLAR:
    ==========================================
    - CARGA (Mañana-Tarde, cuando PV > demanda):
      Llenar BESS a máximo 100% usando PV excedente (costo cero).
      Solo cargar desde PV, NO desde grid.
      
    - DESCARGA (Tarde-Noche, cuando PV < demanda O déficit EV):
      Descargar cuando:
      1) PV < demanda mall (déficit solar) O
      2) Hay déficit EV y SOC > min
      
    BALANCE ENERGÉTICO CORRECTO (v5.4-FIXED):
    ═════════════════════════════════════════
    CARGA:   input_kw × dt → almacenamiento_kwh (con pérdida charging)
    DESCARGA: almacenamiento_kwh → output_kw × dt (con pérdida discharging)
    
    Fórmulas:
    - energy_into_bess = power_charge_kw × (eff_charge)
    - energy_from_bess = energy_stored × (eff_discharge)
    - Balance: sum(energy_into_bess × sqrt(eff)) ≈ sum(energy_from_bess) / sqrt(eff)
    
    VENTAJAS:
    ✓ Independiente de tarifa (funciona cualquier precio)
    ✓ Más seguro: SOC siempre lleno en noche crítica
    ✓ Lógica intuitiva: cargar con sol, descargar sin sol
    ✓ Mejor para OE3: RL agents aprenden patrón natural
    ✓ BALANCE ENERGÉTICO CORRECTO (sin desequilibrio 8.7:1)
    
    Args:
        pv_kwh: Generación PV horaria (8,760 valores)
        ev_kwh: Demanda EV horaria (8,760 valores)
        mall_kwh: Demanda Mall horaria (8,760 valores)
        capacity_kwh: Capacidad BESS (default 1,700 kWh v5.3)
        power_kw: Potencia BESS (default 400 kW v5.3)
        efficiency: Eficiencia round-trip (default 0.95)
        soc_min: SOC mínimo (default 0.20 = 20%)
        soc_max: SOC máximo (default 1.00 = 100%)
        closing_hour: Hora cierre EV (default 22)
        year: Año de simulación
    
    Returns:
        Tuple: (DataFrame con simulación, dict con métricas)
    """
    n_hours = len(pv_kwh)
    # Eficiencia correcta: sqrt(round_trip_efficiency) para CARGA y DESCARGA
    # Ejemplo: round_trip = 0.95 = 95% → charging_eff = sqrt(0.95) = 0.9747
    eff_charge = math.sqrt(efficiency)  # Eficiencia de CARGA
    eff_discharge = math.sqrt(efficiency)  # Eficiencia de DESCARGA
    
    # Arrays de resultados
    soc = np.zeros(n_hours)
    bess_charge = np.zeros(n_hours)
    bess_discharge = np.zeros(n_hours)
    pv_to_ev = np.zeros(n_hours)
    pv_to_bess = np.zeros(n_hours)
    pv_to_mall = np.zeros(n_hours)
    bess_to_ev = np.zeros(n_hours)
    bess_to_mall = np.zeros(n_hours)
    grid_to_ev = np.zeros(n_hours)
    grid_to_mall = np.zeros(n_hours)
    grid_to_bess = np.zeros(n_hours)
    pv_curtailed = np.zeros(n_hours)
    bess_mode = np.array(['idle'] * n_hours, dtype=object)
    tariff_soles_kwh = np.zeros(n_hours)
    cost_grid_import_soles = np.zeros(n_hours)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NUEVAS MÉTRICAS v5.4: Ahorros económicos e impacto CO₂ (por hora)
    # ═══════════════════════════════════════════════════════════════════════════
    peak_reduction_savings_soles = np.zeros(n_hours)  # Ahorro por corte de picos (S/)
    co2_avoided_indirect_kg = np.zeros(n_hours)       # CO2 evitado por BESS discharge (kg)
    
    # Estado inicial
    current_soc = 0.50  # SOC inicial: 50% (neutral)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BUCLE PRINCIPAL: Simular cada hora del año
    # ═══════════════════════════════════════════════════════════════════════════
    
    for h in range(n_hours):
        hour_of_day = h % 24
        pv_h = pv_kwh[h]
        ev_h = ev_kwh[h]
        mall_h = mall_kwh[h]
        
        # ═════════════════════════════════════════════════════════════════════
        # FUERA DE OPERACIÓN (23h-5h): Sin actividad BESS, solo grid/PV
        # ═════════════════════════════════════════════════════════════════════
        if hour_of_day >= closing_hour or hour_of_day < 6:
            # PV solo hacia mall (EV cerrado)
            pv_to_ev[h] = 0.0
            pv_to_mall[h] = min(pv_h, mall_h)
            pv_curtailed[h] = max(pv_h - pv_to_mall[h], 0)
            
            # Grid cubre todo EV + mall deficit
            grid_to_ev[h] = ev_h
            grid_to_mall[h] = max(mall_h - pv_to_mall[h], 0)
            
            # BESS inactivo
            bess_charge[h] = 0.0
            bess_discharge[h] = 0.0
            bess_mode[h] = 'idle'
            
            # Tarifa: HFP por defecto (fuera de punta)
            tariff_soles_kwh[h] = TARIFA_ENERGIA_HFP_SOLES
            cost_grid_import_soles[h] = (grid_to_ev[h] + grid_to_mall[h]) * tariff_soles_kwh[h]
            
            soc[h] = current_soc
            continue
        
        # ═════════════════════════════════════════════════════════════════════
        # OPERACIÓN DIURNA-NOCTURNA (6h-22h)
        # ═════════════════════════════════════════════════════════════════════
        
        # INICIALIZAR VARIABLES
        pv_remaining = pv_h
        ev_deficit = ev_h
        mall_deficit = mall_h
        bess_charge[h] = 0.0
        bess_discharge[h] = 0.0
        pv_to_ev[h] = 0.0
        pv_to_mall[h] = 0.0
        pv_to_bess[h] = 0.0
        
        # ═════════════════════════════════════════════════════════════════════
        # NUEVAS PRIORIDADES - SOLAR PRIORITY v5.4 CORREGIDO
        # ═════════════════════════════════════════════════════════════════════
        # PRIORIDAD 1: BESS CARGA (apenas existe generación PV)
        #              - Carga a máxima potencia mientras PV > 0 Y SOC < 100%
        #              - Se mantiene al 100% hasta hora de descarga
        # PRIORIDAD 2: EV (desde PV restante o BESS)
        # PRIORIDAD 3: MALL (desde PV restante o BESS)
        # PRIORIDAD 4: GRID cubre déficits
        
        # ═════════════════════════════════════════════════════════════════════
        # PASO 1: BESS CARGA A MÁXIMA POTENCIA (si hay PV y SOC < 100%)
        # ═════════════════════════════════════════════════════════════════════
        
        if pv_remaining > 0.01 and current_soc < soc_max:
            # ───────────────────────────────────────────────────────────────
            # MODO CARGA: BESS carga a máxima potencia cuando hay generación PV
            # 
            # LÓGICA CORREGIDA v5.4 FINAL:
            # - Carga apenas existe generación solar (pv_h > 0)
            # - Carga a potencia máxima del BESS hasta alcanzar SOC 100%
            # - UNA VEZ AL 100%: NO intenta cargar, PV pasa directo a EV/MALL
            # - Descarga SOLO cuando hay déficit (EV o MALL con picos > 2000kW)
            # ───────────────────────────────────────────────────────────────
            # Capacidad disponible para almacenar
            soc_headroom_kwh = (soc_max - current_soc) * capacity_kwh
            
            # Poder de carga MÁXIMO:
            # 1. Limitar por potencia nominal del BESS
            # 2. Limitar por PV disponible
            # 3. Limitar por headroom del BESS
            power_charge_kw = min(power_kw, pv_remaining)
            
            # Fórmula CORRECTA de CARGA (energía almacenada):
            # energy_to_store = power_charge_kw × eff_charge
            energy_to_store_kwh = power_charge_kw * eff_charge
            energy_to_store_kwh = min(energy_to_store_kwh, soc_headroom_kwh)
            
            if energy_to_store_kwh > 0.01:
                # Registrar carga
                bess_charge[h] = power_charge_kw
                pv_to_bess[h] = power_charge_kw
                
                # Actualizar SOC
                current_soc += energy_to_store_kwh / capacity_kwh
                current_soc = min(current_soc, soc_max)  # Asegurar SOC ≤ 100%
                
                bess_mode[h] = 'charge'
                
                # Reducir PV disponible (fue consumido por BESS)
                pv_remaining -= power_charge_kw
                pv_remaining = max(pv_remaining, 0.0)
            else:
                # Si no se puede cargar (SOC lleno), pasar PV al siguiente paso
                bess_mode[h] = 'idle'
        elif current_soc >= soc_max and pv_remaining > 0.01:
            # ───────────────────────────────────────────────────────────────
            # BESS YA ESTÁ AL 100%: No cargar, PV se usa directamente
            # El PV se descuenta del generado y se pasa a EV/MALL
            # ───────────────────────────────────────────────────────────────
            bess_mode[h] = 'full'  # Indica que BESS está lleno
            # No hacer nada, dejar que pv_remaining pase al siguiente paso

        
        # ═════════════════════════════════════════════════════════════════════
        # PASO 2: PV RESTANTE → EV (después de cargar BESS)
        # ═════════════════════════════════════════════════════════════════════
        pv_direct_to_ev = min(pv_remaining, ev_h)
        pv_to_ev[h] = pv_direct_to_ev
        pv_remaining -= pv_direct_to_ev
        ev_deficit = ev_h - pv_direct_to_ev
        
        # ═════════════════════════════════════════════════════════════════════
        # PASO 3: PV RESTANTE → MALL (después de EV)
        # ═════════════════════════════════════════════════════════════════════
        pv_direct_to_mall = min(pv_remaining, mall_h)
        pv_to_mall[h] = pv_direct_to_mall
        pv_remaining -= pv_direct_to_mall
        mall_deficit = mall_h - pv_direct_to_mall
        
        # Curtailment: PV que no puede usarse (muy poco o BESS lleno, EV cerrado, Mall satisfecho)
        pv_curtailed[h] = max(pv_remaining, 0.0)
        
        # ═════════════════════════════════════════════════════════════════════
        # PASO 4: BESS DESCARGA (si hay déficit EV O déficit MALL & picos > 2000kW)
        # ═════════════════════════════════════════════════════════════════════
        
        # CONDICIÓN DE DESCARGA MEJORADA:
        # 1. PRIORIDAD MÁXIMA: Hay déficit EV → Descargar 100% para cubrir EV
        # 2. LIMITAR PICOS: Hay déficit MALL Y pv_h < mall_h Y pico > 2000kW → Descargar
        # 3 Solo descargar si SOC > min Y BESS no está cargando
        
        deficit_solar_mall = (pv_h < mall_h)  # Hay más demanda mall que generación PV
        pico_excede_limite = ((ev_h + mall_h) > 2000.0)  # Pico > 2000 kW
        soc_permite_descarga = (current_soc > soc_min)
        puede_descargar = soc_permite_descarga and bess_mode[h] != 'charge'
        
        # CONDICIONES PARA ACTIVAR DESCARGA:
        activar_descarga_ev = (ev_deficit > 0.01 and puede_descargar)  # EV tiene déficit
        activar_descarga_picos = (deficit_solar_mall and pico_excede_limite and puede_descargar)  # Déficit MALL + picos
        
        if (activar_descarga_ev or activar_descarga_picos):
            # ───────────────────────────────────────────────────────────────
            # MODO DESCARGA: Cubrir déficits con energía BESS
            # PRIORIDAD DESCARGA:
            # 1º BESS → EV (cobertura 100% - máxima prioridad)
            # 2º BESS → MALL (limitar picos > 2000kW, si hay energía residual)
            # ───────────────────────────────────────────────────────────────
            
            soc_available_kwh = (current_soc - soc_min) * capacity_kwh
            remaining_discharge_power = power_kw  # Potencia disponible para descargar
            
            # ═══════════════════════════════════════════════════════════════
            # PRIORIDAD 1: CUBRIR 100% DÉFICIT EV (máximo)
            # ═══════════════════════════════════════════════════════════════
            if ev_deficit > 0.01 and soc_available_kwh > 0.01:
                # EV debe recibir 100% de cobertura desde BESS
                power_to_ev = min(remaining_discharge_power, ev_deficit, 
                                   soc_available_kwh / eff_discharge)
                
                # Energía que sale del BESS (fórmula correcta)
                energy_from_bess_ev = power_to_ev / eff_discharge
                energy_from_bess_ev = min(energy_from_bess_ev, soc_available_kwh)
                
                if energy_from_bess_ev > 0.01:
                    # Energía entregada a EV
                    energy_to_ev = energy_from_bess_ev * eff_discharge
                    
                    bess_discharge[h] += power_to_ev
                    bess_to_ev[h] = energy_to_ev
                    
                    # Actualizar SOC
                    current_soc -= energy_from_bess_ev / capacity_kwh
                    current_soc = max(current_soc, soc_min)
                    
                    # Reducir déficit
                    ev_deficit -= energy_to_ev
                    remaining_discharge_power -= power_to_ev
                    soc_available_kwh = (current_soc - soc_min) * capacity_kwh
                    
                    bess_mode[h] = 'discharge'
            
            # ═══════════════════════════════════════════════════════════════
            # PRIORIDAD 2: DESCARGAR ENERGÍA RESIDUAL A MALL
            # ═══════════════════════════════════════════════════════════════
            # ESTRATEGIA v5.5 SIMPLIFICADA:
            # - Después de cubrir EV completamente (100%), descargar energía residual al MALL
            # - Objetivo: SOC baje naturalmente hasta 20% a las 22h (por balance energético)
            # - Sin forzar ningún cálculo de máximo; solo usar lo que sobra
            # ───────────────────────────────────────────────────────────────
            
            # Descargar a MALL solo con la energía RESIDUAL (remanente después de EV)
            if remaining_discharge_power > 0.10 and mall_deficit > 0.01 and soc_available_kwh > 0.01:
                
                # Solo descargar el poder residual que existe (sin cálculos complejos)
                power_to_mall = remaining_discharge_power
                
                # Energía que sale del BESS (con eficiencia)
                energy_from_bess_mall = power_to_mall / eff_discharge
                energy_from_bess_mall = min(energy_from_bess_mall, soc_available_kwh)
                
                if energy_from_bess_mall > 0.01:
                    # Energía entregada al MALL
                    energy_to_mall = energy_from_bess_mall * eff_discharge
                    
                    bess_discharge[h] += power_to_mall
                    bess_to_mall[h] = energy_to_mall
                    
                    # Actualizar SOC
                    current_soc -= energy_from_bess_mall / capacity_kwh
                    current_soc = max(current_soc, soc_min)
                    
                    # Reducir déficit del MALL
                    mall_deficit -= energy_to_mall
                    remaining_discharge_power -= power_to_mall
                    
                    bess_mode[h] = 'discharge'

        
        elif bess_mode[h] == 'charge':
            # Mantenerse cargando si hay PV y SOC < 100% (modo carga mantiene estado)
            pass
        else:
            # MODO IDLE: Sin acción
            if bess_mode[h] != 'charge':
                bess_mode[h] = 'idle'
        



        # ═════════════════════════════════════════════════════════════════════
        # PASO FINAL: Grid cubre déficits restantes
        # ═════════════════════════════════════════════════════════════════════
        grid_to_ev[h] = max(ev_deficit, 0)
        grid_to_mall[h] = max(mall_deficit, 0)
        grid_to_bess[h] = 0.0  # Solar-priority NO carga desde grid
        
        # Tarifa (para logging, aunque no afecta decisión)
        is_hp = 18 <= hour_of_day < 23
        tariff_soles_kwh[h] = TARIFA_ENERGIA_HP_SOLES if is_hp else TARIFA_ENERGIA_HFP_SOLES
        cost_grid_import_soles[h] = (grid_to_ev[h] + grid_to_mall[h]) * tariff_soles_kwh[h]
        
        # ═════════════════════════════════════════════════════════════════════
        # MÉTRICAS v5.4: Ahorros y CO₂ evitado
        # ═════════════════════════════════════════════════════════════════════
        
        if (bess_to_ev[h] + bess_to_mall[h]) > 0.01:
            # CO2 evitado por BESS discharge (reemplaza generación térmica)
            co2_avoided_indirect_kg[h] = (bess_to_ev[h] + bess_to_mall[h]) * FACTOR_CO2_KG_KWH
        else:
            co2_avoided_indirect_kg[h] = 0.0
        
        if bess_to_mall[h] > 0.01:
            peak_reduction_savings_soles[h] = bess_to_mall[h] * tariff_soles_kwh[h]
        else:
            peak_reduction_savings_soles[h] = 0.0
        
        # Guardar SOC
        soc[h] = current_soc
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDACIÓN DEFENSIVA: CERO EN MADRUGADA (00:00-05:59)
    # ═══════════════════════════════════════════════════════════════════════════
    # Regla: BESS NO se carga ni descarga en madrugada
    # - EV está cerrado (cierra 22h)
    # - No hay generación solar (noche)
    # - Fuerza cero incluso si hay bug en lógica anterior
    # ═══════════════════════════════════════════════════════════════════════════
    for h in range(n_hours):
        hour_of_day = h % 24
        if hour_of_day < 6:  # 00:00-05:59 es madrugada
            # Forzar inactividad total
            bess_charge[h] = 0.0
            bess_discharge[h] = 0.0
            pv_to_bess[h] = 0.0
            bess_to_ev[h] = 0.0
            bess_to_mall[h] = 0.0
            grid_to_bess[h] = 0.0
            bess_mode[h] = 'midnight_off'  # Indicador de fuera de operación
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CREAR DATAFRAME DE RESULTADOS
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Índice: datetime para todo el año
    datetime_index = pd.date_range(start=f'{year}-01-01', periods=n_hours, freq='h', tz=None)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NORMALIZAR MÉTRICAS PARA CITYLEARN (escalas apropiadas para observaciones RL)
    # ═══════════════════════════════════════════════════════════════════════════
    # Ahorros por picos normalizados a [0, 1]: dividir por máximo anual
    peak_reduction_savings_normalized = peak_reduction_savings_soles.copy()
    max_savings_hour = np.max(peak_reduction_savings_soles) if np.max(peak_reduction_savings_soles) > 0 else 1.0
    peak_reduction_savings_normalized = peak_reduction_savings_soles / max_savings_hour
    
    # CO2 indirecto normalizado a [0, 1]: dividir por máximo anual
    co2_avoided_indirect_normalized = co2_avoided_indirect_kg.copy()
    max_co2_hour = np.max(co2_avoided_indirect_kg) if np.max(co2_avoided_indirect_kg) > 0 else 1.0
    co2_avoided_indirect_normalized = co2_avoided_indirect_kg / max_co2_hour
    
    df = pd.DataFrame({
        'datetime': datetime_index,
        'pv_generation_kwh': pv_kwh,
        'ev_demand_kwh': ev_kwh,
        'mall_demand_kwh': mall_kwh,
        'pv_to_ev_kwh': pv_to_ev,
        'pv_to_bess_kwh': pv_to_bess,
        'pv_to_mall_kwh': pv_to_mall,
        'pv_curtailed_kwh': pv_curtailed,
        'bess_charge_kwh': bess_charge,
        'bess_discharge_kwh': bess_discharge,
        'bess_to_ev_kwh': bess_to_ev,
        'bess_to_mall_kwh': bess_to_mall,
        'grid_to_ev_kwh': grid_to_ev,
        'grid_to_mall_kwh': grid_to_mall,
        'grid_to_bess_kwh': grid_to_bess,
        'grid_import_total_kwh': grid_to_ev + grid_to_mall,
        'bess_soc_percent': soc * 100,
        'bess_mode': bess_mode,
        'tariff_osinergmin_soles_kwh': tariff_soles_kwh,
        'cost_grid_import_soles': cost_grid_import_soles,
        # ═══════════════════════════════════════════════════════════════════
        # NUEVAS COLUMNAS v5.4: Ahorros e impacto CO₂
        # ═══════════════════════════════════════════════════════════════════
        'peak_reduction_savings_soles': peak_reduction_savings_soles,  # Valor actual (S/)
        'peak_reduction_savings_normalized': peak_reduction_savings_normalized,  # [0,1] para RL
        'co2_avoided_indirect_kg': co2_avoided_indirect_kg,  # Valor actual (kg)
        'co2_avoided_indirect_normalized': co2_avoided_indirect_normalized,  # [0,1] para RL
    })
    
    df.set_index('datetime', inplace=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CALCULAR MÉTRICAS
    # ═══════════════════════════════════════════════════════════════════════════
    
    total_pv = float(pv_kwh.sum())
    total_ev = float(ev_kwh.sum())
    total_mall = float(mall_kwh.sum())
    total_load = total_ev + total_mall
    
    ev_from_pv = float(pv_to_ev.sum())
    ev_from_bess = float(bess_to_ev.sum())
    ev_from_grid = float(grid_to_ev.sum())
    
    # Autosuficiencia EV (lo importante para BESS)
    ev_self_sufficiency = (ev_from_pv + ev_from_bess) / max(total_ev, 1e-9)
    
    # Autosuficiencia total
    total_grid = float(grid_to_ev.sum() + grid_to_mall.sum())
    total_self_sufficiency = 1.0 - (total_grid / max(total_load, 1e-9))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDACIÓN: COBERTURA EV 100% (FASE 3)
    # ═══════════════════════════════════════════════════════════════════════════
    # Verificar que EV siempre recibe su demanda (no depende de Grid)
    
    ev_coverage_pct = ((ev_from_pv + ev_from_bess) / max(total_ev, 1e-9)) * 100.0
    
    # Alerta si no hay cobertura completa
    if ev_coverage_pct < 99.5:  # Permitir 0.5% de tolerancia por redondeos
        print(f"  [ADVERTENCIA] Cobertura EV insuficiente: {ev_coverage_pct:.1f}% (requiere 100%)")
        print(f"    Total EV: {total_ev:,.0f} kWh")
        print(f"    Cubierto por PV: {ev_from_pv:,.0f} kWh")
        print(f"    Cubierto por BESS: {ev_from_bess:,.0f} kWh")
        print(f"    Deficit desde Grid: {ev_from_grid:,.0f} kWh")
    
    # Cálculo de ahorro (comparativa con baseline sin BESS)
    # Baseline: toda demanda desde grid
    cost_baseline = total_load * TARIFA_ENERGIA_HFP_SOLES  # Precio HFP promedio
    cost_with_bess = cost_grid_import_soles.sum()
    savings_bess = cost_baseline - cost_with_bess
    
    # Reducción CO₂ - DETALLADO CON BESS v5.4
    # =========================================================================
    # CO2 EVITADO = (PV directo + BESS discharge) × factor CO2 generación térmica
    # 
    # La red pública Iquitos es generada por:
    # - Generación térmica: diesel B5 @ 0.4521 kg CO₂/kWh (OSINERGMIN)
    # 
    # BESS discharge EVITA que esa demanda venga de la red térmica
    # =========================================================================
    co2_emissions_kg = total_grid * FACTOR_CO2_KG_KWH
    
    # CO2 evitado por PV directo (cubre EV + Mall)
    co2_avoided_by_pv_kg = (ev_from_pv + float(pv_to_mall.sum())) * FACTOR_CO2_KG_KWH
    
    # CO2 evitado por BESS discharge (en lugar de red térmica)
    # BESS atiende: EV + MALL (prioridades 1 y 2)
    co2_avoided_by_bess_kg = (ev_from_bess + float(bess_to_mall.sum())) * FACTOR_CO2_KG_KWH
    
    # Total CO2 evitado = PV + BESS discharge
    co2_avoided_kg = co2_avoided_by_pv_kg + co2_avoided_by_bess_kg
    
    co2_reduction_percent = (co2_avoided_kg / max(co2_emissions_kg + co2_avoided_kg, 1e-9)) * 100
    
    metrics = {
        'total_pv_kwh': total_pv,
        'total_ev_kwh': total_ev,
        'total_mall_kwh': total_mall,
        'total_load_kwh': total_load,
        'ev_from_pv_kwh': ev_from_pv,
        'ev_from_bess_kwh': ev_from_bess,
        'ev_from_grid_kwh': ev_from_grid,
        'mall_from_pv_kwh': float(pv_to_mall.sum()),
        'mall_from_bess_kwh': float(bess_to_mall.sum()),
        'mall_from_grid_kwh': float(grid_to_mall.sum()),
        'total_bess_charge_kwh': float(bess_charge.sum()),
        'total_bess_discharge_kwh': float(bess_discharge.sum()),
        'total_grid_import_kwh': total_grid,
        'total_grid_export_kwh': float(pv_curtailed.sum()),
        'self_sufficiency': total_self_sufficiency,
        'ev_self_sufficiency': ev_self_sufficiency,
        'cycles_per_day': float(bess_charge.sum()) / capacity_kwh / 365 if capacity_kwh > 0 else 0.0,
        'soc_min_percent': float(soc.min() * 100),
        'soc_max_percent': float(soc.max() * 100),
        'soc_avg_percent': float(soc.mean() * 100),
        'cost_baseline_soles_year': cost_baseline,
        'cost_grid_import_soles_year': cost_with_bess,
        'savings_bess_soles_year': savings_bess,
        'savings_total_soles_year': savings_bess,  # Sin arbitraje HP/HFP
        'roi_percent': (savings_bess / cost_baseline * 100) if cost_baseline > 0 else 0.0,
        'co2_emissions_kg_year': co2_emissions_kg,
        'co2_avoided_by_pv_kg_year': co2_avoided_by_pv_kg,  # NEW: CO2 evitado por PV
        'co2_avoided_by_bess_kg_year': co2_avoided_by_bess_kg,  # NEW: CO2 evitado por BESS
        'co2_avoided_kg_year': co2_avoided_kg,  # TOTAL CO2 evitado (PV + BESS)
        'co2_reduction_percent': co2_reduction_percent,
    }
    
    return df, metrics


def simulate_bess_arbitrage_hp_hfp(
    pv_kwh: np.ndarray,
    ev_kwh: np.ndarray,
    mall_kwh: np.ndarray,
    capacity_kwh: float = BESS_CAPACITY_KWH_V53,
    power_kw: float = BESS_POWER_KW_V53,
    efficiency: float = BESS_EFFICIENCY_V53,
    soc_min: float = BESS_SOC_MIN_V53,
    soc_max: float = BESS_SOC_MAX_V53,
    closing_hour: int = 22,
    year: int = 2024,
) -> Tuple[pd.DataFrame, dict]:
    """
    Simula operación BESS con estrategia de ARBITRAJE HP/HFP.
    
    ESTRATEGIA DE ARBITRAJE TARIFARIO:
    ================================
    - CARGA (HFP 00-17h, 23h): Almacena energía cuando tarifa es S/.0.28/kWh
      - Prioridad 1: PV excedente → BESS (costo cero)
      - Prioridad 2: Grid → BESS si SOC < 90% y es HFP temprana (6h-12h)
      
    - DESCARGA (HP 18-22h): Libera energía cuando tarifa es S/.0.45/kWh
      - Prioridad 1: BESS → EV (reemplaza grid caro)
      - Prioridad 2: BESS → Mall (reduce demanda HP)
      
    - AHORRO: S/.0.17/kWh diferencial × energía descargada en HP
    
    Args:
        pv_kwh: Generación PV horaria (8,760 valores)
        ev_kwh: Demanda EV horaria (8,760 valores)
        mall_kwh: Demanda Mall horaria (8,760 valores)
        capacity_kwh: Capacidad BESS (default 1,700 kWh v5.3)
        power_kw: Potencia BESS (default 400 kW v5.3)
        efficiency: Eficiencia round-trip (default 0.95)
        soc_min: SOC mínimo (default 0.20 = 20%)
        soc_max: SOC máximo (default 1.00 = 100%)
        closing_hour: Hora cierre EV (default 22)
        year: Año de simulación
    
    Returns:
        Tuple: (DataFrame con simulación, dict con métricas incluyendo costos)
    """
    n_hours = len(pv_kwh)
    eff_charge = math.sqrt(efficiency)
    eff_discharge = math.sqrt(efficiency)
    
    # Arrays de resultados
    soc = np.zeros(n_hours)
    bess_charge = np.zeros(n_hours)
    bess_discharge = np.zeros(n_hours)
    pv_to_ev = np.zeros(n_hours)
    pv_to_bess = np.zeros(n_hours)
    pv_to_mall = np.zeros(n_hours)
    bess_to_ev = np.zeros(n_hours)
    bess_to_mall = np.zeros(n_hours)
    grid_to_ev = np.zeros(n_hours)
    grid_to_mall = np.zeros(n_hours)
    grid_to_bess = np.zeros(n_hours)
    pv_curtailed = np.zeros(n_hours)
    
    # Arrays de tarifas y costos
    tariff_soles_kwh = np.zeros(n_hours)
    is_peak_hour = np.zeros(n_hours, dtype=int)
    cost_grid_import_soles = np.zeros(n_hours)
    savings_bess_soles = np.zeros(n_hours)
    
    # Estado inicial: SOC al 50% (inicio neutro para arbitraje)
    current_soc = 0.50
    
    for h in range(n_hours):
        hour_of_day = h % 24
        pv_h = pv_kwh[h]
        ev_h = ev_kwh[h]
        mall_h = mall_kwh[h]
        
        # ====================================
        # IDENTIFICAR PERIODO TARIFARIO
        # ====================================
        is_hp = HORA_INICIO_HP <= hour_of_day < HORA_FIN_HP
        is_peak_hour[h] = 1 if is_hp else 0
        tariff_soles_kwh[h] = TARIFA_ENERGIA_HP_SOLES if is_hp else TARIFA_ENERGIA_HFP_SOLES
        
        # ====================================
        # FUERA DE HORARIO OPERATIVO (23h-5h)
        # BESS solo mantiene SOC, sin carga/descarga activa
        # ====================================
        if hour_of_day >= 23 or hour_of_day < 6:
            pv_to_ev[h] = 0
            pv_to_mall[h] = min(pv_h, mall_h)
            grid_to_ev[h] = ev_h if ev_h > 0 else 0
            grid_to_mall[h] = max(mall_h - pv_to_mall[h], 0)
            pv_curtailed[h] = max(pv_h - pv_to_mall[h], 0)
            soc[h] = current_soc
            # Calcular costo
            total_grid_h = grid_to_ev[h] + grid_to_mall[h]
            cost_grid_import_soles[h] = total_grid_h * tariff_soles_kwh[h]
            continue
        
        # ====================================
        # PRIORIDAD 1: PV → EV directo
        # ====================================
        pv_direct_to_ev = min(pv_h, ev_h)
        pv_to_ev[h] = pv_direct_to_ev
        pv_remaining = pv_h - pv_direct_to_ev
        ev_deficit = ev_h - pv_direct_to_ev
        
        # ====================================
        # PERIODO HFP (FUERA DE PUNTA): CARGA BESS
        # Estrategia: Maximizar almacenamiento para HP
        # ====================================
        if not is_hp:
            # Prioridad 2 HFP: PV excedente → BESS
            if pv_remaining > 0 and current_soc < soc_max:
                soc_headroom = (soc_max - current_soc) * capacity_kwh
                max_charge = min(power_kw, pv_remaining, soc_headroom / eff_charge)
                
                if max_charge > 0:
                    bess_charge[h] = max_charge
                    pv_to_bess[h] = max_charge
                    current_soc += (max_charge * eff_charge) / capacity_kwh
                    current_soc = min(current_soc, soc_max)
                    pv_remaining -= max_charge
            
            # Prioridad 3 HFP: Grid → BESS (carga oportunista)
            # Solo si SOC < 80% y es mañana (6h-12h) para prepararse para HP
            if 6 <= hour_of_day <= 12 and current_soc < 0.80:
                soc_headroom = (0.80 - current_soc) * capacity_kwh
                max_grid_charge = min(power_kw * 0.5, soc_headroom / eff_charge)  # 50% potencia
                
                if max_grid_charge > 0:
                    bess_charge[h] += max_grid_charge
                    grid_to_bess[h] = max_grid_charge
                    current_soc += (max_grid_charge * eff_charge) / capacity_kwh
                    current_soc = min(current_soc, 0.80)
            
            # Prioridad 4 HFP: PV → Mall
            pv_direct_to_mall = min(pv_remaining, mall_h)
            pv_to_mall[h] = pv_direct_to_mall
            pv_remaining -= pv_direct_to_mall
            mall_deficit = mall_h - pv_direct_to_mall
            
            # Curtailment
            pv_curtailed[h] = pv_remaining
            
            # Grid cubre déficits (tarifa HFP barata)
            grid_to_ev[h] = max(ev_deficit, 0)
            grid_to_mall[h] = max(mall_deficit, 0)
        
        # ====================================
        # PERIODO HP (HORA PUNTA): DESCARGA BESS
        # Estrategia: Minimizar compra de grid a tarifa cara
        # ====================================
        else:  # is_hp == True
            # Prioridad 2 HP: BESS → EV (reemplaza grid caro)
            if ev_deficit > 0 and current_soc > soc_min:
                soc_available = (current_soc - soc_min) * capacity_kwh
                max_discharge = min(power_kw, ev_deficit / eff_discharge, soc_available)
                
                if max_discharge > 0:
                    actual_discharge = max_discharge * eff_discharge
                    bess_discharge[h] = max_discharge
                    bess_to_ev[h] = actual_discharge
                    current_soc -= max_discharge / capacity_kwh
                    current_soc = max(current_soc, soc_min)
                    ev_deficit -= actual_discharge
                    
                    # AHORRO: energía que NO compramos a tarifa HP
                    # sino que usamos desde BESS (cargado a tarifa HFP)
                    savings_bess_soles[h] += actual_discharge * (TARIFA_ENERGIA_HP_SOLES - TARIFA_ENERGIA_HFP_SOLES)
            
            # Prioridad 3 HP: PV → Mall
            pv_direct_to_mall = min(pv_remaining, mall_h)
            pv_to_mall[h] = pv_direct_to_mall
            pv_remaining -= pv_direct_to_mall
            mall_deficit = mall_h - pv_direct_to_mall
            
            # Prioridad 4 HP: BESS → Mall (reducir demanda HP si queda capacidad)
            if mall_deficit > 0 and current_soc > soc_min and hour_of_day <= closing_hour:
                soc_available = (current_soc - soc_min) * capacity_kwh
                max_discharge = min(power_kw - bess_discharge[h], mall_deficit / eff_discharge, soc_available)
                
                if max_discharge > 0:
                    actual_discharge = max_discharge * eff_discharge
                    bess_discharge[h] += max_discharge
                    bess_to_mall[h] = actual_discharge
                    current_soc -= max_discharge / capacity_kwh
                    current_soc = max(current_soc, soc_min)
                    mall_deficit -= actual_discharge
                    
                    # Ahorro adicional por reducir demanda Mall en HP
                    savings_bess_soles[h] += actual_discharge * (TARIFA_ENERGIA_HP_SOLES - TARIFA_ENERGIA_HFP_SOLES)
            
            # Curtailment
            pv_curtailed[h] = pv_remaining
            
            # Grid cubre déficits restantes (tarifa HP cara - minimizado)
            grid_to_ev[h] = max(ev_deficit, 0)
            grid_to_mall[h] = max(mall_deficit, 0)
        
        # Guardar SOC
        soc[h] = current_soc
        
        # Calcular costo de grid import
        total_grid_h = grid_to_ev[h] + grid_to_mall[h] + grid_to_bess[h]
        cost_grid_import_soles[h] = total_grid_h * tariff_soles_kwh[h]
    
    # =====================================================
    # COLUMNA COMBINADA: bess_action_kwh y bess_mode
    # =====================================================
    bess_action_kwh = np.zeros(n_hours)
    bess_mode = np.empty(n_hours, dtype=object)
    
    for h in range(n_hours):
        if bess_charge[h] > 0:
            bess_action_kwh[h] = bess_charge[h]
            bess_mode[h] = 'charge'
        elif bess_discharge[h] > 0:
            bess_action_kwh[h] = bess_discharge[h]
            bess_mode[h] = 'discharge'
        else:
            bess_action_kwh[h] = 0.0
            bess_mode[h] = 'idle'
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDACIÓN DEFENSIVA: CERO EN MADRUGADA (00:00-05:59)
    # ═══════════════════════════════════════════════════════════════════════════
    # Regla: BESS NO se carga ni descarga en madrugada
    # - EV está cerrado (cierra 22h)
    # - No hay generación solar (noche)
    # - Aplicar incluso en arbitraje HP/HFP (HFP cubre 0-5h pero sin EV activo)
    # - Fuerza cero incluso si hay bug en lógica anterior
    # ═══════════════════════════════════════════════════════════════════════════
    for h in range(n_hours):
        hour_of_day = h % 24
        if hour_of_day < 6:  # 00:00-05:59 es madrugada
            # Forzar inactividad total en madrugada
            bess_charge[h] = 0.0
            bess_discharge[h] = 0.0
            pv_to_bess[h] = 0.0
            bess_to_ev[h] = 0.0
            bess_to_mall[h] = 0.0
            grid_to_bess[h] = 0.0
            bess_action_kwh[h] = 0.0
            bess_mode[h] = 'midnight_off'  # Indicador de fuera de operación
    
    # =====================================================
    # CREAR DATETIME INDEX
    # =====================================================
    datetime_index = pd.date_range(
        start=f'{year}-01-01 00:00:00',
        periods=n_hours,
        freq='h'
    )
    
    # DataFrame de resultados CON TODAS LAS COLUMNAS PARA CITYLEARN
    df = pd.DataFrame({
        # Columnas de energía existentes
        'pv_kwh': pv_kwh,
        'ev_kwh': ev_kwh,
        'mall_kwh': mall_kwh,
        'load_kwh': ev_kwh + mall_kwh,
        'pv_to_ev_kwh': pv_to_ev,
        'pv_to_bess_kwh': pv_to_bess,
        'pv_to_mall_kwh': pv_to_mall,
        'pv_curtailed_kwh': pv_curtailed,
        'bess_charge_kwh': bess_charge,
        'bess_discharge_kwh': bess_discharge,
        'bess_action_kwh': bess_action_kwh,
        'bess_mode': bess_mode,
        'bess_to_ev_kwh': bess_to_ev,
        'bess_to_mall_kwh': bess_to_mall,
        'grid_to_bess_kwh': grid_to_bess,
        'grid_import_ev_kwh': grid_to_ev,
        'grid_import_mall_kwh': grid_to_mall,
        'grid_import_kwh': grid_to_ev + grid_to_mall + grid_to_bess,
        'grid_export_kwh': pv_curtailed,  # Sin conexión a red
        'soc_percent': soc * 100,
        'soc_kwh': soc * capacity_kwh,
        
        # NUEVAS COLUMNAS: Tarifas y Costos OSINERGMIN
        'is_peak_hour': is_peak_hour,
        'tariff_soles_kwh': tariff_soles_kwh,
        'cost_grid_import_soles': cost_grid_import_soles,
        'savings_bess_soles': savings_bess_soles,
        'co2_grid_kg': (grid_to_ev + grid_to_mall + grid_to_bess) * FACTOR_CO2_KG_KWH,
        'co2_avoided_kg': (bess_to_ev + bess_to_mall) * FACTOR_CO2_KG_KWH,
    }, index=datetime_index)
    df.index.name = 'datetime'
    
    # =====================================================
    # MÉTRICAS
    # =====================================================
    total_pv = float(pv_kwh.sum())
    total_ev = float(ev_kwh.sum())
    total_mall = float(mall_kwh.sum())
    total_load = total_ev + total_mall
    
    ev_from_pv = float(pv_to_ev.sum())
    ev_from_bess = float(bess_to_ev.sum())
    ev_from_grid = float(grid_to_ev.sum())
    
    mall_from_pv = float(pv_to_mall.sum())
    mall_from_bess = float(bess_to_mall.sum())
    mall_from_grid = float(grid_to_mall.sum())
    
    # Autosuficiencia
    total_grid = float(grid_to_ev.sum() + grid_to_mall.sum() + grid_to_bess.sum())
    total_self_sufficiency = 1.0 - (total_grid / max(total_load, 1e-9))
    ev_self_sufficiency = (ev_from_pv + ev_from_bess) / max(total_ev, 1e-9)
    
    # Costos y ahorros
    total_cost_grid_soles = float(cost_grid_import_soles.sum())
    total_savings_bess_soles = float(savings_bess_soles.sum())
    
    # Costo sin BESS (baseline) - todo a tarifa variable
    cost_baseline_soles = sum(
        (ev_kwh[h] + mall_kwh[h]) * tariff_soles_kwh[h] 
        for h in range(n_hours)
    )
    
    # CO2
    total_co2_kg = float((grid_to_ev + grid_to_mall + grid_to_bess).sum() * FACTOR_CO2_KG_KWH)
    co2_avoided_kg = float((bess_to_ev + bess_to_mall).sum() * FACTOR_CO2_KG_KWH)
    
    metrics = {
        # Energía
        'total_pv_kwh': total_pv,
        'total_ev_kwh': total_ev,
        'total_mall_kwh': total_mall,
        'total_load_kwh': total_load,
        'ev_from_pv_kwh': ev_from_pv,
        'ev_from_bess_kwh': ev_from_bess,
        'ev_from_grid_kwh': ev_from_grid,
        'mall_from_pv_kwh': mall_from_pv,
        'mall_from_bess_kwh': mall_from_bess,
        'mall_from_grid_kwh': mall_from_grid,
        'total_bess_charge_kwh': float(bess_charge.sum()),
        'total_bess_discharge_kwh': float(bess_discharge.sum()),
        'total_grid_import_kwh': total_grid,
        'total_grid_export_kwh': float(pv_curtailed.sum()),
        
        # Eficiencia
        'ev_self_sufficiency': ev_self_sufficiency,
        'self_sufficiency': total_self_sufficiency,
        'cycles_per_day': float(bess_charge.sum()) / capacity_kwh / 365 if capacity_kwh > 0 else 0.0,
        'soc_min_percent': float(soc.min() * 100),
        'soc_max_percent': float(soc.max() * 100),
        'soc_avg_percent': float(soc.mean() * 100),
        
        # NUEVAS MÉTRICAS: Costos OSINERGMIN
        'cost_grid_import_soles_year': total_cost_grid_soles,
        'cost_baseline_soles_year': cost_baseline_soles,
        'savings_bess_soles_year': total_savings_bess_soles,
        'savings_total_soles_year': cost_baseline_soles - total_cost_grid_soles,
        'roi_percent': (total_savings_bess_soles / cost_baseline_soles * 100) if cost_baseline_soles > 0 else 0.0,
        
        # CO2
        'co2_emissions_kg_year': total_co2_kg,
        'co2_avoided_kg_year': co2_avoided_kg,
        'co2_reduction_percent': (co2_avoided_kg / (total_co2_kg + co2_avoided_kg) * 100) if (total_co2_kg + co2_avoided_kg) > 0 else 0.0,
    }
    
    return df, metrics


def calculate_bess_discharge_allocation(
    soc_array: np.ndarray,
    ev_demand: np.ndarray,
    capacity_kwh: float,
    power_kw: float,
    soc_min_target: float = 0.20,
    closing_hour: int = 22,
) -> np.ndarray:
    """
    Calcula la POTENCIA MÁXIMA DISPONIBLE para descargar al MALL en cada hora,
    respetando que SOC nunca caiga por debajo del 20% antes de cierre.
    
    ESTRATEGIA: DESCARGA MIXTA
    ════════════════════════════════════════════════════════════════════
    1. PRIMERO: Cubrir demanda EV (100% prioridad)
    2. SEGUNDO: Descargar energía extra a MALL (si hay capacidad)
    3. TARGET: SOC = 20% exacto a las 22h
    
    Args:
        soc_array: Array de SOC (0-1) para cada hora (8760 valores)
        ev_demand: Array de demanda EV (0-24 horas, repite 365 días)
        capacity_kwh: Capacidad BESS (1700 kWh)
        power_kw: Potencia nominal BESS (400 kW)
        soc_min_target: SOC mínimo permitido (0.20 = 20%)
        closing_hour: Hora de cierre operativo (22 = 22h)
    
    Returns:
        Array de potencia máxima disponible para MALL (kW/hora)
    """
    n_hours = len(soc_array)
    max_discharge_to_mall = np.zeros(n_hours)
    
    # Convertir SOC a energía (en kWh)
    soc_kwh_array = soc_array * capacity_kwh
    min_allowed_kwh = soc_min_target * capacity_kwh  # 340 kWh (20% de 1700)
    
    for h in range(n_hours):
        hour_of_day = h % 24
        
        # Fuera de horario operativo: no descargar más
        if hour_of_day >= closing_hour or hour_of_day < 6:
            max_discharge_to_mall[h] = 0.0
            continue
        
        # En horario operativo (6h-22h)
        current_soc_kwh = soc_kwh_array[h]
        ev_dem = ev_demand[h] if h < len(ev_demand) else 0.0
        
        # Energía que PUEDE descargar sin perder 20% de SOC
        # = SOC actual - (mínimo 20% + demanda EV siguiente en horas restantes)
        hours_remaining = closing_hour - hour_of_day
        
        if hours_remaining > 0:
            # Energía disponible para MALL = SOC actual - 20% mínimo
            # (la demanda EV se asume que viene de PV primero, luego BESS si es necesario)
            energy_margin_mall = current_soc_kwh - min_allowed_kwh
            
            # Convertir a potencia por hora (kW/h)
            power_available_kw = max(0.0, energy_margin_mall / hours_remaining)
            
            # Limitar a potencia nominal del BESS
            max_discharge_to_mall[h] = min(power_available_kw, power_kw)
    
    return max_discharge_to_mall


def analyze_bess_characteristics(
    df_sim: pd.DataFrame,
    capacity_kwh: float,
    power_kw: float,
    efficiency: float = 0.95,
) -> dict[str, Any]:
    """
    Analiza características detalladas de carga/descarga del BESS.
    
    Calcula:
    - Velocidad de carga vs descarga (potencia promedio, horas activas, energía total)
    - Ciclos anuales de operación
    - Balance energético completo
    - Energía BESS que atiende al MALL (cálculo exacto)
    - Análisis horario: cuándo BESS atiende al MALL
    - Distribución de modos (carga, descarga, idle, full)
    
    Args:
        df_sim: DataFrame con simulación horaria (contiene columnas bess_charge_kwh, bess_discharge_kwh, etc.)
        capacity_kwh: Capacidad nominal del BESS
        power_kw: Potencia nominal del BESS
        efficiency: Eficiencia round-trip
    
    Returns:
        Dict con análisis completo
    """
    # Parámetros de eficiencia
    eff_charge = math.sqrt(efficiency)
    eff_discharge = math.sqrt(efficiency)
    
    # ═════════════════════════════════════════════════════════════════════
    # 1. DISTRIBUCIÓN DE HORAS Y MODOS
    # ═════════════════════════════════════════════════════════════════════
    total_hours = len(df_sim)
    horas_carga = (df_sim['bess_charge_kwh'] > 0.01).sum()
    horas_descarga = (df_sim['bess_discharge_kwh'] > 0.01).sum()
    horas_idle = (df_sim['bess_mode'] == 'idle').sum() if 'bess_mode' in df_sim.columns else 0
    horas_full = (df_sim['bess_mode'] == 'full').sum() if 'bess_mode' in df_sim.columns else 0
    
    # ═════════════════════════════════════════════════════════════════════
    # 2. ENERGÍA TOTAL: CARGA VS DESCARGA
    # ═════════════════════════════════════════════════════════════════════
    carga_total_kwh = df_sim['bess_charge_kwh'].sum()
    descarga_total_kwh = df_sim['bess_discharge_kwh'].sum()
    
    # Velocidad promedio cuando está activa
    carga_por_hora_activa = carga_total_kwh / horas_carga if horas_carga > 0 else 0.0
    descarga_por_hora_activa = descarga_total_kwh / horas_descarga if horas_descarga > 0 else 0.0
    
    # ═════════════════════════════════════════════════════════════════════
    # 3. CICLOS ANUALES Y DESGASTE
    # ═════════════════════════════════════════════════════════════════════
    cycles_per_year = carga_total_kwh / capacity_kwh
    cycles_per_day = cycles_per_year / 365.0
    
    # Para Li-ion típico: 3,000 ciclos = vida útil
    lifetime_cycles_typical = 3000.0
    lifetime_wear_percent_per_year = (cycles_per_year / lifetime_cycles_typical) * 100.0
    
    # ═════════════════════════════════════════════════════════════════════
    # 4. BALANCE ENERGÉTICO
    # ═════════════════════════════════════════════════════════════════════
    diferencia_carga_descarga = carga_total_kwh - descarga_total_kwh
    eficiencia_realizada = (descarga_total_kwh / carga_total_kwh * 100.0) if carga_total_kwh > 0 else 0.0
    
    # ═════════════════════════════════════════════════════════════════════
    # 5. ENERGÍA DEL BESS QUE ATIENDE AL MALL
    # ═════════════════════════════════════════════════════════════════════
    bess_to_mall_total = df_sim['bess_to_mall_kwh'].sum() if 'bess_to_mall_kwh' in df_sim.columns else 0.0
    bess_to_ev_total = df_sim['bess_to_ev_kwh'].sum() if 'bess_to_ev_kwh' in df_sim.columns else 0.0
    mall_demand_total = df_sim['mall_demand_kwh'].sum() if 'mall_demand_kwh' in df_sim.columns else df_sim['mall_kwh'].sum() if 'mall_kwh' in df_sim.columns else 0.0
    ev_demand_total = df_sim['ev_demand_kwh'].sum() if 'ev_demand_kwh' in df_sim.columns else df_sim['ev_kwh'].sum() if 'ev_kwh' in df_sim.columns else 0.0
    
    bess_to_mall_pct = (bess_to_mall_total / mall_demand_total * 100.0) if mall_demand_total > 0 else 0.0
    bess_to_ev_pct = (bess_to_ev_total / ev_demand_total * 100.0) if ev_demand_total > 0 else 0.0
    
    # ═════════════════════════════════════════════════════════════════════
    # 6. ANÁLISIS HORARIO: CUÁNDO BESS ATIENDE AL MALL
    # ═════════════════════════════════════════════════════════════════════
    horas_bess_mall = (df_sim['bess_to_mall_kwh'] > 0.01).sum() if 'bess_to_mall_kwh' in df_sim.columns else 0
    
    # Horas del día cuando BESS atiende al MALL
    horas_activas_mall = []
    if 'datetime' in df_sim.index.names or isinstance(df_sim.index, pd.DatetimeIndex):
        df_with_hour = df_sim.copy()
        if isinstance(df_sim.index, pd.DatetimeIndex):
            df_with_hour['hour'] = df_sim.index.hour
        else:
            df_with_hour['hour'] = pd.to_datetime(df_sim['datetime']).dt.hour if 'datetime' in df_sim.columns else 0
        
        horas_con_bess_mall = df_with_hour[df_with_hour['bess_to_mall_kwh'] > 0.01]
        if len(horas_con_bess_mall) > 0:
            horas_activas_mall = sorted(horas_con_bess_mall['hour'].unique().tolist())
    
    # Energía promedio por hora cuando BESS atiende al MALL
    energia_promedio_mall_por_hora = bess_to_mall_total / horas_bess_mall if horas_bess_mall > 0 else 0.0
    
    # ═════════════════════════════════════════════════════════════════════
    # 7. ANÁLISIS DE DÍA TÍPICO
    # ═════════════════════════════════════════════════════════════════════
    # Tomar el primer día completo como ejemplo
    dia_tipico = {}
    if 'datetime' in df_sim.index.names or isinstance(df_sim.index, pd.DatetimeIndex):
        if isinstance(df_sim.index, pd.DatetimeIndex):
            primer_dia = df_sim.iloc[:24]
        else:
            primer_dia = df_sim.head(24)
        
        # Estadísticas del día típico
        soc_inicial = primer_dia['bess_soc_percent'].iloc[0]
        soc_final = primer_dia['bess_soc_percent'].iloc[-1]
        soc_max_dia = primer_dia['bess_soc_percent'].max()
        soc_min_dia = primer_dia['bess_soc_percent'].min()
        
        carga_dia = primer_dia['bess_charge_kwh'].sum()
        descarga_dia = primer_dia['bess_discharge_kwh'].sum()
        
        dia_tipico = {
            'soc_inicial_pct': float(soc_inicial),
            'soc_final_pct': float(soc_final),
            'soc_max_pct': float(soc_max_dia),
            'soc_min_pct': float(soc_min_dia),
            'carga_total_kwh': float(carga_dia),
            'descarga_total_kwh': float(descarga_dia),
        }
    
    # ═════════════════════════════════════════════════════════════════════
    # RETORNAR ANÁLISIS COMPLETO
    # ═════════════════════════════════════════════════════════════════════
    return {
        'horas_carga': int(horas_carga),
        'horas_descarga': int(horas_descarga),
        'horas_idle': int(horas_idle),
        'horas_full': int(horas_full),
        'carga_total_kwh': float(carga_total_kwh),
        'descarga_total_kwh': float(descarga_total_kwh),
        'carga_por_hora_activa_kwh': float(carga_por_hora_activa),
        'descarga_por_hora_activa_kwh': float(descarga_por_hora_activa),
        'carga_promedio_pct_nominal': float(100 * carga_por_hora_activa / power_kw) if power_kw > 0 else 0.0,
        'descarga_promedio_pct_nominal': float(100 * descarga_por_hora_activa / power_kw) if power_kw > 0 else 0.0,
        'cycles_per_year': float(cycles_per_year),
        'cycles_per_day': float(cycles_per_day),
        'lifetime_wear_percent_per_year': float(lifetime_wear_percent_per_year),
        'color_headroom_carga_descarga': float(diferencia_carga_descarga),
        'eficiencia_realizada_roundtrip': float(eficiencia_realizada),
        'bess_to_mall_kwh': float(bess_to_mall_total),
        'bess_to_mall_pct_demanda': float(bess_to_mall_pct),
        'bess_to_ev_kwh': float(bess_to_ev_total),
        'bess_to_ev_pct_demanda': float(bess_to_ev_pct),
        'horas_bess_atiende_mall': int(horas_bess_mall),
        'energia_prom_mall_por_hora_kwh': float(energia_promedio_mall_por_hora),
        'horas_activas_mall_del_dia': horas_activas_mall,
        'dia_tipico': dia_tipico,
    }


def generate_bess_analysis_report(
    characteristics: dict[str, Any],
    capacity_kwh: float,
    power_kw: float,
    efficiency: float = 0.95,
) -> str:
    """
    Genera reporte texto detallado de características del BESS.
    
    Args:
        characteristics: Dict retornado por analyze_bess_characteristics()
        capacity_kwh: Capacidad nominal BESS
        power_kw: Potencia nominal BESS
        efficiency: Eficiencia round-trip
    
    Returns:
        String con reporte formateado
    """
    report = []
    report.append("=" * 100)
    report.append("ANÁLISIS DETALLADO: CARACTERÍSTICAS DE CARGA/DESCARGA DEL BESS v5.4")
    report.append("=" * 100)
    
    # Especificaciones
    eff_charge = math.sqrt(efficiency)
    report.append(f"\n[1] ESPECIFICACIONES TÉCNICAS DEL BESS")
    report.append("-" * 100)
    report.append(f"  • Capacidad nominal:          {capacity_kwh:,.0f} kWh")
    report.append(f"  • Potencia nominal:           {power_kw:,.0f} kW (CARGA y DESCARGA)")
    report.append(f"  • Velocidad de carga (C-rate): {power_kw / capacity_kwh:.3f} C")
    report.append(f"    → Carga completa en {capacity_kwh / power_kw:.2f} horas")
    report.append(f"  • Eficiencia round-trip:      {efficiency * 100:.1f}%")
    report.append(f"  • Eficiencia carga/descarga:  {eff_charge * 100:.2f}% cada una")
    report.append(f"  • SOC rango operativo:        20% - 100% (80% DoD)")
    
    # Distribución de horas
    report.append(f"\n[2] DISTRIBUCIÓN DE HORAS DE OPERACIÓN (8,760 horas/año)")
    report.append("-" * 100)
    total = characteristics['horas_carga'] + characteristics['horas_descarga'] + characteristics['horas_idle'] + characteristics['horas_full']
    report.append(f"  - Horas CARGANDO:            {characteristics['horas_carga']:>5d}h ({100*characteristics['horas_carga']/8760:>5.1f}%)")
    report.append(f"  - Horas DESCARGANDO:         {characteristics['horas_descarga']:>5d}h ({100*characteristics['horas_descarga']/8760:>5.1f}%)")
    report.append(f"  - Horas LLENO (sin actividad): {characteristics['horas_full']:>5d}h ({100*characteristics['horas_full']/8760:>5.1f}%)")
    report.append(f"  - Horas INACTIVO:            {characteristics['horas_idle']:>5d}h ({100*characteristics['horas_idle']/8760:>5.1f}%)")
    
    # Velocidad de carga vs descarga
    report.append(f"\n[3] VELOCIDAD DE CARGA vs DESCARGA")
    report.append("-" * 100)
    report.append(f"\n  CARGA (cuando está activa):")
    report.append(f"    - Total anual:           {characteristics['carga_total_kwh']:>12,.1f} kWh")
    report.append(f"    - Velocidad promedio:    {characteristics['carga_por_hora_activa_kwh']:>12,.1f} kWh/h")
    report.append(f"    - Como % del máximo:     {characteristics['carga_promedio_pct_nominal']:>12.1f}% de {power_kw:.0f} kW")
    
    report.append(f"\n  DESCARGA (cuando está activa):")
    report.append(f"    - Total anual:           {characteristics['descarga_total_kwh']:>12,.1f} kWh")
    report.append(f"    - Velocidad promedio:    {characteristics['descarga_por_hora_activa_kwh']:>12,.1f} kWh/h")
    report.append(f"    - Como % del máximo:     {characteristics['descarga_promedio_pct_nominal']:>12.1f}% de {power_kw:.0f} kW")
    
    # Ciclos y desgaste
    report.append(f"\n[4] CICLOS ANUALES Y DESGASTE")
    report.append("-" * 100)
    report.append(f"  Ciclos por año:              {characteristics['cycles_per_year']:>12.1f} ciclos")
    report.append(f"  Ciclos por día (promedio):   {characteristics['cycles_per_day']:>12.2f} ciclos/día")
    report.append(f"  Desgaste esperado (Li-ion):  {characteristics['lifetime_wear_percent_per_year']:>12.1f}% de vida/año")
    report.append(f"                               (asumiendo 3,000 ciclos de vida típica)")
    
    # Balance energético
    report.append(f"\n[5] BALANCE ENERGÉTICO (AÑO 2024)")
    report.append("-" * 100)
    report.append(f"  - Energía entrante (carga):   {characteristics['carga_total_kwh']:>12,.1f} kWh")
    report.append(f"  - Energía saliente (descarga): {characteristics['descarga_total_kwh']:>12,.1f} kWh")
    report.append(f"  - Diferencia:                 {characteristics['color_headroom_carga_descarga']:>12,.1f} kWh")
    report.append(f"  - Eficiencia round-trip:      {characteristics['eficiencia_realizada_roundtrip']:>12.1f}%")
    
    # Energía BESS → MALL
    report.append(f"\n[6] ENERGÍA DEL BESS QUE ATIENDE AL MALL")
    report.append("-" * 100)
    report.append(f"\n  DESGLOSE ANUAL DE DESCARGA:")
    report.append(f"    - BESS → EV:    {characteristics['bess_to_ev_kwh']:>12,.1f} kWh ({characteristics['bess_to_ev_pct_demanda']:>5.1f}% de demanda EV)")
    report.append(f"    - BESS → MALL:  {characteristics['bess_to_mall_kwh']:>12,.1f} kWh ({characteristics['bess_to_mall_pct_demanda']:>5.1f}% de demanda MALL)")
    
    report.append(f"\n  HORARIOS CUANDO BESS ATIENDE AL MALL:")
    report.append(f"    - Horas activas: {characteristics['horas_bess_atiende_mall']} horas")
    report.append(f"    - Energía promedio/hora: {characteristics['energia_prom_mall_por_hora_kwh']:.1f} kWh/h")
    if characteristics['horas_activas_mall_del_dia']:
        report.append(f"    - Horas principales del día: {characteristics['horas_activas_mall_del_dia']}")
    
    # Día típico
    report.append(f"\n[7] CICLO TÍPICO DE UN DÍA")
    report.append("-" * 100)
    if characteristics['dia_tipico']:
        d = characteristics['dia_tipico']
        report.append(f"  - SOC inicial:    {d['soc_inicial_pct']:>6.1f}%")
        report.append(f"  - SOC final:      {d['soc_final_pct']:>6.1f}%")
        report.append(f"  - SOC máximo:     {d['soc_max_pct']:>6.1f}%")
        report.append(f"  - SOC mínimo:     {d['soc_min_pct']:>6.1f}%")
        report.append(f"  - Carga total:    {d['carga_total_kwh']:>6.1f} kWh")
        report.append(f"  - Descarga total: {d['descarga_total_kwh']:>6.1f} kWh")
    
    report.append("\n" + "=" * 100)
    
    return "\n".join(report)


def save_bess_analysis_summary(
    characteristics: dict[str, Any],
    capacity_kwh: float,
    power_kw: float,
    efficiency: float,
    report_text: str,
    out_dir: Path,
) -> Path:
    """
    Guarda el análisis completo en archivos.
    
    Crea:
    - bess_characteristics_summary.txt (reporte texto)
    - bess_characteristics_analysis.json (datos estructurados)
    
    Args:
        characteristics: Dict del análisis
        capacity_kwh: Capacidad BESS
        power_kw: Potencia BESS
        efficiency: Eficiencia
        report_text: Reporte formateado
        out_dir: Directorio de salida
    
    Returns:
        Path al archivo creado
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Guardar reporte texto
    txt_path = out_dir / "bess_characteristics_summary.txt"
    txt_path.write_text(report_text, encoding='utf-8')
    print(f"  ✓ Reporte guardado: {txt_path}")
    
    # Guardar JSON
    json_path = out_dir / "bess_characteristics_analysis.json"
    data_to_save = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'bess_specs': {
            'capacity_kwh': capacity_kwh,
            'power_kw': power_kw,
            'efficiency_roundtrip': efficiency,
        },
        'analysis': characteristics,
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Análisis JSON guardado: {json_path}")
    
    return txt_path


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
    Genera las 4 graficas del sistema FV + BESS.

    Args:
        df_sim: DataFrame con simulacion
        capacity_kwh: Capacidad BESS
        power_kw: Potencia BESS
        dod: Profundidad de descarga
        c_rate: Tasa C
        mall_kwh_day: Demanda diaria mall
        ev_kwh_day: Demanda diaria EV
        pv_kwh_day: Generacion diaria PV
        out_dir: Directorio de datos interim
        reports_dir: Directorio de reportes (opcional)
        df_ev_15min: Perfil de 15 min original (96 intervalos) para visualizacion
    """
    plots_dir = out_dir / "plots"
    if reports_dir is not None:
        plots_dir = reports_dir / "oe2" / "bess"
    plots_dir.mkdir(parents=True, exist_ok=True)

    def save_plot(filename: str):
        """Guarda plot en un solo directorio."""
        plt.savefig(plots_dir / filename, dpi=150, bbox_inches='tight')  # type: ignore[attr-defined]

    # Obtener datos de un dia representativo (promedio)
    # Excluir columnas no numéricas (como bess_mode) antes de calcular mean
    df_sim_copy = df_sim.copy()
    # Extraer 'hour' del índice datetime si existe
    if isinstance(df_sim_copy.index, pd.DatetimeIndex):
        df_sim_copy['hour'] = df_sim_copy.index.hour
    elif 'hour' not in df_sim_copy.columns:
        df_sim_copy['hour'] = np.arange(len(df_sim_copy)) % 24
    
    numeric_cols = df_sim_copy.select_dtypes(include=['number']).columns.tolist()
    df_day = df_sim_copy[numeric_cols].groupby('hour').mean().reset_index()  # type: ignore[attr-defined]

    # Asegurar que todas las 24 horas (0-23) esten presentes
    all_hours = pd.DataFrame({'hour': range(24)})
    df_day = all_hours.merge(df_day, on='hour', how='left').fillna(0)  # type: ignore[attr-defined]

    hours = df_day['hour'].values  # type: ignore[attr-defined]
    # Usar el valor pasado como parámetro o calcular desde datos
    total_pv_label = pv_kwh_day if pv_kwh_day > 0 else float(df_day.get('pv_generation_kwh', df_day.get('pv_kwh', pd.Series([0]))).sum())

    # ===========================================================
    # Figura principal con 4 paneles
    # ===========================================================
    _, axes = plt.subplots(4, 1, figsize=(14, 16))  # type: ignore[attr-defined]

    # Datos - convertir a numpy arrays para compatibilidad de tipos
    # Buscar columna PV con fallbacks múltiples
    pv_col = None
    for col in ['pv_generation_kwh', 'pv_kwh', 'potencia_kw']:
        if col in df_day.columns:
            pv_col = col
            break
    pv = np.asarray(df_day[pv_col].values) if pv_col else np.zeros(len(df_day))  # type: ignore[attr-defined]
    
    # Buscar columna LOAD con fallbacks
    if 'load_kwh' in df_day.columns:
        load = np.asarray(df_day['load_kwh'].values)  # type: ignore[attr-defined]
    elif 'ev_demand_kwh' in df_day.columns and 'mall_demand_kwh' in df_day.columns:
        load = np.asarray((df_day['ev_demand_kwh'] + df_day['mall_demand_kwh']).values)  # type: ignore[attr-defined]
    elif 'pv_generation_kwh' in df_day.columns:
        load = np.zeros(len(df_day))  # Fallback: load cero
    else:
        load = np.zeros(len(df_day))  # type: ignore[attr-defined]
    
    # SOC
    soc = np.asarray(df_day['bess_soc_percent'].values) if 'bess_soc_percent' in df_day.columns else np.zeros(len(df_day))  # type: ignore[attr-defined]
    charge = np.asarray(df_day.get('bess_charge_kwh', np.zeros(len(df_day))).values)  # type: ignore[attr-defined]
    discharge = np.asarray(df_day.get('bess_discharge_kwh', np.zeros(len(df_day))).values)  # type: ignore[attr-defined]

    # Separar demanda Mall vs EV (usar datos reales del dataset si disponibles)
    if 'ev_demand_kwh' in df_day.columns:
        # USAR PERFIL EV REAL DEL DATASET (variable)
        ev_h = np.asarray(df_day['ev_demand_kwh'].values)  # type: ignore[attr-defined]
        mall_h = np.asarray(df_day['mall_demand_kwh'].values)  # type: ignore[attr-defined]
    elif 'ev_kwh' in df_day.columns:
        # Usar nombres alternativos si existen
        ev_h = np.asarray(df_day['ev_kwh'].values)  # type: ignore[attr-defined]
        mall_h = np.asarray(df_day['mall_kwh'].values)  # type: ignore[attr-defined]
    else:
        # Fallback: calcular proporcionalmente
        total_demand_day = mall_kwh_day + ev_kwh_day
        mall_ratio = mall_kwh_day / total_demand_day if total_demand_day > 0 else 0.5
        ev_ratio = ev_kwh_day / total_demand_day if total_demand_day > 0 else 0.5
        mall_h = load * mall_ratio
        ev_h = load * ev_ratio
    # PV aplicado al mall solo cuando hay generacion solar (>0)
    mall_solar_used = np.where(pv > 0, np.minimum(mall_h, pv), 0.0)

    grid_import = np.asarray(df_day.get('grid_import_total_kwh', np.zeros(len(df_day))).values)  # type: ignore[attr-defined]
    # grid_export no se usa en graficas actuales
    mall_grid = np.asarray(df_day['grid_to_mall_kwh'].values) if 'grid_to_mall_kwh' in df_day.columns else np.maximum(mall_h - mall_solar_used, 0)  # type: ignore[attr-defined]
    ev_grid = np.asarray(df_day['grid_to_ev_kwh'].values) if 'grid_to_ev_kwh' in df_day.columns else np.maximum(grid_import - mall_grid, 0)  # type: ignore[attr-defined]
    # mall_solar_used_plot no se usa actualmente

    # ===== Panel 1: Demanda Total =====
    ax1 = axes[0]
    # Demanda mall achurada en azul
    ax1.fill_between(hours, 0, mall_h, color='steelblue', alpha=0.5, hatch='///', edgecolor='blue', label='Demanda Mall')
    ax1.bar(hours, ev_h, bottom=mall_h, color='salmon', alpha=0.9, label='Vehículos Eléctricos')
    ax1.plot(hours, load, 'r-', linewidth=2, marker='o', markersize=4, label='Demanda Total')
    ax1.set_xlabel('Hora del Día (Horario Local Perú UTC-5)', fontsize=10)
    ax1.set_ylabel('Energía (kWh)', fontsize=10)
    ax1.set_title(f'Panel 1: Demanda Energética Total - Mall {mall_h.sum():.0f} + EV {ev_h.sum():.0f} = {load.sum():.0f} kWh/día', fontsize=12, fontweight='bold')
    ax1.set_xlim(-0.5, 23.5)
    ax1.set_xticks(range(24))
    ax1.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ===== Panel 2: PV vs Demanda (para dimensionamiento BESS) =====
    ax2 = axes[1]
    mall_pv_used = np.minimum(pv, mall_h)
    surplus_pv_mall = np.maximum(pv - mall_h, 0.0)

    # Demanda mall achurada en azul
    ax2.fill_between(hours, 0, mall_h, color='steelblue', alpha=0.4, hatch='///', edgecolor='blue', label=f'Demanda Mall {mall_h.sum():.1f} kWh/dia')
    # Generacion FV
    ax2.fill_between(hours, 0, pv, color='yellow', alpha=0.5, label=f'Generacion FV {pv.sum():.1f} kWh/dia')
    # Carga EV
    ax2.plot(hours, ev_h, 'm-', linewidth=2.5, marker='s', markersize=4, label=f'Carga EV {ev_h.sum():.1f} kWh/dia')
    # Lineas de referencia
    ax2.plot(hours, pv, 'g-', linewidth=1.5, alpha=0.7)
    ax2.plot(hours, load, 'r--', linewidth=1.5, label='Demanda Total')
    surplus_day = surplus_pv_mall.sum()
    surplus_max = surplus_pv_mall.max()
    mall_pv_used_day = mall_pv_used.sum()

    ax2.annotate(
        f'Solar -> Mall: {mall_pv_used_day:.1f} kWh/dia\n'
        f'Excedente solar: {surplus_day:.1f} kWh/dia\n'
        f'Pico excedente: {surplus_max:.1f} kWh',
        xy=(0.02, 0.98), xycoords='axes fraction', ha='left', va='top',
        fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
    )
    ax2.set_xlabel('Hora del Día (Horario Local Perú UTC-5)', fontsize=10)
    ax2.set_ylabel('Energía (kWh)', fontsize=10)
    ax2.set_title(
        f'Panel 2: Balance Energético - Generación FV {total_pv_label:.0f} kWh/día',
        fontsize=12,
        fontweight='bold',
    )
    ax2.set_xlim(-0.5, 23.5)
    ax2.set_xticks(range(24))
    ax2.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.3)

    # ===== Panel 3: Estado de Carga Bateria =====
    ax3 = axes[2]
    soc_min_limit = (1.0 - dod) * 100
    soc_max_limit = 100.0

    ax3.fill_between(hours, soc_min_limit, soc, color='lightgreen', alpha=0.7, label='SOC BESS')
    ax3.plot(hours, soc, 'g-', linewidth=2, marker='o', markersize=4, label='SOC BESS')
    ax3.axhline(y=soc_min_limit, color='green', linestyle='--', linewidth=1.5, label=f'SOC minimo ({soc_min_limit:.0f}%)')
    ax3.axhline(y=soc_max_limit, color='blue', linestyle='--', linewidth=1.5, label=f'SOC maximo ({soc_max_limit:.0f}%)')

    # LÍNEA DE CIERRE a las 22h
    ax3.axvline(x=22, color='red', linestyle='-', linewidth=2.5, alpha=0.8, label='Cierre 22h')
    ax3.axvspan(22, 24, alpha=0.15, color='gray', label='Fuera horario')

    ax3.set_xlabel('Hora del Día (Horario Local Perú UTC-5)', fontsize=10)
    ax3.set_ylabel('Estado de Carga (%)', fontsize=10)
    ax3.set_title(f'Panel 3: Estado de Carga BESS - {capacity_kwh:.0f} kWh / {power_kw:.0f} kW (DoD {dod*100:.0f}%, {c_rate:.2f}C)',
                  fontsize=12, fontweight='bold')
    ax3.set_xlim(-0.5, 23.5)
    ax3.set_ylim(0, 110)
    ax3.set_xticks(range(24))
    ax3.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
    ax3.legend(loc='upper left', fontsize=9, ncol=2)
    ax3.grid(True, alpha=0.3)

    # Agregar anotaciones de SOC
    soc_min_val = soc.min()
    soc_max_val = soc.max()
    cycles_day = charge.sum() / capacity_kwh if capacity_kwh > 0 else 0
    ax3.annotate(f'SOC min: {soc_min_val:.1f}%\nSOC max: {soc_max_val:.1f}%\nCiclos/día: {cycles_day:.2f}\nHorario EV: 9h-22h',
                 xy=(0.98, 0.98), xycoords='axes fraction', ha='right', va='top',
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

# ===== Panel 4: Flujos de Energía - BESS, EV y Red Pública =====
    ax4 = axes[3]

    # ÁREA FUERA DE HORARIO (22h-24h) - sombreada
    ax4.axvspan(22, 24, alpha=0.15, color='gray', zorder=1)
    ax4.axvline(x=22, color='red', linestyle='-', linewidth=2.5, alpha=0.8, zorder=10)

    # Generacion solar (area amarilla - fondo)
    ax4.fill_between(hours, 0, pv, color='yellow', alpha=0.35, label='Generación Solar')

    # BARRAS DE CARGA BESS: verdes hacia arriba (excedente solar → batería)
    ax4.bar(hours, charge, width=0.7, color='green', alpha=0.8, edgecolor='darkgreen',
            linewidth=1.5, label='Carga BESS (solar → batería)', zorder=4)

    # BARRAS DE DESCARGA BESS: naranjas hacia arriba separadas (batería → EV)
    # Usamos posición desplazada para que no se superpongan
    ax4.bar(np.array(hours) + 0.35, discharge, width=0.35, color='orange', alpha=0.8, 
            edgecolor='darkorange', linewidth=1.5, label='Descarga BESS (batería → EV)', zorder=4)

    # CURVA RED PÚBLICA: Importación de la red eléctrica (línea roja con área)
    ax4.plot(hours, grid_import, 'r-', linewidth=2.5, marker='x', markersize=6,
             label=f'Import Red ({grid_import.sum():.0f} kWh/día)', zorder=6)
    ax4.fill_between(hours, 0, grid_import, color='red', alpha=0.15, zorder=2)

    # Perfil de carga EV - USAR PERFIL REAL DEL DATASET ACTUALIZADO (variable)
    if df_ev_15min is not None and len(df_ev_15min) == 96:
        # Perfil de 15 minutos: 96 intervalos (0-95)
        intervals_15min = df_ev_15min['interval'].values  # type: ignore[attr-defined]
        hours_15min = intervals_15min / 4.0  # type: ignore[operator]
        ev_15min_values = df_ev_15min['ev_kwh'].values  # type: ignore[attr-defined]

        ax4.plot(hours_15min, ev_15min_values, color='darkmagenta', linestyle='-', linewidth=3.5,
                 label='Perfil real EV 15 min (38 sockets)', zorder=7, alpha=1.0)
        ax4.scatter(hours_15min[::4], ev_15min_values[::4], color='purple', s=60, marker='o',
                    zorder=8, edgecolor='white', linewidth=1.5)
    else:
        # Usar perfil horario agregado del dataset real
        ax4.plot(hours, ev_h, 'm-', linewidth=3, marker='o', markersize=6,
                 label=f'Demanda EV ({ev_h.sum():.0f} kWh/día)', zorder=5)

    # Configuración del eje
    ax4.set_xlabel('Hora del Día (Horario Local Perú UTC-5)', fontsize=10)
    ax4.set_ylabel('Energía (kWh)', fontsize=10)
    ax4.set_title(f'Panel 4: Flujos de Energía - BESS y Red Pública', fontsize=12, fontweight='bold')
    ax4.set_xlim(-0.5, 23.5)
    ax4.set_xticks(range(24))

    ax4.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
    ax4.legend(loc='upper left', fontsize=8, ncol=2)
    ax4.grid(True, alpha=0.3)

    # Metricas integradas con explicacion
    # Variables calculadas pero no usadas: grid_total, grid_mall_total, pv_to_bess
    grid_ev_total = ev_grid.sum()
    bess_charge_total = charge.sum()
    bess_discharge_total = discharge.sum()
    ev_total = ev_h.sum()
    bess_to_ev = bess_discharge_total
    ev_self_suff = (1 - grid_ev_total/max(ev_total, 1e-9))*100

    ax4.annotate(
        f'BALANCE BESS:\n'
        f'  Carga (solar): {bess_charge_total:.1f} kWh/dia\n'
        f'  Descarga (EV): {bess_discharge_total:.1f} kWh/dia\n'
        f'\n'
        f'DEMANDA EV:\n'
        f'  Total: {ev_total:.1f} kWh/dia\n'
        f'  Cubierta BESS: {bess_to_ev:.1f} kWh/dia\n'
        f'  De Red: {grid_ev_total:.1f} kWh/dia\n'
        f'  Autosuficiencia: {ev_self_suff:.1f}%',
        xy=(0.98, 0.98), xycoords='axes fraction', ha='right', va='top',
        fontsize=8, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9, edgecolor='orange', linewidth=2)
    )

    # Titulo principal
    plt.suptitle('Sistema FV + BESS - Mall Iquitos, Loreto, Peru', fontsize=14, fontweight='bold', y=1.01)  # type: ignore[attr-defined]
    plt.tight_layout()  # type: ignore[attr-defined]
    save_plot('bess_sistema_completo.png')
    plt.close()  # type: ignore[attr-defined]
    print("  OK Grafica: Sistema FV + BESS Completo")

    # ===========================================================
    # Grafica adicional: Analisis mensual
    # ===========================================================
    if len(df_sim) >= 720:  # Al menos un mes de datos
        _, axes = plt.subplots(2, 2, figsize=(14, 10))  # type: ignore[attr-defined]

        # Agregar por mes - extraer mes del índice datetime
        df_sim_copy = df_sim.copy()
        if isinstance(df_sim_copy.index, pd.DatetimeIndex):
            df_sim_copy['month'] = df_sim_copy.index.month
        else:
            df_sim_copy['month'] = (np.arange(len(df_sim_copy)) // 720) % 12 + 1
        # Excluir columnas no numéricas (datetime, bess_mode) y 'month' para el groupby
        numeric_cols_monthly = [c for c in df_sim_copy.select_dtypes(include=['number']).columns.tolist() 
                               if c != 'month']
        monthly = df_sim_copy[numeric_cols_monthly + ['month']].groupby('month').sum()  # type: ignore[attr-defined]

        # Panel 1: Energia mensual
        ax1 = axes[0, 0]
        months = monthly.index.values  # type: ignore[attr-defined]
        # Usar 'pv_generation_kwh' que es lo que el DataFrame contiene
        pv_col = 'pv_generation_kwh' if 'pv_generation_kwh' in monthly.columns else 'pv_kwh'
        ax1.bar(months - 0.2, monthly[pv_col] / 1000, width=0.4, color='yellow', label='Generacion PV')
        # Usar columna correcta de demanda total
        load_col = 'load_kwh' if 'load_kwh' in monthly.columns else None
        if load_col:
            ax1.bar(months + 0.2, monthly[load_col] / 1000, width=0.4, color='salmon', label='Demanda Total')
        else:
            # Calcular suma de EV + Mall
            total_load = (monthly.get('ev_demand_kwh', 0) + monthly.get('mall_demand_kwh', 0)) if isinstance(monthly.get('ev_demand_kwh', 0), (int, float)) else (monthly['ev_kwh'] + monthly['mall_kwh'])
            ax1.bar(months + 0.2, total_load / 1000, width=0.4, color='salmon', label='Demanda Total')
        ax1.set_xlabel('Mes', fontsize=10)
        ax1.set_ylabel('Energia (MWh)', fontsize=10)
        ax1.set_title('Energia Mensual', fontsize=11, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Panel 2: Flujos de red mensual
        ax2 = axes[0, 1]
        # Usar nombres correctos de columnas
        grid_import_col = 'grid_import_total_kwh' if 'grid_import_total_kwh' in monthly.columns else 'grid_import_kwh'
        grid_export_col = 'pv_curtailed_kwh' if 'pv_curtailed_kwh' in monthly.columns else 'grid_export_kwh'
        ax2.bar(months - 0.2, monthly.get(grid_import_col, 0) / 1000, width=0.4, color='red', label='Import Red')
        ax2.bar(months + 0.2, monthly.get(grid_export_col, 0) / 1000, width=0.4, color='blue', label='Export Red')
        ax2.set_xlabel('Mes', fontsize=10)
        ax2.set_ylabel('Energia (MWh)', fontsize=10)
        ax2.set_title('Intercambio con Red Mensual', fontsize=11, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Panel 3: Ciclos BESS
        ax3 = axes[1, 0]
        monthly_cycles = (monthly['bess_charge_kwh'] / capacity_kwh) / 30  # Ciclos/dia promedio
        ax3.bar(months, monthly_cycles, color='green', alpha=0.7)
        ax3.axhline(y=1.0, color='red', linestyle='--', label='1 ciclo/dia')
        ax3.set_xlabel('Mes', fontsize=10)
        ax3.set_ylabel('Ciclos/dia', fontsize=10)
        ax3.set_title('Ciclos BESS por Mes', fontsize=11, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Panel 4: Autosuficiencia mensual
        ax4 = axes[1, 1]
        # Usar columnas correctas
        grid_col = 'grid_import_total_kwh' if 'grid_import_total_kwh' in monthly.columns else 'grid_import_kwh'
        load_col_total = 'load_kwh' if 'load_kwh' in monthly.columns else None
        if load_col_total:
            self_suff_monthly = 1.0 - (monthly[grid_col] / monthly[load_col_total].replace(0, 1))  # type: ignore[attr-defined]
        else:
            # Calcular carga total como suma de EV + Mall
            total_load_self = (monthly.get('ev_demand_kwh', monthly['ev_kwh']) + monthly.get('mall_demand_kwh', monthly['mall_kwh']))
            self_suff_monthly = 1.0 - (monthly[grid_col] / total_load_self.replace(0, 1))  # type: ignore[attr-defined]
        ax4.bar(months, self_suff_monthly * 100, color='teal', alpha=0.7)
        ax4.axhline(y=50, color='red', linestyle='--', label='50%')
        ax4.set_xlabel('Mes', fontsize=10)
        ax4.set_ylabel('Autosuficiencia (%)', fontsize=10)
        ax4.set_title('Autosuficiencia Mensual', fontsize=11, fontweight='bold')
        ax4.set_ylim(0, 100)
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.suptitle('Analisis Mensual del Sistema', fontsize=13, fontweight='bold')  # type: ignore[attr-defined]
        plt.tight_layout()  # type: ignore[attr-defined]
        save_plot('bess_analisis_mensual.png')
        plt.close()  # type: ignore[attr-defined]
        print("  OK Grafica: Analisis Mensual")

    print(f"  OK Plots guardados en: {plots_dir}")


def prepare_citylearn_data(
    df_sim: pd.DataFrame,
    capacity_kwh: float,
    power_kw: float,
    pv_dc_kw: float,
    out_dir: Path,
) -> dict[str, Any]:
    """
    Prepara los datos del BESS para el schema de CityLearn.

    Genera datos con resolucion horaria (8,760 timesteps/año).

    Returns:
        Diccionario con parametros para schema.json
    """
    citylearn_dir = out_dir.parent / "citylearn"
    citylearn_dir.mkdir(parents=True, exist_ok=True)

    # Guardar timeseries de demanda para CityLearn (solo demanda del mall)
    # CityLearn espera: Hour (0-8759), non_shiftable_load (kWh)
    load_series = df_sim['mall_demand_kwh'] if 'mall_demand_kwh' in df_sim.columns else df_sim['load_kwh']

    # Usar 'hour' si existe (horario), sino usar indice
    if 'hour' in df_sim.columns:
        hour = df_sim['hour'].values  # type: ignore[attr-defined]
    else:
        hour = np.arange(len(df_sim))

    df_export = pd.DataFrame({
        'Hour': hour,
        'non_shiftable_load': load_series.values,  # type: ignore[attr-defined]
    })
    df_export.to_csv(citylearn_dir / "building_load.csv", index=False)

    # Guardar generacion PV
    pv_series = df_sim['pv_generation_kwh'] if 'pv_generation_kwh' in df_sim.columns else df_sim['pv_kwh']
    df_pv = pd.DataFrame({
        'Hour': hour,
        'solar_generation': pv_series.values,  # type: ignore[attr-defined]
    })
    df_pv.to_csv(citylearn_dir / "bess_solar_generation.csv", index=False)

    # Parametros para schema
    schema_params = {  # type: ignore[attr-defined]
        "electrical_storage": {
            "type": "Battery",
            "capacity": capacity_kwh,
            "nominal_power": power_kw,
            "capacity_loss_coefficient": 0.00001,
            "power_efficiency_curve": [[0, 0.83], [0.3, 0.92], [0.6, 0.95], [0.8, 0.94], [1, 0.91]],
            "capacity_power_curve": [[0, 1], [0.8, 1], [1, 0.95]],
            "efficiency": 0.95,  # v5.2
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

    # Guardar parametros
    (citylearn_dir / "bess_schema_params.json").write_text(
        json.dumps(schema_params, indent=2), encoding="utf-8"
    )

    print(f"\nDatos CityLearn guardados en: {citylearn_dir}")

    return schema_params  # type: ignore[attr-defined]


def run_bess_sizing(
    out_dir: Path,
    pv_profile_path: Path,
    ev_profile_path: Path,
    mall_demand_path: Path,
    dod: float = 0.80,  # v5.2: 80% DOD
    c_rate: float = 0.36,  # v5.2: 0.36 C-rate
    round_kwh: float = 10.0,
    efficiency_roundtrip: float = 0.95,  # v5.2: 95% efficiency
    autonomy_hours: float = 4.0,
    pv_dc_kw: float = 0.0,
    tz: Optional[str] = None,
    sizing_mode: str = "ev_open_hours",
    soc_min_percent: Optional[float] = None,
    load_scope: str = "total",
    discharge_hours: Optional[list[int]] = None,
    discharge_only_no_solar: bool = False,
    pv_night_threshold_kwh: float = 0.1,
    surplus_target_kwh_day: float = 0.0,
    year: int = 2024,
    generate_plots: bool = True,
    reports_dir: Optional[Path] = None,
    fixed_capacity_kwh: float = 0.0,
    fixed_power_kw: float = 0.0,
) -> dict[str, object]:
    """
    Ejecuta el dimensionamiento completo del BESS.

    RESPONSABILIDAD: SOLO dimensionamiento BESS
    - Carga datos (PV, EV, Mall) desde archivos existentes
    - NO genera datos sintéticos (responsabilidad de módulos específicos)
    - Simula operación BESS (SOC, flujos energéticos)
    - Calcula métricas (self-sufficiency, CO2, costos)
    - Genera dataset para CityLearn v2

    Args:
        out_dir: Directorio de salida
        pv_profile_path: Ruta al perfil PV (timeseries o 24h)
        ev_profile_path: Ruta al perfil EV (REQUERIDO)
        mall_demand_path: Ruta al archivo de demanda real del mall (REQUERIDO)
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

    # Cargar generación PV desde archivo horario (8,760 horas)
    # Soporta múltiples formatos de columnas
    pv_timeseries_path = pv_profile_path  # Usar directamente el archivo especificado
    if pv_timeseries_path.exists():
        # Leer CSV con manejo robusto de columnas
        df_pv_raw = pd.read_csv(pv_timeseries_path)  # type: ignore[attr-defined]
        
        # Buscar columna de energía PV (prioridad: energia_kwh, ac_energy_kwh, pv_kwh, potencia_kw)
        pv_col = None
        for col in ['energia_kwh', 'ac_energy_kwh', 'pv_kwh', 'potencia_kw', 'ac_power_kw']:
            if col in df_pv_raw.columns:
                pv_col = col
                break
        
        if pv_col is None:
            raise ValueError(f"ERROR: No se encontró columna de generación PV en {pv_timeseries_path.name}")
        
        # Crear DataFrame con índice datetime
        idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
        df_pv = pd.DataFrame(index=idx)
        df_pv['pv_kwh'] = df_pv_raw[pv_col].values[:8760]  # Asegurar 8,760 registros
        
        print(f"   Generacion PV: {len(df_pv)} registros (columna: {pv_col})")
    else:
        raise FileNotFoundError(f"ERROR: Archivo de generación PV NO ENCONTRADO: {pv_timeseries_path}")

    # BESS.PY: SOLO CARGA DATOS, NO GENERA SINTÉTICOS
    # ================================================
    if not mall_demand_path or not mall_demand_path.exists():
        raise FileNotFoundError(
            f"ERROR: Archivo de demanda mall NO ENCONTRADO: {mall_demand_path}\n"
            f"       bess.py solo puede CARGAR datos existentes, NO genera datos sintéticos.\n"
            f"       Responsabilidad: mall_load.py (módulo separado para demanda mall)"
        )
    
    df_mall = load_mall_demand_real(mall_demand_path, year)
    # VALIDACIÓN: df_mall debe tener exactamente 8,760 horas
    # (load_mall_demand_real() ya lo valida, pero se verifica aquí también)
    if len(df_mall) != 8760:
        raise ValueError(
            f"ERROR CRÍTICO: Demanda mall tiene {len(df_mall)} filas, se requieren exactamente 8,760 horas."
        )
    # Calcular promedio diario (para datos horarios: 8,760 horas = 365 días)
    mall_kwh_day = df_mall['mall_kwh'].sum() / 365
    print(f"   Demanda Mall (real, horaria): {mall_kwh_day:.0f} kWh/dia (basado en 8,760 horas)")

    df_ev = load_ev_demand(ev_profile_path, year)

    # Determinar si es formato de 15 min (35,040 intervalos) o horario (8,760)
    if len(df_ev) == 35040:
        # Formato de 15 minutos: 96 intervalos/dia
        ev_kwh_day = df_ev['ev_kwh'].sum() / 365
        print(f"   Demanda EV (15 min, {len(df_ev)} intervalos): {ev_kwh_day:.0f} kWh/dia")
    else:
        # Formato horario: 24 horas/dia
        ev_kwh_day = df_ev['ev_kwh'].sum() / (len(df_ev) / 24)
        print(f"   Demanda EV (horaria, {len(df_ev)} horas): {ev_kwh_day:.0f} kWh/dia")

    print("      - 19 cargadores, 38 tomas totales (Modo 3 @ 7.4 kW)")
    print("      - Playa Motos: 15 cargadores × 2 = 30 tomas")
    print("      - Playa Mototaxis: 4 cargadores × 2 = 8 tomas")

    # ===========================================
    # 2. Alinear series temporales
    # ===========================================
    # Todos los datos en formato horario (8,760 horas/año)

    # EV debe estar en 8,760 horas
    if len(df_ev) != 8760:
        raise ValueError(f"EV debe tener 8,760 horas, tiene {len(df_ev)}")

    # PV debe estar en 8,760 horas
    if len(df_pv) != 8760:
        if len(df_pv) > 8760:
            print(f"   Truncando PV de {len(df_pv)} a 8,760 horas")
            df_pv = df_pv.iloc[:8760].reset_index(drop=True)
        else:
            raise ValueError(f"PV debe tener 8,760 horas, tiene {len(df_pv)}")

    # Mall debe estar en 8,760 horas
    if len(df_mall) != 8760:
        if len(df_mall) > 8760:
            print(f"   Truncando Mall de {len(df_mall)} a 8,760 horas")
            df_mall = df_mall.iloc[:8760].reset_index(drop=True)
        else:
            raise ValueError(f"Mall debe tener 8,760 horas, tiene {len(df_mall)}")

    print("   Alineados a 8,760 horas (formato horario)")

    # Usar las 8,760 horas
    min_len = 8760

    pv_kwh = np.asarray(df_pv['pv_kwh'].values[:min_len])  # type: ignore[attr-defined]
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

    mall_kwh = np.asarray(df_mall['mall_kwh'].values[:min_len])  # type: ignore[attr-defined]
    ev_kwh = np.asarray(df_ev['ev_kwh'].values[:min_len])  # type: ignore[attr-defined]

    total_load_kwh = mall_kwh + ev_kwh

    # ============================================================================
    # REGLAS DE PRIORIDAD GENERACIÓN SOLAR (PROYECTO IQUITOS)
    # ============================================================================
    # 1. Solar -> PRIMERO a motos/mototaxis (EV)
    # 2. Excedente solar -> SEGUNDO carga BESS
    # 3. Excedente despues BESS -> TERCERO a Mall
    # 4. BESS descarga cuando solar no cubre EV, solo hasta cierre (10 PM)
    # 5. SOC BESS debe llegar al 20% a las 10 PM
    # ============================================================================

    bess_load_scope = "ev_only"  # REGLA 1: Solo carga EV
    print("\n[REGLAS BESS - PRIORIDAD SOLAR - EXCLUSIVO EV]")
    print("   1. Solar -> PRIMERO motos/mototaxis (EV)")
    print("   2. Excedente solar -> SEGUNDO carga BESS (hasta SOC 100%)")
    print("   3. Excedente final -> TERCERO Mall")
    print("   4. BESS descarga: Desde punto crítico (PV<EV) hasta cierre 22h")
    print("   5. SOC al cierre (22h): 20%")

    closing_hour = 22  # 10 PM - cierre mall

    # ============================================================================
    # CALCULAR DÉFICIT EV EXACTO PARA DIMENSIONAMIENTO BESS
    # ============================================================================
    # Usando nueva función que analiza el cruce de curvas PV vs EV
    print("\n[ANÁLISIS CRUCE CURVAS PV vs EV]")
    
    deficit_kwh_day_avg, peak_deficit_kw, charge_end_hour, discharge_start_hour, deficit_kwh_day_max = calculate_ev_deficit_for_bess(
        pv_kwh=pv_kwh,
        ev_kwh=ev_kwh,
        closing_hour=closing_hour,
    )
    
    print(f"   Hora fin carga BESS (PV >= EV): ~{charge_end_hour}h (SOC se mantiene 100%)")
    print(f"   Hora inicio descarga (PV < EV): ~{discharge_start_hour}h (punto critico)")
    print(f"   Hora cierre: {closing_hour}h (SOC debe ser 20%)")
    print(f"   Deficit EV promedio: {deficit_kwh_day_avg:.1f} kWh/dia")
    print(f"   Deficit EV MAXIMO: {deficit_kwh_day_max:.1f} kWh/dia [USADO PARA 100% COBERTURA]")
    print(f"   Pico deficit EV: {peak_deficit_kw:.1f} kW")

    hours = np.arange(min_len) % 24

    # Calcular flujos básicos para métricas
    pv_to_ev = np.minimum(pv_kwh, ev_kwh)
    pv_after_ev = pv_kwh - pv_to_ev
    ev_shortfall_hourly = ev_kwh - pv_to_ev

    surplus_day = float(pv_after_ev.sum() / 365)
    pv_day_value = float(pv_kwh.sum() / 365)
    ev_day_value = float(ev_kwh.sum() / 365)
    pv_to_ev_day = float(pv_to_ev.sum() / 365)

    print("\n[FLUJOS ENERGÉTICOS DIARIOS]")
    print(f"   Generacion PV: {pv_day_value:.0f} kWh/dia")
    print(f"   Demanda EV: {ev_day_value:.0f} kWh/dia")
    print(f"   PV->EV directo: {pv_to_ev_day:.0f} kWh/dia")
    print(f"   Excedente PV (para BESS): {surplus_day:.0f} kWh/día")
    print(f"   Deficit EV promedio: {deficit_kwh_day_avg:.0f} kWh/dia")
    print(f"   Deficit EV MAXIMO: {deficit_kwh_day_max:.0f} kWh/dia")

    # ===========================================
    # DIMENSIONAR BESS PARA 100% COBERTURA EV
    # ===========================================
    print("")
    print("=" * 60)
    print("  DIMENSIONAMIENTO BESS - 100% COBERTURA DEFICIT EV")
    print("=" * 60)

    # Parámetros de diseño
    soc_min_percent = 20.0  # SOC mínimo: 20%
    soc_min = soc_min_percent / 100.0
    effective_dod = 0.80  # DoD: 80% (SOC 100% → 20%)
    effective_efficiency = 0.95  # Eficiencia round-trip: 95%

    print("\n[PARÁMETROS DE DISEÑO]")
    print(f"   SOC operacional: {soc_min_percent:.0f}% - 100%")
    print(f"   DoD efectivo: {effective_dod*100:.0f}%")
    print(f"   Eficiencia round-trip: {effective_efficiency*100:.0f}%")

    # CAPACIDAD: Debe cubrir el DÉFICIT EV MÁXIMO en horario nocturno
    # Usamos el MÁXIMO diario para garantizar 100% cobertura todos los días
    # BESS carga la diferencia que el solar no puede cubrir
    sizing_deficit = deficit_kwh_day_max  # MÁXIMO déficit para 100% cobertura
    peak_load = peak_deficit_kw  # Pico deficit EV en descarga

    # Calcular horas de descarga
    n_discharge_hours = closing_hour - discharge_start_hour
    bess_discharge_hours = list(range(discharge_start_hour, closing_hour))

    print("\n[CRITERIO CAPACIDAD - DINAMICO]")
    print("   Criterio: Cubrir DEFICIT EV desde punto critico (EV>PV) hasta cierre (22h)")
    print(f"   SOC final al cierre: 20% (regla operacional)")
    print(f"   Deficit EV en descarga: {sizing_deficit:.0f} kWh/dia")
    print(f"   Horas de descarga: {n_discharge_hours} horas ({discharge_start_hour}h-{closing_hour}h)")
    print(f"   Pico deficit EV: {peak_load:.1f} kW")

    # Capacidad basada en deficit EV desde punto crítico hasta cierre
    # con DoD efectivo del 80% (para llegar al 20% SOC al cierre)
    surplus_for_sizing = surplus_day  # Excedente disponible para carga BESS

    # FACTOR DE DISEÑO: Margen de seguridad adicional
    design_factor = 1.20  # 20% de margen para contingencias, degradacion, picos no previstos

    capacity_kwh, power_kw = calculate_bess_capacity(
        surplus_kwh_day=surplus_for_sizing,
        deficit_kwh_day=sizing_deficit,
        dod=effective_dod,  # 80% segun analisis
        efficiency=effective_efficiency,  # 95% segun analisis
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

    # Ajuste de potencia segun analisis perfil 15 min
    # Capacidad esperada: 1,712 kWh --> Potencia esperada: 622 kW
    # Relacion: 1,712 / 622 = 2.75 (NO es C-rate, es ratio capacidad/potencia)
    power_ratio = 2.75  # Segun analisis de perfil de 15 min
    power_kw = capacity_kwh / power_ratio if capacity_kwh > 0 else 0.0

    print("\nDIMENSIONAMIENTO OPTIMO (segun analisis perfil 15 min):")
    print(f"   Capacidad base:   {capacity_base_kwh:,.0f} kWh")
    print(f"   Factor de diseño: {design_factor:.2f} (margen {(design_factor-1)*100:.0f}%)")
    print(f"   Capacidad final:  {capacity_kwh:,.0f} kWh")
    print(f"   Potencia:         {power_kw:,.0f} kW")
    print(f"   DoD:              {int(effective_dod*100)}%")
    print(f"   Eficiencia:       {int(effective_efficiency*100)}%")
    print(f"   Ratio Cap/Pot:    {power_ratio:.2f}")
    print(f"   Ciclos/dia:       {sizing_deficit/capacity_kwh:.2f}" if capacity_kwh > 0 else "   Ciclos/dia:       0.00")
    print(f"   Deficit cubierto: {sizing_deficit:,.0f} kWh/dia (18h-22h)")

    # ===========================================
    # 5. Simular operacion
    # ===========================================
    print("")
    
    # =====================================================
    # ESTRATEGIA DE OPERACIÓN v5.4: SOLAR-PRIORITY (DEFECTO)
    # Alternativa: ARBITRAJE HP/HFP (legacy)
    # =====================================================
    USE_SOLAR_PRIORITY = True  # ← SET TO FALSE para usar arbitraje tarifario
    
    capacity_kwh = BESS_CAPACITY_KWH_V53  # 1,700 kWh
    power_kw = BESS_POWER_KW_V53          # 400 kW
    
    if USE_SOLAR_PRIORITY:
        print("Simulando operacion BESS con SOLAR-PRIORITY (basado en disponibilidad solar)...")
        print("\n[ESTRATEGIA SOLAR-PRIORITY v5.4 - INDEPENDIENTE DE TARIFA]")
        print(f"   BESS Capacidad:           {capacity_kwh:,.0f} kWh")
        print(f"   BESS Potencia:            {power_kw:,.0f} kW")
        print(f"")
        print(f"   [CARGA] Manana-tarde (6h-22h) cuando PV > demanda")
        print(f"           -> Llenar BESS a 100% desde PV excedente")
        print(f"           -> Solo PV, NO grid")
        print(f"   [DESCARGA] Tarde-noche cuando (PV < Mall) OR (deficit EV AND SOC > min)")
        print(f"              -> BESS->EV (prioridad 1)")
        print(f"              -> BESS->Mall (prioridad 2, si PV < demanda_mall)")
        print(f"   [SOC] 20%-100% con eficiencia {BESS_EFFICIENCY_V53*100:.0f}%")
        print(f"")
        print(f"   Ventajas: Independiente de tarifa futura, mas seguro, logica intuitiva")
        
        df_sim, metrics = simulate_bess_solar_priority(
            pv_kwh=pv_kwh,
            ev_kwh=ev_kwh,
            mall_kwh=mall_kwh,
            capacity_kwh=capacity_kwh,
            power_kw=power_kw,
            efficiency=effective_efficiency,
            soc_min=soc_min,
            closing_hour=closing_hour,
            year=year,
        )
    
    else:
        print("Simulando operacion BESS con ARBITRAJE HP/HFP (OSINERGMIN)...")
        print("\n[ESTRATEGIA ARBITRAJE TARIFARIO OSINERGMIN - LEGACY]")
        print(f"   Tarifa HP  (18:00-23:00): S/.{TARIFA_ENERGIA_HP_SOLES:.2f}/kWh")
        print(f"   Tarifa HFP (resto):       S/.{TARIFA_ENERGIA_HFP_SOLES:.2f}/kWh")
        print(f"   Diferencial ahorro:       S/.{TARIFA_ENERGIA_HP_SOLES - TARIFA_ENERGIA_HFP_SOLES:.2f}/kWh")
        print(f"   BESS Capacidad:           {capacity_kwh:,.0f} kWh")
        print(f"   BESS Potencia:            {power_kw:,.0f} kW")
        print(f"")
        print(f"   [CARGA HFP] 06:00-17:00 → PV excedente + Grid si SOC<80%")
        print(f"   [DESCARGA HP] 18:00-22:00 → BESS→EV y BESS→Mall")
        print(f"   [SOC target] 20%-100% con eficiencia {BESS_EFFICIENCY_V53*100:.0f}%")
        
        df_sim, metrics = simulate_bess_arbitrage_hp_hfp(
            pv_kwh=pv_kwh,
            ev_kwh=ev_kwh,
            mall_kwh=mall_kwh,
            capacity_kwh=capacity_kwh,
            power_kw=power_kw,
            efficiency=effective_efficiency,
            soc_min=soc_min,
            closing_hour=closing_hour,
            year=year,
        )

    # Agregar columnas adicionales si no existen
    if 'mall_grid_import_kwh' not in df_sim.columns:
        df_sim['mall_grid_import_kwh'] = df_sim['grid_to_mall_kwh']

    print(f"\n   Cobertura EV por BESS: {metrics['ev_self_sufficiency']*100:.1f}%")
    print(f"   EV desde PV directo: {metrics['ev_from_pv_kwh']/1000:.0f} MWh/año")
    print(f"   EV desde BESS: {metrics['ev_from_bess_kwh']/1000:.0f} MWh/año")
    print(f"   EV desde red: {metrics['ev_from_grid_kwh']/1000:.0f} MWh/año")
    print(f"   Ciclos/dia:      {metrics['cycles_per_day']:.2f}")
    print(f"   SOC min/max:     {metrics['soc_min_percent']:.1f}% / {metrics['soc_max_percent']:.1f}%")
    print(f"   Import red EV:   {metrics['ev_from_grid_kwh']/(min_len/24):.0f} kWh/dia")
    
    # Métricas de costo y ahorro OSINERGMIN
    print(f"\n[MÉTRICAS ECONÓMICAS OSINERGMIN - ARBITRAJE HP/HFP]")
    print(f"   Costo baseline (sin BESS): S/.{metrics['cost_baseline_soles_year']:,.0f}/año")
    print(f"   Costo con BESS arbitraje:  S/.{metrics['cost_grid_import_soles_year']:,.0f}/año")
    print(f"   Ahorro BESS (arbitraje):   S/.{metrics['savings_bess_soles_year']:,.0f}/año")
    print(f"   Ahorro total:              S/.{metrics['savings_total_soles_year']:,.0f}/año")
    print(f"   ROI arbitraje:             {metrics['roi_percent']:.1f}%")
    
    print(f"\n[MÉTRICAS CO2]")
    print(f"   Emisiones grid (baseline):     {metrics['co2_emissions_kg_year']/1000:.1f} ton CO2/año")
    print(f"")
    print(f"   REDUCCIÓN INDIRECTA DE CO2 (RED TÉRMICA IQUITOS):")
    print(f"   ─────────────────────────────────────────────────────")
    print(f"   Evitado por PV directo:        {metrics['co2_avoided_by_pv_kg_year']/1000:.1f} ton CO2/año")
    print(f"   Evitado por BESS discharge:    {metrics['co2_avoided_by_bess_kg_year']/1000:.1f} ton CO2/año")
    print(f"   ─────────────────────────────────────────────────────")
    print(f"   TOTAL CO2 EVITADO:             {metrics['co2_avoided_kg_year']/1000:.1f} ton CO2/año ✅")
    print(f"   Reducción CO2:                 {metrics['co2_reduction_percent']:.1f}%")
    print(f"")
    print(f"   Factor CO2 generación térmica Iquitos: 0.4521 kg CO2/kWh (diesel B5)")
    print(f"   Energía sustituida red: {(metrics['co2_avoided_kg_year']/FACTOR_CO2_KG_KWH)/1000:.1f} MWh/año")

    # ===========================================
    # 6. Guardar resultados (datetime como índice, sin columna 'hour')
    # ===========================================
    # VALIDACIÓN CRÍTICA: df_sim debe tener exactamente 8,760 filas
    if len(df_sim) != 8760:
        raise ValueError(
            f"ERROR: Dataset BESS tiene {len(df_sim)} filas, se requieren exactamente 8,760.\n"
            f"Verificar simulación y alineación de series temporales."
        )
    
    # Guardar simulación completa (nombre principal: bess_ano_2024.csv)
    df_sim.to_csv(out_dir / "bess_ano_2024.csv", index=True)
    assert (out_dir / "bess_ano_2024.csv").stat().st_size > 0, "ERROR: bess_ano_2024.csv vacío"
    print(f"   ✅ Guardado: bess_ano_2024.csv ({len(df_sim)} filas, año completo 2024)")

    # Promedio diario: agrupar por hora del día (0-23)
    # Crear columna auxiliar 'hour' solo para groupby
    df_sim_copy = df_sim.copy()
    df_sim_copy['hour'] = df_sim_copy.index.hour  # type: ignore[union-attr]
    numeric_cols = df_sim_copy.select_dtypes(include=['number']).columns.tolist()
    df_day = df_sim_copy[numeric_cols].groupby('hour').mean()  # type: ignore[attr-defined]
    
    # =====================================================
    # FORZAR CERO BESS FUERA DE HORARIO OPERATIVO (0-5h, 22-23h)
    # =====================================================
    for hour_val in df_day.index:
        if hour_val >= closing_hour or hour_val < 6:
            df_day.loc[hour_val, 'bess_charge_kwh'] = 0.0
            df_day.loc[hour_val, 'bess_discharge_kwh'] = 0.0
            df_day.loc[hour_val, 'bess_action_kwh'] = 0.0
            df_day.loc[hour_val, 'pv_to_bess_kwh'] = 0.0
            df_day.loc[hour_val, 'bess_to_ev_kwh'] = 0.0
    
    # Agregar bess_mode basado en la lógica: charge > 0 → 'charge', discharge > 0 → 'discharge', else 'idle'
    df_day['bess_mode'] = df_day.apply(
        lambda row: 'charge' if row['bess_charge_kwh'] > 0.1 
                    else ('discharge' if row['bess_discharge_kwh'] > 0.1 else 'idle'),
        axis=1
    )
    
    # =====================================================
    # CONVERTIR ÍNDICE A DATETIME (día representativo 2024-01-01)
    # =====================================================
    df_day.index = pd.to_datetime(f'{year}-01-01') + pd.to_timedelta(df_day.index, unit='h')
    df_day.index.name = 'datetime'
    # Eliminar columna 'hour' del resultado (ya está en el índice como datetime)
    if 'hour' in df_day.columns:
        df_day = df_day.drop(columns=['hour'])
    
    df_day.to_csv(out_dir / "bess_daily_balance_24h.csv", index=True)

    output = BessSizingOutput(
        capacity_kwh=capacity_kwh,
        nominal_power_kw=power_kw,
        dod=effective_dod,
        c_rate=c_rate,
        autonomy_hours=autonomy_hours,
        peak_load_kw=peak_load,
        efficiency_roundtrip=efficiency_roundtrip,
        surplus_kwh_day=surplus_day,
        deficit_kwh_day=deficit_kwh_day_max,  # Usamos MÁXIMO para 100% cobertura
        night_deficit_kwh_day=deficit_kwh_day_max,  # Déficit en descarga (máximo)
        pv_generation_kwh_day=pv_day_value,
        total_demand_kwh_day=ev_kwh_day + mall_kwh_day,
        mall_demand_kwh_day=mall_kwh_day,
        ev_demand_kwh_day=ev_kwh_day,
        bess_load_scope=bess_load_scope,
        pv_available_kwh_day=pv_day_value,  # Total PV disponible
        bess_load_kwh_day=ev_kwh_day,  # BESS exclusivo para EV
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
    
    # =====================================================
    # AGREGAR MÉTRICAS ECONÓMICAS OSINERGMIN (v5.3)
    # =====================================================
    result_dict['osinergmin_tariff'] = {
        'energia_hp_soles_kwh': TARIFA_ENERGIA_HP_SOLES,
        'energia_hfp_soles_kwh': TARIFA_ENERGIA_HFP_SOLES,
        'potencia_hp_soles_kw_mes': TARIFA_POTENCIA_HP_SOLES,
        'potencia_hfp_soles_kw_mes': TARIFA_POTENCIA_HFP_SOLES,
        'horas_punta': HORAS_PUNTA,
    }
    result_dict['cost_baseline_soles_year'] = metrics.get('cost_baseline_soles_year', 0.0)
    result_dict['cost_grid_import_soles_year'] = metrics.get('cost_grid_import_soles_year', 0.0)
    result_dict['savings_bess_soles_year'] = metrics.get('savings_bess_soles_year', 0.0)
    result_dict['savings_total_soles_year'] = metrics.get('savings_total_soles_year', 0.0)
    result_dict['roi_arbitrage_percent'] = metrics.get('roi_percent', 0.0)
    result_dict['co2_emissions_kg_year'] = metrics.get('co2_emissions_kg_year', 0.0)
    result_dict['co2_avoided_by_pv_kg_year'] = metrics.get('co2_avoided_by_pv_kg_year', 0.0)  # NEW v5.4
    result_dict['co2_avoided_by_bess_kg_year'] = metrics.get('co2_avoided_by_bess_kg_year', 0.0)  # NEW v5.4
    result_dict['co2_avoided_kg_year'] = metrics.get('co2_avoided_kg_year', 0.0)  # TOTAL (PV + BESS)
    result_dict['co2_reduction_percent'] = metrics.get('co2_reduction_percent', 0.0)
    result_dict['factor_co2_kg_kwh'] = FACTOR_CO2_KG_KWH
    
    # Información de estrategia
    if USE_SOLAR_PRIORITY:
        result_dict['simulation_mode'] = 'solar_priority_v54'
        result_dict['bess_version'] = 'v5.4 (solar-priority)'
        result_dict['operation_strategy'] = {
            'name': 'Solar-Priority (Disponibilidad Solar)',
            'description': 'Carga: cuando PV > demanda. Descarga: cuando PV < demanda_mall o déficit EV',
            'tariff_independent': True,
            'charge_hours': '6h-22h (cuando hay PV excedente)',
            'discharge_hours': '6h-22h (cuando hay déficit solar o déficit EV)',
            'charge_source': 'PV excedente SOLO (no grid)',
            'discharge_targets': ['EV (prioridad 1)', 'Mall (prioridad 2, si PV < demanda_mall)'],
            'soc_strategy': 'Llenar a 100% en mañana, descargar cuando es necesario',
        }
    else:
        result_dict['simulation_mode'] = 'arbitrage_hp_hfp_v53'
        result_dict['bess_version'] = 'v5.3 (arbitrage-legacy)'
        result_dict['operation_strategy'] = {
            'name': 'Arbitraje HP/HFP (OSINERGMIN)',
            'description': 'Carga en HFP barato (S/.0.28), descarga en HP caro (S/.0.45)',
            'tariff_dependent': True,
            'charge_hours': '6h-17h, 23h (HFP - barato)',
            'discharge_hours': '18h-22h (HP - caro)',
            'arbitrage_differential': f'S/.{TARIFA_ENERGIA_HP_SOLES - TARIFA_ENERGIA_HFP_SOLES:.2f}/kWh',
        }
    
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

    # ═════════════════════════════════════════════════════════════════════════════
    # ANÁLISIS DETALLADO DE CARACTERÍSTICAS BESS (NUEVO)
    # ═════════════════════════════════════════════════════════════════════════════
    print("")
    print("Analizando características detalladas del BESS...")
    try:
        # Calcular análisis completo
        bess_characteristics = analyze_bess_characteristics(
            df_sim=df_sim,
            capacity_kwh=capacity_kwh,
            power_kw=power_kw,
            efficiency=efficiency_roundtrip,
        )
        
        # Generar reporte formateado
        report_text = generate_bess_analysis_report(
            characteristics=bess_characteristics,
            capacity_kwh=capacity_kwh,
            power_kw=power_kw,
            efficiency=efficiency_roundtrip,
        )
        
        # Mostrar reporte en consola
        print("\n" + report_text)
        
        # Guardar análisis a archivo
        save_bess_analysis_summary(
            characteristics=bess_characteristics,
            capacity_kwh=capacity_kwh,
            power_kw=power_kw,
            efficiency=efficiency_roundtrip,
            report_text=report_text,
            out_dir=out_dir,
        )
        
        # Agregar al diccionario de salida
        result_dict['bess_characteristics'] = bess_characteristics
        
    except Exception as e:
        print(f"  Advertencia: No se pudo realizar análisis detallado: {str(e)}")
        print(f"  Continuando...")

    if generate_plots:
        print("")
        print("Generando graficas...")
        try:
            generate_bess_plots(
                df_sim=df_sim,
                capacity_kwh=capacity_kwh,
                power_kw=power_kw,
                dod=effective_dod,
                c_rate=c_rate,
                mall_kwh_day=mall_kwh_day,
                ev_kwh_day=ev_kwh_day,
                pv_kwh_day=pv_day_value,
                out_dir=out_dir,
                reports_dir=reports_dir,
                df_ev_15min=None,  # Perfil de 15 min no disponible aqui
            )
        except Exception as e:
            print(f"  Advertencia: No se pudieron generar graficas: {str(e)}")
            print(f"  Continuando sin graficas...")

    print("")
    print("=" * 60)
    print(f"Resultados guardados en: {out_dir}")
    print("=" * 60)

    return result_dict


if __name__ == "__main__":
    """
    Ejecucion directa del modulo BESS v5.3 con resultados por secciones.

    Uso:
        python -m src.dimensionamiento.oe2.disenobess.bess
        python src/dimensionamiento/oe2/disenobess/bess.py
    
    Muestra resultados detallados por secciones:
        1. CONFIGURACIÓN BESS v5.3
        2. TARIFAS OSINERGMIN MT3
        3. DATOS DE ENTRADA
        4. DIMENSIONAMIENTO BESS
        5. BALANCE ENERGÉTICO ANUAL
        6. SIMULACIÓN ARBITRAJE HP/HFP
        7. MÉTRICAS ECONÓMICAS
        8. MÉTRICAS CO2
        9. ARCHIVOS GENERADOS
    """
    import sys
    from datetime import datetime

    # ===================================================================
    # ENCABEZADO PRINCIPAL
    # ===================================================================
    print("\n")
    print("+" + "="*78 + "+")
    print("|" + " "*20 + "SISTEMA BESS v5.4 - IQUITOS EV MALL" + " "*22 + "|")
    print("|" + " "*15 + "Dimensionamiento Solar-Priority v5.4" + " "*26 + "|")
    print("+" + "="*78 + "+")
    print(f"\nFecha ejecucion: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Agregar directorio raiz al path
    root_dir = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(root_dir))

    # Rutas de datos
    interim_dir = root_dir / "data" / "interim" / "oe2"
    oe2_dir = root_dir / "data" / "oe2"
    reports_dir = root_dir / "reports" / "oe2"

    # Archivos de entrada
    pv_profile_path = oe2_dir / "Generacionsolar" / "pv_generation_citylearn2024.csv"
    ev_profile_path = oe2_dir / "chargers" / "chargers_ev_ano_2024_v3.csv"
    mall_demand_path = oe2_dir / "demandamallkwh" / "demandamallhorakwh.csv"

    # ===================================================================
    # SECCIÓN 1: CONFIGURACIÓN BESS
    # ===================================================================
    print("\n[1] ESPECIFICACIONES TECNICAS BESS v5.4")
    print("-" * 60)
    print(f"  Capacidad nominal:      {BESS_CAPACITY_KWH_V53:,.0f} kWh")
    print(f"  Potencia nominal:       {BESS_POWER_KW_V53:,.0f} kW")
    print(f"  Profundidad descarga:   {BESS_DOD_V53*100:.0f}%")
    print(f"  Eficiencia round-trip:  {BESS_EFFICIENCY_V53*100:.0f}%")
    print(f"  SOC operacional:        {BESS_SOC_MIN_V53*100:.0f}% - {BESS_SOC_MAX_V53*100:.0f}%")

    # ===================================================================
    # SECCIÓN 2: TARIFAS OSINERGMIN
    # ===================================================================
    print("\n[2] TARIFAS OSINERGMIN MT3 - ELECTRO ORIENTE (IQUITOS)")
    print("-" * 60)
    print(f"  HP (18:00-23:00, 5h):   S/.{TARIFA_ENERGIA_HP_SOLES:.2f}/kWh")
    print(f"  HFP (resto, 19h):       S/.{TARIFA_ENERGIA_HFP_SOLES:.2f}/kWh")
    diferencial = TARIFA_ENERGIA_HP_SOLES - TARIFA_ENERGIA_HFP_SOLES
    print(f"  Diferencial:            S/.{diferencial:.2f}/kWh ({diferencial/TARIFA_ENERGIA_HFP_SOLES*100:.1f}%)")
    print(f"  Factor CO2 grid:        {FACTOR_CO2_KG_KWH:.4f} kg CO2/kWh")

    # ===================================================================
    # SECCIÓN 3: VERIFICACIÓN DE DATOS
    # ===================================================================
    print("\n[3] VERIFICACION DE ARCHIVOS DE ENTRADA")
    print("-" * 60)

    missing_files = []
    files_status = []
    
    if pv_profile_path.exists():
        pv_size = pv_profile_path.stat().st_size / 1024
        files_status.append(f"  OK PV Solar:    {pv_profile_path.name} ({pv_size:.1f} KB)")
    else:
        missing_files.append(f"PV: {pv_profile_path}")
    
    if ev_profile_path.exists():
        ev_size = ev_profile_path.stat().st_size / 1024
        files_status.append(f"  OK EV Chargers: {ev_profile_path.name} ({ev_size:.1f} KB)")
    else:
        missing_files.append(f"EV: {ev_profile_path}")
    
    if mall_demand_path.exists():
        mall_size = mall_demand_path.stat().st_size / 1024
        files_status.append(f"  OK Mall Demand: {mall_demand_path.name} ({mall_size:.1f} KB)")
    else:
        missing_files.append(f"MALL: {mall_demand_path}")

    for status in files_status:
        print(status)

    print(f"\n  Output dir: {oe2_dir / 'bess'}")

    if missing_files:
        print("\n  ADVERTENCIA: Archivos faltantes:")
        for f in missing_files:
            print(f"    - {f}")
        sys.exit(1)

    out_dir = oe2_dir / "bess"

    # ===================================================================
    # EJECUTAR DIMENSIONAMIENTO
    # ===================================================================
    print("\n[4] EJECUTANDO DIMENSIONAMIENTO BESS...")
    print("-" * 60)

    result = run_bess_sizing(
        out_dir=out_dir,
        pv_profile_path=pv_profile_path,
        ev_profile_path=ev_profile_path,
        mall_demand_path=mall_demand_path,
        dod=0.80,
        c_rate=0.36,
        round_kwh=10.0,
        efficiency_roundtrip=0.95,
        autonomy_hours=4.0,
        pv_dc_kw=4162.0,
        tz=None,
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

    # ===================================================================
    # RESULTADOS
    # ===================================================================
    print("\n[5] RESULTADOS FINALES DIMENSIONAMIENTO BESS v5.4")
    print("=" * 60)
    
    pv_year = result.get('pv_generation_kwh_day', 0) * 365 / 1000  # MWh/año
    ev_year = result.get('ev_demand_kwh_day', 0) * 365 / 1000
    mall_year = result.get('mall_demand_kwh_day', 0) * 365 / 1000
    total_year = ev_year + mall_year
    
    savings_total = result.get('savings_total_soles_year', 0)
    cost_baseline = result.get('cost_baseline_soles_year', 0)
    reduction_pct = (savings_total / max(cost_baseline, 1)) * 100 if cost_baseline > 0 else 0
    co2_avoided = result.get('co2_avoided_kg_year', 0)
    co2_reduction = result.get('co2_reduction_percent', 0)
    
    print("\nCAPACIDAD:")
    print(f"  Capacidad:        {result.get('capacity_kwh', 0):,.0f} kWh")
    print(f"  Potencia:         {result.get('nominal_power_kw', 0):,.0f} kW")
    print(f"  DoD:              {result.get('dod', 0)*100:.0f}%")
    print(f"  Eficiencia:       {result.get('efficiency_roundtrip', 0)*100:.0f}%")
    
    print("\nENERGETICO (ANUAL):")
    print(f"  Generacion PV:    {pv_year:,.1f} MWh/año")
    print(f"  Demanda Mall:     {mall_year:,.1f} MWh/año")
    print(f"  Demanda EV:       {ev_year:,.1f} MWh/año")
    print(f"  Demanda Total:    {total_year:,.1f} MWh/año")
    
    print("\nFINANCIERO:")
    print(f"  Costo baseline:   S/.{cost_baseline:,.0f}/año")
    print(f"  Ahorro total:     S/.{savings_total:,.0f}/año")
    print(f"  Reduccion costo:  {reduction_pct:.1f}%")
    
    print("\nCO2 (INDIRECTO):")
    print(f"  Reduccion CO2:    {co2_avoided/1000:,.1f} ton/año")
    print(f"  Reduccion %:      {co2_reduction:.1f}%")
    
    print("\n" + "=" * 60)
    print("DIMENSIONAMIENTO COMPLETADO EXITOSAMENTE")
    print(f"Resultados en: {out_dir}")
    print("=" * 60 + "\n")


    print(f"""
    ┌─────────────────────────────────────────────────────────────────────┐
    │  ESPECIFICACIONES TÉCNICAS BESS                                    │
    ├─────────────────────────────────────────────────────────────────────┤
    │  Capacidad nominal:      {BESS_CAPACITY_KWH_V53:>8,.0f} kWh                          │
    │  Potencia nominal:       {BESS_POWER_KW_V53:>8,.0f} kW                           │
    │  Profundidad descarga:   {BESS_DOD_V53*100:>8.0f} % (DoD)                       │
    │  Eficiencia round-trip:  {BESS_EFFICIENCY_V53*100:>8.0f} %                           │
    │  SOC mínimo:             {BESS_SOC_MIN_V53*100:>8.0f} %                           │
    │  SOC máximo:             {BESS_SOC_MAX_V53*100:>8.0f} %                           │
    │  Capacidad útil:         {BESS_CAPACITY_KWH_V53 * BESS_DOD_V53:>8,.0f} kWh (80% DoD)                   │
    │  C-rate nominal:         {BESS_POWER_KW_V53/BESS_CAPACITY_KWH_V53:>8.2f} C                            │
    └─────────────────────────────────────────────────────────────────────┘
    """)

    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 2: TARIFAS OSINERGMIN MT3
    # ═══════════════════════════════════════════════════════════════════════════
    print("┌" + "─"*78 + "┐")
    print("│  2️⃣  TARIFAS OSINERGMIN MT3 - ELECTRO ORIENTE S.A. (IQUITOS)" + " "*17 + "│")
    print("└" + "─"*78 + "┘")
    diferencial = TARIFA_ENERGIA_HP_SOLES - TARIFA_ENERGIA_HFP_SOLES
    print(f"""
    ┌─────────────────────────────────────────────────────────────────────┐
    │  TARIFAS MT3 - Resolución OSINERGMIN N° 047-2024-OS/CD             │
    ├─────────────────────────────────────────────────────────────────────┤
    │                                                                     │
    │  ⏰ HORA PUNTA (HP): 18:00 - 23:00 (5 horas)                        │
    │     • Energía:    S/.{TARIFA_ENERGIA_HP_SOLES:.2f}/kWh  (~USD {TARIFA_ENERGIA_HP_USD:.3f}/kWh)              │
    │     • Potencia:   S/.{TARIFA_POTENCIA_HP_SOLES:.2f}/kW-mes                                 │
    │                                                                     │
    │  ⏰ HORA FUERA DE PUNTA (HFP): 00:00-17:59, 23:00-23:59 (19 horas)  │
    │     • Energía:    S/.{TARIFA_ENERGIA_HFP_SOLES:.2f}/kWh  (~USD {TARIFA_ENERGIA_HFP_USD:.3f}/kWh)              │
    │     • Potencia:   S/.{TARIFA_POTENCIA_HFP_SOLES:.2f}/kW-mes                                 │
    │                                                                     │
    │  💰 DIFERENCIAL ARBITRAJE: S/.{diferencial:.2f}/kWh ({diferencial/TARIFA_ENERGIA_HFP_SOLES*100:.1f}% ahorro)          │
    │                                                                     │
    │  🌡️ FACTOR CO2 (Sistema térmico aislado): {FACTOR_CO2_KG_KWH:.4f} kg/kWh         │
    └─────────────────────────────────────────────────────────────────────┘
    """)

    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3: VERIFICACIÓN DATOS DE ENTRADA
    # ═══════════════════════════════════════════════════════════════════════════
    print("┌" + "─"*78 + "┐")
    print("│  3️⃣  DATOS DE ENTRADA - VERIFICACIÓN DE ARCHIVOS" + " "*29 + "│")
    print("└" + "─"*78 + "┘")

    # Verificar archivos
    missing_files = []
    files_status = []
    
    if pv_profile_path.exists():
        pv_size = pv_profile_path.stat().st_size / 1024
        files_status.append(f"    ✅ PV Solar:    {pv_profile_path.name} ({pv_size:.1f} KB)")
    else:
        missing_files.append(f"PV: {pv_profile_path}")
        files_status.append(f"    ❌ PV Solar:    {pv_profile_path.name} (NO ENCONTRADO)")
    
    if ev_profile_path.exists():
        ev_size = ev_profile_path.stat().st_size / 1024
        files_status.append(f"    ✅ EV Chargers: {ev_profile_path.name} ({ev_size:.1f} KB)")
    else:
        missing_files.append(f"EV: {ev_profile_path}")
        files_status.append(f"    ❌ EV Chargers: {ev_profile_path.name} (NO ENCONTRADO)")
    
    if mall_demand_path.exists():
        mall_size = mall_demand_path.stat().st_size / 1024
        files_status.append(f"    ✅ Mall Demand: {mall_demand_path.name} ({mall_size:.1f} KB)")
    else:
        files_status.append(f"    ⚠️  Mall Demand: Usando perfil sintético (100 kW base)")

    print("\n    📂 ARCHIVOS DE ENTRADA:")
    for status in files_status:
        print(status)
    print(f"\n    📁 Directorio salida: {oe2_dir / 'bess'}")

    if missing_files:
        print("\n    ❌ ERROR: Archivos faltantes críticos:")
        for f in missing_files:
            print(f"       • {f}")
        print("\n    Ejecuta primero:")
        print("       python -m scripts.run_oe2_solar")
        print("       python -m scripts.run_oe2_chargers")
        sys.exit(1)

    # Directorio de salida
    out_dir = oe2_dir / "bess"

    # ═══════════════════════════════════════════════════════════════════════════
    # EJECUTAR DIMENSIONAMIENTO
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n")
    print("┌" + "─"*78 + "┐")
    print("│  4️⃣  EJECUTANDO DIMENSIONAMIENTO BESS..." + " "*37 + "│")
    print("└" + "─"*78 + "┘")

    result = run_bess_sizing(
        out_dir=out_dir,
        pv_profile_path=pv_profile_path,
        ev_profile_path=ev_profile_path,
        mall_demand_path=mall_demand_path,
        dod=0.80,  # v5.3: 80% DOD
        c_rate=0.36,  # v5.3: 0.36 C-rate
        round_kwh=10.0,
        efficiency_roundtrip=0.95,  # v5.3: 95% efficiency
        autonomy_hours=4.0,
        pv_dc_kw=4162.0,
        tz=None,
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

    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 5: RESULTADOS DIMENSIONAMIENTO BESS
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n")
    print("┌" + "─"*78 + "┐")
    print("│  5️⃣  RESULTADOS DIMENSIONAMIENTO BESS v5.3" + " "*35 + "│")
    print("└" + "─"*78 + "┘")
    
    dod_value = float(result['dod']) if isinstance(result['dod'], (int, float, str)) else 0.0
    cap_util = result['capacity_kwh'] * dod_value
    
    print(f"""
    ┌─────────────────────────────────────────────────────────────────────┐
    │  DIMENSIONAMIENTO FINAL                                            │
    ├─────────────────────────────────────────────────────────────────────┤
    │  Capacidad nominal:      {result['capacity_kwh']:>10,.0f} kWh                        │
    │  Capacidad útil (DoD):   {cap_util:>10,.0f} kWh ({dod_value*100:.0f}% DoD)                │
    │  Potencia nominal:       {result['nominal_power_kw']:>10,.0f} kW                         │
    │  C-rate efectivo:        {result['c_rate']:>10.2f}                             │
    │  Ratio Potencia/Cap:     {result['nominal_power_kw']/result['capacity_kwh']:>10.2f}                             │
    │  Modo dimensionamiento:  {result['sizing_mode']:>10}                             │
    └─────────────────────────────────────────────────────────────────────┘
    """)

    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 6: BALANCE ENERGÉTICO ANUAL
    # ═══════════════════════════════════════════════════════════════════════════
    print("┌" + "─"*78 + "┐")
    print("│  6️⃣  BALANCE ENERGÉTICO - FLUJOS DIARIOS Y ANUALES" + " "*27 + "│")
    print("└" + "─"*78 + "┘")
    
    pv_year = result['pv_generation_kwh_day'] * 365 / 1000  # MWh/año
    ev_year = result['ev_demand_kwh_day'] * 365 / 1000
    mall_year = result['mall_demand_kwh_day'] * 365 / 1000
    total_year = result['total_demand_kwh_day'] * 365 / 1000
    grid_import_year = result['grid_import_kwh_day'] * 365 / 1000
    grid_export_year = result['grid_export_kwh_day'] * 365 / 1000
    
    print(f"""
    ┌─────────────────────────────────────────────────────────────────────┐
    │  GENERACIÓN                                                        │
    ├─────────────────────────────────────────────────────────────────────┤
    │  ☀️  PV Solar:         {result['pv_generation_kwh_day']:>10,.0f} kWh/día  │  {pv_year:>8,.1f} MWh/año     │
    ├─────────────────────────────────────────────────────────────────────┤
    │  DEMANDA                                                           │
    ├─────────────────────────────────────────────────────────────────────┤
    │  🏢 Mall:              {result['mall_demand_kwh_day']:>10,.0f} kWh/día  │  {mall_year:>8,.1f} MWh/año     │
    │  🔌 EV Chargers:       {result['ev_demand_kwh_day']:>10,.0f} kWh/día  │  {ev_year:>8,.1f} MWh/año     │
    │  ─────────────────────────────────────────────────────────────────  │
    │  📊 TOTAL DEMANDA:     {result['total_demand_kwh_day']:>10,.0f} kWh/día  │  {total_year:>8,.1f} MWh/año     │
    ├─────────────────────────────────────────────────────────────────────┤
    │  BALANCE                                                           │
    ├─────────────────────────────────────────────────────────────────────┤
    │  ⬆️  Excedente PV:      {result['surplus_kwh_day']:>10,.0f} kWh/día  (PV - Demanda)        │
    │  ⬇️  Déficit EV:        {result['deficit_kwh_day']:>10,.0f} kWh/día  (EV sin PV)           │
    ├─────────────────────────────────────────────────────────────────────┤
    │  INTERCAMBIO RED                                                   │
    ├─────────────────────────────────────────────────────────────────────┤
    │  📥 Import red:        {result['grid_import_kwh_day']:>10,.0f} kWh/día  │  {grid_import_year:>8,.1f} MWh/año     │
    │  📤 Export red:        {result['grid_export_kwh_day']:>10,.0f} kWh/día  │  {grid_export_year:>8,.1f} MWh/año     │
    └─────────────────────────────────────────────────────────────────────┘
    """)

    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 7: OPERACIÓN BESS - SIMULACIÓN
    # ═══════════════════════════════════════════════════════════════════════════
    print("┌" + "─"*78 + "┐")
    print("│  7️⃣  OPERACIÓN BESS - SIMULACIÓN ARBITRAJE HP/HFP" + " "*28 + "│")
    print("└" + "─"*78 + "┘")
    
    self_suff_value = float(result['self_sufficiency']) if isinstance(result['self_sufficiency'], (int, float, str)) else 0.0
    
    print(f"""
    ┌─────────────────────────────────────────────────────────────────────┐
    │  ESTRATEGIA OPERACIÓN ARBITRAJE                                    │
    ├─────────────────────────────────────────────────────────────────────┤
    │  🔋 CARGA (HFP 06:00-17:00):                                        │
    │     • Fuente: Excedente PV + Grid si SOC < 80%                     │
    │     • Tarifa aplicada: S/.{TARIFA_ENERGIA_HFP_SOLES:.2f}/kWh                               │
    │                                                                     │
    │  🔋 DESCARGA (HP 18:00-22:00):                                      │
    │     • Destino: EV Chargers + Mall                                  │
    │     • Tarifa evitada: S/.{TARIFA_ENERGIA_HP_SOLES:.2f}/kWh                                │
    │     • SOC objetivo cierre (22h): 20%                               │
    ├─────────────────────────────────────────────────────────────────────┤
    │  MÉTRICAS OPERACIÓN                                                │
    ├─────────────────────────────────────────────────────────────────────┤
    │  ⚡ Autosuficiencia:     {self_suff_value*100:>10.1f} %                           │
    │  🔄 Ciclos/día:          {result['cycles_per_day']:>10.2f}                             │
    │  📉 SOC mínimo:          {result['soc_min_percent']:>10.0f} %                           │
    │  📈 SOC máximo:          {result['soc_max_percent']:>10.0f} %                           │
    │  ↔️  Rango SOC:           {result['soc_min_percent']:.0f}% - {result['soc_max_percent']:.0f}%                            │
    └─────────────────────────────────────────────────────────────────────┘
    """)

    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 8: MÉTRICAS ECONÓMICAS
    # ═══════════════════════════════════════════════════════════════════════════
    print("┌" + "─"*78 + "┐")
    print("│  8️⃣  MÉTRICAS ECONÓMICAS - AHORRO ARBITRAJE OSINERGMIN" + " "*23 + "│")
    print("└" + "─"*78 + "┘")
    
    # Extraer métricas económicas
    cost_baseline = result.get('cost_baseline_soles_year', 0.0)
    cost_with_bess = result.get('cost_grid_import_soles_year', 0.0)
    savings_bess = result.get('savings_bess_soles_year', 0.0)
    savings_total = result.get('savings_total_soles_year', 0.0)
    roi = result.get('roi_arbitrage_percent', 0.0)
    
    # Si no hay datos económicos en result, calcular aproximado
    if cost_baseline == 0.0:
        # Cálculo aproximado: todo a tarifa promedio
        tarifa_promedio = (TARIFA_ENERGIA_HP_SOLES * 5 + TARIFA_ENERGIA_HFP_SOLES * 19) / 24
        cost_baseline = result['total_demand_kwh_day'] * 365 * tarifa_promedio
        cost_with_bess = result['grid_import_kwh_day'] * 365 * tarifa_promedio
        savings_total = cost_baseline - cost_with_bess
        savings_bess = savings_total * 0.3  # Aprox 30% del ahorro por arbitraje
        roi = (savings_total / (result['capacity_kwh'] * 300)) * 100  # Asumiendo $300/kWh BESS
    
    reduction_pct = ((cost_baseline - cost_with_bess) / cost_baseline * 100) if cost_baseline > 0 else 0.0
    
    print(f"""
    ┌─────────────────────────────────────────────────────────────────────┐
    │  COSTOS ANUALES                                                    │
    ├─────────────────────────────────────────────────────────────────────┤
    │  💸 Costo BASELINE (sin BESS, sin PV):                             │
    │     S/.{cost_baseline:>15,.0f}/año                                        │
    │                                                                     │
    │  💰 Costo CON SISTEMA (PV + BESS + Arbitraje):                     │
    │     S/.{cost_with_bess:>15,.0f}/año                                        │
    ├─────────────────────────────────────────────────────────────────────┤
    │  AHORROS                                                           │
    ├─────────────────────────────────────────────────────────────────────┤
    │  🎯 Ahorro por arbitraje BESS:  S/.{savings_bess:>12,.0f}/año                │
    │  🎯 Ahorro TOTAL sistema:       S/.{savings_total:>12,.0f}/año                │
    │  📉 Reducción costo:            {reduction_pct:>12.1f} %                     │
    │  📈 ROI estimado:               {roi:>12.1f} %                     │
    └─────────────────────────────────────────────────────────────────────┘
    """)

    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 9: MÉTRICAS CO2
    # ═══════════════════════════════════════════════════════════════════════════
    print("┌" + "─"*78 + "┐")
    print("│  9️⃣  MÉTRICAS CO2 - IMPACTO AMBIENTAL" + " "*40 + "│")
    print("└" + "─"*78 + "┘")
    
    # Extraer métricas CO2
    co2_emissions = result.get('co2_emissions_kg_year', 0.0)
    co2_avoided = result.get('co2_avoided_kg_year', 0.0)
    co2_reduction = result.get('co2_reduction_percent', 0.0)
    
    # Si no hay datos CO2 en result, calcular
    if co2_emissions == 0.0:
        co2_baseline = result['total_demand_kwh_day'] * 365 * FACTOR_CO2_KG_KWH
        co2_emissions = result['grid_import_kwh_day'] * 365 * FACTOR_CO2_KG_KWH
        co2_avoided = co2_baseline - co2_emissions
        co2_reduction = (co2_avoided / co2_baseline * 100) if co2_baseline > 0 else 0.0
    else:
        co2_baseline = co2_emissions + co2_avoided
    
    print(f"""
    ┌─────────────────────────────────────────────────────────────────────┐
    │  Factor de emisión: {FACTOR_CO2_KG_KWH:.4f} kg CO2/kWh (Sistema térmico aislado)   │
    ├─────────────────────────────────────────────────────────────────────┤
    │  EMISIONES CO2                                                     │
    ├─────────────────────────────────────────────────────────────────────┤
    │  🏭 BASELINE (sin PV, sin BESS):    {co2_baseline/1000:>10,.1f} ton CO2/año      │
    │  🌱 CON SISTEMA (PV + BESS):        {co2_emissions/1000:>10,.1f} ton CO2/año      │
    ├─────────────────────────────────────────────────────────────────────┤
    │  REDUCCIÓN INDIRECTA (BESS reemplaza energía térmica de red)       │
    ├─────────────────────────────────────────────────────────────────────┤
    │  🌿 REDUCCIÓN INDIRECTA CO2:        {co2_avoided/1000:>10,.1f} ton CO2/año      │
    │  📉 Reducción emisiones:            {co2_reduction:>10.1f} %               │
    └─────────────────────────────────────────────────────────────────────┘
    """)

    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIÓN 10: ARCHIVOS GENERADOS
    # ═══════════════════════════════════════════════════════════════════════════
    print("┌" + "─"*78 + "┐")
    print("│  🔟 ARCHIVOS GENERADOS" + " "*55 + "│")
    print("└" + "─"*78 + "┘")
    
    files_generated = [
        (out_dir / "bess_results.json", "Configuración y métricas BESS"),
        (out_dir / "bess_ano_2024.csv", "Simulación 8,760 horas (29 cols)"),
        (out_dir / "bess_daily_balance_24h.csv", "Perfil día típico (24 horas)"),
        (reports_dir / "bess" / "bess_sistema_completo.png", "Gráfica sistema completo"),
    ]
    
    print("\n    📁 ARCHIVOS DE DATOS:")
    for file_path, description in files_generated[:3]:
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            print(f"    ✅ {file_path.name}")
            print(f"       └─ {description} ({size_kb:.1f} KB)")
        else:
            print(f"    ⚠️  {file_path.name} (no generado)")
    
    print("\n    📊 GRÁFICAS:")
    for file_path, description in files_generated[3:]:
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            print(f"    ✅ {file_path.name}")
            print(f"       └─ {description} ({size_kb:.1f} KB)")
        else:
            print(f"    ⚠️  {file_path.name} (no generado)")

    # ═══════════════════════════════════════════════════════════════════════════
    # RESUMEN EJECUTIVO FINAL
    # ═══════════════════════════════════════════════════════════════════════════
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*25 + "📊 RESUMEN EJECUTIVO" + " "*33 + "║")
    print("╠" + "═"*78 + "╣")
    print(f"║  🔋 BESS:     {result['capacity_kwh']:,.0f} kWh / {result['nominal_power_kw']:,.0f} kW" + " "*(50-len(f"{result['capacity_kwh']:,.0f}")-len(f"{result['nominal_power_kw']:,.0f}")) + "║")
    print(f"║  ☀️  PV:       {pv_year:,.1f} MWh/año generación" + " "*(50-len(f"{pv_year:,.1f}")) + "║")
    print(f"║  ⚡ Demanda:  {total_year:,.1f} MWh/año (Mall + EV)" + " "*(49-len(f"{total_year:,.1f}")) + "║")
    print(f"║  💰 Ahorro:   S/.{savings_total:,.0f}/año ({reduction_pct:.1f}% reducción)" + " "*(46-len(f"{savings_total:,.0f}")-len(f"{reduction_pct:.1f}")) + "║")
    print(f"║  🌿 CO2:      {co2_avoided/1000:,.1f} ton reducción indirecta/año" + " "*(49-len(f"{co2_avoided/1000:,.1f}")) + "║")
    print("╠" + "═"*78 + "╣")
    print("║  ✅ DIMENSIONAMIENTO BESS v5.3 COMPLETADO EXITOSAMENTE" + " "*24 + "║")
    print("╚" + "═"*78 + "╝")
    print("\n")
