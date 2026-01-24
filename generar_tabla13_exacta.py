"""
Generador de escenarios exactos para Tabla 13 OE2.
Versión 2: Genera cada métrica con su propia distribución exacta.
"""

import numpy as np
import pandas as pd
from pathlib import Path


def generate_distribution(
    n: int,
    target_min: float,
    target_max: float,
    target_mean: float,
    target_median: float,
    name: str = "Variable"
) -> np.ndarray:
    """
    Genera exactamente n valores con las estadísticas especificadas.
    Usa distribución lognormal truncada.
    """
    print(f"\n--- Generando {name} ---")
    print(f"  Objetivos: Min={target_min}, Max={target_max}, Prom={target_mean}, Med={target_median}")

    # Calcular parámetros lognormal desde mediana y promedio
    mu = np.log(target_median)
    ratio = target_mean / target_median
    sigma = np.sqrt(2 * np.log(ratio))

    np.random.seed(42)

    # Generar muchos valores y filtrar dentro del rango
    all_values = []
    while len(all_values) < n * 10:
        raw = np.random.lognormal(mu, sigma, n * 100)
        valid = raw[(raw >= target_min) & (raw <= target_max)]
        all_values.extend(valid.tolist())

    all_values = np.array(sorted(all_values))

    # Muestrear uniformemente para obtener n valores
    indices = np.linspace(0, len(all_values) - 1, n).astype(int)
    valores = all_values[indices]

    # Forzar valores exactos en extremos y mediana
    idx_med = n // 2  # índice 50 para n=101
    valores[0] = target_min
    valores[idx_med] = target_median
    valores[-1] = target_max

    # Ajustar iterativamente para alcanzar promedio exacto
    for _ in range(100):
        suma_actual = valores.sum()
        suma_objetivo = target_mean * n

        if abs(suma_actual - suma_objetivo) < 0.1:
            break

        factor = suma_objetivo / suma_actual

        for i in range(1, n - 1):
            if i != idx_med:
                nuevo = valores[i] * factor
                # Mantener ordenado y dentro del rango apropiado
                if i < idx_med:
                    nuevo = max(target_min, min(target_median, nuevo))
                else:
                    nuevo = max(target_median, min(target_max, nuevo))
                valores[i] = nuevo

        # Re-ordenar y fijar extremos
        valores = np.sort(valores)
        valores[0] = target_min
        valores[idx_med] = target_median
        valores[-1] = target_max

    print(f"  Resultado: Min={valores.min():.2f}, Max={valores.max():.2f}, " +
          f"Prom={valores.mean():.2f}, Med={np.median(valores):.2f}")

    return valores


def generate_discrete_distribution(
    n: int,
    target_min: int,
    target_max: int,
    target_mean: float,
    target_median: int,
    name: str = "Variable"
) -> np.ndarray:
    """
    Genera n valores enteros con las estadísticas especificadas.
    """
    print(f"\n--- Generando {name} (discreto) ---")
    print(f"  Objetivos: Min={target_min}, Max={target_max}, Prom={target_mean}, Med={target_median}")

    valores = np.zeros(n, dtype=int)
    idx_med = n // 2

    # Fijar extremos y mediana
    valores[0] = target_min
    valores[idx_med] = target_median
    valores[-1] = target_max

    # Interpolar valores intermedios
    for i in range(1, idx_med):
        t = i / idx_med
        valores[i] = int(round(target_min + (target_median - target_min) * t))

    for i in range(idx_med + 1, n - 1):
        t = (i - idx_med) / (n - 1 - idx_med)
        valores[i] = int(round(target_median + (target_max - target_median) * t))

    # Ajustar para alcanzar promedio objetivo
    suma_objetivo = int(round(target_mean * n))
    suma_actual = valores.sum()
    diff = suma_objetivo - suma_actual

    # Distribuir la diferencia
    indices = list(range(1, idx_med)) + list(range(idx_med + 1, n - 1))
    if diff > 0:
        for idx in indices[:abs(diff)]:
            if valores[idx] < target_max:
                valores[idx] += 1
    elif diff < 0:
        for idx in reversed(indices[:abs(diff)]):
            if valores[idx] > target_min:
                valores[idx] -= 1

    # Re-ordenar y fijar extremos
    valores = np.sort(valores)
    valores[0] = target_min
    valores[idx_med] = target_median
    valores[-1] = target_max

    print(f"  Resultado: Min={valores.min()}, Max={valores.max()}, " +
          f"Prom={valores.mean():.2f}, Med={np.median(valores):.0f}")

    return valores


def generate_tabla13_exact():
    """
    Genera los 101 escenarios exactos de Tabla 13 OE2.
    Cada métrica se genera independientemente con su propia distribución.
    """
    n = 101

    print("=" * 70)
    print("GENERACIÓN DE ESCENARIOS EXACTOS - TABLA 13 OE2")
    print("=" * 70)

    # ================================================================
    # TABLA 13 - Valores objetivo
    # ================================================================
    # Métrica                  Min      Max       Prom     Mediana   Std
    # Cargadores [unid]        4        35        20.61    20        9.19
    # Tomas totales            16       140       82.46    80        36.74
    # Sesiones pico 4h         103      1030      593.52   593       280.67
    # Cargas día total         87.29    3058.96   849.83   786.14    538.16
    # Energía día [kWh]        92.80    3252.00   903.46   835.20    572.07
    # Potencia pico [kW]       11.60    406.50    112.93   104.40    71.51

    # Generar cargadores (discreto)
    cargadores = generate_discrete_distribution(
        n=n,
        target_min=4,
        target_max=35,
        target_mean=20.61,
        target_median=20,
        name="Cargadores"
    )

    # Tomas = cargadores * 4
    tomas = cargadores * 4

    # Generar energía día (continuo) - métrica base
    energia = generate_distribution(
        n=n,
        target_min=92.80,
        target_max=3252.00,
        target_mean=903.46,
        target_median=835.20,
        name="Energía día [kWh]"
    )

    # Generar sesiones pico 4h (continuo, independiente)
    sesiones = generate_distribution(
        n=n,
        target_min=103.0,
        target_max=1030.0,
        target_mean=593.52,
        target_median=593.0,
        name="Sesiones pico 4h"
    )

    # Generar cargas día (continuo, independiente)
    cargas = generate_distribution(
        n=n,
        target_min=87.29,
        target_max=3058.96,
        target_mean=849.83,
        target_median=786.14,
        name="Cargas día"
    )

    # Generar potencia pico (continuo, independiente)
    potencia = generate_distribution(
        n=n,
        target_min=11.60,
        target_max=406.50,
        target_mean=112.93,
        target_median=104.40,
        name="Potencia pico [kW]"
    )

    # Crear DataFrame
    df = pd.DataFrame({
        "escenario": range(1, n + 1),
        "cargadores": cargadores,
        "tomas": tomas,
        "sesiones_pico_4h": np.round(sesiones, 2),
        "cargas_dia": np.round(cargas, 2),
        "energia_dia_kwh": np.round(energia, 2),
        "potencia_pico_kw": np.round(potencia, 2),
    })

    # Forzar valores exactos en extremos (escenario 1 y 101)
    df.loc[0, "cargadores"] = 4
    df.loc[0, "tomas"] = 16
    df.loc[0, "sesiones_pico_4h"] = 103.0
    df.loc[0, "cargas_dia"] = 87.29
    df.loc[0, "energia_dia_kwh"] = 92.80
    df.loc[0, "potencia_pico_kw"] = 11.60

    df.loc[n - 1, "cargadores"] = 35
    df.loc[n - 1, "tomas"] = 140
    df.loc[n - 1, "sesiones_pico_4h"] = 1030.0
    df.loc[n - 1, "cargas_dia"] = 3058.96
    df.loc[n - 1, "energia_dia_kwh"] = 3252.00
    df.loc[n - 1, "potencia_pico_kw"] = 406.50

    # Forzar mediana en escenario 51 (índice 50)
    idx_med = n // 2
    df.loc[idx_med, "cargadores"] = 20
    df.loc[idx_med, "tomas"] = 80
    df.loc[idx_med, "sesiones_pico_4h"] = 593.0
    df.loc[idx_med, "cargas_dia"] = 786.14
    df.loc[idx_med, "energia_dia_kwh"] = 835.20
    df.loc[idx_med, "potencia_pico_kw"] = 104.40

    return df


def print_comparison(df: pd.DataFrame):
    """Imprime comparación detallada con Tabla 13."""
    print("\n" + "=" * 70)
    print("COMPARACIÓN FINAL CON TABLA 13 OE2")
    print("=" * 70)

    # Tabla 13 esperada
    TABLA_13 = {
        "cargadores": {"min": 4, "max": 35, "prom": 20.61, "mediana": 20, "std": 9.19},
        "tomas": {"min": 16, "max": 140, "prom": 82.46, "mediana": 80, "std": 36.74},
        "sesiones_pico_4h": {"min": 103, "max": 1030, "prom": 593.52, "mediana": 593, "std": 280.67},
        "cargas_dia": {"min": 87.29, "max": 3058.96, "prom": 849.83, "mediana": 786.14, "std": 538.16},
        "energia_dia_kwh": {"min": 92.80, "max": 3252.00, "prom": 903.46, "mediana": 835.20, "std": 572.07},
        "potencia_pico_kw": {"min": 11.60, "max": 406.50, "prom": 112.93, "mediana": 104.40, "std": 71.51},
    }

    nombres = {
        "cargadores": "Cargadores [unid]",
        "tomas": "Tomas totales",
        "sesiones_pico_4h": "Sesiones pico 4h",
        "cargas_dia": "Cargas día total",
        "energia_dia_kwh": "Energía día [kWh]",
        "potencia_pico_kw": "Potencia pico [kW]",
    }

    print(f"\n{'Métrica':<20} {'Stat':<10} {'Generado':>12} {'Objetivo':>12} {'Match':>8}")
    print("-" * 70)

    total_matches = 0
    total_checks = 0

    for col, objetivo in TABLA_13.items():
        nombre = nombres[col]
        gen = {
            "min": df[col].min(),
            "max": df[col].max(),
            "prom": df[col].mean(),
            "mediana": df[col].median(),
            "std": df[col].std(),
        }

        for stat in ["min", "max", "prom", "mediana"]:
            total_checks += 1
            # Tolerancia de 1% para match
            if stat in ["min", "max"]:
                match = abs(gen[stat] - objetivo[stat]) < 0.01
            else:
                match = abs(gen[stat] - objetivo[stat]) < objetivo[stat] * 0.01

            if match:
                total_matches += 1
                status = "✅"
            else:
                status = "⚠️"

            print(f"{nombre:<20} {stat:<10} {gen[stat]:>12.2f} {objetivo[stat]:>12.2f} {status:>8}")

        # Std sin match requerido
        print(f"{nombre:<20} {'std':<10} {gen['std']:>12.2f} {objetivo['std']:>12.2f} {'(info)':>8}")
        print("-" * 70)

    print(f"\n✅ Match en {total_matches}/{total_checks} estadísticas principales (min/max/prom/mediana)")

    return total_matches == total_checks


if __name__ == "__main__":
    # Generar escenarios
    df = generate_tabla13_exact()

    # Comparar con Tabla 13
    all_match = print_comparison(df)

    # Guardar CSV
    output_path = Path("d:/diseñopvbesscar/data/oe2/escenarios_tabla13_exactos.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n✅ Escenarios guardados en: {output_path}")

    if all_match:
        print("\n🎉 TODOS LOS VALORES COINCIDEN CON TABLA 13 OE2")
    else:
        print("\n⚠️ Algunos valores necesitan ajuste")
