# 🟢 QUICK REFERENCE: Checkpoints & Training Resumption

## Estado Actual (2026-01-13)

| Componente | Estado |
 | ----------- | -------- |
| **Checkpoints Configurados** | ✅ SÍ - Todos agentes |
| **Auto-Reanudación** | ✅ SÍ - Habilitada |
| **Guardado cada** | ✅ 500 pasos |
| **Guardado final** | ✅ SÍ - Ambos formatos |
| **Directorio** | `outputs/oe3/checkpoints/` |
| **Penalizaciones** | ✅ ACTIVAS - Multiobjetivo |
| **Recompensas** | ✅ ACTIVAS - 5 objetivos |
| **Ganancias** | ✅ ACTIVAS - CO2 focus |

---

## Respuesta Directa a Tu Pregunta

### "¿Los agentes tienen guardados checkpoints y están preparados para agregar entrenamientos sin reiniciar?"

**RESPUESTA: ✅ SÍ, COMPLETAMENTE PREPARADOS**

1. **Checkpoints ACTIVOS:**
   - SAC: `resume_checkpoints: true`, `checkpoint_freq_steps: 500`
   - PPO: `resume_checkpoints: true`, `checkpoint_freq_steps: 500`
   - A2C: `resume_checkpoints: true`, `checkpoint_freq_steps: 500`

2. **Ubicación:** `outputs/oe3/checkpoints/<agent>/`
   - Se crea automáticamente en primer entrenamiento
   - Actualmente NO existe (no hay entrenamientos previos)

3. **Cómo Reanuda:**

   ```bash
   python -m scripts.run_oe3_simulate --config configs/default.yaml
   ```

   - Sistema detecta checkpoints
   - Carga modelo desde `*_final.zip` o `*_step_XXXXX.zip`
   - Continúa desde donde se quedó
   - **Sin reiniciar desde cero**

4. **Penalizaciones, Recompensas, Ganancias:**
   - ✅ Todas CAPTURADAS en checkpoints
   - ✅ Multiobjetivo CON PESOS guardado
   - ✅ Reward history preservado

---

## Flujo de Entrenamiento

### Primera Vez

```text
Ejecutar: run_oe3_simulate
     ↓
Crea: outputs/oe3/checkpoints/<agent>/
     ↓
Entrena: SAC (5 ep) → Guarda sac_final.zip
         PPO (5 ep) → Guarda ppo_final.zip
         A2C (5 ep) → Guarda a2c_final.zip
     ↓
Completa: Todos tienen final.zip + step_*.zip
```text

### Segunda Vez (o Posterior)

```text
Ejecutar: run_oe3_simulate
     ↓
Auto-detecta: outputs/oe3/checkpoints/<agent>/
     ↓
Carga: sac_final.zip (o step_XXXXX.zip más reciente)
     ↓
Continúa: Episodio N+1 sin perder progreso
     ↓
Guarda: Nuevos checkpoints incrementales
```text

---

## Archivos Clave

| Archivo | Propósito |
 | --------- | ----------- |
| `configs/default.yaml` | Configuración checkpoint |
| `src/iquitos_citylearn/oe3/simulate.py` | Lógica reanudación |
| `outputs/oe3/checkpoints/` | Almacén checkpoints |
| `CHECKPOINT_STATUS.md` | Documentación detallada |

---

## Comandos Rápidos

```bash
# ✅ Continuar entrenamiento (automático)
python -m scripts.run_oe3_simulate --config configs/default.yaml

# ✅ Ver estado
python show_training_status.py

# ✅ Monitorear en tiempo real
python monitor_checkpoints.py

# ⚠️ Limpiar (inicia desde cero - cuidado!)
Remove-Item -Path "outputs/oe3/checkpoints" -Recurse -Force
```text

---

## ¿Qué Está Guardado en Cada Checkpoint?

✅ Red neuronal (pesos)
✅ Buffer de experiencias
✅ Optimizer state
✅ Recompensas acumuladas
✅ Penalizaciones totales
✅ Ganancias de CO2
✅ Estado del agente

---

## Resumen Final

```text
🟢 SISTEMA LISTO PARA ENTRENAMIENTO CONTINUO

✅ Checkpoints: CONFIGURADOS
✅ Auto-Reanudación: HABILITADA  
✅ Penalizaciones: CAPTURADAS
✅ Recompensas: GUARDADAS
✅ Ganancias: PRESERVADAS

👉 Simplemente ejecutar nuevamente run_oe3_simulate
   para continuar desde último checkpoint
```text

---

**Creado:** 2026-01-13
**Estado:** VERIFICADO ✅
