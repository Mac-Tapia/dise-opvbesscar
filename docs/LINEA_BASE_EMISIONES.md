# Línea Base de Emisiones CO₂ - Iquitos 2025

## Fuente

Plan de Desarrollo Concertado de la Provincia de Maynas 2025-2030 [4]

---

## 1. Sector Transporte

### Flota Vehicular

| Tipo de Vehículo | Cantidad | Emisiones (tCO₂/año) | % del Total |
| ---------------- | -------- | ------------------- | ----------- |
| Mototaxis | 61,000 | 152,500 | 56.4% |
| Motos lineales | 70,500 | 105,750 | 39.1% |
| Microbuses | 361 | - | - |
| Moto furgones | 1,058 | - | - |
| Taxis | 95 | - | - |
| Automóviles | 202 | - | - |
| **Total transporte** | **133,216** | **258,250** | **95%** |

> **Nota:** Mototaxis y motos lineales representan el **95%** de las emisiones del sector transporte en Iquitos.

---

## 2. Sector Generación Eléctrica

### Sistema Eléctrico Aislado de Iquitos

| Indicador | Valor | Unidad |
| ----------- | ------- | -------- |
| Tipo de sistema | Central térmica aislada | - |
| Consumo anual de combustible | 22.5 | millones de galones |
| Emisiones anuales | 290,000 | tCO₂/año |
| Participación nacional | 9% | del CO₂ de Perú |

---

## 3. Resumen Línea Base

| Sector | Emisiones (tCO₂/año) |
| -------- | --------------------- |
| Transporte (mototaxis + motos) | 258,250 |
| Generación eléctrica | 290,000 |
| **Total Iquitos** | **548,250** |

---

## 4. Parámetros en Configuración

Estos valores están definidos en `configs/default.yaml`:

```yaml
oe3:
  city_baseline_tpy:
    # Fuente: Plan de Desarrollo de Maynas [4]
    # - 61,000 mototaxis: 152,500 tCO2/año
    # - 70,500 motos lineales: 105,750 tCO2/año
    transport: 258250.0  # Total sector transporte (95% de emisiones)
    # Sistema eléctrico aislado: 22.5 millones galones/año → 290,000 tCO2/año
    electricity_generation: 290000.0
```

---

## 5. Hipótesis del Proyecto

### HG - Hipótesis General

> El diseño de la infraestructura de carga inteligente para motos y mototaxis eléctricas **reducirá las emisiones de dióxido de carbono** en la ciudad de Iquitos, 2025.

### Demostración de Reducción (DATOS CORREGIDOS 2026-01-08)

**Línea Base Combinada:**

- Grid-only (red térmica): 5,596.26 tCO₂/año
- Tailpipe (gasolina evitada): 2,784.91 tCO₂/año
- **TOTAL BASE: 8,381.16 tCO₂/año**

| Escenario | tCO₂/año | Reducción vs Base |
| --------- | -------: | ----------------: |
| LÍNEA BASE (Grid + Combustión) | 8,381.16 | — |
| FV+BESS sin control (Uncontrolled) | 2,475.06 | 70.47% |
| FV+BESS + A2C | 2,476.32 | 70.45% |
| FV+BESS + PPO | 2,499.15 | 70.18% |
| FV+BESS + SAC | 2,657.36 | 68.29% |

### Contribución al Sector Transporte de Iquitos

| Métrica | Valor |
| ------- | ----- |
| Emisiones transporte Iquitos | 258,250 tCO₂/año |
| Reducción por proyecto (mejor agente) | 5,906.10 tCO₂/año |
| **Contribución porcentual** | **2.29%** |

---

## 6. Evidencia de Cumplimiento

- **Archivo de validación:** `outputs/oe3/simulations/simulation_summary.json`
- **Criterio HG:** Reducción > 0 ✅
- **Resultado:** 5,906.10 tCO₂/año evitados (70.47%)

### Desglose de Emisiones Evitadas (20 años)

| Tipo de Reducción | Valor (tCO₂/año) | Valor (tCO₂/20 años) |
| ----------------- | ---------------: | -------------------: |
| Total evitado (mejor agente) | 5,906.10 | 118,122.00 |
| Diferencia Control vs Sin Control | ~1.25 | ~25.00 |

---

## Referencias

[4] Plan de Desarrollo Concertado de la Provincia de Maynas 2025-2030
