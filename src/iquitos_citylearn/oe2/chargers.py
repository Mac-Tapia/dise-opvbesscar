"""
Mdulo de dimensionamiento de cargadores EV para motos y mototaxis.

Incluye:
- Cilculo de cantidad de vehculos a cargar (diario, mensual, anual)
- Dimensionamiento de cargadores por escenarios
- Perfil de carga diario con horas pico
- Preparacin de datos para control individual de cargadores en CityLearn
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import math
import json
import shutil
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VehicleFleet:
    """Configuracin de la flota de vehculos."""
    n_motos: int
    n_mototaxis: int
    battery_kwh_moto: float = 2.0  # kWh batera tpica moto elctrica
    battery_kwh_mototaxi: float = 4.0  # kWh batera tpica mototaxi
    daily_km_moto: float = 40.0  # km/da promedio
    daily_km_mototaxi: float = 80.0  # km/da promedio
    efficiency_km_kwh_moto: float = 40.0  # km/kWh
    efficiency_km_kwh_mototaxi: float = 25.0  # km/kWh


@dataclass(frozen=True)
class ChargerSpec:
    """Especificacin de un tipo de cargador."""
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
    fc: float  # Factor de carga (% de batera a cargar)
    chargers_required: int
    sockets_total: int
    energy_day_kwh: float
    peak_sessions_per_hour: float
    session_minutes: float
    utilization: float
    charger_power_kw: float
    sockets_per_charger: int
    # Nuevos campos para vehculos
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
    Calcula la cantidad de vehculos a cargar por perodo.
    
    Args:
        n_motos: Nmero total de motos en la flota
        n_mototaxis: Nmero total de mototaxis en la flota
        pe: Probabilidad de evento de carga (0-1)
        fc: Factor de carga (0-1)
        days_per_month: Das por mes
        days_per_year: Das por ao
    
    Returns:
        Diccionario con vehculos diarios, mensuales y anuales
    """
    # Vehculos que cargan diariamente
    vehicles_day_motos = int(round(n_motos * pe * fc))
    vehicles_day_mototaxis = int(round(n_mototaxis * pe * fc))
    
    # Proyeccin mensual y anual
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
    Calcula el nmero de cargadores requeridos en hora pico.

    Cada socket puede atender 60 / (session_minutes / utilization) sesiones por hora.
    Cada cargador tiene `sockets_per_charger` sockets.
    """
    ts_eff = session_minutes / utilization
    sessions_per_socket_per_hour = 60.0 / ts_eff
    capacity_per_charger_per_hour = sockets_per_charger * sessions_per_socket_per_hour
    return int(math.ceil(sessions_peak_per_hour / max(capacity_per_charger_per_hour, 1e-9)))


def compute_capacity_metrics(
    chargers: int,
    sockets_per_charger: int,
    session_minutes: float,
    opening_hour: int,
    closing_hour: int,
) -> Dict[str, float]:
    """Calcula capacidad de sesiones por hora y por dia dada la infraestructura."""
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
    """Calcula reduccion de CO2 al desplazar km electricos en lugar de gasolina."""
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
    Evala un escenario de dimensionamiento de cargadores Modo 3.
    
    Considera que durante las horas pico (4 horas: 18-22h) llegan
    todos los vehculos de la flota que necesitan cargar.
    
    Args:
        pe_motos: Probabilidad de evento de carga para motos (0-1)
        pe_mototaxis: Probabilidad de evento de carga para mototaxis (0-1)
        fc_motos: Factor de carga motos (% de batera a recargar)
        fc_mototaxis: Factor de carga mototaxis (% de batera a recargar)
        n_motos: Nmero total de motos en la flota
        n_mototaxis: Nmero total de mototaxis en la flota
        peak_hours: Lista de horas pico (ej: [18, 19, 20, 21])
        session_minutes: Duracin de sesin de carga
        utilization: Factor de utilizacin del cargador
        charger_power_kw_moto: Potencia cargador motos (2 kW Modo 3)
        charger_power_kw_mototaxi: Potencia cargador mototaxis (3 kW Modo 3)
        sockets_per_charger: Sockets por cargador
    """
    # Vehculos efectivos que cargan (aplicando PE)
    motos_charging = n_motos * pe_motos
    mototaxis_charging = n_mototaxis * pe_mototaxis
    total_vehicles_charging = motos_charging + mototaxis_charging
    
    # Nmero de horas pico
    n_peak_hours = len(peak_hours)
    
    # Sesiones por hora durante hora punta
    # Los vehculos llegan distribuidos en las 4 horas pico
    sessions_peak_motos = motos_charging / n_peak_hours
    sessions_peak_mototaxis = mototaxis_charging / n_peak_hours
    sessions_peak_per_hour = sessions_peak_motos + sessions_peak_mototaxis
    
    ts_h = session_minutes / 60.0
    
    # Energa por sesin (potencia u tiempo u factor de carga)
    # FC indica qu porcentaje de la batera se recarga
    energy_session_moto_kwh = charger_power_kw_moto * ts_h * fc_motos
    energy_session_mototaxi_kwh = charger_power_kw_mototaxi * ts_h * fc_mototaxis
    
    # Energa diaria total (considera FC en la energa por sesin)
    energy_motos_day = motos_charging * energy_session_moto_kwh
    energy_mototaxis_day = mototaxis_charging * energy_session_mototaxi_kwh
    energy_day = energy_motos_day + energy_mototaxis_day
    
    # Potencia promedio ponderada para cilculo de cargadores
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
    
    # Calcular vehculos (usando PE promedio y FC promedio para compatibilidad)
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

    La estrategia de seleccin es la siguiente:
    1. Filtra los escenarios para quedarse con aquellos cuyo nmero de cargadores
       requeridos esti en o por encima del percentil 75.
    2. De entre esos escenarios, selecciona el que tiene la mixima energa diaria.

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

    Distribuye la energa diaria entre horas pico y horas normales.
    """
    hours = list(range(24))
    operating_hours = [h for h in hours if opening_hour <= h <= closing_hour]
    hours_peak = [h for h in peak_hours if h in operating_hours]
    hours_day = len(operating_hours)
    hours_peak_n = len(hours_peak)
    hours_off = max(hours_day - hours_peak_n, 1)

    share_peak = peak_share_day
    share_off = 1.0 - share_peak

    factors = []
    is_peak = []
    for h in hours:
        if h in hours_peak:
            factors.append(share_peak / hours_peak_n)
            is_peak.append(True)
        elif h in operating_hours:
            factors.append(share_off / hours_off)
            is_peak.append(False)
        else:
            factors.append(0.0)
            is_peak.append(False)

    factors = np.array(factors, dtype=float)
    if factors.sum() > 0:
        factors = factors / factors.sum()

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
) -> List[IndividualCharger]:
    """
    Crea una lista de cargadores individuales para simulacin en CityLearn.

    Distribuye la carga total diaria (definida en `daily_profile`) de manera
    equitativa entre el nmero de cargadores especificado. Para simular un
    uso mis realista, introduce una pequea variacin aleatoria (+/- 10%) en
    el perfil de carga de cada cargador, normalizando luego para que la
    energa diaria total se conserve.

    Args:
        n_chargers: Nmero de cargadores individuales a crear.
        charger_power_kw: Potencia nominal de cada cargador en kW.
        sockets_per_charger: Nmero de tomas por cargador.
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
        # Pequea variacin en el perfil (+/- 10%)
        rng = np.random.default_rng(42 + i)
        variation = 1.0 + rng.uniform(-0.1, 0.1, 24)
        individual_profile = [p * v for p, v in zip(base_profile, variation)]
        
        # Normalizar para mantener energa total
        profile_sum = sum(individual_profile)
        if profile_sum > 0:
            individual_profile = [p * energy_per_charger / profile_sum for p in individual_profile]
        
        charger = IndividualCharger(
            charger_id=f"EV_CHARGER_{i+1:03d}",
            charger_type=charger_type,
            power_kw=charger_power_kw,
            sockets=sockets_per_charger,
            location_x=(i % 10) * 5.0,  # Distribucin en grid
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
    Genera y guarda un conjunto de grificas para el anilisis de dimensionamiento.

    Crea las siguientes visualizaciones:
    1.  **Vehculos a Cargar por Perodo:** Grifico de barras que muestra la
        cantidad de motos y mototaxis a cargar diaria, mensual y anualmente
        para el escenario recomendado.
    2.  **Perfil de Carga Diario:** Grifico de lnea que muestra la distribucin
        horaria de la demanda de energa, destacando las horas pico.
    3.  **Anilisis de Escenarios:** Un mapa de calor que relaciona PE y FC con
        el nmero de cargadores, y un histograma de la distribucin de
        cargadores requeridos.
    4.  **Resumen del Sistema:** Un dashboard con la energa diaria, la
        relacin entre sesiones pico y cargadores, una tabla resumen y el
        perfil de potencia horario.

    Args:
        df_scenarios: DataFrame con todos los escenarios de sensibilidad evaluados.
        esc_rec: Serie de pandas que representa el escenario recomendado.
        profile: DataFrame con el perfil de carga horario del escenario recomendado.
        out_dir: Directorio base para guardar las grificas (usado si `reports_dir`
                 es None).
        reports_dir: Directorio de reportes de alto nivel donde se guardarin las
                     grificas, dentro de una subcarpeta `oe2/chargers`.
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
            print(f"  [ERROR] No se pudo guardar la grifica {filename}: {e}")
    
    # ===========================================================
    # Grifica 1: Cantidad de Vehculos a Cargar por Perodo
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
        ax.set_ylabel('Cantidad de Vehculos', fontsize=10)
        ax.set_ylim(0, max(heights) * 1.15 if max(heights) > 0 else 100)
    
    plt.suptitle('Cantidad de Vehculos a Cargar por Perodo (Escenario Recomendado)', 
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    save_plot('chargers_vehiculos_por_periodo.png')
    plt.close()
    print("  [OK] Grafica: Vehiculos a Cargar por Periodo")
    
    # ===========================================================
    # Grifica 2: Perfil de Carga Diario con Horas Pico
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
    
    # Lnea de energa/potencia
    ax.plot(hours, power, 'o-', color='steelblue', linewidth=2, markersize=6, label='Energa / Potencia')
    
    ax.set_xlabel('Hora', fontsize=11)
    ax.set_ylabel('Energa (kWh) / Potencia (kW)', fontsize=11)
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
    # Grifica 3: Comparacin de Escenarios (PE x FC)
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
    
    # Distribucin de cargadores
    ax2 = axes[1]
    ax2.hist(df_scenarios['chargers_required'], bins=20, color='steelblue', 
             edgecolor='white', alpha=0.7)
    ax2.axvline(x=esc_rec['chargers_required'], color='red', linestyle='--', 
                linewidth=2, label=f'Recomendado: {int(esc_rec["chargers_required"])}')
    ax2.set_xlabel('Nmero de Cargadores', fontsize=10)
    ax2.set_ylabel('Frecuencia', fontsize=10)
    ax2.set_title('Distribucin de Cargadores por Escenario', fontsize=11, fontweight='bold')
    ax2.legend()
    
    plt.suptitle('Anilisis de Escenarios de Dimensionamiento', fontsize=13, fontweight='bold')
    plt.tight_layout()
    save_plot('chargers_analisis_escenarios.png')
    plt.close()
    print("  [OK] Grafica: Analisis de Escenarios")
    
    # ===========================================================
    # Grifica 4: Resumen del Sistema de Carga
    # ===========================================================
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Panel 1: Energa diaria por escenario
    ax1 = axes[0, 0]
    ax1.scatter(df_scenarios['pe'] * df_scenarios['fc'], df_scenarios['energy_day_kwh'],
                alpha=0.5, c='steelblue', s=50)
    ax1.axhline(y=esc_rec['energy_day_kwh'], color='red', linestyle='--', 
                label=f'Recomendado: {esc_rec["energy_day_kwh"]:.0f} kWh')
    ax1.set_xlabel('PE u FC', fontsize=10)
    ax1.set_ylabel('Energa Diaria (kWh)', fontsize=10)
    ax1.set_title('Energa Diaria vs Factor Combinado', fontsize=11, fontweight='bold')
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
        ['Parimetro', 'Mnimo', 'Recomendado', 'Miximo'],
        ['Cargadores', f'{df_scenarios["chargers_required"].min():.0f}', 
         f'{esc_rec["chargers_required"]:.0f}', f'{df_scenarios["chargers_required"].max():.0f}'],
        ['Sockets', f'{df_scenarios["sockets_total"].min():.0f}',
         f'{esc_rec["sockets_total"]:.0f}', f'{df_scenarios["sockets_total"].max():.0f}'],
        ['Energa/da (kWh)', f'{df_scenarios["energy_day_kwh"].min():.0f}',
         f'{esc_rec["energy_day_kwh"]:.0f}', f'{df_scenarios["energy_day_kwh"].max():.0f}'],
        ['Motos/da', f'{df_scenarios["vehicles_day_motos"].min():.0f}',
         f'{esc_rec["vehicles_day_motos"]:.0f}', f'{df_scenarios["vehicles_day_motos"].max():.0f}'],
        ['Mototaxis/da', f'{df_scenarios["vehicles_day_mototaxis"].min():.0f}',
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
    
    ax4.set_xlabel('Hora del Da', fontsize=10)
    ax4.set_ylabel('Potencia (kW)', fontsize=10)
    ax4.set_title('Perfil de Potencia Horario', fontsize=11, fontweight='bold')
    ax4.set_xticks(range(0, 24, 2))
    
    # Estadsticas
    total_energy = profile['energy_kwh'].sum()
    peak_power = profile['power_kw'].max()
    ax4.annotate(f'Energa total: {total_energy:.0f} kWh\nPotencia pico: {peak_power:.0f} kW',
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

    Esta funcin ejecuta los siguientes pasos:
    1.  Calcula la demanda de la flota de vehculos elctricos (motos y mototaxis).
    2.  Evala un escenario de dimensionamiento principal basado en los parimetros
        de entrada (PE, FC, etc.) para establecer una recomendacin.
    3.  Realiza un anilisis de sensibilidad generando mltiples escenarios aleatorios
        de PE (Probabilidad de Evento) y FC (Factor de Carga).
    4.  Determina los escenarios de mnimo y miximo requerimiento de cargadores.
    5.  Construye y exporta el perfil de carga horario para el escenario recomendado.
    6.  Prepara y guarda los datos de cargadores individuales para su uso en
        simulaciones con CityLearn.
    7.  Genera un conjunto de grificas y reportes visuales si se solicita.
    8.  Guarda todos los resultados, incluyendo dataframes y metadatos, en el
        directorio de salida.

    Args:
        out_dir: Directorio para guardar todos los artefactos generados.
        seed: Semilla para la generacin de nmeros aleatorios, asegurando
              reproducibilidad.
        n_motos: Nmero total de motos en la flota.
        n_mototaxis: Nmero total de mototaxis en la flota.
        pe_motos: Probabilidad de que una moto necesite cargar en un da (0-1).
        pe_mototaxis: Probabilidad de que un mototaxi necesite cargar (0-1).
        fc_motos: Factor de carga promedio para motos (% de batera a recargar).
        fc_mototaxis: Factor de carga promedio para mototaxis.
        peak_share_day: Porcentaje de la energa diaria que se consume en horas pico.
        session_minutes: Duracin estimada de una sesin de carga en minutos.
        utilization: Factor de utilizacin de los cargadores (0-1).
        charger_power_kw_moto: Potencia del cargador para motos (kW).
        charger_power_kw_mototaxi: Potencia del cargador para mototaxis (kW).
        sockets_per_charger: Nmero de tomas por cada cargador.
        opening_hour: Hora de apertura del centro de carga.
        closing_hour: Hora de cierre del centro de carga.
        km_per_kwh: Eficiencia elxctrica (km recorridos por kWh).
        km_per_gallon: Eficiencia de referencia de gasolina (km por galxn).
        kgco2_per_gallon: Emisiones de CO2 por galxn de gasolina.
        grid_carbon_kg_per_kwh: Factor de emisixn de la red (kgCO2/kWh).
        peak_hours: Lista de horas consideradas como pico.
        n_scenarios: Nmero de escenarios a generar para el anilisis de sensibilidad.
        generate_plots: Si es `True`, genera y guarda las grificas de anilisis.
        reports_dir: Directorio opcional para guardar las grificas en una estructura
                     de reportes.

    Returns:
        Un diccionario que resume los resultados clave del dimensionamiento,
        incluyendo el nmero de cargadores recomendados, la energa diaria,
        potencia pico y rutas a los archivos generados.
    """
    if out_dir.exists():
        shutil.rmtree(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Calcular potencia total instalada
    potencia_instalada_motos = n_motos * charger_power_kw_moto
    potencia_instalada_mototaxis = n_mototaxis * charger_power_kw_mototaxi
    potencia_total_instalada = potencia_instalada_motos + potencia_instalada_mototaxis
    
    # Vehculos efectivos que cargan
    motos_efectivas = n_motos * pe_motos
    mototaxis_efectivas = n_mototaxis * pe_mototaxis
    
    print("\n" + "="*60)
    print("  DIMENSIONAMIENTO DE CARGADORES EV - MODO 3 (IEC 61851)")
    print("="*60)
    print(f"\n[+] Flota de vehiculos:")
    print(f"   Motos: {n_motos:,} (PE={pe_motos:.0%}, FC={fc_motos:.0%})")
    print(f"   Mototaxis: {n_mototaxis:,} (PE={pe_mototaxis:.0%}, FC={fc_mototaxis:.0%})")
    print(f"   Motos efectivas/da: {motos_efectivas:,.0f}")
    print(f"   Mototaxis efectivas/da: {mototaxis_efectivas:,.0f}")
    print(f"\n[+] Configuracion de carga Modo 3:")
    print(f"   Potencia cargador motos: {charger_power_kw_moto} kW")
    print(f"   Potencia cargador mototaxis: {charger_power_kw_mototaxi} kW")
    print(f"   Sockets por cargador: {sockets_per_charger}")
    print(f"   Duracin sesin: {session_minutes} min")
    print(f"   Horario mall: {opening_hour}:00 - {closing_hour}:00")
    print(f"   Horas pico: {peak_hours} ({len(peak_hours)} horas)")
    print(f"\n[+] Demanda Total Instalada:")
    print(f"   Motos:     {n_motos:,} u {charger_power_kw_moto} kW = {potencia_instalada_motos:,.0f} kW")
    print(f"   Mototaxis: {n_mototaxis:,} u {charger_power_kw_mototaxi} kW = {potencia_instalada_mototaxis:,.0f} kW")
    print(f"   TOTAL:     {potencia_total_instalada:,.0f} kW")

    # Evaluar escenario con los parimetros dados
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
    
    # Tambin generar escenarios adicionales para anilisis de sensibilidad
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

    # Seleccionar escenarios min/max para comparacin
    esc_min = df.sort_values("chargers_required", ascending=True).iloc[0]
    esc_max = df.sort_values("chargers_required", ascending=False).iloc[0]
    
    print(f"\n[+] Resultado del dimensionamiento:")
    print(f"   RECOMENDADO: {int(esc_rec['chargers_required'])} cargadores")
    print(f"   Sesiones/hora pico: {esc_rec['peak_sessions_per_hour']:.0f}")
    print(f"   Energa diaria: {esc_rec['energy_day_kwh']:.0f} kWh")
    print(f"\n   Anilisis de sensibilidad:")
    print(f"   Mnimo:      {int(esc_min['chargers_required'])} cargadores (PE={esc_min['pe']:.2f}, FC={esc_min['fc']:.2f})")
    print(f"   Miximo:      {int(esc_max['chargers_required'])} cargadores (PE={esc_max['pe']:.2f}, FC={esc_max['fc']:.2f})")

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
    

    # Estadisticas de vehiculos y capacidad
    print("\n[+] Vehiculos a cargar (Escenario Recomendado):")
    print(f"   Diario:  {int(esc_rec['vehicles_day_motos']):,} motos + {int(esc_rec['vehicles_day_mototaxis']):,} mototaxis")
    print(f"   Mensual: {int(esc_rec['vehicles_month_motos']):,} motos + {int(esc_rec['vehicles_month_mototaxis']):,} mototaxis")
    print(f"   Anual:   {int(esc_rec['vehicles_year_motos']):,} motos + {int(esc_rec['vehicles_year_mototaxis']):,} mototaxis")

    capacity = compute_capacity_metrics(
        chargers=int(esc_rec['chargers_required']),
        sockets_per_charger=sockets_per_charger,
        session_minutes=session_minutes,
        opening_hour=opening_hour,
        closing_hour=closing_hour,
    )
    print(f"   Capacidad hora pico: {capacity['sessions_per_hour_capacity']:.0f} sesiones/h")
    print(f"   Capacidad diaria:    {capacity['sessions_per_day_capacity']:.0f} sesiones/dia")

    co2_metrics = compute_co2_reduction(
        energy_day_kwh=float(esc_rec['energy_day_kwh']),
        grid_carbon_kg_per_kwh=float(grid_carbon_kg_per_kwh),
        km_per_kwh=float(km_per_kwh),
        km_per_gallon=float(km_per_gallon),
        kgco2_per_gallon=float(kgco2_per_gallon),
    )
    print(f"   CO2 gasolina (dia): {co2_metrics['co2_gas_kg_day']:.1f} kg")
    print(f"   CO2 electrico (dia): {co2_metrics['co2_ev_kg_day']:.1f} kg")
    print(f"   Reduccion (dia):     {co2_metrics['co2_reduction_kg_day']:.1f} kg")

    # Crear cargadores individuales para CityLearn
    n_chargers_rec = int(round(esc_rec['chargers_required']))
    avg_charger_power = esc_rec['charger_power_kw']  # Potencia promedio ponderada
    individual_chargers = create_individual_chargers(
        n_chargers=n_chargers_rec,
        charger_power_kw=avg_charger_power,
        sockets_per_charger=sockets_per_charger,
        daily_profile=profile,
        charger_type="Level2_EV",
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
    
    # Generar grificas
    if generate_plots:
        print("\n[+] Generando graficas...")
        generate_charger_plots(df, esc_rec, profile, out_dir, reports_dir=reports_dir)

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
