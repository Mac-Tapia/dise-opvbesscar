"""
Generador de Dataset EV - SIMULADOR ESTOCÁSTICO REALISTA v2.0
Considera SOC dinámico, escenarios motos vs mototaxis, factores reales
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VehicleType:
    """Especificación de tipo de vehículo"""
    name: str
    energy_capacity_kwh: float  # Capacidad de batería
    charge_rate_kw: float  # Velocidad de carga nominal
    avg_arrival_count_per_hour: float  # Vehículos que llegan por hora
    soc_arrival_mean: float  # SOC promedio al llegar [0-1]
    soc_arrival_std: float  # Desviación estándar SOC llegada
    target_soc: float  # SOC objetivo antes de partir
    parking_time_hours: float  # Tiempo promedio de permanencia


# Especificaciones de vehículos
MOTO_SPEC = VehicleType(
    name="moto",
    energy_capacity_kwh=10.0,
    charge_rate_kw=2.0,
    avg_arrival_count_per_hour=5.5,  # 30 motos / 20.4h activo ≈ 5.5/h
    soc_arrival_mean=0.35,
    soc_arrival_std=0.15,
    target_soc=0.90,
    parking_time_hours=1.5
)

MOTOTAXI_SPEC = VehicleType(
    name="mototaxi",
    energy_capacity_kwh=15.0,
    charge_rate_kw=3.0,
    avg_arrival_count_per_hour=0.78,  # 16 taxis / 20.4h activo ≈ 0.78/h
    soc_arrival_mean=0.40,
    soc_arrival_std=0.18,
    target_soc=0.95,
    parking_time_hours=2.0
)


def generate_realistic_ev_dataset(output_dir: str | Path = "data/oe2/chargers") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Genera dataset de EV con simulación estocástica realista.
    
    - Horario: 9:00-22:00 con perfil variable según llegadas reales
    - Eventos: Llegada estocástica de vehículos con SOC variado
    - Tipos: Motos (112 sockets) y mototaxis (16 sockets)
    - Dinámico: SOC se actualiza según velocidad real de carga
    
    Args:
        output_dir: Directorio para guardar CSVs
        
    Returns:
        Tupla (df_annual_8760h, df_daily_24h)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    start_date = datetime(2024, 1, 1, 0, 0, 0)
    timestamps_annual = [start_date + timedelta(hours=i) for i in range(8760)]
    
    print("\n" + "="*130)
    print("GENERADOR DE DATASET EV - SIMULACIÓN ESTOCÁSTICA REALISTA v2.0")
    print("="*130)
    print(f"""
    ESPECIFICACIONES DE VEHÍCULOS:
    
    MOTOS (28 cargadores x 2 sockets = 112 sockets):
      - Capacidad: {MOTO_SPEC.energy_capacity_kwh} kWh
      - Velocidad de carga: {MOTO_SPEC.charge_rate_kw} kW
      - SOC llegada: {MOTO_SPEC.soc_arrival_mean:.0%} ± {MOTO_SPEC.soc_arrival_std:.0%}
      - SOC objetivo: {MOTO_SPEC.target_soc:.0%}
      - Arribos esperados/hora: {MOTO_SPEC.avg_arrival_count_per_hour:.1f}
      - Tiempo de parking: {MOTO_SPEC.parking_time_hours:.1f}h
    
    MOTOTAXIS (4 cargadores x 2 sockets = 16 sockets):
      - Capacidad: {MOTOTAXI_SPEC.energy_capacity_kwh} kWh
      - Velocidad de carga: {MOTOTAXI_SPEC.charge_rate_kw} kW
      - SOC llegada: {MOTOTAXI_SPEC.soc_arrival_mean:.0%} ± {MOTOTAXI_SPEC.soc_arrival_std:.0%}
      - SOC objetivo: {MOTOTAXI_SPEC.target_soc:.0%}
      - Arribos esperados/hora: {MOTOTAXI_SPEC.avg_arrival_count_per_hour:.2f}
      - Tiempo de parking: {MOTOTAXI_SPEC.parking_time_hours:.1f}h
    
    HORARIO DE OPERACIÓN:
      - 9:00-10:00: Período inicial (ramp-up)
      - 10:00-18:00: Período pico (carga máxima)
      - 18:00-21:00: Período vespertino (demanda alta)
      - 21:00-22:00: Período final (ramp-down)
      - 22:00-9:00: Cerrado (sin operación)
    
    GENERANDO DATOS...
    """)
    
    # ========== INICIALIZAR ESTRUCTURAS ==========
    data_annual = {
        'timestamp': timestamps_annual,
        'hour': [t.hour for t in timestamps_annual],
        'day_of_year': [t.timetuple().tm_yday for t in timestamps_annual],
    }
    
    # Chargers y sockets
    chargers = {}
    sockets_by_charger = {}
    socket_type = {}  # socket_id -> 'moto' | 'mototaxi'
    
    # 28 cargadores de motos (sockets 0-111)
    for charger_id in range(28):
        chargers[charger_id] = {'type': 'moto', 'num_sockets': 4}
        sockets_by_charger[charger_id] = list(range(charger_id * 4, charger_id * 4 + 4))
        for socket_id in sockets_by_charger[charger_id]:
            socket_type[socket_id] = 'moto'
    
    # 4 cargadores de mototaxis (sockets 112-127)
    for charger_id in range(28, 32):
        chargers[charger_id] = {'type': 'mototaxi', 'num_sockets': 4}
        sockets_by_charger[charger_id] = list(range(112 + ((charger_id - 28) * 4), 112 + ((charger_id - 28) * 4) + 4))
        for socket_id in sockets_by_charger[charger_id]:
            socket_type[socket_id] = 'mototaxi'
    
    # Inicializar columnas
    for charger_id in range(32):
        data_annual[f'charger_{charger_id:02d}_power_kw'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_energy_kwh'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_active_sockets'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_soc_avg'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_fully_charged'] = np.zeros(8760)
    
    for socket_id in range(38):
        data_annual[f'socket_{socket_id:03d}_soc_current'] = np.zeros(8760)
        data_annual[f'socket_{socket_id:03d}_active'] = np.zeros(8760)
        data_annual[f'socket_{socket_id:03d}_power_kw'] = np.zeros(8760)
        data_annual[f'socket_{socket_id:03d}_vehicles_waiting'] = np.zeros(8760)
        data_annual[f'socket_{socket_id:03d}_vehicles_charging'] = np.zeros(8760)
    
    # ========== SIMULACIÓN ESTOCÁSTICA ==========
    np.random.seed(42)
    
    # Estado de cada socket: (soc_current, time_charging_started, vehicle_in_socket)
    socket_state = {}
    for socket_id in range(38):
        socket_state[socket_id] = {
            'soc': np.random.uniform(0.3, 0.8),  # SOC inicial
            'time_charging': 0,  # Horas cargando
            'vehicle_type': socket_type[socket_id],
            'in_use': False,
            'charging': False
        }
    
    def get_operational_factor(hour_of_day: int) -> float:
        """Factor de demanda esperado según hora del día.
        
        Modela ramp-up/down pero NO es determinístico - es input para
        estimar llegadas de vehículos.
        """
        if 9 <= hour_of_day < 10:
            return 0.30  # Inicio: 30% de vehículos esperados
        elif 10 <= hour_of_day < 18:
            # Sube de 30% a 100% (período pico)
            return 0.30 + (hour_of_day - 10) * (0.70 / 8)
        elif 18 <= hour_of_day < 21:
            return 1.00  # Máximo
        elif 21 <= hour_of_day < 22:
            # Baja a 20%
            return 1.00 - (hour_of_day - 21) * 0.80
        else:
            return 0.0
    
    # Simulación hora por hora
    for hour_idx in range(8760):
        timestamp = timestamps_annual[hour_idx]
        hour_of_day = timestamp.hour
        
        operational_factor = get_operational_factor(hour_of_day)
        
        if operational_factor > 0.0:
            # PERÍODO OPERATIVO: Generar llegadas y carga
            
            # Motos: Generar nuevas llegadas
            motos_arriving = np.random.poisson(
                MOTO_SPEC.avg_arrival_count_per_hour * operational_factor
            )
            
            # Mototaxis: Generar nuevas llegadas
            taxis_arriving = np.random.poisson(
                MOTOTAXI_SPEC.avg_arrival_count_per_hour * operational_factor
            )
            
            # Asignar motos a sockets disponibles (0-111)
            moto_sockets = list(range(30))
            np.random.shuffle(moto_sockets)
            
            for i, socket_id in enumerate(moto_sockets[:motos_arriving]):
                if not socket_state[socket_id]['in_use']:
                    # Nuevo vehículo llega
                    socket_state[socket_id]['soc'] = np.clip(
                        np.random.normal(
                            MOTO_SPEC.soc_arrival_mean,
                            MOTO_SPEC.soc_arrival_std
                        ), 0.05, 0.95
                    )
                    socket_state[socket_id]['in_use'] = True
                    socket_state[socket_id]['charging'] = True
                    socket_state[socket_id]['time_charging'] = 0
            
            # Asignar taxis a sockets disponibles (112-127)
            taxi_sockets = list(range(112, 128))
            np.random.shuffle(taxi_sockets)
            
            for i, socket_id in enumerate(taxi_sockets[:taxis_arriving]):
                if not socket_state[socket_id]['in_use']:
                    # Nuevo taxi llega
                    socket_state[socket_id]['soc'] = np.clip(
                        np.random.normal(
                            MOTOTAXI_SPEC.soc_arrival_mean,
                            MOTOTAXI_SPEC.soc_arrival_std
                        ), 0.05, 0.95
                    )
                    socket_state[socket_id]['in_use'] = True
                    socket_state[socket_id]['charging'] = True
                    socket_state[socket_id]['time_charging'] = 0
            
            # Actualizar carga de vehículos activos
            for socket_id in range(38):
                if socket_state[socket_id]['charging']:
                    spec = MOTO_SPEC if socket_state[socket_id]['vehicle_type'] == 'moto' else MOTOTAXI_SPEC
                    
                    # Calcular ganancia de energía (1 hora de carga)
                    energy_gained_kwh = spec.charge_rate_kw * 1.0  # 1 hora
                    energy_gained_percent = energy_gained_kwh / spec.energy_capacity_kwh
                    
                    socket_state[socket_id]['soc'] = min(
                        spec.target_soc,
                        socket_state[socket_id]['soc'] + energy_gained_percent
                    )
                    socket_state[socket_id]['time_charging'] += 1
                    
                    # Verificar si alcanzó objetivo o tiempo máximo
                    if (socket_state[socket_id]['soc'] >= spec.target_soc or
                        socket_state[socket_id]['time_charging'] > spec.parking_time_hours + 0.5):
                        socket_state[socket_id]['charging'] = False
                        socket_state[socket_id]['in_use'] = False
            
            # Registrar potencia actual de cada socket
            for socket_id in range(38):
                if socket_state[socket_id]['charging']:
                    spec = MOTO_SPEC if socket_state[socket_id]['vehicle_type'] == 'moto' else MOTOTAXI_SPEC
                    data_annual[f'socket_{socket_id:03d}_power_kw'][hour_idx] = spec.charge_rate_kw
                    data_annual[f'socket_{socket_id:03d}_active'][hour_idx] = 1
                    data_annual[f'socket_{socket_id:03d}_vehicles_charging'][hour_idx] = 1
                else:
                    data_annual[f'socket_{socket_id:03d}_power_kw'][hour_idx] = 0.01  # Standby
                    data_annual[f'socket_{socket_id:03d}_active'][hour_idx] = 0 if not socket_state[socket_id]['in_use'] else 0.5
                    data_annual[f'socket_{socket_id:03d}_vehicles_charging'][hour_idx] = 0
                
                data_annual[f'socket_{socket_id:03d}_soc_current'][hour_idx] = socket_state[socket_id]['soc']
                
                # Vehículos esperando (si hay socket disponible)
                if not socket_state[socket_id]['in_use']:
                    # Probabilidad residual de vehículos en fila
                    data_annual[f'socket_{socket_id:03d}_vehicles_waiting'][hour_idx] = np.random.poisson(0.1)
                else:
                    data_annual[f'socket_{socket_id:03d}_vehicles_waiting'][hour_idx] = 0
        
        else:
            # PERÍODO CERRADO: Sin operaciones
            for socket_id in range(38):
                socket_state[socket_id]['in_use'] = False
                socket_state[socket_id]['charging'] = False
                socket_state[socket_id]['soc'] = max(0.0, socket_state[socket_id]['soc'] - 0.005)  # Autodescarga
                
                data_annual[f'socket_{socket_id:03d}_power_kw'][hour_idx] = 0.01
                data_annual[f'socket_{socket_id:03d}_active'][hour_idx] = 0
                data_annual[f'socket_{socket_id:03d}_vehicles_charging'][hour_idx] = 0
                data_annual[f'socket_{socket_id:03d}_vehicles_waiting'][hour_idx] = 0
                data_annual[f'socket_{socket_id:03d}_soc_current'][hour_idx] = socket_state[socket_id]['soc']
        
        # Agregar al nivel de cargador
        for charger_id in range(32):
            socket_ids = sockets_by_charger[charger_id]
            
            charger_power_kw = sum([data_annual[f'socket_{sid:03d}_power_kw'][hour_idx] for sid in socket_ids])
            charger_energy_kwh = charger_power_kw  # kWh = kW × 1h
            charger_active_sockets = sum([int(data_annual[f'socket_{sid:03d}_vehicles_charging'][hour_idx']) for sid in socket_ids])
            charger_soc_avg = np.mean([socket_state[sid]['soc'] for sid in socket_ids])
            charger_fully_charged = sum([1 for sid in socket_ids if socket_state[sid]['soc'] >= 0.95])
            
            data_annual[f'charger_{charger_id:02d}_power_kw'][hour_idx] = charger_power_kw
            data_annual[f'charger_{charger_id:02d}_energy_kwh'][hour_idx] = charger_energy_kwh
            data_annual[f'charger_{charger_id:02d}_active_sockets'][hour_idx] = charger_active_sockets
            data_annual[f'charger_{charger_id:02d}_soc_avg'][hour_idx] = charger_soc_avg
            data_annual[f'charger_{charger_id:02d}_fully_charged'][hour_idx] = charger_fully_charged
    
    # ========== CREAR DATAFRAMES ==========
    df_annual = pd.DataFrame(data_annual)
    
    cols_base = ['timestamp', 'hour', 'day_of_year']
    cols_chargers = sorted([col for col in df_annual.columns if col.startswith('charger_')])
    cols_sockets = sorted([col for col in df_annual.columns if col.startswith('socket_')])
    
    df_annual = df_annual[cols_base + cols_chargers + cols_sockets]
    
    path_annual = output_dir / 'chargers_ev_ano_2024_v2.csv'
    df_annual.to_csv(path_annual, index=False)
    
    print(f"✅ Dataset anual generado: {path_annual}")
    print(f"   Filas: {len(df_annual)} (8,760 horas)")
    print(f"   Columnas: {len(df_annual.columns)}")
    
    # ========== GENERAR DATOS DE UN DÍA ==========
    timestamps_daily = [start_date + timedelta(hours=i) for i in range(24)]
    
    data_daily = {
        'timestamp': timestamps_daily,
        'hour': [t.hour for t in timestamps_daily],
        'day_of_year': [t.timetuple().tm_yday for t in timestamps_daily],
    }
    
    for col in cols_chargers + cols_sockets:
        data_daily[col] = df_annual[col].iloc[:24].values
    
    df_daily = pd.DataFrame(data_daily)
    df_daily = df_daily[cols_base + cols_chargers + cols_sockets]
    
    path_daily = output_dir / 'chargers_ev_dia_2024_v2.csv'
    df_daily.to_csv(path_daily, index=False)
    
    print(f"\n✅ Dataset diario generado: {path_daily}")
    print(f"   Filas: {len(df_daily)} (24 horas - Día 1)")
    print(f"   Columnas: {len(df_daily.columns)}")
    
    # ========== VALIDACIÓN ==========
    print(f"\n📊 VALIDACIÓN DE DEMANDA:")
    
    socket_power_cols = [col for col in df_annual.columns if col.startswith('socket_') and col.endswith('_power_kw')]
    total_energy_annual_sockets = df_annual[socket_power_cols].sum().sum()
    
    charger_energy_cols = [col for col in df_annual.columns if col.startswith('charger_') and col.endswith('_energy_kwh')]
    total_energy_annual_chargers = df_annual[charger_energy_cols].sum().sum()
    
    print(f"   Energía total anual (socket-level): {total_energy_annual_sockets:,.0f} kWh")
    print(f"   Energía total anual (charger-level): {total_energy_annual_chargers:,.0f} kWh")
    print(f"   Energía diaria promedio: {total_energy_annual_sockets / 365:,.0f} kWh/día")
    
    # Calcular ocupación
    active_sockets = df_annual[[col for col in df_annual.columns if col.endswith('_vehicles_charging')]].sum().sum()
    print(f"\n   Vehículos cargados (total horas): {active_sockets:,.0f} vehículo-horas")
    print(f"   Promedio simultáneo: {active_sockets / 8760:.1f} vehículos")
    
    # Perfil horario
    print(f"\n   Perfil horario:")
    for h in range(9, 22):
        energy_h = df_annual[df_annual['hour'] == h][socket_power_cols].sum().sum()
        active_h = df_annual[df_annual['hour'] == h][
            [col for col in df_annual.columns if col.endswith('_vehicles_charging')]
        ].sum().sum()
        print(f"   {h:02d}:00 → {energy_h:6.0f} kWh, {active_h:3.0f} vehículos-hora")
    
    print(f"\n" + "="*130 + "\n")
    
    return df_annual, df_daily


if __name__ == "__main__":
    df_annual, df_daily = generate_realistic_ev_dataset()
    
    print("✅ Datasets generados exitosamente\n")
    
    print(f"RESUMEN ANUAL:")
    print(f"  Filas: {len(df_annual)}")
    print(f"  Columnas: {len(df_annual.columns)}")
    print(f"  Tamaño: {df_annual.memory_usage(deep=True).sum() / (1024**2):.2f} MB")
    
    print(f"\nRESUMEN DIARIO:")
    print(f"  Filas: {len(df_daily)}")
    print(f"  Columnas: {len(df_daily.columns)}")
    print(f"  Tamaño: {df_daily.memory_usage(deep=True).sum() / (1024**2):.2f} MB")
