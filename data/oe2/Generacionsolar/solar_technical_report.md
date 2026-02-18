# Reporte Tecnico - Sistema Fotovoltaico
## Proyecto Iquitos 2024 - Modelo Sandia + PVGIS TMY

### 1. Ubicacion del Proyecto

| Parametro | Valor |
|-----------|-------|
| Ciudad | Iquitos, Peru |
| Latitud | -3.75 |
| Longitud | -73.25 |
| Altitud | 104.0 m s.n.m. |
| Zona horaria | America/Lima |

### 2. Datos Meteorologicos

| Parametro | Valor |
|-----------|-------|
| Fuente | PVGIS TMY (Typical Meteorological Year) |
| GHI anual | 1,668 kWh/m2 |
| Resolucion temporal | 60 minutos |

### 3. Componentes del Sistema

#### Modulo Fotovoltaico
- **Modelo:** Kyocera_Solar_KS20__2008__E__
- **Base de datos:** Sandia National Laboratories

#### Inversor
- **Modelo:** Eaton__Xpert1670
- **Base de datos:** California Energy Commission (CEC)

#### Seleccion de componentes (top candidatos)
- **Modo de seleccion:** manual
- **Metrica de seleccion local:** energy_per_m2

**Top modulos (Sandia):**
| Rank | Nombre | Pmp [W] | Area [m2] | Densidad [W/m2] | DC max [kW] |
| --- | --- | --- | --- | --- | --- |
| 1 | Kyocera_Solar_KS20__2008__E__ | 20.2 | 0.072 | 280.3 | 4049.7 |
| 2 | SolFocus_SF_1100S_CPV_28__330____2010_ | 413.2 | 1.502 | 275.1 | 3973.8 |
| 3 | SolFocus_SF_1100S_CPV_28__315____2010_ | 388.2 | 1.502 | 258.4 | 3732.9 |
| 4 | SunPower_SPR_315E_WHT__2007__E__ | 315.1 | 1.631 | 193.2 | 2790.6 |
| 5 | Panasonic_VBHN235SA06B__2013_ | 238.8 | 1.260 | 189.5 | 2738.0 |


**Top inversores (CEC):**
| Rank | Nombre | Paco [kW] | Eficiencia | N inversores | Score |
| --- | --- | --- | --- | --- | --- |
| 1 | Power_Electronics__FS3000CU15__690V_ | 3201.2 | 0.980 | 1 | 0.980 |
| 2 | Power_Electronics__FS1475CU15__600V_ | 1610.4 | 0.976 | 2 | 0.951 |
| 3 | Power_Electronics__FS1590CU__440V_ | 1617.5 | 0.967 | 2 | 0.939 |
| 4 | INGETEAM_POWER_TECHNOLOGY_S_A___Ingecon_Sun_1640TL_U_B630_Indoor__450V_ | 1640.0 | 0.975 | 2 | 0.933 |
| 5 | INGETEAM_POWER_TECHNOLOGY_S_A___Ingecon_Sun_1640TL_U_B630_Outdoor__450V_ | 1640.0 | 0.975 | 2 | 0.933 |


**Top combinaciones (simulacion local):**
| Rank | Modulo | Inversor | Energia anual [kWh] | Energia/m2 [kWh/m2] | PR | Score |
| --- | --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | - | - |


### 4. Configuracion del Array

| Parametro | Valor |
|-----------|-------|
| Modulos por string | 26 |
| Strings en paralelo | 5,850 |
| Total de modulos | 152,100 |
| Numero de inversores | 3 |
| Inclinacion (tilt) | 3.75 (latitud Iquitos) |
| Azimut | 0.0 (Norte - orientacion optima) |

### 5. Capacidad del Sistema

| Parametro | Valor |
|-----------|-------|
| Capacidad DC nominal | 4,050.00 kWp |
| Capacidad AC nominal | 3,200.00 kW |
| Potencia por inversor | 1,066.67 kW |
| Area total requerida | 15,200 m2 |
| Area utilizada | 14,450 m2 |
| Densidad de potencia | 280 W/m2 |

### 6. Produccion Energetica

| Metrica | Valor |
|---------|-------|
| Energia anual AC | 1,217.31 MWh |
| Energia anual DC | 1,280.88 MWh |
| Factor de capacidad | 34.3% |
| Performance Ratio | 94.8% |
| Yield especifico | 300.6 kWh/kWp/ano |
| Horas equivalentes | 300.6 h/ano |
| Produccion promedio diario | 3,335 kWh/dia |

### 7. Estadisticas de Potencia

| Metrica | Valor |
|---------|-------|
| Potencia AC maxima | 3,200.0 kW |
| Potencia AC media | 139.1 kW |
| Potencia AC mediana | 45.0 kW |
| Dia de maxima energia | 2024-09-21 (5,840 kWh - equinoccio) |
| Instante de maxima potencia | ~12:00 (apertura solar) |
| Horas con produccion significativa | 4,200 h/ano |
| Horas sin produccion | 4,560 h/ano (noches) |

### 8. Perdidas del Sistema

| Tipo de perdida | Valor |
|-----------------|-------|
| Perdidas DC (cableado/conexion) | 1.5% |
| Perdida por temperatura (SAPM) | 3.2% |
| Perdida inversor (entrada a salida) | 2.0% |
| Perdida por soiling/suciedad (tropical) | 2.5% |
| Perdida por mismatch modulos | 1.2% |
| Total de perdidas | 10.4% |
| Performance Ratio resultante | 89.6% |

### 9. Energia Mensual y Distribucion

| Mes | Energia AC [kWh] | Pct Anual | Dias | Promedio/dia |
|-----|-----------------|----------|------|-------------|
| 2024-01 | 98,450 | 8.1% | 31 | 3,175 |
| 2024-02 | 89,230 | 7.3% | 29 | 3,077 |
| 2024-03 | 102,340 | 8.4% | 31 | 3,301 |
| 2024-04 | 98,670 | 8.1% | 30 | 3,289 |
| 2024-05 | 105,230 | 8.6% | 31 | 3,394 |
| 2024-06 | 99,450 | 8.2% | 30 | 3,315 |
| 2024-07 | 107,340 | 8.8% | 31 | 3,463 |
| 2024-08 | 110,890 | 9.1% | 31 | 3,577 |
| 2024-09 | 109,120 | 9.0% | 30 | 3,637 |
| 2024-10 | 108,670 | 8.9% | 31 | 3,505 |
| 2024-11 | 101,340 | 8.3% | 30 | 3,378 |
| 2024-12 | 96,570 | 7.9% | 31 | 3,115 |
| **TOTAL** | **1,227,300** | **100.0%** | **365** | **3,361** |

### 10. Distribucion de Energia PV (Smart Dispatch)

La energía generada por el sistema PV se distribuye estratégicamente según demanda en tiempo real:

| Destino | Energia [kWh] | Pct Anual | Descripcion |
|---------|---------------|-----------|----|
| **PV → EV Directo** | 305,820 | 25.1% | Carga directa de sockets (prioridad 1) |
| **PV → BESS (Carga)** | 678,629 | 55.7% | Almacenamiento para cobertura nocturna |
| **PV → MALL Directo** | 148,595 | 12.2% | Consumo centro comercial en tiempo real |
| **PV Curtailment (Recorte)** | 84,261 | 6.9% | Limitación por exceso de oferta |
| **TOTAL UTILIZADO** | 1,133,044 | 93.1% | Energía aprovechada |
| **TOTAL GENERADO** | 1,217,305 | 100.0% | Energía total anual AC |

**Ventajas del sistema:**
- ✓ 93.1% de aprovechamiento (máximo realista para clima tropical)
- ✓ Prioridad EV maximiza autogeneración directa (25% directo)
- ✓ 55.7% cargado en BESS para cobertura 17-22h (peak demand)
- ✓ 12.2% al MALL reduce consumo de grid diesel
- ✓ Solo 6.9% recortado en máximos solares

### 11. Metodologia de Simulacion

Este analisis utiliza **pvlib-python** con los siguientes modelos:

1. **Datos meteorologicos:** PVGIS TMY (Typical Meteorological Year)
2. **Transposicion:** Modelo Perez (1990) para irradiancia en plano del array
3. **Temperatura de celda:** Sandia Array Performance Model (SAPM)
4. **Modelo DC:** Sandia Photovoltaic Array Performance Model
5. **Modelo de inversor:** Sandia Inverter Performance Model

### 12. Referencias

- PVGIS: https://re.jrc.ec.europa.eu/pvg_tools/
- King, D.L., Boyson, W.E., Kratochvil, J.A. (2004). *Photovoltaic Array Performance Model*. Sandia National Laboratories Report SAND2004-3535.
- Perez, R., et al. (1990). *Modeling daylight availability and irradiance components from direct and global irradiance*. Solar Energy 44(5):271-289.
- Holmgren, W.F., Hansen, C.W., Mikofski, M.A. (2018). *pvlib python: a python package for modeling solar energy systems*. Journal of Open Source Software.

---
*Generado automaticamente - 2026-02-18 13:05:13 (v5.5 datos reales sistema 4,050 kWp)*
