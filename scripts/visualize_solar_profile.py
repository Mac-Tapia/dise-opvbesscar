"""
Script para visualizar el perfil de generación solar 2024.

Genera gráficos para análisis de:
1. Patrón horario promedio
2. Variación mensual
3. Distribución de potencia
4. Ciclo diario
5. Relación radiación-potencia
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# Configuración de matplotlib
plt.style.use("seaborn-v0_8-darkgrid")
plt.rcParams["figure.figsize"] = (16, 12)
plt.rcParams["font.size"] = 10

def load_solar_data() -> pd.DataFrame:
    """Carga datos de generación solar."""
    csv_path = Path("data/oe2/Generacionsolar/solar_generation_profile_2024.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {csv_path}")
    return pd.read_csv(csv_path)

def create_visualizations(df: pd.DataFrame) -> None:
    """Crea visualizaciones principales."""

    # Preparar datos
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["mes"] = df["fecha"].dt.month.astype('int64')
    df["dia_semana"] = df["fecha"].dt.day_name().astype('str')
    df["semana_ano"] = df["fecha"].dt.isocalendar().week.astype('int64')

    # Crear figura con subplots
    fig = plt.figure(figsize=(18, 14))

    # ====================================================================
    # 1. PATRÓN HORARIO PROMEDIO (Perfil diario típico)
    # ====================================================================
    ax1 = plt.subplot(3, 3, 1)
    hourly_mean = df.groupby("hora")["potencia_kw"].mean()
    hourly_std = df.groupby("hora")["potencia_kw"].std()
    x_vals = np.asarray(hourly_mean.index, dtype=np.float64)
    y_vals = np.asarray(hourly_mean.values, dtype=np.float64)
    y_std_lower = np.asarray((hourly_mean - hourly_std).values, dtype=np.float64)
    y_std_upper = np.asarray((hourly_mean + hourly_std).values, dtype=np.float64)
    ax1.plot(x_vals, y_vals, "b-o", linewidth=2, markersize=6, label="Promedio")
    ax1.fill_between(x_vals, y_std_lower, y_std_upper, alpha=0.3, label="±1 Desv. Est.")
    ax1.set_xlabel("Hora del Día", fontweight="bold")
    ax1.set_ylabel("Potencia (kW)", fontweight="bold")
    ax1.set_title("1. Patrón Horario Promedio 2024", fontweight="bold", fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_xticks(range(0, 24, 2))

    # ====================================================================
    # 2. GENERACIÓN MENSUAL (Total y promedio)
    # ====================================================================
    ax2 = plt.subplot(3, 3, 2)
    monthly_energy = df.groupby("mes")["energia_kwh"].sum() / 1000  # Convertir a MWh
    months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    cmap = plt.get_cmap('RdYlGn')
    colors = cmap(np.linspace(0.3, 0.9, 12))
    heights = np.asarray(monthly_energy.values, dtype=np.float64)
    ax2.bar(range(1, 13), heights, color=colors, edgecolor="black", linewidth=1.5)
    ax2.set_xlabel("Mes", fontweight="bold")
    ax2.set_ylabel("Energía (MWh)", fontweight="bold")
    ax2.set_title("2. Generación Mensual Total", fontweight="bold", fontsize=11)
    ax2.set_xticks(range(1, 13))
    ax2.set_xticklabels(months, rotation=45)
    ax2.grid(True, alpha=0.3, axis="y")

    # Agregar valores en barras
    for i, v in enumerate(monthly_energy.values):
        ax2.text(i+1, v+2, f"{v:.0f}", ha="center", va="bottom", fontsize=8)

    # ====================================================================
    # 3. DISTRIBUCIÓN DE POTENCIA (Histograma)
    # ====================================================================
    ax3 = plt.subplot(3, 3, 3)
    ax3.hist(df["potencia_kw"], bins=50, color="steelblue", edgecolor="black", alpha=0.7)
    ax3.axvline(df["potencia_kw"].mean(), color="red", linestyle="--", linewidth=2, label=f"Promedio: {df['potencia_kw'].mean():.0f} kW")
    ax3.axvline(df["potencia_kw"].median(), color="green", linestyle="--", linewidth=2, label=f"Mediana: {df['potencia_kw'].median():.0f} kW")
    ax3.set_xlabel("Potencia (kW)", fontweight="bold")
    ax3.set_ylabel("Frecuencia (horas)", fontweight="bold")
    ax3.set_title("3. Distribución de Potencia", fontweight="bold", fontsize=11)
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis="y")

    # ====================================================================
    # 4. HEATMAP: POTENCIA POR HORA Y MES
    # ====================================================================
    ax4 = plt.subplot(3, 3, 4)
    pivot_hourly_monthly = df.pivot_table(values="potencia_kw", index="hora", columns="mes", aggfunc="mean")
    im = ax4.imshow(pivot_hourly_monthly.values, aspect="auto", cmap="YlOrRd", interpolation="nearest")
    ax4.set_xlabel("Mes", fontweight="bold")
    ax4.set_ylabel("Hora del Día", fontweight="bold")
    ax4.set_title("4. Heatmap: Potencia (kW) por Hora y Mes", fontweight="bold", fontsize=11)
    ax4.set_xticks(range(12))
    ax4.set_xticklabels(months, rotation=45)
    ax4.set_yticks(range(0, 24, 2))
    cbar = plt.colorbar(im, ax=ax4)
    cbar.set_label("Potencia (kW)", fontweight="bold")

    # ====================================================================
    # 5. RELACIÓN IRRADIANCIA vs POTENCIA
    # ====================================================================
    ax5 = plt.subplot(3, 3, 5)
    x_irrad = np.asarray(df["irradiancia_ghi"].values, dtype=np.float64)
    y_power = np.asarray(df["potencia_kw"].values, dtype=np.float64)
    c_temp = df["temperatura_c"].values.tolist()  # Convertir a lista de Python
    scatter = ax5.scatter(x_irrad, y_power, c=c_temp, cmap="coolwarm", alpha=0.5, s=10)
    ax5.set_xlabel("Irradiancia GHI (W/m²)", fontweight="bold")
    ax5.set_ylabel("Potencia (kW)", fontweight="bold")
    ax5.set_title("5. Relación Irradiancia vs Potencia\n(color: temperatura)", fontweight="bold", fontsize=11)
    ax5.grid(True, alpha=0.3)
    cbar = plt.colorbar(scatter, ax=ax5)
    cbar.set_label("Temperatura (°C)", fontweight="bold")

    # ====================================================================
    # 6. TEMPERATURA AMBIENTE HORARIA
    # ====================================================================
    ax6 = plt.subplot(3, 3, 6)
    temp_hourly_mean = df.groupby("hora")["temperatura_c"].mean()
    temp_hourly_std = df.groupby("hora")["temperatura_c"].std()
    x_temp = np.asarray(temp_hourly_mean.index, dtype=np.float64)
    y_temp = np.asarray(temp_hourly_mean.values, dtype=np.float64)
    y_temp_lower = np.asarray((temp_hourly_mean - temp_hourly_std).values, dtype=np.float64)
    y_temp_upper = np.asarray((temp_hourly_mean + temp_hourly_std).values, dtype=np.float64)
    ax6.plot(x_temp, y_temp, "r-o", linewidth=2, markersize=6)
    ax6.fill_between(x_temp, y_temp_lower, y_temp_upper, alpha=0.3, color="red")
    ax6.set_xlabel("Hora del Día", fontweight="bold")
    ax6.set_ylabel("Temperatura (°C)", fontweight="bold")
    ax6.set_title("6. Patrón Horario Temperatura", fontweight="bold", fontsize=11)
    ax6.grid(True, alpha=0.3)
    ax6.set_xticks(range(0, 24, 2))

    # ====================================================================
    # 7. ENERGÍA ACUMULADA (Cumulative)
    # ====================================================================
    ax7 = plt.subplot(3, 3, 7)
    cumsum = df["energia_kwh"].cumsum() / 1000  # MWh
    x_cumsum = np.arange(len(cumsum), dtype=np.float64)
    y_cumsum = np.asarray(cumsum.values, dtype=np.float64)
    ax7.fill_between(x_cumsum, y_cumsum, alpha=0.3, color="green")
    ax7.plot(x_cumsum, y_cumsum, "g-", linewidth=2)
    ax7.set_xlabel("Día del Año", fontweight="bold")
    ax7.set_ylabel("Energía Acumulada (MWh)", fontweight="bold")
    ax7.set_title("7. Generación Acumulada 2024", fontweight="bold", fontsize=11)
    ax7.grid(True, alpha=0.3)

    # Anotación del total
    total_energy = cumsum.iloc[-1]
    ax7.text(len(cumsum)-1000, total_energy*0.5, f"Total: {total_energy:.0f} MWh",
             fontsize=11, bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
             fontweight="bold")

    # ====================================================================
    # 8. VELOCIDAD DEL VIENTO HORARIA
    # ====================================================================
    ax8 = plt.subplot(3, 3, 8)
    wind_hourly = df.groupby("hora")["velocidad_viento_ms"].mean()
    x_wind = np.asarray(wind_hourly.index, dtype=np.float64)
    y_wind = np.asarray(wind_hourly.values, dtype=np.float64)
    ax8.bar(x_wind, y_wind, color="skyblue", edgecolor="navy", linewidth=1.5)
    ax8.set_xlabel("Hora del Día", fontweight="bold")
    ax8.set_ylabel("Velocidad Viento (m/s)", fontweight="bold")
    ax8.set_title("8. Patrón Horario Velocidad Viento", fontweight="bold", fontsize=11)
    ax8.grid(True, alpha=0.3, axis="y")
    ax8.set_xticks(range(0, 24, 2))

    # ====================================================================
    # 9. ESTADÍSTICAS RESUMIDAS (Tabla)
    # ====================================================================
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis("off")

    stats_text = f"""
ESTADÍSTICAS RESUMIDAS - 2024

Ubicación: Iquitos, Perú (3.74°S, 73.27°W)
Capacidad: 4,050 kWp

IRRADIANCIA (W/m²)
  • Promedio: {df['irradiancia_ghi'].mean():.2f}
  • Máximo: {df['irradiancia_ghi'].max():.2f}
  • Mínimo: {df['irradiancia_ghi'].min():.2f}

POTENCIA (kW)
  • Promedio: {df['potencia_kw'].mean():.2f}
  • Máximo: {df['potencia_kw'].max():.2f}
  • Factor de carga: {df['potencia_kw'].mean()/4050*100:.1f}%

ENERGÍA (kWh)
  • Total anual: {df['energia_kwh'].sum():,.0f}
  • Por día (promedio): {df['energia_kwh'].sum()/365:,.0f}
  • Factor de capacidad: {df['energia_kwh'].sum()/365/4050*100:.1f}%

TEMPERATURA (°C)
  • Promedio: {df['temperatura_c'].mean():.2f}
  • Máximo: {df['temperatura_c'].max():.2f}
  • Mínimo: {df['temperatura_c'].min():.2f}

VIENTO (m/s)
  • Promedio: {df['velocidad_viento_ms'].mean():.2f}
  • Máximo: {df['velocidad_viento_ms'].max():.2f}
"""

    ax9.text(0.05, 0.95, stats_text, transform=ax9.transAxes,
            fontsize=9, verticalalignment="top", fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

    plt.tight_layout()

    # Guardar figura
    output_path = Path("data/oe2/Generacionsolar/solar_profile_visualization_2024.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"✅ Visualización guardada: {output_path}")

    plt.show()

def main():
    """Función principal."""
    print("📊 Generando visualizaciones de generación solar...")
    df = load_solar_data()
    create_visualizations(df)
    print("✅ Proceso completado")

if __name__ == "__main__":
    main()
