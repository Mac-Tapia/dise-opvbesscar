#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ejemplo de Uso: Infraestructura Gráfica de solar_pvlib.py

Este script demuestra cómo usar las nuevas funciones de graphics integradas
en solar_pvlib.py para guardar gráficas matplotlib de forma centralizada.

Funciones disponibles:
- get_graphics_path(filename, subdir)          → Obtiene ruta para guardar
- save_matplotlib_figure(fig, filename, ...)   → Guarda figura en ruta centralizada
- is_matplotlib_available()                    → Verifica disponibilidad

Directorio centralizado: outputs/analysis/solar/

Ejecución:
    python examples_graphics_usage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import pandas as pd

# Importar funciones de graphics
try:
    from dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import (
        get_graphics_path,
        save_matplotlib_figure,
        is_matplotlib_available,
        SOLAR_GRAPHICS_SUBDIR,
    )
    print(f"✓ Importación exitosa de funciones graphics")
    print(f"  Directorio destino: {SOLAR_GRAPHICS_SUBDIR}")
except ImportError as e:
    print(f"✗ Error importando: {e}")
    sys.exit(1)

# Verificar disponibilidad de matplotlib
if not is_matplotlib_available():
    print("\n⚠ matplotlib NO está disponible")
    print("  Las gráficas no se generarán (graceful degradation)")
    sys.exit(0)

# Importar matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams

# Configurar estilo
rcParams['figure.figsize'] = (12, 6)
rcParams['font.size'] = 10


def example_1_simple_line_plot():
    """
    EJEMPLO 1: Gráfica simple - Línea de potencia
    
    Demuestra:
    - Crear figura básica
    - Usar save_matplotlib_figure()
    - Guardar en subdirectorio específico
    """
    print("\n" + "="*70)
    print("EJEMPLO 1: Gráfica Simple - Potencia AC Diaria")
    print("="*70)
    
    # Crear datos sintéticos (perfil de potencia diaria)
    horas = np.arange(0, 24, 1)
    # Curva gaussiana simulando un día despejado
    potencia = 3500 * np.exp(-((horas - 12)**2) / 18)
    
    # Crear figura
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(horas, potencia, 'b-', linewidth=2.5, label='Potencia AC')
    ax.fill_between(horas, potencia, alpha=0.3, color='blue')
    
    # Configurar gráfica
    ax.set_title('Perfil de Potencia AC - Día Despejado', fontsize=14, fontweight='bold')
    ax.set_xlabel('Hora del Día', fontsize=12)
    ax.set_ylabel('Potencia [kW]', fontsize=12)
    ax.set_xlim(0, 23)
    ax.set_ylim(0, 4000)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)
    
    # Guardar gráfica
    path = save_matplotlib_figure(
        fig,
        "01_potencia_ac_diaria.png",
        subdir="solar/profiles",
        dpi=100,
        verbose=True
    )
    plt.close()
    
    print(f"\n✓ Gráfica guardada exitosamente")
    return path


def example_2_bar_chart():
    """
    EJEMPLO 2: Gráfica de barras - Energía mensual
    
    Demuestra:
    - Gráfica de barras (bar chart)
    - Múltiples series
    - xticks rotados
    """
    print("\n" + "="*70)
    print("EJEMPLO 2: Gráfica de Barras - Energía Mensual")
    print("="*70)
    
    # Crear datos sintéticos (energía por mes)
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
             'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    
    # Energía mensual (kWh) - Iquitos tiene menos lluvia en mayo-junio
    energia = np.array([
        750000, 720000, 780000, 760000, 680000, 650000,
        700000, 730000, 710000, 750000, 780000, 800000
    ])
    
    # Crear figura
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # Barras con colores basados en energía
    colors = plt.cm.YlOrRd(energia / energia.max())
    bars = ax.bar(meses, energia / 1000, color=colors, edgecolor='black', linewidth=1.5)
    
    # Agregar valores en barras
    for bar, val in zip(bars, energia / 1000):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.0f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Configurar gráfica
    ax.set_title('Energía Solar Mensual - 2024 (Iquitos)', 
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Mes', fontsize=12)
    ax.set_ylabel('Energía [MWh]', fontsize=12)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Agregar línea de promedio
    promedio = energia.mean()
    ax.axhline(y=promedio/1000, color='red', linestyle='--', linewidth=2, 
               label=f'Promedio: {promedio/1000:.0f} MWh')
    ax.legend(fontsize=11)
    
    # Guardar gráfica
    path = save_matplotlib_figure(
        fig,
        "02_energia_mensual.png",
        subdir="solar/profiles",
        dpi=100,
        verbose=True
    )
    plt.close()
    
    print(f"\n✓ Gráfica guardada exitosamente")
    return path


def example_3_histogram():
    """
    EJEMPLO 3: Histograma - Distribución de energía diaria
    
    Demuestra:
    - Histogramas
    - Estadísticas superpuestas
    - Múltiples ejes Y
    """
    print("\n" + "="*70)
    print("EJEMPLO 3: Histograma - Distribución de Energía Diaria")
    print("="*70)
    
    # Crear datos de energía diaria simulados (365 días)
    np.random.seed(42)
    # Distribución normal con pequeña asimetría (lluvia variable)
    energia_diaria = np.random.normal(21800, 3500, 365)  # Media ~22 MWh, σ ~3.5 MWh
    energia_diaria = np.clip(energia_diaria, 5000, 40000)  # Limitar rangos realistas
    
    # Crear figura
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Histograma
    n, bins, patches = ax.hist(energia_diaria/1000, bins=30, color='skyblue', 
                               edgecolor='black', linewidth=1.2, alpha=0.7)
    
    # Color gradient para barras
    cm = plt.cm.Blues
    for i, patch in enumerate(patches):
        patch.set_facecolor(cm(0.4 + 0.5 * i / len(patches)))
    
    # Configurar gráfica
    ax.set_title('Distribución de Energía Diaria - 365 Días (2024)',
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Energía [MWh/día]', fontsize=12)
    ax.set_ylabel('Frecuencia [días]', fontsize=12)
    
    # Agregar estadísticas
    media = energia_diaria.mean() / 1000
    mediana = np.median(energia_diaria) / 1000
    std = energia_diaria.std() / 1000
    
    ax.axvline(media, color='red', linestyle='-', linewidth=2.5, 
              label=f'Media: {media:.1f} MWh')
    ax.axvline(mediana, color='green', linestyle='--', linewidth=2, 
              label=f'Mediana: {mediana:.1f} MWh')
    
    # Leyenda con estadísticas
    stats_text = f"""Estadísticas:
    Media: {media:.1f} MWh
    Mediana: {mediana:.1f} MWh
    Desv. Est.: {std:.1f} MWh
    Min: {energia_diaria.min()/1000:.1f} MWh
    Max: {energia_diaria.max()/1000:.1f} MWh"""
    
    ax.text(0.98, 0.97, stats_text, transform=ax.transAxes,
           fontsize=10, verticalalignment='top', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Guardar gráfica
    path = save_matplotlib_figure(
        fig,
        "03_distribucion_energia_diaria.png",
        subdir="solar/profiles",
        dpi=100,
        verbose=True
    )
    plt.close()
    
    print(f"\n✓ Gráfica guardada exitosamente")
    return path


def example_4_heatmap():
    """
    EJEMPLO 4: Mapa de calor - Generación horaria mensual
    
    Demuestra:
    - Matrices 2D con imshow()
    - Colormaps personalizados
    - Barra de color (colorbar)
    """
    print("\n" + "="*70)
    print("EJEMPLO 4: Mapa de Calor - Generación Horaria Mensual")
    print("="*70)
    
    # Crear matriz: 12 meses × 24 horas
    np.random.seed(42)
    heatmap_data = np.random.rand(12, 24) * 3500  # Potencia en kW (0-3500)
    
    # Ajustar para parecer más realista (máximo al medio del día)
    for j in range(24):
        # Gaussiana centrada a las 12:00
        factor = np.exp(-((j - 12)**2) / 18)
        heatmap_data[:, j] *= factor + 0.2
    
    # Crear figura
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Heatmap
    im = ax.imshow(heatmap_data, cmap='hot', aspect='auto', interpolation='bilinear')
    
    # Configurar ejes
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
             'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    horas = [f"{h:02d}:00" for h in range(24)]
    
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)], rotation=45)
    ax.set_yticks(range(12))
    ax.set_yticklabels(meses)
    
    # Etiquetas
    ax.set_title('Potencia AC Horaria Media por Mes - 2024',
                fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Hora del Día', fontsize=12)
    ax.set_ylabel('Mes', fontsize=12)
    
    # Colorbar
    cbar = plt.colorbar(im, ax=ax, label='Potencia [kW]')
    
    # Guardar gráfica
    path = save_matplotlib_figure(
        fig,
        "04_heatmap_horaria_mensual.png",
        subdir="solar/heatmaps",
        dpi=100,
        verbose=True
    )
    plt.close()
    
    print(f"\n✓ Gráfica guardada exitosamente")
    return path


def example_5_scatter_comparison():
    """
    EJEMPLO 5: Scatter plot - Comparación temperatura vs potencia
    
    Demuestra:
    - Scatter plots con múltiples series
    - Regresión lineal
    - Eje secundario
    """
    print("\n" + "="*70)
    print("EJEMPLO 5: Scatter Plot - Temperatura vs Potencia")
    print("="*70)
    
    # Crear datos sintéticos
    np.random.seed(42)
    n_puntos = 1000
    temperatura = np.random.normal(26, 4, n_puntos)  # Iquitos: ~26°C promedio
    
    # Potencia correlacionada negativa con temperatura
    # (operación inversa de coeficiente  de temperatura en módulos FV)
    ruido = np.random.normal(0, 300, n_puntos)
    potencia = 3500 - 80 * (temperatura - 26) + ruido
    potencia = np.clip(potencia, 0, 4000)
    
    # Crear figura
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Scatter plot
    scatter = ax.scatter(temperatura, potencia, c=temperatura, cmap='coolwarm',
                        s=50, alpha=0.6, edgecolor='black', linewidth=0.5)
    
    # Agregar línea de tendencia
    z = np.polyfit(temperatura, potencia, 2)  # Polinomio de grado 2
    p = np.poly1d(z)
    temp_sorted = np.sort(temperatura)
    ax.plot(temp_sorted, p(temp_sorted), "r-", linewidth=3, label='Tendencia (polinomio)')
    
    # Configurar gráfica
    ax.set_title('Relación Temperatura vs Potencia - Análisis Anual',
                fontsize=14, fontweight='bold')
    ax.set_xlabel('Temperatura [°C]', fontsize=12)
    ax.set_ylabel('Potencia AC [kW]', fontsize=12)
    
    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax, label='Temperatura [°C]')
    
    # Estadísticas
    correlacion = np.corrcoef(temperatura, potencia)[0, 1]
    texto_stats = f"""Estadísticas:
    Correlación: {correlacion:.3f}
    n puntos: {n_puntos}
    Temp media: {temperatura.mean():.1f}°C
    Potencia media: {potencia.mean():.0f} kW"""
    
    ax.text(0.02, 0.98, texto_stats, transform=ax.transAxes,
           fontsize=10, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # Guardar gráfica
    path = save_matplotlib_figure(
        fig,
        "05_scatter_temp_vs_potencia.png",
        subdir="solar/comparisons",
        dpi=100,
        verbose=True
    )
    plt.close()
    
    print(f"\n✓ Gráfica guardada exitosamente")
    return path


def main():
    """Ejecuta todos los ejemplos."""
    print("\n" + "="*70)
    print("EJEMPLOS DE USO - Infraestructura Gráfica solar_pvlib.py")
    print("="*70)
    
    print(f"\n📁 Directorio destino: {SOLAR_GRAPHICS_SUBDIR}")
    print(f"📊 Disponibilidad matplotlib: {is_matplotlib_available()}")
    
    if not is_matplotlib_available():
        print("\n⚠ matplotlib NO disponible - no se generarán gráficas")
        return
    
    # Ejecutar ejemplos
    paths = []
    try:
        paths.append(example_1_simple_line_plot())
        paths.append(example_2_bar_chart())
        paths.append(example_3_histogram())
        paths.append(example_4_heatmap())
        paths.append(example_5_scatter_comparison())
    except Exception as e:
        print(f"\n❌ Error durante ejecución: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN - GRÁFICAS GENERADAS")
    print("="*70)
    
    for i, path in enumerate(paths, 1):
        if path and path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"{i}. ✓ {path.name:40} ({size_kb:6.1f} KB)")
    
    print(f"\n📂 Ubicación: {SOLAR_GRAPHICS_SUBDIR.resolve()}")
    print(f"\n✅ COMPLETADO - {len(paths)} gráficas generadas exitosamente")
    print("="*70)


if __name__ == "__main__":
    main()
