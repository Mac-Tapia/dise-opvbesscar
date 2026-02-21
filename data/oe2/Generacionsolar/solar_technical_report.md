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
| Modulos por string | 31 |
| Strings en paralelo | 6,472 |
| Total de modulos | 200,632 |
| Numero de inversores | 2 |
| Inclinacion (tilt) | 10.0 |
| Azimut | 0.0 (Norte) |

### 5. Capacidad del Sistema

| Parametro | Valor |
|-----------|-------|
| Capacidad DC nominal | 4,050.00 kWp |
| Capacidad AC nominal | 3,201.00 kW |
| Area total disponible | 20,637 m2 |
| Area utilizada | 14,446 m2 |

### 6. Produccion Energetica

| Metrica | Valor |
|---------|-------|
| Energia anual AC | 8.293 GWh |
| Energia anual DC | 11.804 GWh |
| Factor de capacidad | 29.6% |
| Performance Ratio | 122.8% |
| Yield especifico | 2,048 kWh/kWp/ano |
| Horas equivalentes | 2,591 h/ano |

### 7. Estadisticas de Potencia

| Metrica | Valor |
|---------|-------|
| Potencia AC maxima | 2,886.7 kW |
| Potencia AC media | 946.6 kW |
| Dia de maxima energia | 2024-04-23 (26,620 kWh) |
| Instante de maxima potencia | 2024-01-01 10:00:00-05:00 |
| Horas con produccion | 4,259 h/ano |

### 8. Perdidas del Sistema

| Tipo de perdida | Valor |
|-----------------|-------|
| Total | 13.6% |

### 9. Energia Mensual

| Mes | Energia [kWh] |
|-----|---------------|
| 2024-01 | 676,769 |
| 2024-02 | 590,946 |
| 2024-03 | 717,204 |
| 2024-04 | 668,941 |
| 2024-05 | 697,094 |
| 2024-06 | 687,133 |
| 2024-07 | 719,079 |
| 2024-08 | 759,620 |
| 2024-09 | 728,083 |
| 2024-10 | 741,874 |
| 2024-11 | 679,244 |
| 2024-12 | 626,526 |

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
*Generado automaticamente - 2026-02-20 21:13:11*
