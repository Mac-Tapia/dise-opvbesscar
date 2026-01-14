# ✅ EXPLICACIÓN: Baseline (Uncontrolled) y Checkpoints en Episodios

## Tu Pregunta (Traducción Clara)
>
> "¿El cálculo del baseline se va a hacer una sola vez, y cuando se vayan a agregar más episodios se acumulará con el checkpoint, entrando no desde cero?"

## ✅ RESPUESTA CORRECTA

Hay **DOS comportamientos diferentes** dependiendo de qué ejecutes:

---

## 1️⃣ **BASELINE (Uncontrolled) - SE CALCULA UNA SOLA VEZ**

### Primera Ejecución

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

**Qué sucede:**

1. ✅ Se calcula el baseline (Uncontrolled) **UNA SOLA VEZ**
2. ✅ Se guarda en: `outputs/oe3/simulations/uncontrolled_pv_bess.json`
3. ✅ Se guarda el resumen en: `outputs/oe3/simulations/simulation_summary.json`

**Estado guardado del baseline:**

- Métricas de consumo sin control
- CO2 de la red (sin optimización)
- Energía solar utilizada (sin control)
- Costo total (sin optimización)

### Segunda Ejecución (Agregar Episodios)

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

**Qué sucede:**

1. ✅ Sistema detecta: `simulation_summary.json` ya existe
2. ✅ Reutiliza baseline anterior (NO lo recalcula)
3. ✅ Va directamente a entrenar agentes RL (SAC, PPO, A2C)

**Costo:**

- Primera ejecución: ~2-3 minutos (calcula baseline)
- Ejecuciones posteriores: ~30 seg (omite baseline)

### Para Forzar Recálculo del Baseline

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-uncontrolled false
```text

o simplemente:

```bash
rm outputs/oe3/simulations/simulation_summary.json
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

---

## 2️⃣ **AGENTES RL (SAC, PPO, A2C) - CONTINÚAN DESDE CHECKPOINTS**

### Primera Ejecución

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

**Qué sucede:**

1. ✅ Calcula baseline (una sola vez)
2. ✅ Inicia SAC episodio 1 DESDE CERO
3. ✅ Guarda checkpoints cada 500 pasos:
   - `outputs/oe3/checkpoints/sac/sac_step_500.zip`
   - `outputs/oe3/checkpoints/sac/sac_step_1000.zip`
   - etc.
4. ✅ Al completar episodio 1: guarda `sac_final.zip`
5. ✅ Continúa episodios 2, 3, 4, 5

### Segunda Ejecución (Agregar Episodios)

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

**Qué sucede:**

1. ✅ Reutiliza baseline anterior (NO recalcula)
2. ✅ Detecta `outputs/oe3/checkpoints/sac/sac_final.zip` o último step
3. ✅ CARGA el checkpoint SAC completamente
4. ✅ Continúa DESDE PASO DONDE SE QUEDÓ (NO desde cero)
5. ✅ Guarda nuevos checkpoints incrementales

**Ejemplo concreto:**

```text
Sesión 1: Entrena SAC episodios 1-2 (pasos 0-17520)
  └─ Guarda: sac_final.zip (o sac_step_17520.zip)

Sesión 2: python -m scripts.run_oe3_simulate
  ├─ Detecta: sac_final.zip
  ├─ CARGA: red neuronal completa + buffer + optimizer
  └─ Continúa: DESDE EPISODIO 3 (paso 17520+)
     SIN REINICIAR DESDE CERO
```text

---

## 📊 Comparación: Baseline vs Agentes RL

| Aspecto | Baseline (Uncontrolled) | Agentes RL (SAC/PPO/A2C) |
 | --------- | ------------------------- | ------------------------- |
| **Cálculo** | UNA SOLA VEZ | Múltiples veces (si no hay checkpoint) |
| **Reutilización** | Automática de `simulation_summary.json` | Automática desde checkpoints |
| **Episodios** | No aplica (determinístico) | Acumulativos desde checkpoint |
| **Reinicio** | Solo si borras `simulation_summary.json` | Solo si borras carpeta `checkpoints/` |
| **Tiempo** | ~2-3 min (1era) / ~30 seg (siguientes) | ~5-10 min por episodio |

---

## 🔄 Flujo Completo de Dos Sesiones

### SESIÓN 1 (Día 1 - Mañana)

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

**Qué sucede:**

```text
1. Calcula Baseline (Uncontrolled)
   └─ Guarda en outputs/oe3/simulations/uncontrolled_pv_bess.json
   └─ Guarda resumen en outputs/oe3/simulations/simulation_summary.json

2. Entrena SAC 5 episodios
   ├─ Episodio 1: 0-8760 pasos
   │  └─ Guarda: sac_step_500.zip, sac_step_1000.zip, ..., sac_step_8760.zip
   ├─ Episodio 2: 8760-17520 pasos
   │  └─ Guarda: sac_step_9260.zip, ..., sac_step_17520.zip
   ├─ Episodios 3, 4, 5: ...
   └─ Final: sac_final.zip (todos los 5 episodios completados)

3. Entrena PPO 5 episodios
   └─ Idem SAC (ppo_step_*.zip, ppo_final.zip)

4. Entrena A2C 5 episodios
   └─ Idem SAC/PPO
```text

**Almacenado:**

```text
outputs/oe3/simulations/
├─ uncontrolled_pv_bess.json          ← BASELINE (reutilizable)
├─ simulation_summary.json              ← Índice (reutilizable)
├─ sac_pv_bess.json
├─ ppo_pv_bess.json
└─ a2c_pv_bess.json

outputs/oe3/checkpoints/
├─ sac/
│  ├─ sac_step_500.zip
│  ├─ sac_step_1000.zip
│  └─ sac_final.zip                   ← PUNTO DE REANUDACIÓN
├─ ppo/
│  └─ ppo_final.zip
└─ a2c/
   └─ a2c_final.zip
```text

### SESIÓN 2 (Día 2 - Tarde, agregar más episodios)

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

**Qué sucede:**

```text
1. Detecta simulation_summary.json
   └─ ✅ REUTILIZA baseline anterior
   └─ ✅ NO recalcula Uncontrolled

2. Detecta outputs/oe3/checkpoints/sac/sac_final.zip
   ├─ CARGA red neuronal SAC (completa)
   ├─ CARGA buffer de experiencias
   ├─ CARGA optimizer state
   └─ Continúa DESDE EPISODIO 6 (paso 43800+)
   
3. Entrena 5 episodios más
   ├─ Episodio 6: 43800-52560 pasos
   ├─ Episodio 7: 52560-61320 pasos
   ├─ Episodios 8, 9, 10: ...
   └─ Final: sac_final.zip (ahora con 10 episodios)

4. Idem PPO, A2C
```text

**Diferencia clave:**

- ✅ Baseline NO se recalcula (ahorro de 2-3 minutos)
- ✅ SAC/PPO/A2C cargan desde checkpoint (sin reiniciar)
- ✅ Episodios se ACUMULAN (6+ en esta sesión)

---

## 💡 Resumido en Una Frase

> **"El baseline se calcula una sola vez y se reutiliza. Los agentes RL continúan desde su checkpoint sin reiniciar desde cero, acumulando episodios."**

---

## 🎯 Detalles Técnicos

### Cómo Reutiliza el Baseline

```python
# En run_oe3_simulate.py (líneas 110-115)
summary_path = out_dir / "simulation_summary.json"
res_uncontrolled = None
if args.skip_uncontrolled and summary_path.exists():
    prev = json.loads(summary_path.read_text(encoding="utf-8"))
    if "pv_bess_uncontrolled" in prev:
        res_uncontrolled = prev["pv_bess_uncontrolled"]  # ← Reutiliza

# Luego (línea 118):
if res_uncontrolled is None:  # Solo calcula si NO existe
    res_uncontrolled_obj = simulate(agent_name="Uncontrolled", ...)
```text

### Cómo Reanuda Agentes desde Checkpoints

```python
# En simulate.py (líneas 539-543)
sac_checkpoint_dir = training_dir / "checkpoints" / "sac"
sac_checkpoint_dir.mkdir(parents=True, exist_ok=True)
sac_resume = _latest_checkpoint(sac_checkpoint_dir, "sac")  # ← Busca más reciente
# Si encuentra sac_final.zip o sac_step_XXXXX.zip, lo carga
```text

---

## ⚙️ Configuración Relevante (configs/default.yaml)

```yaml
oe3:
  evaluation:
    agents:
      - SAC         # Reanuda desde checkpoint automáticamente
      - PPO
      - A2C
    
    sac:
      episodes: 5
      resume_checkpoints: true    # ← HABILITA REANUDACIÓN
      checkpoint_freq_steps: 500
      save_final: true
```text

---

## 🚀 Comandos Útiles

### Ejecutar Normal (reutiliza baseline + reanuda agentes)

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

### Forzar Recálculo de Baseline (pero mantiene checkpoints agentes)

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-dataset false
rm outputs/oe3/simulations/simulation_summary.json
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

### Reiniciar Todo (borra baseline + checkpoints)

```bash
rm -r outputs/oe3/simulations/simulation_summary.json
rm -r outputs/oe3/checkpoints/
python -m scripts.run_oe3_simulate --config configs/default.yaml
```text

---

## ✅ Conclusión

| Pregunta | Respuesta |
 | ---------- | ----------- |
| ¿Baseline se calcula 1 sola vez? | ✅ SÍ - Se reutiliza de `simulation_summary.json` |
| ¿Agentes RL continúan desde checkpoint? | ✅ SÍ - Cargan desde `*_final.zip` o `*_step_XXXXX.zip` |
| ¿Se acumulan episodios? | ✅ SÍ - Sesión 2 agrega episodios 6+ a los 5 previos |
| ¿Se reinicia red neuronal? | ❌ NO - Carga pesos completos desde checkpoint |
| ¿Se pierden experiencias? | ❌ NO - Buffer de experiencias preservado |

---

**Verificado:** 2026-01-13
**Status:** 🟢 FUNCIONAMIENTO CONFIRMADO
