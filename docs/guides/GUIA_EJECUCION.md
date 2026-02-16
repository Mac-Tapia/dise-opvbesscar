# 🚀 Guía de Ejecución - PVBESSCAR

## Descripción General

Este documento explica cómo ejecutar el sistema de optimización de carga EV con Solar PV + BESS mediante Reinforcement Learning utilizando el nuevo punto de entrada unificado `ejecutar.py`.

## Requisitos del Sistema

### Hardware Recomendado
- **CPU**: 8+ cores (Intel i7/i9 o AMD Ryzen 7/9)
- **RAM**: 16 GB mínimo, 32 GB recomendado
- **GPU**: NVIDIA RTX 4060 o superior (opcional pero recomendado)
  - 15-30 min training con GPU
  - 2-10 horas training con CPU
- **Almacenamiento**: 50 GB libres

### Software
- **Python**: 3.11 (recomendado) o 3.12
- **Sistema Operativo**: Windows 10/11, Linux (Ubuntu 20.04+), macOS 12+
- **CUDA**: 11.8+ (si se usa GPU NVIDIA)

## Instalación Paso a Paso

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Mac-Tapia/dise-opvbesscar.git
cd dise-opvbesscar
```

### 2. Crear Entorno Virtual

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar Dependencias

**Solo CPU (básico):**
```bash
pip install -r requirements.txt
```

**Con GPU NVIDIA (recomendado para entrenamiento):**
```bash
pip install -r requirements.txt
pip install -r requirements-training.txt
```

### 4. Verificar Instalación

```bash
python ejecutar.py --validate
```

Salida esperada:
```
================================================================================
🚀 PVBESSCAR - Optimización de Carga EV con RL
================================================================================

[1/4] Verificando versión de Python...
  ✓ Python 3.11.x (CORRECTO)

[2/4] Verificando dependencias...
  ✓ numpy
  ✓ pandas
  ✓ torch
  ✓ gymnasium
  ✓ stable_baselines3
  ✓ yaml

[3/4] Verificando datasets OE2...
  ✓ Solar: data/interim/oe2/solar/pv_generation_timeseries.csv
  ✓ Chargers: data/interim/oe2/chargers/chargers_hourly_dataset.csv
  ✓ BESS: data/interim/oe2/bess/bess_hourly_dataset_2024.csv
  ✓ Mall: data/interim/oe2/mall/mall_demand_hourly.csv

[4/4] Verificando entorno de ejecución...
  ✓ GPU disponible: NVIDIA GeForce RTX 4060

✓ Validación completada
```

## Modos de Ejecución

### Modo 1: Validación (Sin Entrenamiento)

Verifica que el sistema esté correctamente configurado sin ejecutar entrenamiento.

```bash
python ejecutar.py --validate
```

**Cuándo usar:**
- Primera vez que instalas el sistema
- Después de actualizar dependencias
- Para verificar que los datasets están disponibles
- Para confirmar disponibilidad de GPU

**Duración:** ~5-10 segundos

---

### Modo 2: Entrenamiento A2C (⭐ RECOMENDADO)

Entrena el agente A2C - el mejor rendimiento según resultados de producción.

```bash
python ejecutar.py --agent a2c
```

**Características:**
- 🏆 **64.3% reducción CO₂** (mejor de los 3 agentes)
- ⚡ **Convergencia rápida** (~2 horas en GPU RTX 4060)
- 📈 **Estable y predecible** (ideal para producción)
- 💰 **Cost savings**: $1.73M USD/año

**Salida guardada en:**
- `checkpoints/A2C/latest.zip` - Modelo entrenado
- `outputs/a2c_training/` - Métricas y logs

**Duración:**
- GPU RTX 4060: ~2 horas
- CPU (8 cores): ~6-8 horas

---

### Modo 3: Entrenamiento PPO

Entrena el agente PPO - alternativa on-policy.

```bash
python ejecutar.py --agent ppo
```

**Características:**
- 📊 **47.5% reducción CO₂**
- ⏱️ **Convergencia media** (~2.5 horas)
- 🔄 **Volatilidad moderada**
- ⚠️ **No recomendado** (A2C es superior)

**Salida guardada en:**
- `checkpoints/PPO/latest.zip`
- `outputs/ppo_training/`

**Duración:**
- GPU RTX 4060: ~2.5 horas
- CPU (8 cores): ~8-10 horas

---

### Modo 4: Entrenamiento SAC

Entrena el agente SAC - off-policy, convergencia lenta.

```bash
python ejecutar.py --agent sac
```

**Características:**
- 📉 **43.3% reducción CO₂**
- 🐌 **Convergencia muy lenta** (~10 horas)
- 🧠 **Complejo off-policy** (replay buffer grande)
- 💾 **Alto uso de memoria** (~17 GB replay buffer)

**Salida guardada en:**
- `checkpoints/SAC/sac_final.zip`
- `outputs/sac_training/`

**Duración:**
- GPU RTX 4060: ~10 horas
- CPU (8 cores): ~30-40 horas

---

## Workflow Completo (Recomendado)

### Paso 1: Validación Inicial
```bash
python ejecutar.py --validate
```

### Paso 2: Entrenar A2C (Producción)
```bash
python ejecutar.py --agent a2c
```

### Paso 3: Verificar Resultados
```bash
# Listar checkpoints generados
ls -lh checkpoints/A2C/

# Ver métricas de entrenamiento
cat outputs/a2c_training/training_evolution.csv
```

### Paso 4: Cargar y Usar Modelo Entrenado
```python
from stable_baselines3 import A2C

# Cargar modelo entrenado
model = A2C.load("checkpoints/A2C/latest.zip")

# Usar para predicción
action, _ = model.predict(observation, deterministic=True)
```

## Métricas de Salida

Después del entrenamiento, encontrarás:

### 1. Checkpoints (Modelos Entrenados)
```
checkpoints/
├── A2C/
│   ├── latest.zip              # Modelo final
│   └── checkpoint_*.zip        # Checkpoints intermedios
```

### 2. Métricas de Entrenamiento
```
outputs/a2c_training/
├── training_evolution.csv      # Evolución por episodio
├── logs.csv                    # Métricas cada 1,000 steps
├── result_a2c.json             # Resumen final
├── timeseries_a2c.csv          # Series temporales completas
└── trace_a2c.csv               # Trace detallado por timestep
```

### 3. Logs del Sistema
```
entrenamiento_a2c.log           # Log completo de entrenamiento
```

## Interpretación de Resultados

### Métricas Clave

| Métrica | Descripción | Valor Óptimo (A2C) |
|---------|-------------|-------------------|
| **CO₂ Reducción** | % reducción vs baseline | 64.3% |
| **Reward Promedio** | Recompensa media | 0.4970 |
| **CO₂ Grid Import** | Emisiones por import grid | 19.8M kg/año |
| **Solar Autoconsumo** | % PV usado directamente | 51.7% |
| **Grid Import Reducción** | % menos import vs baseline | 45% |
| **Cost Savings** | Ahorro económico anual | $1.73M USD |

### Ejemplo de Salida Exitosa

```
================================================================================
✓ ENTRENAMIENTO A2C COMPLETADO
================================================================================

Resultados guardados en:
  • checkpoints/A2C/latest.zip
  • outputs/a2c_training/

Métricas Finales:
  CO₂ Reducción:        64.3%
  Reward Promedio:      0.4970
  Solar Autoconsumo:    51.7%
  Cost Savings:         $1.73M USD/año
  Timesteps:            87,600 (10 episodios)
  Duración:             2h 15m
```

## Solución de Problemas

### Error: Dependencias no instaladas

**Síntoma:**
```
✗ numpy (NO INSTALADO)
✗ pandas (NO INSTALADO)
```

**Solución:**
```bash
pip install -r requirements.txt
```

---

### Error: Datasets no encontrados

**Síntoma:**
```
⚠ Solar: data/interim/oe2/solar/pv_generation_timeseries.csv (NO ENCONTRADO)
```

**Solución:**

Los datasets deben estar en las rutas especificadas. Verifica que:
1. El repositorio se clonó completamente
2. Los archivos de datos están en `data/interim/oe2/`
3. Los permisos de lectura están correctos

---

### Error: GPU no disponible

**Síntoma:**
```
⚠ Solo CPU disponible (entrenamiento será lento)
```

**Soluciones:**

**Opción 1 - Continuar con CPU:**
El entrenamiento funcionará pero será más lento (6-8 horas vs 2 horas).

**Opción 2 - Habilitar GPU:**
1. Instalar CUDA Toolkit 11.8+
2. Instalar PyTorch con soporte CUDA:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

---

### Error: Out of Memory (OOM)

**Síntoma:**
```
RuntimeError: CUDA out of memory
```

**Solución:**

Reduce batch size en el script de entrenamiento:
```python
# En scripts/train/train_a2c_multiobjetivo.py
# Línea ~250 aprox.
batch_size = 64  # Reducir de 128 a 64
```

---

## Comparación de Agentes

| Agente | CO₂ Reducción | Tiempo GPU | Complejidad | Producción |
|--------|---------------|------------|-------------|------------|
| **A2C** ⭐ | **64.3%** | **2h** | Baja | ✅ RECOMENDADO |
| PPO | 47.5% | 2.5h | Media | ⚠️ Alternativa |
| SAC | 43.3% | 10h | Alta | ⚠️ Alternativa |

**Recomendación:** Usar A2C para producción debido a su mejor rendimiento, convergencia rápida y estabilidad.

## Próximos Pasos

Después de ejecutar con éxito:

1. **Evaluar Modelo:**
   - Revisar métricas en `outputs/a2c_training/`
   - Analizar convergencia en `training_evolution.csv`

2. **Validar en Entorno Real:**
   - Cargar checkpoint en sistema de producción
   - Monitorear rendimiento real vs simulado

3. **Optimización Continua:**
   - Ajustar reward weights si es necesario
   - Re-entrenar con nuevos datos

4. **Despliegue:**
   - Ver `DEPLOYMENT_INSTRUCTIONS_A2C.md`
   - Implementar en infraestructura Iquitos

## Referencias

- **README.md** - Descripción general del proyecto
- **DEPLOYMENT_INSTRUCTIONS_A2C.md** - Guía de despliegue
- **docs/** - Documentación técnica completa
- **scripts/train/** - Scripts de entrenamiento individuales

## Soporte

Para preguntas o problemas:
1. Revisar esta guía
2. Consultar logs en `entrenamiento_*.log`
3. Abrir issue en GitHub con logs completos

---

**Última actualización:** 2026-02-15  
**Versión:** 1.0.0
