# Reporte: Costos Tarifarios y Estabilidad de Red — OE3

**Componentes del reward multiobjetivo CO2_DUAL_FOCUS v8.1:**
| Componente     | Peso | Descripcion |
|----------------|------|-------------|
| W_DIRECT_CO2   | 0.20 | CO2 directa (ICE→EV) |
| W_INDIRECT_CO2 | 0.30 | CO2 indirecta (grid import × 0.4521) |
| W_EV_COMPLETE  | 0.35 | Satisfaccion EV (motos + mototaxis) |
| W_BESS_SOLAR   | 0.07 | BESS carga desde solar |
| W_SOLAR        | 0.04 | Autoconsumo PV |
| **W_GRID_STABLE** | **0.02** | **Suavizado rampas grid_import** |
| **W_COST**     | **0.02** | **Costo tarifario OSINERGMIN HP/HFP** |

Tarifa HP (18-23h): **0.45 S./kWh** | Tarifa HFP: **0.28 S./kWh**
Factor CO₂ red Iquitos: **0.4521 kg CO₂/kWh**

---

## 1. Costos Energéticos (S./año)

| Métrica                                |              A2C |              PPO |              SAC |
|----------------------------------------|------------------|------------------|------------------|
| Costo total medio (S./año)             |        2,380,936 |        2,389,574 |        2,440,398 |
| Costo HP medio 18-23h (S./año)         |          728,102 |          732,810 |          759,396 |
| Costo HFP medio (S./año)               |        1,652,834 |        1,656,764 |        1,681,003 |
| % costo en HP                          |      72810199.6% |      73281018.6% |      75939586.5% |
| r_cost medio (reward normalizado)      |          -0.3918 |          -0.3913 |          -0.3873 |

## 2. Estabilidad de Red (W_GRID_STABLE)

| Métrica                                |              A2C |              PPO |              SAC |
|----------------------------------------|------------------|------------------|------------------|
| r_grid_stable medio (reward)           |          -0.1498 |          -0.1555 |          -0.1566 |
| Rampa media |Δgrid_import| (kWh/h)     |           224.81 |           233.41 |           234.98 |
| Rampa std |Δgrid_import| (kWh/h)       |           265.12 |           273.17 |           285.24 |
| CV grid_import por episodio            |           0.8563 |           0.8703 |           0.9190 |
| Grid peak maximo (kWh/h)               |           2779.8 |           2820.8 |           2745.7 |
| Ratio pico/valle                       |              nan |              nan |              nan |

## 3. Exportación Solar a Red Iquitos (F6d)

| Agente | Export solar medio (kWh/año) | CO₂ desplazado (kg/año) | % generacion solar |
|--------|------------------------------|------------------------|--------------------|
| A2C |                      513,546 |                232,174 |                8.8% |
| PPO |                      525,445 |                237,554 |                9.0% |
| SAC |                      510,717 |                230,895 |                8.8% |

## 4. Pruebas estadísticas — Costo total (S./año)

- **A2C vs PPO**: U=1298, p=9.893e-01 ns | Δ=-8,637.5 (A2C menor)
- **A2C vs SAC**: U=1242, p=8.253e-01 ns | Δ=-59,462.1 (A2C menor)
- **PPO vs SAC**: U=1234, p=7.832e-01 ns | Δ=-50,824.6 (PPO menor)

## 5. Pruebas estadísticas — Estabilidad (r_grid_stable)

- **A2C vs PPO**: U=1155, p=3.318e-01 ns | Δ=+0.0 (A2C mayor)
- **A2C vs SAC**: U=1981, p=1.651e-06 ✓ sig. | Δ=+0.0 (A2C mayor)
- **PPO vs SAC**: U=1708, p=3.307e-03 ✓ sig. | Δ=+0.0 (PPO mayor)

## 6. Interpretación multiobjetivo

Los pesos W_COST=0.02 y W_GRID_STABLE=0.02 actúan como restricciones blandas:

- **W_COST (0.02):** Penaliza consumo de red en HP (18-23h) → desplazamiento de carga a HFP. El agente aprende a cargar BESS y EV fuera de horas punta para reducir costo.
- **W_GRID_STABLE (0.02):** Penaliza rampas bruscas en grid_import → suaviza la curva de demanda a la red diesel aislada de Iquitos, reduciendo estrés en generadores.
- La exportacion solar (F6d) desplaza generacion diesel en la red Iquitos para otros consumidores, multiplicando el impacto ambiental del proyecto.
- Aunque con pesos menores que CO₂ (0.50) y EV (0.35), estos componentes son necesarios para la viabilidad operativa del sistema.