# Estado de Checkpoints y Reanudación de Entrenamiento

## 📊 Configuración Actual (2026-01-13)

### ✅ Checkpoints ACTIVADOS y PREPARADOS

Todos los agentes (SAC, PPO, A2C) están configurados correctamente para guardar checkpoints y reanudar entrenamiento sin empezar desde cero.

| Agente | resume_checkpoints | checkpoint_freq | save_final | Episodes |
 | -------- | ------------------- | ----------------- | ----------- | ---------- |
| **SAC** | ✅ True | Cada 500 pasos | ✅ True | 5 |
| **PPO** | ✅ True | Cada 500 pasos | ✅ True | 5 |
| **A2C** | ✅ True | Cada 500 pasos | ✅ True | 5 |

---

## 🗂️ Estructura de Checkpoints

```text
outputs/oe3/
├── checkpoints/                     ← Raíz de checkpoints (se crea en primer entrenamiento)
│   ├── sac/
│   │   ├── sac_step_500.zip        ← Checkpoint incremental (pasos)
│   │   ├── sac_step_1000.zip
│   │   ├── sac_step_1500.zip
│   │   └── sac_final.zip           ← Checkpoint final (al completar episodio)
│   ├── ppo/
│   │   └── ppo_*.zip               ← Misma estructura
│   └── a2c/
│       └── a2c_*.zip               ← Misma estructura
├── simulations/                     ← Resultados de simulación
└── training/                        ← Métricas y reportes
```text

---

## 🔄 Cómo Funciona la Reanudación

### 1️⃣ **Primera Ejecución**

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

- Sistema detecta: `checkpoint_dir` NO existe
- Crea automáticamente: `outputs/oe3/checkpoints/<agent>/`
- Inicia entrenamiento desde CERO (epoch 0)
- Guarda checkpoints cada 500 pasos

### 2️⃣ **Si Entrenamiento se Interrumpe**

Ejemplo: SAC se detiene en paso 1500 durante episodio 3

**Estado Guardado:**

- ✅ `outputs/oe3/checkpoints/sac/sac_step_500.zip`
- ✅ `outputs/oe3/checkpoints/sac/sac_step_1000.zip`
- ✅ `outputs/oe3/checkpoints/sac/sac_step_1500.zip`
- Red neuronal, buffer de experiencias, optimizer state: **TODOS GUARDADOS**

### 3️⃣ **Reanudar Entrenamiento**

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

- Sistema detecta: `checkpoint_dir` EXISTE
- Busca checkpoint MÁS RECIENTE:
  - Si existe `sac_final.zip` → Usa ese
  - Si no → Busca `sac_step_XXXXX.zip` con mayor número
  - En ejemplo: Carga `sac_step_1500.zip`
- **Continúa desde paso 1500** sin perder progreso
- Episodio parcial NO se repite

### 4️⃣ **Al Completar Entrenamiento**

- Sistema guarda `sac_final.zip`
- Próxima ejecución lo detecta automáticamente
- Continúa entrenamiento si `resume_checkpoints: true`

---

## 📍 Ubicación de Checkpoints

**Configuración en `configs/default.yaml`:**

```yaml
oe3:
  evaluation:
    training_dir: "analyses/oe3/training"  # ← Base path
    
    sac:
      resume_checkpoints: true             # ← Habilitar reanudación
      checkpoint_freq_steps: 500           # ← Guardar cada 500 pasos
      save_final: true                     # ← Guardar final
    
    ppo:
      resume_checkpoints: true
      checkpoint_freq_steps: 500
      save_final: true
    
    a2c:
      resume_checkpoints: true
      checkpoint_freq_steps: 500
      save_final: true
```text

**Rutas efectivas:**

```text
analyses/oe3/training/checkpoints/sac/   → Checkpoints SAC
analyses/oe3/training/checkpoints/ppo/   → Checkpoints PPO
analyses/oe3/training/checkpoints/a2c/   → Checkpoints A2C
```text

---

## 🔍 Cómo Verificar Checkpoints

### Opción 1: Ver archivos guardados

```powershell
# En Windows PowerShell
Get-ChildItem -Path "outputs/oe3/checkpoints/" -Recurse -Filter "*.zip"
```text

### Opción 2: Script Python

```python
from pathlib import Path

for agent in ['sac', 'ppo', 'a2c']:
    checkpoint_dir = Path(f'outputs/oe3/checkpoints/{agent}')
    if checkpoint_dir.exists():
        files = list(checkpoint_dir.glob('*.zip'))
        print(f'{agent.upper()}: {len(files)} checkpoints guardados')
        for f in sorted(files):
            size_mb = f.stat().st_size / 1024 / 1024
            print(f'  - {f.name} ({size_mb:.1f} MB)')
```text

### Opción 3: Ver en logs

```bash
grep -i "checkpoint\|resume" analyses/oe3/training/*.log
```text

---

## ⚠️ Consideraciones Importantes

### ✅ QUÉ ESTÁ GUARDADO EN CADA CHECKPOINT

- ✅ Pesos de red neuronal (política + valor)
- ✅ Buffer de experiencias (replay buffer)
- ✅ Optimizer state (momentos, velocidades)
- ✅ Época/paso actual
- ✅ Semilla aleatoria (reproducibilidad)

### ❌ QUÉ NO SE RECUPERA (OK)

- Métricas de entrenamiento parciales (se recalculan)
- Gráficas de progreso (se regeneran)
- Archivos de configuración (se recargan)

### 🔐 Garantías de Continuidad

1. **Sin Pérdida de Aprendizaje**: Red neuronal continúa desde donde se quedó
2. **Buffer Intacto**: Experiencias previas preservadas para re-muestreo
3. **Convergencia Preservada**: Optimizer state (Adam, etc.) restaurado
4. **Reproducibilidad**: Semilla fijada en config (seed=42)

---

## 📋 Comandos Útiles

### Ver estado actual

```bash
python show_training_status.py
```text

### Monitorear en tiempo real

```bash
python monitor_checkpoints.py
```text

### Reanudar entrenamiento (automático)

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
# Sistema auto-detecta checkpoints y continúa
```text

### Limpiar checkpoints (CUIDADO ⚠️)

```bash
# ¡NO HACER SI ENTRENAMIENTO ESTÁ EN PROGRESO!
Remove-Item -Path "outputs/oe3/checkpoints" -Recurse -Force
# Próxima ejecución iniciará desde CERO
```text

### Forzar inicio desde cero

```yaml
# En configs/default.yaml, cambiar a:
resume_checkpoints: false
# Próxima ejecución ignora checkpoints existentes
```text

---

## 🚀 Flujo de Entrenamiento Recomendado

### Sesión 1: Inicio

```bash
# Día 1 - Mañana (15 horas de entrenamiento planificado)
python -m scripts.run_oe3_simulate --config configs/default.yaml
# Sistema crea checkpoints/sac/, /ppo/, /a2c/
# Entrena SAC 5 episodios (~2 horas)
# Entrena PPO 5 episodios (~1.5 horas)
# Entrena A2C 5 episodios (~1 hora)
```text

### Sesión 2: Continuar (en otro momento)

```bash
# Día 2 - Sin perder progreso
python -m scripts.run_oe3_simulate --config configs/default.yaml
# Auto-detecta checkpoints
# Lee SAC final.zip (o step_XXXXX.zip más reciente)
# Continúa SAC sin reiniciar
# Idem PPO, A2C
```text

### Verificar Progreso

```bash
python show_training_status.py
# Output:
# SAC: 3 de 5 episodios completados (paso 2500 / 17520)
# PPO: 2 de 5 episodios completados (paso 1800 / 87600)
# A2C: 1 de 5 episodios completados (paso 890 / 87600)
```text

---

## 📊 Tamaño Estimado de Checkpoints

| Agente | Por Checkpoint | Total (5 ep) |
 | -------- | --------------- | -------------- |
| SAC | 100-150 MB | 500-750 MB |
| PPO | 120-180 MB | 600-900 MB |
| A2C | 120-180 MB | 600-900 MB |
| **Total** | - | **1.7-2.6 GB** |

*Estimaciones aproximadas, varían según `batch_size` y `buffer_size`*

---

## 🎯 Conclusión

✅ **Agentes LISTOS para reanudación:**

- Checkpoints configurados en `configs/default.yaml`
- Sistema auto-crea directorios en primer entrenamiento
- Reanudación automática desde checkpoint más reciente
- Sin necesidad de scripts especiales (`continue_<agent>_training.py`)
- **Simplemente ejecutar `run_oe3_simulate` nuevamente**

✅ **Penalizaciones, Recompensas y Ganancias CAPTURADAS:**

- Multiobjetivo ACTIVO: CO2 (50%), Costo (15%), Solar (20%), EV (10%), Grid (5%)
- Checkpoints guardan estado completo incluyendo reward history
- Reanudación mantiene consistencia de métricas

**Status: 🟢 PREPARADO PARA ENTRENAMIENTOS CONTINUOS**

---

*Último actualizado: 2026-01-13 20:15 UTC*
