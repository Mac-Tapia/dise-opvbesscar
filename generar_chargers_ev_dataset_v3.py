"""
[DEPRECATED] Generador de Dataset EV - SIMULACIÓN POR SOCKET INDEPENDIENTE v3.0

⚠️  ESTE ARCHIVO ESTÁ DEPRECADO - Usar src/dimensionamiento/oe2/disenocargadoresev/chargers.py v5.2

Valores antiguos (ya no válidos):
- 38 sockets (30 motos + 8 mototaxis)

Valores correctos v5.2:
- 38 tomas (30 motos + 8 mototaxis)
- 19 cargadores (15 motos + 4 mototaxis) × 2 tomas/cargador
- Modo 3 @ 7.4 kW por toma
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class VehicleType:
    """Especificación de tipo de vehículo"""
    name: str
    energy_capacity_kwh: float
    charge_rate_kw: float
    avg_arrival_rate_per_hour: float  # Poisson lambda
    soc_arrival_mean: float
    soc_arrival_std: float
    target_soc: float
    parking_time_min_hours: float
    parking_time_max_hours: float


# Especificaciones por tipo
MOTO_SPEC = VehicleType(
    name="moto",
    energy_capacity_kwh=10.0,
    charge_rate_kw=2.0,
    avg_arrival_rate_per_hour=2.0,    # ✓ CORREGIDO: 2 motos por socket por hora
    soc_arrival_mean=0.35,
    soc_arrival_std=0.15,
    target_soc=0.90,
    parking_time_min_hours=0.5,
    parking_time_max_hours=2.5
)

MOTOTAXI_SPEC = VehicleType(
    name="mototaxi",
    energy_capacity_kwh=15.0,
    charge_rate_kw=3.0,
    avg_arrival_rate_per_hour=2.0,    # ✓ CORREGIDO: 2 mototaxis por socket por hora
    soc_arrival_mean=0.40,
    soc_arrival_std=0.18,
    target_soc=0.95,
    parking_time_min_hours=1.0,
    parking_time_max_hours=3.5
)


@dataclass
class Vehicle:
    """Representa un vehículo en simulación"""
    soc_arrival: float
    soc_current: float
    target_soc: float
    time_arrived_hour: int
    time_charging_hours: float
    max_parking_hours: float
    energy_capacity: float
    charge_rate: float
    fully_charged: bool


class SocketSimulator:
    """Simulador independiente para un socket individual"""
    
    def __init__(self, socket_id: int, vehicle_type: str):
        self.socket_id = socket_id
        self.vehicle_type = vehicle_type
        self.spec = MOTO_SPEC if vehicle_type == 'moto' else MOTOTAXI_SPEC
        
        # Estado actual del socket
        self.vehicle_in_socket = None  # Vehicle actual cargando
        self.waiting_queue = deque()  # Vehículos esperando
        self.power_output_kw = 0.0
        self.soc_current = 0.0
        self.num_charging = 0
        self.num_waiting = 0
    
    def hourly_step(self, hour_idx: int, hour_of_day: int, operational_factor: float, rng: np.random.RandomState) -> dict:
        """Simula un paso horario independiente para este socket.
        
        Args:
            hour_idx: Índice global de hora (0-8759)
            hour_of_day: Hora del día (0-23)
            operational_factor: Factor de operación (0-1) para este período
            rng: RandomState para reproducibilidad
            
        Returns:
            Dict con métricas del socket para esta hora
        """
        
        # 1. Generar nuevas llegadas si está en período operativo
        if operational_factor > 0.0:
            # Poisson process: llegadas de vehículos
            arrivals = rng.poisson(self.spec.avg_arrival_rate_per_hour * operational_factor)
            
            for _ in range(arrivals):
                # Crear nuevo vehículo con SOC aleatorio
                soc_arrival = np.clip(
                    rng.normal(self.spec.soc_arrival_mean, self.spec.soc_arrival_std),
                    0.05, 0.95
                )
                
                vehicle = Vehicle(
                    soc_arrival=soc_arrival,
                    soc_current=soc_arrival,
                    target_soc=self.spec.target_soc,
                    time_arrived_hour=hour_idx,
                    time_charging_hours=0.0,
                    max_parking_hours=rng.uniform(
                        self.spec.parking_time_min_hours,
                        self.spec.parking_time_max_hours
                    ),
                    energy_capacity=self.spec.energy_capacity_kwh,
                    charge_rate=self.spec.charge_rate_kw,
                    fully_charged=False
                )
                
                if self.vehicle_in_socket is None:
                    # Socket libre: asignar inmediatamente
                    self.vehicle_in_socket = vehicle
                else:
                    # Socket ocupado: encolar
                    self.waiting_queue.append(vehicle)
        
        # 2. Actualizar vehículo cargando (si hay)
        self.power_output_kw = 0.0
        self.num_charging = 0
        
        if self.vehicle_in_socket is not None:
            vehicle = self.vehicle_in_socket
            
            # Cargar por 1 hora
            energy_gained_kwh = vehicle.charge_rate * 1.0
            soc_gain = energy_gained_kwh / vehicle.energy_capacity
            vehicle.soc_current = min(vehicle.target_soc, vehicle.soc_current + soc_gain)
            vehicle.time_charging_hours += 1.0
            
            self.power_output_kw = vehicle.charge_rate
            self.soc_current = vehicle.soc_current
            self.num_charging = 1
            
            # Verificar si debe partir
            should_depart = (
                vehicle.soc_current >= vehicle.target_soc or
                vehicle.time_charging_hours >= vehicle.max_parking_hours
            )
            
            if should_depart:
                vehicle.fully_charged = (vehicle.soc_current >= vehicle.target_soc)
                
                # Vehículo se va: cargar siguiente de la cola
                if self.waiting_queue:
                    self.vehicle_in_socket = self.waiting_queue.popleft()
                else:
                    self.vehicle_in_socket = None
        else:
            # Socket libre pero puede haber cola
            self.power_output_kw = 0.01  # Standby
            self.soc_current = max(0.0, self.soc_current - 0.002)  # Autodescarga leve
            self.num_charging = 0
            
            # Si hay vehículos esperando, asignar el primero
            if self.waiting_queue:
                self.vehicle_in_socket = self.waiting_queue.popleft()
        
        # 3. Contar vehículos en espera
        self.num_waiting = len(self.waiting_queue)
        
        # 4. Compilar métricas del socket para esta hora
        metrics = {
            'socket_id': self.socket_id,
            'hour_idx': hour_idx,
            'power_kw': self.power_output_kw,
            'soc_current': self.soc_current,
            'num_charging': self.num_charging,
            'num_waiting': self.num_waiting,
            'vehicle_in_socket': 1 if self.vehicle_in_socket is not None else 0,
        }
        
        return metrics


def generate_socket_level_ev_dataset(output_dir: str | Path = "data/oe2/chargers") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Genera dataset EV con simulación independiente por socket.
    
    - 38 sockets simulados independientemente (Poisson arrivals)
    - Cada socket mantiene su propia cola de vehículos
    - SOC dinámico basado en carga real y comportamiento estocástico
    - Tipos: 30 motos + 8 mototaxis con características propias
    
    Args:
        output_dir: Directorio para guardar CSVs
        
    Returns:
        Tupla (df_annual_8760h, df_daily_24h)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    start_date = datetime(2024, 1, 1, 0, 0, 0)
    timestamps_annual = [start_date + timedelta(hours=i) for i in range(8760)]
    
    print("\n" + "="*140)
    print("GENERADOR DE DATASET EV - SIMULACIÓN POR SOCKET INDEPENDIENTE v3.0")
    print("="*140)
    print(f"""
    ARQUITECTURA DE SIMULACIÓN:
    
    📍 38 SOCKETS INDEPENDIENTES:
       - Sockets 0-111: MOTOS (28 cargadores x 2 sockets)
         * Capacidad: {MOTO_SPEC.energy_capacity_kwh} kWh
         * Velocidad carga: {MOTO_SPEC.charge_rate_kw} kW
         * Tasa llegada: {MOTO_SPEC.avg_arrival_rate_per_hour:.3f}/hora (Poisson)
         * SOC llegada: {MOTO_SPEC.soc_arrival_mean:.0%} ± {MOTO_SPEC.soc_arrival_std:.0%}
         * Tiempo parking: {MOTO_SPEC.parking_time_min_hours:.1f}-{MOTO_SPEC.parking_time_max_hours:.1f}h
       
       - Sockets 112-127: MOTOTAXIS (4 cargadores x 2 sockets)
         * Capacidad: {MOTOTAXI_SPEC.energy_capacity_kwh} kWh
         * Velocidad carga: {MOTOTAXI_SPEC.charge_rate_kw} kW
         * Tasa llegada: {MOTOTAXI_SPEC.avg_arrival_rate_per_hour:.3f}/hora (Poisson)
         * SOC llegada: {MOTOTAXI_SPEC.soc_arrival_mean:.0%} ± {MOTOTAXI_SPEC.soc_arrival_std:.0%}
         * Tiempo parking: {MOTOTAXI_SPEC.parking_time_min_hours:.1f}-{MOTOTAXI_SPEC.parking_time_max_hours:.1f}h
    
    ⏰ HORARIO (Mall abierto 9am - 22pm):
       - 9:00-10:00: Ramp-up (factor 0.30)
       - 10:00-18:00: Ramp lineal 0.30→1.00 (período pico)
       - 18:00-21:00: Máximo (factor 1.00)
       - 21:00-22:00: Ramp-down (factor 1.00→0.00 - cierre del mall)
       - 22:00-9:00: Cerrado (factor 0.00 - mall cerrado)
    
    🔄 POR SOCKET:
       - Cola independiente de vehículos esperando
       - 1 vehículo cargando simultáneamente
       - SOC actualizado en tiempo real según carga
       - Salida cuando SOC objetivo o tiempo máximo
    
    GENERANDO DATOS (puede tomar 1-2 minutos)...
    """)
    
    # Crear simuladores para 38 sockets
    sockets = {}
    for i in range(30):
        sockets[i] = SocketSimulator(socket_id=i, vehicle_type='moto')
    for i in range(30, 38):
        sockets[i] = SocketSimulator(socket_id=i, vehicle_type='mototaxi')
    
    # Factor de operación por hora del día
    def get_operational_factor(hour_of_day: int) -> float:
        """Factor de operación según hora (Mall abierto 9-22h)"""
        if 9 <= hour_of_day < 10:
            return 0.30
        elif 10 <= hour_of_day < 18:
            return 0.30 + (hour_of_day - 10) * (0.70 / 8)
        elif 18 <= hour_of_day < 21:
            return 1.00
        elif 21 <= hour_of_day < 22:
            return 1.00 - (hour_of_day - 21) * 1.00  # Ramp a 0% (cierre)
        else:
            return 0.0
    
    # ========== SIMULACIÓN ANUAL ==========
    data_annual = {
        'timestamp': timestamps_annual,
        'hour': [t.hour for t in timestamps_annual],
        'day_of_year': [t.timetuple().tm_yday for t in timestamps_annual],
    }
    
    # Pre-crear todas las columnas
    for socket_id in range(38):
        data_annual[f'socket_{socket_id:03d}_power_kw'] = np.zeros(8760)
        data_annual[f'socket_{socket_id:03d}_soc_current'] = np.zeros(8760)
        data_annual[f'socket_{socket_id:03d}_num_charging'] = np.zeros(8760)
        data_annual[f'socket_{socket_id:03d}_num_waiting'] = np.zeros(8760)
    
    for charger_id in range(32):
        data_annual[f'charger_{charger_id:02d}_power_kw'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_energy_kwh'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_active_count'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_soc_avg'] = np.zeros(8760)
    
    # RNG para reproducibilidad
    rng = np.random.RandomState(42)
    
    # Simulación hora por hora
    for hour_idx in range(8760):
        if hour_idx % 730 == 0:  # Mostrar progreso cada ~mes
            print(f"   Procesando hora {hour_idx}/8760 ({100*hour_idx/8760:.1f}%)...")
        
        timestamp = timestamps_annual[hour_idx]
        hour_of_day = timestamp.hour
        operational_factor = get_operational_factor(hour_of_day)
        
        # Ejecutar paso horario para cada socket
        socket_metrics = {}
        for socket_id in range(38):
            metrics = sockets[socket_id].hourly_step(hour_idx, hour_of_day, operational_factor, rng)
            socket_metrics[socket_id] = metrics
            
            # Guardar métricas del socket
            data_annual[f'socket_{socket_id:03d}_power_kw'][hour_idx] = metrics['power_kw']
            data_annual[f'socket_{socket_id:03d}_soc_current'][hour_idx] = metrics['soc_current']
            data_annual[f'socket_{socket_id:03d}_num_charging'][hour_idx] = metrics['num_charging']
            data_annual[f'socket_{socket_id:03d}_num_waiting'][hour_idx] = metrics['num_waiting']
        
        # Agregar al nivel de cargador
        charger_map = {}
        for charger_id in range(28):
            charger_map[charger_id] = list(range(charger_id * 4, charger_id * 4 + 4))
        for charger_id in range(28, 32):
            charger_map[charger_id] = list(range(112 + (charger_id - 15) * 2, 112 + (charger_id - 15) * 2 + 4))
        
        for charger_id in range(32):
            socket_ids = charger_map[charger_id]
            
            # Calcular agregados de cargador
            charger_power = 0.0
            charger_active = 0
            charger_soc_values = []
            
            for sid in socket_ids:
                charger_power += data_annual[f'socket_{sid:03d}_power_kw'][hour_idx]
                charger_active += int(data_annual[f'socket_{sid:03d}_num_charging'][hour_idx])
                charger_soc_values.append(data_annual[f'socket_{sid:03d}_soc_current'][hour_idx])
            
            charger_energy = charger_power  # kWh = kW × 1h
            charger_soc_avg = np.mean(charger_soc_values) if charger_soc_values else 0.0
            
            data_annual[f'charger_{charger_id:02d}_power_kw'][hour_idx] = charger_power
            data_annual[f'charger_{charger_id:02d}_energy_kwh'][hour_idx] = charger_energy
            data_annual[f'charger_{charger_id:02d}_active_count'][hour_idx] = charger_active
            data_annual[f'charger_{charger_id:02d}_soc_avg'][hour_idx] = charger_soc_avg
    
    # Crear DataFrame anual
    df_annual = pd.DataFrame(data_annual)
    
    # Ordenar columnas
    cols_base = ['timestamp', 'hour', 'day_of_year']
    cols_chargers = sorted([col for col in df_annual.columns if col.startswith('charger_')])
    cols_sockets = sorted([col for col in df_annual.columns if col.startswith('socket_')])
    
    df_annual = df_annual[cols_base + cols_chargers + cols_sockets]
    
    # Guardar
    path_annual = output_dir / 'chargers_ev_ano_2024_v3.csv'
    df_annual.to_csv(path_annual, index=False)
    
    print(f"\n✅ Dataset anual generado: {path_annual}")
    print(f"   Filas: {len(df_annual)} (8,760 horas)")
    print(f"   Columnas: {len(df_annual.columns)}")
    
    # ========== GENERAR MUESTRA DIARIA ==========
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
    
    path_daily = output_dir / 'chargers_ev_dia_2024_v3.csv'
    df_daily.to_csv(path_daily, index=False)
    
    print(f"\n✅ Dataset diario generado: {path_daily}")
    print(f"   Filas: {len(df_daily)} (24 horas - Día 1)")
    print(f"   Columnas: {len(df_daily.columns)}")
    
    # ========== VALIDACIÓN ==========
    print(f"\n📊 VALIDACIÓN DE DEMANDA:")
    
    socket_power_cols = [col for col in df_annual.columns if col.startswith('socket_') and col.endswith('_power_kw')]
    total_energy_sockets = df_annual[socket_power_cols].sum().sum()
    
    charger_energy_cols = [col for col in df_annual.columns if col.startswith('charger_') and col.endswith('_energy_kwh')]
    total_energy_chargers = df_annual[charger_energy_cols].sum().sum()
    
    print(f"\n   Energía total anual (socket-level)  : {total_energy_sockets:>10,.0f} kWh")
    print(f"   Energía total anual (charger-level) : {total_energy_chargers:>10,.0f} kWh")
    print(f"   Energía diaria promedio             : {total_energy_sockets / 365:>10,.0f} kWh/día")
    
    # Ocupación
    num_charging_total = df_annual[[col for col in df_annual.columns if col.endswith('_num_charging')]].sum().sum()
    print(f"\n   Vehículos cargados (total socket-h): {num_charging_total:>10,.0f}")
    print(f"   Ocupación promedio simultánea      : {num_charging_total / 8760:>10.1f} sockets")
    
    # Perfil horario
    print(f"\n   PERFIL HORARIO DETALLADO:")
    print(f"   {'HH':>4} {'Factor':>8} {'Energía':>12} {'Sockets':>10} {'Demanda':>10}")
    print(f"   {'-'*4} {'-'*8} {'-'*12} {'-'*10} {'-'*10}")
    
    for h in range(24):
        mask = df_annual['hour'] == h
        energy_h = df_annual[mask][socket_power_cols].sum().sum()
        charging_h = df_annual[mask][[col for col in df_annual.columns if col.endswith('_num_charging')]].sum().sum()
        factor = get_operational_factor(h)
        
        if energy_h > 0 or charging_h > 0:
            print(f"   {h:02d}h {factor:>8.2%} {energy_h:>12.0f} {charging_h:>10.0f} {energy_h/24:>10.0f} kWh")
    
    print(f"\n" + "="*140 + "\n")
    
    return df_annual, df_daily


if __name__ == "__main__":
    df_annual, df_daily = generate_socket_level_ev_dataset()
    
    print("✅ Datasets generados exitosamente\n")
    
    print(f"RESUMEN ANUAL:")
    print(f"  Filas: {len(df_annual)}")
    print(f"  Columnas: {len(df_annual.columns)}")
    print(f"  Tamaño: {df_annual.memory_usage(deep=True).sum() / (1024**2):.2f} MB")
    
    print(f"\nRESUMEN DIARIO:")
    print(f"  Filas: {len(df_daily)}")
    print(f"  Columnas: {len(df_daily.columns)}")
    print(f"  Tamaño: {df_daily.memory_usage(deep=True).sum() / (1024**2):.2f} MB")
