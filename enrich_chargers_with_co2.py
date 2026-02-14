#!/usr/bin/env python3
"""
Enriquecedor de dataset CHARGERS con 2 columnas nuevas:
1. cantidad_motos_cargadas - Número de motos que se cargan cada hora
2. cantidad_mototaxis_cargadas - Número de mototaxis que se cargan cada hora
3. reduccion_directa_co2_motos_kg - CO₂ evitado por reemplazar motos de gasolina
4. reduccion_directa_co2_mototaxis_kg - CO₂ evitado por reemplazar mototaxis de diésel
5. reduccion_directa_co2_total_kg - CO₂ total evitado (motos + mototaxis)

METODOLOGÍA - REDUCCIÓN DIRECTA DE CO₂ (Cambio de combustible gasolina/diésel → Eléctrico):

=== MOTOS (2T, 110-150cc) ===
- Consumo gasolina típica: 2.86 L/100 km (rendimiento 35 km/L)
- Batería EV: 4.6 kWh
- Autonomía EV: 92 km (4.6 kWh × 20 km/kWh)
- Gasolina para 92 km: 92/35 = 2.63 L
- Factor CO₂ gasolina: 2.31 kg CO₂/L (IPCC)
- CO₂ evitado por carga: 2.63 × 2.31 = 6.07 kg CO₂/carga
- CO₂/kWh: 6.07 / 4.6 = 1.32 kg CO₂/kWh

=== MOTOTAXIS (3-wheelers, 200-300cc) ===
- Consumo diésel típica: 3.6 L/100 km (rendimiento 28 km/L)
- Batería EV: 7.4 kWh
- Autonomía EV: 148 km (7.4 kWh × 20 km/kWh)
- Diésel para 148 km: 148/28 = 5.29 L
- Factor CO₂ diésel: 2.68 kg CO₂/L (IPCC, ~16% más que gasolina)
- CO₂ evitado por carga: 5.29 × 2.68 = 14.18 kg CO₂/carga
- CO₂/kWh: 14.18 / 7.4 = 1.92 kg CO₂/kWh

FUENTES:
- IPCC (2006): CO₂ emissions factors (2.31 gasolina, 2.68 diésel)
- IEA Technology Collaboration Programme: 2/3-wheeler consumption
- ICCT (International Council on Clean Transportation): Electric 2/3-wheelers India
- Real-world data Iquitos (290 motos + 39 mototaxis/día)

CÁLCULO HORARIO:
- Cantidad vehículos cargados = Contador de vehículos activos por hora
- Reducción CO₂ = Cantidad × CO₂ por carga
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path

# Constantes de reducción DIRECTA de CO₂ (en kg CO₂/kWh)
# Basadas en reemplazar combustibles fósiles (gasolina/diésel) con electricidad
# NO incluye emisiones indirectas de la red (eso es otro cálculo)

# MOTOS (gasolina, 2T, 110-150cc)
MOTO_CONSUMO_L_100KM = 2.86          # L/100 km (rendimiento 35 km/L)
MOTO_BATERIA_KWH = 4.6               # kWh batería moto eléctrica
MOTO_AUTONOMIA_KM = MOTO_BATERIA_KWH * 20  # 92 km (20 km/kWh es estándar para motos eV)
MOTO_GASOLINA_PARA_AUTONOMIA = (MOTO_AUTONOMIA_KM / 100) * MOTO_CONSUMO_L_100KM  # 2.63 L
FACTOR_CO2_GASOLINA = 2.31           # kg CO₂/L (IPCC 2006)
MOTO_CO2_POR_CARGA = MOTO_GASOLINA_PARA_AUTONOMIA * FACTOR_CO2_GASOLINA  # 6.07 kg
MOTO_CO2_POR_KWH = MOTO_CO2_POR_CARGA / MOTO_BATERIA_KWH  # 1.32 kg CO₂/kWh

# MOTOTAXIS (diésel, 3-wheelers, 200-300cc)
MOTOTAXI_CONSUMO_L_100KM = 3.6       # L/100 km (rendimiento 28 km/L)
MOTOTAXI_BATERIA_KWH = 7.4           # kWh batería mototaxi eléctrico
MOTOTAXI_AUTONOMIA_KM = MOTOTAXI_BATERIA_KWH * 20  # 148 km
MOTOTAXI_DIESEL_PARA_AUTONOMIA = (MOTOTAXI_AUTONOMIA_KM / 100) * MOTOTAXI_CONSUMO_L_100KM  # 5.29 L
FACTOR_CO2_DIESEL = 2.68             # kg CO₂/L (IPCC, ~16% más que gasolina)
MOTOTAXI_CO2_POR_CARGA = MOTOTAXI_DIESEL_PARA_AUTONOMIA * FACTOR_CO2_DIESEL  # 14.18 kg
MOTOTAXI_CO2_POR_KWH = MOTOTAXI_CO2_POR_CARGA / MOTOTAXI_BATERIA_KWH  # 1.92 kg CO₂/kWh

# Potencia por toma y tiempo de carga real
POTENCIA_CHARGER_KW = 7.4            # kW (Modo 3, 32A @ 230V)
TIEMPO_CARGA_MOTO_MIN = 60            # minutos (real, con pérdidas)
TIEMPO_CARGA_MOTOTAXI_MIN = 90       # minutos (real, con pérdidas)

def enrich_chargers_dataset():
    """
    Lee el dataset de chargers y agrega 5 columnas nuevas:
    1. cantidad_motos_cargadas
    2. cantidad_mototaxis_cargadas
    3. reduccion_directa_co2_motos_kg
    4. reduccion_directa_co2_mototaxis_kg
    5. reduccion_directa_co2_total_kg
    """
    
    print("\n" + "="*110)
    print("🔌 ENRIQUECEDOR DE DATASET CHARGERS - REDUCCIÓN DIRECTA CO₂")
    print("="*110)
    
    # Cargar dataset original
    chargers_path = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    if not chargers_path.exists():
        raise FileNotFoundError(f"Dataset no encontrado: {chargers_path}")
    
    df = pd.read_csv(chargers_path, index_col=0, parse_dates=True)
    
    print(f"\n✅ Dataset cargado: {chargers_path.name}")
    print(f"   Filas: {len(df):,} (8,760 horas)")
    print(f"   Columnas originales: {len(df.columns)}")
    
    # ===================================================================
    # Extraer información de vehículos cargados
    # ===================================================================
    print(f"\n1️⃣  Calculando cantidad de vehículos cargados por hora...")
    
    # MOTOS: sockets 0-29 (30 tomas)
    moto_socket_cols = [col for col in df.columns if '_charging_power_kw' in col and 
                        int(col.split('_')[1]) < 30]
    
    # MOTOTAXIS: sockets 30-37 (8 tomas)
    taxi_socket_cols = [col for col in df.columns if '_charging_power_kw' in col and 
                        int(col.split('_')[1]) >= 30]
    
    # Cantidad de vehículos cargados = número de sockets con potencia > 0
    cantidad_motos = (df[moto_socket_cols] > 0).sum(axis=1)
    cantidad_mototaxis = (df[taxi_socket_cols] > 0).sum(axis=1)
    
    df['cantidad_motos_cargadas'] = cantidad_motos
    df['cantidad_mototaxis_cargadas'] = cantidad_mototaxis
    
    print(f"   ✅ Motos cargadas total anual: {cantidad_motos.sum():,.0f} vehículos-hora")
    print(f"   ✅ Mototaxis cargadas total anual: {cantidad_mototaxis.sum():,.0f} vehículos-hora")
    
    # ===================================================================
    # Calcular reducción DIRECTA de CO₂
    # ===================================================================
    print(f"\n2️⃣  Calculando reducción directa de CO₂...")
    
    print(f"\n   📊 MOTOS (Gasolina → Eléctrico):")
    print(f"   ├─ Consumo gasolina: {MOTO_CONSUMO_L_100KM} L/100 km")
    print(f"   ├─ Autonomía EV: {MOTO_AUTONOMIA_KM:.0f} km ({MOTO_BATERIA_KWH} kWh)")
    print(f"   ├─ Gasolina para autonomía: {MOTO_GASOLINA_PARA_AUTONOMIA:.2f} L")
    print(f"   ├─ Factor CO₂ gasolina: {FACTOR_CO2_GASOLINA} kg CO₂/L")
    print(f"   ├─ CO₂ evitado por carga: {MOTO_CO2_POR_CARGA:.2f} kg CO₂")
    print(f"   └─ CO₂ evitado por kWh: {MOTO_CO2_POR_KWH:.2f} kg CO₂/kWh")
    
    print(f"\n   📊 MOTOTAXIS (Diésel → Eléctrico):")
    print(f"   ├─ Consumo diésel: {MOTOTAXI_CONSUMO_L_100KM} L/100 km")
    print(f"   ├─ Autonomía EV: {MOTOTAXI_AUTONOMIA_KM:.0f} km ({MOTOTAXI_BATERIA_KWH} kWh)")
    print(f"   ├─ Diésel para autonomía: {MOTOTAXI_DIESEL_PARA_AUTONOMIA:.2f} L")
    print(f"   ├─ Factor CO₂ diésel: {FACTOR_CO2_DIESEL} kg CO₂/L")
    print(f"   ├─ CO₂ evitado por carga: {MOTOTAXI_CO2_POR_CARGA:.2f} kg CO₂")
    print(f"   └─ CO₂ evitado por kWh: {MOTOTAXI_CO2_POR_KWH:.2f} kg CO₂/kWh")
    
    # Reducción de CO₂ por cantidad de vehículos cargados
    df['reduccion_directa_co2_motos_kg'] = cantidad_motos * MOTO_CO2_POR_CARGA
    df['reduccion_directa_co2_mototaxis_kg'] = cantidad_mototaxis * MOTOTAXI_CO2_POR_CARGA
    df['reduccion_directa_co2_total_kg'] = (
        df['reduccion_directa_co2_motos_kg'] + df['reduccion_directa_co2_mototaxis_kg']
    )
    
    print(f"\n   ✅ Reducción CO₂ motos anual: {df['reduccion_directa_co2_motos_kg'].sum():>15,.0f} kg")
    print(f"   ✅ Reducción CO₂ mototaxis anual: {df['reduccion_directa_co2_mototaxis_kg'].sum():>10,.0f} kg")
    print(f"   ✅ Reducción CO₂ TOTAL anual: {df['reduccion_directa_co2_total_kg'].sum():>16,.0f} kg")
    print(f"      ({df['reduccion_directa_co2_total_kg'].sum()/1000:>8.1f} ton)")
    
    # ===================================================================
    # Guardar dataset enriquecido
    # ===================================================================
    print(f"\n3️⃣  Guardando dataset enriquecido...")
    
    output_path = Path("data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path)
    
    file_size_kb = output_path.stat().st_size / 1024
    
    print(f"   ✅ Guardado: {output_path.name}")
    print(f"   ├─ Ruta: {output_path}")
    print(f"   ├─ Tamaño: {file_size_kb:.1f} KB")
    print(f"   ├─ Filas: {len(df):,}")
    print(f"   └─ Columnas: {len(df.columns)} (antes: 353, nuevas: 5)")
    
    # ===================================================================
    # Mostrar resumen estadístico
    # ===================================================================
    print(f"\n4️⃣  Validaciones y resumen...")
    
    print(f"\n   📊 CANTIDAD DE VEHÍCULOS CARGADOS:")
    print(f"   ├─ Motos:")
    print(f"   │  ├─ Total vehículos-hora: {cantidad_motos.sum():>12,.0f}")
    print(f"   │  ├─ Promedio por hora: {cantidad_motos.mean():>19.2f}")
    print(f"   │  ├─ Máximo por hora: {cantidad_motos.max():>22.0f}")
    print(f"   │  └─ Ocupación promedio: {cantidad_motos.mean()/30*100:>17.1f}% (de 30 tomas)")
    
    print(f"   ├─ Mototaxis:")
    print(f"   │  ├─ Total vehículos-hora: {cantidad_mototaxis.sum():>12,.0f}")
    print(f"   │  ├─ Promedio por hora: {cantidad_mototaxis.mean():>19.2f}")
    print(f"   │  ├─ Máximo por hora: {cantidad_mototaxis.max():>22.0f}")
    print(f"   │  └─ Ocupación promedio: {cantidad_mototaxis.mean()/8*100:>17.1f}% (de 8 tomas)")
    
    print(f"\n   🌿 REDUCCIÓN DIRECTA CO₂ (Cambio de combustible):")
    
    # Estimar número de vehículos cargados por año (asumiendo 1 carga = 1 vehículo)
    cargas_motos_ano = df['cantidad_motos_cargadas'].sum()
    cargas_taxis_ano = df['cantidad_mototaxis_cargadas'].sum()
    
    # En la realidad: 270 motos/día × 365 = 98,550 cargas motos/año
    # 39 mototaxis/día × 365 = 14,235 cargas mototaxis/año
    
    print(f"   ├─ Motos:")
    print(f"   │  ├─ Vehículos-hora anual: {cargas_motos_ano:>15,.0f}")
    print(f"   │  ├─ CO₂ evitado anual: {df['reduccion_directa_co2_motos_kg'].sum():>17,.0f} kg ({df['reduccion_directa_co2_motos_kg'].sum()/1000:>6.1f} ton)")
    print(f"   │  └─ Factor CO₂: {MOTO_CO2_POR_CARGA:.2f} kg/carga")
    
    print(f"   ├─ Mototaxis:")
    print(f"   │  ├─ Vehículos-hora anual: {cargas_taxis_ano:>15,.0f}")
    print(f"   │  ├─ CO₂ evitado anual: {df['reduccion_directa_co2_mototaxis_kg'].sum():>17,.0f} kg ({df['reduccion_directa_co2_mototaxis_kg'].sum()/1000:>6.1f} ton)")
    print(f"   │  └─ Factor CO₂: {MOTOTAXI_CO2_POR_CARGA:.2f} kg/carga")
    
    print(f"   └─ TOTAL CO₂ evitado (cambio combustible):")
    print(f"      {df['reduccion_directa_co2_total_kg'].sum():>50,.0f} kg ({df['reduccion_directa_co2_total_kg'].sum()/1000:>6.1f} ton/año)")
    
    # ===================================================================
    # Proporción de reducción CO₂
    # ===================================================================
    print(f"\n   📈 PROPORCIÓN MOTOS vs MOTOTAXIS:")
    try:
        pct_motos = df['reduccion_directa_co2_motos_kg'].sum() / df['reduccion_directa_co2_total_kg'].sum() * 100
        pct_taxis = df['reduccion_directa_co2_mototaxis_kg'].sum() / df['reduccion_directa_co2_total_kg'].sum() * 100
        print(f"   ├─ Motos: {pct_motos:>6.1f}%")
        print(f"   └─ Mototaxis: {pct_taxis:>6.1f}%")
    except:
        print("   └─ (sin datos suficientes)")
    
    # ===================================================================
    # Mostrar primeras 3 filas
    # ===================================================================
    print(f"\n5️⃣  Primeras 3 filas del dataset enriquecido:")
    
    display_cols = ['cantidad_motos_cargadas', 'cantidad_mototaxis_cargadas',
                    'reduccion_directa_co2_motos_kg', 'reduccion_directa_co2_mototaxis_kg',
                    'reduccion_directa_co2_total_kg']
    
    print(df[display_cols].head(3).to_string())
    
    print(f"\n" + "="*110)
    print("✅ ENRIQUECIMIENTO COMPLETO - CHARGERS LISTO PARA CityLearn v2")
    print("="*110 + "\n")
    
    return df


if __name__ == "__main__":
    df_enriched = enrich_chargers_dataset()
