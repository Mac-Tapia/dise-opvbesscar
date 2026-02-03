# IQUITOS BASELINE CO₂ REFERENCE
## Valores Base para Comparativas de Reducción de CO₂
**Fecha: 2026-02-03 | Fuente: Plan de Desarrollo Provincia de Maynas + Sistema Eléctrico Aislado**

---

## 📊 SECTOR TRANSPORTE - FLOTA VEHICULAR

### Composición de Flota
| Tipo de Vehículo | Cantidad | % de Flota | Emisiones Anuales |
|---|---|---|---|
| **Mototaxis** | 61,000 | ~46% | 152,500 tCO₂/año |
| **Motos Lineales** | 70,500 | ~54% | 105,750 tCO₂/año |
| **TOTAL FLOTA** | **131,500** | **100%** | **258,250 tCO₂/año** |

### Contribución a Emisiones Totales
- **% de sector transporte:** 95% (responsables de casi todas las emisiones)
- **Emisiones promedio por vehículo:** 1.964 tCO₂/año

### Factor de Emisión (Derivado)
- **Mototaxis:** 152,500 / 61,000 = **2.50 tCO₂/vehículo/año**
- **Motos:** 105,750 / 70,500 = **1.50 tCO₂/vehículo/año**

---

## ⚡ SECTOR GENERACIÓN ELÉCTRICA - SISTEMA AISLADO

### Configuración del Sistema
- **Tipo:** Sistema aislado (NO conectado a grid nacional)
- **Tecnología:** Central térmica (combustibles fósiles)
- **Operador:** ELECTROPERU / Distribuidor local

### Consumo de Combustible Fósil (Anual)
| Concepto | Valor |
|---|---|
| **Consumo anual total** | 22.5 millones de galones |
| **Emisiones generadas** | 290,000 tCO₂/año |

### Factor de Emisión (Derivado)
- **Factor de emisión eléctrica:** 290,000 tCO₂/año ÷ 22.5M galones = **0.0129 tCO₂/galón**
- **Equivalente en kWh:** Asumiendo rendimiento térmico de ~35% (típico para diesel)
  - 22.5M galones × 38.9 kWh/galón × 35% = ~306,000 MWh/año
  - **Factor eléctrico:** 290,000 tCO₂ / 306,000 MWh = **0.948 kgCO₂/kWh**
  - **Factor eléctrico simplificado:** ~**0.95 kgCO₂/kWh** o **0.4521 kgCO₂/kWh** (usando dato conservador)

---

## 🔴 COMPARATIVA: LÍNEA BASE (ACTUAL)

### Escenario Actual (Sin Control EV)
**Flota EV OE2/OE3:** 2,912 motos + 416 mototaxis = **3,328 vehículos eléctricos**

#### A) Emisiones si fueran vehículos de combustión (REDUCCIÓN DIRECTA)
Si estos 3,328 vehículos siguieran siendo a gasolina:

| Tipo | Cantidad | Factor | Emisiones/año |
|---|---|---|---|
| Mototaxis | 416 | 2.50 tCO₂/veh | **1,040 tCO₂/año** |
| Motos | 2,912 | 1.50 tCO₂/veh | **4,368 tCO₂/año** |
| **TOTAL (BASELINE)** | **3,328** | **promedio 1.92** | **5,408 tCO₂/año** |

**Interpretación:** Si los 3,328 vehículos EV fuesen a gasolina, generarían ~5,408 tCO₂/año en el transporte.

#### B) Emisiones si la carga viniera 100% de red térmica (LÍNEA BASE GRID)
- Demanda EV estimada: 50 kW constante × 13 h/día × 365 días = **237,250 kWh/año**
- Factor eléctrico Iquitos: 0.4521 kgCO₂/kWh (DATO CRÍTICO USADO EN OE3)
- **Emisiones desde grid:** 237,250 kWh × 0.4521 kg/kWh = **1,073 tCO₂/año**

**Interpretación:** Si toda la carga de EVs viniera del grid térmico, generaría ~1,073 tCO₂/año en electricidad.

---

## 🟢 OBJETIVOS DE REDUCCIÓN (OE2/OE3)

### Reducción Directa (COMPARATIVA 1)
**Evitar combustión de gasolina:** 5,408 tCO₂/año → Meta: Reemplazar con energía limpia

Estrategia: Cargar EVs desde PV + BESS (preferentemente)
- Objetivo: 100% de carga desde renovables
- **Reducción posible:** 5,408 tCO₂/año evitados vs. combustión

### Reducción Indirecta (COMPARATIVA 2)
**Evitar emisiones de grid térmico:** 1,073 tCO₂/año → Meta: Maximizar PV directo

Estrategia: Autoconsumo solar en horas de carga
- Generación solar disponible: ~8,030,119 kWh/año (4,162 kWp × ~1,930 h/kWp)
- Demanda mall + EV: ~237,250 + ~876,000 (mall) = ~1,113,250 kWh/año
- **Cobertura potencial:** 8,030,119 / 1,113,250 = ~7.2x demanda
- **Reducción posible (indirecta):** 1,073 tCO₂/año × (cobertura solar %)

### Reducción Total (COMPARATIVA 3)
**Suma de ambas reducciones:**

$$\text{Reducción Total} = \text{Directa (vs. gasolina)} + \text{Indirecta (vs. grid)}$$
$$= 5,408 + 1,073 = 6,481 \text{ tCO₂/año máximo}$$

---

## 📈 MÉTRICAS DE COMPARATIVA

### Baseline Global Iquitos (Transporte + Electricidad)
| Sector | Emisiones Base | % del Total |
|---|---|---|
| **Transporte (flota total)** | 258,250 tCO₂/año | 47.1% |
| **Electricidad (todo el sistema)** | 290,000 tCO₂/año | 52.9% |
| **TOTAL IQUITOS** | **548,250 tCO₂/año** | **100%** |

### Impacto OE2/OE3 en Iquitos
- **3,328 vehículos EV:** 
  - Reducción potencial directa: **5,408 tCO₂/año** (~2.1% del transporte)
  - Reducción potencial indirecta: **1,073 tCO₂/año** (~0.4% de electricidad)
  - **Reducción total máxima:** 6,481 tCO₂/año (~1.2% del total Iquitos)

---

## 🔗 VINCULACIÓN CON OE3 (simulate.py)

### Cálculo de CO₂ en Simulación (3-COMPONENTES)

**Componente 1: CO₂ EMITIDO (indirecto por grid)**
```
co2_emitido_grid = grid_import_kwh × 0.4521 kg/kWh
```
- Usa factor: **0.4521 kgCO₂/kWh** (sistema térmico Iquitos)
- Línea base anual: ~1,073 tCO₂/año

**Componente 2: REDUCCIONES INDIRECTAS (evita grid)**
```
reducciones_indirectas = (solar_aprovechado + bess_descargado) × 0.4521 kg/kWh
```
- Objetivo: Maximizar solar directo
- Máximo teórico: ~8,030,119 kWh × 0.4521 = ~3,631 tCO₂/año evitados

**Componente 3: REDUCCIONES DIRECTAS (evita gasolina)**
```
reducciones_directas = total_ev_cargada × 2.146 kg/kWh
```
- Usa factor: **2.146 kgCO₂/kWh** (equivalencia vs. combustión)
- Calculado como: 237,250 kWh × 2.146 = ~509 tCO₂/año

---

## ✅ VALORES CRÍTICOS PARA VALIDACIÓN

### Factores de Emisión (FUENTE DE VERDAD)
| Concepto | Valor | Unidad | Fuente |
|---|---|---|---|
| **Grid Iquitos (indirecto)** | 0.4521 | kgCO₂/kWh | Sistema térmico aislado |
| **EV vs. Gasolina (directo)** | 2.146 | kgCO₂/kWh | Equivalencia combustión |
| **Mototaxi (anual)** | 2.50 | tCO₂/veh/año | 152,500 ÷ 61,000 |
| **Moto (anual)** | 1.50 | tCO₂/veh/año | 105,750 ÷ 70,500 |

### Demandas (LÍNEA BASE OE3)
| Componente | Valor | Unidad |
|---|---|---|
| **EV demand (constante)** | 50 | kW |
| **EV demand (anual)** | 237,250 | kWh |
| **Mall demand (anual)** | 876,000 | kWh (estimado) |
| **Total demand** | 1,113,250 | kWh |

### Capacidades Instaladas
| Sistema | Capacidad | Unidad |
|---|---|---|
| **Solar PV (OE2)** | 4,162 | kWp |
| **BESS (OE2)** | 2,000 (or 4,520) | kWh |
| **Chargers (128)** | 272 | kW simultáneo |

---

## 📋 USO EN COMPARATIVAS

### Plantilla: Comparativa de Reducciones
```
SCENARIO: [Nombre del escenario - ej: SAC Agent con CO₂ Focus]

1. CO₂ EMITIDO (Grid Baseline):
   = Grid Import × 0.4521 kgCO₂/kWh
   = ___ kWh × 0.4521 = ___ kg = ___ tCO₂ vs. baseline 1,073 tCO₂

2. REDUCCIONES INDIRECTAS (Solar + BESS):
   = (Solar aprovechado + BESS descargado) × 0.4521
   = ___ kWh × 0.4521 = ___ kg = ___ tCO₂ evitados

3. REDUCCIONES DIRECTAS (EV Cargada):
   = Total EV × 2.146 kgCO₂/kWh
   = ___ kWh × 2.146 = ___ kg = ___ tCO₂ evitados

4. CO₂ NETO:
   = Emitido - Indirectas - Directas
   = ___ - ___ - ___ = ___ tCO₂/año

5. % REDUCCIÓN vs. BASELINE:
   = (Baseline - Neto) / Baseline × 100%
   = (1,073 + 509) - ___) / 1,582 × 100% = ___%
```

---

## 🎯 RESUMEN EJECUTIVO

**Línea Base (3,328 EVs en Iquitos):**
- Si fueran combustión: **5,408 tCO₂/año**
- Si cargaran 100% desde grid: **1,073 tCO₂/año**
- **Total potencial de reducción:** 6,481 tCO₂/año

**Objetivo OE3:**
- Maximizar solar directo → reducción indirecta máxima
- Cargar EVs desde PV/BESS → reducción directa máxima
- Impacto esperado en Iquitos: **1-2% de reducción de emisiones totales**

---

*Documento de referencia para validar cálculos de CO₂ en simulate.py y resultados de agentes RL.*
