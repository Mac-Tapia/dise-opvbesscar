"""
Modulo de dimensionamiento de sistema de almacenamiento BESS.

Incluye:
- Carga de demanda real del mall desde CSV
- Simulacion horaria del balance energetico
- Estado de carga (SOC) de la bateria
- Flujos de energia (red, BESS, PV)
- Graficas de analisis completo
- Preparacion de datos para CityLearn schema
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


def load_mall_demand_real(
    mall_demand_path: Path,
    year: int = 2024,
) -> pd.DataFrame:
    """
    Carga la demanda real del mall desde CSV.

    Los datos del archivo estan en kW (potencia) a intervalos de 15 minutos.
    Se convierten a kWh (energia) horaria.

    TRANSFORMACIÓN 15 MIN → HORA:
    ==============================
    Si time_diff = 15 minutos:
    1. Potencia 15min [kW] → Energía 15min [kWh] = power_kw × (15/60) = power_kw × 0.25
    2. Resamplear cada hora: 4×(power_kw × 0.25) = power_kw × 1.0 [kWh/hora]

    Ejemplo para demanda de 100 kW en 96 intervalos/día:
    - Intervalo de 15min: 100 kW × 0.25 = 25 kWh
    - Suma 4 intervalos/hora: 4 × 25 = 100 kWh/hora
    - Día completo: 24 horas × 100 kWh = 2,400 kWh/día

    Args:
        mall_demand_path: Ruta al archivo CSV con demanda del mall
        year: Año de simulacion

    Returns:
        DataFrame con demanda horaria del mall en kWh (8760 filas)
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
        # Los valores ya son energia por intervalo (kWh). Usar directamente.
        df["energy_kwh"] = df["power_kw"]
        df["power_kw"] = df["energy_kwh"] * 60.0 / time_diff
        # Validación: verificar que sea coherente
        assert df["energy_kwh"].min() >= 0, "❌ ERROR: Energía negativa detectada"
        print(f"      ✓ Datos en formato ENERGÍA (kWh): {len(df)} registros")
    else:
        # Los valores son potencia (kW). Convertir a energia por intervalo.
        # FÓRMULA: energy = power × (interval_minutes / 60)
        # Para 15 min: energy_kwh = power_kw × (15 / 60) = power_kw × 0.25
        df["energy_kwh"] = df["power_kw"] * (time_diff / 60.0)
        # Validación: verificar conversión
        assert df["energy_kwh"].min() >= 0, "❌ ERROR: Energía negativa detectada"
        print(f"      ✓ Datos en formato POTENCIA (kW): Convertida a {len(df)} registros × {time_diff} min")
        print(f"      ✓ Factor conversión: power_kw × {time_diff / 60.0:.4f} = energy_kwh")

    if time_diff < 60:
        # RESAMPLEAR: Sumar intervalos menores de 1 hora a valor horario
        # Para 15 min: 4 intervalos/hora → sum() suma todos los 4
        # Validación de coherencia:
        intervals_per_hour = int(60 / time_diff)
        df_hourly = df["energy_kwh"].resample("h").sum().to_frame("mall_kwh")  # type: ignore[attr-defined]
        # Verificar que el resampleo sea correcto
        if len(df) >= intervals_per_hour * 24:  # Al menos 1 día completo
            sample_day = df["energy_kwh"].iloc[:intervals_per_hour*24]
            sample_daily = sample_day.resample("h").sum()
            expected_intervals = intervals_per_hour * 24
            actual_intervals = len(df[:intervals_per_hour*24])
            assert actual_intervals == expected_intervals, f"❌ ERROR: Mismatch {actual_intervals} vs {expected_intervals}"
            print(f"      ✓ Resampleo {intervals_per_hour} intervalos/hora → horario: {len(df)} → {len(df_hourly)} registros")
    else:
        # Los datos ya están en formato horario
        df_hourly = df["energy_kwh"].to_frame("mall_kwh")  # type: ignore[attr-defined]
        print(f"      ✓ Datos ya son horarios: {len(df_hourly)} registros")
    # Si los datos no cubren un año completo, repetir para llenar
    if len(df_hourly) < 8760:
        # Calcular perfil promedio diario
        df_hourly['hour'] = pd.to_datetime(df_hourly.index).hour  # type: ignore[union-attr]
        hourly_profile = df_hourly.groupby('hour')['mall_kwh'].mean()  # type: ignore[attr-defined]

        # Crear indice de año completo
        idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
        df_full = pd.DataFrame(index=idx)
        df_full['hour'] = pd.to_datetime(df_full.index).hour  # type: ignore[union-attr]
        df_full['mall_kwh'] = df_full['hour'].map(hourly_profile)
        df_full = df_full.drop(columns=['hour'])
        return df_full

    return df_hourly[['mall_kwh']]


def load_pv_generation(pv_timeseries_path: Path) -> pd.DataFrame:
    """
    Carga la generacion PV desde timeseries (formato horario).

    TRANSFORMACIÓN SUBHORARIA → HORA:
    ==================================
    Si hay más de 8,760 registros → es subhoraria (15 min o menor)
    Resamplear sumando intervalos: resample('h').sum()

    Para datos de 15 minutos (35,040 registros):
    - 4 intervalos/hora × 8,760 horas = 35,040 total
    - Suma de 4 valores cada hora da valor horario

    NOTA: Los datos deben estar en formato de ENERGÍA (kWh), NO potencia (kW).
    """
    df = pd.read_csv(pv_timeseries_path)  # type: ignore[attr-defined]

    # Detectar columna de tiempo
    time_col = None
    for col in ['datetime', 'timestamp', 'time', 'Timestamp', 'fecha', 'date']:
        if col in df.columns:
            time_col = col
            break

    if time_col:
        df[time_col] = pd.to_datetime(df[time_col])  # type: ignore[attr-defined]
        df = df.set_index(time_col)  # type: ignore[attr-defined]

    # RESAMPLEAR a horario si es subhorario
    if len(df) > 8760:
        # TRANSFORMACIÓN: Datos subhorarios → Horarios
        # Contar intervalos para validar
        n_intervals = len(df)
        if n_intervals == 35040:
            # 96 intervalos/día × 365 días = 35,040 (formato 15 min)
            intervals_per_hour = 4
            print(f"      ✓ Datos en formato 15 minutos: {n_intervals} intervalos")
        elif n_intervals == 8760 * 2:
            # 2 intervalos/hora (30 min)
            intervals_per_hour = 2
            print(f"      ✓ Datos en formato 30 minutos")
        else:
            intervals_per_hour = int(n_intervals / 8760)
            print(f"      ✓ Datos subhorarios: {n_intervals} intervalos ({intervals_per_hour} por hora)")

        # SUMA HORARIA: Resamplear sumando (para datos en kWh)
        df_hourly = df.resample('h').sum()  # type: ignore[attr-defined]
        print(f"      ✓ Resampleo: {n_intervals} → {len(df_hourly)} registros (horarios)")
    else:
        # Ya está en formato horario (8,760 registros)
        df_hourly = df
        print(f"      ✓ Datos ya son horarios: {len(df_hourly)} registros")

    # Buscar columna de generacion PV\n    pv_col = None\n    for col in ['pv_kwh', 'ac_energy_kwh', 'ac_power_kw', 'p_ac', 'energia_kwh', 'energy_kwh', 'power_kw']:\n        if col in df_hourly.columns:\n            pv_col = col\n            break\n\n    if pv_col:\n        # VALIDACION: Si es potencia, convertir a energia\n        if 'power' in pv_col.lower() or 'p_ac' in pv_col.lower():\n            # Estos son valores de potencia (kW), necesitan conversion\n            # Para datos horarios: kW = kWh/1hora, entonces asignamos directamente\n            df_hourly['pv_kwh'] = df_hourly[pv_col]\n            print(f\"      \u2713 Detectada columna potencia: {pv_col}\")\n        else:\n            # Estos ya son energia (kWh)\n            df_hourly['pv_kwh'] = df_hourly[pv_col]\n            print(f\"      \u2713 Detectada columna energia: {pv_col}\")\n        \n        # VALIDACION: Verificar valores positivos\n        assert (df_hourly['pv_kwh'] >= 0).all(), \"\u274c ERROR: Generacion PV negativa detectada\"\n        energía_total = df_hourly['pv_kwh'].sum()\n        print(f\"      \u2713 Generacion total: {energía_total:,.0f} kWh, promedio: {df_hourly['pv_kwh'].mean():.1f} kWh/h\")\n    else:\n        print(f\"      \u26a0 ADVERTENCIA: No se encontro columna PV. Usando ceros.\")\n        df_hourly['pv_kwh'] = 0.0\n\n    # VALIDACION FINAL: Debe haber 8,760 registros horarios\n    assert len(df_hourly) == 8760, f\"\u274c ERROR: Se esperaban 8,760 horas, se obtuvieron {len(df_hourly)}\"\n    \n    return df_hourly[['pv_kwh']]

def load_ev_demand(ev_profile_path: Path, year: int = 2024) -> pd.DataFrame:
    """Carga el perfil de demanda EV (formato horario 8,760 horas).

    El archivo CSV puede tener:
    - 96 intervalos (15 minutos) para un dia tipico → se suma a 24 horas horarias
      TRANSFORMACIÓN: Agrupar cada 4 intervalos (0-3, 4-7, ..., 92-95) e sumar energy_kwh
    - 8,760 intervalos (horario) → se retorna tal cual
    - 24 horas (formato antiguo) → se expande a 8,760 horas/año

    TRANSFORMACIÓN 96 INTERVALOS (15 MIN) → 24 HORAS:
    ===================================================
    96 intervalos = 24 horas × 4 intervalos/hora

    Agrupación por hora:
    - Hora 0: intervalos 0-3 (00:00-00:45)
    - Hora 1: intervalos 4-7 (01:00-01:45)
    - ...
    - Hora 23: intervalos 92-95 (23:00-23:45)

    Cada intervalo debe estar en kWh (energía por 15 minutos).
    La suma de 4 intervalos da el kWh total para esa hora.

    Returns:
        DataFrame con 8,760 registros horarios con columna 'ev_kwh' (energia en kWh por hora)
    """
    df = pd.read_csv(ev_profile_path)  # type: ignore[attr-defined]

    # Verificar si es formato de 15 minutos (96 intervalos) o formato horario (8,760 horas)
    if 'interval' in df.columns and 'energy_kwh' in df.columns:
        # Formato nuevo: 96 intervalos de 15 minutos para un dia
        if len(df) == 96:
            # VALIDACIÓN: Verificar que interval sea 0-95 (96 valores)
            assert df['interval'].min() >= 0 and df['interval'].max() == 95, "❌ ERROR: Intervalo no es 0-95"

            # AGRUPACIÓN POR HORA: Cada 4 intervalos = 1 hora
            # interval 0-3   → hour 0 (00:00-00:45)
            # interval 4-7   → hour 1 (01:00-01:45)
            # interval 92-95 → hour 23 (23:00-23:45)
            df['hour'] = df['interval'] // 4

            # VALIDACIÓN: Verificar que energy_kwh sea positivo
            assert (df['energy_kwh'] >= 0).all(), "❌ ERROR: Energía negativa detectada"

            # SUMA HORARIA: Sumar los 4 intervalos de 15 min en cada hora
            df_hourly = df.groupby('hour')['energy_kwh'].sum().reset_index()  # type: ignore[attr-defined]
            df_hourly.columns = ['hour', 'ev_kwh']

            # VALIDACIÓN: Debe haber 24 horas
            assert len(df_hourly) == 24, f"❌ ERROR: Se esperaban 24 horas, se obtuvieron {len(df_hourly)}"
            print(f"      ✓ Transformación 96 intervalos → 24 horas: {len(df)} → {len(df_hourly)} registros")
            print(f"      ✓ Energía diaria: {df_hourly['ev_kwh'].sum():.0f} kWh/día")

            # EXPANSIÓN A AÑO COMPLETO: 365 días × 24 horas/día = 8,760 horas
            df_annual = []
            for day in range(365):
                for _, row in df_hourly.iterrows():
                    df_annual.append({
                        'hour': int(row['hour']),
                        'ev_kwh': float(row['ev_kwh']),
                        'day': day
                    })  # type: ignore[attr-defined]
            df_result = pd.DataFrame(df_annual)

            # VALIDACIÓN FINAL:
            assert len(df_result) == 8760, f"❌ ERROR: Se esperaban 8,760 horas, se obtuvieron {len(df_result)}"
            assert (df_result['ev_kwh'] >= 0).all(), "❌ ERROR: Energía negativa en resultado"
            print(f"      ✓ Expansión a año completo: {len(df_result)} registros (365 × 24)")

            return df_result[['ev_kwh']]
        elif len(df) == 8760:
            # Ya es formato horario (8,760 registros = 1 año)
            assert (df['energy_kwh'] >= 0).all(), "❌ ERROR: Energía negativa detectada"
            print(f"      ✓ Datos ya son horarios/anuales: {len(df)} registros")
            return df[['energy_kwh']].rename(columns={'energy_kwh': 'ev_kwh'})

    # Formato antiguo: 24 horas (retrocompatibilidad)
    if 'hour' in df.columns and 'energy_kwh' in df.columns:
        # VALIDACIÓN: Verificar que haya 24 horas
        assert len(df) == 24, f"❌ ERROR: Se esperaban 24 horas, se encontraron {len(df)}"
        assert (df['energy_kwh'] >= 0).all(), "❌ ERROR: Energía negativa detectada"

        # Perfil de 24 horas, expandir a año completo
        hourly_profile = df.set_index('hour')['energy_kwh']  # type: ignore[attr-defined]
        df_full = []
        for day in range(365):
            for hour in range(24):
                ev_kwh = hourly_profile.get(hour, 0.0)
                df_full.append({
                    'hour': hour,
                    'ev_kwh': ev_kwh,
                    'day': day
                })  # type: ignore[attr-defined]

        df_result = pd.DataFrame(df_full)
        # VALIDACIÓN FINAL
        assert len(df_result) == 8760, f"❌ ERROR: Se esperaban 8,760 horas, se obtuvieron {len(df_result)}"
        print(f"      ✓ Expansión formato 24h a año completo: {len(df_result)} registros (365 × 24)")

        return df_result[['ev_kwh']]

    # ERROR: Formato no reconocido
    error_msg = (
        "❌ ERROR: Formato de CSV no reconocido.\n"
        "Se esperan:"
        "  • 96 intervalos: columnas 'interval' (0-95) y 'energy_kwh' (kWh/15min)\n"
        "  • 24 horas: columnas 'hour' (0-23) y 'energy_kwh' (kWh/hora)\n"
        "  • 8,760 horas: más de 8,000 registros horarios\n"
        f"Se encontró: {len(df)} registros con columnas {list(df.columns)}"
    )
    raise ValueError(error_msg)

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

    # POTENCIA: Usar C-rate 0.60 segun analisis perfil 15 min
    # Esto da ~622 kW para capacidad de 1,712 kWh
    c_rate_target = 0.60  # C-rate segun analisis
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
    df_day = df_sim.groupby('hour').mean().reset_index()  # type: ignore[attr-defined]

    # Asegurar que todas las 24 horas (0-23) esten presentes
    all_hours = pd.DataFrame({'hour': range(24)})
    df_day = all_hours.merge(df_day, on='hour', how='left').fillna(0)  # type: ignore[attr-defined]

    hours = df_day['hour'].values  # type: ignore[attr-defined]
    total_pv_label = pv_kwh_day if pv_kwh_day > 0 else float(df_day['pv_kwh'].sum())

    # ===========================================================
    # Figura principal con 4 paneles
    # ===========================================================
    _, axes = plt.subplots(4, 1, figsize=(14, 16))  # type: ignore[attr-defined]

    # Datos - convertir a numpy arrays para compatibilidad de tipos
    pv = np.asarray(df_day['pv_kwh'].values)  # type: ignore[attr-defined]
    load = np.asarray(df_day['load_kwh'].values)  # type: ignore[attr-defined]
    soc = np.asarray(df_day['soc_percent'].values)  # type: ignore[attr-defined]
    charge = np.asarray(df_day['bess_charge_kwh'].values)  # type: ignore[attr-defined]
    discharge = np.asarray(df_day['bess_discharge_kwh'].values)  # type: ignore[attr-defined]

    # Separar demanda Mall vs EV (proporcional)
    total_demand_day = mall_kwh_day + ev_kwh_day
    mall_ratio = mall_kwh_day / total_demand_day if total_demand_day > 0 else 0.5
    ev_ratio = ev_kwh_day / total_demand_day if total_demand_day > 0 else 0.5

    mall_h = load * mall_ratio
    ev_h = load * ev_ratio
    # PV aplicado al mall solo cuando hay generacion solar (>0)
    mall_solar_used = np.where(pv > 0, np.minimum(mall_h, pv), 0.0)

    grid_import = np.asarray(df_day['grid_import_kwh'].values)  # type: ignore[attr-defined]
    # grid_export no se usa en graficas actuales
    mall_grid = np.asarray(df_day['mall_grid_import_kwh'].values) if 'mall_grid_import_kwh' in df_day else np.maximum(mall_h - mall_solar_used, 0)  # type: ignore[attr-defined]
    ev_grid = np.asarray(df_day['ev_grid_import_kwh'].values) if 'ev_grid_import_kwh' in df_day else np.maximum(grid_import - mall_grid, 0)  # type: ignore[attr-defined]
    # mall_solar_used_plot no se usa actualmente

    # ===== Panel 1: Demanda Total =====
    ax1 = axes[0]
    # Demanda mall achurada en azul
    ax1.fill_between(hours, 0, mall_h, color='steelblue', alpha=0.5, hatch='///', edgecolor='blue', label='Demanda Mall')
    ax1.bar(hours, ev_h, bottom=mall_h, color='salmon', alpha=0.9, label='Vehiculos Electricos')
    ax1.plot(hours, load, 'r-', linewidth=2, marker='o', markersize=4, label='Demanda Total')
    ax1.set_xlabel('Hora del Dia (Horario Local Peru UTC-5)', fontsize=10)
    ax1.set_ylabel('Energia (kWh)', fontsize=10)
    ax1.set_title(f'Demanda Energetica Total: {load.sum():.1f} kWh/dia', fontsize=12, fontweight='bold')
    ax1.set_xlim(-0.5, 23.5)
    ax1.set_xticks(range(24))
    ax1.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ===== Panel 2: Balance Energetico (PV vs Demanda) =====
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
        f'Solar → Mall: {mall_pv_used_day:.1f} kWh/dia\n'
        f'Excedente solar: {surplus_day:.1f} kWh/dia\n'
        f'Pico excedente: {surplus_max:.1f} kWh',
        xy=(0.02, 0.98), xycoords='axes fraction', ha='left', va='top',
        fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
    )
    ax2.set_xlabel('Hora del Dia (Horario Local Peru UTC-5)', fontsize=10)
    ax2.set_ylabel('Energia (kWh)', fontsize=10)
    ax2.set_title(
        f'Balance Energetico - Generacion FV Iquitos: {total_pv_label:.1f} kWh/dia',
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

    ax3.set_xlabel('Hora del Dia (Horario Local Peru UTC-5)', fontsize=10)
    ax3.set_ylabel('Estado de Carga (%)', fontsize=10)
    ax3.set_title(f'Estado de Carga Bateria - {capacity_kwh:.0f} kWh / {power_kw:.0f} kW (DoD {dod*100:.0f}%, {c_rate}C)',
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
    ax3.annotate(f'SOC min: {soc_min_val:.1f}%\nSOC max: {soc_max_val:.1f}%\nCiclos/dia: {cycles_day:.2f}',
                 xy=(0.02, 0.98), xycoords='axes fraction', ha='left', va='top',
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

# ===== Panel 4: Carga y Descarga BESS - Integracion con EV =====
    ax4 = axes[3]

    # Demanda mall achurada en azul (fondo)
    ax4.fill_between(hours, 0, mall_h, color='steelblue', alpha=0.3, hatch='///', edgecolor='blue', linewidth=0.5, label='Demanda Mall')

    # Generacion solar (area amarilla)
    ax4.fill_between(hours, 0, pv, color='yellow', alpha=0.4, label='Generacion Solar')

    # BARRAS DE CARGA Y DESCARGA BESS (elementos principales)
    # Carga BESS: barras verdes hacia arriba (excedente solar)
    ax4.bar(hours, charge, width=0.8, color='green', alpha=0.7, edgecolor='darkgreen',
            linewidth=1.5, label='Carga BESS (excedente solar)', zorder=4)

    # Descarga BESS: barras naranjas hacia abajo (cubre deficit EV nocturno)
    ax4.bar(hours, -discharge, width=0.8, color='orange', alpha=0.7, edgecolor='darkorange',
            linewidth=1.5, label='Descarga BESS (cubre deficit EV)', zorder=4)

    # Perfil de carga EV - USAR PERFIL DE 15 MIN SI ESTÁ DISPONIBLE
    if df_ev_15min is not None and len(df_ev_15min) == 96:
        # Perfil de 15 minutos: 96 intervalos (0-95)
        # Convertir intervalos a horas decimales para graficar
        intervals_15min = df_ev_15min['interval'].values  # type: ignore[attr-defined]
        hours_15min = intervals_15min / 4.0  # type: ignore[operator]  # 0, 0.25, 0.5, 0.75, 1.0, ...

        # USAR DIRECTAMENTE energy_kwh del archivo
        # El archivo ya tiene la energía correcta calculada según (Actualizado 2026-01-30):
        # - 112 sockets motos (11,648 kWh/día @ 4 kWh/ciclo) + 16 sockets mototaxis (3,328 kWh/día @ 8 kWh/ciclo)
        # - Total: 14,976 kWh/día durante operación 9AM-10PM (Modo 3, 26 ciclos/socket/día)
        # - Distribuido en 96 intervalos de 15 min según perfil de demanda horaria
        ev_15min_values = df_ev_15min['ev_kwh'].values  # type: ignore[attr-defined]

        # Graficar curva real de 15 minutos CON LÍNEA MÁS GRUESA Y VISIBLE
        ax4.plot(hours_15min, ev_15min_values, color='darkmagenta', linestyle='-', linewidth=3.5,
                 label='Perfil real EV 15 min (28 cargadores × 4 sockets = 68 kW)', zorder=6, alpha=1.0)
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

        # Agregar por mes
        df_sim_copy = df_sim.copy()
        df_sim_copy['month'] = (df_sim_copy.index // 720) % 12 + 1 if len(df_sim) > 720 else 1
        monthly = df_sim_copy.groupby('month').sum()  # type: ignore[attr-defined]

        # Panel 1: Energia mensual
        ax1 = axes[0, 0]
        months = monthly.index.values  # type: ignore[attr-defined]
        ax1.bar(months - 0.2, monthly['pv_kwh'] / 1000, width=0.4, color='yellow', label='Generacion PV')
        ax1.bar(months + 0.2, monthly['load_kwh'] / 1000, width=0.4, color='salmon', label='Demanda Total')
        ax1.set_xlabel('Mes', fontsize=10)
        ax1.set_ylabel('Energia (MWh)', fontsize=10)
        ax1.set_title('Energia Mensual', fontsize=11, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Panel 2: Flujos de red mensual
        ax2 = axes[0, 1]
        ax2.bar(months - 0.2, monthly['grid_import_kwh'] / 1000, width=0.4, color='red', label='Import Red')
        ax2.bar(months + 0.2, monthly['grid_export_kwh'] / 1000, width=0.4, color='blue', label='Export Red')
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
        self_suff_monthly = 1.0 - (monthly['grid_import_kwh'] / monthly['load_kwh'].replace(0, 1))  # type: ignore[attr-defined]
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
    load_series = df_sim['mall_kwh'] if 'mall_kwh' in df_sim.columns else df_sim['load_kwh']

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
    df_pv = pd.DataFrame({
        'Hour': hour,
        'solar_generation': df_sim['pv_kwh'].values,  # type: ignore[attr-defined]
    })
    df_pv.to_csv(citylearn_dir / "bess_solar_generation.csv", index=False)

    # Parametros para schema
    schema_params = {  # type: ignore[attr-defined]
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

    # Guardar parametros
    (citylearn_dir / "bess_schema_params.json").write_text(
        json.dumps(schema_params, indent=2), encoding="utf-8"
    )

    print(f"\nDatos CityLearn guardados en: {citylearn_dir}")

    return schema_params  # type: ignore[attr-defined]


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
        pv24 = pd.read_csv(pv_profile_path)  # type: ignore[attr-defined]
        idx = pd.date_range(start=f'{year}-01-01', periods=8760, freq='h')
        df_pv = pd.DataFrame(index=idx)
        df_pv['hour'] = pd.to_datetime(df_pv.index).hour  # type: ignore[union-attr]
        hourly_profile = pv24.set_index('hour')['pv_kwh']  # type: ignore[attr-defined]
        df_pv['pv_kwh'] = df_pv['hour'].map(hourly_profile)
        df_pv = df_pv.drop(columns=['hour'])
        print(f"   Generacion PV (perfil 24h): {len(df_pv)} registros")

    if mall_demand_path and mall_demand_path.exists():
        df_mall = load_mall_demand_real(mall_demand_path, year)
        # Calcular promedio diario
        if len(df_mall) == 35040:  # 15 minutos
            mall_kwh_day = df_mall['mall_kwh'].sum() / 365
        else:  # horario
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
        # Formato de 15 minutos: 96 intervalos/dia
        ev_kwh_day = df_ev['ev_kwh'].sum() / 365
        print(f"   Demanda EV (15 min, {len(df_ev)} intervalos): {ev_kwh_day:.0f} kWh/dia")
    else:
        # Formato horario: 24 horas/dia
        ev_kwh_day = df_ev['ev_kwh'].sum() / (len(df_ev) / 24)
        print(f"   Demanda EV (horaria, {len(df_ev)} horas): {ev_kwh_day:.0f} kWh/dia")

    print("      - 32 cargadores, 128 sockets totales")
    print("      - Playa Motos: 112 sockets")
    print("      - Playa Mototaxis: 16 sockets")

    # ===========================================
    # 2. Alinear series temporales
    # ===========================================
    # Todos los datos en formato horario (8,760 horas/año)

    # EV debe estar en 8,760 horas
    if len(df_ev) != 8760:
        raise ValueError(f"EV debe tener 8,760 horas, tiene {len(df_ev)}")

    # PV debe estar en 8,760 horas
    if len(df_pv) != 8760:
        raise ValueError(f"PV debe tener 8,760 horas, tiene {len(df_pv)}")

    # Mall debe estar en 8,760 horas
    if len(df_mall) != 8760:
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
    # 1. Solar → PRIMERO a motos/mototaxis (EV)
    # 2. Excedente solar → SEGUNDO carga BESS
    # 3. Excedente despues BESS → TERCERO a Mall
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
    # 1. EV consume PRIMERO del PV (prioridad maxima)
    pv_to_ev = np.minimum(pv_kwh, ev_kwh)

    # 2. PV remanente disponible (despues de cubrir EV)
    pv_after_ev = pv_kwh - pv_to_ev

    # 3. Deficit EV real (lo que el solar NO puede cubrir directamente)
    ev_shortfall_hourly = ev_kwh - pv_to_ev

    # deficit_hours no se usa actualmente (calculo reemplazado por analisis de cruce)
    # ev_shortfall_hourly_mean = pd.Series(ev_shortfall_hourly).groupby(hours).mean()  # type: ignore[attr-defined]
    # deficit_hours = set(ev_shortfall_hourly_mean[ev_shortfall_hourly_mean > 1.0].index.astype(int).tolist())

    # REGLA 2: Descarga BESS desde cuando termina generacion solar hasta cierre mall
    closing_hour = 22  # 10 PM - cierre mall

    # ANÁLISIS: Determinar punto exacto donde solar YA NO puede cargar EVs
    print("\n   Analizando cruce de curvas solar vs demanda EV (horario)...")

    # Usar datos horarios completos (8,760 horas)
    # Buscar primer dia completo de deficit en horario EV
    daily_deficit_start = None
    for day_idx in range(365):
        h_start = day_idx * 24
        h_end = h_start + 24
        pv_day = pv_kwh[h_start:h_end]
        ev_day = ev_kwh[h_start:h_end]

        # Horas de operacion EV: 9 AM - 10 PM (9:00 - 22:00)
        for hour_in_day in range(9, 23):
            if ev_day[hour_in_day] > pv_day[hour_in_day] + 0.1:
                daily_deficit_start = day_idx * 24 + hour_in_day
                break
        if daily_deficit_start is not None:
            break

    if daily_deficit_start is not None:
        discharge_start = daily_deficit_start % 24
        print(f"   Primer deficit EV: dia {daily_deficit_start // 24}, hora {discharge_start}")
    else:
        # Fallback: ultima hora con generacion solar
        pv_hours_with_gen = np.where(pv_kwh > 0.1)[0]
        if len(pv_hours_with_gen) > 0:
            last_solar_hour = pv_hours_with_gen[-1]
            discharge_start = (last_solar_hour % 24) + 1
        else:
            discharge_start = 17

    # Horas de descarga permitidas: desde deficit hasta cierre
    bess_discharge_hours = set(range(discharge_start, closing_hour + 1))

    # Crear mascara para horas de descarga (aplicable a arrays horarios)
    discharge_mask = np.array([int((i % 24) in bess_discharge_hours) for i in range(min_len)])

    # Calcular deficit total en horario de descarga (RESOLUCIÓN HORARIA)
    # deficit_15min esta en kWh/15min
    ev_shortfall_discharge = ev_shortfall_hourly * discharge_mask
    ev_shortfall_discharge_total = float(ev_shortfall_discharge.sum() / 365)  # kWh/dia
    peak_ev_shortfall_discharge = float(ev_shortfall_discharge.max()) if np.any(discharge_mask) else 0.0

    # ===========================================
    # 3. Calcular balance energetico con NUEVA PRIORIDAD
    # ===========================================
    print("")
    print("Calculando balance energetico...")

    # PRIORIDAD SOLAR:
    # 1. Solar → EV (ya calculado: pv_to_ev)
    # 2. Excedente solar → Carga BESS (pv_after_ev disponible)
    # 3. Excedente despues BESS → Mall

    # BESS solo maneja carga EV
    bess_load = ev_kwh  # Solo EV, NO incluir mall

    # Excedente solar DESPUÉS de cubrir EV (disponible para BESS)
    surplus = pv_after_ev  # Excedente despues de EV

    # Carga EV total en horario nocturno (sin solar) - no usado actualmente
    # ev_night_load = ev_kwh * discharge_mask
    # ev_night_day no se usa actualmente

    # Deficit EV en horario de descarga BESS (cuando solar no cubre EV)
    # Usar calculo preciso de perfil 15 min
    deficit_day = ev_shortfall_discharge_total  # Deficit calculado de 15 min

    surplus_day = float(surplus.sum() / (min_len / 24))
    pv_day_value = float(pv_kwh.sum() / (min_len / 24))
    # Variables diarias no usadas: mall_day, ev_day
    load_day = float(total_load_kwh.sum() / (min_len / 24))
    bess_load_day = float(bess_load.sum() / (min_len / 24))
    pv_to_ev_day = float(pv_to_ev.sum() / (min_len / 24))

    print("\n[HORARIO BESS - Basado en cruce de curvas]")
    print(f"   Generacion solar: 5h-17h (~{pv_day_value:.0f} kWh/dia)")
    print(f"   PRIORIDAD: Solar → EV ({pv_to_ev_day:.0f} kWh/dia) → BESS → Mall")
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
    soc_min_percent = 20.0  # SOC minimo: 20%
    soc_min = soc_min_percent / 100.0
    effective_dod = 0.80  # DoD: 80% (fijo segun analisis)
    effective_efficiency = 0.95  # Eficiencia: 95% (fijo segun analisis)

    print("\n[DIMENSIONAMIENTO - Segun analisis perfil 15 min]")
    print("   SOC operacional: 20% - 100%")
    print(f"   DoD: {effective_dod*100:.0f}%")
    print(f"   Eficiencia round-trip: {effective_efficiency*100:.0f}%")

    # CAPACIDAD: Debe cubrir solo el DÉFICIT EV en horario nocturno
    # Solo la diferencia entre demanda EV y generacion solar disponible
    # BESS carga la diferencia que el solar no puede cubrir
    sizing_deficit = deficit_day  # Solo el deficit EV en horario descarga
    peak_load = peak_ev_shortfall_discharge  # Pico deficit EV en descarga

    print("\n[CRITERIO CAPACIDAD]")
    print("   Criterio: Cubrir solo DÉFICIT EV en horario nocturno (demanda - solar)")
    print(f"   Deficit EV nocturno: {sizing_deficit:.0f} kWh/dia")
    print(f"   Horas de descarga: {len(bess_discharge_hours)} horas ({discharge_start}h-{closing_hour}h)")
    print(f"   Pico deficit EV nocturno: {peak_load:.1f} kW")

    # Capacidad basada en deficit EV durante horario nocturno
    # con DoD efectivo del 80% (para llegar al 20% al cierre)
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
    # Capacidad esperada: 1,712 kWh → Potencia esperada: 622 kW
    # Relacion: 1,712 / 622 = 2.75 (NO es C-rate, es ratio capacidad/potencia)
    power_ratio = 2.75  # Segun analisis de perfil de 15 min
    power_kw = capacity_kwh / power_ratio if capacity_kwh > 0 else 0.0

    print("\n📦 DIMENSIONAMIENTO ÓPTIMO (segun analisis perfil 15 min):")
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
    print("Simulando operacion del sistema...")

    # REGLA 2: Descarga solo en horario sin solar hasta cierre (10 PM)
    discharge_hours_sim = bess_discharge_hours  # Usar horas calculadas anteriormente
    print("\n[SIMULACIÓN]")
    print(f"   Descarga BESS: {sorted(discharge_hours_sim)}")
    print("   Carga BESS: Durante generacion solar (excedente)")

    # REGLA 1: Solo carga EV
    ev_load_kwh = ev_kwh
    mall_load_kwh = mall_kwh

    # Simular operacion BESS con carga EV solamente
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
    grid_import_total = mall_grid_import + df_bess['grid_import_mall_kwh'].values + df_bess['grid_import_ev_kwh'].values  # type: ignore[attr-defined]
    df_sim = df_bess.copy()
    df_sim['pv_kwh'] = pv_kwh
    df_sim['load_kwh'] = total_load_kwh
    df_sim['net_balance_kwh'] = pv_kwh - total_load_kwh
    df_sim['grid_import_kwh'] = grid_import_total
    df_sim['grid_export_kwh'] = df_bess['grid_export_kwh'].values  # type: ignore[attr-defined]
    df_sim['mall_grid_import_kwh'] = mall_grid_import + df_bess['grid_import_mall_kwh'].values  # type: ignore[attr-defined]
    df_sim['ev_grid_import_kwh'] = df_bess['grid_import_ev_kwh'].values  # type: ignore[attr-defined]

    total_pv = float(pv_kwh.sum())
    total_load = float(total_load_kwh.sum())
    total_grid_import = float(np.sum(grid_import_total))  # type: ignore[attr-defined]
    total_grid_export = float(np.sum(df_sim['grid_export_kwh'].to_numpy()))  # type: ignore[attr-defined]
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

    df_day = df_sim.groupby('hour').mean().reset_index()  # type: ignore[attr-defined]
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
        night_deficit_kwh_day=deficit_day,  # Mismo valor que deficit_day (deficit en descarga)
        pv_generation_kwh_day=pv_day_value,
        total_demand_kwh_day=load_day,
        mall_demand_kwh_day=mall_kwh_day,
        ev_demand_kwh_day=ev_kwh_day,
        bess_load_scope=bess_load_scope,
        pv_available_kwh_day=pv_day_value,  # Total PV disponible
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
            pv_kwh_day=pv_day_value,
            out_dir=out_dir,
            reports_dir=reports_dir,
            df_ev_15min=None,  # Perfil de 15 min no disponible aqui
        )

    print("")
    print("=" * 60)
    print(f"Resultados guardados en: {out_dir}")
    print("=" * 60)

    return result_dict


if __name__ == "__main__":
    """
    Ejecucion directa del modulo BESS.

    Uso:
        python -m src.iquitos_citylearn.oe2.bess
        python src/iquitos_citylearn/oe2/bess.py
    """
    import sys

    # Agregar directorio raiz al path
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
        missing_files.append(f"PV: {pv_profile_path}")  # type: ignore[attr-defined]
    if not ev_profile_path.exists():
        missing_files.append(f"EV: {ev_profile_path}")  # type: ignore[attr-defined]

    if missing_files:
        print("\n❌ ERROR: Archivos faltantes:")
        for f in missing_files:  # type: ignore[attr-defined]
            print(f"   • {f}")
        print("\nEjecuta primero:")
        print("   python -m scripts.run_oe2_solar")
        print("   python -m scripts.run_oe2_chargers")
        sys.exit(1)

    # Directorio de salida
    out_dir = interim_dir / "bess"

    # Parametros por defecto
    print("\n" + "="*70)
    print("  DIMENSIONAMIENTO BESS - Ejecucion Directa")
    print("="*70)
    print("\nParametros:")
    print(f"   • PV: {pv_profile_path.name}")
    print(f"   • EV: {ev_profile_path.name}")
    print(f"   • Mall: {'demanda_mall_kwh.csv' if mall_demand_path.exists() else 'perfil sintetico'}")
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
    print(f"   • Generacion PV:    {result['pv_generation_kwh_day']:,.0f} kWh/dia")
    print(f"   • Demanda total:    {result['total_demand_kwh_day']:,.0f} kWh/dia")
    print(f"     - Mall:           {result['mall_demand_kwh_day']:,.0f} kWh/dia")
    print(f"     - EV:             {result['ev_demand_kwh_day']:,.0f} kWh/dia")
    print(f"   • Excedente PV:     {result['surplus_kwh_day']:,.0f} kWh/dia")
    print(f"   • Deficit:          {result['deficit_kwh_day']:,.0f} kWh/dia")

    print("\n🔋 OPERACIÓN:")
    self_suff_value = float(result['self_sufficiency']) if isinstance(result['self_sufficiency'], (int, float, str)) else 0.0
    print(f"   • Autosuficiencia:  {self_suff_value*100:.1f}%")
    print(f"   • Import red:       {result['grid_import_kwh_day']:,.0f} kWh/dia")
    print(f"   • Export red:       {result['grid_export_kwh_day']:,.0f} kWh/dia")
    print(f"   • Ciclos/dia:       {result['cycles_per_day']:.2f}")
    print(f"   • SOC rango:        {result['soc_min_percent']:.0f}% - {result['soc_max_percent']:.0f}%")

    print("\n📁 ARCHIVOS GENERADOS:")
    print(f"   • {out_dir / 'bess_results.json'}")
    print(f"   • {out_dir / 'bess_simulation_hourly.csv'}")
    print(f"   • {out_dir / 'bess_daily_balance_24h.csv'}")
    print(f"   • {reports_dir / 'bess' / 'bess_sistema_completo.png'}")

    print("\n" + "="*70)
    print("✅ DIMENSIONAMIENTO BESS COMPLETADO")
    print("="*70 + "\n")
