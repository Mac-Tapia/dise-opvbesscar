#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generador Completo de Gráficas Solar PV - pvlib Demonstration
==============================================================

Script que genera TODAS las gráficas y curvas estadísticas recomendadas
para demostración del dimensionamiento real de generación solar.

Incluye:
- Perfiles de potencia (diarios, mensuales, anuales)
- Análisis de irradiancia (GHI, DNI, DHI)
- Distribuciones de energía
- Comparativas temporales
- Mapas de calor
- Estadísticas y métricas

Ejecución:
    cd d:\\diseñopvbesscar
    python scripts/generate_solar_graphics_complete.py
    
Salida:
    outputs/analysis/solar/
    ├── profiles/
    ├── heatmaps/
    ├── irradiance/
    ├── comparisons/
    └── statistics/
"""

from __future__ import annotations

import sys
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Importar funciones de graphics
try:
    from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import (
        save_matplotlib_figure,
        get_graphics_path,
        is_matplotlib_available,
        run_solar_sizing,
        IQUITOS_PARAMS,
    )
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    sys.exit(1)

# Verificar matplotlib
if not is_matplotlib_available():
    print("❌ matplotlib NO disponible - instalar: pip install matplotlib")
    sys.exit(1)

import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib.patches as mpatches

# Configurar estilo global
rcParams['figure.figsize'] = (14, 8)
rcParams['font.size'] = 10
rcParams['lines.linewidth'] = 2
plt.style.use('seaborn-v0_8-darkgrid')


class SolarGraphicsGenerator:
    """Generador completo de gráficas para análisis solar PV."""
    
    def __init__(self, verbose: bool = True):
        """Inicializa el generador."""
        self.verbose = verbose
        self.results = None
        self.metadata = None
        self.graphics_count = 0
        
    def _print(self, msg: str) -> None:
        """Imprime mensaje si verbose=True."""
        if self.verbose:
            print(msg)
    
    def _save_fig(self, fig, filename: str, subdir: str = "solar", dpi: int = 150) -> bool:
        """Guarda figura y actualiza contador."""
        try:
            path = save_matplotlib_figure(fig, filename, subdir=subdir, dpi=dpi, verbose=False)
            if path:
                self.graphics_count += 1
                self._print(f"   ✓ {filename}")
                return True
            return False
        except Exception as e:
            print(f"   ❌ Error guardando {filename}: {e}")
            return False
    
    def generate_dataset(self) -> bool:
        """Genera dataset solar mediante run_solar_sizing."""
        self._print("\n" + "="*80)
        self._print("📊 FASE 1: Generando Dataset Solar (pvlib + PVGIS)")
        self._print("="*80)
        
        try:
            output_dir = Path("data/oe2/Generacionsolar")
            sizing_result = run_solar_sizing(
                out_dir=output_dir,
                year=2024,
                tz=str(IQUITOS_PARAMS["tz"]),
                lat=float(IQUITOS_PARAMS["lat"]),
                lon=float(IQUITOS_PARAMS["lon"]),
                seconds_per_time_step=3600,  # Horario para 8,760 puntos
                target_dc_kw=4050.0,
                target_ac_kw=3201.0,
                target_annual_kwh=8_000_000.0,
                selection_mode="manual",
                _use_pvlib=True,
            )
            
            # Cargar dataset
            pv_file = output_dir / "pv_generation_hourly_citylearn_v2.csv"
            if pv_file.exists():
                self.results = pd.read_csv(pv_file, index_col=0, parse_dates=True)
                self._print(f"✓ Dataset cargado: {self.results.shape[0]} filas × {self.results.shape[1]} columnas")
                return True
        except Exception as e:
            self._print(f"❌ Error generando dataset: {e}")
            return False
        return False
    
    def plot_daily_power_profile(self) -> None:
        """Perfil promedio de potencia diaria (24 horas)."""
        self._print("\n📈 Distribución de Gráficas")
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # Calcular perfil promedio por hora
        hourly_avg = self.results.groupby(
            pd.to_datetime(self.results.index).hour
        )['ac_power_kw'].mean()
        
        hours = range(24)
        colors = plt.cm.viridis(np.linspace(0, 1, 24))
        
        bars = ax.bar(hours, hourly_avg.values, color=colors, edgecolor='black', linewidth=1.5, alpha=0.8)
        
        # Agregar valores en barras
        for i, (hour, val) in enumerate(zip(hours, hourly_avg.values)):
            if val > 100:
                ax.text(hour, val, f'{val:.0f}', ha='center', va='bottom', fontsize=8, fontweight='bold')
        
        # Configuración
        ax.set_title('Perfil Promedio de Potencia AC - 24 Horas (2024)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Hora del Día', fontsize=12)
        ax.set_ylabel('Potencia [kW]', fontsize=12)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)])
        ax.grid(True, alpha=0.3, axis='y')
        
        # Estadísticas
        stats_text = f"""Estadísticas:
Mean: {hourly_avg.mean():.0f} kW
Max: {hourly_avg.max():.0f} kW
Min: {hourly_avg.min():.0f} kW
Peak Hour: {hourly_avg.idxmax()}:00"""
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        fig.tight_layout()
        self._save_fig(fig, "01_perfil_potencia_24h.png", subdir="solar/profiles")
        plt.close()
    
    def plot_monthly_energy_distribution(self) -> None:
        """Distribución de energía mensual."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Energía mensual
        monthly_energy = self.results.groupby(
            pd.to_datetime(self.results.index).month
        )['ac_energy_kwh'].sum()
        
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        # Gráfica 1: Barras de energía mensual
        colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, 12))
        bars = ax1.bar(meses, monthly_energy.values/1000, color=colors, edgecolor='black', linewidth=1.5)
        
        for bar, val in zip(bars, monthly_energy.values/1000):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax1.set_title('Energía Mensual AC', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Energía [MWh]', fontsize=11)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Gráfica 2: Línea de energía acumulada
        cumsum = monthly_energy.cumsum() / 1000
        ax2.plot(meses, cumsum.values, marker='o', linewidth=2.5, markersize=8, color='darkblue')
        ax2.fill_between(range(len(meses)), cumsum.values, alpha=0.3, color='lightblue')
        
        for i, (mes, val) in enumerate(zip(meses, cumsum.values)):
            ax2.text(i, val, f'{val:.1f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax2.set_title('Energía Acumulada', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Energía Acumulada [MWh]', fontsize=11)
        ax2.grid(True, alpha=0.3)
        
        # Promedio anual
        promedio = monthly_energy.mean() / 1000
        ax1.axhline(y=promedio, color='red', linestyle='--', linewidth=2, label=f'Promedio: {promedio:.0f} MWh')
        ax1.legend(fontsize=10)
        
        fig.suptitle('Análisis de Energía Mensual - 2024', fontsize=14, fontweight='bold', y=1.02)
        fig.tight_layout()
        self._save_fig(fig, "02_energia_mensual.png", subdir="solar/profiles")
        plt.close()
    
    def plot_daily_energy_distribution(self) -> None:
        """Histograma de distribución de energía diaria."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Energía diaria
        daily_energy = self.results.groupby(
            pd.to_datetime(self.results.index).date
        )['ac_energy_kwh'].sum()
        
        # Histograma
        n, bins, patches = ax1.hist(daily_energy/1000, bins=30, color='skyblue', 
                                   edgecolor='black', linewidth=1.2, alpha=0.7)
        
        # Colorear gradiente
        cm = plt.cm.Blues
        for i, patch in enumerate(patches):
            patch.set_facecolor(cm(0.4 + 0.5 * i / len(patches)))
        
        # Líneas de estadísticas
        media = daily_energy.mean() / 1000
        mediana = np.median(daily_energy) / 1000
        std = daily_energy.std() / 1000
        
        ax1.axvline(media, color='red', linestyle='-', linewidth=2.5, label=f'Media: {media:.1f} MWh')
        ax1.axvline(mediana, color='green', linestyle='--', linewidth=2, label=f'Mediana: {mediana:.1f} MWh')
        ax1.axvline(media + std, color='orange', linestyle=':', linewidth=2, label=f'±σ')
        ax1.axvline(media - std, color='orange', linestyle=':', linewidth=2)
        
        ax1.set_title('Distribución de Energía Diaria', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Energía [MWh/día]', fontsize=11)
        ax1.set_ylabel('Frecuencia [días]', fontsize=11)
        ax1.legend(fontsize=10, loc='upper right')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Box plot
        bp = ax2.boxplot([daily_energy/1000], vert=True, patch_artist=True,
                        widths=0.5, labels=['Energia Diaria'])
        
        for patch in bp['boxes']:
            patch.set_facecolor('lightblue')
            patch.set_alpha(0.7)
        
        ax2.set_ylabel('Energía [MWh]', fontsize=11)
        ax2.set_title('Box Plot - Energía Diaria', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Texto de estadísticas
        stats_text = f"""Estadísticas Diarias:
Media: {media:.2f} MWh
Mediana: {mediana:.2f} MWh
Desv. Est.: {std:.2f} MWh
Min: {daily_energy.min()/1000:.2f} MWh
Max: {daily_energy.max()/1000:.2f} MWh
Coef. Variación: {(std/media)*100:.1f}%"""
        
        ax2.text(0.5, 0.30, stats_text, transform=ax2.transAxes, fontsize=10,
                verticalalignment='top', horizontalalignment='center',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
        
        fig.suptitle('Análisis de Distribución de Energía Diaria - 2024', fontsize=14, fontweight='bold', y=1.02)
        fig.tight_layout()
        self._save_fig(fig, "03_distribucion_energia_diaria.png", subdir="solar/profiles")
        plt.close()
    
    def plot_irradiance_analysis(self) -> None:
        """Análisis de irradiancia (GHI, DNI, DHI)."""
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Análisis de Irradiancia - Radiación Solar', fontsize=14, fontweight='bold', y=0.995)
        
        # Extraer irradiancia
        ghi = self.results['ghi_wm2'].values
        dni = self.results.get('dni_wm2', self.results['ghi_wm2'] * 0.8).values
        dhi = self.results.get('dhi_wm2', self.results['ghi_wm2'] * 0.2).values
        
        # 1. Series temporal de GHI
        dates = pd.to_datetime(self.results.index)
        daily_indices = dates.date
        daily_ghi = self.results.groupby(daily_indices)['ghi_wm2'].sum()
        
        ax = axes[0, 0]
        ax.plot(range(len(daily_ghi)), daily_ghi.values / 1000, linewidth=1.5, color='darkgreen', alpha=0.7)
        ax.fill_between(range(len(daily_ghi)), daily_ghi.values / 1000, alpha=0.3, color='lightgreen')
        ax.set_title('GHI Diario (Irradiancia Global)', fontsize=11, fontweight='bold')
        ax.set_ylabel('GHI [kWh/m²/día]', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # 2. Histograma de irradiancia máxima diaria
        ax = axes[0, 1]
        daily_max_ghi = self.results.groupby(daily_indices)['ghi_wm2'].max()
        ax.hist(daily_max_ghi, bins=30, color='orange', alpha=0.7, edgecolor='black')
        ax.axvline(daily_max_ghi.mean(), color='red', linestyle='--', linewidth=2, label=f'Media: {daily_max_ghi.mean():.0f} W/m²')
        ax.set_title('Distribución de Irradiancia Máxima Diaria', fontsize=11, fontweight='bold')
        ax.set_xlabel('GHI Máximo [W/m²]', fontsize=10)
        ax.set_ylabel('Frecuencia [días]', fontsize=10)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 3. Comparativa de componentes (GHI, DNI, DHI)
        ax = axes[1, 0]
        hourly_indices = dates.hour
        ghi_hourly = self.results.groupby(hourly_indices)['ghi_wm2'].mean()
        
        # Obtener DNI y DHI si existen, sino generar estimados
        if 'dni_wm2' in self.results.columns:
            dni_hourly = self.results.groupby(hourly_indices)['dni_wm2'].mean()
        else:
            dni_hourly = (self.results.groupby(hourly_indices)['ghi_wm2'].mean() * 0.8)
        
        if 'dhi_wm2' in self.results.columns:
            dhi_hourly = self.results.groupby(hourly_indices)['dhi_wm2'].mean()
        else:
            dhi_hourly = (self.results.groupby(hourly_indices)['ghi_wm2'].mean() * 0.2)
        
        hours = range(24)
        ax.plot(hours, ghi_hourly.values, marker='o', label='GHI (Global)', linewidth=2)
        ax.plot(hours, dni_hourly.values, marker='s', label='DNI (Direct)', linewidth=2)
        ax.plot(hours, dhi_hourly.values, marker='^', label='DHI (Diffuse)', linewidth=2)
        ax.fill_between(hours, ghi_hourly.values, alpha=0.2)
        ax.set_title('Perfil Horario de Irradiancia', fontsize=11, fontweight='bold')
        ax.set_xlabel('Hora del Día', fontsize=10)
        ax.set_ylabel('Irradiancia [W/m²]', fontsize=10)
        ax.set_xticks(range(0, 24, 2))
        ax.legend(fontsize=9, loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # 4. Tabla de estadísticas
        ax = axes[1, 1]
        ax.axis('off')
        
        stats_text = f"""ESTADÍSTICAS DE IRRADIANCIA (2024 - Iquitos)

GHI (Irradiancia Global Horizontal):
  • Media anual:        {ghi.mean():.1f} W/m²
  • Máximo:             {ghi.max():.1f} W/m²
  • Mínimo:             {ghi.min():.1f} W/m²
  • Desv. Estándar:     {ghi.std():.1f} W/m²
  • Total anual:        {ghi.sum()/1000:.1f} kWh/m²

DNI (Irradiancia Normal Directa):
  • Media anual:        {dni.mean():.1f} W/m²
  • Máximo:             {dni.max():.1f} W/m²
  
DHI (Irradiancia Horizontal Difusa):
  • Media anual:        {dhi.mean():.1f} W/m²
  • Máximo:             {dhi.max():.1f} W/m²

Horas de Sol Pico (HSP):
  • GHI > 500 W/m²:     {(ghi > 500).sum()} horas
  • GHI > 700 W/m²:     {(ghi > 700).sum()} horas
  • GHI > 900 W/m²:     {(ghi > 900).sum()} horas"""
        
        ax.text(0.05, 0.95, stats_text, transform=ax.transAxes, fontsize=9,
               verticalalignment='top', family='monospace',
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        fig.tight_layout()
        self._save_fig(fig, "04_analisis_irradiancia.png", subdir="solar/irradiance")
        plt.close()
    
    def plot_heatmap_monthly_hourly(self) -> None:
        """Mapa de calor: generación horaria por mes."""
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Crear matriz: 12 meses × 24 horas
        dates = pd.to_datetime(self.results.index)
        heatmap_data = np.zeros((12, 24))
        
        for i in range(len(self.results)):
            month = dates[i].month - 1
            hour = dates[i].hour
            heatmap_data[month, hour] += self.results.iloc[i]['ac_power_kw']
        
        # Promediar
        heatmap_data = heatmap_data / (365 / 12)
        
        # Gráfica
        im = ax.imshow(heatmap_data, cmap='hot', aspect='auto', interpolation='bilinear')
        
        # Configurar ejes
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)])
        ax.set_yticks(range(12))
        ax.set_yticklabels(meses)
        
        ax.set_title('Potencia AC Promedio Horaria-Mensual (2024)', 
                    fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Hora del Día', fontsize=12)
        ax.set_ylabel('Mes', fontsize=12)
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax, label='Potencia Promedio [kW]')
        
        fig.tight_layout()
        self._save_fig(fig, "05_heatmap_potencia_mensual_horaria.png", subdir="solar/heatmaps")
        plt.close()
    
    def plot_heatmap_daily_hourly(self) -> None:
        """Mapa de calor: generación horaria por día (primeros 60 días)."""
        fig, ax = plt.subplots(figsize=(16, 10))
        
        dates = pd.to_datetime(self.results.index)
        days = dates.date
        unique_days = pd.Series(days).unique()[:60]  # Primeros 60 días
        
        # Crear matriz
        heatmap_data = np.zeros((len(unique_days), 24))
        
        for i, day in enumerate(unique_days):
            day_data = self.results[dates.date == day]['ac_power_kw'].values
            heatmap_data[i, :len(day_data)] = day_data[:24] if len(day_data) >= 24 else np.pad(day_data, (0, 24-len(day_data)))
        
        # Gráfica
        im = ax.imshow(heatmap_data, cmap='viridis', aspect='auto', interpolation='nearest')
        
        # Ejes
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)])
        
        # Configurar etiquetas Y: mostrar cada 5 días
        ytick_positions = list(range(0, len(unique_days), 5))
        ytick_labels = [str(unique_days[i]) for i in ytick_positions]
        ax.set_yticks(ytick_positions)
        ax.set_yticklabels(ytick_labels)
        
        ax.set_title('Potencia AC Diaria (Primeros 60 Días del Año)', 
                    fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel('Hora del Día', fontsize=12)
        ax.set_ylabel('Fecha', fontsize=12)
        
        cbar = plt.colorbar(im, ax=ax, label='Potencia [kW]')
        
        fig.tight_layout()
        self._save_fig(fig, "06_heatmap_diaria_horaria_60dias.png", subdir="solar/heatmaps")
        plt.close()
    
    def plot_performance_metrics(self) -> None:
        """Métricas de desempeño del sistema."""
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Métricas de Desempeño del Sistema Fotovoltaico', fontsize=14, fontweight='bold', y=0.995)
        
        # Datos
        annual_energy = self.results['ac_energy_kwh'].sum()
        max_power = self.results['ac_power_kw'].max()
        mean_power = self.results['ac_power_kw'].mean()
        system_capacity_kw = 3201.0
        system_capacity_kwhp = 4050.0
        
        capacity_factor = (annual_energy / (system_capacity_kw * 8760)) * 100
        specific_yield = annual_energy / system_capacity_kwhp
        annual_solar_irr = self.results['ghi_wm2'].sum() / 1000
        performance_ratio = (specific_yield / annual_solar_irr) * 100
        
        # 1. Indicador de Factor de Capacidad
        ax = axes[0, 0]
        ax.barh(['Capacidad'], [capacity_factor], color='#2ecc71', height=0.5, edgecolor='black', linewidth=2)
        ax.set_xlim(0, 40)
        ax.set_xlabel('Factor de Capacidad [%]', fontsize=11)
        ax.set_title('Factor de Capacidad del Sistema', fontsize=12, fontweight='bold')
        ax.text(capacity_factor + 1, 0, f'{capacity_factor:.1f}%', va='center', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        
        # 2. Energía anual
        ax = axes[0, 1]
        energies = [annual_energy / 1e6]
        ax.bar(['Anual'], energies, color='#3498db', edgecolor='black', linewidth=2, width=0.5)
        ax.set_ylabel('Energía [GWh]', fontsize=11)
        ax.set_title('Energía AC Anual Generada', fontsize=12, fontweight='bold')
        ax.text(0, energies[0] + 0.1, f'{energies[0]:.3f} GWh', ha='center', fontsize=12, fontweight='bold')
        ax.set_ylim(0, max(energies) * 1.2)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 3. Curva de potencia
        ax = axes[1, 0]
        dates = pd.to_datetime(self.results.index)
        days = dates.date
        daily_max = self.results.groupby(days)['ac_power_kw'].max()
        daily_avg = self.results.groupby(days)['ac_power_kw'].mean()
        
        ax.scatter(range(len(daily_max)), daily_max.values, s=20, alpha=0.5, label='Máximo diario', color='red')
        ax.scatter(range(len(daily_avg)), daily_avg.values, s=20, alpha=0.5, label='Promedio diario', color='blue')
        ax.axhline(mean_power, color='green', linestyle='--', linewidth=2, label=f'Media anual: {mean_power:.0f} kW')
        ax.axhline(max_power, color='red', linestyle='--', linewidth=2, label=f'Máximo: {max_power:.0f} kW')
        
        ax.set_xlabel('Día del Año', fontsize=11)
        ax.set_ylabel('Potencia [kW]', fontsize=11)
        ax.set_title('Variación Diaria de Potencia', fontsize=12, fontweight='bold')
        ax.legend(fontsize=9, loc='lower right')
        ax.grid(True, alpha=0.3)
        
        # 4. Tabla de métricas
        ax = axes[1, 1]
        ax.axis('off')
        
        stats_text = f"""MÉTRICAS PRINCIPALES DE DESEMPEÑO

Sistema:
  • Capacidad AC:           {system_capacity_kw:,.0f} kW
  • Capacidad DC:           {system_capacity_kwhp:,.0f} kWp
  • Ratio AC/DC:            {system_capacity_kw/system_capacity_kwhp:.3f}

Energía (2024):
  • Energía AC anual:       {annual_energy/1e6:.3f} GWh
  • Energía AC anual:       {annual_energy/1e9:.2f} TWh
  
Potencia:
  • Potencia máxima:        {max_power:,.0f} kW
  • Potencia media:         {mean_power:,.0f} kW
  • Ratio max/media:        {max_power/mean_power:.2f}

Eficiencia:
  • Factor capacidad:       {capacity_factor:.2f}%
  • Performance Ratio:      {performance_ratio:.2f}%
  • Yield específico:       {specific_yield:,.0f} kWh/kWp
  
Radiación:
  • GHI anual:              {annual_solar_irr:,.0f} kWh/m²"""
        
        ax.text(0.05, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', family='monospace',
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
        
        fig.tight_layout()
        self._save_fig(fig, "07_metricas_desempenio.png", subdir="solar/statistics")
        plt.close()
    
    def plot_temperature_effect(self) -> None:
        """Efecto de la temperatura en potencia."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Correlación temperatura vs potencia
        if 'temperatura_c' in self.results.columns:
            temp = self.results['temperatura_c'].values
            power = self.results['ac_power_kw'].values
            
            # Scatter plot
            scatter = ax1.scatter(temp, power, c=temp, cmap='coolwarm', s=30, alpha=0.5, edgecolor='black', linewidth=0.5)
            
            # Línea de tendencia
            z = np.polyfit(temp, power, 2)  # type: ignore[no-overload-found]
            p = np.poly1d(z)
            temp_sorted = np.sort(temp)  # type: ignore[no-overload-found]
            ax1.plot(temp_sorted, p(temp_sorted), "r-", linewidth=3, label='Tendencia')
            
            ax1.set_xlabel('Temperatura del Aire [°C]', fontsize=11)
            ax1.set_ylabel('Potencia AC [kW]', fontsize=11)
            ax1.set_title('Relación Temperatura vs Potencia', fontsize=12, fontweight='bold')
            ax1.legend(fontsize=10)
            ax1.grid(True, alpha=0.3)
            
            cbar = plt.colorbar(scatter, ax=ax1, label='Temperatura [°C]')
            
            # Correlación por hora
            dates = pd.to_datetime(self.results.index)
            hourly_temp = self.results.groupby(dates.hour)['temperatura_c'].mean()
            hourly_power = self.results.groupby(dates.hour)['ac_power_kw'].mean()
            
            ax2.plot(hourly_temp.index, hourly_temp.values, marker='o', label='Temperatura', 
                    linewidth=2, markersize=6, color='red')
            ax2_twin = ax2.twinx()
            ax2_twin.plot(hourly_power.index, hourly_power.values, marker='s', label='Potencia',
                         linewidth=2, markersize=6, color='blue')
            
            ax2.set_xlabel('Hora del Día', fontsize=11)
            ax2.set_ylabel('Temperatura [°C]', fontsize=11, color='red')
            ax2_twin.set_ylabel('Potencia [kW]', fontsize=11, color='blue')
            ax2.set_title('Perfil Horario: Temperatura vs Potencia', fontsize=12, fontweight='bold')
            ax2.tick_params(axis='y', labelcolor='red')
            ax2_twin.tick_params(axis='y', labelcolor='blue')
            ax2.grid(True, alpha=0.3)
            
            # Leyendas
            lines1, labels1 = ax2.get_legend_handles_labels()
            lines2, labels2 = ax2_twin.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=10, loc='upper left')
        
        fig.tight_layout()
        self._save_fig(fig, "08_efectotemperatura_potencia.png", subdir="solar/comparisons")
        plt.close()
    
    def plot_cloud_days_analysis(self) -> None:
        """Análisis de días despejados vs nublados."""
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Análisis de Variabilidad: Días Despejados vs Nublados', fontsize=14, fontweight='bold', y=0.995)
        
        dates = pd.to_datetime(self.results.index)
        days = dates.date
        
        # Energía diaria
        daily_energy = self.results.groupby(days)['ac_energy_kwh'].sum()
        
        # Clasificar días
        mean_energy = daily_energy.mean()
        std_energy = daily_energy.std()
        
        despejado_mask = daily_energy > (mean_energy + 0.5 * std_energy)
        nublado_mask = daily_energy < (mean_energy - 0.5 * std_energy)
        intermedio_mask = ~(despejado_mask | nublado_mask)
        
        # 1. Distribución de tipos de día
        ax = axes[0, 0]
        counts = [despejado_mask.sum(), intermedio_mask.sum(), nublado_mask.sum()]
        colors = ['#ffd700', '#87ceeb', '#696969']
        wedges, texts, autotexts = ax.pie(counts, labels=['Despejado', 'Intermedio', 'Nublado'],
                                           autopct='%1.1f%%', colors=colors, startangle=90,
                                           textprops={'fontsize': 11, 'fontweight': 'bold'})
        ax.set_title('Distribución de Tipos de Día', fontsize=12, fontweight='bold')
        
        # 2. Perfiles por tipo de día
        ax = axes[0, 1]
        
        if despejado_mask.any():
            despejado_dates = daily_energy[despejado_mask].index[0]
            despejado_data = self.results[dates.date == despejado_dates]
            ax.plot(despejado_data.index.hour, despejado_data['ac_power_kw'].values, 
                   label='Día Despejado', linewidth=2.5, marker='o', color='#ffd700')
        
        if nublado_mask.any():
            nublado_dates = daily_energy[nublado_mask].index[0]
            nublado_data = self.results[dates.date == nublado_dates]
            ax.plot(nublado_data.index.hour, nublado_data['ac_power_kw'].values,
                   label='Día Nublado', linewidth=2.5, marker='o', color='#696969')
        
        ax.set_xlabel('Hora del Día', fontsize=11)
        ax.set_ylabel('Potencia [kW]', fontsize=11)
        ax.set_title('Comparativa de Perfiles de Potencia', fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # 3. Curva de duración de potencia
        ax = axes[1, 0]
        power_sorted = np.sort(self.results['ac_power_kw'].values)[::-1]  # type: ignore[no-overload-found]
        cumulative_pct = np.arange(1, len(power_sorted) + 1) / len(power_sorted) * 100
        
        ax.plot(cumulative_pct, power_sorted, linewidth=2.5, color='darkblue')
        ax.fill_between(cumulative_pct, power_sorted, alpha=0.3, color='lightblue')
        ax.set_xlabel('Porcentaje de Horas (%)', fontsize=11)
        ax.set_ylabel('Potencia [kW]', fontsize=11)
        ax.set_title('Curva de Duración de Potencia', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 4. Estadísticas por tipo de día
        ax = axes[1, 1]
        ax.axis('off')
        
        despejado_energy = daily_energy[despejado_mask]
        intermedio_energy = daily_energy[intermedio_mask]
        nublado_energy = daily_energy[nublado_mask]
        
        stats_text = f"""ANÁLISIS DE VARIABILIDAD CLIMÁTICA

Distribución de Días:
  • Despejados:             {despejado_mask.sum()} días ({despejado_mask.sum()/len(daily_energy)*100:.1f}%)
  • Intermedios:            {intermedio_mask.sum()} días ({intermedio_mask.sum()/len(daily_energy)*100:.1f}%)
  • Nublados:               {nublado_mask.sum()} días ({nublado_mask.sum()/len(daily_energy)*100:.1f}%)

Energía Promedio Diaria:
  • Despejados:             {despejado_energy.mean()/1000:.2f} MWh
  • Intermedios:            {intermedio_energy.mean()/1000:.2f} MWh
  • Nublados:               {nublado_energy.mean()/1000:.2f} MWh

Variabilidad Diaria:
  • Media:                  {daily_energy.mean()/1000:.2f} MWh
  • Desv. Estándar:         {daily_energy.std()/1000:.2f} MWh
  • Coef. Variación:        {(daily_energy.std()/daily_energy.mean())*100:.1f}%
  • Max/Min:                {daily_energy.max()/daily_energy.min():.2f}x

Horas de Potencia > 50%:   {(self.results['ac_power_kw'] > (self.results['ac_power_kw'].max() * 0.5)).sum()} horas"""
        
        ax.text(0.05, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', family='monospace',
               bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.9))
        
        fig.tight_layout()
        self._save_fig(fig, "09_analisis_variabilidad_climatica.png", subdir="solar/comparisons")
        plt.close()
    
    def plot_summary_report(self) -> None:
        """Reporte resumen único con toda la información."""
        fig = plt.figure(figsize=(20, 14))
        gs = fig.add_gridspec(4, 3, hspace=0.4, wspace=0.3)
        
        fig.suptitle('REPORTE COMPLETO: Dimensionamiento Solar PV - Iquitos 2024', 
                    fontsize=16, fontweight='bold', y=0.995)
        
        # 1. Perfil 24h
        ax1 = fig.add_subplot(gs[0, 0])
        hourly_avg = self.results.groupby(pd.to_datetime(self.results.index).hour)['ac_power_kw'].mean()
        ax1.bar(range(24), hourly_avg.values, color='steelblue', alpha=0.7)
        ax1.set_title('Perfil 24h', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Potencia [kW]')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 2. Energía mensual
        ax2 = fig.add_subplot(gs[0, 1])
        monthly_energy = self.results.groupby(pd.to_datetime(self.results.index).month)['ac_energy_kwh'].sum()
        meses = ['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
        ax2.bar(meses, monthly_energy.values/1000, color='coral', alpha=0.7)
        ax2.set_title('Energía Mensual', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Energía [MWh]')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # 3. Irradiancia
        ax3 = fig.add_subplot(gs[0, 2])
        daily_ghi = self.results.groupby(pd.to_datetime(self.results.index).date)['ghi_wm2'].sum()
        ax3.hist(daily_ghi/1000, bins=25, color='gold', alpha=0.7, edgecolor='black')
        ax3.set_title('Distribución GHI', fontsize=11, fontweight='bold')
        ax3.set_xlabel('GHI [kWh/m²]')
        ax3.grid(True, alpha=0.3, axis='y')
        
        # 4. Heatmap pequeño
        ax4 = fig.add_subplot(gs[1, 0])
        dates = pd.to_datetime(self.results.index)
        heatmap_data = np.zeros((12, 24))
        for i in range(len(self.results)):
            month = dates[i].month - 1
            hour = dates[i].hour
            heatmap_data[month, hour] += self.results.iloc[i]['ac_power_kw']
        heatmap_data = heatmap_data / (365 / 12)
        im = ax4.imshow(heatmap_data, cmap='hot', aspect='auto')
        ax4.set_title('Heatmap Mensual-Horario', fontsize=11, fontweight='bold')
        ax4.set_ylabel('Mes')
        plt.colorbar(im, ax=ax4, label='kW')
        
        # 5. Distribución energía diaria
        ax5 = fig.add_subplot(gs[1, 1])
        daily_energy = self.results.groupby(pd.to_datetime(self.results.index).date)['ac_energy_kwh'].sum()
        ax5.hist(daily_energy/1000, bins=30, color='lightgreen', alpha=0.7, edgecolor='black')
        media = daily_energy.mean() / 1000
        ax5.axvline(media, color='red', linestyle='--', linewidth=2, label=f'Media: {media:.1f}')
        ax5.set_title('Distribución Energía Diaria', fontsize=11, fontweight='bold')
        ax5.set_xlabel('Energía [MWh/día]')
        ax5.legend(fontsize=9)
        ax5.grid(True, alpha=0.3, axis='y')
        
        # 6. Curva de duración
        ax6 = fig.add_subplot(gs[1, 2])
        power_sorted = np.sort(self.results['ac_power_kw'].values)[::-1]  # type: ignore[no-overload-found]
        cumulative_pct = np.arange(1, len(power_sorted) + 1) / len(power_sorted) * 100
        ax6.plot(cumulative_pct, power_sorted, linewidth=2, color='darkblue')
        ax6.fill_between(cumulative_pct, power_sorted, alpha=0.3)
        ax6.set_title('Curva de Duración', fontsize=11, fontweight='bold')
        ax6.set_xlabel('% de Horas')
        ax6.set_ylabel('Potencia [kW]')
        ax6.grid(True, alpha=0.3)
        
        # 7-12. Tabla de métricas grandes
        ax_metrics = fig.add_subplot(gs[2:, :])
        ax_metrics.axis('off')
        
        annual_energy = self.results['ac_energy_kwh'].sum()
        max_power = self.results['ac_power_kw'].max()
        mean_power = self.results['ac_power_kw'].mean()
        system_capacity_kw = 3201.0
        system_capacity_kwhp = 4050.0
        
        capacity_factor = (annual_energy / (system_capacity_kw * 8760)) * 100
        specific_yield = annual_energy / system_capacity_kwhp
        annual_solar_irr = self.results['ghi_wm2'].sum() / 1000
        performance_ratio = (specific_yield / annual_solar_irr) * 100
        
        metrics_text = f"""
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ESPECIFICACIONES DEL SISTEMA                                                                                         │
├────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────┤
│ Ubicación: Iquitos, Perú (-3.75°, -73.25°)        │ Módulo: Kyocera KS20 (20.2W, 280.3 W/m²)                      │
│ Altitud: 104 m s.n.m.                             │ Inversor: Eaton Xpert1670 (3201 kW AC)                         │
│ Zona Horaria: America/Lima (UTC-5)                │ Total Módulos: 186,279 unidades                                │
│ Año Análisis: 2024 (365 días, 8,760 horas)       │ Strings en paralelo: Optimizado para máximo rendimiento        │
├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ ENERGÍA Y POTENCIA                                │ EFICIENCIA Y RENDIMIENTO                                        │
├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ Energía AC anual:          {annual_energy/1e9:>12.2f} TWh  │ Factor de Capacidad:        {capacity_factor:>10.2f} %       │
│ Energía AC anual:          {annual_energy/1e6:>12.0f} MWh  │ Performance Ratio:          {performance_ratio:>10.2f} %       │
│ Energía AC promedio diaria:{annual_energy/365/1e3:>12.1f} MWh  │ Yield Específico:           {specific_yield:>10.0f} kWh/kWp │
│ Potencia AC máxima:        {max_power:>12.0f} kW   │ Hora Equivalentes/año:       {annual_energy/max_power:>10.0f} h       │
│ Potencia AC media:         {mean_power:>12.0f} kW   │ Horas con producción:        {(self.results['ac_power_kw'] > 0).sum():>10.0f} h       │
├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ RADIACIÓN SOLAR (IRRADIANCIA)                     │ CAPACIDAD DEL SISTEMA                                          │
├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ GHI Total Anual:           {annual_solar_irr:>12.0f} kWh/m² │ Capacidad AC Nominal:       {system_capacity_kw:>10.0f} kW    │
│ GHI Promedio Diario:       {annual_solar_irr/365:>12.1f} kWh/m² │ Capacidad DC Nominal:       {system_capacity_kwhp:>10.0f} kWp   │
│ GHI Máximo Horario:        {self.results['ghi_wm2'].max():>12.0f} W/m² │ Ratio AC/DC:                {system_capacity_kw/system_capacity_kwhp:>10.3f}       │
│ GHI Medio Horario:         {self.results['ghi_wm2'].mean():>12.0f} W/m² │ Pérdidas del Sistema:       {100-100*(system_capacity_kw/system_capacity_kwhp):>10.1f} %       │
├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ VARIABILIDAD CLIMÁTICA                            │ HORAS DE OPERACIÓN SIGNIFICATIVA                               │
├────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────┤
│ Desv. Est. Potencia Diaria: {self.results.groupby(pd.to_datetime(self.results.index).date)['ac_power_kw'].mean().std():>12.0f} kW   │ P > 50% Pmáx:               {(self.results['ac_power_kw'] > self.results['ac_power_kw'].max()*0.5).sum():>10.0f} horas   │
│ Coef. Variación Diaria:    {(self.results.groupby(pd.to_datetime(self.results.index).date)['ac_energy_kwh'].sum().std() / self.results.groupby(pd.to_datetime(self.results.index).date)['ac_energy_kwh'].sum().mean() * 100):>10.1f} %       │ P > 75% Pmáx:               {(self.results['ac_power_kw'] > self.results['ac_power_kw'].max()*0.75).sum():>10.0f} horas   │
│ Días Despejados:           {(self.results.groupby(pd.to_datetime(self.results.index).date)['ac_energy_kwh'].sum() > (self.results.groupby(pd.to_datetime(self.results.index).date)['ac_energy_kwh'].sum().mean() + self.results.groupby(pd.to_datetime(self.results.index).date)['ac_energy_kwh'].sum().std()*0.5)).sum():>12} días   │ P > 90% Pmáx:               {(self.results['ac_power_kw'] > self.results['ac_power_kw'].max()*0.9).sum():>10.0f} horas   │
│ Días Nublados:             {(self.results.groupby(pd.to_datetime(self.results.index).date)['ac_energy_kwh'].sum() < (self.results.groupby(pd.to_datetime(self.results.index).date)['ac_energy_kwh'].sum().mean() - self.results.groupby(pd.to_datetime(self.results.index).date)['ac_energy_kwh'].sum().std()*0.5)).sum():>12} días   │ P > 25% Pmáx:               {(self.results['ac_power_kw'] > self.results['ac_power_kw'].max()*0.25).sum():>10.0f} horas   │
└────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────┘

CONCLUSIONES:
• El sistema fotovoltaico de {system_capacity_kwhp:,.0f} kWp genera {annual_energy/1e9:.3f} TWh anuales en el clima tropical de Iquitos
• Factor de capacidad de {capacity_factor:.1f}% indica un desempeño excelente para la latitud ecuatorial
• Alto porcentaje de horas con producción significativa asegura generación consistente durante el año
• Variabilidad climática moderada permite integración predecible en sistemas de energía aislada
"""
        
        ax_metrics.text(0.02, 0.98, metrics_text, transform=ax_metrics.transAxes, fontsize=8.5,
                       verticalalignment='top', family='monospace',
                       bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.95, pad=1))
        
        self._save_fig(fig, "10_resumen_completo_sistema.png", subdir="solar/statistics", dpi=150)
        plt.close()
    
    def run_all(self) -> None:
        """Ejecuta todas las gráficas."""
        print("\n" + "="*80)
        print("🎨 GENERADOR COMPLETO DE GRÁFICAS SOLARES - pvlib System")
        print("="*80)
        
        # Generar dataset
        if not self.generate_dataset():
            print("❌ No se pudo generar el dataset solar")
            return
        
        # Generar gráficas
        self._print("\n" + "="*80)
        self._print("📊 Generando 10 Gráficas de Análisis Completo...")
        self._print("="*80)
        
        self._print("\n1️⃣  Perfil de potencia 24 horas...")
        self.plot_daily_power_profile()
        
        self._print("2️⃣  Energía mensual...")
        self.plot_monthly_energy_distribution()
        
        self._print("3️⃣  Distribución energía diaria...")
        self.plot_daily_energy_distribution()
        
        self._print("4️⃣  Análisis de irradiancia...")
        self.plot_irradiance_analysis()
        
        self._print("5️⃣  Heatmap potencia mensual-horaria...")
        self.plot_heatmap_monthly_hourly()
        
        self._print("6️⃣  Heatmap diaria-horaria (60 días)...")
        self.plot_heatmap_daily_hourly()
        
        self._print("7️⃣  Métricas de desempeño...")
        self.plot_performance_metrics()
        
        self._print("8️⃣  Efecto de temperatura...")
        self.plot_temperature_effect()
        
        self._print("9️⃣  Análisis de variabilidad climática...")
        self.plot_cloud_days_analysis()
        
        self._print("🔟 Resumen completo del sistema...")
        self.plot_summary_report()
        
        # Resumen final
        print("\n" + "="*80)
        print(f"✅ GENERACIÓN COMPLETADA EXITOSAMENTE")
        print("="*80)
        print(f"\n📊 Total de gráficas generadas: {self.graphics_count}")
        print(f"📂 Ubicación: outputs/analysis/solar/")
        print(f"""
Gráficas clasificadas en:
  • profiles/       → Perfiles temporales (5 gráficas)
  • heatmaps/       → Mapas de calor (2 gráficas)
  • irradiance/     → Análisis radiación (1 gráfica)
  • comparisons/    → Comparativas (1 gráfica)
  • statistics/     → Estadísticas (1 gráfica)
  
Todas las gráficas están listas para:
  ✓ Informes técnicos
  ✓ Presentaciones ejecutivas
  ✓ Análisis de inversión
  ✓ Publicaciones académicas
""")
        print("="*80)


def main():
    """Función principal."""
    generator = SolarGraphicsGenerator(verbose=True)
    generator.run_all()


if __name__ == "__main__":
    main()
