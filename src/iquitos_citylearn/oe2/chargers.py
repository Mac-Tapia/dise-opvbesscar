"""
Módulo de dimensionamiento de cargadores EV para motos y mototaxis.

Incluye:
- Cálculo de cantidad de vehículos a cargar (diario, mensual, anual)
- Dimensionamiento de cargadores por escenarios
- Perfil de carga diario con horas pico
- Preparación de datos para control individual de cargadores en CityLearn
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import math
import json
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VehicleFleet:
    """Configuración de la flota de vehículos."""
    n_motos: int
    n_mototaxis: int
    battery_kwh_moto: float = 2.0  # kWh batería típica moto eléctrica
    battery_kwh_mototaxi: float = 4.0  # kWh batería típica mototaxi
    daily_km_moto: float = 40.0  # km/día promedio
    daily_km_mototaxi: float = 80.0  # km/día promedio
    efficiency_km_kwh_moto: float = 40.0  # km/kWh
    efficiency_km_kwh_mototaxi: float = 25.0  # km/kWh


@dataclass(frozen=True)
class ChargerSpec:
    """Especificación de un tipo de cargador."""
    charger_id: str
    power_kw: float
    sockets: int
    connector_type: str = "Type2"
    efficiency: float = 0.95


@dataclass
class ChargerSizingResult:
    """Resultado del dimensionamiento de cargadores."""
    scenario_id: int
    pe: float  # Probabilidad de evento de carga
    fc: float  # Factor de carga (% de batería a cargar)
    chargers_required: int
    sockets_total: int
    energy_day_kwh: float
    peak_sessions_per_hour: float
    session_minutes: float
    utilization: float
    charger_power_kw: float
    sockets_per_charger: int
    # Nuevos campos para vehículos
    vehicles_day_motos: int = 0
    vehicles_day_mototaxis: int = 0
    vehicles_month_motos: int = 0
    vehicles_month_mototaxis: int = 0
    vehicles_year_motos: int = 0
    vehicles_year_mototaxis: int = 0


@dataclass
class IndividualCharger:
    """Datos de un cargador individual para CityLearn."""
    charger_id: str
    charger_type: str
    power_kw: float
    sockets: int
    location_x: float = 0.0
    location_y: float = 0.0
    # Perfil de uso asignado
    hourly_load_profile: List[float] = field(default_factory=list)
    daily_energy_kwh: float = 0.0
    peak_power_kw: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'charger_id': self.charger_id,
            'charger_type': self.charger_type,
            'power_kw': self.power_kw,
            'sockets': self.sockets,
            'location_x': self.location_x,
            'location_y': self.location_y,
            'daily_energy_kwh': self.daily_energy_kwh,
            'peak_power_kw': self.peak_power_kw,
            'hourly_load_profile': self.hourly_load_profile,
        }


def calculate_vehicle_demand(
    n_motos: int,
    n_mototaxis: int,
    pe: float,
    fc: float,
    days_per_month: int = 30,
    days_per_year: int = 365,
) -> Dict[str, int]:
    """
    Calcula la cantidad de vehículos a cargar por período.
    
    Args:
        n_motos: Número total de motos en la flota
        n_mototaxis: Número total de mototaxis en la flota
        pe: Probabilidad de evento de carga (0-1)
        fc: Factor de carga (0-1)
        days_per_month: Días por mes
        days_per_year: Días por año
    
    Returns:
        Diccionario con vehículos diarios, mensuales y anuales
    """
    # Vehículos que cargan diariamente
    vehicles_day_motos = int(round(n_motos * pe * fc))
    vehicles_day_mototaxis = int(round(n_mototaxis * pe * fc))
    
    # Proyección mensual y anual
    vehicles_month_motos = vehicles_day_motos * days_per_month
    vehicles_month_mototaxis = vehicles_day_mototaxis * days_per_month
    
    vehicles_year_motos = vehicles_day_motos * days_per_year
    vehicles_year_mototaxis = vehicles_day_mototaxis * days_per_year
    
    return {
        'vehicles_day_motos': vehicles_day_motos,
        'vehicles_day_mototaxis': vehicles_day_mototaxis,
        'vehicles_month_motos': vehicles_month_motos,
        'vehicles_month_mototaxis': vehicles_month_mototaxis,
        'vehicles_year_motos': vehicles_year_motos,
        'vehicles_year_mototaxis': vehicles_year_mototaxis,
    }


def chargers_needed(
    sessions_peak_per_hour: float,
    session_minutes: float,
    utilization: float,
    sockets_per_charger: int,
) -> int:
    """
    Calcula el número de cargadores requeridos en hora pico.

    Cada socket puede atender 60 / (session_minutes / utilization) sesiones por hora.
    Cada cargador tiene `sockets_per_charger` sockets.
    """
    ts_eff = session_minutes / utilization
    sessions_per_socket_per_hour = 60.0 / ts_eff
    capacity_per_charger_per_hour = sockets_per_charger * sessions_per_socket_per_hour
    return int(math.ceil(sessions_peak_per_hour / max(capacity_per_charger_per_hour, 1e-9)))


def compute_capacity_breakdown(
    chargers: int,
    sockets_per_charger: int,
    session_minutes: float,
    opening_hour: int,
    closing_hour: int,
    peak_hours: List[int],
) -> Dict[str, float]:
    """Capacidad pico y total considerando horario de apertura y horas pico."""
    hours_open = max(closing_hour - opening_hour, 0)
    hours_peak = float(len(set(peak_hours)))
    hours_offpeak = max(hours_open - hours_peak, 0.0)
    sessions_per_socket_peak = hours_peak * (60.0 / session_minutes)
    sessions_per_socket_offpeak = hours_offpeak * (60.0 / session_minutes)
    sessions_per_charger_peak = sessions_per_socket_peak * sockets_per_charger
    sessions_per_charger_offpeak = sessions_per_socket_offpeak * sockets_per_charger
    peak_total = sessions_per_charger_peak * chargers
    offpeak_total = sessions_per_charger_offpeak * chargers
    return {
        "hours_open": hours_open,
        "hours_peak": hours_peak,
        "hours_offpeak": hours_offpeak,
        "sessions_peak_total": peak_total,
        "sessions_offpeak_total": offpeak_total,
        "sessions_day_total": peak_total + offpeak_total,
        "sessions_per_charger_peak": sessions_per_charger_peak,
        "sessions_per_charger_day": sessions_per_charger_peak + sessions_per_charger_offpeak,
    }


def compute_capacity_metrics(
    chargers: int,
    sockets_per_charger: int,
    session_minutes: float,
    opening_hour: int,
    closing_hour: int,
) -> Dict[str, float]:
    """Calcula la capacidad de sesiones por hora y por día dada la infraestructura."""
    hours_open = max(closing_hour - opening_hour, 0)
    sessions_per_hour_capacity = chargers * sockets_per_charger * (60.0 / session_minutes)
    sessions_per_day_capacity = sessions_per_hour_capacity * hours_open
    return {
        "sessions_per_hour_capacity": sessions_per_hour_capacity,
        "sessions_per_day_capacity": sessions_per_day_capacity,
    }


def compute_co2_reduction(
    energy_day_kwh: float,
    grid_carbon_kg_per_kwh: float,
    km_per_kwh: float,
    km_per_gallon: float,
    kgco2_per_gallon: float,
) -> Dict[str, float]:
    """Calcula reducción de CO2 al desplazar km eléctricos en lugar de gasolina.
    
    NOTA: Esta función calcula la reducción DIRECTA (electrificación).
    Para la metodología completa OE3, usar compute_co2_breakdown_oe3().
    """
    km_day = energy_day_kwh * km_per_kwh
    gallons_day = km_day / km_per_gallon if km_per_gallon else 0.0
    co2_gas_kg_day = gallons_day * kgco2_per_gallon
    co2_ev_kg_day = energy_day_kwh * grid_carbon_kg_per_kwh
    co2_reduction_kg_day = co2_gas_kg_day - co2_ev_kg_day
    return {
        "km_day": km_day,
        "gallons_day": gallons_day,
        "co2_gas_kg_day": co2_gas_kg_day,
        "co2_ev_kg_day": co2_ev_kg_day,
        "co2_reduction_kg_day": co2_reduction_kg_day,
        "co2_reduction_kg_year": co2_reduction_kg_day * 365.0,
    }


def allocate_grid_to_ev(grid_import_kwh: float, ev_kwh: float, building_kwh: float) -> float:
    """Asigna proporcionalmente la importación de red a la carga EV.
    
    Metodología OE3: la fracción de EV sobre la demanda total determina
    cuánta energía de red se asigna a la carga EV.
    """
    denom = max(ev_kwh + building_kwh, 1e-9)
    return grid_import_kwh * (ev_kwh / denom)


def compute_co2_breakdown_oe3(
    ev_energy_kwh_day: float,
    total_demand_kwh_day: float,
    grid_import_kwh_day: float,
    pv_generation_kwh_day: float,
    grid_export_kwh_day: float,
    grid_carbon_kg_per_kwh: float,
    km_per_kwh: float,
    km_per_gallon: float,
    kgco2_per_gallon: float,
    project_life_years: int = 20,
) -> Dict[str, float]:
    """Calcula breakdown completo de CO2 usando metodología OE3.
    
    Metodología:
    1. Asigna energía de red a EV proporcionalmente (fracción EV/total)
    2. Energía EV no-red = EV total - EV desde red (proviene de PV/BESS)
    3. Reducción DIRECTA = Baseline gasolina - EV toda red
    4. Reducción INDIRECTA = EV desde PV × factor red
    5. NETO = Directa + Indirecta
    
    Args:
        ev_energy_kwh_day: Energía diaria EV
        total_demand_kwh_day: Demanda total diaria (EV + edificio)
        grid_import_kwh_day: Importación diaria de red
        pv_generation_kwh_day: Generación PV diaria
        grid_export_kwh_day: Exportación diaria a red
        grid_carbon_kg_per_kwh: Factor de emisión de red
        km_per_kwh: Eficiencia EV (km/kWh)
        km_per_gallon: Eficiencia gasolina (km/galón)
        kgco2_per_gallon: Factor emisión gasolina
        project_life_years: Vida útil del proyecto (años)
    
    Returns:
        Diccionario con métricas diarias y anuales de reducción CO2
    """
    # Demanda de edificio (sin EV)
    building_kwh_day = total_demand_kwh_day - ev_energy_kwh_day
    
    # Asignación de energía de red a EV (metodología OE3)
    ev_from_grid_kwh_day = allocate_grid_to_ev(
        grid_import_kwh_day, ev_energy_kwh_day, building_kwh_day
    )
    ev_from_pv_kwh_day = max(ev_energy_kwh_day - ev_from_grid_kwh_day, 0.0)
    
    # PV usado localmente
    pv_used_kwh_day = max(pv_generation_kwh_day - grid_export_kwh_day, 0.0)
    
    # Valores anuales
    ev_energy_kwh_year = ev_energy_kwh_day * 365
    ev_from_grid_kwh_year = ev_from_grid_kwh_day * 365
    ev_from_pv_kwh_year = ev_from_pv_kwh_day * 365
    
    # Servicio de transporte
    km_day = ev_energy_kwh_day * km_per_kwh
    km_year = ev_energy_kwh_year * km_per_kwh
    gallons_day = km_day / max(km_per_gallon, 1e-9)
    gallons_year = km_year / max(km_per_gallon, 1e-9)
    
    # 1. Baseline: CO2 si usaran gasolina
    transport_base_kg_day = gallons_day * kgco2_per_gallon
    transport_base_kg_year = gallons_year * kgco2_per_gallon
    
    # 2. CO2 si toda la carga EV fuera de red (escenario sin PV)
    ev_all_grid_kg_day = ev_energy_kwh_day * grid_carbon_kg_per_kwh
    ev_all_grid_kg_year = ev_energy_kwh_year * grid_carbon_kg_per_kwh
    
    # 3. Reducción DIRECTA: Gasolina → EV (aunque toda sea de red)
    direct_avoided_kg_day = transport_base_kg_day - ev_all_grid_kg_day
    direct_avoided_kg_year = transport_base_kg_year - ev_all_grid_kg_year
    
    # 4. Reducción INDIRECTA: EV alimentado por PV en lugar de red
    indirect_avoided_kg_day = ev_from_pv_kwh_day * grid_carbon_kg_per_kwh
    indirect_avoided_kg_year = ev_from_pv_kwh_year * grid_carbon_kg_per_kwh
    
    # 5. Reducción NETA
    net_avoided_kg_day = direct_avoided_kg_day + indirect_avoided_kg_day
    net_avoided_kg_year = direct_avoided_kg_year + indirect_avoided_kg_year
    
    # 6. CO2 residual (EV que aún viene de la red)
    residual_grid_ev_kg_day = ev_from_grid_kwh_day * grid_carbon_kg_per_kwh
    residual_grid_ev_kg_year = ev_from_grid_kwh_year * grid_carbon_kg_per_kwh
    
    # Fracción EV
    ev_fraction = ev_energy_kwh_day / max(total_demand_kwh_day, 1e-9)
    
    return {
        # Energía
        "ev_energy_kwh_day": ev_energy_kwh_day,
        "ev_energy_kwh_year": ev_energy_kwh_year,
        "ev_from_grid_kwh_day": ev_from_grid_kwh_day,
        "ev_from_grid_kwh_year": ev_from_grid_kwh_year,
        "ev_from_pv_kwh_day": ev_from_pv_kwh_day,
        "ev_from_pv_kwh_year": ev_from_pv_kwh_year,
        "ev_fraction": ev_fraction,
        "pv_used_kwh_day": pv_used_kwh_day,
        # Transporte
        "km_day": km_day,
        "km_year": km_year,
        "gallons_day": gallons_day,
        "gallons_year": gallons_year,
        # Baseline gasolina
        "transport_base_kgco2_day": transport_base_kg_day,
        "transport_base_kgco2_year": transport_base_kg_year,
        "transport_base_tco2_year": transport_base_kg_year / 1000.0,
        # Escenario solo red
        "ev_all_grid_kgco2_day": ev_all_grid_kg_day,
        "ev_all_grid_kgco2_year": ev_all_grid_kg_year,
        "ev_all_grid_tco2_year": ev_all_grid_kg_year / 1000.0,
        # Reducción DIRECTA (electrificación)
        "direct_avoided_kgco2_day": direct_avoided_kg_day,
        "direct_avoided_kgco2_year": direct_avoided_kg_year,
        "direct_avoided_tco2_year": direct_avoided_kg_year / 1000.0,
        # Reducción INDIRECTA (PV alimenta EV)
        "indirect_avoided_kgco2_day": indirect_avoided_kg_day,
        "indirect_avoided_kgco2_year": indirect_avoided_kg_year,
        "indirect_avoided_tco2_year": indirect_avoided_kg_year / 1000.0,
        # Reducción NETA
        "net_avoided_kgco2_day": net_avoided_kg_day,
        "net_avoided_kgco2_year": net_avoided_kg_year,
        "net_avoided_tco2_year": net_avoided_kg_year / 1000.0,
        # Residual
        "residual_grid_ev_kgco2_day": residual_grid_ev_kg_day,
        "residual_grid_ev_kgco2_year": residual_grid_ev_kg_year,
        "residual_grid_ev_tco2_year": residual_grid_ev_kg_year / 1000.0,
        # Proyección
        "direct_avoided_tco2_life": direct_avoided_kg_year / 1000.0 * project_life_years,
        "indirect_avoided_tco2_life": indirect_avoided_kg_year / 1000.0 * project_life_years,
        "net_avoided_tco2_life": net_avoided_kg_year / 1000.0 * project_life_years,
    }


def evaluate_scenario(
    scenario_id: int,
    pe_motos: float,
    pe_mototaxis: float,
    fc_motos: float,
    fc_mototaxis: float,
    n_motos: int,
    n_mototaxis: int,
    peak_hours: List[int],
    session_minutes: float,
    utilization: float,
    charger_power_kw_moto: float,
    charger_power_kw_mototaxi: float,
    sockets_per_charger: int,
) -> ChargerSizingResult:
    """
    Evalúa un escenario de dimensionamiento de cargadores Modo 3.
    
    Considera que durante las horas pico (4 horas: 18-22h) llegan
    todos los vehículos de la flota que necesitan cargar.
    
    Args:
        pe_motos: Probabilidad de evento de carga para motos (0-1)
        pe_mototaxis: Probabilidad de evento de carga para mototaxis (0-1)
        fc_motos: Factor de carga motos (% de batería a recargar)
        fc_mototaxis: Factor de carga mototaxis (% de batería a recargar)
        n_motos: Número total de motos en la flota
        n_mototaxis: Número total de mototaxis en la flota
        peak_hours: Lista de horas pico (ej: [18, 19, 20, 21])
        session_minutes: Duración de sesión de carga
        utilization: Factor de utilización del cargador
        charger_power_kw_moto: Potencia cargador motos (2 kW Modo 3)
        charger_power_kw_mototaxi: Potencia cargador mototaxis (3 kW Modo 3)
        sockets_per_charger: Sockets por cargador
    """
    # Vehículos efectivos que cargan (aplicando PE)
    motos_charging = n_motos * pe_motos
    mototaxis_charging = n_mototaxis * pe_mototaxis
    total_vehicles_charging = motos_charging + mototaxis_charging
    
    # Número de horas pico
    n_peak_hours = len(peak_hours)
    
    # Sesiones por hora durante hora punta
    # Los vehículos llegan distribuidos en las 4 horas pico
    sessions_peak_motos = motos_charging / n_peak_hours
    sessions_peak_mototaxis = mototaxis_charging / n_peak_hours
    sessions_peak_per_hour = sessions_peak_motos + sessions_peak_mototaxis
    
    ts_h = session_minutes / 60.0
    
    # Energía por sesión (potencia × tiempo × factor de carga)
    # FC indica qué porcentaje de la batería se recarga
    energy_session_moto_kwh = charger_power_kw_moto * ts_h * fc_motos
    energy_session_mototaxi_kwh = charger_power_kw_mototaxi * ts_h * fc_mototaxis
    
    # Energía diaria total (considera FC en la energía por sesión)
    energy_motos_day = motos_charging * energy_session_moto_kwh
    energy_mototaxis_day = mototaxis_charging * energy_session_mototaxi_kwh
    energy_day = energy_motos_day + energy_mototaxis_day
    
    # Potencia promedio ponderada para cálculo de cargadores
    if total_vehicles_charging > 0:
        avg_charger_power = (motos_charging * charger_power_kw_moto + 
                            mototaxis_charging * charger_power_kw_mototaxi) / total_vehicles_charging
    else:
        avg_charger_power = (charger_power_kw_moto + charger_power_kw_mototaxi) / 2

    chargers = chargers_needed(
        sessions_peak_per_hour=sessions_peak_per_hour,
        session_minutes=session_minutes,
        utilization=utilization,
        sockets_per_charger=sockets_per_charger,
    )
    
    # Calcular vehículos (usando PE promedio y FC promedio para compatibilidad)
    pe_avg = (pe_motos * n_motos + pe_mototaxis * n_mototaxis) / (n_motos + n_mototaxis)
    fc_avg = (fc_motos * n_motos + fc_mototaxis * n_mototaxis) / (n_motos + n_mototaxis)
    vehicle_demand = calculate_vehicle_demand(n_motos, n_mototaxis, pe_avg, fc_avg)

    return ChargerSizingResult(
        scenario_id=scenario_id,
        pe=pe_avg,
        fc=fc_avg,
        chargers_required=chargers,
        sockets_total=chargers * sockets_per_charger,
        energy_day_kwh=energy_day,
        peak_sessions_per_hour=sessions_peak_per_hour,
        session_minutes=session_minutes,
        utilization=utilization,
        charger_power_kw=avg_charger_power,
        sockets_per_charger=sockets_per_charger,
        **vehicle_demand,
    )


def generate_random_scenarios(
    seed: int, 
    n_scenarios: int = 100,
    pe_values: Optional[np.ndarray] = None,
    fc_values: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """Genera escenarios aleatorios de PE y FC."""
    rng = np.random.default_rng(seed)
    if pe_values is None:
        pe_values = np.array([0.10, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 1.0])
    if fc_values is None:
        fc_values = np.array([0.40, 0.50, 0.60, 0.70, 0.80, 1.0])
    
    pe_list = rng.choice(pe_values, size=n_scenarios, replace=True)
    fc_list = rng.choice(fc_values, size=n_scenarios, replace=True)
    return pe_list, fc_list


def select_recommended(df: pd.DataFrame) -> pd.Series:
    """
    Selecciona el escenario recomendado de un DataFrame de escenarios.

    La estrategia de selección es la siguiente:
    1. Filtra los escenarios para quedarse con aquellos cuyo número de cargadores
       requeridos está en o por encima del percentil 75.
    2. De entre esos escenarios, selecciona el que tiene la máxima energía diaria.

    Args:
        df: DataFrame con los escenarios de dimensionamiento. Debe contener
            las columnas 'chargers_required' y 'energy_day_kwh'.

    Returns:
        Una Serie de pandas con la fila del escenario recomendado.
    """
    p75 = df["chargers_required"].quantile(0.75)
    df_p75 = df[df["chargers_required"] >= p75]
    return df_p75.sort_values("energy_day_kwh", ascending=False).iloc[0]


def build_hourly_profile(
    energy_day_kwh: float,
    opening_hour: int,
    closing_hour: int,
    peak_hours: List[int],
    peak_share_day: float,
) -> pd.DataFrame:
    """
    Construye perfil de carga horario de 24h.

    Distribuye la energía diaria con campana suave que encaja en el bloque pico:
    - Subida progresiva (smoothstep) desde apertura hasta inicio de pico.
    - Pico plano en la ventana definida.
    - Bajada progresiva (smoothstep) hasta el cierre.
    - Respeta peak_share_day para energía en pico vs. resto.
    """
    hours = list(range(24))
    operating_hours = [h for h in hours if opening_hour <= h <= closing_hour]
    hours_peak = [h for h in peak_hours if h in operating_hours]
    hours_day = len(operating_hours)

    share_peak = peak_share_day
    share_off = 1.0 - share_peak
    peak_start = min(hours_peak) if hours_peak else opening_hour
    peak_end = max(hours_peak) if hours_peak else peak_start

    def smoothstep(x: float) -> float:
        # transición suave 0->1 sin quiebres
        return x * x * (3 - 2 * x)

    # Pesos base: pre-pico crece suave, pico plano, post-pico decrece suave
    pre_peak = [h for h in operating_hours if h < peak_start]
    post_peak = [h for h in operating_hours if h > peak_end]

    weights_base: Dict[int, float] = {}
    # Subida
    for h in pre_peak:
        t = (h - opening_hour) / max(len(pre_peak), 1)
        weights_base[h] = max(0.0, smoothstep(t))
    # Pico plano
    for h in hours_peak:
        weights_base[h] = 1.0
    # Bajada
    for h in post_peak:
        t = (closing_hour - h) / max(len(post_peak), 1)
        weights_base[h] = max(0.0, smoothstep(t))

    base_peak_sum = sum(weights_base[h] for h in hours_peak) if hours_peak else 0.0
    base_off_sum = sum(weights_base[h] for h in operating_hours if h not in hours_peak)

    weights: Dict[int, float] = {}
    for h in operating_hours:
        if h in hours_peak and base_peak_sum > 0:
            weights[h] = weights_base[h] * (share_peak / base_peak_sum)
        elif h not in hours_peak and base_off_sum > 0:
            weights[h] = weights_base[h] * (share_off / base_off_sum)
        else:
            weights[h] = 0.0

    total_w = sum(weights.values()) if weights else 1.0
    factors = []
    is_peak = []
    for h in hours:
        if h in weights:
            factors.append(weights[h] / total_w)
            is_peak.append(h in hours_peak)
        else:
            factors.append(0.0)
            is_peak.append(False)

    factors = np.array(factors, dtype=float)

    energy_h = energy_day_kwh * factors
    power_kw = energy_h  # 1-hour timestep: kWh == kW average

    return pd.DataFrame({
        "hour": hours,
        "factor": factors,
        "energy_kwh": energy_h,
        "power_kw": power_kw,
        "is_peak": is_peak,
    })


def create_individual_chargers(
    n_chargers: int,
    charger_power_kw: float,
    sockets_per_charger: int,
    daily_profile: pd.DataFrame,
    charger_type: str = "Level2",
    prefix: str = "EV_CHARGER",
    start_index: int = 1,
) -> List[IndividualCharger]:
    """
    Crea una lista de cargadores individuales para simulación en CityLearn.

    Distribuye la carga total diaria (definida en `daily_profile`) de manera
    equitativa entre el número de cargadores especificado. Para simular un
    uso más realista, introduce una pequeña variación aleatoria (+/- 10%) en
    el perfil de carga de cada cargador, normalizando luego para que la
    energía diaria total se conserve.

    Args:
        n_chargers: Número de cargadores individuales a crear.
        charger_power_kw: Potencia nominal de cada cargador en kW.
        sockets_per_charger: Número de tomas por cargador.
        daily_profile: DataFrame con el perfil de carga agregado de 24 horas.
                       Debe contener las columnas 'energy_kwh' y 'power_kw'.
        charger_type: Etiqueta del tipo de cargador (ej. "Level2_EV").

    Returns:
        Una lista de objetos `IndividualCharger`, cada uno con su perfil de
        carga horario, listo para ser usado en CityLearn.
    """
    chargers = []
    total_daily_energy = daily_profile['energy_kwh'].sum()
    energy_per_charger = total_daily_energy / n_chargers

    # Perfil base por cargador
    base_profile = (daily_profile['power_kw'] / n_chargers).tolist()

    for i in range(n_chargers):
        # Pequeña variación en el perfil (+/- 10%)
        rng = np.random.default_rng(42 + i)
        variation = 1.0 + rng.uniform(-0.1, 0.1, 24)
        individual_profile = [p * v for p, v in zip(base_profile, variation)]
        
        # Normalizar para mantener energía total
        profile_sum = sum(individual_profile)
        if profile_sum > 0:
            individual_profile = [p * energy_per_charger / profile_sum for p in individual_profile]
        
        charger = IndividualCharger(
            charger_id=f"{prefix}_{start_index + i:03d}",
            charger_type=charger_type,
            power_kw=charger_power_kw,
            sockets=sockets_per_charger,
            location_x=(i % 10) * 5.0,  # Distribución en grid
            location_y=(i // 10) * 5.0,
            hourly_load_profile=individual_profile,
            daily_energy_kwh=sum(individual_profile),
            peak_power_kw=max(individual_profile) if individual_profile else 0,
        )
        chargers.append(charger)
    
    return chargers


def generate_charger_plots(
    df_scenarios: pd.DataFrame,
    esc_rec: pd.Series,
    profile: pd.DataFrame,
    out_dir: Path,
    reports_dir: Optional[Path] = None,
) -> None:
    """
    Genera y guarda un conjunto de gráficas para el análisis de dimensionamiento.

    Crea las siguientes visualizaciones:
    1.  **Vehículos a Cargar por Período:** Gráfico de barras que muestra la
        cantidad de motos y mototaxis a cargar diaria, mensual y anualmente
        para el escenario recomendado.
    2.  **Perfil de Carga Diario:** Gráfico de línea que muestra la distribución
        horaria de la demanda de energía, destacando las horas pico.
    3.  **Análisis de Escenarios:** Un mapa de calor que relaciona PE y FC con
        el número de cargadores, y un histograma de la distribución de
        cargadores requeridos.
    4.  **Resumen del Sistema:** Un dashboard con la energía diaria, la
        relación entre sesiones pico y cargadores, una tabla resumen y el
        perfil de potencia horario.

    Args:
        df_scenarios: DataFrame con todos los escenarios de sensibilidad evaluados.
        esc_rec: Serie de pandas que representa el escenario recomendado.
        profile: DataFrame con el perfil de carga horario del escenario recomendado.
        out_dir: Directorio base para guardar las gráficas (usado si `reports_dir`
                 es None).
        reports_dir: Directorio de reportes de alto nivel donde se guardarán las
                     gráficas, dentro de una subcarpeta `oe2/chargers`.
    """
    import matplotlib.pyplot as plt
    
    plots_dir = out_dir / "plots"
    if reports_dir is not None:
        plots_dir = reports_dir / "oe2" / "chargers"
    plots_dir.mkdir(parents=True, exist_ok=True)
    
    def save_plot(filename: str):
        """Guarda plot en un solo directorio con manejo de errores."""
        try:
            plt.savefig(plots_dir / filename, dpi=150, bbox_inches='tight')
        except (IOError, OSError) as e:
            print(f"  [ERROR] No se pudo guardar la gráfica {filename}: {e}")
    
    # ===========================================================
    # Gráfica 1: Cantidad de Vehículos a Cargar por Período
    # ===========================================================
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    
    # Datos del escenario recomendado
    motos_day = int(esc_rec.get('vehicles_day_motos', 0))
    mototaxis_day = int(esc_rec.get('vehicles_day_mototaxis', 0))
    motos_month = int(esc_rec.get('vehicles_month_motos', 0))
    mototaxis_month = int(esc_rec.get('vehicles_month_mototaxis', 0))
    motos_year = int(esc_rec.get('vehicles_year_motos', 0))
    mototaxis_year = int(esc_rec.get('vehicles_year_mototaxis', 0))
    
    periods = ['Diario', 'Mensual', 'Anual']
    motos_data = [motos_day, motos_month, motos_year]
    mototaxis_data = [mototaxis_day, mototaxis_month, mototaxis_year]
    
    colors = ['#5DADE2', '#F1948A']  # Azul claro, Rojo claro
    
    for idx, (period, m, mt) in enumerate(zip(periods, motos_data, mototaxis_data)):
        ax = axes[idx]
        x = ['Motos', 'Mototaxis']
        heights = [m, mt]
        bars = ax.bar(x, heights, color=colors, edgecolor='black', alpha=0.9)
        
        # Etiquetas en barras
        for bar, val in zip(bars, heights):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(heights)*0.02,
                    f'{val:,}', ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax.set_title(period, fontsize=12, fontweight='bold')
        ax.set_ylabel('Cantidad de Vehículos', fontsize=10)
        ax.set_ylim(0, max(heights) * 1.15 if max(heights) > 0 else 100)
    
    plt.suptitle('Cantidad de Vehículos a Cargar por Período (Escenario Recomendado)', 
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    save_plot('chargers_vehiculos_por_periodo.png')
    plt.close()
    print("  [OK] Grafica: Vehiculos a Cargar por Periodo")
    
    # ===========================================================
    # Gráfica 2: Perfil de Carga Diario con Horas Pico
    # ===========================================================
    fig, ax = plt.subplots(figsize=(12, 6))
    
    hours = np.asarray(profile['hour'].values)
    power = np.asarray(profile['power_kw'].values)
    is_peak = profile['is_peak'].values
    
    # Marcar zona de horas pico
    peak_start = None
    peak_end = None
    for i, (h, pk) in enumerate(zip(hours, is_peak)):
        if pk and peak_start is None:
            peak_start = h
        if pk:
            peak_end = h
    
    if peak_start is not None and peak_end is not None:
        ax.axvspan(peak_start - 0.5, peak_end + 0.5, alpha=0.3, color='orange', label='Horas Pico')
    
    # Línea suavizada de energía/potencia (sin alterar los valores originales)
    x_fine = np.linspace(hours.min(), hours.max(), num=len(hours) * 4)
    power_smooth = np.interp(x_fine, hours, power)
    ax.plot(x_fine, power_smooth, '-', color='steelblue', linewidth=2, label='Energía / Potencia (suavizado)')
    ax.plot(hours, power, 'o', color='steelblue', markersize=4, alpha=0.6)
    
    ax.set_xlabel('Hora', fontsize=11)
    ax.set_ylabel('Energía (kWh) / Potencia (kW)', fontsize=11)
    ax.set_title('Perfil de Carga Diario - Escenario Recomendado', fontsize=13, fontweight='bold')
    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(range(24))
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    save_plot('chargers_perfil_diario.png')
    plt.close()
    print("  [OK] Grafica: Perfil de Carga Diario")
    
    # ===========================================================
    # Gráfica 3: Comparación de Escenarios (PE x FC)
    # ===========================================================
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Mapa de calor: Cargadores requeridos vs PE y FC
    ax1 = axes[0]
    pivot = df_scenarios.pivot_table(values='chargers_required', index='fc', columns='pe', aggfunc='mean')
    im = ax1.imshow(pivot.values, aspect='auto', cmap='YlOrRd', origin='lower')
    ax1.set_xticks(range(len(pivot.columns)))
    ax1.set_xticklabels([f'{x:.2f}' for x in pivot.columns], fontsize=8)
    ax1.set_yticks(range(len(pivot.index)))
    ax1.set_yticklabels([f'{y:.2f}' for y in pivot.index], fontsize=8)
    ax1.set_xlabel('PE (Probabilidad de Evento)', fontsize=10)
    ax1.set_ylabel('FC (Factor de Carga)', fontsize=10)
    ax1.set_title('Cargadores Requeridos por Escenario', fontsize=11, fontweight='bold')
    cbar = plt.colorbar(im, ax=ax1)
    cbar.set_label('Cargadores')
    
    # Distribución de cargadores
    ax2 = axes[1]
    ax2.hist(df_scenarios['chargers_required'], bins=20, color='steelblue', 
             edgecolor='white', alpha=0.7)
    ax2.axvline(x=esc_rec['chargers_required'], color='red', linestyle='--', 
                linewidth=2, label=f'Recomendado: {int(esc_rec["chargers_required"])}')
    ax2.set_xlabel('Número de Cargadores', fontsize=10)
    ax2.set_ylabel('Frecuencia', fontsize=10)
    ax2.set_title('Distribución de Cargadores por Escenario', fontsize=11, fontweight='bold')
    ax2.legend()
    
    plt.suptitle('Análisis de Escenarios de Dimensionamiento', fontsize=13, fontweight='bold')
    plt.tight_layout()
    save_plot('chargers_analisis_escenarios.png')
    plt.close()
    print("  [OK] Grafica: Analisis de Escenarios")
    
    # ===========================================================
    # Gráfica 4: Resumen del Sistema de Carga
    # ===========================================================
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Panel 1: Energía diaria por escenario
    ax1 = axes[0, 0]
    ax1.scatter(df_scenarios['pe'] * df_scenarios['fc'], df_scenarios['energy_day_kwh'],
                alpha=0.5, c='steelblue', s=50)
    ax1.axhline(y=esc_rec['energy_day_kwh'], color='red', linestyle='--', 
                label=f'Recomendado: {esc_rec["energy_day_kwh"]:.0f} kWh')
    ax1.set_xlabel('PE × FC', fontsize=10)
    ax1.set_ylabel('Energía Diaria (kWh)', fontsize=10)
    ax1.set_title('Energía Diaria vs Factor Combinado', fontsize=11, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: Sesiones pico vs cargadores
    ax2 = axes[0, 1]
    ax2.scatter(df_scenarios['peak_sessions_per_hour'], df_scenarios['chargers_required'],
                alpha=0.5, c='green', s=50)
    ax2.set_xlabel('Sesiones Pico por Hora', fontsize=10)
    ax2.set_ylabel('Cargadores Requeridos', fontsize=10)
    ax2.set_title('Sesiones Pico vs Cargadores', fontsize=11, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: Tabla resumen
    ax3 = axes[1, 0]
    ax3.axis('off')
    
    summary_data = [
        ['Parámetro', 'Mínimo', 'Recomendado', 'Máximo'],
        ['Cargadores', f'{df_scenarios["chargers_required"].min():.0f}', 
         f'{esc_rec["chargers_required"]:.0f}', f'{df_scenarios["chargers_required"].max():.0f}'],
        ['Sockets', f'{df_scenarios["sockets_total"].min():.0f}',
         f'{esc_rec["sockets_total"]:.0f}', f'{df_scenarios["sockets_total"].max():.0f}'],
        ['Energía/día (kWh)', f'{df_scenarios["energy_day_kwh"].min():.0f}',
         f'{esc_rec["energy_day_kwh"]:.0f}', f'{df_scenarios["energy_day_kwh"].max():.0f}'],
        ['Motos/día', f'{df_scenarios["vehicles_day_motos"].min():.0f}',
         f'{esc_rec["vehicles_day_motos"]:.0f}', f'{df_scenarios["vehicles_day_motos"].max():.0f}'],
        ['Mototaxis/día', f'{df_scenarios["vehicles_day_mototaxis"].min():.0f}',
         f'{esc_rec["vehicles_day_mototaxis"]:.0f}', f'{df_scenarios["vehicles_day_mototaxis"].max():.0f}'],
    ]
    
    table = ax3.table(cellText=summary_data[1:], colLabels=summary_data[0],
                      cellLoc='center', loc='center', colWidths=[0.35, 0.2, 0.25, 0.2])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)
    
    # Colorear header
    for i in range(4):
        table[(0, i)].set_facecolor('steelblue')
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    
    ax3.set_title('Resumen de Escenarios', fontsize=11, fontweight='bold', y=0.95)
    
    # Panel 4: Perfil horario ampliado
    ax4 = axes[1, 1]
    bars = ax4.bar(profile['hour'], profile['power_kw'], color='steelblue', 
                   edgecolor='darkblue', alpha=0.8)
    
    # Marcar horas pico
    for i, (h, pk) in enumerate(zip(profile['hour'], profile['is_peak'])):
        if pk:
            bars[i].set_color('orange')
    
    ax4.set_xlabel('Hora del Día', fontsize=10)
    ax4.set_ylabel('Potencia (kW)', fontsize=10)
    ax4.set_title('Perfil de Potencia Horario', fontsize=11, fontweight='bold')
    ax4.set_xticks(range(0, 24, 2))
    
    # Estadísticas
    total_energy = profile['energy_kwh'].sum()
    peak_power = profile['power_kw'].max()
    ax4.annotate(f'Energía total: {total_energy:.0f} kWh\nPotencia pico: {peak_power:.0f} kW',
                 xy=(0.98, 0.95), xycoords='axes fraction', ha='right', va='top',
                 fontsize=9, bbox=dict(boxstyle='round', facecolor='lightyellow'))
    
    plt.suptitle('Sistema de Carga EV - Resumen', fontsize=14, fontweight='bold')
    plt.tight_layout()
    save_plot('chargers_resumen_sistema.png')
    plt.close()
    print("  [OK] Grafica: Resumen del Sistema de Carga")
    
    print(f"  OK Plots guardados en: {plots_dir}")


def run_charger_sizing(
    out_dir: Path,
    seed: int,
    n_motos: int,
    n_mototaxis: int,
    pe_motos: float,
    pe_mototaxis: float,
    fc_motos: float,
    fc_mototaxis: float,
    peak_share_day: float,
    session_minutes: float,
    utilization: float,
    charger_power_kw_moto: float,
    charger_power_kw_mototaxi: float,
    sockets_per_charger: int,
    opening_hour: int,
    closing_hour: int,
    km_per_kwh: float,
    km_per_gallon: float,
    kgco2_per_gallon: float,
    grid_carbon_kg_per_kwh: float,
    peak_hours: List[int],
    n_scenarios: int = 100,
    generate_plots: bool = True,
    reports_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Orquesta el proceso completo de dimensionamiento de cargadores EV Modo 3.

    Esta función ejecuta los siguientes pasos:
    1.  Calcula la demanda de la flota de vehículos eléctricos (motos y mototaxis).
    2.  Evalúa un escenario de dimensionamiento principal basado en los parámetros
        de entrada (PE, FC, etc.) para establecer una recomendación.
    3.  Realiza un análisis de sensibilidad generando múltiples escenarios aleatorios
        de PE (Probabilidad de Evento) y FC (Factor de Carga).
    4.  Determina los escenarios de mínimo y máximo requerimiento de cargadores.
    5.  Construye y exporta el perfil de carga horario para el escenario recomendado.
    6.  Prepara y guarda los datos de cargadores individuales para su uso en
        simulaciones con CityLearn.
    7.  Genera un conjunto de gráficas y reportes visuales si se solicita.
    8.  Guarda todos los resultados, incluyendo dataframes y metadatos, en el
        directorio de salida.

    Args:
        out_dir: Directorio para guardar todos los artefactos generados.
        seed: Semilla para la generación de números aleatorios, asegurando
              reproducibilidad.
        n_motos: Número total de motos en la flota.
        n_mototaxis: Número total de mototaxis en la flota.
        pe_motos: Probabilidad de que una moto necesite cargar en un día (0-1).
        pe_mototaxis: Probabilidad de que un mototaxi necesite cargar (0-1).
        fc_motos: Factor de carga promedio para motos (% de batería a recargar).
        fc_mototaxis: Factor de carga promedio para mototaxis.
        peak_share_day: Porcentaje de la energía diaria que se consume en horas pico.
        session_minutes: Duración estimada de una sesión de carga en minutos.
        utilization: Factor de utilización de los cargadores (0-1).
        charger_power_kw_moto: Potencia del cargador para motos (kW).
        charger_power_kw_mototaxi: Potencia del cargador para mototaxis (kW).
        sockets_per_charger: Número de tomas por cada cargador.
        opening_hour: Hora de apertura del centro de carga.
        closing_hour: Hora de cierre del centro de carga.
        peak_hours: Lista de horas consideradas como pico.
        n_scenarios: Número de escenarios a generar para el análisis de sensibilidad.
        generate_plots: Si es `True`, genera y guarda las gráficas de análisis.
        reports_dir: Directorio opcional para guardar las gráficas en una estructura
                     de reportes.

    Returns:
        Un diccionario que resume los resultados clave del dimensionamiento,
        incluyendo el número de cargadores recomendados, la energía diaria,
        potencia pico y rutas a los archivos generados.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Calcular potencia total instalada
    potencia_instalada_motos = n_motos * charger_power_kw_moto
    potencia_instalada_mototaxis = n_mototaxis * charger_power_kw_mototaxi
    potencia_total_instalada = potencia_instalada_motos + potencia_instalada_mototaxis
    
    # Vehículos efectivos que cargan
    motos_efectivas = n_motos * pe_motos
    mototaxis_efectivas = n_mototaxis * pe_mototaxis
    
    print("\n" + "="*60)
    print("  DIMENSIONAMIENTO DE CARGADORES EV - MODO 3 (IEC 61851)")
    print("="*60)
    print(f"\n[+] Flota de vehiculos:")
    print(f"   Motos: {n_motos:,} (PE={pe_motos:.0%}, FC={fc_motos:.0%})")
    print(f"   Mototaxis: {n_mototaxis:,} (PE={pe_mototaxis:.0%}, FC={fc_mototaxis:.0%})")
    print(f"   Motos efectivas/día: {motos_efectivas:,.0f}")
    print(f"   Mototaxis efectivas/día: {mototaxis_efectivas:,.0f}")
    print(f"\n[+] Configuracion de carga Modo 3:")
    print(f"   Potencia cargador motos: {charger_power_kw_moto} kW")
    print(f"   Potencia cargador mototaxis: {charger_power_kw_mototaxi} kW")
    print(f"   Sockets por cargador: {sockets_per_charger}")
    print(f"   Duración sesión: {session_minutes} min")
    print(f"   Horario mall: {opening_hour}:00 - {closing_hour}:00")
    print(f"   Horas pico: {peak_hours} ({len(peak_hours)} horas)")
    print(f"\n[+] Demanda Total Instalada:")
    print(f"   Motos:     {n_motos:,} × {charger_power_kw_moto} kW = {potencia_instalada_motos:,.0f} kW")
    print(f"   Mototaxis: {n_mototaxis:,} × {charger_power_kw_mototaxi} kW = {potencia_instalada_mototaxis:,.0f} kW")
    print(f"   TOTAL:     {potencia_total_instalada:,.0f} kW")

    # Evaluar escenario con los parámetros dados
    print(f"\n[+] Evaluando escenario con PE y FC configurados...")
    
    res = evaluate_scenario(
        scenario_id=1,
        pe_motos=pe_motos,
        pe_mototaxis=pe_mototaxis,
        fc_motos=fc_motos,
        fc_mototaxis=fc_mototaxis,
        n_motos=n_motos,
        n_mototaxis=n_mototaxis,
        peak_hours=peak_hours,
        session_minutes=session_minutes,
        utilization=utilization,
        charger_power_kw_moto=charger_power_kw_moto,
        charger_power_kw_mototaxi=charger_power_kw_mototaxi,
        sockets_per_charger=sockets_per_charger,
    )
    
    # Usar el resultado como escenario recomendado
    esc_rec = pd.Series(res.__dict__)

    # Ajustar vehículos diarios según capacidad total (9-22h) y mix motos/mototaxis
    capacity_mix = compute_capacity_breakdown(
        chargers=int(esc_rec["chargers_required"]),
        sockets_per_charger=sockets_per_charger,
        session_minutes=session_minutes,
        opening_hour=opening_hour,
        closing_hour=closing_hour,
        peak_hours=peak_hours,
    )
    total_sessions_day = capacity_mix["sessions_day_total"]
    share_motos = n_motos / max(n_motos + n_mototaxis, 1e-9)
    share_mototaxis = 1.0 - share_motos
    esc_rec["vehicles_day_motos"] = total_sessions_day * share_motos
    esc_rec["vehicles_day_mototaxis"] = total_sessions_day * share_mototaxis
    esc_rec["vehicles_month_motos"] = esc_rec["vehicles_day_motos"] * 30
    esc_rec["vehicles_month_mototaxis"] = esc_rec["vehicles_day_mototaxis"] * 30
    esc_rec["vehicles_year_motos"] = esc_rec["vehicles_day_motos"] * 365
    esc_rec["vehicles_year_mototaxis"] = esc_rec["vehicles_day_mototaxis"] * 365
    # Recalcular energía diaria usando todos los vehículos/día efectivos
    ts_h = session_minutes / 60.0
    energy_session_moto = charger_power_kw_moto * ts_h * fc_motos
    energy_session_mototaxi = charger_power_kw_mototaxi * ts_h * fc_mototaxis
    energy_day_total = esc_rec["vehicles_day_motos"] * energy_session_moto + esc_rec["vehicles_day_mototaxis"] * energy_session_mototaxi
    esc_rec["energy_day_kwh"] = energy_day_total
    res.energy_day_kwh = energy_day_total
    
    # También generar escenarios adicionales para análisis de sensibilidad
    pe_list, fc_list = generate_random_scenarios(seed=seed, n_scenarios=n_scenarios)
    rows = []
    scenario_results: List[ChargerSizingResult] = []
    for i, (pe, fc) in enumerate(zip(pe_list, fc_list), start=2):
        res_i = evaluate_scenario(
            scenario_id=i,
            pe_motos=pe,
            pe_mototaxis=pe,
            fc_motos=fc,
            fc_mototaxis=fc,
            n_motos=n_motos,
            n_mototaxis=n_mototaxis,
            peak_hours=peak_hours,
            session_minutes=session_minutes,
            utilization=utilization,
            charger_power_kw_moto=charger_power_kw_moto,
            charger_power_kw_mototaxi=charger_power_kw_mototaxi,
            sockets_per_charger=sockets_per_charger,
        )
        scenario_results.append(res_i)
        rows.append(res_i.__dict__)

    df = pd.DataFrame(rows).drop_duplicates(subset=["pe", "fc"]).reset_index(drop=True)
    try:
        df.to_csv(out_dir / "selection_pe_fc_completo.csv", index=False)
        print(f"   [OK] {len(df)} escenarios de sensibilidad evaluados")
    except (IOError, OSError) as e:
        print(f"   [ERROR] No se pudo guardar el archivo de escenarios: {e}")

    # Seleccionar escenarios min/max para comparación
    esc_min = df.sort_values("chargers_required", ascending=True).iloc[0]
    esc_max = df.sort_values("chargers_required", ascending=False).iloc[0]
    
    print(f"\n[+] Resultado del dimensionamiento:")
    print(f"   RECOMENDADO: {int(esc_rec['chargers_required'])} cargadores")
    print(f"   Sesiones/hora pico: {esc_rec['peak_sessions_per_hour']:.0f}")
    print(f"   Energía diaria: {esc_rec['energy_day_kwh']:.0f} kWh")
    print(f"\n   Análisis de sensibilidad:")
    print(f"   Mínimo:      {int(esc_min['chargers_required'])} cargadores (PE={esc_min['pe']:.2f}, FC={esc_min['fc']:.2f})")
    print(f"   Máximo:      {int(esc_max['chargers_required'])} cargadores (PE={esc_max['pe']:.2f}, FC={esc_max['fc']:.2f})")

    # Exportar perfiles horarios para cada escenario (incluye recomendado)
    variant_dir = out_dir / "charger_profile_variants"
    variant_dir.mkdir(parents=True, exist_ok=True)
    variant_metadata: List[Dict[str, Any]] = []
    variant_rows = [res] + scenario_results
    for variant in variant_rows:
        scenario_id = int(variant.scenario_id)
        profile_df = build_hourly_profile(
            energy_day_kwh=float(variant.energy_day_kwh),
            opening_hour=opening_hour,
            closing_hour=closing_hour,
            peak_hours=peak_hours,
            peak_share_day=peak_share_day,
        )
        profile_filename = f"scenario_{scenario_id:03d}_profile.csv"
        profile_path = variant_dir / profile_filename
        try:
            profile_df.to_csv(profile_path, index=False)
            variant_metadata.append(
                {
                    "scenario_id": scenario_id,
                    "pe": variant.pe,
                    "fc": variant.fc,
                    "energy_day_kwh": variant.energy_day_kwh,
                    "chargers_required": variant.chargers_required,
                    "peak_sessions_per_hour": variant.peak_sessions_per_hour,
                    "profile_path": profile_filename,
                    "is_recommended": scenario_id == res.scenario_id,
                }
            )
        except (IOError, OSError) as e:
            print(f"   [ERROR] No se pudo guardar el perfil para el escenario {scenario_id}: {e}")

    # Construir perfil horario
    profile = build_hourly_profile(
        energy_day_kwh=float(esc_rec["energy_day_kwh"]),
        opening_hour=opening_hour,
        closing_hour=closing_hour,
        peak_hours=peak_hours,
        peak_share_day=peak_share_day,
    )
    try:
        profile.to_csv(out_dir / "perfil_horario_carga.csv", index=False)
    except (IOError, OSError) as e:
        print(f"   [ERROR] No se pudo guardar el perfil de carga horario: {e}")
    
    # Estadísticas de vehículos
    print(f"\n[+] Vehiculos a cargar (Escenario Recomendado):")
    print(f"   Diario:  {int(esc_rec['vehicles_day_motos']):,} motos + {int(esc_rec['vehicles_day_mototaxis']):,} mototaxis")
    print(f"   Mensual: {int(esc_rec['vehicles_month_motos']):,} motos + {int(esc_rec['vehicles_month_mototaxis']):,} mototaxis")
    print(f"   Anual:   {int(esc_rec['vehicles_year_motos']):,} motos + {int(esc_rec['vehicles_year_mototaxis']):,} mototaxis")
    
    # Crear cargadores individuales para CityLearn (per-toma controlable)
    # Reparto: 28 cargadores motos (2 kW) -> 112 tomas individuales
    #          4 cargadores mototaxis (3 kW) -> 16 tomas individuales
    n_moto_chargers = 28
    n_mototaxi_chargers = 4
    n_tomas_moto = n_moto_chargers * sockets_per_charger
    n_tomas_mototaxi = n_mototaxi_chargers * sockets_per_charger

    total_veh = esc_rec['vehicles_day_motos'] + esc_rec['vehicles_day_mototaxis']
    frac_moto = esc_rec['vehicles_day_motos'] / total_veh if total_veh > 0 else 0.8
    energy_moto = profile['energy_kwh'].sum() * frac_moto
    energy_mototaxi = profile['energy_kwh'].sum() - energy_moto

    profile_moto = build_hourly_profile(
        energy_day_kwh=energy_moto,
        opening_hour=opening_hour,
        closing_hour=closing_hour,
        peak_hours=peak_hours,
        peak_share_day=peak_share_day,
    )
    profile_mototaxi = build_hourly_profile(
        energy_day_kwh=energy_mototaxi,
        opening_hour=opening_hour,
        closing_hour=closing_hour,
        peak_hours=peak_hours,
        peak_share_day=peak_share_day,
    )

    individual_chargers = []
    individual_chargers += create_individual_chargers(
        n_chargers=n_tomas_moto,
        charger_power_kw=charger_power_kw_moto,
        sockets_per_charger=1,
        daily_profile=profile_moto,
        charger_type="Level2_MOTO",
        prefix="MOTO_CH",
        start_index=1,
    )
    individual_chargers += create_individual_chargers(
        n_chargers=n_tomas_mototaxi,
        charger_power_kw=charger_power_kw_mototaxi,
        sockets_per_charger=1,
        daily_profile=profile_mototaxi,
        charger_type="Level2_MOTOTAXI",
        prefix="MOTO_TAXI_CH",
        start_index=n_tomas_moto + 1,
    )
    
    # Guardar datos de cargadores individuales
    chargers_data = [c.to_dict() for c in individual_chargers]
    try:
        (out_dir / "individual_chargers.json").write_text(
            json.dumps(chargers_data, indent=2), encoding="utf-8"
        )
        print(f"\n[+] Cargadores individuales preparados: {len(individual_chargers)}")
    except (IOError, OSError) as e:
        print(f"\n[ERROR] No se pudo guardar el archivo JSON de cargadores individuales: {e}")
    
    # Crear DataFrame de cargadores para CityLearn
    chargers_df = pd.DataFrame([{
        'charger_id': c.charger_id,
        'power_kw': c.power_kw,
        'sockets': c.sockets,
        'daily_energy_kwh': c.daily_energy_kwh,
        'peak_power_kw': c.peak_power_kw,
    } for c in individual_chargers])
    try:
        chargers_df.to_csv(out_dir / "chargers_citylearn.csv", index=False)
    except (IOError, OSError) as e:
        print(f"   [ERROR] No se pudo guardar el archivo CSV de cargadores para CityLearn: {e}")
    
    # Crear perfiles horarios por cargador (para CityLearn)
    hourly_profiles_df = pd.DataFrame({
        c.charger_id: c.hourly_load_profile for c in individual_chargers
    })
    hourly_profiles_df.index.name = 'hour'
    try:
        hourly_profiles_df.to_csv(out_dir / "chargers_hourly_profiles.csv")
    except (IOError, OSError) as e:
        print(f"   [ERROR] No se pudo guardar el archivo de perfiles horarios por cargador: {e}")
    
    # Generar gráficas
    if generate_plots:
        print("\n[+] Generando graficas...")
        generate_charger_plots(df, esc_rec, profile, out_dir, reports_dir=reports_dir)

    # Supuestos de SOC de llegada y energia/tiempo restante promedio
    soc_arrival_pct = [20, 40, 50, 60]
    soc_missing_pct = [80, 60, 50, 40]
    avg_missing_frac = 0.575  # 57.5% de la energia de una sesion de 30 min
    full_energy_per_session_kwh = esc_rec["charger_power_kw"] * (session_minutes / 60.0)
    avg_energy_needed_kwh = full_energy_per_session_kwh * avg_missing_frac
    avg_time_remaining_minutes = session_minutes * avg_missing_frac

    co2_metrics = compute_co2_reduction(
        energy_day_kwh=float(esc_rec['energy_day_kwh']),
        grid_carbon_kg_per_kwh=float(grid_carbon_kg_per_kwh),
        km_per_kwh=float(km_per_kwh),
        km_per_gallon=float(km_per_gallon),
        kgco2_per_gallon=float(kgco2_per_gallon),
    )
    print(f"   SOC llegada (supuesto): {soc_arrival_pct} % -> faltan {soc_missing_pct} %")
    print(f"   Energia x sesion (30 min): {full_energy_per_session_kwh:.2f} kWh")
    print(f"   Energia faltante promedio: {avg_energy_needed_kwh:.2f} kWh (~{avg_missing_frac*100:.1f}% de la sesion)")
    print(f"   Tiempo restante promedio: {avg_time_remaining_minutes:.1f} min")

    capacity = compute_capacity_metrics(
        chargers=int(esc_rec.get("chargers_required", n_chargers_rec)),
        sockets_per_charger=sockets_per_charger,
        session_minutes=session_minutes,
        opening_hour=opening_hour,
        closing_hour=closing_hour,
    )

    # Resumen JSON
    metadata_payload = {
        "profiles_dir": "charger_profile_variants",
        "variants": variant_metadata,
    }
    metadata_path = out_dir / "charger_profile_variants.json"
    try:
        metadata_path.write_text(
            json.dumps(metadata_payload, indent=2), encoding="utf-8"
        )
    except (IOError, OSError) as e:
        print(f"   [ERROR] No se pudo guardar el archivo de metadatos de perfiles: {e}")

    summary = {
        "esc_min": esc_min.to_dict(),
        "esc_max": esc_max.to_dict(),
        "esc_rec": esc_rec.to_dict(),
        "profile_path": str((out_dir / "perfil_horario_carga.csv").resolve()),
        "scenarios_path": str((out_dir / "selection_pe_fc_completo.csv").resolve()),
        "individual_chargers_path": str((out_dir / "individual_chargers.json").resolve()),
        "chargers_citylearn_path": str((out_dir / "chargers_citylearn.csv").resolve()),
        "hourly_profiles_path": str((out_dir / "chargers_hourly_profiles.csv").resolve()),
        "n_chargers_recommended": n_chargers_rec,
        "total_daily_energy_kwh": profile['energy_kwh'].sum(),
        "peak_power_kw": profile['power_kw'].max(),
        "avg_soc_arrival_pct": soc_arrival_pct,
        "avg_soc_missing_pct": soc_missing_pct,
        "avg_missing_energy_kwh": avg_energy_needed_kwh,
        "avg_missing_time_minutes": avg_time_remaining_minutes,
        "full_session_energy_kwh": full_energy_per_session_kwh,
        "avg_missing_frac": avg_missing_frac,
        "capacity_sessions_per_hour": capacity["sessions_per_hour_capacity"],
        "capacity_sessions_per_day": capacity["sessions_per_day_capacity"],
        "demand_sessions_per_day": float(esc_rec["vehicles_day_motos"] + esc_rec["vehicles_day_mototaxis"]),
        "co2_gas_kg_day": co2_metrics["co2_gas_kg_day"],
        "co2_ev_kg_day": co2_metrics["co2_ev_kg_day"],
        "co2_reduction_kg_day": co2_metrics["co2_reduction_kg_day"],
        "co2_reduction_kg_year": co2_metrics["co2_reduction_kg_year"],
        # Demanda total instalada
        "n_motos": n_motos,
        "n_mototaxis": n_mototaxis,
        "charger_power_kw_moto": charger_power_kw_moto,
        "charger_power_kw_mototaxi": charger_power_kw_mototaxi,
        "potencia_instalada_motos_kw": potencia_instalada_motos,
        "potencia_instalada_mototaxis_kw": potencia_instalada_mototaxis,
        "potencia_total_instalada_kw": potencia_total_instalada,
        "charger_profile_variants_path": str(metadata_path.resolve()),
        "charger_profile_variants_dir": str(variant_dir.resolve()),
        "charger_profile_variants": variant_metadata,
    }
    
    try:
        (out_dir / "chargers_results.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
    except (IOError, OSError) as e:
        print(f"   [ERROR] No se pudo guardar el archivo de resultados JSON: {e}")
    
    print("\n" + "="*60)
    print(f"[OK] Resultados guardados en: {out_dir}")
    print("="*60)
    
    return summary
