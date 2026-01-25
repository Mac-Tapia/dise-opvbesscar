# 🚀 COMANDOS PARA INICIAR ENTRENAMIENTO

**Fecha**: 2026-01-24  
**Estado**: ✅ Todos los agentes verificados y listos

---

## ✅ VERIFICACIÓN PREVIA

Antes de entrenar, **siempre ejecuta** la verificación:

### Windows (CMD)

```cmd
verificar_agentes.bat
```

### Windows (PowerShell)

```powershell
.\verificar_agentes.ps1
```

### Linux/Mac

```bash
source .venv/bin/activate
python scripts/verificar_agentes.py
```

**Resultado esperado**: Todas las verificaciones en ✅ OK

---

## 🎯 ENTRENAMIENTO RÁPIDO (5 EPISODIOS)

### Entrenar SAC (Soft Actor-Critic)

```bash
# Windows (PowerShell)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cuda

# Linux/Mac
python scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cuda
```

**Duración estimada**: ~15-20 minutos  
**Memoria GPU**: ~4-6 GB VRAM

---

### Entrenar PPO (Proximal Policy Optimization)

```bash
# Windows (PowerShell)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent PPO --episodes 5 --device cuda

# Linux/Mac
python scripts/train_gpu_robusto.py --agent PPO --episodes 5 --device cuda
```

**Duración estimada**: ~20-25 minutos  
**Memoria GPU**: ~3-4 GB VRAM

---

### Entrenar A2C (Advantage Actor-Critic)

```bash
# Windows (PowerShell)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent A2C --episodes 5 --device cuda

# Linux/Mac
python scripts/train_gpu_robusto.py --agent A2C --episodes 5 --device cuda
```

**Duración estimada**: ~10-15 minutos  
**Memoria GPU**: ~2-3 GB VRAM

---

## 🔄 ENTRENAR TODOS LOS AGENTES EN SERIE

Entrena SAC, PPO y A2C automáticamente uno después del otro:

```bash
# Windows (PowerShell)
& .venv/Scripts/python.exe scripts/train_agents_serial.py --device cuda --episodes 5

# Linux/Mac
python scripts/train_agents_serial.py --device cuda --episodes 5
```

**Duración estimada total**: ~45-60 minutos  
**Checkpoints**: Guardados automáticamente cada 1000 steps

---

## 💪 ENTRENAMIENTO COMPLETO (PRODUCCIÓN)

### SAC (50 episodios recomendados)

```bash
# Windows (PowerShell)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda

# Linux/Mac
python scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda
```

**Duración estimada**: ~2.5-3 horas  
**Nota**: 50 episodios es el **mínimo recomendado** para alta dimensionalidad

---

### PPO (500k timesteps = ~57 episodios)

```bash
# Windows (PowerShell)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent PPO --episodes 57 --device cuda

# Linux/Mac
python scripts/train_gpu_robusto.py --agent PPO --episodes 57 --device cuda
```

**Duración estimada**: ~3.5-4 horas  
**Nota**: 500k timesteps es el **mínimo recomendado**

---

### A2C (500k timesteps = ~57 episodios)

```bash
# Windows (PowerShell)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent A2C --episodes 57 --device cuda

# Linux/Mac
python scripts/train_gpu_robusto.py --agent A2C --episodes 57 --device cuda
```

**Duración estimada**: ~2-2.5 horas  
**Nota**: A2C es más rápido pero menos estable que PPO

---

## 🎮 OPCIONES AVANZADAS

### Entrenar en CPU (sin GPU)

```bash
python scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cpu
```

⚠️ **Advertencia**: El entrenamiento será **10-20x más lento** en CPU

---

### Reanudar desde checkpoint

```bash
# Resume automático habilitado por defecto
python scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda --resume
```

**Nota**: El script busca automáticamente el último checkpoint y continúa desde ahí.

---

### Deshabilitar resume (empezar de cero)

```bash
python scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda --no-resume
```

---

## 📊 MONITOREO DURANTE ENTRENAMIENTO

### Archivos de progreso

Los logs de entrenamiento se guardan en:

```
training/oe3/progress/
├── sac_progress.csv
├── ppo_progress.csv
└── a2c_progress.csv
```

**Contenido**: timestamp, agent, episode, episode_reward, episode_length, global_step

---

### Checkpoints

Los modelos intermedios se guardan en:

```
training/oe3/checkpoints/
├── sac/
│   ├── checkpoint_1000.zip
│   ├── checkpoint_2000.zip
│   └── final_model.zip
├── ppo/
│   └── ...
└── a2c/
    └── ...
```

**Frecuencia**: Cada 1000 steps (configurable)

---

### Visualizar progreso en tiempo real

```bash
# En otra terminal
tail -f training/oe3/progress/sac_progress.csv
```

O usar Excel/Pandas para graficar `episode_reward` vs `episode`.

---

## 🛑 DETENER ENTRENAMIENTO

### Parada segura

1. Presiona `Ctrl+C` **UNA VEZ**
2. El script guardará el checkpoint actual
3. Espera a que termine el episodio en curso (~5-10 min)

⚠️ **No presiones** `Ctrl+C` múltiples veces o perderás el progreso del episodio actual.

---

### Reanudar después de detener

```bash
# El script detecta automáticamente el último checkpoint
python scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda
```

**Nota**: Asegúrate de usar el **mismo número de episodios** (o más) que la ejecución anterior.

---

## 📈 RESULTADOS ESPERADOS

### Después de 5 episodios (prueba rápida)

- **Reward promedio**: -1000 a -500 (baseline)
- **CO₂**: ~1000-800 kg/episodio
- **SOC BESS**: Estabilizado en 40-60%
- **Cargadores**: Demanda parcialmente satisfecha

### Después de 50 episodios (producción)

- **Reward promedio**: -200 a +100 (optimizado)
- **CO₂**: ~600-400 kg/episodio
- **SOC BESS**: Optimizado (20-80% rango útil)
- **Cargadores**: Demanda 80-90% satisfecha
- **Autoconsumo solar**: 60-70%

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### Error: CUDA out of memory

**Solución 1**: Reducir batch size

```python
# En src/iquitos_citylearn/oe3/agents/sac.py
batch_size: int = 256  # Reducido de 512
```

**Solución 2**: Entrenar en CPU

```bash
python scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cpu
```

---

### Error: Checkpoint not found

**Solución**: Verificar que existe el directorio

```bash
ls training/oe3/checkpoints/sac/
```

Si no existe, el entrenamiento empezará desde cero automáticamente.

---

### Entrenamiento muy lento

**Causas comunes**:

1. Ejecutando en CPU (usar `--device cuda`)
2. Batch size muy grande (reducir a 256 o 128)
3. Mixed precision deshabilitado (verificar `use_amp: True`)

**Verificar velocidad**:

```bash
# Debería mostrar ~100-200 steps/seg en GPU
# Debería mostrar ~10-20 steps/seg en CPU
```

---

## 📝 LOGS Y DEBUGGING

### Habilitar logs detallados

```bash
# Establecer nivel de logging a DEBUG
export PYTHON_LOG_LEVEL=DEBUG  # Linux/Mac
$env:PYTHON_LOG_LEVEL="DEBUG"  # Windows PowerShell

python scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cuda
```

---

### Ver uso de GPU durante entrenamiento

```bash
# Ejecutar en otra terminal
watch -n 1 nvidia-smi  # Linux
# O en Windows PowerShell:
while ($true) { nvidia-smi; Start-Sleep -Seconds 1; Clear-Host }
```

---

## ✅ CHECKLIST PRE-ENTRENAMIENTO

Antes de iniciar un entrenamiento largo (50+ episodios):

- [ ] Ejecutar `verificar_agentes.bat/.ps1` → todas ✅
- [ ] GPU disponible → `nvidia-smi` muestra RTX 4060
- [ ] Espacio en disco → >10 GB libres en `training/`
- [ ] Datos verificados → 128 cargadores, 5 schemas
- [ ] Entorno virtual activado → `.venv/Scripts/python.exe`
- [ ] Checkpoints antiguos respaldados (opcional)

---

## 🎯 RECOMENDACIÓN

Para **primera prueba**:

```bash
# 1. Verificar
.\verificar_agentes.ps1

# 2. Entrenar SAC rápido (5 episodios)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cuda

# 3. Si funciona bien, lanzar entrenamiento completo
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda
```

---

**Última actualización**: 2026-01-24  
**Documento**: COMANDOS_ENTRENAMIENTO.md  
**Autor**: GitHub Copilot
