# OBJETIVO ESPECÍFICO: ENTRENAMIENTO Y SELECCIÓN DE AGENTES RL

## 🎯 OBJETIVO ESPECÍFICO

**Seleccionar el agente inteligente de gestión de carga de motos y mototaxis eléctricas más apropiado para maximizar la eficiencia operativa del sistema, asegurando:**
1. **Reducciones DIRECTAS de CO₂:** -241 t/año (sincronización solar)
2. **Reducciones INDIRECTAS de CO₂:** -78 t/año (máximo BESS + solar)
3. **TOTAL:** -319 t CO₂/año (-59% vs baseline 537 t)
4. **Capacidad de expansión:** Soportar +1-2M kWh/año sin impacto CO₂ proporcional

---

## 🔗 ALINEAMIENTO JERÁRQUICO

```
OBJETIVO GENERAL
├─ "Infraestructura de carga inteligente para reducir CO₂ en Iquitos"
│  └─ OE2: Dimensionar infraestructura (4,050 kWp + 4,520 kWh BESS + 128 chargers)
│  └─ OE3: Control inteligente (agentes RL)
│
├─ BASELINE: 537 t CO₂/año (sin control)
│  └─ Problemas identificados: 4 limitantes operativas
│
└─ OBJETIVO ESPECÍFICO (ACTUAL)
   ├─ Entrenar: SAC, PPO, A2C
   ├─ Seleccionar: "Más apropiado"
   └─ Meta: Cuantificar reducción de CO₂ Iquitos
```

---

## 📊 ¿QUÉ SIGNIFICA "MÁS APROPIADO"?

### Criterios de Selección (Ordenados por Prioridad)

#### 1️⃣ CRITERIO PRINCIPAL: Reducciones Cuantificables de CO₂

| Componente | Métrica | Baseline | Meta RL | Estado |
|-----------|---------|----------|---------|--------|
| **Reduc. DIRECTA** | Sincronización solar | 0 t | -241 t/año | ← SAC debe lograr |
| **Reduc. INDIRECTA** | Máximo BESS + solar noche | 0 t | -78 t/año | ← SAC debe lograr |
| **Reduc. TOTAL** | CO₂ final vs baseline | 537 t | ≤218 t | -59% (-319 t) |
| **Autoconsumo Solar** | % de demanda | ~30% | 60-80% | Target |
| **Grid Térmico** | MWh importado | 831 MWh | 240-300 MWh | -60-70% |

**✅ MÁS APROPIADO = Agente que logre máxima reducción -319 t CO₂ (directa + indirecta)**

---

#### 2️⃣ CRITERIO SECUNDARIO: Resolver Limitaciones Operativas

| Limitación SIN CONTROL | Problema | Solución RL | Validación |
|--------|----------|-----------|-----------|
| Ocupación desigual (49.8%) | 50% capacidad ociosa | Desplazamiento flexible | Motos cargadas 70%+ en horas solares |
| Autoconsumo bajo (30%) | 70% desde GRID | Sincronización solar | Autoconsumo sube a 60-80% |
| Picos nocturnos (410 kW) | 100% GRID @ 18:00 | BESS lleno en día | Picos 70% desde BESS |
| Ciclo inverso | Carga noche, solar día | Ciclo coherente | Noche 100% desde BESS (renovable) |

**✅ MÁS ESTABLE = Agente que resuelva 4/4 limitaciones**

---

#### 3️⃣ CRITERIO TERCIARIO: Capacidad de Expansión

| Métrica | Sin Control | Con RL | Agente Ganador |
|---------|-----------|--------|----------------|
| Volumen actual | 1,187 MWh/año | 1,200-1,400 MWh | +1-18% sin sacrificar CO₂ |
| Potencial expansión | 2,394 MWh adicional | Soportable con RL | Expandir flota sin +CO₂ proporcional |
| CO₂ per MWh | 0.452 t/MWh | 0.112-0.184 t/MWh | 2.5-4× mejor eficiencia |
| Escalabilidad | Imposible (limite thermal) | Viable (RL optimiza) | Agente reproducible |

**✅ MÁS ESCALABLE = Agente que permita duplicar flota (537 → 485 t CO₂ vs baseline 537)**

---

## 🎯 DEFINICIÓN OPERATIVA: "MÁS APROPIADO"

Un agente es "más apropiado" si:

### Orden de Importancia

1. **[CRÍTICO]** Reduce CO₂ en ≥60% (de 537 → ≤215 t/año)
2. **[CRÍTICO]** Mantiene 100% EV Satisfaction (no hay demanda insatisfecha)
3. **[CRÍTICO]** Preserva Taxi Priority (sin diferimientos involuntarios)
4. **[IMPORTANTE]** Maximiza autoconsumo solar (>60%)
5. **[IMPORTANTE]** Converge rápido (<5 episodios al plateau)
6. **[DESEABLE]** Varianza baja en reward (σ < 10% de media)

## 🧮 FÓRMULA DE SELECCIÓN (Actualizada)

```
SCORE_AGENTE = 
  0.50 × (Reduc_CO2_Lograda / 319) +      ← Pesa directa + indirecta
  0.20 × (EV_Satisfaction / 100) +         ← Debe mantener 100%
  0.15 × (Autoconsumo_Solar / 80) +        ← Meta 60-80%
  0.10 × (BESS_Utilizacion / 90) +         ← Meta 70-90%
  0.05 × (1 - Sigma_Reward / 10)           ← Estabilidad

EJEMPLO SAC:
= 0.50 × (300/319) +
  0.20 × (100/100) +
  0.15 × (75/80) +
  0.10 × (80/90) +
  0.05 × (1 - 0.06/10)
= 0.50×0.94 + 0.20×1.0 + 0.15×0.94 + 0.10×0.89 + 0.05×0.99
= 0.47 + 0.20 + 0.14 + 0.09 + 0.05
= 0.95 ← Excelente
```

**Ganador:** Agente con SCORE más alto (máximo 1.0)

---

## 🏆 AGENTES EN COMPETENCIA (Actualizado)

### SAC (Soft Actor-Critic)
**¿Qué debe aprender?**
1. ✅ Desplazar motos a horas solares (-241 t DIRECTA)
2. ✅ Llenar BESS en mediodía (-78 t INDIRECTA)
3. ✅ Servir picos 70% desde BESS (energía renovable)
4. ✅ Crear ciclo diario solar-coherente

**Ventajas esperadas:**
- ✓ Off-policy: Aprende rápido de diferentes estrategias
- ✓ Entropía adaptativa: Explora bien sincronización solar
- ✓ Muestro-eficiente: Puede detectar patrón 24h rápidamente

**Predicción:** 🎯 GANADOR - Logra -60% CO₂ (-300 t), SAC score 0.92-0.96

---

### PPO (Proximal Policy Optimization)
**¿Qué debe aprender?**
1. ✅ Ídem SAC pero más conservador
2. ✅ Validar que cambios son estables
3. ✅ Evitar sobre-optimizaciones que sacrifiquen restricciones

**Ventajas esperadas:**
- ✓ On-policy: Garantiza que cada cambio es "safe"
- ✓ Clipping: Evita saltos bruscos en decisiones
- ✓ Robusto: Mantiene restricciones mejor

**Predicción:** 🏅 SEGUNDO - Logra -58% CO₂ (-296 t), PPO score 0.88-0.92

---

### A2C (Advantage Actor-Critic)
**¿Qué debe aprender?**
1. ⚠️ Ídem SAC/PPO pero más lentamente
2. ⚠️ Baseline simple para validar concepto
3. ⚠️ Si falla, indica que RL es difícil

**Ventajas esperadas:**
- ✓ Simple: Fácil debuggear si algo falla
- ✓ Baseline: Si A2C logra -50%, entonces concepto es sólido
- ✓ Referencia: Comparar convergencia

**Predicción:** 🔧 REFERENCIA - Logra -50% CO₂ (-258 t), A2C score 0.70-0.78

---

## � CÓMO SE COMPONE LA REDUCCIÓN: DIRECTA + INDIRECTA

### Reducción DIRECTA (-241 t CO₂/año): Sincronización Solar

**Mecanismo:** Cargar motos en horas donde hay solar = menos imports GRID

```
Baseline (sin control):
  - Autoconsumo solar: 30% = 70% desde GRID
  - 70% × 1,187 MWh × 0.4521 kg CO₂/kWh = 375 t CO₂ por imports

Con RL (sincronización):
  - Autoconsumo solar: 75% = 25% desde GRID
  - 25% × 1,187 MWh × 0.4521 kg CO₂/kWh = 134 t CO₂ por imports

Reducción DIRECTA = 375 - 134 = -241 t CO₂/año
```

**El agente RL aprende:** Cargar cuando hay solar = 0 CO₂ incremental

---

### Reducción INDIRECTA (-78 t CO₂/año): Máximo BESS + Renovable Nocturna

**Mecanismo:** Llenar BESS en mediodía con solar → servir picos nocturnos desde BESS

```
Baseline (sin control):
  - Pico nocturno (18:00): 410 kW × 6h = 2,460 kWh
  - 100% desde GRID térmico
  - 2,460 kWh × 0.4521 kg CO₂/kWh = 111 t CO₂/año en picos

Con RL (BESS lleno):
  - 70% desde BESS (energía renovable almacenada): 0 CO₂
  - 30% desde GRID: 738 kWh × 0.4521 kg CO₂/kWh = 33 t CO₂/año

Reducción INDIRECTA = 111 - 33 = -78 t CO₂/año
```

**El agente RL aprende:** Llenar BESS de día = picos nocturnos renovables

---

### TOTAL: -319 t CO₂/año (-59%)

```
Baseline:          537 t CO₂/año (100%)
- Directa:         -241 t CO₂/año (-45%)
- Indirecta:       -78 t CO₂/año (-15%)
= Nuevo Total:     218 t CO₂/año (41% del baseline, -59% reducción)
```

---

## 📊 MATRIZ DE RESULTADOS ESPERADOS

### Expectativas Entrenamiento (Actualizado)

| Métrica | SAC | PPO | A2C | META | Cálculo |
|---------|-----|-----|-----|------|---------|
| **CO₂ t/año** | 210-230 | 215-240 | 280-350 | ≤218 | -59% vs 537 |
| **CO₂ Reducción Directa** | -235-245 | -225-240 | -150-200 | -241 | Sincronización solar |
| **CO₂ Reducción Indirecta** | -72-82 | -70-80 | -40-60 | -78 | BESS + renovable noche |
| **TOTAL Reducción %** | 57-61% | 55-60% | 40-55% | ≥59% | (Directa + Indirecta) |
| **Autoconsumo %** | 72-82% | 68-78% | 55-70% | >60% | Solar sincronizado |
| **BESS Utilización** | 75-88% | 70-85% | 60-75% | >70% | Ciclo diario |
| **EV Satisfaction** | 100% | 100% | 100% | 100% | Sin comprometer |
| **Taxi Priority** | ✓ Preservado | ✓ Preservado | ✓ Preservado | ✓ Obligatorio | Críticos garantizados |
| **Picos desde GRID** | 25-35% | 28-40% | 45-60% | <40% | 410 kW @18:00 |
| **Picos desde BESS** | 65-75% | 60-72% | 40-55% | >60% | Energía renovable |
| **Convergencia** | 3-5 ep | 5-8 ep | 8-12 ep | <10 ep | Rapidez aprendizaje |
| **Varianza σ** | 5-8% | 4-6% | 8-12% | <10% | Estabilidad reward |

**Interpretación:**
- SAC es FAVORITO: Logra -60% CO₂ (directa -240 + indirecta -75)
- PPO es EQUILIBRADO: Logra -58% CO₂ con más estabilidad
- A2C es REFERENCIA: Si logra -50%, entonces RL es viable; si falla, revisar SAC/PPO

---

## 🏆 PROCESO DE SELECCIÓN

### Fase 1: Entrenamiento Paralelo (EN PROGRESO)
```
Tiempo 0h
├─ SAC: Inicia training (AHORA, paso 2300/26280)
├─ PPO: Espera finalización SAC
└─ A2C: Espera finalización PPO
```

**SAC:** 🟡 26,280 timesteps = ~10 episodios (2-3 horas GPU RTX 4060)

### Fase 2: Evaluación Comparativa (PENDIENTE)
```
Cuando SAC, PPO, A2C terminen:

1. Extraer métricas finales:
   - CO₂ anual final
   - Autoconsumo solar alcanzado
   - EV Satisfaction mantenido
   - Varianza reward
   - Rapidez convergencia

2. Calcular SCORE_AGENTE para cada uno

3. Ranking: Mejor → Segundo → Tercero
```

### Fase 3: Validación (PENDIENTE)
```
Al agente ganador:

1. Ejecutar 5 validaciones adicionales (distintas semillas)
   → Confirmar reproducibilidad

2. Verificar restricciones:
   - SOC BESS > 15% siempre
   - Taxi nunca diferido
   - EV Sat = 100% siempre

3. Generar reporte final:
   - Comparativa cuantificada
   - Justificación de selección
   - Recomendación para implementación Iquitos
```

---

## � ÉXITO DEL ENTRENAMIENTO (Criterios Definitivos)

### Objetivo Específico Logrado SI SAC demuestra que:

1. ✅ **Reducciones DIRECTAS:** -235 a -245 t CO₂/año (vs meta -241)
   - Sincronización solar: autoconsumo sube a 70-80%
   - Grid imports bajan de 831 MWh a 240-300 MWh

2. ✅ **Reducciones INDIRECTAS:** -72 a -82 t CO₂/año (vs meta -78)
   - BESS utilización sube a 75-85%
   - Picos nocturnos 70% desde BESS (energía renovable)

3. ✅ **TOTAL:** -300 a -320 t CO₂/año (537 → 210-237 t, -59%)
   - Alcanza o supera meta de -319 t

4. ✅ **Restricciones Preservadas:**
   - EV Satisfaction = 100% SIEMPRE
   - Taxi Priority = garantizado (nunca diferido)
   - BESS SOC > 15% siempre
   - Rampa power < 50 kW/min

5. ✅ **Reproducibilidad:** 
   - 5 validaciones con distintas semillas
   - Varianza σ < 8% en reward final

6. ✅ **Escalabilidad:**
   - Sistema soporta +1-2M kWh/año sin +CO₂ proporcional
   - Eficiencia: 0.112-0.184 t CO₂/MWh (vs 0.452 baseline)

**ENTONCES:** Proyecto alcanza objetivo específico = SAC es "más apropiado" = Implementación en Iquitos viable

---

## 🎬 SALIDAS ESPERADAS

### Documento Final: Comparativa Agentes
```markdown
# Resultados: SAC vs PPO vs A2C

## Ranking Final
1. 🥇 SAC: CO₂ = 145 t/año (-73%), Score = 0.87
2. 🥈 PPO: CO₂ = 165 t/año (-69%), Score = 0.82
3. 🥉 A2C: CO₂ = 240 t/año (-55%), Score = 0.68

## Recomendación
**SAC es MÁS APROPIADO:** Máxima reducción CO₂ + estable + rápido

## Conclusión
PVBESSCAR puede implementarse con SAC:
- Reducirá 392 t CO₂/año en Iquitos
- Autoconsumo solar subirá de 30% → 73%
- EV Satisfaction = 100% (sin sacrificios)
```

### Archivos Asociados
- ✓ `OBJETIVO_GENERAL_PROYECTO.md` - Marco estratégico
- ✓ `REPORTE_ANALISIS_CARGA_SIN_CONTROL.md` - Problemas + correcciones
- ✓ `OBJETIVO_ESPECIFICO_ENTRENAMIENTO_AGENTES.md` - Este documento
- ⏳ `RESULTADOS_COMPARATIVA_AGENTES_FINALES.md` - Post-entrenamiento

---

## 📅 CRONOGRAMA

| Fase | Tarea | ETA | Status |
|------|-------|-----|--------|
| 1 | SAC Entrenamiento | +2h | 🟡 En progreso |
| 2 | PPO Entrenamiento | +4h | ⏳ Tras SAC |
| 3 | A2C Entrenamiento | +6h | ⏳ Tras PPO |
| 4 | Evaluación Comparativa | +30min | ⏳ Post-entrenamientos |
| 5 | Validaciones Finales | +1h | ⏳ Post-comparativa |
| 6 | Reporte Final | +30min | ⏳ Post-validaciones |

**Tiempo Total Estimado:** 6-7 horas (GPU RTX 4060 con CUDA)

---

## 🎓 HIPÓTESIS DE SELECCIÓN

**Si SAC logra:**
- CO₂ < 180 t/año (>67% reducción)
- Autoconsumo solar > 70%
- EV Satisfaction = 100% SIEMPRE
- Convergencia < 5 episodios
- σ reward < 8%

**ENTONCES:**
- SAC es "más apropiado"
- Implementación en Iquitos viable
- Modelo replicable a otras ciudades

---

**Documento Generado:** 28 Enero 2026  
**Versión:** 1.0 - Objetivo Específico Alineado  
**Estado:** Aguardando resultados SAC/PPO/A2C para comparativa

---

## 🔗 Referencias
- [Objetivo General](OBJETIVO_GENERAL_PROYECTO.md)
- [Problemas Identificados](REPORTE_ANALISIS_CARGA_SIN_CONTROL.md)
- [Baseline Calculado](reports/resumen_carga_baseline.json)
