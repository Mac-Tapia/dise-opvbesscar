# OE1 - Ubicacion estrategica (datos reales 4.6.2)

Este documento desarrolla el Objetivo Especifico 1 con los datos reales del
numeral 4.6.2 de `tesisvefinal.pdf` y muestra el vinculo directo con los
calculos del OE2 ya ejecutados en el proyecto.

## Datos reales extraidos de 4.6.2 (tesisvefinal)

| Indicador (Tabla 18 / 4.6.2) | Valor | Evidencia |
| --- | --- | --- |
| Puntos evaluados | 10 ubicaciones | Tabla 18 (4.6.2) |
| Infraestructura EV existente | No se identificaron puntos formales | Tabla 18 |
| Area techada disponible | 20,637 m2 | Figura 35 / Tabla 18 |
| Area de estacionamiento | 957 m2 | Tabla 18 |
| Distancia a SET Santa Rosa | 60 m | Figura 35 / Texto 4.6.2 |
| Motos en hora pico | 900 unidades | Visita 19/10/2025 19:00 (Fig. 29-30) |
| Mototaxis en hora pico | 130 unidades | Visita 19/10/2025 19:00 (Fig. 31) |
| Tiempo de permanencia | >= 4 horas | Texto 4.6.2 |

## Tabla 10 - Puntos de ubicacion evaluados (datos reales)

| Item | Lugar | Area techada (m2) | Dist red MT (m) | Dist SET (m) | Motos+mototaxis | Tiempo (h) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | Empresa distribuidora de energia Electro Oriente S.A. | 14000 | 40 | 40 | 200 | 4 |
| 2 | Complejo deportivo Champios | 8000 | 40 | 1300 | 300 | 4 |
| 3 | Aeropuerto de Iquitos | 6000 | 500 | 4400 | 400 | 2 |
| 4 | Centro comercial Precios UNO | 2500 | 45 | 580 | 100 | 2 |
| 5 | Universidad Nacional de Amazonia sede central | 10000 | 10 | 1300 | 200 | 2 |
| 6 | Grifo Atenas | 368 | 70 | 5300 | 500 | 0.20 |
| 7 | Mall de Iquitos | 20637 | 60 | 60 | 900 | 4 |
| 8 | Universidad nacional Amazonia - Zungarococha | 8300 | 200 | 16000 | 100 | 4 |
| 9 | Escuela tecnica PNP | 21000 | 100 | 9000 | 200 | 4 |
| 10 | Complejo CNI | 3500 | 100 | 2200 | 300 | 4 |

Nota: valores transcritos de la Tabla 10 del PDF; el valor "4.4" se corrigio a 4400 m por error de digitacion
tal como aparece en la columna distancia a SET.
CSV: `data/interim/oe1/ubicacion_candidatos.csv`.

## Vinculo directo con OE2 (dimensionamiento ya calculado)

1) Area techada -> FV (OE2)
   - La superficie de 20,637 m2 es la base del dimensionamiento PV.
   - Se aplica factor de diseno 0.65: area util 13,413.344 m2.
   - Resultado OE2 (solar):
     - DC: 2,591.15 kWp
     - AC: 2,500.00 kW
     - Energia anual: 3,298,753 kWh
   - Fuente: `data/interim/oe2/solar/solar_results.json`

2) Flota real en hora pico -> cargadores (OE2)
   - 900 motos y 130 mototaxis definen la demanda de carga.
   - El horario de permanencia >= 4 h sustenta la ventana 18:00-22:00.
   - Resultado OE2 (chargers):
     - 31 cargadores, 124 sockets
     - Energia diaria EV: 644.4 kWh
   - Fuente: `data/interim/oe2/chargers/chargers_results.json`

3) Ubicacion y red -> BESS (OE2)
   - Proximidad a SET Santa Rosa (60 m) soporta conexion tecnica.
   - BESS se dimensiona para deficit EV nocturno con SOC minimo 20%.
   - Resultado OE2 (bess):
     - Capacidad: 740 kWh
     - Potencia: 370 kW
     - PV diaria: 9,016 kWh
   - Fuente: `data/interim/oe2/bess/bess_results.json`

## Trazabilidad en configuracion del proyecto

Los datos reales del OE1 se reflejan en:
- `configs/default.yaml` -> `oe1.site.*` (area techada, estacionamiento,
  distancia a subestacion, flota en hora pico, permanencia).

Esto asegura que el OE1 alimenta directamente al OE2 y mantiene coherencia
con la Tabla 9 (operacionalizacion de variables).
