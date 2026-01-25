# 🤖 Documentación SAC TIER 2

Documentación especializada para el algoritmo SAC (Soft Actor-Critic) en TIER 2.

## 📑 Contenido Consolidado

### Principal

  | Archivo | Descripción |  
| --------- | ------------- |
  | **SAC_TIER2_IMPLEMENTATION_STEP_BY_STEP.md** | 🔧 Implementación... |  
  | **SAC_TIER2_OPTIMIZATION.md** | ⚙️ Optimizaciones específicas SAC |  
  | **SAC_TIER2_QUICK_START.md** | 🚀 Inicio rápido SAC TIER 2 |  

### Referencias

  | Archivo | Descripción |  
| --------- | ------------- |
  | SAC_TIER2_INDICE.md | 📖 Índice de contenidos SAC |  
  | SAC_TIER2_START_HERE.md | 🎯 Comienza aquí SAC |  
  | SAC_TIER2_RESUMEN_EJECUTIVO.md | 📊 Resumen ejecutivo |  
  | SAC_LEARNING_RATE_FIX_REPORT.md | 🔨 Reporte de corrección LR |  

## 📌 Características SAC TIER 2

### Configuración

- **Learning Rate**: 2.5e-4
- **Batch Size**: 256
- **Hidden Sizes**: (512, 512)
- **Entropy Coef**: 0.02
- **Target Entropy**: -40

### Optimizaciones

✅ Normalización adaptativa de recompensas
✅ Baselines dinámicas por hora
✅ Bonuses BESS (almacenamiento)
✅ Update per timestep: 2x
✅ Dropout: 0.1 (regularización)

## 🎯 Recomendado Leer

**Primero**: `SAC_TIER2_QUICK_START.md`
**Luego**: `SAC_TIER2_IMPLEMENTATION_STEP_BY_STEP.md`
**Detalle**: `SAC_TIER2_OPTIMIZATION.md`

## 🔗 Para información general

Ver: `../00_INDEX_MAESTRO_CONSOLIDADO.md`