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
    power_kw: float  # Potencia total del cargador (suma de sockets)
    sockets: int
    socket_power_moto_kw: float = 2.0
    socket_power_mototaxi_kw: float = 3.0
    socket_power_avg_kw: float = 0.0
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
            'socket_power_moto_kw': self.socket_power_moto_kw,
            'socket_power_mototaxi_kw': self.socket_power_mototaxi_kw,
            'socket_power_avg_kw': self.socket_power_avg_kw,
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



def evaluate_scenario(
    scenario_id: int,
    pe_motos: float,
    pe_mototaxis: float,
    fc_motos: float,
    fc_mototaxis: float,
    n_motos: int,
    n_mototaxis: int,
    opening_hour: int,
    closing_hour: int,
    peak_hours: List[int],
    session_minutes: float,
    utilization: float,
    charger_power_kw_moto: float,
    charger_power_kw_mototaxi: float,
    sockets_per_charger: int,
) -> ChargerSizingResult:
    """
    Evalua un escenario de dimensionamiento de cargadores Modo 3.

    Los conteos de motos y mototaxis se consideran observados en el bloque
    de horas pico y se escalan al total de horas operativas (apertura-cierre)
    para estimar el flujo diario.

    Args:
        pe_motos: Probabilidad de evento de carga para motos (0-1)
        pe_mototaxis: Probabilidad de evento de carga para mototaxis (0-1)
        fc_motos: Factor de carga motos (% de bateria a recargar)
        fc_mototaxis: Factor de carga mototaxis (% de bateria a recargar)
        n_motos: Conteo de motos observado en bloque pico
        n_mototaxis: Conteo de mototaxis observado en bloque pico
        opening_hour: Hora de apertura del mall
        closing_hour: Hora de cierre del mall
        peak_hours: Lista de horas pico (ej: [18, 19, 20, 21])
        session_minutes: Duracion de sesion de carga
        utilization: Factor de utilizacion del cargador
        charger_power_kw_moto: Potencia cargador motos (2 kW Modo 3)
        charger_power_kw_mototaxi: Potencia cargador mototaxis (3 kW Modo 3)
        sockets_per_charger: Sockets por cargador
    """
    hours_day = max(closing_hour - opening_hour + 1, 1)
    n_peak_hours = max(len(peak_hours), 1)
    scale_to_day = hours_day / n_peak_hours

    # Escalar conteos pico a estimado diario
    motos_day_est = n_motos * scale_to_day
    mototaxis_day_est = n_mototaxis * scale_to_day

    # Vehiculos efectivos que cargan (aplicando PE)
    motos_charging = motos_day_est * pe_motos
    mototaxis_charging = mototaxis_day_est * pe_mototaxis
    total_vehicles_charging = motos_charging + mototaxis_charging

    # Sesiones por hora durante hora punta
    sessions_peak_motos = motos_charging / n_peak_hours
    sessions_peak_mototaxis = mototaxis_charging / n_peak_hours
    sessions_peak_per_hour = sessions_peak_motos + sessions_peak_mototaxis

    ts_h = session_minutes / 60.0

    # Energia por sesion (potencia - tiempo - factor de carga)
    energy_session_moto_kwh = charger_power_kw_moto * ts_h * fc_motos
    energy_session_mototaxi_kwh = charger_power_kw_mototaxi * ts_h * fc_mototaxis

    # Energia diaria total
    energy_motos_day = motos_charging * energy_session_moto_kwh
    energy_mototaxis_day = mototaxis_charging * energy_session_mototaxi_kwh
    energy_day = energy_motos_day + energy_mototaxis_day

    # Potencia promedio ponderada para calculo de cargadores
    if total_vehicles_charging > 0:
        avg_charger_power = (
            motos_charging * charger_power_kw_moto
            + mototaxis_charging * charger_power_kw_mototaxi
        ) / total_vehicles_charging
    else:
        avg_charger_power = (charger_power_kw_moto + charger_power_kw_mototaxi) / 2

    chargers = chargers_needed(
        sessions_peak_per_hour=sessions_peak_per_hour,
        session_minutes=session_minutes,
        utilization=utilization,
        sockets_per_charger=sockets_per_charger,
    )

    # Calcular vehiculos diarios equivalentes
    pe_avg = (pe_motos * motos_day_est + pe_mototaxis * mototaxis_day_est) / max(
        motos_day_est + mototaxis_day_est, 1e-9
    )
    fc_avg = (fc_motos * motos_day_est + fc_mototaxis * mototaxis_day_est) / max(
        motos_day_est + mototaxis_day_est, 1e-9
    )
    vehicle_demand = calculate_vehicle_demand(
        int(round(motos_day_est)),
        int(round(mototaxis_day_est)),
        pe_avg,
        fc_avg,
    )

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
    df_p75 = pd.DataFrame(df[df["chargers_required"] >= p75])
    df_sorted = df_p75.sort_values(by="energy_day_kwh", ascending=False)
    return df_sorted.iloc[0]



def build_hourly_profile(
    energy_day_kwh: float,
    opening_hour: int,
    closing_hour: int,
    peak_hours: List[int],
    peak_share_day: float,
) -> pd.DataFrame:
    """
    Construye perfil de carga horario de 24h.

    Distribuye la energia diaria entre horas pico y horas normales con un
    realce determinista (no aleatorio) en las horas pico para reflejar mayor
    ingreso en el bloque de hora punta.
    """
    hours = list(range(24))
    operating_hours = [h for h in hours if opening_hour <= h <= closing_hour]
    hours_peak = [h for h in peak_hours if h in operating_hours]
    hours_peak_n = len(hours_peak)

    share_peak = float(np.clip(peak_share_day, 0.0, 1.0))
    share_off = 1.0 - share_peak

    factors = np.zeros(24, dtype=float)
    is_peak = [False] * 24

    # Pico: rampa suavizada para mostrar mayor demanda hacia el centro del bloque
    if hours_peak_n > 0:
        if hours_peak_n == 1:
            peak_weights = np.array([1.0])
        else:
            mid = (hours_peak_n - 1) / 2.0
            peak_weights = np.array([
                1.0 + 0.5 * (1.0 - abs(i - mid) / max(mid, 1.0))
                for i in range(hours_peak_n)
            ])
        peak_weights = peak_weights / peak_weights.sum()
        peak_allocation = peak_weights * share_peak
        for i, h in enumerate(hours_peak):
            factors[h] = peak_allocation[i]
            is_peak[h] = True

    # Horas fuera de pico dentro del horario de atencion: reparto uniforme
    hours_off_list = [h for h in operating_hours if h not in hours_peak]
    if hours_off_list:
        off_value = share_off / len(hours_off_list)
        for h in hours_off_list:
            factors[h] = off_value

    # Normalizacion numerica
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
    socket_power_moto_kw: float = 2.0,
    socket_power_mototaxi_kw: float = 3.0,
    randomize: bool = True,
    seed: Optional[int] = None,
    variation_pct: float = 0.1,
) -> List[IndividualCharger]:
    """
    Crea una lista de cargadores individuales para simulacion en CityLearn.

    Distribuye la carga total diaria (definida en `daily_profile`) de manera
    equitativa entre el numero de cargadores especificado. Si `randomize` es
    True, aplica una variacion estocastica controlada (+/- variation_pct) a
    cada perfil horario y luego normaliza para conservar la energia diaria.
    """
    # Aceptar valores flotantes y garantizar al menos 1 cargador
    n_chargers_int = max(1, int(round(n_chargers)))
    rng = np.random.default_rng(seed) if randomize else None

    chargers = []
    total_daily_energy = float(daily_profile['energy_kwh'].sum())
    energy_per_charger = total_daily_energy / n_chargers_int if n_chargers_int > 0 else 0.0
    
    base_profile = daily_profile['power_kw'].to_numpy()
    moto_sockets = sockets_per_charger // 2
    mototaxi_sockets = sockets_per_charger - moto_sockets
    unit_power_kw = moto_sockets * socket_power_moto_kw + mototaxi_sockets * socket_power_mototaxi_kw
    socket_power_avg_kw = unit_power_kw / sockets_per_charger if sockets_per_charger > 0 else charger_power_kw
    
    for i in range(n_chargers_int):
        individual_profile = base_profile.copy()

        if rng is not None and variation_pct > 0:
            noise = rng.uniform(1 - variation_pct, 1 + variation_pct, size=individual_profile.shape)
            individual_profile = individual_profile * noise

        profile_sum = float(individual_profile.sum())
        if profile_sum > 0:
            individual_profile = (individual_profile * energy_per_charger / profile_sum).tolist()
        else:
            individual_profile = individual_profile.tolist()
        
        charger = IndividualCharger(
            charger_id=f"EV_CHARGER_{i+1:03d}",
            charger_type=charger_type,
            power_kw=unit_power_kw,
            sockets=sockets_per_charger,
            socket_power_moto_kw=socket_power_moto_kw,
            socket_power_mototaxi_kw=socket_power_mototaxi_kw,
            socket_power_avg_kw=socket_power_avg_kw,
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
    _fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    
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
    _fig, ax = plt.subplots(figsize=(12, 6))
    
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
    
    # Línea de energía/potencia
    ax.plot(hours, power, 'o-', color='steelblue', linewidth=2, markersize=6, label='Energía / Potencia')
    
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
    _fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
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
    _fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
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
    peak_hours: List[int],
    n_scenarios: int = 100,
    generate_plots: bool = True,
    reports_dir: Optional[Path] = None,
    randomize_chargers: bool = True,
    charger_variation_pct: float = 0.1,
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

    hours_day = max(closing_hour - opening_hour + 1, 1)
    peak_hours_count = max(len(peak_hours), 1)
    scale_to_day = hours_day / peak_hours_count
    n_motos_day = n_motos * scale_to_day
    n_mototaxis_day = n_mototaxis * scale_to_day
    moto_sockets = sockets_per_charger // 2
    mototaxi_sockets = sockets_per_charger - moto_sockets
    charger_unit_power_kw = moto_sockets * charger_power_kw_moto + mototaxi_sockets * charger_power_kw_mototaxi
    socket_power_avg_kw = charger_unit_power_kw / sockets_per_charger if sockets_per_charger > 0 else 0.0

    # Calcular potencia total instalada sobre el flujo diario estimado
    potencia_instalada_motos = n_motos_day * charger_power_kw_moto
    potencia_instalada_mototaxis = n_mototaxis_day * charger_power_kw_mototaxi
    potencia_total_instalada = potencia_instalada_motos + potencia_instalada_mototaxis

    # Vehiculos efectivos que cargan
    motos_efectivas = n_motos_day * pe_motos
    mototaxis_efectivas = n_mototaxis_day * pe_mototaxis

    print("\n" + "="*60)
    print("  DIMENSIONAMIENTO DE CARGADORES EV - MODO 3 (IEC 61851)")
    print("="*60)
    print(f"\n[+] Flota de vehiculos:")
    print(f"   Observado en bloque pico: {n_motos:,} motos, {n_mototaxis:,} mototaxis")
    print(f"   Estimado en dia completo ({hours_day} h): {n_motos_day:,.0f} motos, {n_mototaxis_day:,.0f} mototaxis")
    print(f"   PE/FC: Motos PE={pe_motos:.0%}, FC={fc_motos:.0%} | Mototaxis PE={pe_mototaxis:.0%}, FC={fc_mototaxis:.0%}")
    print(f"   Motos efectivas/dia: {motos_efectivas:,.0f}")
    print(f"   Mototaxis efectivas/dia: {mototaxis_efectivas:,.0f}")
    print(f"\n[+] Configuracion de carga Modo 3:")
    print(f"   Potencia cargador motos: {charger_power_kw_moto} kW")
    print(f"   Potencia cargador mototaxis: {charger_power_kw_mototaxi} kW")
    print(f"   Sockets por cargador: {sockets_per_charger}")
    print(f"   Duracion sesion: {session_minutes} min")
    print(f"   Horario mall: {opening_hour}:00 - {closing_hour}:00")
    print(f"   Horas pico: {peak_hours} ({len(peak_hours)} horas)")
    print(f"   Aleatoriedad por cargador: {'ON' if randomize_chargers else 'OFF'} (±{charger_variation_pct*100:.0f}%)")
    print(f"\n[+] Demanda Total Instalada (flujo diario estimado):")
    print(f"   Motos:     {n_motos_day:,.0f} x {charger_power_kw_moto} kW = {potencia_instalada_motos:,.0f} kW")
    print(f"   Mototaxis: {n_mototaxis_day:,.0f} x {charger_power_kw_mototaxi} kW = {potencia_instalada_mototaxis:,.0f} kW")
    print(f"   TOTAL:     {potencia_total_instalada:,.0f} kW")

    # Evaluar escenario con los parametros dados
    print("\n[+] Evaluando escenario con PE y FC configurados...")

    
    res = evaluate_scenario(
        scenario_id=1,
        pe_motos=pe_motos,
        pe_mototaxis=pe_mototaxis,
        fc_motos=fc_motos,
        fc_mototaxis=fc_mototaxis,
        n_motos=n_motos,
        n_mototaxis=n_mototaxis,
        opening_hour=opening_hour,
        closing_hour=closing_hour,
        peak_hours=peak_hours,
        session_minutes=session_minutes,
        utilization=utilization,
        charger_power_kw_moto=charger_power_kw_moto,
        charger_power_kw_mototaxi=charger_power_kw_mototaxi,
        sockets_per_charger=sockets_per_charger,
    )
    
    # Usar el resultado como escenario recomendado
    esc_rec = pd.Series(res.__dict__)
    esc_rec["socket_power_moto_kw"] = charger_power_kw_moto
    esc_rec["socket_power_mototaxi_kw"] = charger_power_kw_mototaxi
    esc_rec["socket_power_avg_kw"] = socket_power_avg_kw
    esc_rec["charger_unit_power_kw"] = charger_unit_power_kw
    esc_rec["sockets_per_charger"] = sockets_per_charger
    
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
            opening_hour=opening_hour,
            closing_hour=closing_hour,
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
    esc_min = df.sort_values(by="chargers_required", ascending=True).iloc[0]
    esc_max = df.sort_values(by="chargers_required", ascending=False).iloc[0]
    
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
    # Ajuste: rampa descendente 21h-22h y cero desde las 22h
    total_energy_original = profile["energy_kwh"].sum()
    if total_energy_original > 0:
        # Reducir la hora 21 al 50% y cortar a cero >=22
        mask_21 = profile["hour"] == 21
        profile.loc[mask_21, ["energy_kwh", "power_kw"]] *= 0.5
        mask_cut = profile["hour"] >= 22
        profile.loc[mask_cut, ["energy_kwh", "power_kw"]] = 0.0

        # Suavizar ligero para evitar escalones (ventana [0.25,0.5,0.25])
        kernel = np.array([0.25, 0.5, 0.25])
        smoothed = np.convolve(profile["energy_kwh"].to_numpy(), kernel, mode="same")
        profile["energy_kwh"] = smoothed
        profile["power_kw"] = smoothed  # paso horario: kWh == kW promedio

        # Reaplicar corte a partir de las 22h
        profile.loc[mask_cut, ["energy_kwh", "power_kw"]] = 0.0

        # Renormalizar para conservar la energía diaria original
        if profile["energy_kwh"].sum() > 0:
            scale = total_energy_original / profile["energy_kwh"].sum()
            profile["energy_kwh"] *= scale
            profile["power_kw"] *= scale

        # Recalcular factor
        if profile["energy_kwh"].sum() > 0:
            profile["factor"] = profile["energy_kwh"] / profile["energy_kwh"].sum()
        else:
            profile["factor"] = 0.0
    try:
        profile.to_csv(out_dir / "perfil_horario_carga.csv", index=False)
    except (IOError, OSError) as e:
        print(f"   [ERROR] No se pudo guardar el perfil de carga horario: {e}")
    
    # Estadísticas de vehículos
    print(f"\n[+] Vehiculos a cargar (Escenario Recomendado):")
    print(f"   Diario:  {int(esc_rec['vehicles_day_motos']):,} motos + {int(esc_rec['vehicles_day_mototaxis']):,} mototaxis")
    print(f"   Mensual: {int(esc_rec['vehicles_month_motos']):,} motos + {int(esc_rec['vehicles_month_mototaxis']):,} mototaxis")
    print(f"   Anual:   {int(esc_rec['vehicles_year_motos']):,} motos + {int(esc_rec['vehicles_year_mototaxis']):,} mototaxis")
    
    # Crear cargadores individuales para CityLearn
    n_chargers_rec = esc_rec['chargers_required']
    avg_charger_power = esc_rec['charger_power_kw']  # Potencia promedio ponderada
    individual_chargers = create_individual_chargers(
        n_chargers=n_chargers_rec,
        charger_power_kw=avg_charger_power,
        sockets_per_charger=sockets_per_charger,
        daily_profile=profile,
        charger_type="Level2_EV",
        socket_power_moto_kw=charger_power_kw_moto,
        socket_power_mototaxi_kw=charger_power_kw_mototaxi,
        randomize=randomize_chargers,
        seed=seed,
        variation_pct=charger_variation_pct,
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
        # Demanda total instalada estimada
        "n_motos_peak": n_motos,
        "n_mototaxis_peak": n_mototaxis,
        "n_motos": int(round(n_motos_day)),
        "n_mototaxis": int(round(n_mototaxis_day)),
        "charger_power_kw_moto": charger_power_kw_moto,
        "charger_power_kw_mototaxi": charger_power_kw_mototaxi,
        "socket_power_moto_kw": charger_power_kw_moto,
        "socket_power_mototaxi_kw": charger_power_kw_mototaxi,
        "socket_power_avg_kw": socket_power_avg_kw,
        "charger_unit_power_kw": charger_unit_power_kw,
        "potencia_instalada_motos_kw": potencia_instalada_motos,
        "potencia_instalada_mototaxis_kw": potencia_instalada_mototaxis,
        "potencia_total_instalada_kw": potencia_total_instalada,
        "charger_profile_variants_path": str(metadata_path.resolve()),
        "charger_profile_variants_dir": str(variant_dir.resolve()),
        "charger_profile_variants": variant_metadata,
        "randomize_chargers": randomize_chargers,
        "charger_variation_pct": charger_variation_pct,
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
