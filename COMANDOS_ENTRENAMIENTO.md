# 🚀 COMANDOS PARA INICIAR ENTRENAMIENTO

**Fecha**: 2026-01-24  
**Estado**: ✅ Todos los agentes verificados y listos

---

## ✅ VERIFICACIÓN PREVIA

Antes de entrenar, **siempre ejecuta** la verificación:

### Windows (CMD)

<!-- markdownlint-disable MD013 -->
```cmd
verificar_agentes.bat
```bash
<!-- markdownlint-enable MD013 -->

### Windows (PowerShell)

<!-- markdownlint-disable MD013 -->
```powershell
.\verificar_agentes.ps1
```bash
<!-- markdownlint-enable MD013 -->

### Linux/Mac

<!-- markdownlint-disable MD013 -->
```bash
source .venv/bin/activate
python scripts/verificar_agentes.py
```bash
<!-- markdownlint-enable MD013 -->

**Resultado esperado**: T...
```

[Ver código completo en GitHub]bash
# Windows (PowerShell) (2)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cuda

# Linux/Mac (2)
python scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

**Duración estimada**: ~15-20 minutos  
**Memoria GPU**: ~4-6 GB VRAM

---

### Entrenar PPO (Proximal Policy Optimization)

<!-- markdownlint-disable MD013 -->
```bash
# Windows (PowerShell) (3)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent PPO --episodes 5 --device cuda

# Linux/Mac (3)
python scripts/train_gpu_robusto.py --agent PPO --episod...
```

[Ver código completo en GitHub]bash
# Windows (PowerShell) (4)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent A2C --episodes 5 --device cuda

# Linux/Mac (4)
python scripts/train_gpu_robusto.py --agent A2C --episodes 5 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

**Duración estimada**: ~10-15 minutos  
**Memoria GPU**: ~2-3 GB VRAM

---

## 🔄 ENTRENAR TODOS LOS AGENTES EN SERIE

Entrena SAC, PPO y A2C automáticamente uno después del otro:

<!-- markdownlint-disable MD013 -->
```bash
# Windows (PowerShell) (5)
& .venv/Scripts/python.exe scripts/train_agents_serial.py --device cuda --episodes 5

# Linux/Mac (5)
python scri...
```

[Ver código completo en GitHub]bash
# Windows (PowerShell) (6)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda

# Linux/Mac (6)
python scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

**Duración estimada**: ~2.5-3 horas  
**Nota**: 50 episodios es el **mínimo recomendado** para alta dimensionalidad

---

### PPO (500k timesteps = ~57 episodios)

<!-- markdownlint-disable MD013 -->
```bash
# Windows (PowerShell) (7)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent PPO --episodes 57 --device cuda

# Linux/Mac (7)
python scripts/t...
```

[Ver código completo en GitHub]bash
# Windows (PowerShell) (8)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent A2C --episodes 57 --device cuda

# Linux/Mac (8)
python scripts/train_gpu_robusto.py --agent A2C --episodes 57 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

**Duración estimada**: ~2-2.5 horas  
**Nota**: A2C es más rápido pero menos estable que PPO

---

## 🎮 OPCIONES AVANZADAS

### Entrenar en CPU (sin GPU)

<!-- markdownlint-disable MD013 -->
```bash
python scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cpu
```bash
<!-- markdownlint-enable MD013 -->

⚠️ **Advertencia**: El entrenamiento será **10-...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Nota**: El script busca automáticamente el último checkpoint y continúa desde
ahí.

---

### Deshabilitar resume (empezar de cero)

<!-- markdownlint-disable MD013 -->
```bash
python scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda --no-resume
```bash
<!-- markdownlint-enable MD013 -->

---

## 📊 MONITOREO DURANTE ENTRENAMIENTO

### Archivos de progreso

Los logs de entrenamiento se guardan en:

<!-- markdownlint-disable MD013 -->
```bash
training/oe3/progress/
├── sac_progress.csv
├── ppo_progress.csv
└── a2c_progress.csv
```bash
<!-- markdownlint-e...
```

[Ver código completo en GitHub]bash
training/oe3/checkpoints/
├── sac/
│   ├── checkpoint_1000.zip
│   ├── checkpoint_2000.zip
│   └── final_model.zip
├── ppo/
│   └── ...
└── a2c/
    └── ...
```bash
<!-- markdownlint-enable MD013 -->

**Frecuencia**: Cada 1000 steps (configurable)

---

### Visualizar progreso en tiempo real

<!-- markdownlint-disable MD013 -->
```bash
# En otra terminal
tail -f training/oe3/progress/sac_progress.csv
```bash
<!-- markdownlint-enable MD013 -->

O usar Excel/Pandas para graficar `episode_reward` vs `episode`.

---

## 🛑 DETENER ENTRENAMIENTO

### Parada segura
...
```

[Ver código completo en GitHub]bash
# El script detecta automáticamente el último checkpoint
python scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

**Nota**: Asegúrate de usar el **mismo número de episodios** (o más) que la
ejecución anterior.

---

## 📈 RESULTADOS ESPERADOS

### Después de 5 episodios (prueba rápida)

- **Reward promedio**: -1000 a -500 (baseline)
- **CO₂**: ~1000-800 kg/episodio
- **SOC BESS**: Estabilizado en 40-60%
- **Cargadores**: Demanda parcialmente satisfecha

### Después de 50 epi...
```

[Ver código completo en GitHub]python
# En src/iquitos_citylearn/oe3/agents/sac.py
batch_size: int = 256  # Reducido de 512
```bash
<!-- markdownlint-enable MD013 -->

**Solución 2**: Entrenar en CPU

<!-- markdownlint-disable MD013 -->
```bash
python scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cpu
```bash
<!-- markdownlint-enable MD013 -->

---

### Error: Checkpoint not found

**Solución**: Verificar que existe el directorio

<!-- markdownlint-disable MD013 -->
```bash
ls training/oe3/checkpoints/sac/
```b...
```

[Ver código completo en GitHub]bash
# Debería mostrar ~100-200 steps/seg en GPU
# Debería mostrar ~10-20 steps/seg en CPU
```bash
<!-- markdownlint-enable MD013 -->

---

## 📝 LOGS Y DEBUGGING

### Habilitar logs detallados

<!-- markdownlint-disable MD013 -->
```bash
# Establecer nivel de logging a DEBUG
export PYTHON_LOG_LEVEL=DEBUG  # Linux/Mac
$env:PYTHON_LOG_LEVEL="DEBUG"  # Windows PowerShell

python scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

---

###...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

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

<!-- markdownlint-disable MD013 -->
```bash
# 1. Verificar
.\verificar_agentes.ps1

# 2. Entrenar SAC rápido (5 episodios)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cuda

# 3. Si funciona bien, lanzar entrenamiento completo
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent SAC --episodes 50 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

---

**Última actualización**: 2026-01-24  
**Documento**: COMANDOS_ENTRENAMIENTO.md  
**Autor**: GitHub Copilot
