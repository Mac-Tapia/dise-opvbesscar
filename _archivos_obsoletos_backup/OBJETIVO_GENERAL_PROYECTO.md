# OBJETIVO GENERAL DEL PROYECTO

## 🎯 INFRAESTRUCTURA DE CARGA INTELIGENTE DE MOTOS Y MOTOTAXIS ELÉCTRICAS PARA REDUCIR LAS EMISIONES DE DIÓXIDO DE CARBONO EN LA CIUDAD DE IQUITOS

---

## 📍 Ubicación: Iquitos, Perú
- **Contexto:** Ciudad aislada, generación térmica (0.45 kg CO₂/kWh)
- **Población:** ~400,000 habitantes
- **Movilidad Dominante:** Motos y mototaxis eléctricos

---

## 🚗 ALCANCE DEL PROYECTO

### OE2 (Dimensionamiento de Infraestructura)
- **PV:** 4,050 kWp (energía limpia disponible)
- **BESS:** 4,520 kWh / 2,712 kW (almacenamiento de día)
- **Chargers:** 128 (112 motos + 16 taxis)
- **Capacidad:** 272 kW potencia nominal

### OE3 (Control Inteligente = Agentes RL)
- **SAC, PPO, A2C:** Aprendimiento automático para optimizar carga
- **Objetivo:** Maximizar autoconsumo solar = minimizar grid térmico = reducir CO₂

---

## ❌ PROBLEMA ACTUAL (SIN CONTROL)

**Baseline Calculado:**
- **Carga total anual:** 1,186,980 kWh/año
  - Motos: 977,835 kWh (82.4%)
  - Taxis: 209,145 kWh (17.6%)
- **Autoconsumo solar:** ~30% (70% desperdiciado)
- **Importación grid térmico:** ~70% (1,187 MWh)
- **Emisiones CO₂:** **537 t CO₂/año** ← ESTO ES LO QUE DEBE REDUCIRSE

---

## ✅ SOLUCIÓN: AGENTES RL INTELIGENTES

Los agentes SAC/PPO/A2C aprenderán a:

### 1️⃣ Desplazar motos a horas solares
- Cargar motos en 09:00-15:00 (cuando hay solar)
- Mantener taxis críticos (últimas 6 horas)
- Ganancia: 50% flexibilidad en motos

### 2️⃣ Llenar BESS en mediodía
- Acumular 2,000 kWh en 12:00-15:00 desde solar
- Servir picos (15:00-22:00) desde BESS
- Ganancia: 0% CO₂ en picos nocturnos

### 3️⃣ Maximizar autoconsumo solar
- Sincronizar carga con generación solar
- Evitar imports termoeléctricos innecesarios
- Ganancia: 60-80% autoconsumo (vs 30%)

### 4️⃣ Ciclo solar-coherente
- Mañana: Cargar motos desde solar
- Mediodía: Cargar BESS desde solar excedente
- Tarde: Mezcla solar + BESS
- Noche: Solo BESS (energía verde almacenada)
- Ganancia: Ciclo diario 100% renovable

---

## 🎯 MÉTRICA PRINCIPAL: REDUCCIÓN DE CO₂

### Baseline (Sin Control)
**537 t CO₂/año**

### Objetivo RL (Con Agentes Inteligentes)
**107-215 t CO₂/año** (60-80% reducción)

### Cómo se logra
```
537 t CO₂/año × (100% - 60-80% autoconsumo solar)
= 537 × (20-40% imports termoeléctricos)
= 107-215 t CO₂/año
```

---

## 📊 INDICADORES DE ÉXITO

| KPI | Baseline | Meta RL | Estado |
|-----|----------|---------|--------|
| **CO₂ t/año** | 537 | 107-215 | 🟡 SAC Entrenando |
| **Autoconsumo Solar** | ~30% | 60-80% | 🟡 SAC Entrenando |
| **Grid Import MWh** | 1,187 | 237-475 | 🟡 SAC Entrenando |
| **BESS Utilización** | ~20% | 70-90% | 🟡 SAC Entrenando |
| **EV Satisfaction** | 100% | 100% | 🟡 SAC Entrenando |

---

## 🚀 ESTADO DEL PROYECTO

### ✅ COMPLETADO
- ✅ OE2 Infraestructura dimensionada
- ✅ Baseline calculado: 537 t CO₂/año
- ✅ Problemas identificados en reporte
- ✅ Estrategia de corrección definida

### 🟡 EN PROGRESO
- 🟡 SAC Entrenando (paso 2300/26280 = 8.8%)
  - Episode: 1/3 de 10
  - Reward avg: 0.59 (estable)
  - GPU: RTX 4060 CUDA

### ⏳ PENDIENTE
- ⏳ PPO Entrenamiento (100K timesteps)
- ⏳ A2C Entrenamiento (100K timesteps)
- ⏳ Comparativa final: SAC vs PPO vs A2C
- ⏳ Documento de resultados finales

---

## 📁 ARCHIVOS CLAVE

**Reporte Técnico:**
- [REPORTE_ANALISIS_CARGA_SIN_CONTROL.md](REPORTE_ANALISIS_CARGA_SIN_CONTROL.md) - Problemas + estrategia RL

**Datos Baseline:**
- `reports/demanda_horaria_motos_taxis.csv` - Demanda por tipo
- `reports/resumen_carga_baseline.json` - Métricas agregadas

**Entrenamiento:**
- `analyses/oe3/training/checkpoints/sac/` - SAC en progreso
- `analyses/oe3/training/checkpoints/ppo/` - PPO pendiente
- `analyses/oe3/training/checkpoints/a2c/` - A2C pendiente

---

## 🎓 HIPÓTESIS DEL PROYECTO

**Si los agentes RL aprenden a:**
1. Desplazar carga flexible (motos) a horas solares
2. Garantizar disponibilidad crítica (taxis)
3. Sincronizar consumo con generación

**ENTONCES:**
- Autoconsumo solar subirá de 30% a 60-80%
- CO₂ bajará de 537 t/año a 107-215 t/año
- Sistema será resiliente ante crecimiento de flota EV

---

## 📌 CONCLUSIÓN

El proyecto busca demostrar que **la inteligencia artificial (RL)** puede optimizar infraestructuras de energía renovable en ciudades aisladas para:
- ✅ Reducir dependencia de generación térmica (0.45 kg CO₂/kWh)
- ✅ Maximizar autoconsumo solar sin sacrificar servicio
- ✅ Proporcionar modelo replicable para otras ciudades similares (Iquitos → Perú → Latinoamérica)

**Métrica de Éxito Global:** Reducir de **537 t CO₂/año → 107-215 t CO₂/año** (-60% a -80%)

---

**Documento Generado:** 28 Enero 2026  
**Versión:** 1.0 - Objetivo General Alineado con OE2 + OE3  
**Estado:** Proyecto en ejecución, SAC en entrenamiento
