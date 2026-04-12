#!/bin/bash
# Docker entrypoint script for PVBESSCAR
# Modos: pipeline | sac | ppo | a2c | jupyter | shell
set -e

echo "=========================================================="
echo " PVBESSCAR — Iquitos EV Charging RL System"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================================="

# ── Verificaciones base ────────────────────────────────────────
python_version=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python: $python_version"

python -c "
import torch
device = 'cuda' if torch.cuda.is_available() else 'cpu'
if device == 'cuda':
    gpu = torch.cuda.get_device_name(0)
    mem = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f'✓ GPU: {gpu} ({mem:.1f} GB VRAM) | CUDA {torch.version.cuda}')
else:
    print('⚠ GPU no disponible — modo CPU')
" || echo "⚠ torch no disponible"

# ── Crear directorios necesarios ───────────────────────────────
mkdir -p /app/data/interim/oe2/{solar,chargers,bess}
mkdir -p /app/outputs/{oe3/{checkpoints,results},sac_training,ppo_training,a2c_training}
mkdir -p /app/checkpoints/{SAC_CityLearn,PPO_CityLearn,A2C_CityLearn}
mkdir -p /app/logs/{training/{sac_citylearn,ppo_citylearn,a2c_citylearn},tensorboard/{sac_citylearn,ppo_citylearn,a2c_citylearn}}
echo "✓ Directorios listos"
echo ""

# ── Modo de ejecución ──────────────────────────────────────────
MODE=${MODE:-${1:-pipeline}}
CONFIG_FILE=${CONFIG_FILE:-"/app/configs/default.yaml"}
TIMESTEPS=${TIMESTEPS:-438000}     # 50 episodes × 8760 h/año

echo "Modo:       $MODE"
echo "Config:     $CONFIG_FILE"
echo "Timesteps:  $TIMESTEPS"
echo ""

case "$MODE" in

  # ── SAC Training (recomendado — off-policy, mejor para CO2 asimétrico) ──
  sac)
    echo ">> SAC Training: Soft Actor-Critic"
    echo "   Checkpoints: /app/checkpoints/SAC_CityLearn/"
    echo "   TensorBoard:  /app/logs/tensorboard/sac_citylearn/"
    echo ""
    exec python scripts/train/train_sac_citylearn.py --timesteps "$TIMESTEPS"
    ;;

  # ── PPO Training ─────────────────────────────────────────────
  ppo)
    echo ">> PPO Training: Proximal Policy Optimization"
    exec python scripts/train/train_ppo_multiobjetivo.py --timesteps "$TIMESTEPS"
    ;;

  # ── A2C Training ─────────────────────────────────────────────
  a2c)
    echo ">> A2C Training: Advantage Actor-Critic"
    exec python scripts/train/train_a2c_citylearn.py --timesteps "$TIMESTEPS"
    ;;

  # ── Pipeline OE2 → OE3 completo ──────────────────────────────
  pipeline)
    SKIP_OE2=${SKIP_OE2:-false}
    echo ">> Pipeline OE2 → OE3 (skip_oe2=$SKIP_OE2)"
    if [ "$SKIP_OE2" = "true" ]; then
        exec python -m scripts.run_oe3_simulate --config "$CONFIG_FILE"
    else
        exec python -m scripts.run_pipeline --config "$CONFIG_FILE"
    fi
    ;;

  # ── Jupyter Lab (análisis interactivo) ───────────────────────
  jupyter)
    echo ">> Jupyter Lab en http://localhost:8888"
    exec jupyter lab --ip=0.0.0.0 --allow-root --no-browser \
        --NotebookApp.token='' --NotebookApp.password=''
    ;;

  # ── Shell interactiva para debug ──────────────────────────────
  shell | bash)
    exec /bin/bash
    ;;

  # ── Pasar comandos directamente ───────────────────────────────
  *)
    exec "$@"
    ;;

esac
