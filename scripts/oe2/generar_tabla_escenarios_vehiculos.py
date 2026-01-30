#!/usr/bin/env python
"""
Generador de Tabla de Escenarios - Vehículos Cargados
=====================================================

Calcula la cantidad de motos y mototaxis cargados por:
- Día
- Mes
- Año

Para todos los escenarios de la Tabla 13 OE2.

ESCENARIO RECOMENDADO: Se usa para el entrenamiento del agente OE3.
"""

import pandas as pd
from pathlib import Path
from typing import Any, Dict, List

# ============================================================================
# CONSTANTES - TABLA 13 OE2
# ============================================================================

# Flota de vehículos en Iquitos (estimación)
# Proporción: 87.5% motos, 12.5% mototaxis (basado en 112/128 y 16/128 tomas)
FLOTA_TOTAL = 1030  # Vehículos totales que potencialmente cargarían
RATIO_MOTOS = 0.875  # 87.5% motos
RATIO_MOTOTAXIS = 0.125  # 12.5% mototaxis

# Configuración de infraestructura
N_TOMAS_MOTOS = 112  # 28 cargadores × 4 tomas
N_TOMAS_MOTOTAXIS = 16  # 4 cargadores × 4 tomas
N_TOMAS_TOTAL = 128

POTENCIA_MOTO_KW = 2.0  # kW por toma
POTENCIA_MOTOTAXI_KW = 3.0  # kW por toma

# Sesiones de 30 minutos
SESSION_MINUTES = 30
ENERGY_PER_SESSION_MOTO = POTENCIA_MOTO_KW * (SESSION_MINUTES / 60)  # 1.0 kWh
ENERGY_PER_SESSION_MOTOTAXI = POTENCIA_MOTOTAXI_KW * (SESSION_MINUTES / 60)  # 1.5 kWh

# Días
DAYS_MONTH = 30
DAYS_YEAR = 365

# ============================================================================
# ESTADÍSTICAS TABLA 13 OE2
# ============================================================================
TABLA_13_STATS = {
    "energia_dia_kwh": {
        "min": 92.80,
        "max": 3252.00,
        "promedio": 903.46,
        "mediana": 835.20,
        "std": 572.07
    },
    "cargadores": {
        "min": 4,
        "max": 35,
        "promedio": 20.61,
        "mediana": 20,
        "std": 9.19
    },
    "tomas": {
        "min": 16,
        "max": 140,
        "promedio": 82.46,
        "mediana": 80,
        "std": 36.76
    },
    "cargas_dia": {
        "min": 87.29,
        "max": 3058.96,
        "promedio": 849.83,
        "mediana": 785.62,
        "std": 538.12
    }
}


def generate_scenarios() -> pd.DataFrame:
    """
    Genera los 4 escenarios principales con desglose de motos/mototaxis.

    CORRECCIÓN: Las 4 horas pico (6pm-10pm) representan ~40% de la demanda diaria.
    Si en horas pico hay ~900 motos y ~130 mototaxis, en el día completo hay más.

    Horario: 9am - 10pm = 13 horas de operación
    Horas pico: 6pm - 10pm = 4 horas (~40% de la demanda)
    Horas normales: 9am - 6pm = 9 horas (~60% de la demanda)
    """

    # =========================================================================
    # PARÁMETROS BASE PARA EL ESCENARIO RECOMENDADO
    # =========================================================================
    # Datos de horas pico (6pm-10pm, 4 horas):
    # - ~900 motos en horas pico
    # - ~130 mototaxis en horas pico
    # Las horas pico representan ~40% de la demanda diaria
    # Entonces el día completo tiene:
    # - Motos/día = 900 / 0.40 = 2,250 motos
    # - Mototaxis/día = 130 / 0.40 = 325 mototaxis

    MOTOS_PICO_RECOMENDADO = 900  # motos en 4 horas pico
    MOTOTAXIS_PICO_RECOMENDADO = 130  # mototaxis en 4 horas pico
    FACTOR_PICO = 0.40  # 4 horas pico = 40% de demanda diaria

    # Calcular vehículos totales del día para escenario RECOMENDADO
    motos_dia_rec = int(round(MOTOS_PICO_RECOMENDADO / FACTOR_PICO))  # ~2,250
    mototaxis_dia_rec = int(round(MOTOTAXIS_PICO_RECOMENDADO / FACTOR_PICO))  # ~325

    # Energía para escenario RECOMENDADO
    # Moto: 1 sesión = 1.0 kWh (30 min @ 2 kW)
    # Mototaxi: 1 sesión = 1.5 kWh (30 min @ 3 kW)
    energia_rec = motos_dia_rec * ENERGY_PER_SESSION_MOTO + mototaxis_dia_rec * ENERGY_PER_SESSION_MOTOTAXI
    # ~2,250 × 1.0 + ~325 × 1.5 = ~2,737.5 kWh/día

    print("\n[CÁLCULO CORREGIDO]")
    print(f"  Horas pico (6pm-10pm): ~{MOTOS_PICO_RECOMENDADO} motos + ~{MOTOTAXIS_PICO_RECOMENDADO} mototaxis")
    print(f"  Factor pico: {FACTOR_PICO:.0%} de demanda diaria")
    print(f"  Día completo: {motos_dia_rec:,} motos + {mototaxis_dia_rec:,} mototaxis = {motos_dia_rec + mototaxis_dia_rec:,} total")
    print(f"  Energía calculada: {energia_rec:,.0f} kWh/día")

    # Definir escenarios escalando desde RECOMENDADO con tipos explícitos
    escenarios: List[Dict[str, Any]] = [
        {
            "escenario": "CONSERVADOR",
            "PE": 0.10,
            "FC": 0.40,
            "cargadores": 4,
            "tomas": 16,
            "energia_dia_kwh": 92.80,
            "factor_vs_rec": 92.80 / 903.46,  # ~0.10
        },
        {
            "escenario": "MEDIANO",
            "PE": 0.50,
            "FC": 0.60,
            "cargadores": 20,
            "tomas": 80,
            "energia_dia_kwh": 835.20,
            "factor_vs_rec": 835.20 / 903.46,  # ~0.92
        },
        {
            "escenario": "RECOMENDADO*",
            "PE": 0.65,
            "FC": 0.75,
            "cargadores": 32,  # 28 motos + 4 mototaxis (configuración actual)
            "tomas": 128,
            "energia_dia_kwh": 903.46,
            "factor_vs_rec": 1.0,  # Escenario base
        },
        {
            "escenario": "MÁXIMO",
            "PE": 1.00,
            "FC": 1.00,
            "cargadores": 35,
            "tomas": 140,
            "energia_dia_kwh": 3252.00,
            "factor_vs_rec": 3252.00 / 903.46,  # ~3.6
        },
    ]

    results = []

    for esc in escenarios:
        factor = float(esc["factor_vs_rec"])

        # Escalar vehículos desde RECOMENDADO
        motos_dia = int(round(motos_dia_rec * factor))
        mototaxis_dia = int(round(mototaxis_dia_rec * factor))

        # Proyecciones mensual y anual
        motos_mes = motos_dia * DAYS_MONTH
        mototaxis_mes = mototaxis_dia * DAYS_MONTH

        motos_año = motos_dia * DAYS_YEAR
        mototaxis_año = mototaxis_dia * DAYS_YEAR

        results.append({
            "Escenario": esc["escenario"],
            "PE": esc["PE"],
            "FC": esc["FC"],
            "Cargadores": esc["cargadores"],
            "Tomas": esc["tomas"],
            "Energía/Día (kWh)": esc["energia_dia_kwh"],
            "Motos/Día": motos_dia,
            "Mototaxis/Día": mototaxis_dia,
            "Total/Día": motos_dia + mototaxis_dia,
            "Motos/Mes": motos_mes,
            "Mototaxis/Mes": mototaxis_mes,
            "Total/Mes": motos_mes + mototaxis_mes,
            "Motos/Año": motos_año,
            "Mototaxis/Año": mototaxis_año,
            "Total/Año": motos_año + mototaxis_año,
        })

    return pd.DataFrame(results)


def main():
    print("\n" + "="*100)
    print("TABLA 13 OE2 - ESCENARIOS DE DIMENSIONAMIENTO")
    print("Vehículos Cargados (Motos y Mototaxis)")
    print("="*100)

    # Mostrar configuración
    print("\n[CONFIGURACIÓN DE INFRAESTRUCTURA]")
    print(f"  Tomas Motos: {N_TOMAS_MOTOS} (28 cargadores × 4 tomas) @ {POTENCIA_MOTO_KW} kW")
    print(f"  Tomas Mototaxis: {N_TOMAS_MOTOTAXIS} (4 cargadores × 4 tomas) @ {POTENCIA_MOTOTAXI_KW} kW")
    print(f"  Total Tomas: {N_TOMAS_TOTAL}")
    print(f"  Potencia Total: {N_TOMAS_MOTOS * POTENCIA_MOTO_KW + N_TOMAS_MOTOTAXIS * POTENCIA_MOTOTAXI_KW} kW")

    print("\n[MODO DE CARGA]")
    print(f"  Sesión: {SESSION_MINUTES} minutos")
    print(f"  Energía/sesión Moto: {ENERGY_PER_SESSION_MOTO} kWh")
    print(f"  Energía/sesión Mototaxi: {ENERGY_PER_SESSION_MOTOTAXI} kWh")

    # Generar tabla de escenarios
    scenarios_df = generate_scenarios()

    # Mostrar tabla principal
    print("\n" + "-"*100)
    print("ESCENARIOS DE DIMENSIONAMIENTO - VEHÍCULOS CARGADOS")
    print("-"*100)

    # Tabla de escenarios con PE, FC, Cargadores, Tomas, Energía
    print("\n[TABLA 13 - ESCENARIOS]")
    print(f"{'Escenario':<15} {'PE':>6} {'FC':>6} {'Cargadores':>12} {'Tomas':>8} {'Energía/Día':>14}")
    print("-"*65)
    for _, row in scenarios_df.iterrows():
        print(f"{row['Escenario']:<15} {row['PE']:>6.2f} {row['FC']:>6.2f} "
              f"{row['Cargadores']:>12} {row['Tomas']:>8} {row['Energía/Día (kWh)']:>14,.2f}")

    # Tabla de vehículos por día
    print("\n[VEHÍCULOS CARGADOS POR DÍA]")
    print(f"{'Escenario':<15} {'Motos/Día':>12} {'Mototaxis/Día':>15} {'Total/Día':>12}")
    print("-"*58)
    for _, row in scenarios_df.iterrows():
        print(f"{row['Escenario']:<15} {row['Motos/Día']:>12,} {row['Mototaxis/Día']:>15,} {row['Total/Día']:>12,}")

    # Tabla de vehículos por mes
    print("\n[VEHÍCULOS CARGADOS POR MES]")
    print(f"{'Escenario':<15} {'Motos/Mes':>12} {'Mototaxis/Mes':>15} {'Total/Mes':>12}")
    print("-"*58)
    for _, row in scenarios_df.iterrows():
        print(f"{row['Escenario']:<15} {row['Motos/Mes']:>12,} {row['Mototaxis/Mes']:>15,} {row['Total/Mes']:>12,}")

    # Tabla de vehículos por año
    print("\n[VEHÍCULOS CARGADOS POR AÑO]")
    print(f"{'Escenario':<15} {'Motos/Año':>12} {'Mototaxis/Año':>15} {'Total/Año':>12}")
    print("-"*58)
    for _, row in scenarios_df.iterrows():
        print(f"{row['Escenario']:<15} {row['Motos/Año']:>12,} {row['Mototaxis/Año']:>15,} {row['Total/Año']:>12,}")

    # Resumen escenario RECOMENDADO
    rec = scenarios_df[scenarios_df["Escenario"] == "RECOMENDADO*"].iloc[0]

    print("\n" + "="*100)
    print("✅ ESCENARIO RECOMENDADO - PARA ENTRENAMIENTO OE3")
    print("="*100)
    print(f"""
    Configuración:
    - PE (Penetración): {rec['PE']:.0%}
    - FC (Factor Carga): {rec['FC']:.0%}
    - Cargadores: {rec['Cargadores']} (28 motos + 4 mototaxis)
    - Tomas: {rec['Tomas']} (112 motos + 16 mototaxis = 128 sockets en 32 cargadores)
    - Potencia Total: 272 kW

    Energía:
    - Energía/Día: {rec['Energía/Día (kWh)']:,.2f} kWh

    Vehículos Cargados:
    ┌─────────────┬────────────┬────────────────┬────────────┐
    │ Período     │ Motos      │ Mototaxis      │ Total      │
    ├─────────────┼────────────┼────────────────┼────────────┤
    │ Día         │ {rec['Motos/Día']:>10,} │ {rec['Mototaxis/Día']:>14,} │ {rec['Total/Día']:>10,} │
    │ Mes         │ {rec['Motos/Mes']:>10,} │ {rec['Mototaxis/Mes']:>14,} │ {rec['Total/Mes']:>10,} │
    │ Año         │ {rec['Motos/Año']:>10,} │ {rec['Mototaxis/Año']:>14,} │ {rec['Total/Año']:>10,} │
    └─────────────┴────────────┴────────────────┴────────────┘
    """)

    # Guardar CSV
    output_dir = Path("data/oe2")
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "tabla_escenarios_vehiculos.csv"
    scenarios_df.to_csv(csv_path, index=False)
    print(f"\n✅ Tabla guardada en: {csv_path}")

    return scenarios_df


if __name__ == "__main__":
    main()
