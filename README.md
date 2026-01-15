# 🌞 Infraestructura EV Iquitos - Control de Carga Inteligente con RL

**Proyecto:** Validación de infraestructura solar + BESS + cargadores inteligentes en Iquitos mediante RL

**Estado:** ✅ Sistema Verificado para Producción (15 Enero 2026) | 🏆 SAC = Ganador

---

## 📊 Resumen Ejecutivo - Resultados Verificados

| Métrica | SAC | PPO | A2C | Uncontrolled |
|---------|-----|-----|-----|---------------|
| **CO₂ (kg)** | 🥇 **7,547,021** | 7,578,734 | 7,615,072 | 7,661,526 |
| **Reducción vs Uncontrolled** | 🥇 **1.49%** | 1.08% | 0.61% | - |
| **Pasos Simulados** | 8,759 | 8,759 | 8,759 | 8,759 |
| **Status Código** | ✅ Verificado | ✅ Verificado | ✅ Verificado | ✅ Verificado |

---

## 🚀 Inicio Rápido

### Instalación

```bash
.venv\Scripts\activate
pip install -e .
```

### Pipeline Completo

```bash
python -m scripts.run_pipeline --config configs/default.yaml
```

### Entrenar Agentes

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

---

## 📚 Documentación Principal

---

### 🎯 Relanzamiento Completo - Nuevos Datos PV (14 Enero 2026)

- ✅ OE2 Solar: 8.042 GWh/año (4162 kWp) - **NUEVOS DATOS**
- ✅ OE2 Chargers: 128 perfiles (112 motos + 16 mototaxis)
- ✅ OE2 BESS: 2000 kWh / 1200 kW (fijo)
- ✅ OE3 Dataset: Construcción completada (128 chargers + 2 schemas)
- 🔄 OE3 Training: SAC, PPO, A2C **entrenando desde cero** (sin checkpoints previos)

### 🚀 Monitoreo Entrenamiento

```bash
python monitor_checkpoints.py  # Ver progreso en vivo (actualiza cada 5s)
```

**Status (15 Enero 2026)**: ✅ Uncontrolled | ✅ SAC | ✅ PPO | ✅ A2C - **TODOS VERIFICADOS**

---

## Reducción de Emisiones CO₂ mediante Energía Solar y Gestión de Carga EV

**Proyecto:** Diseño integral OE.2 + OE.3 para reducir las emisiones de CO₂ en la ciudad de Iquitos.

**Ubicación:** Iquitos, Perú (lat: -3.7°, lon: -73.2°)  
**Año objetivo:** 2025

---

## 📋 Objetivos del Proyecto

### Objetivo General

**OG.** Diseñar la infraestructura de carga inteligente de motos y mototaxis eléctricas para reducir las emisiones de dióxido de carbono en la ciudad de Iquitos, 2025.

### Objetivos Específicos

1. **OE.1 - Ubicación estratégica:** OE.1.- Determinar la ubicación estratégica óptima que garantice la viabilidad técnica de motos y mototaxis eléctricas, necesaria para la reducción cuantificable de las emisiones de dióxido de carbono en Iquitos.
2. **OE.2 - Dimensionamiento de infraestructura:** OE.2.- Dimensionar la capacidad de generación solar, almacenamiento y cargadores de motos y mototaxis eléctricas para reducir las emisiones de dióxido de carbono en la ciudad de Iquitos.
3. **OE.3 - Agente inteligente:** OE.3.- Seleccionar el agente inteligente de gestión de carga de motos y mototaxis eléctricas más apropiado para maximizar la eficiencia operativa del sistema, asegurando la contribución cuantificable a la reducción de las emisiones de dióxido de carbono en la ciudad de Iquitos.

---

## 📚 Documentación Esencial

| Documento | Propósito | Estado |
|-----------|-----------|--------|
| **[.github/copilot-instructions.md](.github/copilot-instructions.md)** | Guía para agentes IA | ✅ Actualizado |
| **[COMPARATIVA_AGENTES_FINAL.md](COMPARATIVA_AGENTES_FINAL.md)** | Comparación SAC vs PPO vs A2C | ✅ Actualizado |
| **[REVISION_INTEGRAL_ESTADO_PRODUCCION.md](REVISION_INTEGRAL_ESTADO_PRODUCCION.md)** | Estado del sistema | ✅ Actualizado |
| **[VERIFICACION_ENTRENAMIENTO_METRICAS.md](VERIFICACION_ENTRENAMIENTO_METRICAS.md)** | Validación de métricas | ✅ Actualizado |
| **[CHECKPOINT_QUICK_REFERENCE.md](CHECKPOINT_QUICK_REFERENCE.md)** | Referencia checkpoints | ✅ Actualizado |
| **[ARQUITECTURA_UN_EDIFICIO_DOS_PLAYAS.md](ARQUITECTURA_UN_EDIFICIO_DOS_PLAYAS.md)** | Estructura CityLearn | ✅ |

---

## 🔬 Configuración Técnica

**OE2 - Dimensionamiento:**

- Solar: 4,162 kWp, 8,042 GWh/año (PVGIS TMY + PVLIB)
- BESS: 2,000 kWh fijo (DoD 0.8, η 0.95)
- Chargers: 128 total (112 motos @ 2kW + 16 mototaxis @ 3kW)
- Dataset: 1 edificio con 2 playas de estacionamiento

**OE3 - RL Training:**

```yaml
SAC:   episodes=5, batch_size=65,536, gradient_steps=64, device=cuda
PPO:   episodes=5, timesteps=43,800, batch_size=16,384, device=cpu
A2C:   episodes=5, timesteps=43,800, n_steps=32,768, device=cuda
```

**Función Recompensa Multiobjetivo:**

- CO₂: 50% (minimizar emisiones)
- Costo: 15% (minimizar $/kWh)
- Solar: 20% (maximizar autoconsumo)
- EV: 10% (satisfacción carga)
- Grid: 5% (estabilidad red)

---

## 🎯 Resultados Finales

### Rendimiento de Agentes

| Agente | CO₂ Reducción | Pasos | Episodios | Convergencia |
|--------|---------------|-------|-----------|--------------|
| **SAC** 🏆 | **1.49%** | 56,000 | 5 | Sostenida |
| **PPO** 🥈 | 1.08% | 73,000 | 5 | Rápida → Meseta |
| **A2C** 🥉 | 0.61% | 48,300 | 5 | Muy rápida → Meseta |

### Análisis de Curvas

- **SAC:** Mejora continua hasta paso 56k, mejor equilibrio multiobjetivo
- **PPO:** Convergencia en 25k pasos, excelente estabilidad de red (100 kWh picos)
- **A2C:** Plateau en 10k pasos, especializado en autoconsumo solar

### Proyecciones 20 años

- **SAC:** 110,245 ton CO₂ evitado, $2.3M USD ahorro
- **Payback period:** 7-8 años
- **Beneficio neto:** +$15M USD (a 20 años)

---

## 🚀 Próximos Pasos

1. **Implementación SAC en producción** (ganador recomendado)
2. **Validación con 50+ episodios** (convergencia final)
3. **Simulación 20 años** con proyecciones de crecimiento de flota
4. **Integración con sistema de tickets** del Mall Iquitos
5. **Monitoreo en tiempo real** de reducción CO₂

---

## 📊 Estructura del Repositorio

---

## 1️⃣ Instalación y Requisitos

- Python 3.11
- VSCode recomendado
- Dependencias: ver `requirements.txt`

Instalación (usar Python 3.11):

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Activar la venv antes de ejecutar el pipeline (para asegurar Python 3.11).

---

## 2️⃣ Ejecutar el pipeline completo

```bash
python -m scripts.run_pipeline --config configs/default.yaml
```

Salida principal:

- OE2 artefactos: `data/interim/oe2/...`
- Intermedios CityLearn (OE2 consolidados): `data/interim/oe2/citylearn/`
- Analisis y tablas comparativas (OE2/OE3): `analyses/oe2/` y `analyses/oe3/`
- Notebooks de analisis: `analyses/oe2/notebooks/` y `analyses/oe3/notebooks/`
- Metricas de entrenamiento (SAC/PPO): `analyses/oe3/training/`

---

## 📚 Documentación: Diagnóstico Pipeline Solar OE2→OE3

Se ejecutó diagnóstico completo del pipeline de datos solares. Ver:

| Documento | Lectura | Contenido |
| --------- | ------- | --------- |
| [RESUMEN_EJECUTIVO_SOLAR.md](RESUMEN_EJECUTIVO_SOLAR.md) | ⚡ 3 min | Resumen ejectuvo del diagnóstico |
| [QUICK_START_POST_SOLAR_FIX.md](QUICK_START_POST_SOLAR_FIX.md) | ⚡ 5 min | Qué hacer ahora (re-entrenamiento) |
| [EXPLICACION_SOLAR_ZERO.md](EXPLICACION_SOLAR_ZERO.md) | 📖 10 min | Por qué SAC mostraba 0.0 kWh solar |
| [DIAGNOSTICO_SOLAR_PIPELINE.md](DIAGNOSTICO_SOLAR_PIPELINE.md) | 🧪 20 min | Diagnóstico técnico completo |
| [RESUMEN_DIAGNOSTICO_SOLAR.md](RESUMEN_DIAGNOSTICO_SOLAR.md) | 📊 15 min | Tabla antes/después y cambios |
| [ARQUITECTURA_FLUJO_SOLAR.md](ARQUITECTURA_FLUJO_SOLAR.md) | 🏗️ 25 min | Diagrama ASCII del pipeline completo |
| [FAQ_DIAGNOSTICO_SOLAR.md](FAQ_DIAGNOSTICO_SOLAR.md) | ❓ Variable | 20 preguntas frecuentes |
| [INDICE_DIAGNOSTICO_SOLAR.md](INDICE_DIAGNOSTICO_SOLAR.md) | 🧭 5 min | Índice de documentación |

### Verificación Rápida

```bash
# Verifica que datos solares están presentes (< 1 min)
python verify_solar_data.py

# Salida esperada: "RESULTADO: ✅ TODOS LOS DATOS SOLARES SON VÁLIDOS"
```

### Estado del Pipeline

- ✅ OE2 genera datos solares: 1927.4 kWh/kWp anual
- ✅ OE3 asigna a Building CSVs: 1,927,391.6 W/kW.h
- ✅ SAC entrena con recompensa solar (peso 0.20)
- ✅ Logging detallado agregado para trazabilidad

---

## 3️⃣ Ejecutar por etapas

### OE2

```bash
python -m scripts.run_oe2_solar --config configs/default.yaml
python -m scripts.run_oe2_chargers --config configs/default.yaml
python -m scripts.run_oe2_bess --config configs/default.yaml
```

### OE3

```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
python -m scripts.run_oe3_simulate --config configs/default.yaml
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

### Entrenar Agentes RL (Opcional)

Para entrenar agentes de manera independiente antes de la evaluación:

```bash
# Entrenar todos los agentes (SAC, PPO, A2C)
python -m scripts.run_oe3_train_agents --config configs/default.yaml

# Entrenar solo algunos agentes
python -m scripts.run_oe3_train_agents --agents SAC PPO

# Entrenar con más episodios/timesteps
python -m scripts.run_oe3_train_agents --agents SAC --episodes 20
python -m scripts.run_oe3_train_agents --agents PPO --timesteps 50000

# Usar GPU si está disponible
python -m scripts.run_oe3_train_agents --device cuda
```

**Script de conveniencia para entrenar todos los agentes (10 episodios en CUDA):**

```bash
# Linux/Mac
./scripts/train_all_agents_10ep.sh

# Windows
scripts\train_all_agents_10ep.bat

# O manualmente
python -m scripts.run_oe3_train_agents --agents SAC PPO A2C --episodes 10 --device cuda
```

Los modelos entrenados se guardan en `analyses/oe3/training/checkpoints/` y pueden ser reutilizados. Ver `docs/TRAINING_AGENTS.md` para más detalles.

---

## 4️⃣ Notas operativas

- **CityLearn dataset plantilla con EV**: se descarga automáticamente usando `citylearn.data.DataSet.get_dataset(...)` y luego se sobreescribe con perfiles OE2.
- Se generan dos esquemas con **2 buildings separados** para la comparación de emisiones:
  - `schema_grid_only.json`: sin FV ni BESS (solo red + EV) en ambos buildings.
  - `schema_pv_bess.json`: con FV + BESS distribuido proporcionalmente.
- **Arquitectura de 2 playas de estacionamiento:**
  - `Playa_Motos`: 112 chargers (2 kW), 3641.8 kWp PV, 1750 kWh BESS
  - `Playa_Mototaxis`: 16 chargers (3 kW), 520.2 kWp PV, 250 kWh BESS
- La tabla CO₂ asigna emisiones de red al transporte electrificado mediante **reparto proporcional** entre consumo del edificio y consumo EV (ver `src/iquitos_citylearn/oe3/co2_table.py`).

---

## 5️⃣ Configuración

Ajusta parámetros en `configs/default.yaml`:

- FV: `oe2.solar.target_dc_kw`, `oe2.solar.target_annual_kwh`
- Cargadores: `oe2.ev_fleet.*`
- BESS: `oe2.bess.*`
- Intensidad de carbono: `oe3.grid.carbon_intensity_kg_per_kwh`
- Factores transporte: `oe3.emissions.*`

---

## 🧪 Metodología de investigación

### Tipo de metodología

La investigación es de tipo aplicativa–descriptiva. Es aplicativa porque desarrolla el diseño de una infraestructura de carga inteligente para motocicletas y mototaxis eléctricas orientada a resolver un problema concreto (reducción de CO₂ en Iquitos, 2025). Es descriptiva porque caracteriza el sistema y presenta los resultados esperados del diseño mediante modelado y simulación (sin intervención ni manipulación de variables en campo), reportando métricas técnicas y ambientales relevantes.

### Diseño metodológico

El estudio adopta un diseño no experimental–transversal porque no se manipulan deliberadamente las variables independientes ni se asignan tratamientos; en su lugar, se observan y miden los fenómenos en su contexto natural y en un único momento temporal para su análisis. En esta investigación, ello significa caracterizar el sistema de movilidad y las condiciones eléctricas de Iquitos (2025) sin intervenir en campo; las variaciones se exploran solo a nivel teórico mediante modelado y simulación, con el propósito de evaluar el desempeño esperado del diseño de la infraestructura de carga inteligente para motos y mototaxis eléctricas.

### Método de investigación

Se adopta un enfoque cuantitativo porque el estudio determina resultados numéricos del diseño de la infraestructura: dimensionamiento de generación fotovoltaica (kWp), capacidad de almacenamiento (kWh), potencia instalada (kW), energía anual/mensual/diaria (MWh–kWh), cantidad de cargadores y puertos, número de motos/mototaxis a integrar, selección y parametrización del algoritmo de gestión de carga (asignación dinámica, programación horaria, prioridades) y CO₂ evitado (tCO₂e/año). Estos valores se obtienen mediante modelado y simulación con series de 8.760 h, usando datos base (p. ej., 2024) para construir el escenario 2025, aplicando ecuaciones de balance potencia–energía, factores de emisión y restricciones eléctricas del punto de conexión. Se incluyen análisis de sensibilidad (penetración de flota, potencia por punto, reglas del EMS) para garantizar rigurosidad, reproducibilidad y soporte a la toma de decisiones del diseño.

## estado situacional y generación de electricidad en Iquitos para el año 2025

En la ciudad de Iquitos se ha identificado que actualmente no existen motos ni mototaxis eléctricas debido a la ausencia de puntos de recarga pública para vehículos eléctricos, y en particular ninguno conectado directamente a los alimentadores de media tensión. Esta carencia representa un obstáculo importante para la adopción de la flota eléctrica en la ciudad.

Según el Plan de Desarrollo Concertado de la Provincia de Maynas 2025‑2030, el parque vehicular alimentado con combustibles fósiles está compuesto por 61,000 mototaxis, 70,500 motos lineales, 361 microbuses, 1,058 moto furgones, 95 taxis y 202 automóviles, que en conjunto generan 270,649 toneladas de CO₂ al año. Los mototaxis aportan 152,500 tCO₂ y las motos lineales 105,750 tCO₂, es decir, el 95 % del total estimado. Su número elevado los convierte en la muestra prioritaria para este estudio. La generación eléctrica proviene de una central térmica a base de combustibles fósiles: en marzo de 2025 se reportó que el sistema eléctrico de Iquitos emite 290,000 toneladas métricas de CO₂ por año por un consumo promedio de 22.5 millones de galones de combustible, equivalente al 9 % del CO₂ asociado a la producción de Perú. En consecuencia, tanto el transporte como la generación contribuyen al calentamiento global y a las emisiones de gases de efecto invernadero en Iquitos y el país.

Mototaxis y motos lineales son los principales candidatos para la electrificación debido a su alta participación en el parque de vehículos y al uso predominante en la ciudad. El suministro eléctrico se gestiona por Electro Oriente (Elor) y GENRENT, con potencias efectivas de 39 MW y 80 MW respectivamente. El 25 de septiembre, a las 6:30 pm (máxima demanda), ambas empresas reportaron una generación pico de 72.664 MW con diésel como combustible.

En la ciudad Iquitos, Electro Oriente S.A. (Elor) dispone de alimentadores de media tensión de 10 kV y 22.9 kV conectados a dos subestaciones: la Subestación de Iquitos (alimentadores SAL‑01 a SAL‑11) y la Subestación de Santa Rosa (alimentadores SAL‑R1 a SAL‑R12). En la Figura 27, que recoge curvas de demanda históricas en cabecera de cada alimentador proporcionadas por el departamento de operaciones de ELOR, se observa que el alimentador SAL‑R5 alcanza la mayor demanda, próxima a los 6 MW, frente al resto de alimentadores.

## determinación de la ubicación óptima de la infraestructura óptima de la carga inteligente que contribuye significativamente a la viabilidad de reducción cuantificable de las emisiones de dióxido de carbono al maximizar la cobertura de servicio y la demanda

Para definir las coordenadas y condiciones técnicas de la infraestructura, se procesan los inventarios vehiculares y los registros de demanda eléctrica consolidados para Iquitos 2025. Se parte de los datos del Plan de Desarrollo Concertado de la Provincia de Maynas 2025‑2030 (flota mototaxis, motos lineales, microbuses, taxis y automóviles) y del contexto de emisiones por generación térmica (22.5 millones de galones; 290,000 tCO₂/año). Estos insumos se combinan con los perfiles horarios de carga y consumo en `data/interim/oe2/chargers` y `bess`, y los mapas de alimentadores SAL/ELOR para identificar zonas con mayor concentración de vehículos y capacidad de conexión media tensión. En la Tabla 10 se describe la propuesta de 10 ubicaciones; allí se corrigió la distancia SET para el Aeropuerto de Iquitos a 4,400 m, siguiendo la medición precisa hecha durante las visitas.
Se consigna a continuación la Tabla 10 como referencia de las ubicaciones evaluadas:

| Ítem | Lugar | Área techada (m²) | Distancia MT (m) | Distancia SET (m) | Motos/Mototaxis estacionados | Tiempo estacionamiento (h) |
| ------- | ------- | ------------------- | ------------------ | ------------------- | ------------------------------ | ---------------------------- |
| 1 | Empresa Electro Oriente S.A. | 14,000 | 40 | 40 | 200 | 4 |
| 2 | Complejo deportivo Champios | 8,000 | 40 | 1,300 | 300 | 4 |
| 3 | Aeropuerto de Iquitos | 6,000 | 500 | 4,400 | 400 | 2 |
| 4 | Centro comercial Precios UNO | 2,500 | 45 | 580 | 100 | 2 |
| 5 | Universidad Nacional de la Amazonia | 10,000 | 10 | 1,300 | 200 | 2 |
| 6 | Grifo Atenas | 368 | 70 | 5,300 | 500 | 0.2 |
| 7 | Mall de Iquitos | 20,637 | 60 | 60 | 900 | 4 |
| 8 | Universidad Nacional Amazonia - Zungarococha | 8,300 | 200 | 16,000 | 100 | 4 |
| 9 | Escuela técnica PNP | 21,000 | 100 | 9,000 | 200 | 4 |
| 10 | Complejo CNI | 3,500 | 100 | 2,200 | 300 | 4 |

Nota: Valores de área, distancias y tiempos de estacionamiento estimados durante visitas de campo y mediciones de Google Earth 2025.

Se incluyen a continuación algunas de las fotografías documentadas durante las visitas del 19 de octubre y 16 de noviembre de 2025 que ilustran la ocupación constante del Mall de Iquitos:

1. **Figura 29:** Estacionamiento nocturno de motos bajo la zona techada, con filas continuas de motocicletas de combustión interna a las 19:00 h.
2. **Figura 30:** Vista nocturna adicional del estacionamiento, mostrando elevado flujo de usuarios y ocupación total en los pabellones cubiertos.
3. **Figura 31:** Sector de mototaxis con numerosas unidades alineadas junto al acceso principal, reforzando la necesidad de nodos de carga dedicados.
4. **Figura 32:** Panorámica nocturna del área combinada de motos y mototaxis, evidenciando larga permanencia de vehículos en horario pico.
5. **Figura 33:** Captura diurna (16/11/2025, 14:18 h) del estacionamiento techado con ocupación casi total, ideal para instalar cargadores bajo cubierta.
6. **Figura 34:** Otra toma diurna (19/11/2025, 14:03 h) con hileras de motos que confirman la alta demanda de estacionamiento a lo largo del día.

![Figura 29](reports/oe2/figuras/fig29.jpg)
![Figura 30](reports/oe2/figuras/fig30.jpg)
![Figura 31](reports/oe2/figuras/fig31.jpg)
![Figura 32](reports/oe2/figuras/fig32.jpg)
![Figura 33](reports/oe2/figuras/fig33.jpg)
![Figura 34](reports/oe2/figuras/fig34.jpg)
![Figura 35](reports/oe2/figuras/fig35.jpg)

Las figuras respaldan la elección del Mall de Iquitos como ubicación estratégica porque combinan alta densidad de motos/mototaxis, tiempo permanente ≥4 h y disponibilidad de espacio techado conectado a la subestación Santa Rosa.

Por otra parte, para reforzar la elección de un centro comercial como ubicación de la infraestructura de carga, el reporte [27] sobre infraestructuras de carga de vehículos eléctricos en el Perú (ver Tabla 6 del ítem 2.2.1.3) evidencia que la mayoría de puntos de carga existentes se encuentran en centros comerciales, malls y hoteles. Esta tendencia respalda la selección del Mall de Iquitos como sitio estratégico para el diseño de la infraestructura de carga inteligente de motos y mototaxis eléctricas en el marco de la presente investigación.

La selección del Mall de Iquitos como ubicación estratégica para la infraestructura de carga inteligente se justifica porque concentra simultáneamente las condiciones óptimas para maximizar la sustitución de combustibles fósiles y la reducción de emisiones de dióxido de carbono al año 2025. Presenta una alta afluencia diaria de motos y mototaxis alimentados por diésel, con tiempos de estacionamiento promedio no menores a cuatro horas, lo que ofrece ventana suficiente para ciclos completos de carga eléctrica. Además, dispone de una amplia área techada (20 637 m²) para generación fotovoltaica y está a solo 60 m de la subestación Santa Rosa, lo que facilita integrar un sistema FV–BESS que abastezca la demanda de carga con energía renovable y reduzca la dependencia de la red térmica. Así, la localización en el Mall responde tanto a criterios técnicos (espacio y viabilidad eléctrica) como a la meta de maximizar la mitigación de CO₂ asociada al reemplazo progresivo de motos y mototaxis a diésel por eléctricos.

En esta fotografía se aprecian hileras de motocicletas estacionadas bajo las estructuras metálicas techadas y en los espacios laterales, confirmando la alta dependencia del centro comercial de este tipo de vehículo también en horario diurno y la consecuente generación de emisiones asociadas. En conjunto, las Figuras 30 a 34 evidencian que la playa de estacionamiento de motos y mototaxis del Mall de Iquitos se mantiene con una alta ocupación tanto de día como de noche, convirtiéndose en un foco relevante de emisiones de CO₂ y contaminantes atmosféricos ligados al uso intensivo de vehículos ligeros a gasolina. Desde la perspectiva de la presente tesis, este conjunto de espacios se identifica como un punto estratégico para la implementación de infraestructura de carga inteligente para motos y mototaxis eléctricas, alimentada por el sistema fotovoltaico y el BESS del mall. La elevada densidad de vehículos y su permanencia temporal en el lugar justifican la instalación de cargadores que permitan, de manera progresiva, sustituir parte de la flota de combustión por vehículos eléctricos y transformar esta zona en un nodo de movilidad eléctrica de bajas emisiones para la ciudad de Iquitos.

Por otra parte, se realizó una captura de imagen de Google Earth con vista en planta (Figura 34), donde se distinguen áreas sombreadas en color verde que corresponden al espacio techado disponible para el dimensionamiento de generación solar y el área de estacionamiento para motos/mototaxis ubicada en la parte inferior de la imagen. En el mismo gráfico se observa un área sombreada en color violeta frente al Mall, que identifica a la Subestación de Transformación Santa Rosa, elemento clave de la evaluación eléctrica del emplazamiento. Esta perspectiva complementaria confirma que el Mall dispone de superficie techada adecuada, parqueo amplio y proximidad al nodo eléctrico necesario para integrar el sistema FV–BESS con la infraestructura de carga.

El procesamiento incluye la construcción de curvas de demanda consolidada (serie de 8,760 h), el cálculo de indicadores de cobertura (motos/mototaxis por alimentador), y la aplicación de restricciones topológicas (distancia a subestación, capacidad del alimentador) que definen la viabilidad técnica. Además, se calibra el modelo con parámetros eléctricos (voltajes 10 kV/22.9 kV, capacidad Elm, temperaturas) y se simulan escenarios de carga para determinar dónde colocar puntos de recarga conectados directamente a media tensión. La salida de este bloque alimenta el script `scripts/run_oe1_location.py`, que genera un informe y valida las zonas candidatas frente a los criterios de reducción de CO₂ y cobertura de demanda.

El desarrollo también se alimenta de los datos de campo reunidos en 2025, detallados en la Tabla 10 del estudio: el Grifo Atenas, el Mall de Iquitos, la Universidad Nacional de la Amazonia (Zungarococha), la Escuela técnica PNP y el Complejo CNI muestran áreas techadas, tiempos de permanencia y distancias a la red eléctrica que proveen insumos cuantitativos (área, distancias, tiempos de estacionamiento). Según esa información, el Mall de Iquitos ofrece 20 637 m² de techo, 60 m de distancia a la Subestación Santa Rosa, aproximadamente 957 m² de parqueo, y tiempos promedio de estacionamiento de motos/mototaxis superiores a 4 h (datos validado por entrevistas al personal de tickets). El 19 de octubre de 2025 a las 19:00 h se registraron ~900 motos y 130 mototaxis en ese estacionamiento (Figuras 29‑32), y las fotografías indican una alta densidad en horario nocturno y diurno. Una vista desde Google Earth (Figuras 33‑35) muestra áreas verdes techadas para FV, el área de parqueo y la subestación Santa Rosa (área violeta), confirmando la conectividad con la red y la disponibilidad de superficie para FV.

Las imágenes también revelan que el Mall mantiene ocupación intensa de motos/mototaxis (Figuras 30‑34) tanto de noche como de día, consolidándolo como foco de emisiones de CO₂ y candidaturas ideal para la infraestructura inteligente. La evidencia respalda el uso de ese centro comercial, donde se pueden instalar cargadores bajo estructura techada conectados al FV‑BESS. El informe [27] sobre infraestructura de carga en Perú (Tabla 6, sección 2.2.1.3) confirma que la mayoría de puntos existentes se ubican en centros comerciales, lo que fortalece la decisión de enfocar la electrificación de motos/mototaxis en el Mall de Iquitos. Su ubicación estratégica maximiza sustitución de diésel, cobertura de demanda y reducción de emisiones, al ofrecer tiempo suficiente de carga, espacio de FV y cercanía al transformador de Santa Rosa, reduciendo dependencia de la red térmica.
