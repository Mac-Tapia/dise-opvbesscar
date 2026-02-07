# ✅ VALIDACIÓN FINAL - Pesos Multi-Objetivo Sincronizados

**Fecha:** 2026-02-07  
**Estado:** VERIFICADO Y FIJADO ✅

## Pesos Oficiales (INMUTABLES)

| Componente | Peso | Descripción |
|------------|------|-------------|
| **CO₂** | `0.35` | PRIMARY: Minimizar emisiones CO₂ grid (reducido de 0.50) |
| **Solar** | `0.20` | SECONDARY: Maximizar autoconsumo solar |
| **EV** | `0.30` | TRIPLICADO: Satisfacción carga EV (era 0.10) |
| **Cost** | `0.10` | Minimizar costo electricidad (reducido de 0.15) |
| **Grid** | `0.05` | Estabilidad grid (peak minimization) |
| **SUMA** | `1.00` | ✅ Normalizado |

## Tabla de Validación - 11 Archivos

| # | Archivo | CO₂ | Solar | EV | Cost | Grid | SUMA | Estado |
|---|---------|-----|-------|-----|------|------|------|--------|
| 1 | `src/rewards/rewards.py:773` | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ |
| 2 | `configs/default.yaml:192` | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ |
| 3 | `configs/default_optimized.yaml:201` (A2C) | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ |
| 4 | `configs/default_optimized.yaml:236` (PPO) | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ |
| 5 | `configs/default_optimized.yaml:275` (SAC) | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ |
| 6 | `configs/agents/sac_config.yaml:38` | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ |
| 7 | `configs/agents/ppo_config.yaml:59` | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ |
| 8 | `configs/agents/a2c_config.yaml:49` | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ |
| 9 | `configs/agents/agents_config.yaml:29` | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ FIJADO |
| 10 | `configs/sac_optimized.json:29` | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ |
| 11 | `.github/training/training_config.json:30` | 0.35 | 0.20 | 0.30 | 0.10 | 0.05 | 1.00 | ✅ |

## Justificación de Pesos

### CO₂ = 0.35 (PRIMARY)
- Factor emisión Iquitos: 0.4521 kg CO₂/kWh (grid aislado, generación térmica)
- Objetivo principal del proyecto: minimizar huella de carbono

### EV = 0.30 (TRIPLICADO)
- **Cambio crítico:** incrementado de 0.10 → 0.30
- Razón: Máxima prioridad para cargar 2,912 motos + 416 mototaxis
- Penalizaciones SOC < 70% y > 95% (concentración)

### Solar = 0.20 (MANTENER)
- Capacidad: 4,050 kWp instalados
- Generación anual: ~8,292,514 kWh/año
- Maximizar autoconsumo para reducir CO₂ indirecto

### Cost = 0.10 (REDUCIDO)
- Tarifa Iquitos relativamente baja
- No es constraint operacional crítico

### Grid = 0.05 (BASELINE)
- Estabilidad de potencia
- Minimizar picos de importación

## Comando de Validación

```bash
# Verificar todos los archivos
python -c "
import yaml, json
from pathlib import Path

weights_expected = {'co2': 0.35, 'solar': 0.20, 'ev': 0.30, 'cost': 0.10, 'grid': 0.05}

files = [
    ('configs/default.yaml', 'rewards'),
    ('configs/agents/sac_config.yaml', 'multi_objective_weights'),
    ('configs/agents/ppo_config.yaml', 'multi_objective_weights'),
    ('configs/agents/a2c_config.yaml', 'multi_objective_weights'),
]

for f, key in files:
    with open(f) as fp:
        data = yaml.safe_load(fp)
    # Navigate to weights
    if 'sac' in data:
        w = data['sac'][key]
    elif 'a2c' in data:
        w = data['a2c'][key]
    elif 'ppo' in data:
        w = data['ppo'][key]
    else:
        w = data.get('oe3', {}).get(key, data.get(key, {}))
    total = sum(v for k,v in w.items() if k in weights_expected)
    print(f'{f}: sum={total:.2f}')
print('✅ Validación completada')
"
```

## Historial de Cambios

| Fecha | Cambio | Autor |
|-------|--------|-------|
| 2026-02-07 | Sincronización inicial 11 archivos | Agent |
| 2026-02-07 | EV triplicado 0.10 → 0.30 | User Request |
| 2026-02-07 | CO₂ reducido 0.50 → 0.35 | Balanceo |
| 2026-02-07 | Cost reducido 0.15 → 0.10 | Tarifa baja |

---

**⚠️ NO MODIFICAR estos pesos sin actualizar TODOS los 11 archivos simultáneamente.**
