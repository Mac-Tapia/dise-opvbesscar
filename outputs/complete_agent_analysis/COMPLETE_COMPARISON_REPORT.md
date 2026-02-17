# COMPLETE AGENT COMPARISON REPORT

## TRAINING SUMMARY

### A2C
- **Total Timesteps:** 87,600
- **Episodes:** 10
- **Training Duration:** 176.4 seconds
- **Training Speed:** 496.5 steps/sec
- **Learning Rate:** 0.0003
- **Gamma:** 0.99
- **GAE Lambda:** 0.95

### PPO
- **Total Timesteps:** 87,600
- **Episodes:** 10
- **Training Duration:** 175.6 seconds
- **Training Speed:** 498.8 steps/sec
- **Learning Rate:** 0.0001
- **Gamma:** 0.88
- **GAE Lambda:** 0.97

### SAC
- **Total Timesteps:** 0
- **Episodes:** 0
- **Training Duration:** 0.0 seconds
- **Training Speed:** 0.0 steps/sec
- **Learning Rate:** 0
- **Gamma:** 0
- **GAE Lambda:** 0

## REWARD METRICS

### A2C
- **Final Reward:** 3036.82
- **Best Reward:** 3036.82
- **Average Reward:** 2725.09
- **Mean Validation Reward:** 3062.62

### PPO
- **Final Reward:** 1014.44
- **Best Reward:** 1014.44
- **Average Reward:** 818.55
- **Mean Validation Reward:** 659.35

### SAC
- **Final Reward:** 0.67
- **Best Reward:** 0.68
- **Average Reward:** 0.67
- **Mean Validation Reward:** 0.00

## CO2 METRICS

### A2C
- **Final CO2 Grid (kg):** 2115420
- **Best CO2 Grid (kg):** 2104618
- **Average CO2 Grid (kg):** 2200222
- **Mean CO2 Avoided (kg):** 4428720
- **Mean Grid Import (kWh):** 4680326
- **Mean Solar Available (kWh):** 8292514

### PPO
- **Final CO2 Grid (kg):** 2738263
- **Best CO2 Grid (kg):** 2738263
- **Average CO2 Grid (kg):** 3074701
- **Mean CO2 Avoided (kg):** 4409364
- **Mean Grid Import (kWh):** 5335239
- **Mean Solar Available (kWh):** 8292514

### SAC
- **Final CO2 Grid (kg):** 2940169
- **Best CO2 Grid (kg):** 2586090
- **Average CO2 Grid (kg):** 2904378
- **Mean CO2 Avoided (kg):** 0
- **Mean Grid Import (kWh):** 0
- **Mean Solar Available (kWh):** 0

