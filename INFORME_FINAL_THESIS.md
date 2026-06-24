# INFORME FINAL DE TESIS

## Sistema de optimizacion de carga EV con Solar PV + BESS mediante Reinforcement Learning

**Proyecto:** `pvbesscar`  
**Repositorio:** `/workspace`  
**Estado del entregable:** consolidado a partir del codigo y la documentacion disponible en el repositorio  
**Fecha de elaboracion:** 2026-06-24

---

## Tabla de contenido

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Planteamiento del problema](#2-planteamiento-del-problema)
3. [Objetivos de la tesis](#3-objetivos-de-la-tesis)
4. [Alcance del trabajo](#4-alcance-del-trabajo)
5. [Arquitectura tecnica del sistema](#5-arquitectura-tecnica-del-sistema)
6. [Metodologia](#6-metodologia)
7. [Resultados consolidados](#7-resultados-consolidados)
8. [Aportes principales de la tesis](#8-aportes-principales-de-la-tesis)
9. [Limitaciones y observaciones de consistencia](#9-limitaciones-y-observaciones-de-consistencia)
10. [Reproducibilidad y evidencias en el repositorio](#10-reproducibilidad-y-evidencias-en-el-repositorio)
11. [Conclusiones](#11-conclusiones)
12. [Referencias internas del repositorio](#12-referencias-internas-del-repositorio)

---

## 1. Resumen ejecutivo

Esta tesis presenta un sistema de optimizacion de carga para vehiculos electricos en Iquitos, Peru, integrando tres capas tecnicas:

1. **Infraestructura energetica modelada** con generacion solar fotovoltaica y un sistema BESS.
2. **Demanda de movilidad electrica** para motos y mototaxis, modelada a nivel horario.
3. **Control inteligente** mediante agentes de Reinforcement Learning (SAC, PPO y A2C).

El objetivo central del proyecto es minimizar el impacto ambiental de la electrificacion del transporte ligero en una red aislada y predominantemente termica, priorizando el uso de energia solar, reduciendo importaciones de red y manteniendo la satisfaccion de carga de los vehiculos.

De acuerdo con la documentacion final del repositorio, el escenario consolidado utiliza:

- **Solar PV:** 4,050 kWp aproximadamente
- **BESS:** 1,700 kWh maximos
- **Infraestructura EV:** 38 tomas (19 cargadores de 2 tomas)
- **Contexto geografico:** Iquitos, Peru
- **Agente recomendado en la documentacion final:** **SAC**

El repositorio tambien conserva resultados de impacto directo por sustitucion de combustible y resultados de optimizacion del sistema completo. Este informe deja ambas familias de metricas separadas para evitar ambiguedades.

---

## 2. Planteamiento del problema

El trabajo parte de una tension tecnica y ambiental concreta: electrificar motos y mototaxis en una ciudad aislada como Iquitos puede reducir emisiones por sustitucion de gasolina, pero el beneficio real depende de como se produzca y gestione la electricidad que alimenta esa nueva demanda.

En este contexto aparecen tres retos:

1. **El reto energetico:** coordinar generacion fotovoltaica, almacenamiento y demanda EV en resolucion horaria.
2. **El reto operativo:** cargar vehiculos dentro de restricciones fisicas, temporales y de potencia.
3. **El reto ambiental:** diferenciar entre la reduccion directa de CO2 por cambio de combustible y el balance neto de emisiones cuando la red electrica aun depende de diesel.

La tesis aborda estos retos combinando modelado de infraestructura, construccion de datasets, funciones de recompensa multiobjetivo y entrenamiento de agentes RL.

---

## 3. Objetivos de la tesis

### Objetivo general

Desarrollar y documentar un sistema de control inteligente para la carga de motos y mototaxis electricos en Iquitos, integrando solar PV, BESS y Reinforcement Learning, con enfasis en la reduccion de CO2 y el aprovechamiento de energia renovable.

### Objetivos especificos inferidos desde el repositorio

1. Modelar la generacion solar horaria para el caso Iquitos.
2. Modelar la demanda EV y la infraestructura de carga realista.
3. Incorporar almacenamiento BESS al balance energetico.
4. Construir un entorno util para entrenamiento RL con recompensas multiobjetivo.
5. Comparar distintos agentes RL bajo metricas de CO2, autoconsumo solar, satisfaccion de carga y estabilidad operativa.
6. Diferenciar de forma explicita el beneficio directo por sustitucion de combustible del beneficio neto del sistema completo.

---

## 4. Alcance del trabajo

El repositorio evidencia que la tesis cubre, como minimo, los siguientes frentes:

- **Dimensionamiento y simulacion solar** (`src/dimensionamiento/oe2/generacionsolar/...`)
- **Modelado de cargadores EV** (`src/dimensionamiento/oe2/disenocargadoresev/chargers.py`)
- **Modelado de BESS** (`src/dimensionamiento/oe2/disenobess/bess.py`)
- **Integracion y construccion de datasets tipo CityLearn** (`src/dataset_builder_citylearn/...`)
- **Reward multiobjetivo y wrapper RL** (`src/dataset_builder_citylearn/rewards.py`)
- **Implementaciones de agentes RL** (`src/agents/sac.py`, `src/agents/ppo_sb3.py`, `src/agents/a2c_sb3.py`)
- **Scripts de entrenamiento** (`scripts/train/train_sac_multiobjetivo.py`, `scripts/train/train_ppo_multiobjetivo.py`, `scripts/train/train_a2c_multiobjetivo.py`)
- **Analisis comparativo posterior** (`scripts/analysis/compare_agents_sac_ppo_a2c.py`)

No se observa, en el estado actual del arbol, una version final unica del manuscrito academico completo; por ello este documento funciona como un **informe final consolidado de thesis** a partir de la evidencia tecnica presente.

---

## 5. Arquitectura tecnica del sistema

### 5.1 Componentes principales

| Capa | Evidencia en repositorio | Funcion |
|---|---|---|
| Solar PV | `src/dimensionamiento/oe2/generacionsolar/run/main.py` | Simulacion y generacion de series solares horarias |
| Cargadores EV | `src/dimensionamiento/oe2/disenocargadoresev/chargers.py` | Modelado de sockets, energia y columnas de CO2 |
| BESS | `src/dimensionamiento/oe2/disenobess/bess.py` | Gestion del almacenamiento electrico |
| Balance energetico | `src/dimensionamiento/oe2/balance_energetico/balance.py` | Coordinacion energetica entre fuentes y consumos |
| Dataset builder | `src/dataset_builder_citylearn/main_build_citylearn.py` | Preparacion e integracion de datos para entrenamiento |
| Reward wrapper | `src/dataset_builder_citylearn/rewards.py` | Recompensa multiobjetivo y adaptacion del entorno |
| Agentes RL | `src/agents/sac.py`, `src/agents/ppo_sb3.py`, `src/agents/a2c_sb3.py` | Entrenamiento y evaluacion de controladores |

### 5.2 Evidencia de entorno multiobjetivo

El archivo `src/dataset_builder_citylearn/rewards.py` define `CityLearnMultiObjectiveWrapper`, que encapsula el entorno y reemplaza la recompensa por una formulacion multiobjetivo. En la misma unidad de codigo se observan componentes de recompensa para:

- CO2
- costo
- uso solar
- carga EV
- estabilidad de red

Adicionalmente, el wrapper recopila metricas de red, solar, EV y estado de BESS durante el `step`, lo que confirma que la tesis no solo entrena agentes sino que integra variables fisicas y operativas en la recompensa.

### 5.3 Evidencia de entrenamiento RL

El archivo `src/agents/sac.py` muestra una implementacion extensa y adaptada del agente SAC, incluyendo:

- deteccion automatica de dispositivo (`cuda`, `mps`, `cpu`)
- configuracion de hiperparametros especificos
- estabilizacion numerica
- clipping de gradientes
- manejo de cobertura anual de datos

El arbol `scripts/train/` contiene los tres scripts de entrenamiento multiobjetivo disponibles en el estado actual del repositorio:

- `train_sac_multiobjetivo.py`
- `train_ppo_multiobjetivo.py`
- `train_a2c_multiobjetivo.py`

---

## 6. Metodologia

### 6.1 Modelado de la generacion solar

El reporte `data/oe2/Generacionsolar/solar_technical_report.md` documenta un caso de Iquitos 2024 basado en PVGIS TMY y modelos de `pvlib`, con una produccion anual AC reportada de **8.293 GWh**. El mismo reporte indica:

- capacidad DC nominal: **4,162.00 kWp**
- capacidad AC nominal: **3,201.00 kW**
- factor de capacidad: **29.6%**
- horas equivalentes: **2,591 h/ano**

### 6.2 Modelado de la demanda EV

La documentacion consolidada en `README.md` y los reportes asociados describen una infraestructura final de:

- **19 cargadores**
- **38 tomas**
- **30 sockets para motos**
- **8 sockets para mototaxis**
- potencia nominal de **7.4 kW por toma**

El archivo `src/dimensionamiento/oe2/disenocargadoresev/chargers.py` es la pieza central para este subsistema y, segun la documentacion, tambien es donde se construyen las columnas de CO2 a nivel horario.

### 6.3 Modelado del BESS

La documentacion del repositorio reporta un BESS con:

- capacidad maxima: **1,700 kWh**
- potencia maxima: **342 kW**

La implementacion principal asociada se encuentra en `src/dimensionamiento/oe2/disenobess/bess.py`.

### 6.4 Construccion del entorno de aprendizaje

El pipeline de datos y entorno se apoya en `src/dataset_builder_citylearn/`, donde se observa:

- integracion de datasets
- enriquecimiento de informacion de cargadores
- construccion de metadatos
- wrapper de recompensa multiobjetivo

Esto sugiere una metodologia donde el entorno RL no es sintetico, sino construido sobre series horarias y componentes fisicos previamente modelados.

### 6.5 Evaluacion

El repositorio conserva evidencia de evaluacion y comparacion multiagente, principalmente en:

- `README.md`
- `REPORTE_FINAL_V52_LIMPIEZA.md`
- `scripts/analysis/compare_agents_sac_ppo_a2c.py`

La comparacion incluye, al menos, las siguientes dimensiones:

- reduccion de CO2
- autoconsumo solar
- satisfaccion de carga EV
- estabilidad
- costo
- uso del BESS

---

## 7. Resultados consolidados

### 7.1 Resultados energeticos de infraestructura

Del material tecnico disponible pueden consolidarse los siguientes valores:

| Metrica | Valor reportado |
|---|---|
| Produccion anual solar AC | 8.293 GWh |
| Capacidad solar DC | 4,162.00 kWp |
| Capacidad solar AC | 3,201.00 kW |
| Infraestructura EV final | 38 tomas |
| Demanda EV anual | 565,875 kWh/ano |
| BESS maximo | 1,700 kWh |

Estos resultados describen la base fisica sobre la que se construye el problema de control.

### 7.2 Resultados de CO2 por sustitucion directa de combustible

El documento `ESPECIFICACION_CO2_REDUCCION_DIRECTA_vs_NETO.md` deja claramente diferenciadas las metricas de CO2 a nivel de dataset EV:

| Metrica | Valor anual |
|---|---|
| Reduccion directa por cambio de combustible | **456,561 kg CO2** |
| Emisiones del grid asociadas a la carga | **255,832 kg CO2** |
| Beneficio neto | **200,729 kg CO2** |

Interpretacion:

- **Reduccion directa** responde a la pregunta: "Cuanta gasolina deja de quemarse por electrificar motos y mototaxis?"
- **CO2 neto** responde a la pregunta: "Cual es el beneficio ambiental real despues de considerar la electricidad de una red diesel?"

Esta distincion es esencial para una tesis porque evita interpretar como equivalentes dos indicadores que responden a preguntas distintas.

### 7.3 Resultados de optimizacion con RL

La documentacion final del repositorio, especialmente `README.md`, reporta la siguiente comparacion multiobjetivo:

| Agente | Score multiobjetivo | Reduccion CO2 reportada |
|---|---:|---:|
| SAC | **8.2/10** | **65.7%** |
| PPO | 5.9/10 | 50.9% |
| A2C | 3.1/10 | 50.1% |

En ese mismo cuerpo documental, **SAC** se presenta como el agente recomendado y ganador del analisis multiobjetivo.

### 7.4 Lectura correcta de las metricas

El repositorio contiene al menos **dos familias de metricas de CO2**:

1. **Metricas de sustitucion directa y CO2 neto del dataset EV**
   - 456,561 kg CO2 de reduccion directa
   - 200,729 kg CO2 de beneficio neto

2. **Metricas de evaluacion del sistema RL completo**
   - hasta 65.7% de reduccion reportada para SAC
   - valores en millones de kg en la documentacion final

La recomendacion metodologica para la tesis es **no mezclar ambas familias en una misma tabla sin explicar su escala y su frontera de sistema**. La primera familia parece describir el impacto directo de la electrificacion de la demanda EV del dataset; la segunda resume escenarios integrados de operacion del sistema y comparacion contra un baseline de control.

---

## 8. Aportes principales de la tesis

Desde la evidencia disponible, los aportes mas fuertes del trabajo son los siguientes:

1. **Integracion de movilidad electrica con gestion energetica distribuida** en un caso de red aislada.
2. **Modelado horario de un ecosistema completo**: solar, BESS, demanda EV y red.
3. **Formalizacion de una recompensa multiobjetivo** para un problema energetico realista.
4. **Comparacion reproducible de tres agentes RL** en un mismo entorno de evaluacion.
5. **Clarificacion conceptual del CO2** mediante separacion entre reduccion directa y beneficio neto.
6. **Base tecnica reutilizable** para nuevas iteraciones, pilotos de produccion o extension a otros contextos.

---

## 9. Limitaciones y observaciones de consistencia

Durante la consolidacion del informe se identificaron varios puntos importantes:

### 9.1 Deriva documental

Algunos archivos de documentacion mencionan scripts que no existen en el estado actual del arbol, por ejemplo:

- `ejecutar.py`
- `demo_ejecucion.py`
- `compare_agents_complete.py`

Sin embargo, si existen scripts actuales equivalentes o cercanos en:

- `scripts/train/`
- `scripts/analysis/compare_agents_sac_ppo_a2c.py`

Esto indica que parte de la documentacion fue escrita para estados anteriores del repositorio y debe interpretarse con cautela.

### 9.2 Recomendaciones de agente no totalmente uniformes

La documentacion final principal (`README.md`) recomienda **SAC**, mientras que `QUICK_START_EJECUTAR.md` conserva una recomendacion centrada en **A2C**. Para un informe final de tesis, la postura mas consistente con el estado general del repositorio es tratar **SAC** como la recomendacion vigente y citar la discrepancia como evidencia de deuda documental.

### 9.3 Formato de consolidacion

El estado actual del repositorio no muestra un manuscrito academico final unico. Por ello, este entregable se construyo como un **informe markdown estructurado**, con trazabilidad a codigo, reportes tecnicos y scripts existentes.

---

## 10. Reproducibilidad y evidencias en el repositorio

Los siguientes artefactos estan presentes y sirven como evidencia directa para reconstruir o verificar partes del trabajo:

### Validacion de datos y CO2

- `VALIDACION_DATASET_COMPLETO_v2026-02-16.py`
- `VERIFICACION_CO2_TERMINOLOGIA.py`
- `ESPECIFICACION_CO2_REDUCCION_DIRECTA_vs_NETO.md`

### Modelado de infraestructura

- `src/dimensionamiento/oe2/generacionsolar/run/main.py`
- `src/dimensionamiento/oe2/disenocargadoresev/chargers.py`
- `src/dimensionamiento/oe2/disenobess/bess.py`
- `src/dimensionamiento/oe2/balance_energetico/balance.py`

### Entrenamiento y analisis RL

- `scripts/train/train_sac_multiobjetivo.py`
- `scripts/train/train_ppo_multiobjetivo.py`
- `scripts/train/train_a2c_multiobjetivo.py`
- `scripts/analysis/compare_agents_sac_ppo_a2c.py`
- `src/dataset_builder_citylearn/rewards.py`
- `src/agents/sac.py`
- `src/agents/ppo_sb3.py`
- `src/agents/a2c_sb3.py`

### Reportes clave usados para este informe

- `README.md`
- `REPORTE_FINAL_V52_LIMPIEZA.md`
- `ENTREGA_FINAL_CO2_REDUCCION_DIRECTA.md`
- `data/oe2/Generacionsolar/solar_technical_report.md`

---

## 11. Conclusiones

1. El proyecto `pvbesscar` representa una base solida para una tesis aplicada en gestion energetica inteligente y movilidad electrica.
2. La evidencia del repositorio confirma una arquitectura integradora que combina modelado fisico, ingenieria de datos y aprendizaje por refuerzo.
3. La contribucion conceptual mas importante para el cierre del trabajo es distinguir con claridad:
   - la **reduccion directa de CO2** por sustitucion de combustible, y
   - el **beneficio neto** del sistema cuando se considera la red electrica.
4. La evidencia documental final disponible favorece a **SAC** como mejor agente en el analisis multiobjetivo consolidado.
5. Para una defensa o entrega academica, conviene anexar este informe junto con una normalizacion final de metricas y una depuracion de guias desactualizadas para evitar contradicciones entre documentos.

---

## 12. Referencias internas del repositorio

- `README.md`
- `QUICK_START_EJECUTAR.md`
- `REPORTE_FINAL_V52_LIMPIEZA.md`
- `ENTREGA_FINAL_CO2_REDUCCION_DIRECTA.md`
- `ESPECIFICACION_CO2_REDUCCION_DIRECTA_vs_NETO.md`
- `data/oe2/Generacionsolar/solar_technical_report.md`
- `src/dataset_builder_citylearn/rewards.py`
- `src/agents/sac.py`
- `src/agents/ppo_sb3.py`
- `src/agents/a2c_sb3.py`
- `scripts/train/train_sac_multiobjetivo.py`
- `scripts/train/train_ppo_multiobjetivo.py`
- `scripts/train/train_a2c_multiobjetivo.py`
- `scripts/analysis/compare_agents_sac_ppo_a2c.py`

---

**Resultado del trabajo solicitado:** informe final de thesis consolidado y listo para usar como base de entrega, revision academica o conversion posterior a documento formal.
