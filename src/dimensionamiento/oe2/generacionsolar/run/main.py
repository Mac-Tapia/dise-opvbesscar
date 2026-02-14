"""
Análisis y Consultas de Generación Solar - Iquitos 2024

Script principal para:
- Cargar datos de generación solar horaria
- Análisis diario, mensual y anual
- Identificar días representativos (despejado, nublado, templado)
- Generar gráficas relevantes
- Mostrar estadísticas detalladas

Uso:
    python main.py [--show-plots] [--output-dir <dir>]
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import argparse
from datetime import datetime

import pandas as pd
import numpy as np

# Intentar importar matplotlib para gráficas
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None  # type: ignore


class SolarGenerationAnalyzer:
    """Analizador de generación solar para Iquitos 2024."""

    def __init__(self, csv_path: Path):
        """Inicializar con ruta al archivo CSV de generación solar.

        Args:
            csv_path: Ruta al archivo CSV con datos de generación solar
        """
        self.csv_path = csv_path
        self.df: Optional[pd.DataFrame] = None
        self.daily_energy: Optional[pd.Series] = None
        self.monthly_energy: Optional[pd.Series] = None
        self.annual_energy: float = 0.0

        # Cargar datos
        self._load_data()

    def _load_data(self) -> None:
        """Cargar datos desde el CSV."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {self.csv_path}")

        print(f"📂 Cargando datos desde: {self.csv_path}")
        self.df = pd.read_csv(self.csv_path)

        # Convertir datetime/timestamp a índice si es necesario
        if 'datetime' in self.df.columns:
            self.df['datetime'] = pd.to_datetime(self.df['datetime'])
            self.df.set_index('datetime', inplace=True)
        elif 'timestamp' in self.df.columns:
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
            self.df.set_index('timestamp', inplace=True)

        # Calcular energía por hora a partir de potencia (kW × 1 hora = kWh)
        # Si existe 'ac_energy_kwh', usarla; si no, calcularla desde 'ac_power_kw'
        if 'ac_energy_kwh' not in self.df.columns:
            if 'ac_power_kw' in self.df.columns:
                self.df['ac_energy_kwh'] = self.df['ac_power_kw'] * 1.0  # 1 hora de operación
            else:
                raise ValueError("El CSV debe contener 'ac_power_kw' o 'ac_energy_kwh'")

        """Obtener resumen anual completo."""
        if self.df is None:
            raise ValueError("No hay datos cargados")

        return {
            "energia_anual_kwh": self.annual_energy,
            "energia_anual_mwh": self.annual_energy / 1000.0,
            "energia_anual_gwh": self.annual_energy / 1e6,
            "potencia_promedio_kw": self.df['ac_power_kw'].mean(),
            "potencia_maxima_kw": self.df['ac_power_kw'].max(),
            "potencia_minima_kw": self.df['ac_power_kw'].min(),
            "temperatura_promedio_c": self.df['temp_air_c'].mean(),
            "temperatura_maxima_c": self.df['temp_air_c'].max(),
            "temperatura_minima_c": self.df['temp_air_c'].min(),
            "irradiancia_promedio_wm2": self.df['ghi_wm2'].mean(),
            "irradiancia_maxima_wm2": self.df['ghi_wm2'].max(),
        }

    def get_monthly_summary(self) -> pd.DataFrame:
        """Obtener resumen mensual."""
        if self.df is None:
            raise ValueError("No hay datos cargados")

        months = []
        month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                      "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        for month_num in range(1, 13):
            month_mask = self.df.index.month == month_num
            month_data = self.df[month_mask]

            if len(month_data) > 0:
                months.append({
                    'Mes': month_names[month_num - 1],
                    'Num': month_num,
                    'Energia_kWh': month_data['ac_energy_kwh'].sum(),
                    'Potencia_Promedio_kW': month_data['ac_power_kw'].mean(),
                    'Potencia_Maxima_kW': month_data['ac_power_kw'].max(),
                    'Temperatura_Promedio_C': month_data['temp_air_c'].mean(),
                    'Irradiancia_Promedio_Wm2': month_data['ghi_wm2'].mean(),
                    'Dias': (month_data.index.max() - month_data.index.min()).days + 1,
                })

        return pd.DataFrame(months)

    def get_daily_summary(self) -> pd.DataFrame:
        """Obtener resumen diario."""
        if self.df is None:
            raise ValueError("No hay datos cargados")

        daily_stats = self.df.groupby(self.df.index.date).agg({
            'ac_energy_kwh': 'sum',
            'ac_power_kw': ['mean', 'max'],
            'temp_air_c': ['mean', 'max', 'min'],
            'ghi_wm2': ['mean', 'max'],
        }).round(2)

        daily_stats.columns = ['Energia_kWh', 'Potencia_Promedio_kW', 'Potencia_Maxima_kW',
                               'Temp_Promedio_C', 'Temp_Maxima_C', 'Temp_Minima_C',
                               'Irradiancia_Promedio_Wm2', 'Irradiancia_Maxima_Wm2']

        return daily_stats.reset_index().rename(columns={'timestamp': 'Fecha'})

    # =========================================================================
    # DÍAS REPRESENTATIVOS
    # =========================================================================

    def find_representative_days(self) -> dict[str, dict[str, Any]]:
        """Encontrar días representativos: despejado, nublado, templado."""
        if self.daily_energy is None:
            raise ValueError("No hay datos de energía diaria calculados")

        # Día más despejado: máxima energía
        idx_max = self.daily_energy.idxmax()
        max_energy = self.daily_energy.max()

        # Día más nublado: mínima energía
        idx_min = self.daily_energy.idxmin()
        min_energy = self.daily_energy.min()

        # Día templado: energía más cercana a la mediana
        median_energy = self.daily_energy.median()
        idx_median = (self.daily_energy - median_energy).abs().idxmin()
        median_value = self.daily_energy[idx_median]

        return {
            'despejado': {
                'fecha': idx_max,
                'energia_kwh': float(max_energy),
                'tipo': 'Día más despejado (máxima generación)',
            },
            'nublado': {
                'fecha': idx_min,
                'energia_kwh': float(min_energy),
                'tipo': 'Día más nublado (mínima generación)',
            },
            'templado': {
                'fecha': idx_median,
                'energia_kwh': float(median_value),
                'tipo': 'Día templado (energía mediana)',
            },
        }

    def get_day_profile(self, date: pd.Timestamp) -> pd.DataFrame:
        """Obtener perfil horario de un día específico."""
        if self.df is None:
            raise ValueError("No hay datos cargados")

        day_data = self.df[self.df.index.date == date.date()]

        if len(day_data) == 0:
            return pd.DataFrame()

        return day_data[['ac_energy_kwh', 'ac_power_kw', 'temp_air_c', 'ghi_wm2']].reset_index()

    # =========================================================================
    # ESTADÍSTICAS DETALLADAS
    # =========================================================================

    def get_temperature_analysis(self) -> dict[str, float]:
        """Análisis detallado de temperatura."""
        if self.df is None:
            raise ValueError("No hay datos cargados")

        temps = self.df['temp_air_c']

        return {
            'promedio': float(temps.mean()),
            'mediana': float(temps.median()),
            'max': float(temps.max()),
            'min': float(temps.min()),
            'std': float(temps.std()),
            'q25': float(temps.quantile(0.25)),
            'q75': float(temps.quantile(0.75)),
        }

    def get_irradiance_analysis(self) -> dict[str, float]:
        """Análisis detallado de irradiancia."""
        if self.df is None:
            raise ValueError("No hay datos cargados")

        ghi = self.df['ghi_wm2']

        return {
            'promedio': float(ghi.mean()),
            'mediana': float(ghi.median()),
            'max': float(ghi.max()),
            'min': float(ghi.min()),
            'std': float(ghi.std()),
            'q25': float(ghi.quantile(0.25)),
            'q75': float(ghi.quantile(0.75)),
        }

    def get_power_analysis(self) -> dict[str, float]:
        """Análisis detallado de potencia."""
        if self.df is None:
            raise ValueError("No hay datos cargados")

        power = self.df['ac_power_kw']

        return {
            'promedio': float(power.mean()),
            'mediana': float(power.median()),
            'max': float(power.max()),
            'min': float(power.min()),
            'std': float(power.std()),
            'q25': float(power.quantile(0.25)),
            'q75': float(power.quantile(0.75)),
        }

    # =========================================================================
    # GRÁFICAS
    # =========================================================================

    def plot_all(self, output_dir: Optional[Path] = None) -> None:
        """Generar todas las gráficas relevantes."""
        if not MATPLOTLIB_AVAILABLE:
            print("⚠️  Matplotlib no disponible, saltando gráficas")
            return

        if output_dir is None:
            output_dir = Path("data/oe2/Generacionsolar/graficas")

        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📊 Generando gráficas en: {output_dir}")

        # 1. Energía mensual
        self._plot_monthly_energy(output_dir)

        # 2. Energía diaria
        self._plot_daily_energy(output_dir)

        # 3. Perfil horario promedio
        self._plot_hourly_profile(output_dir)

        # 4. Temperatura mensual
        self._plot_monthly_temperature(output_dir)

        # 5. Irradiancia mensual
        self._plot_monthly_irradiance(output_dir)

        # 6. Distribución de potencia
        self._plot_power_distribution(output_dir)

        # 7. Series temporales mensual
        self._plot_monthly_timeseries(output_dir)

        # 8. Correlación temperatura vs potencia
        self._plot_temp_power_correlation(output_dir)

        print("✓ Todas las gráficas generadas exitosamente")

    def _plot_monthly_energy(self, output_dir: Path) -> None:
        """Gráfica de energía mensual."""
        fig, ax = plt.subplots(figsize=(12, 6))

        months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        energies = [self.monthly_energy.iloc[i] if i < len(self.monthly_energy) else 0
                   for i in range(12)]

        bars = ax.bar(months, energies, color='forestgreen', edgecolor='darkgreen', alpha=0.8)

        # Añadir valores en barras
        for bar, energy in zip(bars, energies):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{energy/1e3:.0f}k',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')

        ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
        ax.set_ylabel('Energía (kWh)', fontsize=11, fontweight='bold')
        ax.set_title('Energía Generada por Mes - 2024', fontsize=13, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, max(energies) * 1.15 if max(energies) > 0 else 100)

        plt.tight_layout()
        plt.savefig(output_dir / 'energia_mensual.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ energia_mensual.png")

    def _plot_daily_energy(self, output_dir: Path) -> None:
        """Gráfica de energía diaria."""
        fig, ax = plt.subplots(figsize=(14, 5))

        ax.plot(self.daily_energy.index, self.daily_energy.values,
               color='navy', linewidth=1.5, alpha=0.8)
        ax.fill_between(self.daily_energy.index, self.daily_energy.values,
                       alpha=0.3, color='skyblue')

        ax.axhline(y=self.daily_energy.mean(), color='red', linestyle='--',
                  linewidth=2, label=f'Promedio: {self.daily_energy.mean():.0f} kWh')

        ax.set_xlabel('Fecha', fontsize=11, fontweight='bold')
        ax.set_ylabel('Energía (kWh)', fontsize=11, fontweight='bold')
        ax.set_title('Energía Generada Diaria - 2024', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / 'energia_diaria.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ energia_diaria.png")

    def _plot_hourly_profile(self, output_dir: Path) -> None:
        """Gráfica de perfil horario promedio."""
        if self.df is None:
            return

        hourly_avg = self.df['ac_power_kw'].groupby(self.df.index.hour).mean()

        fig, ax = plt.subplots(figsize=(12, 6))

        hours = hourly_avg.index
        ax.bar(hours, hourly_avg.values, color='coral', edgecolor='darkorange', alpha=0.8)

        ax.set_xlabel('Hora del Día', fontsize=11, fontweight='bold')
        ax.set_ylabel('Potencia Promedio (kW)', fontsize=11, fontweight='bold')
        ax.set_title('Perfil Horario Promedio de Potencia - 2024', fontsize=13, fontweight='bold')
        ax.set_xticks(range(0, 24, 2))
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / 'perfil_horario.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ perfil_horario.png")

    def _plot_monthly_temperature(self, output_dir: Path) -> None:
        """Gráfica de temperatura mensual."""
        if self.df is None:
            return

        monthly_temp = self.df['temp_air_c'].resample('ME').mean()

        fig, ax = plt.subplots(figsize=(12, 6))

        months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        temps = [monthly_temp.iloc[i] if i < len(monthly_temp) else 0 for i in range(12)]

        ax.plot(months, temps, marker='o', linewidth=2.5, markersize=8, color='red')
        ax.fill_between(range(len(months)), temps, alpha=0.3, color='red')

        ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
        ax.set_ylabel('Temperatura (°C)', fontsize=11, fontweight='bold')
        ax.set_title('Temperatura Promedio por Mes - 2024', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(20, 30)

        plt.tight_layout()
        plt.savefig(output_dir / 'temperatura_mensual.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ temperatura_mensual.png")

    def _plot_monthly_irradiance(self, output_dir: Path) -> None:
        """Gráfica de irradiancia mensual."""
        if self.df is None:
            return

        monthly_irr = self.df['ghi_wm2'].resample('ME').mean()

        fig, ax = plt.subplots(figsize=(12, 6))

        months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        irrs = [monthly_irr.iloc[i] if i < len(monthly_irr) else 0 for i in range(12)]

        bars = ax.bar(months, irrs, color='gold', edgecolor='orange', alpha=0.8)

        for bar, irr in zip(bars, irrs):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{irr:.0f}', ha='center', va='bottom', fontsize=9)

        ax.set_xlabel('Mes', fontsize=11, fontweight='bold')
        ax.set_ylabel('Irradiancia (W/m²)', fontsize=11, fontweight='bold')
        ax.set_title('Irradiancia Global Promedio por Mes - 2024', fontsize=13, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / 'irradiancia_mensual.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ irradiancia_mensual.png")

    def _plot_power_distribution(self, output_dir: Path) -> None:
        """Gráfica de distribución de potencia."""
        if self.df is None:
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        power = self.df['ac_power_kw'].values
        ax.hist(power, bins=50, color='steelblue', edgecolor='navy', alpha=0.8)

        ax.axvline(power.mean(), color='red', linestyle='--', linewidth=2,
                  label=f'Promedio: {power.mean():.1f} kW')
        ax.axvline(np.median(power), color='green', linestyle='--', linewidth=2,
                  label=f'Mediana: {np.median(power):.1f} kW')

        ax.set_xlabel('Potencia (kW)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Frecuencia (horas)', fontsize=11, fontweight='bold')
        ax.set_title('Distribución de Potencia AC - 2024', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / 'distribucion_potencia.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ distribucion_potencia.png")

    def _plot_monthly_timeseries(self, output_dir: Path) -> None:
        """Gráfica de series temporales por mes."""
        if self.df is None:
            return

        fig, axes = plt.subplots(3, 4, figsize=(16, 10))
        months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        for month_num in range(1, 13):
            row = (month_num - 1) // 4
            col = (month_num - 1) % 4
            ax = axes[row, col]

            month_mask = self.df.index.month == month_num
            month_data = self.df[month_mask]

            if len(month_data) > 0:
                ax.plot(month_data.index, month_data['ac_power_kw'].values,
                       color='navy', linewidth=1, alpha=0.8)
                ax.fill_between(month_data.index, month_data['ac_power_kw'].values,
                               alpha=0.3, color='skyblue')

            ax.set_title(months[month_num - 1], fontweight='bold', fontsize=10)
            ax.set_ylabel('Potencia (kW)', fontsize=8)
            ax.grid(True, alpha=0.3)

        fig.suptitle('Series Temporales Horarias por Mes - 2024',
                    fontsize=14, fontweight='bold', y=1.00)

        plt.tight_layout()
        plt.savefig(output_dir / 'series_temporales_mensual.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ series_temporales_mensual.png")

    def _plot_temp_power_correlation(self, output_dir: Path) -> None:
        """Gráfica de correlación temperatura vs potencia."""
        if self.df is None:
            return

        fig, ax = plt.subplots(figsize=(10, 7))

        scatter = ax.scatter(self.df['temp_air_c'], self.df['ac_power_kw'],
                           c=self.df.index.month, cmap='viridis', alpha=0.5, s=10)

        # Línea de tendencia
        z = np.polyfit(self.df['temp_air_c'].dropna(),
                      self.df['ac_power_kw'][self.df['temp_air_c'].notna()], 2)
        p = np.poly1d(z)
        temp_range = np.linspace(self.df['temp_air_c'].min(), self.df['temp_air_c'].max(), 100)
        ax.plot(temp_range, p(temp_range), "r--", linewidth=2, alpha=0.8, label='Tendencia')

        ax.set_xlabel('Temperatura (°C)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Potencia AC (kW)', fontsize=11, fontweight='bold')
        ax.set_title('Correlación Temperatura vs Potencia - 2024', fontsize=13, fontweight='bold')
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)

        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Mes', fontsize=10)

        plt.tight_layout()
        plt.savefig(output_dir / 'correlacion_temperatura_potencia.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ correlacion_temperatura_potencia.png")


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description='Análisis de Generación Solar - Iquitos 2024')
    parser.add_argument('--show-plots', action='store_true', help='Mostrar gráficas interactivas')
    parser.add_argument('--output-dir', type=str, default='data/oe2/Generacionsolar/graficas',
                       help='Directorio para guardar gráficas')
    parser.add_argument('--csv-path', type=str,
                       default='data/oe2/Generacionsolar/pv_generation_timeseries.csv',
                       help='Ruta al archivo CSV de generación solar')

    args = parser.parse_args()

    # Convertir a Path
    csv_path = Path(args.csv_path)
    output_dir = Path(args.output_dir)

    print("\n" + "=" * 80)
    print("  ANÁLISIS DE GENERACIÓN SOLAR - IQUITOS 2024")
    print("=" * 80)

    try:
        # Crear analizador
        analyzer = SolarGenerationAnalyzer(csv_path)

        # =====================================================================
        # RESUMEN ANUAL
        # =====================================================================
        print("\n" + "█" * 80)
        print("  RESUMEN ANUAL")
        print("█" * 80)

        annual = analyzer.get_annual_summary()
        print(f"""
    📊 ENERGÍA GENERADA:
       • Total anual:        {annual['energia_anual_kwh']:>15,.0f} kWh
       •                     {annual['energia_anual_mwh']:>15,.1f} MWh
       •                     {annual['energia_anual_gwh']:>15,.3f} GWh
       • Promedio diario:    {annual['energia_anual_kwh']/365:>15,.0f} kWh/día

    ⚡ POTENCIA:
       • Promedio:           {annual['potencia_promedio_kw']:>15,.1f} kW
       • Máxima:             {annual['potencia_maxima_kw']:>15,.1f} kW
       • Mínima:             {annual['potencia_minima_kw']:>15,.1f} kW

    🌡️  TEMPERATURA:
       • Promedio:           {annual['temperatura_promedio_c']:>15,.1f} °C
       • Máxima:             {annual['temperatura_maxima_c']:>15,.1f} °C
       • Mínima:             {annual['temperatura_minima_c']:>15,.1f} °C

    ☀️  IRRADIANCIA:
       • Promedio:           {annual['irradiancia_promedio_wm2']:>15,.1f} W/m²
       • Máxima:             {annual['irradiancia_maxima_wm2']:>15,.1f} W/m²
        """)

        # =====================================================================
        # RESUMEN MENSUAL
        # =====================================================================
        print("█" * 80)
        print("  RESUMEN MENSUAL")
        print("█" * 80)

        monthly = analyzer.get_monthly_summary()
        print("\n" + monthly.to_string(index=False))

        # =====================================================================
        # DÍAS REPRESENTATIVOS
        # =====================================================================
        print("\n" + "█" * 80)
        print("  DÍAS REPRESENTATIVOS")
        print("█" * 80)

        rep_days = analyzer.find_representative_days()

        for key, data in rep_days.items():
            print(f"\n🔆 {data['tipo']}:")
            print(f"   Fecha:         {data['fecha'].strftime('%d/%m/%Y (%A)')}")
            print(f"   Energía:       {data['energia_kwh']:>8,.1f} kWh")

            # Obtener perfil del día
            day_profile = analyzer.get_day_profile(data['fecha'])
            if len(day_profile) > 0:
                print(f"   Potencia Max:  {day_profile['ac_power_kw'].max():>8,.1f} kW")
                print(f"   Temp. Promedio:{day_profile['temp_air_c'].mean():>8,.1f} °C")
                print(f"   Irradiancia Max:{day_profile['ghi_wm2'].max():>8,.1f} W/m²")

        # =====================================================================
        # ANÁLISIS DE TEMPERATURA
        # =====================================================================
        print("\n" + "█" * 80)
        print("  ANÁLISIS DETALLADO DE TEMPERATURA")
        print("█" * 80)

        temp_analysis = analyzer.get_temperature_analysis()
        print(f"""
    Promedio:             {temp_analysis['promedio']:>8,.2f} °C
    Mediana:              {temp_analysis['mediana']:>8,.2f} °C
    Máxima:               {temp_analysis['max']:>8,.2f} °C
    Mínima:               {temp_analysis['min']:>8,.2f} °C
    Desv. Estándar:       {temp_analysis['std']:>8,.2f} °C
    Percentil 25%:        {temp_analysis['q25']:>8,.2f} °C
    Percentil 75%:        {temp_analysis['q75']:>8,.2f} °C
        """)

        # =====================================================================
        # ANÁLISIS DE IRRADIANCIA
        # =====================================================================
        print("█" * 80)
        print("  ANÁLISIS DETALLADO DE IRRADIANCIA")
        print("█" * 80)

        irr_analysis = analyzer.get_irradiance_analysis()
        print(f"""
    Promedio:             {irr_analysis['promedio']:>8,.1f} W/m²
    Mediana:              {irr_analysis['mediana']:>8,.1f} W/m²
    Máxima:               {irr_analysis['max']:>8,.1f} W/m²
    Mínima:               {irr_analysis['min']:>8,.1f} W/m²
    Desv. Estándar:       {irr_analysis['std']:>8,.1f} W/m²
    Percentil 25%:        {irr_analysis['q25']:>8,.1f} W/m²
    Percentil 75%:        {irr_analysis['q75']:>8,.1f} W/m²
        """)

        # =====================================================================
        # ANÁLISIS DE POTENCIA
        # =====================================================================
        print("█" * 80)
        print("  ANÁLISIS DETALLADO DE POTENCIA")
        print("█" * 80)

        power_analysis = analyzer.get_power_analysis()
        print(f"""
    Promedio:             {power_analysis['promedio']:>8,.1f} kW
    Mediana:              {power_analysis['mediana']:>8,.1f} kW
    Máxima:               {power_analysis['max']:>8,.1f} kW
    Mínima:               {power_analysis['min']:>8,.1f} kW
    Desv. Estándar:       {power_analysis['std']:>8,.1f} kW
    Percentil 25%:        {power_analysis['q25']:>8,.1f} kW
    Percentil 75%:        {power_analysis['q75']:>8,.1f} kW
        """)

        # =====================================================================
        # GENERAR GRÁFICAS
        # =====================================================================
        print("█" * 80)
        print("  GENERANDO GRÁFICAS")
        print("█" * 80)

        analyzer.plot_all(output_dir)

        print("\n" + "=" * 80)
        print("  ✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
        print("=" * 80)
        print(f"\n📂 Archivos guardados en: {output_dir.absolute()}")

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print(f"   Asegúrate de haber ejecutado primero el script de generación solar:")
        print(f"   python run_solar_generation_hourly.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
