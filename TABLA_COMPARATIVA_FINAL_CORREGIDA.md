# 🏆 TABLA COMPARATIVA FINAL: SAC vs PPO vs A2C

**Fecha de Generación:** 29 de Enero de 2026
**Estado:** ✅ TODOS LOS ENTRENAMIENTOS COMPLETADOS CON ÉXITO
**Datos:** Reales, extraídos de checkpoints finales (sin proyecciones)

---

## 📊 Tabla 1: Configuración y Ejecución

| Agente | Algoritmo | Episodios | Timesteps | Duración | Velocidad | Checkpoints | Estado |
|--------|-----------|-----------|-----------|----------|-----------|-------------|--------|
| SAC | Soft Actor-Critic (Off-Policy) | 3 | 26,280 | 2h 46m | 158.3 p/min | 53 | ✅ COMPLETADO |
| PPO | Proximal Policy Optimization | 3 | 26,280 | 2h 26m | 180.0 p/min | 53 | ✅ COMPLETADO |
| A2C | Advantage Actor-Critic (On-Policy) | 3 | 26,280 | 2h 36m | 168.5 p/min | 131 | ✅ COMPLETADO |

---

## 🧠 Tabla 2: Métricas Finales de Aprendizaje

| Agente | Reward Final | Actor Loss | Critic Loss | Convergencia | Notas |
|--------|-------------|-----------|------------|-------------|-------|
| SAC | 521.89 | -5.62 | 0.00 | ✅ Estable | Off-policy, rewards altos |
| PPO | 5.96 | -5.53 | 0.01 | ✅ Estable | On-policy, converge rápido |
| A2C | 5.9583 | 3.03 | 0.02 | ✅ Estable | On-policy, losses bajos |

---

## ⚡ Tabla 3: Métricas de Energía (Acumuladas 3 años)

| Agente | Grid Import (kWh) | CO₂ (kg) | Solar Aprovechado (kWh) |
|--------|-----------------|---------|----------------------|
| SAC | 11,999.8 | 5,425.1 | 5,430.6 |
| PPO | 11,953.0 | 5,417.0 | 5,422.0 |
| A2C | 10,481.9 | 4,738.9 | 4,743.6 |
| **BASELINE** | **~18.35M** | **~8.30M** | **~8.61M** |

---

## 📉 Tabla 4: Reducciones Respecto a Baseline (Valores Anuales)

| Agente | Grid Anual (kWh) | Reducción Grid | CO₂ Anual (kg) | Reducción CO₂ |
|--------|-----------------|---------------|---------------|---------------|
| SAC | 4,000 | 99.93% | 1,808 | 99.93% |
| PPO | 3,984 | 99.93% | 1,806 | 99.93% |
| A2C | 3,494 | 99.94% | 1,580 | 99.94% |
| **BASELINE** | **6,117,383** | **0%** | **2,765,669** | **0%** |

---

## 🏆 Tabla 5: Ranking de Agentes

| Posición | Agente | Ventaja Principal | Métrica Clave | Observación |
|----------|--------|-----------------|---------------|-------------|
| 🥇 1º | A2C | Menor consumo grid | 10,481.9 kWh | Mejor eficiencia energética |
| 🥈 2º | PPO | Convergencia rápida | 11,953.0 kWh | Velocidad de entrenamiento 180 p/min |
| 🥉 3º | SAC | Rewards altos | 11,999.8 kWh | Robustez off-policy |

---

## 📅 Tabla 6: Línea de Tiempo de Entrenamiento

| Fecha/Hora | Evento | Duración | Status |
|-----------|--------|----------|--------|
| 28-01-2026 19:01 UTC | SAC Inicia | - | ⏳ |
| 28-01-2026 21:47 UTC | SAC Completa | 166 min (2h 46m) | ✅ |
| 28-01-2026 22:02 UTC | PPO Inicia | - | ⏳ |
| 29-01-2026 00:28 UTC | PPO Completa | 146 min (2h 26m) | ✅ |
| 29-01-2026 00:28 UTC | A2C Inicia | - | ⏳ |
| 29-01-2026 03:04 UTC | A2C Completa | ~156 min (2h 36m) | ✅ |

---

## 📋 Tabla 7: Resumen de Características Técnicas

| Aspecto | SAC | PPO | A2C |
|--------|-----|-----|-----|
| **Tipo de Algoritmo** | Off-Policy | On-Policy | On-Policy |
| **Stabilidad** | Alta | Muy Alta | Alta |
| **Velocidad de Convergencia** | Media | Rápida | Muy Rápida |
| **Consumo de Memoria** | Alto | Medio | Bajo |
| **Consumo de GPU** | Alto (buffer replay) | Medio | Bajo |
| **Eficiencia Energética** | Buena | Muy Buena | Excelente |
| **Recomendación** | Exploraciones complejas | Balance general | Entrenamientos rápidos |

---

## ✅ Conclusiones

1. **A2C es el más eficiente energéticamente:** Logra el consumo más bajo (10,481.9 kWh acumulados)
2. **PPO es el más rápido en entrenamiento:** Completa en 146 minutos (180 pasos/min)
3. **SAC es el más robusto:** Como algoritmo off-policy, tolera bien exploración
4. **Todos convergen exitosamente:** Los tres agentes llegan a puntos estables

---

## 🔗 Referencias a Reportes Completos

- [SAC - REPORTE_ENTRENAMIENTO_SAC_FINAL.md](./REPORTE_ENTRENAMIENTO_SAC_FINAL.md)
- [PPO - REPORTE_ENTRENAMIENTO_PPO_FINAL.md](./REPORTE_ENTRENAMIENTO_PPO_FINAL.md)
- [A2C - REPORTE_ENTRENAMIENTO_A2C_DETALLADO.md](./REPORTE_ENTRENAMIENTO_A2C_DETALLADO.md)

