#!/bin/bash
# Script para regenerar todas las gráficas de OE2 y OE3
# Requiere Python 3.11 y dependencias instaladas

set -e  # Salir si algún comando falla

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  REGENERACIÓN DE GRÁFICAS OE2 Y OE3                          ║"
echo "║  Proyecto: Infraestructura de Carga EV - Mall de Iquitos    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Verificar Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Error: Python 3.11 no encontrado"
    echo "   Instala Python 3.11 primero"
    exit 1
fi

echo "✓ Python 3.11 encontrado"
echo ""

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    echo "▶ Activando entorno virtual..."
    source .venv/bin/activate
    echo "✓ Entorno activado"
else
    echo "⚠ No se encontró .venv, usando Python del sistema"
fi

CONFIG="${1:-configs/default.yaml}"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  FASE 1: OE2 - DIMENSIONAMIENTO                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "▶ 1.1 Dimensionamiento Solar (PV)..."
python -m scripts.run_oe2_solar --config "$CONFIG"

echo ""
echo "▶ 1.2 Dimensionamiento Cargadores EV..."
python -m scripts.run_oe2_chargers --config "$CONFIG"

echo ""
echo "▶ 1.3 Dimensionamiento BESS..."
python -m scripts.run_oe2_bess --config "$CONFIG"

echo ""
echo "▶ 1.4 Gráficas Solar..."
python -m scripts.run_oe2_solar_plots --config "$CONFIG"

echo ""
echo "▶ 1.5 Reporte completo OE2..."
python -m scripts.generate_oe2_report

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  FASE 2: OE3 - SIMULACIÓN Y AGENTES                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "▶ 2.1 Construcción dataset CityLearn..."
python -m scripts.run_oe3_build_dataset --config "$CONFIG"

echo ""
echo "▶ 2.2 Simulación y entrenamiento agentes..."
python -m scripts.run_oe3_simulate --config "$CONFIG"

echo ""
echo "▶ 2.3 Tabla comparativa CO₂..."
python -m scripts.run_oe3_co2_table --config "$CONFIG"

echo ""
echo "▶ 2.4 Gráficas de entrenamiento..."
python -m scripts.plot_oe3_training --config "$CONFIG"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✓ COMPLETADO - TODAS LAS GRÁFICAS REGENERADAS              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Gráficas generadas en:"
echo "  - reports/oe2/"
echo "  - reports/oe2/solar_plots/"
echo "  - analyses/oe3/training/"
echo "  - reports/oe3/"
echo ""
