#!/usr/bin/env python
"""
Generador de Dataset Anual para OE3 - CityLearn v2
===================================================

Genera dataset de 8760 horas (1 año) para entrenamiento de agentes RL.

Configuración:
- 32 cargadores físicos × 4 tomas = 128 tomas totales
- Playa Motos: 28 cargadores × 4 tomas = 112 tomas (2 kW)
- Playa Mototaxis: 4 cargadores × 4 tomas = 16 tomas (3 kW)

Cada toma es un punto de control independiente para el agente OE3.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import json
from datetime import datetime, timedelta

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Estructura de playas - CALIBRADO PARA TABLA 13 OE2
# Tabla 13: Energía día promedio = 903.46 kWh, 128 tomas
# Horario de operación: 9 AM - 10 PM (13 horas)
# Modo de carga: Sesiones de 30 minutos, alta rotación
# Calibrado para Tabla 13: 903 kWh/día promedio
PLAYAS_CONFIG = {
    "Playa_Motos": {
        "n_cargadores": 28,
        "tomas_por_cargador": 4,
        "potencia_toma_kw": 2.0,
        "prefijo": "MOTO",
        "battery_kwh": 1.5,  # Batería típica moto eléctrica
        "session_minutes": 30,  # Sesiones fijas de 30 minutos
        "sessions_per_hour": 2,  # Hasta 2 sesiones por hora (30 min cada una)
        "base_probability": 0.45,  # Calibrado para 903 kWh/día (Tabla 13)
    },
    "Playa_Mototaxis": {
        "n_cargadores": 4,
        "tomas_por_cargador": 4,
        "potencia_toma_kw": 3.0,
        "prefijo": "MOTOTAXI",
        "battery_kwh": 2.5,  # Batería típica mototaxi
        "session_minutes": 30,  # Sesiones fijas de 30 minutos
        "sessions_per_hour": 2,  # Hasta 2 sesiones por hora
        "base_probability": 0.48,  # Calibrado para 903 kWh/día (Tabla 13)
    }
}

# Horarios de operación
OPENING_HOUR = 9   # Mall abre
CLOSING_HOUR = 22  # Mall cierra
PEAK_HOURS = [18, 19, 20, 21]  # Horas pico

# Parámetros de simulación
N_HOURS_YEAR = 8760  # 365 días × 24 horas
RANDOM_SEED = 42

# Perfil horario típico de demanda (normalizado)
HOURLY_DEMAND_PROFILE = {
    0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0, 8: 0.0,
    9: 0.10, 10: 0.15, 11: 0.35, 12: 0.55, 13: 0.65, 14: 0.75, 15: 0.85,
    16: 0.90, 17: 0.95, 18: 1.00, 19: 0.95, 20: 0.85, 21: 0.70,
    22: 0.0, 23: 0.0
}

# Variación estacional (factor multiplicador por mes)
SEASONAL_FACTORS = {
    1: 0.95,   # Enero (vacaciones)
    2: 0.90,   # Febrero
    3: 1.00,   # Marzo
    4: 1.05,   # Abril
    5: 1.10,   # Mayo
    6: 1.05,   # Junio
    7: 1.15,   # Julio (vacaciones)
    8: 1.10,   # Agosto
    9: 1.00,   # Septiembre
    10: 1.05,  # Octubre
    11: 1.10,  # Noviembre
    12: 1.20,  # Diciembre (navidad)
}

# Variación por día de semana
WEEKDAY_FACTORS = {
    0: 0.90,  # Lunes
    1: 0.95,  # Martes
    2: 1.00,  # Miércoles
    3: 1.00,  # Jueves
    4: 1.10,  # Viernes
    5: 1.20,  # Sábado
    6: 1.15,  # Domingo
}


# ============================================================================
# FUNCIONES DE GENERACIÓN
# ============================================================================

def get_demand_factor(hour: int, month: int, weekday: int) -> float:
    """
    Calcula el factor de demanda combinado para una hora específica.

    Args:
        hour: Hora del día (0-23)
        month: Mes del año (1-12)
        weekday: Día de la semana (0=Lun, 6=Dom)

    Returns:
        Factor de demanda normalizado
    """
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

    Modelo de carga:
    - Horario: 9 AM - 10 PM (13 horas de operación)
    - Sesiones de 30 minutos (0.5 horas)
    - Hasta 2 sesiones por hora por toma
    - Alta rotación de vehículos

    Returns:
        Tuple (states, power) - Arrays (n_hours, n_tomas)
    """
    np.random.seed(seed)

    # Crear timestamps para el año
    start_date = datetime(2024, 1, 1, 0, 0)
    timestamps = [start_date + timedelta(hours=h) for h in range(n_hours)]

    # Matriz de estados: 3=sin EV (disponible), 1=EV conectado cargando
    states = np.full((n_hours, n_tomas), 3, dtype=int)

    # Matriz de potencia de carga (kW)
    power = np.zeros((n_hours, n_tomas))

    # Energía por sesión de 30 min a potencia nominal
    energy_per_session = power_kw * (session_minutes / 60)  # kWh

    print(f"    Energía por sesión (30 min): {energy_per_session:.2f} kWh")

    # Simular para cada toma
    for toma_idx in range(n_tomas):
        for t in range(n_hours):
            ts = timestamps[t]
            hour = ts.hour
            month = ts.month
            weekday = ts.weekday()

            # Solo durante horario de operación (9 AM - 10 PM)
            if hour < OPENING_HOUR or hour >= CLOSING_HOUR:
                states[t, toma_idx] = 3  # Cerrado, sin EV
                power[t, toma_idx] = 0.0
                continue

            # Calcular probabilidad de ocupación basada en demanda
            demand_factor = get_demand_factor(hour, month, weekday)
            occupation_prob = base_probability * demand_factor

            # Limitar probabilidad máxima
            occupation_prob = min(occupation_prob, 0.95)

            # Determinar si hay EV cargando en esta hora
            if np.random.random() < occupation_prob:
                states[t, toma_idx] = 1  # EV cargando

                # Potencia efectiva (con variación realista)
                # Las sesiones de 30 min en una hora de 60 min = factor 0.5-1.0
                n_sessions_this_hour = np.random.choice([1, 2], p=[0.4, 0.6])
                effective_power = power_kw * (n_sessions_this_hour * 0.5)

                # Variación adicional por eficiencia
                power[t, toma_idx] = effective_power * np.random.uniform(0.90, 1.0)
            else:
                states[t, toma_idx] = 3  # Disponible pero sin EV
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
    """
    Genera DataFrame en formato CityLearn para una toma específica.

    CityLearn requiere:
    - electric_vehicle_charger_state: 1=conectado, 3=sin EV
    - electric_vehicle_id: ID del vehículo (o None)
    - electric_vehicle_departure_time: Horas restantes para salir
    - electric_vehicle_required_soc_departure: SOC requerido al salir
    - electric_vehicle_estimated_arrival_time: Horas hasta próxima llegada
    - electric_vehicle_estimated_soc_arrival: SOC esperado al llegar
    """
    n = len(states)

    # Generar IDs de vehículos (nuevo ID cada vez que llega un EV)
    ev_ids = []
    ev_counter = 0
    prev_state = 3

    for i, state in enumerate(states):
        if state == 1 and prev_state != 1:
            ev_counter += 1
        ev_ids.append(f"EV_{toma_id}_{ev_counter:05d}" if state == 1 else f"EV_{toma_id}_000")
        prev_state = state

    # Calcular tiempos de salida
    departure_times = np.zeros(n)
    for i in range(n):
        if states[i] == 1:
            # Buscar cuántas horas quedan de carga
            remaining = 0
            j = i
            while j < n and states[j] == 1:
                remaining += 1
                j += 1
            departure_times[i] = remaining

    # SOC requerido al salir (típicamente 80-95%)
    req_soc = np.where(states == 1, np.random.uniform(0.80, 0.95, n), 0.0)

    # Tiempo estimado hasta próxima llegada (cuando no hay EV)
    arrival_times = np.zeros(n)
    for i in range(n):
        if states[i] != 1:
            # Buscar próxima llegada
            j = i + 1
            while j < n and states[j] != 1:
                j += 1
            arrival_times[i] = min(j - i, 24)  # Máximo 24 horas

    # SOC esperado de llegada
    arr_soc = np.where(states != 1, np.random.uniform(0.20, 0.50, n), 0.0)

    df = pd.DataFrame({
        "electric_vehicle_charger_state": states,
        "electric_vehicle_charger_power": power,
        "electric_vehicle_id": ev_ids,
        "electric_vehicle_departure_time": departure_times,
        "electric_vehicle_required_soc_departure": req_soc,
        "electric_vehicle_estimated_arrival_time": arrival_times,
        "electric_vehicle_estimated_soc_arrival": arr_soc,
    })

    # Agregar fila extra para CityLearn (evita IndexError en t+1)
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
    """
    Genera datasets anuales para todas las tomas de una playa.
    Modo de carga: sesiones de 30 minutos con alta rotación.
    """
    n_cargadores = playa_config["n_cargadores"]
    tomas_por_cargador = playa_config["tomas_por_cargador"]
    n_tomas = n_cargadores * tomas_por_cargador
    power_kw = playa_config["potencia_toma_kw"]
    battery_kwh = playa_config["battery_kwh"]
    prefijo = playa_config["prefijo"]
    session_minutes = playa_config["session_minutes"]
    sessions_per_hour = playa_config["sessions_per_hour"]

    print(f"\n{'='*70}")
    print(f"Generando dataset para {playa_name}")
    print(f"{'='*70}")
    print(f"  Cargadores: {n_cargadores}")
    print(f"  Tomas por cargador: {tomas_por_cargador}")
    print(f"  Total tomas: {n_tomas}")
    print(f"  Potencia por toma: {power_kw} kW")
    print(f"  Batería promedio: {battery_kwh} kWh")
    print(f"  Sesión de carga: {session_minutes} minutos")
    print(f"  Sesiones máx. por hora: {sessions_per_hour}")

    # Crear directorio de salida
    playa_dir = output_dir / playa_name
    playa_dir.mkdir(parents=True, exist_ok=True)

    # Generar estados y potencia para todas las tomas
    print(f"\n  Simulando llegadas de EVs para {N_HOURS_YEAR} horas...")
    print(f"    Modo: Sesiones de {session_minutes} min, hasta {sessions_per_hour} por hora")

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

    # Generar CSV para cada toma
    tomas_info = []
    total_energy = 0.0

    print(f"  Generando {n_tomas} archivos CSV...")

    for cargador_idx in range(n_cargadores):
        for toma_idx in range(tomas_por_cargador):
            global_toma_idx = cargador_idx * tomas_por_cargador + toma_idx

            # ID de la toma
            toma_id = f"{prefijo}_CH_{cargador_idx+1:03d}_T{toma_idx+1}"

            # Extraer estados y potencia de esta toma
            toma_states = all_states[:, global_toma_idx]
            toma_power = all_power[:, global_toma_idx]

            # Generar DataFrame CityLearn
            df = generate_citylearn_charger_csv(
                toma_id=toma_id,
                states=toma_states,
                power=toma_power,
                power_kw=power_kw,
                battery_kwh=battery_kwh
            )

            # Guardar CSV
            csv_path = playa_dir / f"{toma_id}.csv"
            df.to_csv(csv_path, index=False)

            # Calcular estadísticas
            energy_kwh = toma_power.sum()  # kWh (1 hora por timestep)
            sessions = np.sum(np.diff(toma_states.astype(int)) == -2) + (1 if toma_states[0] == 1 else 0)

            total_energy += energy_kwh

            tomas_info.append({
                "toma_id": toma_id,
                "cargador_idx": cargador_idx + 1,
                "toma_local_idx": toma_idx + 1,
                "playa": playa_name,
                "power_kw": power_kw,
                "energy_year_kwh": round(energy_kwh, 2),
                "sessions_year": int(sessions),
                "csv_file": f"{toma_id}.csv"
            })

    # Estadísticas de la playa
    stats = {
        "playa": playa_name,
        "n_cargadores": n_cargadores,
        "n_tomas": n_tomas,
        "power_per_toma_kw": power_kw,
        "total_power_kw": n_tomas * power_kw,
        "total_energy_year_kwh": round(total_energy, 2),
        "avg_energy_per_toma_kwh": round(total_energy / n_tomas, 2),
        "tomas": tomas_info
    }

    # Guardar resumen JSON
    summary_path = playa_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\n  ✅ {n_tomas} archivos CSV generados")
    print(f"  ✅ Energía total año: {total_energy:,.0f} kWh")
    print(f"  ✅ Energía promedio por toma: {total_energy/n_tomas:,.0f} kWh/año")

    return stats


def generate_schema_with_tomas(
    playas_stats: Dict[str, Dict],
    output_dir: Path,
    schema_template_path: Path = None
) -> Dict:
    """
    Genera el schema CityLearn v2 con las 128 tomas como chargers controlables.
    """
    print(f"\n{'='*70}")
    print("Generando Schema CityLearn v2 para OE3")
    print(f"{'='*70}")

    # Schema base
    schema = {
        "root_directory": str(output_dir),
        "central_agent": True,
        "seconds_per_time_step": 3600,  # 1 hora
        "simulation_start_time_step": 0,
        "simulation_end_time_step": N_HOURS_YEAR,
        "observations": {
            "hour": {"active": True, "shared_in_central_agent": True},
            "day_type": {"active": True, "shared_in_central_agent": True},
            "month": {"active": True, "shared_in_central_agent": True},
            "solar_generation": {"active": True, "shared_in_central_agent": True},
            "electrical_storage_soc": {"active": True, "shared_in_central_agent": True},
            "net_electricity_consumption": {"active": True, "shared_in_central_agent": True},
            "carbon_intensity": {"active": True, "shared_in_central_agent": True},
            "electricity_pricing": {"active": True, "shared_in_central_agent": True},
        },
        "actions": {
            "electrical_storage": {"active": True},
        },
        "reward_function": {
            "type": "citylearn.reward_function.MARL",
        },
        "buildings": {},
        "electric_vehicles_def": {},
    }

    # Agregar observables para cada toma
    for playa_name, stats in playas_stats.items():
        for toma in stats["tomas"]:
            toma_id = toma["toma_id"]
            schema["observations"][f"charger_{toma_id}_state"] = {
                "active": True,
                "shared_in_central_agent": True
            }
            schema["observations"][f"charger_{toma_id}_power_kw"] = {
                "active": True,
                "shared_in_central_agent": True
            }

    # Agregar acciones para cada toma (control de carga)
    for playa_name, stats in playas_stats.items():
        for toma in stats["tomas"]:
            toma_id = toma["toma_id"]
            schema["actions"][f"charger_{toma_id}_control"] = {"active": True}

    # Crear buildings (uno por playa)
    for playa_name, stats in playas_stats.items():
        building_chargers = {}

        for toma in stats["tomas"]:
            toma_id = toma["toma_id"]
            building_chargers[toma_id] = {
                "type": "citylearn.electric_vehicle_charger.Charger",
                "charger_simulation": f"{playa_name}/{toma['csv_file']}",
                "autosize": False,
                "active": True,
                "attributes": {
                    "nominal_power": toma["power_kw"],
                    "efficiency": 0.95,
                    "charger_type": 0,  # Level 2
                    "max_charging_power": toma["power_kw"],
                    "min_charging_power": 0.5,
                    "num_sockets": 1,  # Cada toma es una unidad
                }
            }

        schema["buildings"][playa_name] = {
            "name": playa_name,
            "include": True,
            "energy_simulation": f"{playa_name}/energy.csv",
            "weather": "weather.csv",
            "carbon_intensity": "carbon_intensity.csv",
            "pricing": "pricing.csv",
            "inactive_observations": [],
            "inactive_actions": [],
            "chargers": building_chargers,
            "pv": {
                "type": "citylearn.energy_model.PV",
                "autosize": False,
                "attributes": {
                    "nominal_power": stats["total_power_kw"] * 10,  # 10x para cubrir demanda
                }
            },
            "electrical_storage": {
                "type": "citylearn.energy_model.Battery",
                "autosize": False,
                "attributes": {
                    "capacity": stats["total_power_kw"] * 4,  # 4h de autonomía
                    "nominal_power": stats["total_power_kw"] * 0.6,
                    "efficiency": 0.95,
                    "initial_soc": 0.5,
                }
            }
        }

    # Definiciones de EVs
    ev_idx = 1
    for playa_name, stats in playas_stats.items():
        battery_kwh = PLAYAS_CONFIG[playa_name]["battery_kwh"]
        for toma in stats["tomas"]:
            ev_name = f"EV_{toma['toma_id']}"
            schema["electric_vehicles_def"][ev_name] = {
                "include": True,
                "battery": {
                    "type": "citylearn.energy_model.Battery",
                    "autosize": False,
                    "attributes": {
                        "capacity": battery_kwh,
                        "nominal_power": toma["power_kw"],
                        "initial_soc": 0.25,
                        "depth_of_discharge": 0.85,
                    }
                }
            }
            ev_idx += 1

    # Guardar schema
    schema_path = output_dir / "schema_128_tomas.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"  ✅ Schema guardado: {schema_path}")
    print(f"  ✅ Total observables: {len(schema['observations'])}")
    print(f"  ✅ Total acciones: {len(schema['actions'])}")
    print(f"  ✅ Total chargers: {sum(len(b.get('chargers', {})) for b in schema['buildings'].values())}")

    return schema


def main():
    """Función principal de generación de dataset."""
    print("=" * 70)
    print("GENERADOR DE DATASET OE3 - CITYLEARN v2")
    print("128 Tomas Controlables (32 cargadores × 4 tomas)")
    print("=" * 70)
    print(f"\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Período: {N_HOURS_YEAR} horas (1 año)")

    # Directorio de salida
    output_dir = Path("d:/diseñopvbesscar/data/processed/citylearn/iquitos_128_tomas")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nDirectorio de salida: {output_dir}")

    # Generar datasets para cada playa
    playas_stats = {}

    for playa_name, config in PLAYAS_CONFIG.items():
        seed_offset = 0 if "Motos" in playa_name else 1000

        # Probabilidad base desde configuración calibrada para Tabla 13
        base_prob = config.get("base_probability", 0.35)

        stats = generate_playa_datasets(
            playa_name=playa_name,
            playa_config=config,
            output_dir=output_dir,
            base_probability=base_prob,
            seed_offset=seed_offset
        )
        playas_stats[playa_name] = stats

    # Generar schema CityLearn
    schema = generate_schema_with_tomas(playas_stats, output_dir)

    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)

    total_tomas = 0
    total_energy = 0
    total_power = 0

    for playa_name, stats in playas_stats.items():
        print(f"\n{playa_name}:")
        print(f"  Cargadores: {stats['n_cargadores']}")
        print(f"  Tomas: {stats['n_tomas']}")
        print(f"  Potencia total: {stats['total_power_kw']:.1f} kW")
        print(f"  Energía anual: {stats['total_energy_year_kwh']:,.0f} kWh")

        total_tomas += stats["n_tomas"]
        total_energy += stats["total_energy_year_kwh"]
        total_power += stats["total_power_kw"]

    print(f"\n{'='*70}")
    print(f"TOTALES:")
    print(f"  Cargadores: 32")
    print(f"  Tomas controlables: {total_tomas}")
    print(f"  Potencia instalada: {total_power:.1f} kW")
    print(f"  Energía anual estimada: {total_energy:,.0f} kWh")
    print(f"  Energía diaria promedio: {total_energy/365:,.0f} kWh/día")
    print(f"{'='*70}")

    # Guardar resumen general
    summary = {
        "generacion": datetime.now().isoformat(),
        "n_horas": N_HOURS_YEAR,
        "n_cargadores_total": 32,
        "n_tomas_total": total_tomas,
        "potencia_total_kw": total_power,
        "energia_anual_kwh": total_energy,
        "playas": playas_stats,
        "output_dir": str(output_dir)
    }

    summary_path = output_dir / "dataset_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n✅ Dataset completo generado en: {output_dir}")
    print(f"✅ Resumen guardado en: {summary_path}")

    return summary


if __name__ == "__main__":
    summary = main()
