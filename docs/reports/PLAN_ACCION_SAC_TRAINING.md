# PLAN DE ACCION EJECUTIVO - SAC TRAINING FIX

**Status:** CRÍTICO - Episode return = 0 (entrenamiento roto)  
**Fecha:** 2026-02-15  
**Prioridad:** P0 - BLOQUEADOR (sin esto, SAC no aprende)

---

## 🎯 OBJETIVO FINAL

Ejecutar entrenamiento SAC que logre:
- ✅ Episode return ≠ 0 (debe ser [-0.01, +0.01] típico)
- ✅ CO2 reduction: 25-40% vs baseline sin control
- ✅ Solar self-consumption: 60-70%
- ✅ Entrenamien completa en 5-7 horas GPU RTX 4060

---

## 📋 PASO 1: PREPARACIÓN (10 minutos)

### 1.1 Leer Diagnóstico Completo
- Archivo: `DIAGNOSTICO_SAC_EPISODE_RETURN_CERO.md`
- Elementos claves:
  - Root cause: Ambiente NO se instancia + agent.learn() NO se llama
  - REWARD_SCALE demasiado pequeño (0.01)
  - Pesos multiobjetivo nunca se pasan al ambiente

### 1.2 Revisar Fragmentos de Código
- Archivo: `SOLUCION_SAC_FRAGMENTOS.md`
- Contiene 5 fragmentos listos para copiar/pegar
- Incluyen comentarios TODO y numero de línea

### 1.3 Verificar Ambiente Actual
```bash
# Terminal PowerShell

# Verificar estructura de directorios
ls .\scripts\train\
# Debe mostrar: train_sac_multiobjetivo.py

# Verificar checkpoints actual
ls .\checkpoints\SAC\
# Puede estar vacia (OK) o tener archivos viejos

# Verificar datos
ls .\data\oe2\chargers\chargers_ev_ano_2024_v3.csv
ls .\data\oe2\Generacionsolar\pv_generation_citylearn_enhanced_v2.csv
ls .\data\oe2\demandamallkwh\demandamallhorakwh.csv
ls .\data\oe2\bess\bess_ano_2024.csv
# Todos deben existir
```

---

## 📝 PASO 2: IMPLEMENTAR FIXES (20-30 minutos)

### 2.1 Abrir train_sac_multiobjetivo.py
```bash
code .\scripts\train\train_sac_multiobjetivo.py
```

### 2.2 Aplicar Fragmento #1 (Reemplazar main())
- **Ubicación:** Línea ~2235
- **Acción:** Reemplazar función `main()` completa
- **Duración:** 2 minutos

Pasos:
1. Buscar: `def main():`
2. Seleccionar TODO el contenido de main() hasta el siguiente `if __name__`
3. Reemplazar CON el fragmento #1 de SOLUCION_SAC_FRAGMENTOS.md
4. Guardar (Ctrl+S)

### 2.3 Aplicar Fragmento #2 (Crear Ambiente)
- **Ubicación:** Después de desempaquetar datasets (línea ~2400)
- **Acción:** Insertar instantiación del ambiente
- **Duración:** 2 minutos

Pasos:
1. Buscar: `# Desempaquetar datos cargados` (fin del fragmento anterior)
2. Ir al final de ese bloque
3. Insertar Fragmento #2 completo
4. Guardar

### 2.4 Aplicar Fragmento #3 (SAC Training)
- **Ubicación:** Después de crear ambiente (línea ~2420)
- **Acción:** Agregar agent creation + learn() call
- **Duración:** 2 minutos

Pasos:
1. Ir a final de bloque de creación de ambiente
2. Insertar Fragmento #3 completo
3. Guardar

### 2.5 Aplicar Fragmento #4 (Reward Scale)
- **Ubicación:** Línea ~2800 en step()
- **Acción:** Cambiar REWARD_SCALE y clip
- **Duración:** 1 minuto

Pasos:
1. Buscar: `REWARD_SCALE = 0.01`
2. Reemplazar línea con: `REWARD_SCALE = 0.1`
3. Buscar: `np.clip(scaled_reward, -0.02, 0.02)`
4. Reemplazar con: `np.clip(scaled_reward, -0.01, 0.01)`
5. Guardar

### 2.6 Verificar Imports
- **Ubicación:** Top of file (~línea 40)
- **Acción:** Verificar que existan imports de SAC

Pasos:
1. Buscar: `from stable_baselines3 import SAC`
2. Si NO existe, agregar después de otros stable-baselines imports
3. Guardar

### 2.7 Syntax Check
```bash
# En PowerShell, verificar síntaxis
python -m py_compile .\scripts\train\train_sac_multiobjetivo.py

# Si sale exitoso, no muestra mensaje
# Si hay error, lo muestra con línea exacta
```

---

## 🚀 PASO 3: EJECUTAR ENTRENAMIENTO (5-7 horas)

### 3.1 Limpiar Checkpoints Viejos (Opcional)
```bash
# SI quieres entrenar desde CERO:
rm .\checkpoints\SAC\*

# Si quieres CONTINUAR con checkpoints anteriores:
# No hacer nada, mantener archivos
```

### 3.2 Ejecutar Training
```bash
# Terminal PowerShell - Entrenamiento
cd d:\diseñopvbesscar
python scripts/train/train_sac_multiobjetivo.py
```

**Qué esperar:**
- Línea 1-30: Carga de datos (30 segundos)
- Línea 31-50: Creación de ambiente (10 segundos)
- Línea 51-60: Creación de agente SAC (5 segundos)
- Línea 61+: **Entrenamiento comienza** (5-7 horas para 26,280 steps)

El output debe mostrar algo como:
```
[6] INSTANCIAR AGENTE SAC
-----------...--------
  [OK] Agente SAC creado

[7] INICIAR ENTRENAMIENTO SAC
-----------...--------
  [START] 2026-02-15 14:30:00
  
  26280/26280 [==============================] 100%  
  
  [DONE] 2026-02-15 19:45:30
  [SAVE] Checkpoint final guardado
```

### 3.3 Monitorear en Tiempo Real (EN OTRO TERMINAL)

**Terminal 2 - TensorBoard:**
```bash
cd d:\diseñopvbesscar
tensorboard --logdir=runs/ --host=localhost --port=6006
```

Luego abrir navegador: `http://localhost:6006`

**Qué ver:**
- Tab "SCALARS"
- Gráfico "rollout/ep_reward_mean"
- **Debe cambiar** (no plana en 0.0)
- Debe converger lentamente hacia arriba

**Métricas claves a monitorear:**
- `episode_reward` → debe estar en rango [-0.01, +0.01]
- `actor_loss` → debe ser negativo y convergente
- `critic_loss` → debe ser ~0.05-0.5
- `entropy` → debe decrecer ~0.9 → 0.2

### 3.4 Guardar Logs
```bash
# Hacer backup de logs antes de nuevos entrenamientos
$timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
Copy-Item .\runs\ .\runs_backup_$timestamp\ -Recurse
```

---

## ✅ PASO 4: VALIDACIÓN (10 minutos)

### 4.1 Verificar Checkpoints Guardados
```bash
ls -la .\checkpoints\SAC\
# Debe mostrar:
# - sac_iquitos_<number>.zip (checkpoints cada 8760 steps)
# - sac_iquitos_final.zip (checkpoint final)
```

### 4.2 Verificar Gráficos
```bash
# Abrir TensorBoard y revisar:
# 1. episode_reward → debe ser curva (no línea plana = 0.0)
# 2. actor_loss → debe decrecer
# 3. critic_loss → debe converger
# 4. entropy → debe cambiar

# Si gráficos están planos (todas líneas = 0): FALLO en implementación
```

### 4.3 Verificar Logs Finales
```bash
# Los últimos 100 líneas del output
# Buscar "EPISODIO COMPLETADO" con métricas

# Métricas esperadas:
# - Total Reward: > -0.02 (NO debe ser exactamente 0.0)
# - Solar kWh: > 0.0
# - CO2 Avoided: > 0.0
# - EV Satisfaction: > 0.0
```

### 4.4 Diagnóstico si Falla

**Si episode_reward sigue siendo = 0.0:**

Checklist:
- [ ] ¿Se ejecutó Fragmento #1 completamente?
- [ ] ¿Se ejecutó Fragmento #2 (creación ambiente)?
- [ ] ¿Se ejecutó Fragmento #3 (agent.learn)?
- [ ] ¿Se cambió REWARD_SCALE a 0.1?
- [ ] ¿Hay errores en consola? Leerlos primero
- [ ] ¿Está el dataset cargado correctamente? (validar en logs iniciales)
- [ ] ¿Está el ambiente siendo creado? (buscar "[5] VALIDAR AMBIENTE")

Si dice error, mostrar:
```bash
python -c "from stable_baselines3 import SAC; print(SAC.__version__)"
```

---

## 📊 PASO 5: RESULTADOS Y PRÓXIMOS PASOS (30 min - 1 hora)

### 5.1 Evaluar Resultados
Después de completar entrenamiento:

```bash
# Crear script de evaluación rápida
python << 'EOF'
import numpy as np
from stable_baselines3 import SAC
from pathlib import Path

# Cargar checkpoint
model = SAC.load('./checkpoints/SAC/sac_iquitos_final')

# Evaluar en 1 episodio
obs, _ = model.env.reset()
total_reward = 0.0
for step in range(8760):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, _, info = model.env.step(action)
    total_reward += reward
    if done:
        break

print(f"Eval Episode Reward: {total_reward:.4f}")
print(f"Solar kWh: {info.get('episode_solar_kwh', 0.0):.1f}")
print(f"CO2 Avoided: {info.get('episode_co2_avoided', 0.0):.1f} kg")
EOF
```

### 5.2 Analizar CO2 Reduction
Una vez entrenado, calcular reducción:

```python
# Métrica clave: CO2 reduction %
baseline_co2 = 640000  # kg/año sin solar (del copilot-instructions.md)
trained_co2 = 520000   # kg/año después de entrenamiento (estimado)
reduction_pct = (baseline_co2 - trained_co2) / baseline_co2 * 100

print(f"CO2 Reduction: {reduction_pct:.1f}%")
# Target: 25-40% reduction
# Éxito: > 20% reduction
```

### 5.3 Documentar Resultados
> Crear archivo `RESULTADO_ENTRENAMIENTO_SAC_<date>.txt`

Contenido:
```
RESULTADO ENTRENAMIENTO SAC
===========================
Fecha: 2026-02-15
Duración: 5h 45m
Timesteps: 26,280 (3 episodios)
Device: CUDA RTX 4060 8GB

METRICAS FINALES:
- Episode Reward: 0.0132 (éxito: ≠ 0.0)
- Solar kWh/año: 4,200,000
- CO2 Avoided: 425,000 kg/año
- CO2 Reduction: 34.5% vs baseline
- EV Satisfaction: 78.3%

CONVERGENCIA:
- Actor Loss: -0.45 (convergente)
- Critic Loss: 0.12 (estable)
- Entropy α: 0.21 (decreciente)

STATUS: ✅ ÉXITO
```

---

## ⚠️ CHECKLIST FINAL

### Antes de empezar:
- [ ] Leí DIAGNOSTICO_SAC_EPISODE_RETURN_CERO.md
- [ ] Leí SOLUCION_SAC_FRAGMENTOS.md
- [ ] Verificar que train_sac_multiobjetivo.py existe
- [ ] Verificar que dataset CSVs existen
- [ ] Verificar GPU disponible (`nvidia-smi`)

### Durante fixes:
- [ ] Apliqué Fragmento #1 (main function)
- [ ] Apliqué Fragmento #2 (ambiente)
- [ ] Apliqué Fragmento #3 (SAC training)
- [ ] Apliqué Fragmento #4 (reward scale)
- [ ] Apliqué Fragmento #5 (imports)
- [ ] Syntax check sin errores
- [ ] Archivos guardados

### Durante entrenamiento:
- [ ] Script inicia sin errores
- [ ] Datos cargan en segundos
- [ ] TensorBoard muestra gráficos
- [ ] episode_reward ≠ 0.0 (éxito)
- [ ] Velocidad: 50-100 steps/seg
- [ ] GPU memory: 4-5 GB

### Después:
- [ ] Checkpoints guardados
- [ ] Eval episode reward > -0.02
- [ ] CO2 reduction > 20%
- [ ] Resultados documentados

---

## 🆘 SOPORTE

Si hay problemas:

1. **Error: RealOE2Environment not defined**
   - Solución: Verificar que está definido en mismo archivo (línea ~1800)

2. **Error: SAC not imported**
   - Solución: Agregar `from stable_baselines3 import SAC`

3. **Error: Dataset not found**
   - Solución: Verificar rutas en SOLUCION_SAC_FRAGMENTOS.md

4. **Episode reward still = 0.0**
   - Solución: Verificar que agent.learn() se ejecuta (ver output)
   - Revisar Fragmento #3 fue insertado correctamente

5. **Out of Memory GPU**
   - Solución: Reduce buffer_size en SACConfig.for_gpu (línea ~400)
   - Cambiar de 300K a 150K

---

## 📞 REFERENCIA RÁPIDA

| Problema | Solución | Archivo |
|---|---|---|
| Episode return = 0 | Aplicar Fragmento #3 (agent.learn) | SOLUCION_SAC_FRAGMENTOS.md |
| Reward demasiado pequeño | REWARD_SCALE: 0.01→0.1 | FRAGMENTO #4 |
| Ambiente no existe | Aplicar Fragmento #2 | SOLUCION_SAC_FRAGMENTOS.md |
| SAC no entrena | Verificar imports | FRAGMENTO #5 |
| TensorBoard sin datos | Verificar tb_log_name en learn() | FRAGMENTO #3 |

---

## 🎓 APRENDIZAJES CLAVE

Este problema enseña:
1. **Always test the full pipeline**, no solo componentes individuales
2. **env.reset() + agent.learn() son CRÍTICOS** - sin ellos, no hay training
3. **Reward scaling importa** - rewards muy pequeños → no convergencia
4. **Off-policy (SAC) > On-policy (PPO/A2C)** para este problema
5. **TensorBoard es essential** -monitorear en tiempo real

---

**Autor:** GitHub Copilot (Análisis SAC Training v7.3)  
**Date:** 2026-02-15  
**Status:** READY TO IMPLEMENT ✅

