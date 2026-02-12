# 🚀 Pipeline SAC - Producción

## Estado: ✅ FUNCIONAL Y LISTO PARA PRODUCCIÓN

### Uso Rápido

```bash
# Entrenamiento completo (3 episodios = 26,280 steps)
python -m scripts.train_sac_production

# Entrenamiento rápido (1 episodio = 8,760 steps)
python -m scripts.train_sac_production --episodes 1

# Continuar desde checkpoint existente
python -m scripts.train_sac_production --resume

# Solo evaluación (sin entrenar)
python -m scripts.train_sac_production --eval-only
```

### Configuración SAC Optimizada (RTX 4060 8GB)

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| **Batch Size** | 512 | Balance GPU/convergencia |
| **Buffer Size** | 200,000 | 11+ años de datos |
| **Learning Rate** | 5e-5 | Estabilidad gradientes |
| **Gamma** | 0.995 | Horizonte largo (1 año) |
| **Tau** | 0.02 | Target network update |
| **Hidden Layers** | (256, 256) | Evita overfitting |
| **Entropy Coeff** | auto | Adaptive exploration |
| **AMP** | Enabled | Acelera 30-40% en GPU |
| **Grad Clip** | 10.0 | Previene explosión |

### Multi-Objetivo (CO₂ Focus)

| Componente | Peso | Objetivo |
|------------|------|----------|
| **CO₂ Minimization** | 0.50 | Reducir emisiones grid |
| **Solar Self-Consumption** | 0.20 | Maximizar uso solar |
| **Cost Optimization** | 0.15 | Minimizar costo |
| **EV Satisfaction** | 0.10 | Cargar EVs target |
| **Grid Stability** | 0.05 | Evitar picos |

### Archivos Generados

```
outputs/agents/sac/
├── sac_summary.json        # Métricas finales
├── timeseries_sac.csv      # Serie temporal 8,760 horas
├── trace_sac.csv           # Observaciones/acciones
└── result_sac.json         # Resultado completo

checkpoints/sac/
├── sac_final.zip           # Modelo final entrenado
├── sac_step_1000.zip       # Checkpoint cada 1000 steps
├── sac_step_2000.zip
└── ...
```

### Métricas CO₂ (3 Componentes)

1. **CO₂ Emitido Grid**: Grid import × 0.4521 kg/kWh
2. **CO₂ Reducción Indirecta**: (Solar + BESS) × 0.4521 kg/kWh
3. **CO₂ Reducción Directa**: EV × 2.146 kg/kWh (vs gasolina)

**CO₂ NETO = Emitido - Indirecta - Directa**

Si CO₂ NETO < 0 → Sistema **CARBONO-NEGATIVO** ✅

### Dataset Dinámico EV (2026-02-03)

- **38 sockets** (30 motos + 8 mototaxis)
- **1,338,724 kWh/año** demanda EV total
- **~4,640 horas/charger** conectado (52.9% uptime)
- Modelo físico: SOC arrival/departure, capacidad batería, potencia charger

### Tiempo Estimado de Entrenamiento

| Episodios | Steps | GPU RTX 4060 | CPU |
|-----------|-------|--------------|-----|
| 1 | 8,760 | ~5-10 min | ~30-60 min |
| 3 | 26,280 | ~15-30 min | ~2-3 horas |
| 10 | 87,600 | ~1 hora | ~8 horas |

### Verificación Pre-Entrenamiento

```bash
python -c "
from pathlib import Path
schema = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
chargers = list(schema.parent.glob('charger_simulation_*.csv'))
print(f'Schema: {\"OK\" if schema.exists() else \"MISSING\"}'
print(f'Chargers: {len(chargers)}/128')
"
```

### Troubleshooting

| Error | Solución |
|-------|----------|
| `Schema no encontrado` | Ejecutar `python -m scripts.run_oe3_build_dataset` |
| `CUDA out of memory` | Reducir batch_size a 256 |
| `Checkpoints corruptos` | Eliminar `checkpoints/sac/` y reentrenar |
