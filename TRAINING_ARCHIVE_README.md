# Training Results Archive Documentation

## Overview

The `training_results_archive.json` file is a comprehensive record of all completed RL agent training sessions for the pvbesscar OE3 (Optimization and Control) project in Iquitos, Perú.

## Purpose

This archive serves multiple purposes:

1. **Historical Record**: Permanent record of all training runs with detailed metrics
2. **Comparison Reference**: Baseline for comparing future training iterations
3. **Reproducibility**: Complete configuration details for reproducing results
4. **Performance Tracking**: Track improvements across different agent implementations

## Structure

The archive contains the following main sections:

### Metadata
- Project information and location
- Generation timestamp
- Archive version
- Training completion status

### Baseline
Reference metrics from uncontrolled scenario (no intelligent EV charging management):
- Annual grid import: 6,117,383 kWh
- Annual CO₂ emissions: 2,765,669 kg
- Solar utilization: 2,870,435 kWh

### Agents

Training results for three RL algorithms:

#### SAC (Soft Actor-Critic)
- **Type**: Off-policy
- **Status**: COMPLETED
- **Training Duration**: 2h 46min
- **CO₂ Reduction**: 99.93%
- **Best For**: Highest reward values, excellent sample efficiency

#### PPO (Proximal Policy Optimization)
- **Type**: On-policy
- **Status**: COMPLETED
- **Training Duration**: 2h 26min (fastest)
- **CO₂ Reduction**: 99.93%
- **Best For**: Balance of speed, stability, and efficiency

#### A2C (Advantage Actor-Critic)
- **Type**: On-policy
- **Status**: COMPLETED
- **Training Duration**: 2h 36min
- **CO₂ Reduction**: 99.94% (best)
- **Best For**: Best energy efficiency, lowest grid import

### Comparison Summary

Quick reference for agent selection based on different criteria:
- **Best Energy Efficiency**: A2C
- **Fastest Training**: PPO
- **Highest Reward**: SAC
- **Best All-Around**: PPO

## Verification

To verify the integrity of the archive file, run:

```bash
python3 verify_training_archive.py
```

This will:
- Validate JSON structure
- Check all required sections exist
- Verify agent completion status
- Display summary of results

## File Location

- **Archive File**: `training_results_archive.json`
- **Verification Script**: `verify_training_archive.py`
- **Documentation**: `TRAINING_ARCHIVE_README.md` (this file)

## Training Details

### Configuration
- **Episodes**: 3 per agent
- **Timesteps per Episode**: 8,760 (1 year hourly)
- **Total Timesteps**: 26,280 per agent
- **Observation Space**: 534 dimensions
- **Action Space**: 126 dimensions (126 controllable EV chargers)

### Hardware
- **Primary Device**: CUDA-enabled GPU (RTX 4060) for SAC and PPO
- **Fallback**: CPU for A2C
- **Average Training Speed**: 158-180 steps/minute

### Key Results

All three agents achieved remarkable reductions compared to baseline:

| Metric | Baseline | SAC | PPO | A2C |
|--------|----------|-----|-----|-----|
| Grid Import (kWh/year) | 6,117,383 | 4,000 | 3,984 | 3,494 |
| CO₂ (kg/year) | 2,765,669 | 1,808 | 1,806 | 1,580 |
| Reduction (%) | - | 99.93% | 99.93% | 99.94% |

## Restoration

If the archive file is lost or corrupted:

1. **Check Git History**:
   ```bash
   git log --all --full-history -- training_results_archive.json
   git show <commit-hash>:training_results_archive.json > training_results_archive.json
   ```

2. **Verify After Restoration**:
   ```bash
   python3 verify_training_archive.py
   ```

3. **Regenerate from Checkpoints** (if original is unrecoverable):
   - Load agent checkpoints from `checkpoints/{SAC,PPO,A2C}/`
   - Re-run evaluation to generate fresh metrics
   - Reconstruct archive JSON manually

## Related Files

- Training Reports:
  - `REPORTE_ENTRENAMIENTO_SAC_FINAL.md`
  - `REPORTE_ENTRENAMIENTO_PPO_FINAL.md`
  - `REPORTE_ENTRENAMIENTO_A2C_DETALLADO.md`
- Comparison Tables:
  - `TABLA_COMPARATIVA_FINAL_CORREGIDA.md`
- Checkpoints:
  - `checkpoints/sac/` (53 checkpoints)
  - `checkpoints/ppo/` (53 checkpoints)
  - `checkpoints/a2c/` (131 checkpoints)

## Version History

- **v1.0** (2026-01-29): Initial archive with 3 completed agent training runs
  - SAC: 26,280 timesteps over 2h 46min
  - PPO: 26,280 timesteps over 2h 26min
  - A2C: 26,280 timesteps over 2h 36min

## Contact & Support

For questions about the training archive:
1. Review this documentation
2. Run verification script to check file integrity
3. Consult detailed training reports in `REPORTE_*` files
4. Check project documentation in `README.md`

---

**Last Updated**: 2026-02-15  
**Archive Status**: ✓ Valid and Complete  
**Total Training Time**: 7h 48min across all agents
