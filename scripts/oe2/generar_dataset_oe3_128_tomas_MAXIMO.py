#!/usr/bin/env python
"""
Generador de Dataset Anual para OE3 - ESCENARIO MÁXIMO (DISEÑO)
================================================================

Genera dataset de 8760 horas (1 año) para entrenamiento de agentes RL.
ESCENARIO MÁXIMO: Para dimensionamiento de infraestructura (diseño)

Configuración:
- 32 cargadores físicos × 4 tomas = 128 tomas totales
- Playa Motos: 28 cargadores × 4 tomas = 112 tomas (2 kW)
- Playa Mototaxis: 4 cargadores × 4 tomas = 16 tomas (3 kW)

ESCENARIO MÁXIMO (Tabla 13):
- Energía/día: 2,228 kWh (capacidad real 128 tomas)
- PE: 1.00, FC: 1.00
- Vehículos/día: ~8,099 motos + ~1,170 mototaxis = ~9,269 total

Cada toma es un punto de control independiente para el agente OE3.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Optional, Any
import json
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURACIÓN - ESCENARIO MÁXIMO (DISEÑO)
# ============================================================================

# Tabla 13 OE2 - ESCENARIO MÁXIMO AJUSTADO
# Energía objetivo: 2,228 kWh/día (capacidad máxima real con 128 tomas)
# Este es el máximo realista con la infraestructura de 32 cargadores × 4 tomas

# Estructura de playas - CALIBRADO PARA ESCENARIO MÁXIMO (~2,228 kWh/día)
PLAYAS_CONFIG = {
    "Playa_Motos": {
        "n_cargadores": 28,
        "tomas_por_cargador": 4,
        "potencia_toma_kw": 2.0,
        "prefijo": "MOTO",
        "battery_kwh": 1.5,
        "session_minutes": 30,
        "sessions_per_hour": 2,
        # Calibrado para ~2,228 kWh/día (escenario MÁXIMO)
        "base_probability": 0.74,
    },
    "Playa_Mototaxis": {
        "n_cargadores": 4,
        "tomas_por_cargador": 4,
        "potencia_toma_kw": 3.0,
        "prefijo": "MOTOTAXI",
        "battery_kwh": 2.5,
        "session_minutes": 30,
        "sessions_per_hour": 2,
        "base_probability": 0.76,
    }
}

# Horarios de operación
OPENING_HOUR = 9   # Mall abre
CLOSING_HOUR = 22  # Mall cierra
PEAK_HOURS = [18, 19, 20, 21]  # Horas pico

# Parámetros de simulación
N_HOURS_YEAR = 8760  # 365 días × 24 horas
RANDOM_SEED = 42

# Perfil horario típico de demanda (normalizado) - ESCENARIO MÁXIMO
# Alta demanda para alcanzar ~2,228 kWh/día (capacidad real)
HOURLY_DEMAND_PROFILE = {
    0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0,
    9: 0.60, 10: 0.70, 11: 0.80, 12: 0.90, 13: 0.95, 14: 0.95, 15: 0.98,
    16: 1.00, 17: 1.00, 18: 1.00, 19: 1.00, 20: 1.00, 21: 0.95,
    22: 0.0, 23: 0.0
}

# Variación estacional (factor multiplicador por mes)
SEASONAL_FACTORS = {
    1: 0.95, 2: 0.90, 3: 1.00, 4: 1.05, 5: 1.10, 6: 1.05,
    7: 1.15, 8: 1.10, 9: 1.00, 10: 1.00, 11: 1.05, 12: 1.15
}

# Variación día de semana
WEEKDAY_FACTORS = {
    0: 0.90, 1: 0.95, 2: 1.00, 3: 1.00, 4: 1.05, 5: 1.15, 6: 1.10
}

# Directorio de salida - ESCENARIO MÁXIMO
OUTPUT_DIR = Path("data/processed/citylearn/iquitos_128_tomas_maximo")


def get_demand_factor(hour: int, month: int, weekday: int) -> float:
    """Calcula factor de demanda combinado."""
    base = HOURLY_DEMAND_PROFILE.get(hour, 0.0)
    seasonal = SEASONAL_FACTORS.get(month, 1.0)
    weekday_f = WEEKDAY_FACTORS.get(weekday, 1.0)
    return base * seasonal * weekday_f


def generate_ev_arrivals_30min(
    n_tomas: int,
    n_hours: int,
    base_probability: float,
    power_kw: float,
    battery_kwh: float,
    session_minutes: int = 30,
    sessions_per_hour: int = 2,
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Genera matriz de llegadas de EVs con sesiones de 30 minutos.
    ESCENARIO MÁXIMO: Alta ocupación para diseño.
    """
    # Documentar parámetros de referencia
    _ = battery_kwh  # Capacidad para referencia
    _ = sessions_per_hour  # Capacidad máxima por hora

    np.random.seed(seed)

    start_date = datetime(2024, 1, 1, 0, 0)
    timestamps = [start_date + timedelta(hours=h) for h in range(n_hours)]

    states = np.full((n_hours, n_tomas), 3, dtype=int)
    power = np.zeros((n_hours, n_tomas))

    energy_per_session = power_kw * (session_minutes / 60)
    print(f"    Energía por sesión (30 min): {energy_per_session:.2f} kWh")

    for toma_idx in range(n_tomas):
        for t in range(n_hours):
            ts = timestamps[t]
            hour = ts.hour
            month = ts.month
            weekday = ts.weekday()

            if hour < OPENING_HOUR or hour >= CLOSING_HOUR:
                states[t, toma_idx] = 3
                power[t, toma_idx] = 0.0
                continue

            demand_factor = get_demand_factor(hour, month, weekday)
            occupation_prob = base_probability * demand_factor
            occupation_prob = min(occupation_prob, 0.98)  # Límite máximo

            if np.random.random() < occupation_prob:
                states[t, toma_idx] = 1
                # En escenario MÁXIMO: más probable 2 sesiones por hora
                n_sessions_this_hour = np.random.choice([1, 2], p=[0.15, 0.85])
                effective_power = power_kw * (n_sessions_this_hour * 0.5)
                power[t, toma_idx] = effective_power * np.random.uniform(0.95, 1.0)
            else:
                states[t, toma_idx] = 3
                power[t, toma_idx] = 0.0

    return states, power


def generate_citylearn_charger_csv(
    toma_id: str,
    states: np.ndarray,
    power: np.ndarray,
    power_kw: float,
    battery_kwh: float,
    n_hours: int = N_HOURS_YEAR
) -> pd.DataFrame:
    """Genera DataFrame con formato CityLearn para una toma."""
    # Documentar parámetros de referencia
    _ = toma_id  # Identificador para metadata
    _ = power_kw  # Potencia nominal
    _ = battery_kwh  # Capacidad batería

    start_date = datetime(2024, 1, 1, 0, 0)
    timestamps = [start_date + timedelta(hours=h) for h in range(n_hours)]

    hours = np.array([ts.hour for ts in timestamps])
    days = np.array([ts.timetuple().tm_yday for ts in timestamps])
    months = np.array([ts.month for ts in timestamps])

    # Energía acumulada por hora
    energy = power.copy()  # kWh = kW * 1h

    soc = np.zeros(n_hours)
    for t in range(n_hours):
        if states[t] == 1:
            soc[t] = np.random.uniform(0.3, 0.7)
        else:
            soc[t] = 0.0

    req_soc = np.where(states == 1, np.random.uniform(0.9, 1.0, n_hours), 0.0)
    arrival_times = np.where(states == 1, hours + np.random.uniform(0, 0.5, n_hours), 0.0)
    arr_soc = np.where(states == 1, np.random.uniform(0.2, 0.4, n_hours), 0.0)

    df = pd.DataFrame({
        "Hour": hours,
        "Day_of_Year": days,
        "Month": months,
        "charger_state": states,
        "charger_power_kw": power,
        "charger_energy_kwh": energy,  # Usar variable energy
        "electric_vehicle_soc": soc,
        "electric_vehicle_required_soc_departure": req_soc,
        "electric_vehicle_estimated_arrival_time": arrival_times,
        "electric_vehicle_estimated_soc_arrival": arr_soc,
    })

    last_row = df.iloc[-1:].copy()
    df = pd.concat([df, last_row], ignore_index=True)

    return df


def generate_playa_datasets(
    playa_name: str,
    playa_config: Dict,
    output_dir: Path,
    base_probability: float = 0.15,
    seed_offset: int = 0
) -> Dict:
    """Genera datasets anuales para todas las tomas de una playa."""

    n_cargadores = playa_config["n_cargadores"]
    tomas_por_cargador = playa_config["tomas_por_cargador"]
    n_tomas = n_cargadores * tomas_por_cargador
    power_kw = playa_config["potencia_toma_kw"]
    battery_kwh = playa_config["battery_kwh"]
    prefijo = playa_config["prefijo"]
    session_minutes = playa_config["session_minutes"]
    sessions_per_hour = playa_config["sessions_per_hour"]

    print(f"\n{'='*70}")
    print(f"Generando dataset para {playa_name} - ESCENARIO MÁXIMO")
    print(f"{'='*70}")
    print(f"  Cargadores: {n_cargadores}")
    print(f"  Tomas por cargador: {tomas_por_cargador}")
    print(f"  Total tomas: {n_tomas}")
    print(f"  Potencia por toma: {power_kw} kW")
    print(f"  Batería promedio: {battery_kwh} kWh")
    print(f"  Sesión de carga: {session_minutes} minutos")
    print(f"  Probabilidad base: {base_probability:.0%} (MÁXIMO)")

    playa_dir = output_dir / playa_name
    playa_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Simulando llegadas de EVs para {N_HOURS_YEAR} horas...")
    print(f"    Modo: Sesiones de {session_minutes} min, alta ocupación")

    all_states, all_power = generate_ev_arrivals_30min(
        n_tomas=n_tomas,
        n_hours=N_HOURS_YEAR,
        base_probability=base_probability,
        power_kw=power_kw,
        battery_kwh=battery_kwh,
        session_minutes=session_minutes,
        sessions_per_hour=sessions_per_hour,
        seed=RANDOM_SEED + seed_offset
    )

    tomas_info = []
    total_energy = 0.0

    print(f"  Generando {n_tomas} archivos CSV...")

    for cargador_idx in range(n_cargadores):
        for toma_idx in range(tomas_por_cargador):
            global_toma_idx = cargador_idx * tomas_por_cargador + toma_idx
            toma_id = f"{prefijo}_CH_{cargador_idx+1:03d}_T{toma_idx+1}"
            toma_states = all_states[:, global_toma_idx]
            toma_power = all_power[:, global_toma_idx]

            df = generate_citylearn_charger_csv(
                toma_id=toma_id,
                states=toma_states,
                power=toma_power,
                power_kw=power_kw,
                battery_kwh=battery_kwh
            )

            csv_path = playa_dir / f"{toma_id}.csv"
            df.to_csv(csv_path, index=False)

            toma_energy = df["charger_power_kw"].sum()
            total_energy += toma_energy

            tomas_info.append({
                "toma_id": toma_id,
                "cargador": cargador_idx + 1,
                "toma": toma_idx + 1,
                "power_kw": power_kw,
                "energy_year_kwh": toma_energy,
                "csv_path": str(csv_path.relative_to(output_dir.parent.parent.parent))
            })

    print(f"\n  ✅ {n_tomas} archivos CSV generados")
    print(f"  ✅ Energía total año: {total_energy:,.0f} kWh")
    print(f"  ✅ Energía promedio por toma: {total_energy/n_tomas:,.0f} kWh/año")

    return {
        "playa": playa_name,
        "n_cargadores": n_cargadores,
        "n_tomas": n_tomas,
        "power_kw_per_toma": power_kw,
        "total_power_kw": n_tomas * power_kw,
        "total_energy_year_kwh": total_energy,
        "tomas": tomas_info
    }


def generate_schema_with_tomas(
    playas_stats: Dict[str, Any],
    output_dir: Path,
    schema_template_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Genera schema CityLearn v2 con todas las tomas."""
    _ = schema_template_path  # Reservado para futuro uso

    print(f"\n{'='*70}")
    print("Generando Schema CityLearn v2 para OE3 - ESCENARIO MÁXIMO")
    print(f"{'='*70}")

    # Schema tipado explícitamente
    schema: Dict[str, Any] = {
        "root_directory": str(output_dir),
        "simulation_end_time_step": N_HOURS_YEAR - 1,
        "central_agent": True,
        "observations": {
            "hour": {"active": True, "shared_in_central_agent": True},
            "day_type": {"active": True, "shared_in_central_agent": True},
            "month": {"active": True, "shared_in_central_agent": True},
        },
        "actions": {
            "charger_global_control": {"active": True}
        },
        "reward_function": "citylearn.reward_function.RewardFunction",
        "buildings": {},
        "electric_vehicle_storage": {"chargers": {}},
        "electric_vehicles_def": {}
    }

    # Variables tipadas para acceso
    observations: Dict[str, Any] = schema["observations"]
    actions: Dict[str, Any] = schema["actions"]
    buildings: Dict[str, Any] = schema["buildings"]
    ev_defs: Dict[str, Any] = schema["electric_vehicles_def"]

    charger_idx = 0
    for playa_name, stats in playas_stats.items():
        for toma in stats["tomas"]:
            toma_id = toma["toma_id"]

            observations[f"charger_{toma_id}_state"] = {
                "active": True, "shared_in_central_agent": True
            }
            observations[f"charger_{toma_id}_power_kw"] = {
                "active": True, "shared_in_central_agent": True
            }

            actions[f"charger_{toma_id}_control"] = {"active": True}

            charger_idx += 1

        playa_dir = playa_name
        chargers_in_playa = {
            toma["toma_id"]: {
                "type": "ev_charger",
                "power_kw": toma["power_kw"],
                "csv_file": f"{playa_dir}/{toma['toma_id']}.csv"
            }
            for toma in stats["tomas"]
        }

        buildings[playa_name] = {
            "type": "ev_charging_station",
            "include": True,
            "chargers": chargers_in_playa,
            "energy_simulation": f"{playa_dir}/energy_simulation.csv"
        }

        for toma in stats["tomas"]:
            ev_name = f"ev_{toma['toma_id']}"
            ev_defs[ev_name] = {
                "charger": toma["toma_id"],
                "battery_capacity_kwh": stats.get("battery_kwh", 2.0),
                "charging_efficiency": 0.95,
                "arrival_soc_range": [0.2, 0.4],
                "departure_soc_target": 0.95
            }

    schema_path = output_dir / "schema_128_tomas_maximo.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print(f"  ✅ Schema guardado: {schema_path}")
    print(f"  ✅ Total observables: {len(observations)}")
    print(f"  ✅ Total acciones: {len(actions)}")
    print(f"  ✅ Total chargers: {charger_idx}")

    return schema


def main():
    """Función principal de generación."""

    print("\n" + "="*70)
    print("GENERADOR DE DATASET OE3 - ESCENARIO MÁXIMO (DISEÑO)")
    print("128 Tomas Controlables (32 cargadores × 4 tomas)")
    print("="*70)
    print(f"\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Período: {N_HOURS_YEAR} horas (1 año)")
    print("\n⚠️  ESCENARIO: MÁXIMO (PE=1.0, FC=1.0)")
    print("⚠️  Objetivo: ~2,228 kWh/día (Capacidad máxima 128 tomas)")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nDirectorio de salida: {OUTPUT_DIR.absolute()}")

    playas_stats = {}
    total_energy = 0
    total_tomas = 0
    total_power = 0

    for playa_name, config in PLAYAS_CONFIG.items():
        stats = generate_playa_datasets(
            playa_name=playa_name,
            playa_config=config,
            output_dir=OUTPUT_DIR,
            base_probability=config["base_probability"],
            seed_offset=total_tomas
        )
        playas_stats[playa_name] = stats
        total_energy += stats["total_energy_year_kwh"]
        total_tomas += stats["n_tomas"]
        total_power += stats["total_power_kw"]

    _schema = generate_schema_with_tomas(playas_stats, OUTPUT_DIR)

    print("\n" + "=" * 70)
    print("RESUMEN FINAL - ESCENARIO MÁXIMO (DISEÑO)")
    print("=" * 70)

    for playa_name, stats in playas_stats.items():
        print(f"\n{playa_name}:")
        print(f"  Cargadores: {stats['n_cargadores']}")
        print(f"  Tomas: {stats['n_tomas']}")
        print(f"  Potencia total: {stats['total_power_kw']} kW")
        print(f"  Energía anual: {stats['total_energy_year_kwh']:,.0f} kWh")

    energia_diaria = total_energy / 365
    print(f"\n{'='*70}")
    print("TOTALES:")
    print("  Cargadores: 32")
    print(f"  Tomas controlables: {total_tomas}")
    print(f"  Potencia instalada: {total_power} kW")
    print(f"  Energía anual estimada: {total_energy:,.0f} kWh")
    print(f"  Energía diaria promedio: {energia_diaria:,.0f} kWh/día")
    print("  ✅  Objetivo MÁXIMO alcanzado: ~2,228 kWh/día")
    print("=" * 70)

    main_summary = {
        "escenario": "MÁXIMO (DISEÑO)",
        "fecha_generacion": datetime.now().isoformat(),
        "n_hours": N_HOURS_YEAR,
        "total_cargadores": 32,
        "total_tomas": total_tomas,
        "total_power_kw": total_power,
        "total_energy_year_kwh": total_energy,
        "energy_day_kwh": energia_diaria,
        "target_energy_day_kwh": 2228.0,
        "playas": {
            name: {
                "n_cargadores": s["n_cargadores"],
                "n_tomas": s["n_tomas"],
                "power_kw": s["total_power_kw"],
                "energy_year_kwh": s["total_energy_year_kwh"]
            }
            for name, s in playas_stats.items()
        }
    }

    summary_path = OUTPUT_DIR / "dataset_summary_maximo.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(main_summary, f, indent=2)

    print(f"\n✅ Dataset MÁXIMO generado en: {OUTPUT_DIR}")
    print(f"✅ Resumen guardado en: {summary_path}")

    return main_summary


if __name__ == "__main__":
    main()
