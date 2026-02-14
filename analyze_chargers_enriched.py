#!/usr/bin/env python3
"""
Análisis completo del dataset CHARGERS enriquecido con reducción directa de CO₂
Visualiza las 5 nuevas columnas y su impacto en reducción de emisiones.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path

def analyze_chargers_enriched():
    """Analiza el dataset enriquecido de chargers."""
    
    print("\n" + "="*120)
    print("📊 ANÁLISIS DATASET CHARGERS ENRIQUECIDO - REDUCCIÓN DIRECTA CO₂ v2")
    print("="*120)
    
    # Cargar dataset
    chargers_path = Path("data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv")
    df = pd.read_csv(chargers_path, index_col=0, parse_dates=True)
    
    print(f"\n✅ Dataset: {chargers_path.name}")
    print(f"   Dimensiones: {len(df):,} filas × {len(df.columns)} columnas")
    print(f"   Período: {df.index[0].strftime('%Y-%m-%d %H:%M')} a {df.index[-1].strftime('%Y-%m-%d %H:%M')}")
    
    # ===================================================================
    # 1. CANTIDAD DE VEHÍCULOS CARGADOS
    # ===================================================================
    print(f"\n{'='*120}")
    print("1️⃣  CANTIDAD DE VEHÍCULOS CARGADOS POR HORA")
    print(f"{'='*120}")
    
    print(f"\n🏍️  MOTOS (Playa 30 tomas):")
    print(f"   ├─ Total vehículos-hora anual: {df['cantidad_motos_cargadas'].sum():>12,.0f}")
    print(f"   ├─ Promedio por hora: {df['cantidad_motos_cargadas'].mean():>22.2f} motos/h")
    print(f"   ├─ Mediana: {df['cantidad_motos_cargadas'].median():>36.2f} motos/h")
    print(f"   ├─ Mínimo: {df['cantidad_motos_cargadas'].min():>38.0f} motos/h")
    print(f"   ├─ Máximo: {df['cantidad_motos_cargadas'].max():>38.0f} motos/h")
    print(f"   └─ Std Dev: {df['cantidad_motos_cargadas'].std():>35.2f}")
    
    motos_activos = (df['cantidad_motos_cargadas'] > 0).sum()
    motos_pct = motos_activos / len(df) * 100
    print(f"   └─ Horas activas: {motos_activos:>30} ({motos_pct:.1f}% del año)")
    
    print(f"\n🛵  MOTOTAXIS (Playa 8 tomas):")
    print(f"   ├─ Total vehículos-hora anual: {df['cantidad_mototaxis_cargadas'].sum():>12,.0f}")
    print(f"   ├─ Promedio por hora: {df['cantidad_mototaxis_cargadas'].mean():>22.2f} taxis/h")
    print(f"   ├─ Mediana: {df['cantidad_mototaxis_cargadas'].median():>36.2f} taxis/h")
    print(f"   ├─ Mínimo: {df['cantidad_mototaxis_cargadas'].min():>38.0f} taxis/h")
    print(f"   ├─ Máximo: {df['cantidad_mototaxis_cargadas'].max():>38.0f} taxis/h")
    print(f"   └─ Std Dev: {df['cantidad_mototaxis_cargadas'].std():>35.2f}")
    
    taxis_activos = (df['cantidad_mototaxis_cargadas'] > 0).sum()
    taxis_pct = taxis_activos / len(df) * 100
    print(f"   └─ Horas activas: {taxis_activos:>30} ({taxis_pct:.1f}% del año)")
    
    # ===================================================================
    # 2. REDUCCIÓN DIRECTA DE CO₂
    # ===================================================================
    print(f"\n{'='*120}")
    print("2️⃣  REDUCCIÓN DIRECTA DE CO₂ (Cambio de combustible: Gasolina/Diésel → Eléctrico)")
    print(f"{'='*120}")
    
    print(f"\n🏍️  MOTOS (Gasolina → Eléctrico):")
    co2_motos_total = df['reduccion_directa_co2_motos_kg'].sum()
    print(f"   ├─ CO₂ evitado anual: {co2_motos_total:>19,.0f} kg ({co2_motos_total/1000:>6.1f} toneladas)")
    print(f"   ├─ Promedio horario: {df['reduccion_directa_co2_motos_kg'].mean():>21.2f} kg CO₂/h")
    print(f"   ├─ Máximo horario: {df['reduccion_directa_co2_motos_kg'].max():>23.1f} kg CO₂/h")
    print(f"   ├─ Factor CO₂ por carga: {co2_motos_total / df['cantidad_motos_cargadas'].sum():>17.2f} kg CO₂/carga")
    print(f"   └─ Factor CO₂ por kWh: 1.32 kg CO₂/kWh (vs gasolina)")
    
    print(f"\n🛵  MOTOTAXIS (Diésel → Eléctrico):")
    co2_taxis_total = df['reduccion_directa_co2_mototaxis_kg'].sum()
    print(f"   ├─ CO₂ evitado anual: {co2_taxis_total:>19,.0f} kg ({co2_taxis_total/1000:>6.1f} toneladas)")
    print(f"   ├─ Promedio horario: {df['reduccion_directa_co2_mototaxis_kg'].mean():>21.2f} kg CO₂/h")
    print(f"   ├─ Máximo horario: {df['reduccion_directa_co2_mototaxis_kg'].max():>23.1f} kg CO₂/h")
    print(f"   ├─ Factor CO₂ por carga: {co2_taxis_total / df['cantidad_mototaxis_cargadas'].sum():>17.2f} kg CO₂/carga")
    print(f"   └─ Factor CO₂ por kWh: 1.93 kg CO₂/kWh (vs diésel)")
    
    print(f"\n🌍 TOTAL REDUCCIÓN DIRECTA DE CO₂:")
    co2_total = df['reduccion_directa_co2_total_kg'].sum()
    print(f"   ├─ CO₂ evitado anual: {co2_total:>19,.0f} kg ({co2_total/1000:>6.1f} toneladas)")
    print(f"   ├─ Promedio horario: {df['reduccion_directa_co2_total_kg'].mean():>21.2f} kg CO₂/h")
    print(f"   ├─ Máximo horario: {df['reduccion_directa_co2_total_kg'].max():>23.1f} kg CO₂/h")
    print(f"   └─ Std Dev: {df['reduccion_directa_co2_total_kg'].std():>35.2f}")
    
    # ===================================================================
    # 3. PROPORCIÓN Y COMPARATIVAS
    # ===================================================================
    print(f"\n{'='*120}")
    print("3️⃣  PROPORCIÓN MOTOS vs MOTOTAXIS")
    print(f"{'='*120}")
    
    pct_motos = co2_motos_total / co2_total * 100
    pct_taxis = co2_taxis_total / co2_total * 100
    
    print(f"\n📊 Distribución de CO₂ evitado:")
    print(f"   ├─ Motos:     {pct_motos:>6.1f}% ({co2_motos_total:>12,.0f} kg)")
    print(f"   └─ Mototaxis: {pct_taxis:>6.1f}% ({co2_taxis_total:>12,.0f} kg)")
    
    # Cargas por tipo
    cargas_motos = df['cantidad_motos_cargadas'].sum()
    cargas_taxis = df['cantidad_mototaxis_cargadas'].sum()
    
    print(f"\n📊 Distribución de vehículos cargados:")
    print(f"   ├─ Motos:     {cargas_motos / (cargas_motos + cargas_taxis) * 100:>6.1f}% ({cargas_motos:>12,.0f} veh-h)")
    print(f"   └─ Mototaxis: {cargas_taxis / (cargas_motos + cargas_taxis) * 100:>6.1f}% ({cargas_taxis:>12,.0f} veh-h)")
    
    # ===================================================================
    # 4. EQUIVALENCIAS Y CONTEXTO
    # ===================================================================
    print(f"\n{'='*120}")
    print("4️⃣  EQUIVALENCIAS Y CONTEXTO AMBIENTAL")
    print(f"{'='*120}")
    
    # Equivalencias
    arboles_ano = co2_total / 21  # 1 árbol absorbe ~21 kg CO₂/año
    viajes_auto = co2_total / 4.6  # 1 auto emite ~4.6 kg CO₂/km
    personas_dia = co2_total / 8  # 1 persona emite ~8 kg CO₂/día
    
    print(f"\n🌳 CO₂ EQUIVALENTE A:")
    print(f"   ├─ Árboles plantados (absorción/año): {arboles_ano:>16,.0f} árboles")
    print(f"   ├─ Kilómetros de auto evitados (emisión): {viajes_auto:>14,.0f} km")
    print(f"   └─ Personas durante 1 año (8 kg CO₂/persona/día): {personas_dia:>7,.0f} personas")
    
    # ===================================================================
    # 5. DISTRIBUCIÓN POR HORA DEL DÍA
    # ===================================================================
    print(f"\n{'='*120}")
    print("5️⃣  DISTRIBUCIÓN POR HORA DEL DÍA (Ejemplo día 2024-01-01)")
    print(f"{'='*120}")
    
    # Extraer un día ejemplo
    fecha_ejemplo = pd.Timestamp('2024-01-01')
    dia = df.loc[fecha_ejemplo:fecha_ejemplo + pd.Timedelta(days=1)]
    
    print(f"\nHora │ Motos │ Taxa │ CO₂ Motos │ CO₂ Taxa │ CO₂ Total")
    print(f"─────┼───────┼──────┼───────────┼──────────┼──────────")
    
    for idx, row in dia[:-1].iterrows():  # Excluir última fila (00:00 del siguiente día)
        hora = idx.hour
        print(f" {hora:02d}h │  {int(row['cantidad_motos_cargadas']):>2d}  │  {int(row['cantidad_mototaxis_cargadas']):>2d}  │ "
              f"{row['reduccion_directa_co2_motos_kg']:>7.1f}  │ {row['reduccion_directa_co2_mototaxis_kg']:>8.1f} │ "
              f"{row['reduccion_directa_co2_total_kg']:>8.1f}")
    
    # ===================================================================
    # 6. ESTADÍSTICAS MENSUALES
    # ===================================================================
    print(f"\n{'='*120}")
    print("6️⃣  ESTADÍSTICAS MENSUALES (2024)")
    print(f"{'='*120}")
    
    df['mes'] = df.index.month
    df['mes_nombre'] = df.index.strftime('%B')
    
    resumen_mensual = df.groupby('mes').agg({
        'cantidad_motos_cargadas': ['sum', 'mean'],
        'cantidad_mototaxis_cargadas': ['sum', 'mean'],
        'reduccion_directa_co2_motos_kg': 'sum',
        'reduccion_directa_co2_mototaxis_kg': 'sum',
        'reduccion_directa_co2_total_kg': 'sum'
    }).round(2)
    
    print(f"\nMes │ Motos (total) │ Taxa (total) │ CO₂ Motos │ CO₂ Taxa │ CO₂ Total")
    print(f"────┼───────────────┼──────────────┼───────────┼──────────┼──────────")
    
    meses = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
    
    for i in range(1, 13):
        mes_data = df[df['mes'] == i]
        if len(mes_data) > 0:
            print(f" {meses[i-1]} │ {mes_data['cantidad_motos_cargadas'].sum():>12,.0f} │ "
                  f"{mes_data['cantidad_mototaxis_cargadas'].sum():>11,.0f} │ "
                  f"{mes_data['reduccion_directa_co2_motos_kg'].sum():>8,.0f} │ "
                  f"{mes_data['reduccion_directa_co2_mototaxis_kg'].sum():>8,.0f} │ "
                  f"{mes_data['reduccion_directa_co2_total_kg'].sum():>8,.0f}")
    
    # ===================================================================
    # 7. DESCRIPCIÓN DE LAS 5 COLUMNAS NUEVAS
    # ===================================================================
    print(f"\n{'='*120}")
    print("7️⃣  DESCRIPCIÓN DE LAS 5 COLUMNAS NUEVAS")
    print(f"{'='*120}")
    
    print(f"""
┌─ COLUMNA 1: cantidad_motos_cargadas
│  ├─ Tipo de dato: Int (0-26)
│  ├─ Descripción: Número de motos cargando simultáneamente cada hora
│  ├─ Rango: 0 a 26 motos/hora (máximo de 30 tomas disponibles)
│  ├─ Promedio: {df['cantidad_motos_cargadas'].mean():.2f} motos/hora
│  └─ Total anual: {df['cantidad_motos_cargadas'].sum():,.0f} vehículos-hora

├─ COLUMNA 2: cantidad_mototaxis_cargadas
│  ├─ Tipo de dato: Int (0-8)
│  ├─ Descripción: Número de mototaxis cargando simultáneamente cada hora
│  ├─ Rango: 0 a 8 mototaxis/hora (máximo de 8 tomas disponibles)
│  ├─ Promedio: {df['cantidad_mototaxis_cargadas'].mean():.2f} mototaxis/hora
│  └─ Total anual: {df['cantidad_mototaxis_cargadas'].sum():,.0f} vehículos-hora

├─ COLUMNA 3: reduccion_directa_co2_motos_kg
│  ├─ Tipo de dato: Float
│  ├─ Descripción: CO₂ evitado por motos (reemplazar gasolina con eléctrico)
│  ├─ Factor: 6.08 kg CO₂ por carga de moto (100 km autonomía)
│  ├─ Metodología: cantidad_motos_cargadas × 6.08 kg CO₂/carga
│  ├─ Promedio horario: {df['reduccion_directa_co2_motos_kg'].mean():.2f} kg CO₂/h
│  └─ Total anual: {co2_motos_total:,.0f} kg ({co2_motos_total/1000:.1f} ton)

├─ COLUMNA 4: reduccion_directa_co2_mototaxis_kg
│  ├─ Tipo de dato: Float
│  ├─ Descripción: CO₂ evitado por mototaxis (reemplazar diésel con eléctrico)
│  ├─ Factor: 14.28 kg CO₂ por carga de mototaxi (150 km autonomía)
│  ├─ Metodología: cantidad_mototaxis_cargadas × 14.28 kg CO₂/carga
│  ├─ Promedio horario: {df['reduccion_directa_co2_mototaxis_kg'].mean():.2f} kg CO₂/h
│  └─ Total anual: {co2_taxis_total:,.0f} kg ({co2_taxis_total/1000:.1f} ton)

└─ COLUMNA 5: reduccion_directa_co2_total_kg
   ├─ Tipo de dato: Float
   ├─ Descripción: CO₂ total evitado (motos + mototaxis)
   ├─ Fórmula: reduccion_directa_co2_motos_kg + reduccion_directa_co2_mototaxis_kg
   ├─ Promedio horario: {df['reduccion_directa_co2_total_kg'].mean():.2f} kg CO₂/h
   └─ Total anual: {co2_total:,.0f} kg ({co2_total/1000:.1f} ton)
    """)
    
    # ===================================================================
    # 8. METODOLOGÍA TÉCNICA
    # ===================================================================
    print(f"\n{'='*120}")
    print("8️⃣  METODOLOGÍA TÉCNICA - FACTORES CO₂ CALCULADOS")
    print(f"{'='*120}")
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════════╗
║ MOTOS (Gasolina → Eléctrico)                                                                       ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════╣
║ • Consumo gasolina típica (2T, 110-150cc): 2.86 L/100 km (35 km/L)                                 ║
║ • Batería eléctrica moto: 4.6 kWh                                                                   ║
║ • Autonomía EV: 4.6 kWh × 20 km/kWh = 92 km                                                        ║
║ • Gasolina para 92 km: (92/100) × 2.86 = 2.63 L                                                    ║
║ • Factor CO₂ gasolina (IPCC): 2.31 kg CO₂/L                                                        ║
║ • CO₂ evitado por carga: 2.63 L × 2.31 kg/L = 6.08 kg CO₂                                         ║
║ • CO₂ por kWh: 6.08 kg / 4.6 kWh = 1.32 kg CO₂/kWh                                                ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════╣
║ MOTOTAXIS (Diésel → Eléctrico)                                                                     ║
╠══════════════════════════════════════════════════════════════════════════════════════════════════════╣
║ • Consumo diésel típico (3-wheelers, 200-300cc): 3.6 L/100 km (28 km/L)                           ║
║ • Batería eléctrica mototaxi: 7.4 kWh                                                              ║
║ • Autonomía EV: 7.4 kWh × 20 km/kWh = 148 km                                                       ║
║ • Diésel para 148 km: (148/100) × 3.6 = 5.33 L                                                     ║
║ • Factor CO₂ diésel (IPCC): 2.68 kg CO₂/L (16% más que gasolina)                                   ║
║ • CO₂ evitado por carga: 5.33 L × 2.68 kg/L = 14.28 kg CO₂                                        ║
║ • CO₂ por kWh: 14.28 kg / 7.4 kWh = 1.93 kg CO₂/kWh                                               ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════╝

FUENTES:
  • IPCC (2006): Emission factors for fossil fuels
  • IEA Technology Collaboration Programme: 2/3-wheeler technology deployment
  • ICCT: Electric two/three-wheelers deployment perspectives in India
  • Real-world data Iquitos: 270 motos + 39 mototaxis cargando diariamente
    """)
    
    print(f"\n{'='*120}")
    print("✅ ANÁLISIS COMPLETO - CHARGERS ENRIQUECIDO LISTO")
    print(f"{'='*120}\n")
    
    return df


if __name__ == "__main__":
    df = analyze_chargers_enriched()
