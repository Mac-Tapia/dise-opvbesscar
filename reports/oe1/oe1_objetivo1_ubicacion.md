# OE1 - Ubicación estratégica (datos reales 4.6.2)

Documento del Objetivo Específico 1 (datos reales del numeral 4.6.2 de `tesisvefinal.pdf`), vinculado con los cálculos OE2 vigentes.

## Datos reales extraídos (Tabla 18 / 4.6.2)

| Indicador | Valor | Evidencia |
| --- | --- | --- |
| Puntos evaluados | 10 ubicaciones | Tabla 18 |
| Infraestructura EV existente | No se identificaron puntos formales | Tabla 18 |
| Área techada disponible | 20,637 m2 | Figura 35 / Tabla 18 |
| Área de estacionamiento | 957 m2 | Tabla 18 |
| Distancia a SET Santa Rosa | 60 m | Figura 35 / texto 4.6.2 |
| Motos en hora pico | 900 unidades | Visita 19/10/2025 19:00 (Fig. 29-30) |
| Mototaxis en hora pico | 130 unidades | Visita 19/10/2025 19:00 (Fig. 31) |
| Tiempo de permanencia | ≥ 4 horas | Texto 4.6.2 |

## Tabla 10 - Puntos de ubicación evaluados

| Ítem | Lugar | Área techada (m2) | Dist red MT (m) | Dist SET (m) | Motos+mototaxis | Tiempo (h) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | Empresa distribuidora de energía Electro Oriente S.A. | 14000 | 40 | 40 | 200 | 4 |
| 2 | Complejo deportivo Champios | 8000 | 40 | 1300 | 300 | 4 |
| 3 | Aeropuerto de Iquitos | 6000 | 500 | 4400 | 400 | 2 |
| 4 | Centro comercial Precios UNO | 2500 | 45 | 580 | 100 | 2 |
| 5 | Universidad Nacional de Amazonia sede central | 10000 | 10 | 1300 | 200 | 2 |
| 6 | Grifo Atenas | 368 | 70 | 5300 | 500 | 0.20 |
| 7 | Mall de Iquitos | 20637 | 60 | 60 | 900 | 4 |
| 8 | Universidad nacional Amazonia - Zungarococha | 8300 | 200 | 16000 | 100 | 4 |
| 9 | Escuela técnica PNP | 21000 | 100 | 9000 | 200 | 4 |
| 10 | Complejo CNI | 3500 | 100 | 2200 | 300 | 4 |

Nota: Tabla 10 transcrita; la distancia 4.4 km al SET se corrigió a 4400 m. CSV: `data/interim/oe1/ubicacion_candidatos.csv`.

## Vínculo directo con OE2 (dimensionamiento vigente)

1. **Área techada → FV (OE2).** La superficie de 20,637 m² y factor de diseño 0.65 dan área útil 13,414 m². Resultado OE2 (solar): **DC 2,591 kWp** (8,224 módulos SunPower SPR-315E), **AC 2,500 kW** (inversor Sungrow SG2500U), energía anual **3,299 MWh** (`data/interim/oe2/solar/solar_results.json`).
2. **Flota pico → cargadores (OE2).** 900 motos + 130 mototaxis, permanencia ≥4 h, ventana 18:00-22:00. Resultado OE2 (chargers): **33 cargadores**, **129 sockets** (4 por cargador), potencia objetivo **310-340 kW**, energía diaria EV **567 kWh**, **927 vehículos efectivos/día** (`data/interim/oe2/chargers/chargers_results.json`).
3. **Ubicación y red → BESS (OE2).** Distancia 60 m a SET Santa Rosa soporta conexión. BESS dimensionado para autonomía 4h: capacidad **740 kWh**, potencia **370 kW**, DoD 90%, eficiencia roundtrip 95%, SOC mínimo 10% (`data/interim/oe2/bess/bess_results.json`).

## Trazabilidad en configuración

Los datos OE1 se reflejan en `configs/default.yaml` (`oe1.site.*`), alimentan OE2 y mantienen coherencia con la Tabla 9 (operacionalización de variables).
