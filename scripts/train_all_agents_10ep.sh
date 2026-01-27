#!/bin/bash
# Script to train all agents (SAC, PPO, A2C) for 10 episodes on CUDA
# Usage: ./scripts/train_all_agents_10ep.sh

echo "=============================================================="
echo " Training All RL Agents - 10 Episodes - CUDA"
echo "=============================================================="
echo ""

# Check if CUDA is available
python -c "import torch; assert torch.cuda.is_available(), 'CUDA not available!'; print(f'✓ CUDA available: {torch.cuda.get_device_name(0)}')" || {
    echo "ERROR: CUDA not available. Install PyTorch with CUDA support."
    echo "Visit: https://pytorch.org/get-started/locally/"
    exit 1
}

echo ""
echo "Starting training..."
echo "Agents: SAC, PPO, A2C"
echo "Episodes: 10"
echo "Device: cuda"
echo "Config: configs/default.yaml"
echo ""
echo "This may take 1-3 hours depending on your GPU."
echo "=============================================================="
echo ""

# Run the training script
python -m scripts.run_oe3_train_agents \
    --config configs/default.yaml \
    --agents SAC PPO A2C \
    --episodes 10 \
    --device cuda

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo "=============================================================="
    echo " ✓ Training Completed Successfully"
    echo "=============================================================="
    echo ""
    echo "Trained models saved in:"
    echo "  analyses/oe3/training/checkpoints/sac/sac_final.zip"
    echo "  analyses/oe3/training/checkpoints/ppo/ppo_final.zip"
    echo "  analyses/oe3/training/checkpoints/a2c/a2c_final.zip"
    echo ""
    echo "Training metrics:"
    echo "  analyses/oe3/training/progress/sac_progress.csv"
    echo "  analyses/oe3/training/progress/ppo_progress.csv"
    echo "  analyses/oe3/training/progress/a2c_progress.csv"
    echo ""
    echo "Learning curves:"
    echo "  analyses/oe3/training/sac_training.png"
    echo "  analyses/oe3/training/ppo_training.png"
    echo "  analyses/oe3/training/a2c_training.png"
    echo ""
else
    echo ""
    echo "=============================================================="
    echo " ✗ Training Failed"
    echo "=============================================================="
    echo ""
    echo "Check the error messages above for details."
    exit 1
fi
