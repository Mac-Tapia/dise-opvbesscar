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
| GHI anual | 1,664 kWh/m2 |
| Resolucion temporal | 15 minutos |

### 3. Componentes del Sistema

#### Modulo Fotovoltaico
- **Modelo:** Kyocera_Solar_KS20__2008__E__
- **Base de datos:** Sandia National Laboratories

#### Inversor
- **Modelo:** INGETEAM_POWER_TECHNOLOGY_S_A___Ingecon_Sun_1560TL_U_B600_Indoor__450V_
- **Base de datos:** California Energy Commission (CEC)

#### Seleccion de componentes (top candidatos)
- **Modo de seleccion:** auto_top5
- **Metrica de seleccion local:** energy_per_m2

**Top modulos (Sandia):**
| Rank | Nombre | Pmp [W] | Area [m2] | Densidad [W/m2] | DC max [kW] |
| --- | --- | --- | --- | --- | --- |
| 1 | Kyocera_Solar_KS20__2008__E__ | 20.2 | 0.072 | 280.3 | 2769.7 |
| 2 | SolFocus_SF_1100S_CPV_28__330____2010_ | 413.2 | 1.502 | 275.1 | 2717.6 |
| 3 | SolFocus_SF_1100S_CPV_28__315____2010_ | 388.2 | 1.502 | 258.4 | 2552.9 |
| 4 | SunPower_SPR_315E_WHT__2007__E__ | 315.1 | 1.631 | 193.2 | 1908.4 |
| 5 | Panasonic_VBHN235SA06B__2013_ | 238.8 | 1.260 | 189.5 | 1872.5 |


**Top inversores (CEC):**
| Rank | Nombre | Paco [kW] | Eficiencia | N inversores | Score |
| --- | --- | --- | --- | --- | --- |
| 1 | TMEIC__PVH_L3200GR__600V_ | 3127.4 | 0.986 | 1 | 0.983 |
| 2 | TMEIC__PVH_L3200GR_E7__600V_ | 3127.4 | 0.986 | 1 | 0.983 |
| 3 | TMEIC__PVH_L3200GR_EG__600V_ | 3127.4 | 0.986 | 1 | 0.983 |
| 4 | Power_Electronics__FS3000CU15__690V_ | 3201.2 | 0.980 | 1 | 0.955 |
| 5 | INGETEAM_POWER_TECHNOLOGY_S_A___Ingecon_Sun_1560TL_U_B600_Indoor__450V_ | 1560.0 | 0.975 | 2 | 0.955 |


**Top combinaciones (simulacion local):**
| Rank | Modulo | Inversor | Energia anual [kWh] | Energia/m2 [kWh/m2] | PR | Score |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Kyocera_Solar_KS20__2008__E__ | INGETEAM_POWER_TECHNOLOGY_S_A___Ingecon_Sun_1560TL_U_B600_Indoor__450V_ | 6,539,017 | 662.0 | 1.419 | 661.990 |
| 2 | SunPower_SPR_315E_WHT__2007__E__ | INGETEAM_POWER_TECHNOLOGY_S_A___Ingecon_Sun_1560TL_U_B600_Indoor__450V_ | 4,823,458 | 489.2 | 1.522 | 489.225 |
| 3 | Panasonic_VBHN235SA06B__2013_ | INGETEAM_POWER_TECHNOLOGY_S_A___Ingecon_Sun_1560TL_U_B600_Indoor__450V_ | 4,797,004 | 486.2 | 1.541 | 486.226 |
| 4 | SolFocus_SF_1100S_CPV_28__330____2010_ | INGETEAM_POWER_TECHNOLOGY_S_A___Ingecon_Sun_1560TL_U_B600_Indoor__450V_ | 4,126,895 | 418.2 | 0.913 | 418.204 |
| 5 | SolFocus_SF_1100S_CPV_28__315____2010_ | INGETEAM_POWER_TECHNOLOGY_S_A___Ingecon_Sun_1560TL_U_B600_Indoor__450V_ | 3,911,140 | 396.3 | 0.921 | 396.340 |


### 4. Configuracion del Array

| Parametro | Valor |
|-----------|-------|
| Modulos por string | 44 |
| Strings en paralelo | 3,118 |
| Total de modulos | 137,192 |
| Numero de inversores | 2 |
| Inclinacion (tilt) | 10.0 |
| Azimut | 0.0 (Norte) |

### 5. Capacidad del Sistema

| Parametro | Valor |
|-----------|-------|
| Capacidad DC nominal | 4,050.00 kWp |
| Capacidad AC nominal | 3,118.50 kW |
| Area total disponible | 15,200 m2 |
| Area utilizada | 9,878 m2 |

### 6. Produccion Energetica

| Metrica | Valor |
|---------|-------|
| Energia anual AC | 6.539 GWh |
| Energia anual DC | 8.045 GWh |
| Factor de capacidad | 23.9% |
| Performance Ratio | 141.9% |
| Yield especifico | 2,361 kWh/kWp/ano |
| Horas equivalentes | 2,097 h/ano |

### 7. Estadisticas de Potencia

| Metrica | Valor |
|---------|-------|
| Potencia AC maxima | 2,694.9 kW |
| Potencia AC media | 744.5 kW |
| Dia de maxima energia | 2024-09-13 (22,617 kWh) |
| Instante de maxima potencia | 2024-01-03 15:45:00+00:00 |
| Horas con produccion | 4,312 h/ano |

### 8. Perdidas del Sistema

| Tipo de perdida | Valor |
|-----------------|-------|
| Total | 13.6% |

### 9. Energia Mensual

| Mes | Energia [kWh] |
|-----|---------------|
| 2024-01 | 522,036 |
| 2024-02 | 434,884 |
| 2024-03 | 569,898 |
| 2024-04 | 530,623 |
| 2024-05 | 533,612 |
| 2024-06 | 535,504 |
| 2024-07 | 563,878 |
| 2024-08 | 620,133 |
| 2024-09 | 595,265 |
| 2024-10 | 602,732 |
| 2024-11 | 532,899 |
| 2024-12 | 497,554 |

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
*Generado automaticamente - 2026-03-22 00:11:28*
