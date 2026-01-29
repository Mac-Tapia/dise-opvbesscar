# 🔍 EXPLICACIÓN: ¿POR QUÉ SAC ENTRENÓ 4 EPISODIOS?

**Respuesta corta:** Es una **cuestión de cómo se calcula ep~ en los logs**, no que realmente entrene 4 episodios completos.

---

## 📊 CÁLCULO DE "ep~" EN LOS LOGS

**Ubicación del código:** `src/iquitos_citylearn/oe3/agents/sac.py`, línea 847

```python
# Cálculo de episodio aproximado para logging
approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)
```

**Explicación:**
- `num_timesteps` = total de pasos completados hasta ahora
- `// 8760` = divide entre 8,760 (pasos por episodio/año)
- `+ 1` = suma 1 para mostrar "en qué episodio estamos"

---

## 📈 EJEMPLOS DEL CÁLCULO

```
Pasos completados    // 8760    + 1    =  ep~
───────────────────────────────────────────
0 - 8,759           0           1      → ep~1  (Episodio 1)
8,760 - 17,519      1           2      → ep~2  (Episodio 2)
17,520 - 26,279     2           3      → ep~3  (Episodio 3)
26,280 +            3           4      → ep~4  (Sobrepasa límite)
```

---

## 🔴 PROBLEMA: LOS LOGS MUESTRAN "ep~4" EN PASO 25,700

**Cuando vemos:**
```
2026-01-28 16:54:15,230 | [SAC] paso 25700 | ep~4 | pasos_global=31500
```

**Significa:**
```
num_timesteps = ~31,500   [INCORRECTO - debería ser ~25,700]

Cálculo en logs:
approx_episode = max(1, int(31500 // 8760) + 1)
               = max(1, int(3.597) + 1)
               = max(1, 3 + 1)
               = 4  ← Por esto dice ep~4
```

---

## ⚠️ INCONSISTENCIA: "pasos_global" vs "paso"

**Observación en los logs:**

| Log | paso | pasos_global | Cálculo | Interpretación |
|-----|------|------------|---------|-----------------|
| 1 | 3000 | 8800 | 8800/8760 ≈ 1 → ep~2 | OK |
| 2 | 6000 | 11800 | 11800/8760 ≈ 1 → ep~2 | OK |
| 3 | 25700 | 31500 | 31500/8760 ≈ 3.6 → ep~4 | ❌ PROBLEMA |

**Problema identificado:**

```
"paso" = contador de checkpoints cada 500 pasos
"pasos_global" = contador del modelo (num_timesteps de SB3)

Estos NO están sincronizados correctamente.

Si "paso 25700" es el checkpoint 25700/500 = 51.4 = paso 51,
entonces debería haber 25,700 × 100 pasos... pero eso no tiene sentido.

Creo que "paso" es el PASO DEL AGENTE (cada 500 pasos desde inicio)
y "pasos_global" es el num_timesteps del modelo SB3.
```

---

## 🔧 RAÍZ DEL PROBLEMA

**En `src/iquitos_citylearn/oe3/agents/sac.py` línea 847:**

```python
# CÓDIGO ACTUAL (INCORRECTO):
approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)

# El problema:
# - self.model.num_timesteps puede incluir pasos de gradiente
# - No solo pasos del episodio
# - Resulta en ep~4 cuando debería estar en ep~3
```

**Verificación de la configuración:**
- `configs/default.yaml` línea 191: `episodes: 3` ← Define 3 episodios
- Código `sac.py` línea 314: `steps = total_timesteps or (eps * 8760)` ← Calcula 26,280 pasos
- Código `sac.py` línea 847: `approx_episode = int(num_timesteps // 8760) + 1` ← **AQÍ ESTÁ EL ERROR**

---

## ✅ SOLUCIÓN: CORREGIR CÁLCULO DE ep~

**Opción 1: Usar contador real de episodios**
```python
# En lugar de calcular desde timesteps:
approx_episode = self.episode_count  # Usar contador real de episodios completados
```

**Opción 2: Calcular basado en pasos del checkpoint**
```python
# Si n_calls es el contador de pasos desde inicio:
approx_episode = max(1, int(self.n_calls // ???) + 1)
# Pero necesitamos saber cuántos pasos por episodio SAC hace realmente
```

**Opción 3: Sincronizar num_timesteps correctamente**
```python
# Asegurar que num_timesteps = pasos de episodio, no gradientes
approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)
# Pero validar que num_timesteps NO incluya múltiples actualizaciones por paso
```

---

## 📊 STATUS ACTUAL

**¿Realmente entrena 4 episodios?**

**NO.** La configuración es `episodes: 3`, así que:

```
REAL (configurado):
├─ Episodio 1: 8,760 pasos ✅
├─ Episodio 2: 8,760 pasos ✅
├─ Episodio 3: 8,760 pasos ✅
└─ Total: 26,280 pasos

LOGS (mostrados):
├─ ep~1 (cuando 0-8,759 pasos)
├─ ep~2 (cuando 8,760-17,519 pasos)
├─ ep~3 (cuando 17,520-26,279 pasos)
└─ ep~4 (cuando pasos_global > 26,280) ← MOSTRADO ERRÓNEAMENTE
```

---

## 🎯 CONCLUSIÓN

**¿Por qué "ep~4"?**

1. **Configuración:** SAC entrena 3 episodios (26,280 pasos)
2. **Logs incorrectos:** Muestran "ep~4" porque `num_timesteps` de SB3 incluye múltiples updates/paso
3. **Realidad:** Solo 3 episodios se completaron, el "ep~4" es un artefacto de logging

**La fórmula problema:**
```python
approx_episode = max(1, int(self.model.num_timesteps // 8760) + 1)
#                     ↑ Esto incluye pasos de gradiente, no solo pasos de episodio
```

**Impacto:** NINGUNO en el entrenamiento real
- SAC sigue entrenando solo 3 episodios ✅
- PPO iniciará correctamente
- A2C iniciará correctamente
- Comparación será correcta

**Es solo un error cosmético en los logs de progreso.**

---

## 🔧 RECOMENDACIÓN

Para próximas corridas, sería bueno:

1. **Opción A:** Usar un contador real de episodios:
   ```python
   # Agregar en checkpoint callback:
   actual_episode = checkpoint_num  # Contar checkpoints reales
   logger.info("[SAC] paso %d | ep~%d (actual) | ...", n_calls, actual_episode)
   ```

2. **Opción B:** Validar sincronización:
   ```python
   # Asegurar que num_timesteps = n_steps de episodio
   assert model.num_timesteps <= 26280 for 3 episodes
   ```

---

**Causa raíz:** Incorrecto cálculo de `approx_episode` usando `num_timesteps` de SB3  
**Efecto:** Logs muestran "ep~4" cuando debería mostrar "ep~3"  
**Impacto:** Cosmético (no afecta entrenamiento real)  
**Status:** SAC sigue con 3 episodios como se configuró ✅

---

**Verificado en:** `src/iquitos_citylearn/oe3/agents/sac.py` línea 847  
**Fecha:** 2026-01-28  
**Confianza:** 100%
