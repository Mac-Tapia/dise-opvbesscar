# Informe de generacion solar fotovoltaica

Proyecto: pvbesscar - Iquitos, Peru
Modulo OE2: Dimensionamiento y perfil horario de generacion solar
Archivo base canónico: `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv`
Reporte de verificacion OE2: `docs/REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md`

## 1. Objetivo

El objetivo del procedimiento fue construir un perfil horario anual de generacion solar fotovoltaica para Iquitos, Peru, utilizable por los modelos BESS, cargadores EV y agentes de aprendizaje por refuerzo. El resultado principal es una serie de 8,760 registros horarios con potencia, energia, irradiancia, temperatura, ahorro economico y reduccion indirecta de CO2.

## 2. Datos de entrada

| Elemento | Valor |
|---|---:|
| Ubicacion | Iquitos, Peru |
| Latitud | -3.75 |
| Longitud | -73.25 |
| Altitud | 104 m s.n.m. |
| Zona horaria | America/Lima |
| Fuente meteorologica | PVGIS TMY |
| Resolucion temporal | 60 minutos |
| Periodo del perfil | 365 dias, 8,760 horas |
| GHI anual | 1,668.08 kWh/m2 |
| POA anual | 1,675.26 kWh/m2 |

Nota: el perfil esta etiquetado como 2024, pero usa un ano meteorologico tipico de 365 dias. Por eso el rango horario validado es `2024-01-01 00:00:00-05:00` a `2024-12-30 23:00:00-05:00`, equivalente a 365 x 24 = 8,760 horas.

## 3. Configuracion del sistema fotovoltaico

| Parametro | Valor |
|---|---:|
| Capacidad DC nominal | 4,162.00 kWp |
| Capacidad AC nominal | 3,201.00 kW |
| Modulo seleccionado | Jinko_Tiger_Neo_JKM580N_72HL4_BDV__PVWatts_ |
| Inversor seleccionado | Eaton__Xpert1670 |
| Modulos por string | 14 |
| Strings en paralelo | 512 |
| Total de modulos | 7,175 |
| Numero de inversores | 2 |
| Inclinacion | 10.0 grados |
| Azimut | 0.0 grados, orientacion norte |
| Area total disponible | 20,637 m2 |
| Area utilizada | 18,534.83 m2 |
| Factor de diseno | 0.70 |

## 4. Procedimiento de generacion del perfil solar

El procedimiento usado para construir el dataset fue el siguiente:

1. Se definio la ubicacion del proyecto en Iquitos, Peru, con coordenadas, altitud y zona horaria local.
2. Se tomaron datos meteorologicos PVGIS TMY con irradiancia global horizontal, temperatura ambiente y velocidad de viento.
3. Se convirtio la irradiancia horizontal a irradiancia en plano del arreglo fotovoltaico usando el modelo de transposicion Perez.
4. Se configuro el arreglo fotovoltaico con inclinacion de 10 grados y azimut norte.
5. Se aplico el modelo de desempeno fotovoltaico con parametros de modulo e inversor.
6. Se calculo la potencia AC horaria disponible en el punto de salida del inversor.
7. Se convirtio potencia a energia por intervalo horario mediante:

```text
E_hora [kWh] = P_AC [kW] x 1 h
```

8. Se calcularon variables derivadas para integracion con CityLearn y OE3:

```text
pv_kwh = ac_energy_kwh
pv_kw  = ac_power_kw
CO2 evitado [kg] = energia solar [kWh] x 0.4521 kg CO2/kWh
ahorro solar [S/] = energia solar [kWh] x tarifa horaria aplicada
```

9. Se exportaron archivos horarios, diarios, mensuales y perfiles representativos.
10. Se valido integridad temporal, columnas, rangos fisicos, limpieza, duplicados y compatibilidad con los agentes RL.

## 5. Validacion del dataset

| Criterio | Resultado |
|---|---|
| Filas horarias | 8,760 |
| Cobertura temporal | 100% anual, 365 x 24 horas |
| Columnas principales | GHI, temperatura, viento, POA, potencia AC, energia AC, CO2 evitado |
| Valores faltantes criticos | No reportados |
| Duplicados temporales | No |
| Compatibilidad RL | Aprobada |
| Estado | Production ready |

Validacion complementaria 30 May 2026: `python -m pytest tests -v -ra` reporto 106 passed; `python scripts/generate_oe2_datasets.py --loader-only` regenero `data/iquitos_ev_mall/dataset_config_v7.json` con `ready_for_citylearn_v2 = true`.

## 6. Resultados anuales descriptivos

| Indicador | Valor |
|---|---:|
| Energia anual AC | 5,819,332 kWh |
| Energia anual AC | 5,819.33 MWh |
| Energia anual AC | 5.819 GWh |
| Potencia media anual, todas las horas | 664.31 kW |
| Potencia media en horas con produccion | 1,366.36 kW |
| Potencia maxima AC | 3,245.95 kW |
| Fecha/hora de potencia maxima | 2024-10-18 11:00:00-05:00 |
| Horas con produccion | 4,259 h |
| Horas sin produccion | 4,501 h |
| Porcentaje de horas con produccion | 48.62% |
| Factor de capacidad | 20.75% |
| Performance Ratio | 83.46% |
| Yield especifico | 1,398.21 kWh/kWp-ano |
| Horas equivalentes | 1,817.97 h/ano |
| Perdidas totales estimadas | 13.62% |

## 7. Resultados ambientales y economicos

| Indicador | Valor |
|---|---:|
| Factor CO2 red Iquitos | 0.4521 kg CO2/kWh |
| Reduccion indirecta anual de CO2 | 2,630,920 kg CO2 |
| Reduccion indirecta anual de CO2 | 2,630.92 tCO2 |
| Ahorro solar anual estimado | S/ 1,629,413.07 |

La reduccion es indirecta porque cada kWh generado por el sistema fotovoltaico evita importar energia equivalente de la red termica de Iquitos.

## 8. Resultados diarios descriptivos

| Indicador diario | Valor |
|---|---:|
| Media diaria | 15,943.38 kWh/dia |
| Mediana diaria | 16,225.08 kWh/dia |
| Desviacion estandar diaria | 3,484.97 kWh/dia |
| Percentil 5 | 10,088.16 kWh/dia |
| Percentil 25 | 13,796.68 kWh/dia |
| Percentil 75 | 18,626.59 kWh/dia |
| Percentil 95 | 20,725.01 kWh/dia |
| Dia de maxima generacion | 2024-03-09 |
| Maxima energia diaria | 22,573.15 kWh |
| Dia de minima generacion | 2024-12-24 |
| Minima energia diaria | 3,020.29 kWh |

Dias con mayor generacion:

| Fecha | Energia diaria |
|---|---:|
| 2024-03-09 | 22,573.15 kWh |
| 2024-09-06 | 22,357.69 kWh |
| 2024-03-10 | 22,063.81 kWh |
| 2024-09-13 | 22,049.90 kWh |
| 2024-10-10 | 21,679.91 kWh |

Dias con menor generacion:

| Fecha | Energia diaria |
|---|---:|
| 2024-12-24 | 3,020.29 kWh |
| 2024-12-25 | 3,221.08 kWh |
| 2024-02-06 | 3,768.20 kWh |
| 2024-04-19 | 5,032.47 kWh |
| 2024-06-18 | 5,390.08 kWh |

## 9. Resultados mensuales

| Mes | Energia |
|---|---:|
| 2024-01 | 460,305 kWh |
| 2024-02 | 405,139 kWh |
| 2024-03 | 509,481 kWh |
| 2024-04 | 472,138 kWh |
| 2024-05 | 460,889 kWh |
| 2024-06 | 467,950 kWh |
| 2024-07 | 491,789 kWh |
| 2024-08 | 563,964 kWh |
| 2024-09 | 551,952 kWh |
| 2024-10 | 543,068 kWh |
| 2024-11 | 469,118 kWh |
| 2024-12 | 423,539 kWh |

Resumen mensual:

| Indicador mensual | Valor |
|---|---:|
| Promedio mensual | 484,944 kWh |
| Desviacion estandar mensual | 49,350 kWh |
| Mes de mayor generacion | 2024-08 |
| Generacion maxima mensual | 563,964 kWh |
| Mes de menor generacion | 2024-02 |
| Generacion minima mensual | 405,139 kWh |

La mayor generacion mensual se concentra en agosto, septiembre y octubre. Los menores valores se observan en febrero y diciembre.

## 10. Perfil horario promedio

| Hora | Energia media horaria | Energia anual acumulada en esa hora |
|---:|---:|---:|
| 06:00 | 92.17 kWh | 33,641 kWh |
| 07:00 | 639.61 kWh | 233,456 kWh |
| 08:00 | 1,253.87 kWh | 457,661 kWh |
| 09:00 | 1,758.34 kWh | 641,793 kWh |
| 10:00 | 2,109.71 kWh | 770,045 kWh |
| 11:00 | 2,278.25 kWh | 831,562 kWh |
| 12:00 | 2,232.65 kWh | 814,916 kWh |
| 13:00 | 2,016.02 kWh | 735,848 kWh |
| 14:00 | 1,662.82 kWh | 606,930 kWh |
| 15:00 | 1,178.40 kWh | 430,115 kWh |
| 16:00 | 610.60 kWh | 222,869 kWh |
| 17:00 | 110.95 kWh | 40,496 kWh |

La generacion se concentra entre 06:00 y 17:00. El maximo promedio ocurre alrededor de las 11:00, con 2,278.25 kWh por hora promedio.

## 11. Dias representativos

| Tipo de dia | Fecha | GHI diario | Energia diaria |
|---|---|---:|---:|
| Maxima generacion | 2024-03-09 | 6,697.85 Wh/m2 | 22,573.15 kWh |
| Despejado | 2024-11-21 | 6,786.75 Wh/m2 | 20,968.80 kWh |
| Intermedio | 2024-04-28 | 4,553.70 Wh/m2 | 16,619.66 kWh |
| Nublado | 2024-12-24 | 896.85 Wh/m2 | 3,020.29 kWh |

Estos perfiles permiten validar que el dataset captura dias de alta irradiancia, dias intermedios y dias nublados, lo cual es necesario para entrenar agentes que respondan a variabilidad solar.

## 12. Interpretacion tecnica

El sistema fotovoltaico presenta un desempeno consistente con una ubicacion tropical: generacion distribuida a lo largo de todo el ano, sin estacionalidad extrema, pero con variabilidad diaria relevante por nubosidad. La energia anual de 5.819 GWh permite representar una fuente renovable de escala suficiente para alimentar parcialmente la demanda del centro comercial, cargadores EV y estrategias de carga/descarga del BESS.

La potencia maxima de 3,245.95 kW esta alineada con la capacidad AC nominal de 3,201 kW, considerando condiciones horarias favorables y el modelo de conversion usado. El factor de capacidad de 20.75% y el performance ratio de 83.46% son tecnicamente razonables para un sistema PV bien orientado en Iquitos.

Desde el punto de vista ambiental, la generacion solar evita aproximadamente 2,630.92 tCO2/ano al desplazar energia de la red termica. Este valor sirve como base para las metricas de reduccion indirecta empleadas posteriormente en OE3.

## 13. Archivos producidos

| Archivo | Contenido |
|---|---|
| `pv_generation_citylearn2024.csv` | Dataset canónico para CityLearn |
| `pv_generation_hourly_citylearn_v2.csv` | Perfil horario ampliado con energia, potencia, irradiancia, ahorro y CO2 |
| `pv_daily_energy.csv` | Energia diaria |
| `pv_monthly_energy.csv` | Energia mensual |
| `pv_dias_representativos.csv` | Perfiles horarios de dias representativos |
| `solar_results.json` | Resumen tecnico del sistema |
| `CERTIFICACION_SOLAR_DATASET_2024.json` | Validacion del dataset |
| `solar_technical_report.md` | Reporte tecnico base |

## 14. Conclusion

El procedimiento genero un perfil solar horario completo, validado y apto para simulacion energetica y entrenamiento RL. El sistema fotovoltaico alcanza 5.819 GWh/ano, con 4,259 horas de produccion, potencia maxima de 3.246 MW y reduccion indirecta de 2,630.92 tCO2/ano. Los resultados descriptivos muestran una produccion diaria media de 15.94 MWh/dia, con maximos superiores a 22 MWh/dia en dias despejados y reducciones fuertes en dias nublados. Por tanto, el dataset solar es adecuado para representar la variabilidad operativa que debe gestionar el BESS y los agentes de carga inteligente.
