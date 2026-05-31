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
| GHI anual (horizontal) | 1,668 kWh/m2 |
| POA anual (plano array) | 1,675 kWh/m2 |
| Resolucion temporal | 60 minutos |

### 3. Componentes del Sistema

#### Modulo Fotovoltaico
- **Modelo:** Jinko_Tiger_Neo_JKM580N_72HL4_BDV__PVWatts_
- **Base de datos:** Sandia National Laboratories

#### Inversor
- **Modelo:** Eaton__Xpert1670
- **Base de datos:** California Energy Commission (CEC)

#### Seleccion de componentes (top candidatos)
- **Modo de seleccion:** pvwatts
- **Metrica de seleccion local:** pvwatts

**Top modulos (Sandia):**
| Rank | Nombre | Pmp [W] | Area [m2] | Densidad [W/m2] | DC max [kW] |
| --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | - |


**Top inversores (CEC):**
| Rank | Nombre | Paco [kW] | Eficiencia | N inversores | Score |
| --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | - |


**Top combinaciones (simulacion local):**
| Rank | Modulo | Inversor | Energia anual [kWh] | Energia/m2 [kWh/m2] | PR | Score |
| --- | --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | - | - |


### 4. Configuracion del Array

| Parametro | Valor |
|-----------|-------|
| Modulos por string | 14 |
| Strings en paralelo | 512 |
| Total de modulos | 7,175 |
| Numero de inversores | 2 |
| Inclinacion (tilt) | 10.0 |
| Azimut | 0.0 (Norte) |

### 5. Capacidad del Sistema

| Parametro | Valor |
|-----------|-------|
| Capacidad DC nominal | 4,162.00 kWp |
| Capacidad AC nominal | 3,201.00 kW |
| Area total disponible | 20,637 m2 |
| Area utilizada | 18,535 m2 |

### 6. Produccion Energetica

| Metrica | Valor |
|---------|-------|
| Energia anual AC | 5.819 GWh |
| Energia anual DC | 5.819 GWh |
| Factor de capacidad | 20.8% |
| Performance Ratio | 83.5% |
| Yield especifico | 1,398 kWh/kWp/ano |
| Horas equivalentes | 1,818 h/ano |

### 7. Estadisticas de Potencia

| Metrica | Valor |
|---------|-------|
| Potencia AC maxima | 3,245.9 kW |
| Potencia AC media | 664.3 kW |
| Dia de maxima energia | 2024-03-09 (22,573 kWh) |
| Instante de maxima potencia | 2024-10-18 11:00:00-05:00 |
| Horas con produccion | 4,259 h/ano |

### 8. Perdidas del Sistema

| Tipo de perdida | Valor |
|-----------------|-------|
| Total | 13.6% |

### 9. Energia Mensual

| Mes | Energia [kWh] |
|-----|---------------|
| 2024-01 | 460,305 |
| 2024-02 | 405,139 |
| 2024-03 | 509,481 |
| 2024-04 | 472,138 |
| 2024-05 | 460,889 |
| 2024-06 | 467,950 |
| 2024-07 | 491,789 |
| 2024-08 | 563,964 |
| 2024-09 | 551,952 |
| 2024-10 | 543,068 |
| 2024-11 | 469,118 |
| 2024-12 | 423,539 |

### 10. Metodologia de Simulacion

Este analisis utiliza **pvlib-python** con los siguientes modelos:

1. **Datos meteorologicos:** PVGIS TMY (Typical Meteorological Year)
2. **Transposicion:** Modelo Perez (1990) para irradiancia en plano del array
3. **Temperatura de celda:** Sandia Array Performance Model (SAPM)
4. **Modelo DC:** Sandia Photovoltaic Array Performance Model
5. **Modelo de inversor:** Sandia Inverter Performance Model

### 11. Referencias

- PVGIS: https://re.jrc.ec.europa.eu/pvg_tools/
- King, D.L., Boyson, W.E., Kratochvil, J.A. (2004). *Photovoltaic Array Performance Model*. Sandia National Laboratories Report SAND2004-3535.
- Perez, R., et al. (1990). *Modeling daylight availability and irradiance components from direct and global irradiance*. Solar Energy 44(5):271-289.
- Holmgren, W.F., Hansen, C.W., Mikofski, M.A. (2018). *pvlib python: a python package for modeling solar energy systems*. Journal of Open Source Software.

---
*Generado automaticamente - 2026-05-31 14:33:57*
