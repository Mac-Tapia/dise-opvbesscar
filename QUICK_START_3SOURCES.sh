#!/bin/bash
# 🚀 QUICK START: TRAINING CON LAS 3 FUENTES DE CO₂ (2026-02-02)

echo "=================================="
echo "TRAINING: 3 VECTORES DE CO₂"
echo "=================================="
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}[INFO]${NC} Sistema listo para training con:"
echo -e "${GREEN}  ✅ Vector 1: Solar directo (indirecta)${NC}"
echo -e "${GREEN}  ✅ Vector 2: BESS descarga (indirecta)${NC}"
echo -e "${GREEN}  ✅ Vector 3: EV carga (directa)${NC}"
echo ""

# Step 1: Verify dataset
echo -e "${YELLOW}[STEP 1/4]${NC} Verificando dataset..."
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dataset OK${NC}"
else
    echo -e "${YELLOW}⚠️  Dataset rebuild started${NC}"
fi
echo ""

# Step 2: Run baseline (uncontrolled)
echo -e "${YELLOW}[STEP 2/4]${NC} Ejecutando baseline (sin control)..."
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
echo -e "${GREEN}✅ Baseline completado${NC}"
echo ""

# Step 3: Train SAC, PPO, A2C
echo -e "${YELLOW}[STEP 3/4]${NC} Entrenando agentes (SAC, PPO, A2C)..."
python -m scripts.run_oe3_simulate --config configs/default.yaml
echo -e "${GREEN}✅ Training completado${NC}"
echo ""

# Step 4: Compare results with 3-source breakdown
echo -e "${YELLOW}[STEP 4/4]${NC} Comparando resultados (3 fuentes de CO₂)..."
python -m scripts.run_oe3_co2_table --config configs/default.yaml
echo -e "${GREEN}✅ Análisis completado${NC}"
echo ""

echo "=================================="
echo -e "${GREEN}✅ TRAINING COMPLETADO${NC}"
echo "=================================="
echo ""

echo "📊 RESULTADOS DISPONIBLES EN:"
echo "  • outputs/oe3_simulations/ (timeseries y métricas)"
echo "  • checkpoints/ (modelos entrenados)"
echo "  • analyses/ (análisis detallados)"
echo ""

echo "🔍 PARA VER EL DESGLOSE DE 3 FUENTES:"
echo "  cat outputs/oe3_simulations/*.log | grep -A 30 'CO₂ BREAKDOWN'"
echo ""

echo "📈 PARA COMPARAR AGENTES:"
echo "  head -20 outputs/oe3_simulations/co2_comparison.csv"
echo ""
