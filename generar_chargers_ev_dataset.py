"""
[DEPRECATED] Generador de Dataset EV para Control y Entrenamiento de Agentes

⚠️  ESTE ARCHIVO ESTÁ DEPRECADO - Usar src/dimensionamiento/oe2/disenocargadoresev/chargers.py v5.2

Valores antiguos (ya no válidos):
- 19 cargadores x 2 tomas = 38 tomas (INCORRECTO)

Valores correctos v5.2:
- 19 cargadores × 2 tomas = 38 tomas (Modo 3 @ 7.4 kW)
- 15 cargadores motos (30 tomas) + 4 cargadores mototaxis (8 tomas)
- Energía: 1,529.9 kWh/día (escenario RECOMENDADO pe=0.30, fc=0.55)
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def generate_chargers_ev_dataset(output_dir: str | Path = "data/oe2/chargers") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Genera dataset completo de EV con 19 cargadores y 38 tomas.
    
    Estructura:
    - 15 cargadores de motos (índices 0-14): 4 tomas cada uno = 112 tomas
    - 4 cargadores de mototaxis (índices 15-18): 4 tomas cada uno = 16 tomas
    
    Datos realistas:
    - Demanda: 544 kWh/h durante horas activas (10-16h, 18-20h)
    - Anual: 1,985,600 kWh (10h/día × 365 días)
    
    Args:
        output_dir: Directorio para guardar CSVs
        
    Returns:
        Tupla (df_annual_8760h, df_daily_24h)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Crear índice temporal para año 2024 completo
    start_date = datetime(2024, 1, 1, 0, 0, 0)
    timestamps_annual = [start_date + timedelta(hours=i) for i in range(8760)]
    
    print("\n" + "="*120)
    print("GENERANDO DATASET EV - ESTRUCTURA CORRECTA")
    print("="*120)
    print(f"""
    19 CARGADORES:
      - 15 cargadores MOTOS (índices 0-14): 4 tomas cada uno = 112 tomas
      - 4 cargadores MOTOTAXIS (índices 15-18): 4 tomas cada uno = 16 tomas
    
    DEMANDA:
      - 9:00-10:00: 10% demanda (1h)
      - 10:00-18:00: Sube 10% a 100% lineal (8h)
      - 18:00-21:00: 100% demanda (3h)
      - 21:00-22:00: Baja 100% a 0% lineal (1h)
      - Anual: ~1,588,480 kWh (~4,352 kWh/día)
    
    GENERANDO DATOS...
    """)
    
    # ========== GENERAR DATOS ANUALES ==========
    data_annual = {
        'timestamp': timestamps_annual,
        'hour': [t.hour for t in timestamps_annual],
        'day_of_year': [t.timetuple().tm_yday for t in timestamps_annual],
    }
    
    # Especificaciones de cargadores
    chargers = {}
    sockets_by_charger = {}
    
    # 15 cargadores de motos
    for charger_id in range(28):
        chargers[charger_id] = {'type': 'moto', 'power_per_socket': 2.0}
        sockets_by_charger[charger_id] = list(range(charger_id * 4, charger_id * 4 + 4))
    
    # 4 cargadores de mototaxis
    for charger_id in range(28, 32):
        chargers[charger_id] = {'type': 'mototaxi', 'power_per_socket': 3.0}
        sockets_by_charger[charger_id] = list(range(30 + ((charger_id - 15) * 2), 30 + ((charger_id - 15) * 2) + 4))
    
    # Horas de carga: 9-22 con perfil variable
    # 9-10: 10%, 10-18: lineal 10%-100%, 18-21: 100%, 21-22: lineal 100%-0%
    
    def get_demand_factor(hour_of_day: int) -> float:
        """Retorna factor de demanda (0-1) según hora del día.
        
        9:00-10:00: 0.10 (10%)
        10:00-18:00: lineal 0.10 → 1.00
        18:00-21:00: 1.00 (100%)
        21:00-22:00: lineal 1.00 → 0.00
        22:00-9:00: 0.00 (sin carga)
        """
        if 9 <= hour_of_day < 10:
            return 0.10
        elif 10 <= hour_of_day < 18:
            # Subida lineal de 0.10 a 1.00 en 8 horas
            return 0.10 + (hour_of_day - 10) * (0.90 / 8)
        elif 18 <= hour_of_day < 21:
            return 1.00
        elif 21 <= hour_of_day < 22:
            # Bajada lineal de 1.00 a 0.00 en 1 hora
            return 1.00 - (hour_of_day - 21) * 1.00
        else:
            return 0.00
    
    # Demanda máxima base (cuando factor = 1.00)
    BASE_DEMAND_KWH_H = 544.0
    
    # Solución: Los 2 ciclos de 30min/hora permiten cargar 2 vehículos por toma
    # Demanda promedio por toma = (544 kWh/h) / 38 tomas = 4.25 kWh/h
    
    # Inicializar arrays para tomas y cargadores
    for charger_id in range(32):
        num_sockets = 4
        data_annual[f'charger_{charger_id:02d}_power_kw'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_energy_kwh'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_active_sockets'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_soc_avg'] = np.zeros(8760)
        data_annual[f'charger_{charger_id:02d}_fully_charged'] = np.zeros(8760)
    
    # Inicializar arrays para tomas individuales
    for socket_id in range(38):
        data_annual[f'socket_{socket_id:03d}_soc_current'] = np.zeros(8760)
        data_annual[f'socket_{socket_id:03d}_active'] = np.zeros(8760)
        data_annual[f'socket_{socket_id:03d}_power_kw'] = np.zeros(8760)
        data_annual[f'socket_{socket_id:03d}_vehicles_waiting'] = np.zeros(8760)
    
    # Simular por hora
    np.random.seed(42)
    soc_current = np.random.uniform(0.2, 0.5, 128)  # SOC inicial aleatorio
    
    for hour_idx in range(8760):
        timestamp = timestamps_annual[hour_idx]
        hour_of_day = timestamp.hour
        
        # Factor de demanda según perfil horario
        demand_factor = get_demand_factor(hour_of_day)
        
        if demand_factor > 0.0:
            # CARGA ACTIVA: Aplicar factor de demanda
            target_total_power = BASE_DEMAND_KWH_H * demand_factor
            
            # Distribuir proporcionalmente
            target_per_socket = target_total_power / 38.0
            
            # Crear distribución realista con variación (38 sockets v5.2)
            socket_demands = np.random.normal(target_per_socket, target_per_socket * 0.15, 38)
            socket_demands = np.clip(socket_demands, 0, None)  # No negativos
            
            # Normalizar para asegurar que suma exactamente a target_total_power
            current_sum = socket_demands.sum()
            if current_sum > 0:
                socket_demands = socket_demands * (target_total_power / current_sum)
            else:
                socket_demands = np.ones(38) * (target_total_power / 38)
            
            # Aplicar demanda a cada toma
            for socket_id in range(38):
                power_kw = socket_demands[socket_id]
                
                # Actualizar SOC
                if socket_id < 112:
                    # Motos: energía típica 10 kWh
                    soc_gain = power_kw / 10.0
                else:
                    # Taxis: energía típica 15 kWh
                    soc_gain = power_kw / 15.0
                
                soc_current[socket_id] = min(1.0, soc_current[socket_id] + soc_gain)
                
                data_annual[f'socket_{socket_id:03d}_active'][hour_idx] = 1
                data_annual[f'socket_{socket_id:03d}_power_kw'][hour_idx] = power_kw
                data_annual[f'socket_{socket_id:03d}_vehicles_waiting'][hour_idx] = 1
                data_annual[f'socket_{socket_id:03d}_soc_current'][hour_idx] = soc_current[socket_id]
        else:
            # Horas sin demanda: reposo (pero permanecer conectadas con pequeño consumo de standby)
            standby_power = 0.01  # kW standby
            
            for socket_id in range(38):
                # Standby consumption
                soc_current[socket_id] = max(0.0, soc_current[socket_id] - standby_power / 1000)
                
                data_annual[f'socket_{socket_id:03d}_active'][hour_idx] = 0
                data_annual[f'socket_{socket_id:03d}_power_kw'][hour_idx] = standby_power
                data_annual[f'socket_{socket_id:03d}_vehicles_waiting'][hour_idx] = 0
                data_annual[f'socket_{socket_id:03d}_soc_current'][hour_idx] = soc_current[socket_id]
        
        # Agregar al nivel de cargador
        for charger_id in range(32):
            socket_ids = sockets_by_charger[charger_id]
            
            charger_power = sum([data_annual[f'socket_{sid:03d}_power_kw'][hour_idx] for sid in socket_ids])
            charger_active = sum([data_annual[f'socket_{sid:03d}_active'][hour_idx] for sid in socket_ids])
            charger_soc_avg = np.mean([soc_current[sid] for sid in socket_ids])
            charger_fully_charged = sum([1 for sid in socket_ids if soc_current[sid] >= 0.95])
            
            data_annual[f'charger_{charger_id:02d}_power_kw'][hour_idx] = charger_power
            data_annual[f'charger_{charger_id:02d}_energy_kwh'][hour_idx] = charger_power  # kWh = kW × 1h
            data_annual[f'charger_{charger_id:02d}_active_sockets'][hour_idx] = int(charger_active)
            data_annual[f'charger_{charger_id:02d}_soc_avg'][hour_idx] = charger_soc_avg
            data_annual[f'charger_{charger_id:02d}_fully_charged'][hour_idx] = int(charger_fully_charged)
    
    # Crear DataFrame anual
    df_annual = pd.DataFrame(data_annual)
    
    # Ordenar columnas
    cols_base = ['timestamp', 'hour', 'day_of_year']
    cols_chargers = sorted([col for col in df_annual.columns if col.startswith('charger_')])
    cols_sockets = sorted([col for col in df_annual.columns if col.startswith('socket_')])
    
    df_annual = df_annual[cols_base + cols_chargers + cols_sockets]
    
    # Guardar anual
    path_annual = output_dir / 'chargers_ev_ano_2024.csv'
    df_annual.to_csv(path_annual, index=False)
    
    print(f"✅ Dataset anual generado: {path_annual}")
    print(f"   Filas: {len(df_annual)} (8,760 horas)")
    print(f"   Columnas: {len(df_annual.columns)}")
    print(f"     - 3 base (timestamp, hour, day_of_year)")
    print(f"     - 160 de cargadores (19 cargadores × 5 métricas)")
    print(f"     - 896 de tomas (38 tomas × 7 métricas)")
    
    # ========== GENERAR DATOS DE UN DÍA ==========
    day1_start = start_date
    day1_end = start_date + timedelta(hours=24)
    timestamps_daily = [start_date + timedelta(hours=i) for i in range(24)]
    
    data_daily = {
        'timestamp': timestamps_daily,
        'hour': [t.hour for t in timestamps_daily],
        'day_of_year': [t.timetuple().tm_yday for t in timestamps_daily],
    }
    
    # Copiar datos del primer día desde annual
    for col in cols_chargers + cols_sockets:
        data_daily[col] = df_annual[col].iloc[:24].values
    
    df_daily = pd.DataFrame(data_daily)
    df_daily = df_daily[cols_base + cols_chargers + cols_sockets]
    
    # Guardar diaria
    path_daily = output_dir / 'chargers_ev_dia_2024.csv'
    df_daily.to_csv(path_daily, index=False)
    
    print(f"\n✅ Dataset diario generado: {path_daily}")
    print(f"   Filas: {len(df_daily)} (24 horas - Día 1)")
    print(f"   Columnas: {len(df_daily.columns)}")
    
    # Validación
    print(f"\n📊 VALIDACION DE DEMANDA:")
    total_energy_annual = df_annual[[col for col in df_annual.columns if col.startswith('socket_') and col.endswith('_power_kw')]].sum().sum()
    print(f"   Energía total anual (socket-level): {total_energy_annual:,.0f} kWh")
    print(f"   Esperado aprox: 1,588,480 kWh (4,352 kWh/día)")
    print(f"   Diferencia: {abs(total_energy_annual - 1588480):,.0f} kWh ({abs(total_energy_annual - 1588480) / 1588480 * 100:.2f}%)")
    
    total_energy_chargers = df_annual[[col for col in df_annual.columns if col.startswith('charger_') and col.endswith('_energy_kwh')]].sum().sum()
    print(f"\n   Energía total anual (charger-level): {total_energy_chargers:,.0f} kWh")
    
    print(f"\n" + "="*120 + "\n")
    
    return df_annual, df_daily


if __name__ == "__main__":
    df_annual, df_daily = generate_chargers_ev_dataset()
    
    print("✅ Datasets generados exitosamente\n")
    
    print(f"RESUMEN ANUAL:")
    print(f"  Filas: {len(df_annual)}")
    print(f"  Columnas: {len(df_annual.columns)}")
    print(f"  Tamaño: {df_annual.memory_usage(deep=True).sum() / (1024**2):.2f} MB")
    
    print(f"\nRESUMEN DIARIO:")
    print(f"  Filas: {len(df_daily)}")
    print(f"  Columnas: {len(df_daily.columns)}")
    print(f"  Tamaño: {df_daily.memory_usage(deep=True).sum() / (1024**2):.2f} MB")
