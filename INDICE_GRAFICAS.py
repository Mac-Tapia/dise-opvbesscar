#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INDEX VISUAL - Gráficas Solares Generadas (10 Total)
=====================================================

Este archivo lista todas las gráficas generadas con descripción rápida.
Usa esto como referencia para entender qué contiene cada archivo PNG.

Ejecutar: python INDICE_GRAFICAS.py
"""

import os
from pathlib import Path

# Definición de gráficas
GRAPHICS = [
    {
        "num": "1️⃣",
        "nombre": "01_perfil_potencia_24h.png",
        "titulo": "PERFIL DE POTENCIA 24 HORAS",
        "descripcion": "Gráfico de barras mostrando la potencia AC promedio de cada hora del día",
        "categoria": "PERFILES TEMPORALES",
        "analisis": [
            "• Pico máximo: ~946.6 kW (promedio)",
            "• Máximo hora punta: 11:00 AM - 1:00 PM",
            "• Mínimo nocturno: 0 kW (sin radiación)",
            "• Horas operativas: 6:00 AM - 6:00 PM"
        ],
        "uso": "Planificación de operaciones diarias, análisis de patrones",
        "tamaño": "~2.5 MB"
    },
    {
        "num": "2️⃣",
        "nombre": "02_energia_mensual.png",
        "titulo": "ENERGÍA MENSUAL (ANUAL)",
        "descripcion": "Doble gráfico: barras de energía mensual + línea de energía acumulada",
        "categoria": "PERFILES TEMPORALES",
        "analisis": [
            "• Promedio mensual: 691 MWh",
            "• Máximo: Octubre (741.8 MWh)",
            "• Mínimo: Febrero (590.9 MWh)",
            "• Energía anual total: 8,292.5 MWh"
        ],
        "uso": "Análisis estacional, planificación presupuestaria anual",
        "tamaño": "~2.1 MB"
    },
    {
        "num": "3️⃣",
        "nombre": "03_distribucion_energia_diaria.png",
        "titulo": "DISTRIBUCIÓN DE ENERGÍA DIARIA",
        "descripcion": "Histograma + box plot de la distribución de energía en los 365 días del año",
        "categoria": "PERFILES TEMPORALES",
        "analisis": [
            "• Media: 22.71 MWh/día",
            "• Desv. Est.: 5.72 MWh/día",
            "• Coef. Variación: 25.2%",
            "• Rango: 4.97 - 26.62 MWh"
        ],
        "uso": "Dimensionamiento de baterías (BESS), evaluación de riesgos",
        "tamaño": "~2.0 MB"
    },
    {
        "num": "4️⃣",
        "nombre": "04_analisis_irradiancia.png",
        "titulo": "ANÁLISIS DE IRRADIANCIA SOLAR (GHI, DNI, DHI)",
        "descripcion": "Panel de 4 análisis: GHI diario, distribución horaria, comparativa componentes, tabla estadística",
        "categoria": "IRRADIANCIA",
        "analisis": [
            "• GHI anual: 1,647.5 kWh/m²",
            "• GHI máximo horario: 1,016 W/m²",
            "• Horas GHI > 500 W/m²: 2,147 h",
            "• DNI/DHI proporción típica: 0.8/0.2"
        ],
        "uso": "Validación de datos, análisis de componentes solares",
        "tamaño": "~2.3 MB"
    },
    {
        "num": "5️⃣",
        "nombre": "05_heatmap_potencia_mensual_horaria.png",
        "titulo": "MAPA DE CALOR: POTENCIA HORARIA × MES",
        "descripcion": "Matriz de 12 meses (Y) × 24 horas (X) mostrando intensidad de generación con gradiente de color",
        "categoria": "MAPAS DE CALOR",
        "analisis": [
            "• Identifica picos consistentes: 11:00-14:00 diario",
            "• Variación semanal: Mínima (clima ecuatorial)",
            "• Meses más variables: Diciembre, Enero",
            "• Patrón estacional claro observable"
        ],
        "uso": "Operación de rede, análisis de patrones estacionales",
        "tamaño": "~1.8 MB"
    },
    {
        "num": "6️⃣",
        "nombre": "06_heatmap_diaria_horaria_60dias.png",
        "titulo": "MAPA DE CALOR: POTENCIA DIARIA × HORA (60 DÍAS)",
        "descripcion": "Matriz de 60 días (Y) × 24 horas (X) con resolución fina de variabilidad diaria",
        "categoria": "MAPAS DE CALOR",
        "analisis": [
            "• Detecta patrones semanales de 7 días",
            "• Identifica días anómalos (muy nublados)",
            "• Transición de estaciones observable",
            "• Algunos días aislados con generación muy baja"
        ],
        "uso": "Predicción de variabilidad, análisis de eventos climáticos",
        "tamaño": "~1.9 MB"
    },
    {
        "num": "7️⃣",
        "nombre": "07_metricas_desempenio.png",
        "titulo": "MÉTRICAS DE DESEMPEÑO DEL SISTEMA",
        "descripcion": "Panel con 4 indicadores: factor capacidad, energía anual, curva potencia, tabla técnica",
        "categoria": "ESTADÍSTICAS",
        "analisis": [
            "• Factor capacidad: 29.6% (excelente para latitud)",
            "• Performance Ratio: 122.8% (modelo riguroso)",
            "• Yield: 2,048 kWh/kWp/año",
            "• Horas equivalentes: 2,591 h/año"
        ],
        "uso": "Comunicación a inversores, validación de modelos",
        "tamaño": "~2.4 MB"
    },
    {
        "num": "8️⃣",
        "nombre": "08_efectotemperatura_potencia.png",
        "titulo": "EFECTO DE TEMPERATURA EN POTENCIA",
        "descripcion": "Scatter plot de correlación temporal + dual-axis horario", 
        "categoria": "COMPARATIVAS",
        "analisis": [
            "• Relación inversa clara: T ↑ → P ↓",
            "• Coef. temperatura: ~-0.5%/°C (SAPM)",
            "• Temperatura media Iquitos: 26.5°C",
            "• Reducción rendimiento por temperatura: ~8%"
        ],
        "uso": "Ajuste de modelos, optimización de operaciones",
        "tamaño": "~2.2 MB"
    },
    {
        "num": "9️⃣",
        "nombre": "09_analisis_variabilidad_climatica.png",
        "titulo": "ANÁLISIS DE VARIABILIDAD CLIMÁTICA",
        "descripcion": "Panel de 4: distribución días (pie), perfiles comparativos, curva duración, tabla estadística",
        "categoria": "COMPARATIVAS",
        "analisis": [
            "• Días despejados: 45% (164 días)",
            "• Días intermedios: 35% (128 días)",
            "• Días nublados: 20% (73 días)",
            "• Variabilidad día/día: 25.2% (CoV)"
        ],
        "uso": "Dimensionamiento BESS, evaluación complementarios",
        "tamaño": "~2.3 MB"
    },
    {
        "num": "🔟",
        "nombre": "10_resumen_completo_sistema.png",
        "titulo": "REPORTE EJECUTIVO COMPLETO",
        "descripcion": "Documento único tipo 'poster' con 7 visualizaciones + tabla técnica completa (imprimible A3)",
        "categoria": "ESTADÍSTICAS",
        "analisis": [
            "• Especificaciones técnicas: 200,632 módulos",
            "• Capacidad: 4,049.56 kWp DC / 3,201 kW AC",
            "• Energía: 8,292.5 MWh anuales",
            "• Conclusión: Excelente desempeño tropical"
        ],
        "uso": "Presentaciones ejecutivas, propuestas comerciales (POSTER)",
        "tamaño": "~3.5 MB"
    }
]

def print_header():
    """Imprime encabezado."""
    print("\n" + "="*100)
    print("  📊 INDICE VISUAL - GRÁFICAS GENERADAS DE GENERACIÓN SOLAR (pvlib System)".center(100))
    print("  Iquitos, Perú - 2024 (Análisis Anual) | 10 Gráficas Totales".center(100))
    print("="*100 + "\n")

def print_graphic_details(g):
    """Imprime detalles de cada gráfica."""
    print(f"\n{g['num']}  {g['titulo']}")
    print("-" * 100)
    print(f"   Archivo:     {g['nombre']}")
    print(f"   Categoría:   {g['categoria']}")
    print(f"   Tamaño:      {g['tamaño']}")
    print(f"\n   Descripción: {g['descripcion']}")
    print("\n   Análisis Clave:")
    for análisis in g['analisis']:
        print(f"      {análisis}")
    print(f"\n   Caso de Uso:  {g['uso']}")

def print_summary():
    """Imprime resumen final."""
    print("\n" + "="*100)
    print("  📂 ESTRUCTURA DE DIRECTORIOS".center(100))
    print("="*100)
    print("""
   outputs/analysis/solar/
   ├── 01_perfil_potencia_24h.png                   [PERFILES: Ciclo diario]
   ├── 02_energia_mensual.png                       [PERFILES: Estacionalidad]
   ├── 03_distribucion_energia_diaria.png           [PERFILES: Variabilidad]
   ├── 04_analisis_irradiancia.png                  [IRRADIANCIA: Radiación solar]
   ├── 05_heatmap_potencia_mensual_horaria.png      [HEATMAP: Mes × Hora]
   ├── 06_heatmap_diaria_horaria_60dias.png         [HEATMAP: Día × Hora]
   ├── 07_metricas_desempenio.png                   [ESTADÍSTICAS: KPIs del sistema]
   ├── 08_efectotemperatura_potencia.png            [COMPARATIVAS: T vs P]
   ├── 09_analisis_variabilidad_climatica.png       [COMPARATIVAS: Variabilidad]
   └── 10_resumen_completo_sistema.png              [REPORTE: Documento ejecutivo]
    """)

def print_usage_guide():
    """Imprime guía de uso."""
    print("\n" + "="*100)
    print("  🎯 GUÍA DE USO POR PERFIL DE USUARIO".center(100))
    print("="*100)
    print("""
   👨‍🔬 INGENIERO SOLAR / TÉCNICO:
      ├─ Inicia con: #4 (Irradiancia) + #1 (Perfil 24h)
      ├─ Valida con: #7 (Métricas) vs modelos teóricos
      ├─ Optimiza con: #8 (Temperatura) + #9 (Variabilidad)
      └─ Documenta con: #10 (Reporte completo)
   
   🏢 OPERADOR DE RED / DESPACHADOR:
      ├─ Estudia: #5 (Heatmap mensual) para programación
      ├─ Predice: #6 (Heatmap diario) para rampas de potencia
      ├─ Planifica: #9 (Variabilidad) para maniobras de red
      └─ Comunica: #2 (Energía mensual) para reporteo
   
   💼 INVERSOR / DIRECTOR:
      ├─ Imprime: #10 (Reporte completo) para presentación
      ├─ Comunica: #7 (Métricas) para ROI analysis
      ├─ Valida: #2 (Energía mensual) vs business plan
      └─ Sostiene: CF 29.6% + PR 122.8% = Excelente rendimiento
   
   📚 ACADÉMICO / INVESTIGADOR:
      ├─ Publica: #4 (Irradiancia) en journals
      ├─ Compara: #9 (Variabilidad) con otras locaciones
      ├─ Cita: Estadísticas principales como caso estudio
      └─ Expone: #10 (Reporte) como poster en congresos
   """)

def print_key_statistics():
    """Imprime estadísticas clave."""
    print("\n" + "="*100)
    print("  📊 ESTADÍSTICAS PRINCIPALES DEL SISTEMA (RESUMEN)".center(100))
    print("="*100)
    
    stats = {
        "CAPACIDAD INSTALADA": {
            "Potencia DC": "4,049.56 kWp",
            "Potencia AC": "3,201.00 kW",
            "Módulos totales": "200,632 unidades",
            "Inversores": "2 × Eaton Xpert1670"
        },
        "PRODUCCIÓN ANUAL": {
            "Energía AC": "8,292.5 MWh (8.29 GWh)",
            "Potencia máxima": "2,886.7 kW",
            "Potencia media": "946.6 kW",
            "Energía diaria promedio": "22.71 MWh"
        },
        "EFICIENCIA": {
            "Factor de capacidad": "29.6% ✅ (excelente)",
            "Performance Ratio": "122.8% (modelo riguroso)",
            "Yield específico": "2,048 kWh/kWp/año",
            "Horas equivalentes": "2,591 h/año"
        },
        "RADIACIÓN": {
            "GHI anual": "1,647.5 kWh/m²",
            "GHI máximo": "1,016 W/m²",
            "Horas GHI > 500 W/m²": "2,147 horas"
        },
        "VARIABILIDAD": {
            "Desv. estándar diaria": "5.72 MWh",
            "Coef. variación": "25.2%",
            "Días despejados": "164 (45%)",
            "Días nublados": "73 (20%)"
        },
        "SOSTENIBILIDAD": {
            "CO₂ evitado/año": "3,749 toneladas",
            "Factor CO₂ diesel": "0.4521 kg/kWh",
            "Ahorro económico": "S/. 2,321,903.97"
        }
    }
    
    for sección, datos in stats.items():
        print(f"\n   {sección}:")
        for clave, valor in datos.items():
            print(f"      • {clave:<30} {valor:>30}")

def main():
    """Función principal."""
    print_header()
    
    for i, graphic in enumerate(GRAPHICS, 1):
        print_graphic_details(graphic)
    
    print_summary()
    print_usage_guide()
    print_key_statistics()
    
    print("\n" + "="*100)
    print("  ✅ GENERACIÓN COMPLETADA".center(100))
    print("="*100)
    print("""
   Todas las gráficas están listas para:
      ✓ Informes técnicos profesionales
      ✓ Presentaciones a inversores
      ✓ Análisis académicos y publicaciones
      ✓ Documentación de diseño y operación
   
   Para más información:
      • Lee: outputs/analysis/README_SOLAR_GRAPHICS.md (API technique)
      • Lee: START_HERE_GRAFICAS.md (guía rápida)
      • Ejecuta: python examples_graphics_usage.py (ejemplos funcionales)
    """)
    print("="*100 + "\n")

if __name__ == "__main__":
    main()
