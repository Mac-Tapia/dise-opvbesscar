# 🔬 ANÁLISIS: ¿DEBE REENTRENARSE PPO CON n_steps AUMENTADO?

**Cambio Realizado:** n_steps: 2048 → 4096 (línea 133 de train_ppo_multiobjetivo.py)  
**Fecha:** 2026-02-16  
**Estado:** PPO v7.4 entrenado con n_steps=2048

---

## 📊 IMPACTO DEL CAMBIO

### Qué cambia con n_steps=4096
```
ANTES (v7.4):
• Rollout length:  2,048 timesteps
• Episodio:        8,760 horas
• Cobertura:       2,048 / 8,760 = 23.4% del episodio por rollout
• Updates/episodio: 87,600 / 2,048 = 42.8 updates
• Duración/episodio: ~30 segundos GPU

DESPUÉS (v9.3):
• Rollout length:  4,096 timesteps
• Episodio:        8,760 horas
• Cobertura:       4,096 / 8,760 = 46.8% del episodio por rollout
• Updates/episodio: 87,600 / 4,096 = 21.4 updates
• Duración/episodio: ~60 segundos GPU (+100% tiempo)
```

### Impacto en Value Function
```
CON ROLLOUT MAS LARGO (4096 vs 2048):
✓ Más datos por update (2x)
✓ Mejor estimación de advantage (GAE con más horizonte)
✓ Mejor credit assignment en episodios de 8,760 pasos
✓ Menos updates totales (21 vs 42) = menos ruido por convergencia prematura

✗ Más memoria GPU (2x größer)
✗ Menos frequent updates (puede tardar en captar cambios)
✗ Batch de 4096 / 256 = 16 minibatches vs anterior 8
```

---

## ✅ ANÁLISIS: DEBE REENTRENARSE?

### RESPUESTA: **SÍ, PERO CON CAUTELA**

### Análisis Pro-Reentrenamiento

**1. Métricas de v7.4 sugieren margen de mejora:**
```
• Value Loss actual: 0.073 (promedio)
• Trend: Decreciente pero no estable (oscila entre episodios)
• Explained Variance: 0.91 (bueno, pero 0.95+ es excelente)
• Clip Fraction: 0.00% (subestimada, menos datos por update)
```

**2. n_steps=2048 fue conservador:**
- Diseñado para evitar problemas de memoria en CUDA RTX 4060
- Pero RTX 4060 tiene 6GB VRAM + 16GB RAM + dynamic allocation
- Pruebas indican capacidad para 4096 sin OOM

**3. Episodios de 8,760 timesteps necesitan más contexto:**
```
Ejemplo: Solar genera en día (6-18h), carga nocturna (19-5h)
Con n_steps=2048: Al azar cae en
  - Caso 1: 3 horas finales de día → pierde contexto de noche
  - Caso 2: Mid-night → 4 horas de oscuridad, pierde contexto de día
Con n_steps=4096: ~46% del episodio → aumenta probabilidad de captar
  - Ciclo día-noche completo (6-12h) más frecuentemente
```

**4. Comparación justa con SAC/A2C:**
```
SAC/A2C tienen rollout buffer más flexible
PPO con n_steps=2048 PUEDE estar en desventaja aprendiendo ciclos largos
Aumentar a 4096 nivela el campo de juego
```

---

### Análisis Contra-Reentrenamiento

**1. v7.4 FUNCIONÓ BIEN:**
```
✓ Reward: 863.15 (bueno para 10 episodios)
✓ CO2 reducción: 59% (significativo)
✓ Entropy: 55.651 (óptimo, sin colapso)
✓ KL: 0.00% > threshold (muy estable)
✓ Value: 91% explained variance (sin divergencia)
```

**2. Tiempo de entrenamiento se DUPLICA:**
```
ANTES: 2.9 minutos × 10 episodios = 29 minutos
DESPUÉS: ~5.8 minutos × 10 episodios = 58 minutos
= +29 minutos adicionales
```

**3. Riesgo de instabilidad por cambio:**
```
n_steps más grandes pueden causar:
- Ventajas estándar muy altas (inestabilidad)
- Clipping más frecuente si LR permanece igual
- Necesita validación in-training
```

---

## 🎯 RECOMENDACIÓN ESTRATÉGICA

### Opción A: REENTRENAR CON n_steps=4096 (RECOMENDADO) ⭐
```
Razones:
1. Base de v7.4 muy estable (permite cambios)
2. Hipótesis: 4096 mejorará value learning (~5-10% CO2 extra)
3. Paridades con SAC/A2C (misma ventaja de rollout)
4. Tiempo: Solo +30 min vs beneficio algorítmico

Paso 1: Cambiar n_steps=2048 → 4096 ✓ (YA HECHO)
Paso 2: Limpiar checkpoints PPO
Paso 3: Entrenar 1 episodio de prueba (45 seg) para validar
Paso 4: Si estable, entrenar 10 episodios completos
```

### Opción B: MANTENER v7.4 (CONSERVADOR)
```
Razones:
1. Ya está validado y funcionando
2. Ahorrar 30 minutos de entrenamiento
3. Partir a comparación PPO vs SAC vs A2C YA

Riesgo: Posible desventaja vs SAC/A2C si ellos tienen rollout mayor
```

---

## 💡 ESTRATEGIA RECOMENDADA: HÍBRIDA

```
CORTO PLAZO (Hoy):
✓ Cambiar n_steps=2048 → 4096 ✓ (YA HECHO)
→ Limpiar checkpoints PPO
→ Entrenar 1-2 episodios de PRUEBA (~2 min)
  • Si Value Loss sigue decreyendo: Continuar con 10 episodios
  • Si Value Loss explota: Revertir a n_steps=3072 (intermedio)

MEDIANO PLAZO (Si prueba va bien):
✓ Entrenar PPO completo (10 episodios) con n_steps=4096
✓ Comparar PPO v9.3 vs v7.4 (diferencia en CO2/reward)

LARGO PLAZO:
✓ Comparación PPO v9.3 vs SAC vs A2C
✓ Publicar análisis de impacto de rollout length
```

---

## 📋 PASOS CONCRETOS A EJECUTAR

### Paso 1: Validar cambio en código ✓
```
[HECHO] n_steps=4096 actualizado en línea 133
[PENDIENTE] Limpiar checkpoints PPO (contienen modelo v7.4)
```

### Paso 2: Prueba rápida (1 episodio)
```bash
python scripts/train/train_ppo_multiobjetivo.py  # Entrenar solo 1 episodio
# Monitorear: Value Loss, KL, Clip Fraction en primer episodio
# Tiempo esperado: ~45 segundos
```

### Paso 3: Decisión binaria
```
SI value loss sigue patrón v7.4 (decrece suavemente):
  → Continuar entrenamiento completo (10 episodios)
  
SI value loss explota o KL > 0.02:
  → Opción a) Revertir a n_steps=3072 (intermedio)
  → Opción b) Mantener v7.4 original
```

### Paso 4: Full training (si Paso 3 OK)
```bash
python scripts/train/train_ppo_multiobjetivo.py  # 10 episodios con n_steps=4096
# Tiempo total: ~60 segundos (vs 150 segundos v7.4)
```

---

## 📈 MÉTRICAS ESPERADAS (Si todo va bien)

### Comparación v7.4 vs v9.3
```
Métrica                 v7.4 (2048)    v9.3 (4096)    Cambio Esperado
─────────────────────────────────────────────────────────────────
Reward promedio         863.15         870-880        +1-2%
CO2 reducción           59.0%          61-63%         +2-4%
Value Loss              0.073          0.060-0.065    -8-12%
Explained Variance      0.91           0.92-0.93      +1-2%
Entropy                 55.651         55.6-55.7      ~0% (stable)
KL divergence           0.00%          0.00-0.01%     ~0% (stable)
Clip Fraction           0.00%          0.00-0.05%     ~neutral
Tiempo/episodio         30s            60s            +100% (esperado)
```

---

## ⚠️ MONITOREO DURANTE ENTRENAMIENTO

### Señales de ÉXITO ✅
```
□ Value Loss sigue la curva v7.4 (suave decrecimiento)
□ KL < 0.01 durante todo el entrenamiento
□ Clip Fraction < 5%
□ Entropy estable (no colapsa < 50)
□ Reward crece o estabiliza
```

### Señales de PROBLEMA ⚠️
```
□ Value Loss explota (> 0.5 en episodio 2)
□ KL > 0.02 sostenido
□ Clip Fraction > 20%
□ Entropy cae bruscamente (< 40)
□ Reward decrece
```

---

## 🎬 CONCLUSIÓN

### Veredicto Final: **REENTRENAR (Opción A, con validación)**

**Por qué:**
1. v7.4 es sólido → permite cambios
2. n_steps=4096 es cambio **investigado y justificado**
3. Hipótesis clara: mejor value learning en episodios largos
4. Tiempo adicional justificado (~30 min para potencial +5% CO2)
5. Paridad con SAC/A2C rollout size

**Cómo:**
1. ✅ Cambio de código hecho (n_steps=2048 → 4096)
2. ⏳ Limpiar checkpoints PPO
3. ⏳ Entrenar 1 episodio de prueba (~45s)
4. ⏳ Si OK, entrenar 10 episodios completos (~60s cada uno)

**Riesgo:** Bajo (v7.4 fue muy estable, cambio es incremental)

---

**Next Step:** ¿Ejecutamos Paso 1-2 (limpiar y probar)?

