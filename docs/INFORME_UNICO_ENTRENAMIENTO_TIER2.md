# INFORME ÚNICO ENTRENAMIENTO TIER 2 (18-19 Ene 2026)

## Resumen
- Se ejecutaron corridas TIER 2 para PPO, SAC (2 episodios) y un intento de A2C.
- Los registros muestran recompensas planas y cero producción solar → los
  - agentes no aprendieron con la señal actual.
- No se generaron `results_summary.json`; las únicas métricas consolidadas
  - están en `analyses/oe3/training/*_training_metrics.csv`.

## Objetivos del proyecto
- OE3: Control CityLearn v2 con carga EV y BESS; minimizar CO₂ y stress de red
  - con operación multiobjetivo.
- TIER 2: Replicar las mejoras de SAC (TIER 2) en PPO y A2C y validar
  - equivalencia en 2 episodios seriales.
- Función multiobjetivo (pesos balanceados actuales): CO2 0.35, Costo 0.25,
  - Solar 0.20, EV 0.15, Grid 0.05 (`COMIENZA_AQUI_TIER2_FINAL.md`).
- KPIs esperados (por agente, 2 episodios): CO₂ < 1.8–2.0M kg, Peak Import <
  - 250–290 kWh/h, Avg Reward 0.40–0.65, Grid Stability 0.70–0.90.

## Reducción anual de CO₂ (infraestructura OE2, referencia)
- Reducción directa (gasolina → EV): **3,081.20 tCO₂/año**
- Reducción indirecta (PV+BESS desplaza red): **3,626.66 tCO₂/año**
- Reducción neta anual: **6,707.86 tCO₂/año**
- Emisiones EV si todo fuera red: 536.63 tCO₂/año
- Emisiones reales con PV+BESS: 2,501.49 tCO₂/año
- Origen: `reports/oe2/co2_breakdown/oe2_co2_breakdown.json` (capacidad diaria
  - 2,679 motos + 382 mototaxis, inversor Eaton Xpert1670 regenerado).

## Resultados observados
  | Agente | Pasos | Mean Reward | CO2 episodio (kg) | Grid (kWh) | Solar (kWh) | Fuente |  
| --- | --- | --- | --- | --- | --- | --- |
  ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
  ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
  | A2C | — | — | — | — | — | Sin métricas... |  

## Conclusión
- PPO y SAC no muestran aprendizaje: reward constante, CO2 y grid sin mejora,
  - solar = 0.
- A2C no produjo resumen de métricas; no hay evidencia de convergencia.
- Se requiere ajustar recompensas/observables antes de nuevos entrenamientos.

## Cumplimiento de objetivos (estado actual)
- Objetivo OE3 (minimizar CO₂ con control RL): **No cumplido**. Métricas planas
  - y sin autoconsumo solar.
- Objetivo TIER 2 (equivalencia PPO/A2C vs SAC): **No verificado**. Faltan
  - resultados consolidados y A2C sin métricas finales.
- KPIs esperados: **No alcanzados**. CO₂ y Peak Import no mejoran, Grid
  - Stability no calculada.

## Procedimiento recomendado para cumplimiento
1. **Evaluar corridas actuales**
   - Ejecutar `python EVALUACION_METRICAS_COMPLETAS.py` y generar
     - `analyses/oe3/training/RESULTADOS_METRICAS_COMPLETAS.json`.
   - Exportar `results_summary.json` por agente en
     - `outputs/oe3/training/tier2_2ep_serial/` (o la ruta activa).
2. **Revisar señal de aprendizaje**
   - Ajustar recompensas: penalizar CO₂ pico/importación pico, incluir potencia
     - pico y reserva de SOC.
   - Ajustar observables: hora pico, SOC actual y target, colas por playa,
     - precio horario.
3. **Relanzar TIER 2**
   - Reentrenar A2C, PPO, SAC con las recompensas y observables corregidos (2
     - episodios seriales).
   - Registrar métricas post-entrenamiento (reward, CO₂, Peak Import, Grid
     - Stability, solar).
4. **Validar contra KPIs**
   - Comparar métricas obtenidas vs KPIs esperados.
   - Documentar en este informe las cifras finales y marcar cumplimiento/no
     - cumplimiento.
5. **Actualizar documentación**
   - Sincronizar `COMIENZA_AQUI_TIER2_FINAL.md` y
     - `COMPARATIVA_AGENTES_FINAL_TIER2.md` con los resultados finales.
   - Dejar trazabilidad de pesos de recompensa y cambios de observables para la
     - tesis.
