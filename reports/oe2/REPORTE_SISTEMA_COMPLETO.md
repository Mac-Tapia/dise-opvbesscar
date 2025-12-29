# REPORTE DEL SISTEMA FOTOVOLTAICO CON ALMACENAMIENTO Y CARGADORES EV

## Proyecto: Infraestructura de Carga EV para Mall de Iquitos

**Ubicación:** Iquitos, Perú (lat=-3.75°, lon=-73.25°, alt=104m)  
**Fecha de Generación:** 2024  

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
| Ciclos por día | 0.79 | ciclos |
| SOC mínimo | 20 | % |
| SOC máximo | 100 | % |
| **Autosuficiencia** | **25.3** | **%** |

---

## 3. CARGADORES EV - MODO 3 (IEC 61851)

### 3.1 Flota y supuestos operativos

| Tipo             | Cantidad | % que cargan | SOC faltante medio | Vehículos que cargan/día |
| ---              | ---      | ---          | ---                | ---                      |
| Motos eléctricas | 900      | 90%          | 57.5%              | 810                      |
| Mototaxis        | 130      | 90%          | 57.5%              | 117                      |
| **TOTAL**        | **1,030**| -            | -                  | **927**                  |

> SOC faltante medio 57.5% = promedio de 20/40/50/60% al llegar (equiprobable). Permanencia mínima 4 h; sesión de carga 30 min modo 3 (ocupación 12.5%).

### 3.2 Configuración de Carga

| Parámetro | Valor | Unidad |
| --- | --- | --- |
| Tipo de carga | Modo 3 | IEC 61851 |
| Potencia cargador motos | 2.0 | kW |
| Potencia cargador mototaxis | 3.0 | kW |
| Cargadores recomendados | 33 | unidades |
| Sockets por cargador | 4 | - |
| **Sockets totales** | **129** | **tomas** |
| Duración de sesión | 30 | minutos |
| Horario del mall | 9:00 - 22:00 | horas |
| Horas pico | 18:00 - 22:00 | 4 horas |
| Utilización | 85 | % |
| **Potencia objetivo** | **310-340** | **kW** |

> Implementación modular: Fase 1 (piloto) 10-15 cargadores (40-60 tomas), 100-150 kW para medir ocupación real con bajo CAPEX. Fase 2 (escalado) obra/acometida listas para 30-40 cargadores (120-160 tomas), 300-400 kW, activando módulos si la ocupación pico supera 50-60%.

### 3.3 Demanda de Energía EV

| Parámetro | Valor | Unidad |
| --- | --- | --- |
| Energía diaria EV | 567 | kWh/día |
| Potencia pico perfil | 283 | kW |
| Sesiones/hora pico (capacidad) | 258 | sesiones |
| Sesiones/día (capacidad) | 3,354 | sesiones |
| Sesiones/día (demanda objetivo) | 927 | sesiones |

### 3.4 Demanda Total Instalada

| Tipo | Cantidad | Potencia | Demanda Instalada |
| --- | --- | --- | --- |
| Motos (pico) | 113 | 2.0 kW | 226 kW |
| Mototaxis (pico) | 17 | 3.0 kW | 51 kW |
| **TOTAL dimensionado** | - | - | **277 kW** |

---

## 4. BALANCE ENERGÉTICO DIARIO

### 4.1 Demandas

| Componente | Valor | Unidad |
| --- | --- | --- |
| Demanda Mall | 33,885 | kWh/día |
| Demanda EV | 567 | kWh/día |
| **Demanda Total** | **34,452** | **kWh/día** |

### 4.2 Generación y Flujos

| Parámetro | Valor | Unidad |
| --- | --- | --- |
| Generación PV | 9,016 | kWh/día |
| Excedente PV | 0 | kWh/día |
| Déficit | 25,436 | kWh/día |
| Importación de red | 25,436 | kWh/día |
| Exportación a red | 222 | kWh/día |
| **Autosuficiencia** | **26.2** | **%** |

Nota: La FV se asigna primero a la carga EV y al BESS; el excedente cubre la demanda del mall y el remanente se exporta.

---

## 5. RESUMEN EJECUTIVO

### Inversión en Infraestructura

| Sistema | Capacidad | Especificación |
| --- | --- | --- |
| **PV** | 2,591 kWp | 8,224 módulos SunPower SPR-315E |
| **BESS** | 740 kWh | 370 kW potencia |
| **Cargadores Modo 3** | 33 unidades | 129 sockets (2-3 kW), 310-340 kW objetivo |

### Indicadores Clave

| Indicador | Valor |
| --- | --- |
| Generación anual | **3,299 MWh** |
| Almacenamiento | **740 kWh** |
| Demanda total instalada EV | **277 kW** |
| Vehículos efectivos/día | **927** |
| Autosuficiencia energética | **26.2%** |
| Importación de red | **25,436 kWh/día** |
| Exportación a red | **222 kWh/día** |

---

## 6. CONSIDERACIONES DE HORA PUNTA

### 6.1 Distribución Temporal

| Período | Horario | Vehículos | Observación |
| --- | --- | --- | --- |
| Apertura mall | 9:00 | - | Inicio operación |
| Hora normal | 9:00 - 17:59 | Moderada | Demanda repartida |
| Hora pico | 18:00 - 21:59 | hasta 258/hora (capacidad) | Alta demanda, rotación 30 min |
| Cierre | 22:00 | - | Fin operación |

### 6.2 Capacidad en hora pico

- 33 cargadores x 4 tomas = 129 puntos simultáneos.
- Sesiones por hora (capacidad): ~258 (30 min por sesión).
- Sesiones totales por día (capacidad): ~3,354.
- Demanda objetivo: 927 sesiones/día; cabe sin colas con la capacidad dimensionada.

---
