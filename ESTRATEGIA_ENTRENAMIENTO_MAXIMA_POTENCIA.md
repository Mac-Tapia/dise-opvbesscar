# 🚀 ESTRATEGIA DE ENTRENAMIENTO RECOMENDADA

<!-- markdownlint-disable MD013 -->
 **Fecha**: 2026-01-24 | **Versión**: MÁXIMA POTENCIA INDIVIDUAL | **Estado**: ✅ 

---

## 📋 ÍNDICE DE ESTRATEGIAS

1. [Opción 1: Entrenamiento Secuencial (Recomendado)][ref]

[ref]: #opción-1-entrenamiento-secuencial-recomendado
2. [Opción 2: Entrenamiento Paralelo en GPUs][ref]

[ref]: #opción-2-entrenamiento-paralelo-en-gpus
3. [Opción 3: Entrenamiento Individual Rápido][ref]

[ref]: #opción-3-entrenamiento-individual-rápido
4. [Opción 4: Entrenamiento de Prueba (5 episodios)][ref]

[ref]: #opción-4-entrenamiento-de-prueba-5-episodios
5. [Monitoreo y Resultados](#monitoreo-y-resultados)

---

## OPCIÓN 1: ENTRENAMIENTO SECUENCIAL (Recomendado)

**Descripción**: Entrena los 3 agentes uno después de otro en la misma GPU.

**Ventajas**:

- ✅ Simple de ejecutar (un comando)
- ✅ GPU siempre disponible
- ✅ Reproducible
- ✅ Menos riesgo de OOM

**Duración Total**: ~11 horas

### Comando

<!-- markdownlint-disable MD013 -->
```bash
# Verificar primero
.\verificar_agentes.ps1

# Entrenar todos en serie
& .venv/Scripts/python.exe scripts/train_agents_serial.py --device cuda --episodes 50
```bash
<!-- markdownlint-enable MD013 -->

### Detalle de Ejecución

<!-- markdownlint-disable MD013 -->
```bash
┌─ A2C (Rápido) ─────────────────────────┐
│ Duración: 2.5-3 horas                  │
│ Episodes: 57 (~500k steps)             │
...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Logs Esperados

<!-- markdownlint-disable MD013 -->
```bash
[Inicio] A2C Entrenamiento
 Episode 1/57 | Reward: -1200 | CO₂: 600 kg 
 Episode 10/57 | Reward: -800 | CO₂: 500 kg 
 Episode 30/57 | Reward: -400 | CO₂: 350 kg 
 Episode 50/57 | Reward: -100 | CO₂: 300 kg ✅ 

[Inicio] SAC Entrenamiento
 Episode 1/50 | Reward: -1100 | CO₂: 580 kg 
 Episode 5/50 | Reward: -700 | CO₂: 450 kg 
 Episode 20/50 | Reward: -200 | CO₂: 280 kg 
 Episode 50/50 | Reward: +100...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## OPCIÓN 2: ENTRENAMIENTO PARALELO EN GPUS

**Descripción**: Entrena 2-3 agentes simultáneamente en GPU usando subprocesos.

**Ventajas**:

- ✅ Mucho más rápido (~6-7 horas)
- ✅ Mejor utilización GPU
- ✅ Todos los agentes avanzan simultáneamente

**Desventajas**:

- ⚠️ Requiere GPU con suficiente VRAM
- ⚠️ Menor control individual
- ⚠️ Potencial OOM si VRAM insuficiente

**Requisito**: RTX 4060 (8GB) puede manejar:

- SAC + PPO en GPU: ~5-6 GB + 3-4 GB = 9-10 GB (❌ Ajustado)
- Mejor: SAC o PPO en GPU, A2C en CPU

### Comando Opción 2A: SAC+A2C en GPU

<!-- markdownlint-disable MD013 -->
```bash
# Terminal 1 (GPU)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  --agent SAC --episodes 50 --device cuda

# Terminal 2 (esperar 30 segundos, luego GPU asignará)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  --agent A2C --episodes 57 --device cuda

# Terminal 3 (CPU mientras GPU está ocupada)
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  --agent PPO --episo...
```

[Ver código completo en GitHub]bash
# Más seguro y controlado
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  --agent SAC --episodes 50 --device cuda

& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  --agent PPO --episodes 57 --device cuda

& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  --agent A2C --episodes 57 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

**Tiempo Total**: ~11 horas (igual que secuencial, pero control fino)

---

## OPCIÓN 3: ENTRENAMIENTO INDIVIDUAL RÁPIDO

**Descripción**: Entrena un solo agente para experimentar sin esperar.

### Solo SAC (Máxima Estabilidad)

<!-- markdownlint-disable MD013 -->
```bash
# 3 horas, máxima estabilidad
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  -...
```

[Ver código completo en GitHub]bash
# 2.5 horas, prototipado rápido
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  --agent A2C --episodes 57 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

**Resultado Esperado**:

- Convergencia: ~15-20 episodios
- Reward Final: -150 a +100
- CO₂: 300-400 kg/episodio
- Baseline funcional

### Solo PPO (Mejor rendimiento)

<!-- markdownlint-disable MD013 -->
```bash
# 5-6 horas, mejor rendimiento final
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  --agent PPO --episodes 57 --device cuda
```bash
<!-- m...
```

[Ver código completo en GitHub]bash
# ~30 minutos
& .venv/Scripts/python.exe scripts/train_agents_serial.py ^
  --device cuda --episodes 5
```bash
<!-- markdownlint-enable MD013 -->

### Prueba Individual SAC

<!-- markdownlint-disable MD013 -->
```bash
# ~10 minutos
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  --agent SAC --episodes 5 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

### Prueba Individual PPO

<!-- markdownlint-disable MD013 -->
```bash
# ~15 minutos
& .venv/Scripts/python.exe scripts/train_gpu_robust...
```

[Ver código completo en GitHub]bash
# ~8 minutos
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py ^
  --agent A2C --episodes 5 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

---

## 📊 MONITOREO Y RESULTADOS

### Archivos de Salida Generados

<!-- markdownlint-disable MD013 -->
```bash
results/
├── SAC/
│   ├── checkpoints/
│   │   ├── model_episode_10.zip
│   │   ├── model_episode_25.zip
│   │   ├── model_episode_50.zip (FINAL)
│   │   └── ...
│   ├── logs/
│   │   ├── training_log.txt
│   │   ├── metrics.csv
│   │   └── performance...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### Métricas Clave a Monitorear

#### 1. Reward Convergencia

<!-- markdownlint-disable MD013 -->
```bash
SAC:
  Episode 1:    -1100  (inicio caótico)
  Episode 10:   -600   (mejorando)
  Episode 25:   -200   (converging)
  Episode 50:   +100   ✅ (óptimo)

PPO:
  Episode 1:    -1300  (inicio peor)
  Episode 20:   -400   (mejorando más lento)
  Episode 40:   +50    (convergencia suave)
  Episode 57:   +250   ✅✅ (MEJOR)

A2C:
  Episode 1:    -1200  (inicio)
  Episode 15:   -500   (rápida mejora)
  Episo...
```

[Ver código completo en GitHub]bash
SAC:
  Initial: ~600 kg/episodio
  Final:   250-350 kg/episodio (EXCELENTE)

PPO:
  Initial: ~620 kg/episodio
  Final:   200-300 kg/episodio (MÁS BAJO!)

A2C:
  Initial: ~600 kg/episodio
  Final:   300-400 kg/episodio (BUENO)
```bash
<!-- markdownlint-enable MD013 -->

#### 3. EV Satisfacción

<!-- markdownlint-disable MD013 -->
```bash
SAC:  90-95% (ALTA)
PPO:  88-93% (ALTA)
A2C:  85-90% (BUENA)
```bash
<!-- markdownlint-enable MD013 -->

### Herramientas de Monitoreo

<!-- markdownlint-disable MD013 -->
```bash
# Ver métricas en tiempo real
tail -f results/SAC/logs/training_log.txt

# Generar gráficos después del entrenamien...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## 🎯 RECOMENDACIÓN FINAL

### Para Máximo Rendimiento Total

**Opción 1 (Secuencial)** ← RECOMENDADO

<!-- markdownlint-disable MD013 -->
```bash
& .venv/Scripts/python.exe scripts/train_agents_serial.py --device cuda --episodes 50
```bash
<!-- markdownlint-enable MD013 -->

- ✅ Simple (un comando)
- ✅ Controlado (no OOM)
- ✅ Completo (todos los agentes)
- ⏱️ Duración: ~11 horas

### Para Máxima Velocidad

#### Opción 3B (Solo A2C)

<!-- markdownlint-disable MD013 -->
```bash
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent A...
```

[Ver código completo en GitHub]bash
# Entrenar todos 3 agentes
& .venv/Scripts/python.exe scripts/train_agents_serial.py --device cuda --episodes 50

# Luego reentrenar PPO con más episodios
& .venv/Scripts/python.exe scripts/train_gpu_robusto.py --agent PPO --episodes 100 --device cuda
```bash
<!-- markdownlint-enable MD013 -->

- ✅ Todos los agentes entrenados
- ✅ PPO con entrenamiento extra
- ⏱️ Duración: ~17 horas

---

## ⚠️ SOLUCIÓN DE PROBLEMAS

### Si tienes OOM (Out of Memory)

<!-- markdownlint-disable MD013 -->
```bash
# Reducir batch size para SAC
# Cambiar en sac.py: batch_size = 256 (desde 512)

# O usar CPU para un agente
& .venv/Scripts/python.exe scripts/train_gpu_robust...
```

[Ver código completo en GitHub]bash
# Aumentar learning rate (ligeramente)
# SAC:  1.5e-4 → 2.0e-4
# PPO:  2.0e-4 → 2.5e-4
# A2C:  1.5e-4 → 2.0e-4
```bash
<!-- markdownlint-enable MD013 -->

### Si el reward es muy negativo después de 20 episodios

<!-- markdownlint-disable MD013 -->
```bash
# Checkear normalización de observaciones
# Checkear pesos multiobjetivo
# Considerar reducir hidden_sizes a (512, 512)
```bash
<!-- markdownlint-enable MD013 -->

---

## 📈 ROADMAP DE ENTRENAMIENTO

<!-- markdownlint-disable MD013 -->
```bash
DÍA 1 (Mañana):
  ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## ✅ CHECKLIST PRE-ENTRENAMIENTO

- [ ] Ejecutar `.\verificar_agentes.ps1`
- [ ] Revisar STATUS_CATALIZACION_MAXIMA_POTENCIA.txt
- [ ] Verificar GPU disponible: `nvidia-smi`
- [ ] Tener suficiente espacio en disco (~20 GB para checkpoints)
- [ ] Seleccionar estrategia de entrenamiento
- [ ] Documentar inicio con timestamp
- [ ] Monitorear los primeros 5-10 episodios

---

## 🚀 GO TIME

Todos los agentes están optimizados al máximo nivel individual.

#### Opción recomendada:

<!-- markdownlint-disable MD013 -->
```bash
& .venv/Scripts/python.exe scripts/train_agents_serial.py --device cuda --episodes 50
```bash
<!-- markdownlint-enable MD013 -->

**Tiempo estimado**: 11 horas  
**Resultado esperado**: 3 agentes entrenados, converging, listos para producción

---

**Última actualización**: 2026-01-24  
**Versión**: MÁXIMA POTENCIA INDIVIDUAL v2.0  
**Estado**: ✅ LISTO PARA ENTRENAR
