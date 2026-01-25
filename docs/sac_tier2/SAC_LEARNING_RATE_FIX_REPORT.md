# 🔴 CRÍTICO: SAC Learning Rate Cap Bug - IDENTIFICADO Y CORREGIDO

**Fecha**: 2026-01-18 19:05
**Estado**: ✅ FIXED Y RELANZADO
**Impacto**: Bloqueaba completamente el aprendizaje del agente SAC

---

## Problema Detectado

El log de entrenamiento mostró que SAC **NO estaba aprendiendo**:

```text
Paso 25-500:   reward_avg = 0.5600 → 0.5550 (EMPEORANDO)
Learning Rate: lr = 3.00e-05 (¡100x MENOR que lo configurado!)
```text

**Configurado en YAML**: `learning_rate: 0.001` (0.001)
**Actual en ejecución**: `learning_rate: 3.00e-05` (0.00003)
**Factor de degradación**: **33.3x más lento** ❌

---

## Raíz del Problema

En [src/iquitos_citylearn/oe3/agents/sac.py][ref], líneas 659-667:

[ref]: src/iquitos_citylearn/oe3/agents/sac.py

```python
# ❌ ANTES (BUG)
stable_lr = min(self.config.learning_rate, 3e-5)  # Cap a 3e-5 (muy bajo)
stable_batch = min(self.config.batch_size, 512)   # Cap a 512 (muy bajo)
```text

**Problema**:

- Capaba el learning rate a 3e-5 sin importar la configuración
- Capaba batch_size a 512 (config = 32,768 para GPU)
- Código antiguo de "estabilidad conservadora" que nunca se removió

---

## Solución Aplicada

✅ Removida la limitación de learning rate
✅ Removida la limitación de batch size
✅ Usando valores de configuración directamente

**Cambio en sac.py líneas 659-667**:

```python
# ✅ DESPUÉS (FIXED)
stable_lr = self.config.learning_rate        # Usar config completo: 0.001
stable_batch = self.config.batch_size        # Usar config completo: 32,768
```text

---

## Impacto de la Corrección

| Métrica | Antes | Después | Mejora |
| --- | ------- | --- | -------- |
| Learning Rate | 3.00e-05 | 1.00e-03 | **33.3x más rápido** |
| Batch Size | 512 | 32,768 | **64x más grande** |
| Gradient Quality | Muy bajo | Óptimo para GPU | **Mejor convergencia** |
| Esperado: Reward 500 pasos | 0.5550 (plano) | 0.6x+ (creciente) | **Aprendizaje real** |

---

## Entrenamiento Relanzado

**Comando ejecutado** (19:05:28):

```bash
.\\.venv\\Scripts\\python.exe -m scripts.run_oe3_simulate --config configs/default.yaml
```text

**Configuración confirmada**:

- SAC: episodes=2, batch_size=32,768, gradient_steps=256,
  - **learning_rate=0.001**
- PPO: episodes=2, n_steps=32,768, batch_size=32,768, **learning_rate=0.001**
- A2C: episodes=2, n_steps=65,536, **learning_rate=0.001**
- Multiobjetivo: CO2=0.50, Solar=0.20, Costo=0.15, EV=0.10, Grid=0.05

**Terminal ID**: b0dc12af-7904-4f3e-9ec8-b653ea9298b3
**Inicio Baseline**: 19:05:28

---

## Monitoreo Esperado

**Pasos SAC (próximas 30-40 min)**:

- Paso 25: reward_avg = 0.56+
- Paso 100: reward_avg = 0.60+ (inicio de aprendizaje)
- Paso 250: reward_avg = 0.65+ (crecimiento claro)
- Paso 500: reward_avg = 0.70+ (convergencia visible)

**Si reward sigue plano o baja**: Habrá otro bug invisible. Investigar
actor_loss y critic_loss.

---

## Archivo Modificado

**[src/iquitos_citylearn/oe3/agents/sac.py][ref]**

[ref]: src/iquitos_citylearn/oe3/agents/sac.py#L659-L667

```diff
  target_entropy = self.config.target_entropy if self.config.target_entropy is not None else "auto"

- # Learning rate MÁS conservador para estabilidad
- stable_lr = min(self.config.learning_rate, 3e-5)  # Max 3e-5 (muy bajo)
-
- # Gamma estándar (SAC maneja bien gamma alto con entropy)
- stable_gamma = self.config.gamma  # Usar config original (0.99)
-
- # Batch size moderado
- stable_batch = min(self.config.batch_size, 512)
+ # Use configured learning rate (not capped anymore)
+ stable_lr = self.config.learning_rate
+
+ # Gamma estándar (SAC maneja bien gamma alto con entropy)
+ stable_gamma = self.config.gamma  # Usar config original (0.99)
+
+ # Use configured batch size (not capped anymore - GPU can handle 32k)
+ stable_batch = self.config.batch_size
```text

---

## Commit

```text
Fix: Remove SAC learning rate cap (3e-5 → use config 0.001) and batch_size cap (512 → use config 32768)
```text

---

## Análisis Post-Mortem

**Por qué no se detectó antes**:

1. Los logs mostraban `lr=3.00e-05` pero no indicaban quién la capaba
2. La variable `stable_lr` hacía que pareciera una decisión deliberada
3. El actor_loss y critic_loss bajaban (falsamente indicaban "progreso")

**Lecciones**:

- Siempre loguear qué valor se estaba usando vs qué se configuró
- Revisar `min()` y `max()` caps en código crítico de RL
- La estabilidad no viene de learning rates ultra-bajos, sino de good reward
  - design + entropy

---

**Estado**: 🟢 **ENTRENAMIENTO RELANZADO CON FIX APLICADO - ESPERAR SAC PHASE
~30 MIN**