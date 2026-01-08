# REPORTE DEL SISTEMA FOTOVOLTAICO CON ALMACENAMIENTO Y CARGADORES EV

## Proyecto: Infraestructura de Carga EV para Mall de Iquitos

**Ubicación:** Iquitos, Perú (lat=-3.75°, lon=-73.25°, alt=104m)  
**Fecha de Generación:** 2024  

---

## Línea Base de Emisiones CO₂ - Iquitos 2025

Fuente: Plan de Desarrollo Concertado de la Provincia de Maynas 2025-2030 [4]

| Sector | Detalle | Emisiones (tCO₂/año) |
| ------ | ------- | ------------------- |
| Transporte | 61,000 mototaxis | 152,500 |
| Transporte | 70,500 motos lineales | 105,750 |
| **Total transporte** | 95% del sector | **258,250** |
| Generación eléctrica | Central térmica (22.5M gal/año) | **290,000** |

---

## 1. SISTEMA FOTOVOLTAICO (PV)

### 1.1 Componentes Seleccionados

| Componente | Modelo | Especificación |
| --- | --- | --- |
| **Módulo Solar** | SunPower SPR-315E | 315 W, 1.631 m², 193.2 W/m² |
| **Inversor Central** | Sungrow SG2500U (550V) | 2,500 kW AC |

### 1.2 Dimensionamiento del Sistema

| Parámetro | Valor | Unidad |
| --- | --- | --- |
| Área total disponible | 20,637 | m² |
| Factor de diseño | 65 | % |
| **Área utilizable** | **13,414** | **m²** |
| Número de módulos | 8,224 | unidades |
| **Potencia DC instalada** | **2,591.15** | **kWp** |
| Potencia AC máxima | 2,500 | kW |

### 1.3 Generación de Energía

| Parámetro | Valor | Unidad |
| --- | --- | --- |
| **Energía anual** | **3,299** | **MWh/año** |
| Energía diaria promedio | 9,040 | kWh/día |
| Irradiación específica | 1,273 | kWh/kWp/año |
| Performance Ratio | 76.5 | % |

---

## 2. SISTEMA DE ALMACENAMIENTO (BESS)

### 2.1 Dimensionamiento

| Parámetro | Valor | Unidad |
| --- | --- | --- |
| **Capacidad** | **740** | **kWh** |
| **Potencia nominal** | **370** | **kW** |
| C-rate | 0.5 | - |
| Profundidad de descarga (DoD) | 80 | % |
| Eficiencia round-trip | 90 | % |

### 2.2 Operación Diaria

| Parámetro | Valor | Unidad |
| --- | --- | --- |
| Ciclos por dia | 0.79 | ciclos |
| SOC mínimo | 20 | % |
| SOC máximo | 100 | % |
| **Autosuficiencia** | **25.3** | **%** |

---

## 3. CARGADORES EV - MODO 3 (IEC 61851)

### 3.1 Flota de Vehículos

| Tipo | Cantidad | PE | FC | Vehículos efectivos/día |
| --- | --- | --- | --- | --- |
| **Motos eléctricas** | 900 | 80% | 70% | 720 |
| **Mototaxis** | 130 | 90% | 80% | 117 |
| **TOTAL** | **1,030** | - | - | **837** |

> **PE** = Probabilidad de Evento (% de vehículos que cargan diariamente)  
> **FC** = Factor de Carga (% de batería a recargar por sesión)

### 3.2 Configuración de Carga

| Parámetro | Valor | Unidad |
| --- | --- | --- |
| **Tipo de carga** | **Modo 3** | IEC 61851 |
| Potencia cargador motos | 2.0 | kW |
| Potencia cargador mototaxis | 3.0 | kW |
| Cargadores recomendados | 31 | unidades |
| Sockets por cargador | 4 | - |
| **Sockets totales** | **124** | **tomas** |
| Duración de sesión | 30 | minutos |
| Horario del mall | 9:00 - 22:00 | horas |
| **Horas pico** | **18:00 - 22:00** | **4 horas** |
| Utilización | 85 | % |

### 3.3 Demanda de Energía EV

| Parámetro | Valor | Unidad |
| --- | --- | --- |
| **Energía diaria EV** | **644** | **kWh/día** |
| Potencia pico perfil | 129 | kW |
| Sesiones/hora pico | 209 | sesiones |

### 3.4 Demanda Total Instalada

| Tipo | Cantidad | Potencia | Demanda Instalada |
| --- | --- | --- | --- |
| Motos | 900 | 2.0 kW | 1,800 kW |
| Mototaxis | 130 | 3.0 kW | 390 kW |
| **TOTAL** | 1,030 | - | **2,190 kW** |

---

## 4. BALANCE ENERGÉTICO DIARIO

### 4.1 Demandas

| Componente | Valor | Unidad |
| --- | --- | --- |
| Demanda Mall | 33,885 | kWh/día |
| Demanda EV | 644 | kWh/día |
| **Demanda Total** | **34,531** | **kWh/día** |

### 4.2 Generación y Flujos

| Parámetro | Valor | Unidad |
| --- | --- | --- |
| Generación PV | 9,016 | kWh/día |
| Excedente PV | 222 | kWh/día |
| Deficit | 25,795 | kWh/día |
| Importacion de red | 25,795 | kWh/día |
| Exportacion a red | 222 | kWh/día |
| **Autosuficiencia** | **25.3** | **%** |

Nota: La FV se asigna primero a la carga EV y al BESS; el excedente cubre la demanda del mall y el remanente se exporta.

---

## 5. RESUMEN EJECUTIVO

### Inversión en Infraestructura

| Sistema | Capacidad | Especificación |
| --- | --- | --- |
| **PV** | 2,591 kWp | 8,224 módulos SunPower SPR-315E |
| **BESS** | 740 kWh | 370 kW potencia |
| **Cargadores Modo 3** | 31 unidades | 124 sockets (2-3 kW) |

### Indicadores Clave

| Indicador | Valor |
| --- | --- |
| 🌞 Generación anual | **3,299 MWh** |
| 🔋 Almacenamiento | **740 kWh** |
| ⚡ Demanda total instalada EV | **2,190 kW** |
| 🚗 Vehículos efectivos/día | **837** |
| 🌱 Autosuficiencia energética | **25.3%** |
| ⬇️ Importación de red | **25,795 kWh/día** |
| ⬆️ Exportación a red | **222 kWh/día** |

---

## 6. CONSIDERACIONES DE HORA PUNTA

### 6.1 Distribución Temporal

| Período | Horario | Vehículos | Observación |
| --- | --- | --- | --- |
| Apertura mall | 9:00 | - | Inicio operación |
| Hora normal | 9:00 - 17:59 | Pocos | Baja demanda |
| **Hora punta** | **18:00 - 21:59** | **837/hora** | **Alta demanda** |
| Cierre | 22:00 | - | Fin operación |

### 6.2 Llegada de Vehículos en Hora Punta

- **4 horas pico**: 18:00, 19:00, 20:00, 21:00
- **Distribución**: Los 837 vehículos efectivos llegan distribuidos en las 4 horas
- **Sesiones por hora**: ~209 sesiones/hora
- **Capacidad cargadores**: 31 cargadores × 4 sockets = 124 puntos de carga

---

## 7. RESULTADOS OE3 - ENTRENAMIENTO DE AGENTES

Grafica comparativa del aprendizaje de SAC, PPO y A2C para el escenario con PV+BESS:

![Comparativa de entrenamiento OE3](../oe3/training_comparison.png)

Graficas individuales de aprendizaje por agente:

![SAC entrenamiento](../oe3/SAC_training.png)

![PPO entrenamiento](../oe3/PPO_training.png)

![A2C entrenamiento](../oe3/A2C_training.png)

CSV de metricas de entrenamiento:

Resumen num?rico (mejor y ?ltimo reward):

- SAC: mejor=15145.8391, ?ltimo=15145.8391, pasos=17518
- PPO: mejor=8142.5492, ?ltimo=8142.5492, pasos=17518
- A2C: mejor=8040.8059, ?ltimo=8040.8059, pasos=17518

- `../../analyses/oe3/training/SAC_training_metrics.csv`
- `../../analyses/oe3/training/PPO_training_metrics.csv`
- `../../analyses/oe3/training/A2C_training_metrics.csv`

## 8. Validacion de reduccion de CO2 (OE2 -> OE3)

Se vincula el dimensionamiento OE2 con la reduccion de CO2 cuantificada en OE3.

- Agente seleccionado: A2C (SB3) — control inteligente de cargadores y BESS para cumplir OE.3 y maximizar la energía PV.
- CO2 sin control (PV+BESS): 103,184 kgCO2/año
- CO2 con control: 95,505 kgCO2/año
- Reducción neta: 7,679 kgCO2/año (~7.45%)

Fuente: analyses/oe3/co2_control_vs_uncontrolled.csv

La distribución de la reducción de CO2 se desglosa en:

- **Directa**: 85,534 kgCO2/año evitados por desplazar consumo de la matriz con PV+BESS.
- **Indirecta**: 9,971 kgCO2/año adicionales por maximizar el uso de generación renovable y almacenamiento.
- **Total**: 95,504 kgCO2/año (aprox. 0.10 tCO2/año) con el agente inteligente A2C en OE3.

Comparando con el escenario sin control, las **emisiones del transporte** se reducen de 111,761 kgCO2/año a 7,967 kgCO2/año (92.87% menos).

---

**Notas:**

1. Todos los valores son calculados con datos reales de irradiación de Iquitos (PVGIS TMY)
2. La potencia PV está limitada por el área disponible (13,414 m²)
3. **Cargadores Modo 3 (IEC 61851)**: Carga AC con comunicación piloto
4. El sistema opera con **25.3% de autosuficiencia**, dado que la demanda del mall supera la generación FV
5. El excedente de energía (~222 kWh/día) se exporta a red; el BESS se dimensiona por déficit EV nocturno (SOC mínimo 20%)
