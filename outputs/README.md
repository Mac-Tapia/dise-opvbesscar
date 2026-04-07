# 📄 TESIS PVBESSCAR v7.2

## 🎯 Descripción del Proyecto

**PVBESSCAR** es un sistema de optimización de carga de vehículos eléctricos (EVs) que combina:
- **Energía Solar**: 4,050 kWp (generate 8,292,514 kWh/año)
- **Almacenamiento en Batería (BESS)**: 2,000 kWh / 400 kW (peak shaving)
- **Control Inteligente**: Agente SAC (Soft Actor-Critic) basado en RL

### 📊 Resultados Principales

| Métrica | Valor | Status |
|---------|-------|--------|
| **Reducción CO₂** | 1,303,273 kg/año | ✅ Validado |
| **EVs Cargados** | 3,500 motos/año | ✅ Máximo |
| **Utilización Solar** | 66.6% desplazamiento | ✅ Alto |
| **Infraestructura** | 4,050 kWp + 2,000 kWh + 38 chargers | ✅ Completo |
| **Agente Óptimo** | SAC (off-policy) | ✅ Mejor rendimiento |

---

## 📑 Estructura de la Tesis

### Sección 4.6: Función de Recompensa Multi-Objetivo
- **4.6.4.6**: Componente RCO2 (framework de 3 canales)
  - Canal 1: Reducción importaciones grid (318,516 kg CO₂)
  - Canal 2: Desplazamiento solar (868,514 kg CO₂)
  - Canal 3: BESS peak shaving (116,243 kg CO₂)
- **4.6.4.7**: Resultados de Entrenamiento
  - Comparación SAC vs PPO vs A2C
  - Métricas de convergencia y benchmarks

### Sección 5: Análisis de Resultados y Conclusiones

#### 5.2: Dimensionamiento de Infraestructura
- 5.2.1: Capacidad de Generación Solar (patrones diarios/mensuales)
- 5.2.2: Dimensionamiento de Cargadores EV (19 chargers × 2 sockets)
- 5.2.3: Dimensionamiento del BESS (2,000 kWh / 400 kW)
- 5.2.4: Balance Energético Diario (ciclo solar-BESS)
- 5.2.5: Contribución CO₂ por Infraestructura (3 canales)

#### 5.3: Algoritmo de Control RL
- 5.3.1: Estrategia SAC (arquitectura y parámetros)
- 5.3.2: Función de Recompensa Multi-Objetivo (5 componentes)
- 5.3.3: Resultados Comparativos (tablas agent benchmarks)
- 5.3.4: Mecanismo de Optimización (timing + dispatch)
- 5.3.5: Validación contra Datos Reales (7-día simulation)

#### 5.4: Análisis de Sensibilidad y Consideraciones
- 5.4.1: Sensibilidad a Pesos de Recompensa (5 escenarios)
- 5.4.2: Robustez ante Perturbaciones (6 casos críticos)
- 5.4.3: Escalabilidad (+50% a +100% infraestructura)
- 5.4.4: Consideraciones Operacionales (monitoreo, updates, contingencies)

#### 5.5: Validación de Hipótesis y Conclusiones
- 5.5.1: Validación de Hipótesis (6 hipótesis probadas)
- 5.5.2: Contribución Científica (metodología RL novel)
- 5.5.3: Conclusiones Generales (6 hallazgos clave)
- 5.5.4: Recomendaciones de Implementación (3-phase plan)
- 5.5.5: Síntesis Final (viabilidad y rentabilidad)

---

## 📁 Archivos Incluidos

### Documentos Word
```
outputs/
├── TESIS_PVBESSCAR_COMPLETA_4.6_a_5.5.docx (60 KB)
│   └── Documento maestro: Portada + Secciones 4.6 + Secciones 5.2-5.5 + Gráficos
├── APENDICES_TECNICOS_PVBESSCAR.docx (41 KB)
│   └── 6 apéndices: BESS, SAC, Chargers, Reward, Data, Validation
└── TESIS_SECCIONES_5_2_a_5_5_CON_GRAFICOS.docx (1,323 KB)
    └── Versión alternativa: Solo secciones 5.2-5.5 con gráficos integrados
```

### Gráficos (300 DPI, Formato PNG)
```
outputs/
├── ANALISIS_GRAFICO_PVBESSCAR_v7.2.png (689 KB)
│   └── 6 figuras integradas: Comparación, Sensibilidad, Robustez, Escalabilidad, Pareto, CO₂
├── MATRIZ_SENSIBILIDAD_PESOS.png (168 KB)
│   └── Elasticidad del sistema ante cambios de pesos de recompensa
├── VALIDACION_TEMPORAL_7DIAS.png (596 KB)
│   └── Validación operacional: PV vs Demanda vs Estado BESS
├── ARQUITECTURA_SISTEMA_PVBESSCAR.png (600 KB)
│   └── Diagrama de flujo: Solar → BESS → Chargers → EVs + SAC RL
├── TIMELINE_IMPLEMENTACION_3FASES.png (400 KB)
│   └── Plan: Validación (Q1) → Piloto (Q2-Q3) → Operación (Q4)
└── COMPARATIVA_DESEMPENIO_AGENTES.png (550 KB)
    └── 4 métricas: CO₂, Solar, EVs, Estabilidad
```

### Documentos de Apoyo
```
outputs/
├── DOCUMENTO_METADATOS.txt
│   └── Descripción de contenido y validaciones
└── README.md (este archivo)
    └── Guía de estructura y contenido
```

---

## 🔬 Contenido Técnico Validado

### Datos Reales Utilizados
- **PV Generation**: 8,762 registros horarios (8,292,514 kWh/año)
  - Fuente: `pv_generation_hourly_citylearn_v2.csv`
  - Patrón: 0 kW noche, pico 10-13h (2,886 kW)
  
- **Demanda Mall**: 8,762 registros horarios (12,368,653 kWh/año)
  - Fuente: `demandamallhorakwh.csv`
  - Patrón: Off-peak 0-17h (0.30 S/kWh), Punta 18-22h (0.50 S/kWh)
  
- **Demanda EV**: ~3,500 motos + 39 mototaxis/año
  - Fuente: `chargers_ev_ano_2024_v3.csv`
  - Patrones: Picos diarios 06-09h, 20-23h

### Métricas Verificadas
✅ CO₂ Total SAC: 1,303,273 kg/año
✅ 3-Canal CO₂: 318,516 (Grid) + 868,514 (Solar) + 116,243 (BESS)
✅ EVs SAC: 3,500 motos/año (máximo teórico)
✅ Pesos Recompensa (CO2_DUAL_FOCUS v7.0): 0.35 (CO₂ Directo) + 0.30 (CO₂ Indirecto) + 0.25 (EV) + 0.05 (Solar) + 0.05 (Grid) + 0.00 (Cost)
✅ Infraestructura: 4,050 kWp + 2,000 kWh + 38 chargers (4.4 sockets/charger)

### Configuración del Agente SAC
- **Framework**: Stable-Baselines3 v1.8.0
- **Learning Rate**: 3e-4 (actor), 1e-3 (critic)
- **Batch Size**: 256
- **Replay Buffer**: 1,000,000 transiciones
- **Episode Length**: 8,760 timesteps (1 año)
- **Total Training**: 26,280 timesteps (3 años)
- **GPU**: RTX 4060 recomendado (5-7 horas)
- **CPU**: 20-30 horas sin GPU

---

## 🎯 Plan de Implementación 3-Fases

### FASE 1: VALIDACIÓN Y PILOTO (Q1 2026 - Mes 1-3)
- ✓ Validar datos solar e integración IoT
- ✓ Entrenar SAC en ambiente simulado
- ✓ Desplegar 10 chargers bidireccionales
- **Target KPI**: RMSE < 5% vs predicción

### FASE 2: IMPLEMENTACIÓN PARCIAL (Q2-Q3 2026 - Mes 4-9)
- ✓ Desplegar 25 chargers (66% capacidad)
- ✓ Integrar BESS con 400 kW potencia
- ✓ Ejecutar SAC en tiempo real
- **Target**: 1,100 EVs/mes, CO₂ −20% vs baseline

### FASE 3: OPERACIÓN COMPLETA (Q4 2026 - Mes 10-12)
- ✓ Desplegar 38 chargers (100% capacidad)
- ✓ BESS operación plena (2,000 kWh)
- ✓ SAC optimización continua
- **Target**: 3,500 EVs/año, CO₂ −27.6% vs baseline

---

## 📚 Referencias y Secciones

**DOI de publicaciones relacionadas**:
- Haarnoja et al. (2018): Soft Actor-Critic
- Brockman et al. (2016): OpenAI Gym / Gymnasium
- CityLearn v2: Building Energy Simulation

**Estándares aplicables**:
- IEC 61851: Especificaciones cargadores EV
- IEEE 1547: Interconexión sistemas distribuidos
- ISO 14040: Evaluación del ciclo de vida (LCA CO₂)

---

## 🚀 Cómo Usar Este Repositorio

### Opción 1: Leer Documento Completo
```bash
# Descargar y abrir el documento maestro
# Ubicación: outputs/TESIS_PVBESSCAR_COMPLETA_4.6_a_5.5.docx
# Tamaño: 60 KB (formato Word)
```

### Opción 2: Convertir a PDF
```bash
# Opción A: Microsoft Word
# - Abrir archivo .docx
# - Archivo → Guardar como → Formato PDF

# Opción B: LibreOffice
# libreoffice --headless --convert-to pdf \
#   outputs/TESIS_PVBESSCAR_COMPLETA_4.6_a_5.5.docx \
#   --outdir outputs/

# Opción C: Online
# Visitar https://convertio.co/docx-pdf/
```

### Opción 3: Revisar Gráficos
```bash
# Todas los gráficos incluidos en formato PNG (300 DPI)
# Ubicación: outputs/*.png
# Licencia: Creative Commons (si se publica)
```

---

## ✅ State de Validación

| Componente | Status | Detalles |
|------------|--------|----------|
| CO₂ Framework | ✅ VALIDADO | 3 canales, total 1,303,273 kg ✓ |
| EV Satisfaction | ✅ VALIDADO | 3,500 motos, máximo alcanzado ✓ |
| SAC Agent | ✅ VALIDADO | Óptimo vs PPO/A2C, convergencia ✓ |
| Data Integrity | ✅ VALIDADO | 8,762 registros por CSV ✓ |
| Gráficos | ✅ VALIDADO | 6 figuras integradas, 300 DPI ✓ |
| Apéndices | ✅ VALIDADO | 6 secciones técnicas completas ✓ |
| Portada/Preliminares | ✅ VALIDADO | ToC, resumen ejecutivo ✓ |

---

## 📝 Autor y Atribuciones

**Proyecto**: PVBESSCAR v7.2
**Tema**: Optimización de Carga EV con Energía Solar + BESS + RL
**Ubicación**: Iquitos, Perú (grid aislado)
**Fecha**: Febrero 2026

**Agradecimientos**:
- CityLearn v2 (Building Energy Simulation)
- Stable-Baselines3 (RL Algorithms)
- OpenAI Gymnasium (RL Environments)

---

## 📞 Contacto y Soporte

Para preguntas sobre esta tesis:
1. revisar el documento maestro completo
2. Consultar apéndices técnicos para detalles
3. Revisar gráficos para visualizaciones

---

**Última actualización**: Febrero 22, 2026
**Versión**: 7.2 (Final)
**Estado**: ✅ Listo para publicación
