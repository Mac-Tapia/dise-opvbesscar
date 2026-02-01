# 📚 Índice Consolidado de Documentación - pvbesscar (OE3)

**Fecha de Actualización:** 2026-02-01  
**Estado:** ✅ AUDITADO Y LIMPIADO  
**Documentos Activos:** 18 archivos  
**Archivos Históricos:** 60+ en `docs/archive/`

---

## 🎯 Inicio Rápido

- **[GUIA_RAPIDA.md](GUIA_RAPIDA.md)** - Start here para entrenar agentes (SAC, PPO, A2C)
- **[COMIENZA_AQUI_TIER2_FINAL.md](COMIENZA_AQUI_TIER2_FINAL.md)** - Setup y primeros pasos con TIER2

---

## 🏗️ Arquitectura & Diseño

- **[ARQUITECTURA_CONTROL_AGENTES.md](ARQUITECTURA_CONTROL_AGENTES.md)** - Cómo RL agents controlan 128 chargers
- **[ARQUITECTURA_DESPACHO_OPERACIONAL.md](ARQUITECTURA_DESPACHO_OPERACIONAL.md)** - Sistema automático de despacho de energía (PV → EV/BESS/Grid)
- **[DIAGRAMAS_VISUALIZACION.md](DIAGRAMAS_VISUALIZACION.md)** - Diagramas de arquitectura y flujos de datos

---

## 🤖 Agentes RL & Entrenamiento

### Resultados Comparativos
- **[COMPARATIVA_AGENTES_FINAL_TIER2.md](COMPARATIVA_AGENTES_FINAL_TIER2.md)** - SAC vs PPO vs A2C (CO₂, solar, convergencia)
- **[INFORME_UNICO_ENTRENAMIENTO_TIER2.md](INFORME_UNICO_ENTRENAMIENTO_TIER2.md)** - Informe consolidado de entrenamientos

### Configuración & Justificación
- **[HYPERPARAMETERS_JUSTIFICATION.md](HYPERPARAMETERS_JUSTIFICATION.md)** - Justificación técnica de hiperparámetros (learning rate, batch size, etc.)
- **[IMPACTO_OPTIMIZACIONES_EXPLORACION_APRENDIZAJE.md](IMPACTO_OPTIMIZACIONES_EXPLORACION_APRENDIZAJE.md)** - Análisis de impacto de optimizaciones

---

## 📊 Datos & Datasets

- **[DATASETS_ANUALES_128_CHARGERS.md](DATASETS_ANUALES_128_CHARGERS.md)** - Estructura de datasets anuales (8,760 timesteps)
- **[CONSTRUCCION_128_CHARGERS_FINAL.md](CONSTRUCCION_128_CHARGERS_FINAL.md)** - Proceso de construcción de 128 chargers en CityLearn

---

## 💾 Control & Despacho

- **[INDICE_DESPACHO.md](INDICE_DESPACHO.md)** - Referencia completa del sistema de despacho operacional
- **[SINCRONIZACION_EMISIONES_CO2.md](SINCRONIZACION_EMISIONES_CO2.md)** - Tracking de emisiones CO₂ y validación de métricas

---

## 🔧 Operacional

- **[DOCKER_SETUP_GUIDE.md](DOCKER_SETUP_GUIDE.md)** - Configuración y uso de Docker para entrenamientos
- **[GUIA_USO_GRAFICAS_REGENERADAS.md](GUIA_USO_GRAFICAS_REGENERADAS.md)** - Cómo generar y interpretar gráficas de entrenamiento

---

## 📈 Planes & Próximos Pasos

- **[PROXIMOSPASOS_OPCIONES_CONTINUACION.md](PROXIMOSPASOS_OPCIONES_CONTINUACION.md)** - Opciones para continuar proyecto (mejoras, investigación)
- **[PPO_A2C_TIER2_MASTER_PLAN.md](PPO_A2C_TIER2_MASTER_PLAN.md)** - Plan maestro para entrenamientos PPO y A2C

---

## 📖 Verificación & Auditoría

- **[VERIFICACION_AGENTES_LISTOS_ENTRENAMIENTO.md](VERIFICACION_AGENTES_LISTOS_ENTRENAMIENTO.md)** - Checklist para verificar que agentes están listos
- **[VERIFICACION_Y_MEJORAS_AGENTS_FOLDER_FINAL.md](VERIFICACION_Y_MEJORAS_AGENTS_FOLDER_FINAL.md)** - Validación final de estructura de agents/

---

## 📝 Documentación General

- **[README_GUIA.md](README_GUIA.md)** - Guía general y contextual del proyecto
- **[index.md](index.md)** - Index original de documentación
- **[LIMPIEZA_MEMORIA_RESUMEN_EJECUTIVO.md](LIMPIEZA_MEMORIA_RESUMEN_EJECUTIVO.md)** - Resumen de limpieza de memoria realizada (2026-02-01)

---

## 📁 Directorios

- **`sac_tier2/`** - Documentación específica de SAC (Tier 2 detallado)
- **`archive/`** - 60+ documentos históricos y desactualizados (archivados para referencia)
- **`images/`** - Imágenes, diagramas y visualizaciones

---

## 🗂️ Documentos Archivados

Los siguientes documentos fueron archivados por estar desactualizados, ser duplicados o fuera de scope:

**Desactualizados (enero 2026):**
- ACTUALIZACION_DOCUMENTACION_2026_01_24.md
- DATASETS_OE3_RESUMEN_2026_01_24.md

**Obsoletos/Fuera de Scope:**
- KUBERNETES_MONGODB_GUIDE.md, KUBERNETES_MONGODB_STATUS.md (K8s nunca usado)
- FASTAPI_RUNNING_STATUS.md (FastAPI nunca fue producción)
- DASHBOARD_PRO_DOCUMENTACION.md (dashboard no fue requisito)
- MODO_3_OPERACION_30MIN.md (OE2 antiguo)

**Subdirectorios Archivados:**
- `thesis/` - Contenido académico no relacionado
- `historico/` - Documentación histórica
- `reportes/`, `verificacion/`, `actualizaciones/` - Reportes/auditorías antiguas

Para acceder a documentación histórica: ver `docs/archive/`

---

## 🎯 Flujo de Trabajo Recomendado

1. **Comenzar:** [GUIA_RAPIDA.md](GUIA_RAPIDA.md)
2. **Entender Arquitectura:** [ARQUITECTURA_CONTROL_AGENTES.md](ARQUITECTURA_CONTROL_AGENTES.md) + [ARQUITECTURA_DESPACHO_OPERACIONAL.md](ARQUITECTURA_DESPACHO_OPERACIONAL.md)
3. **Entrenamiento:** [COMIENZA_AQUI_TIER2_FINAL.md](COMIENZA_AQUI_TIER2_FINAL.md)
4. **Datos & Datasets:** [DATASETS_ANUALES_128_CHARGERS.md](DATASETS_ANUALES_128_CHARGERS.md)
5. **Configuración Agentes:** [HYPERPARAMETERS_JUSTIFICATION.md](HYPERPARAMETERS_JUSTIFICATION.md)
6. **Resultados:** [COMPARATIVA_AGENTES_FINAL_TIER2.md](COMPARATIVA_AGENTES_FINAL_TIER2.md)
7. **Próximos Pasos:** [PROXIMOSPASOS_OPCIONES_CONTINUACION.md](PROXIMOSPASOS_OPCIONES_CONTINUACION.md)

---

## 📊 Estadísticas Finales

**Auditoría de Limpieza (2026-02-01):**
- ✅ Documentos desactualizados archivados: 19
- ✅ Subdirectorios de bajo valor archivados: 5
- ✅ Documentos duplicados consolidados: 6
- ✅ Documentos activos mantenidos: 18
- ✅ Archivos históricos preservados en: `docs/archive/`
- ✅ Total archivos en archive/: 60+

**Resultado:**
- 📊 Reducción: 47 archivos → 18 activos (60% consolidación)
- 🎯 Enfoque: 100% alineado con OE3 (RL agents, training, datasets, rewards)
- 📚 Claridad: Índice único consolidado para fácil navegación

---

**Última Actualización:** 2026-02-01  
**Responsable:** AI Copilot - Auditoría Automática de Documentación
