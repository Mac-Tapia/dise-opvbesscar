# Guía Paso a Paso: Ejecutar Entrenamiento de Agentes

## ⚠️ IMPORTANTE

**NO se puede ejecutar el entrenamiento en GitHub Actions / CI/CD.**

El entrenamiento de agentes RL requiere:
- ✅ GPU con CUDA (NVIDIA)
- ✅ PyTorch instalado con soporte CUDA
- ✅ 2-8 GB VRAM
- ✅ 1-3 horas de tiempo de cómputo

**Debes ejecutar esto en tu computadora local con GPU.**

---

## Paso 1: Verificar que tienes GPU

Abre una terminal y ejecuta:

```bash
nvidia-smi
```

**Salida esperada:** Deberías ver información de tu GPU NVIDIA.

Si obtienes un error, tu máquina no tiene GPU NVIDIA o los drivers no están instalados.

---

## Paso 2: Clonar el Repositorio (si no lo has hecho)

```bash
git clone https://github.com/Mac-Tapia/dise-opvbesscar.git
cd dise-opvbesscar
git checkout copilot/prepare-agents-for-training
```

---

## Paso 3: Instalar Dependencias

### Opción A: Con ambiente virtual (recomendado)

```bash
# Crear ambiente virtual
python -m venv .venv

# Activar ambiente virtual
# En Linux/Mac:
source .venv/bin/activate
# En Windows:
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
pip install -e .
```

### Opción B: Sin ambiente virtual

```bash
pip install -r requirements.txt
pip install -e .
```

---

## Paso 4: Verificar que CUDA está disponible

```bash
python -c "import torch; print(f'CUDA disponible: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

**Salida esperada:**
```
CUDA disponible: True
GPU: NVIDIA GeForce RTX 3080 (o tu GPU)
```

---

## Paso 5: EJECUTAR EL ENTRENAMIENTO

### Opción 1: Script de Conveniencia (MÁS FÁCIL)

**Linux/Mac:**
```bash
./scripts/train_all_agents_10ep.sh
```

**Windows:**
```bash
scripts\train_all_agents_10ep.bat
```

### Opción 2: Comando Manual

```bash
python -m scripts.run_oe3_train_agents --agents SAC PPO A2C --episodes 10 --device cuda
```

---

## ⏱️ Tiempo Esperado

- **Con GPU (RTX 3080 o similar):** 1-3 horas
- **Con GPU (GTX 1080 o similar):** 2-4 horas
- **Sin GPU (CPU):** 12-48 horas ❌ NO RECOMENDADO

---

## 📊 Progreso del Entrenamiento

Mientras entrena, verás mensajes como:

```
==============================================================
 ENTRENAMIENTO SAC - 10 episodios (8760 pasos/episodio)
==============================================================
Dispositivo: cuda | Batch: 256 | LR: 3.00e-04
==============================================================

[SAC] ep 1/10 iniciado
[SAC] paso 1000 | ep~1 | pasos_global=1000
[SAC] paso 2000 | ep~1 | pasos_global=2000
...
[SAC] ep 1/10 terminado reward=-1234.56 pasos=8760
```

---

## 📁 Resultados

Después del entrenamiento, encontrarás los modelos en:

```
analyses/oe3/training/
├── checkpoints/
│   ├── sac/sac_final.zip       ← Modelo SAC entrenado
│   ├── ppo/ppo_final.zip       ← Modelo PPO entrenado
│   └── a2c/a2c_final.zip       ← Modelo A2C entrenado
├── progress/
│   ├── sac_progress.csv        ← Métricas de entrenamiento
│   ├── ppo_progress.csv
│   └── a2c_progress.csv
├── sac_training.png            ← Gráfica de aprendizaje
├── ppo_training.png
└── a2c_training.png
```

---

## ❓ Preguntas Frecuentes

### P: ¿Por qué no se puede ejecutar en GitHub?
**R:** GitHub Actions no tiene GPUs disponibles. El entrenamiento requiere GPU para ser práctico (1-3 horas vs 12-48 horas en CPU).

### P: ¿Qué hago si no tengo GPU?
**R:** 
1. Usa Google Colab (tiene GPUs gratis): https://colab.research.google.com/
2. Reduce episodios: `--episodes 2` (más rápido pero menos entrenado)
3. Usa solo un agente: `--agents SAC`

### P: ¿Cómo verifico que funcionó?
**R:** Verifica que existan los archivos `.zip` en `analyses/oe3/training/checkpoints/`

---

## 🆘 Problemas Comunes

### Error: "CUDA out of memory"
**Solución:** Reduce batch_size en `configs/default.yaml`:
```yaml
sac:
  batch_size: 128  # en vez de 256
```

### Error: "No module named 'torch'"
**Solución:** Instala PyTorch con CUDA:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Error: "CUDA not available"
**Solución:** 
1. Verifica drivers NVIDIA: `nvidia-smi`
2. Reinstala PyTorch con CUDA
3. Verifica CUDA toolkit instalado

---

## 📞 Soporte

Si tienes problemas:
1. Revisa la documentación: `docs/TRAINING_AGENTS.md`
2. Verifica los logs de error completos
3. Asegúrate de tener GPU NVIDIA con drivers actualizados

---

**RECUERDA: Este proceso se ejecuta en TU COMPUTADORA LOCAL, no en GitHub.**
