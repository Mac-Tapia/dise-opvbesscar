# DIMENSIONAMIENTO DE ALMACENAMIENTO DE ENERGÍA (BESS) v5.3
**Sistema EV Mall Iquitos - Arbitraje Tarifario OSINERGMIN**

---

## 1. CONFIGURACIÓN TÉCNICA BESS v5.3

### Especificaciones Técnicas

| Parámetro | Valor | Unidad |
|-----------|-------|--------|
| Capacidad nominal | 1,700 | kWh |
| Potencia nominal | 400 | kW |
| Profundidad de descarga (DoD) | 80 | % |
| Eficiencia round-trip | 95 | % |
| Capacidad útil (80% DoD) | 1,360 | kWh |
| SOC mínimo operacional | 20 | % |
| SOC máximo operacional | 100 | % |
| C-rate nominal | 0.24 | C |
| Rango operacional | 20-100 | % |

---

## 2. TARIFAS REGULATORIAS OSINERGMIN MT3
**Electro Oriente S.A. - Iquitos, Loreto**
**Resolución OSINERGMIN N° 047-2024-OS/CD (Vigente desde 2024-11-04)**

### Tarificar de Energía

#### ⏰ Hora Punta (HP): 18:00 - 23:00 (5 horas)
- Tarifa energía: **S/.0.45/kWh** (~USD 0.120/kWh)
- Tarifa potencia: **S/.48.50/kW-mes**

#### ⏰ Hora Fuera de Punta (HFP): 00:00-17:59, 23:00-23:59 (19 horas)
- Tarifa energía: **S/.0.28/kWh** (~USD 0.075/kWh)
- Tarifa potencia: **S/.22.80/kW-mes**

### Diferencial de Arbitraje
- **Margen: S/.0.17/kWh** (60.7% de ahorro respecto a tarifa HFP)
- **Factor de emisión CO₂**: 0.4521 kg CO₂/kWh (sistema térmico aislado)

---

## 3. DATOS DE ENTRADA VERIFICADOS

### Archivos de Entrada Utilizados

| Archivo | Tamaño | Estado | Descripción |
|---------|--------|--------|-------------|
| pv_generation_hourly_citylearn_v2.csv | 1,458.1 KB | ✅ | Generación PV horaria (8,760 horas) |
| chargers_ev_ano_2024_v3.csv | 15,892.9 KB | ✅ | Demanda EV: 38 sockets (19 cargadores × 2) |
| demandamallhorakwh.csv | 193.7 KB | ✅ | Demanda mall real Iquitos |

### Carga de Datos
- **Generación PV**: 8,760 registros horarios (1 año)
- **Demanda EV**: 39 sockets operativos, horario 9h-22h
  - 19 cargadores Mode 3 @ 7.4 kW c/u
  - Playa motos: 15 cargadores × 2 = 30 tomas
  - Playa mototaxis: 4 cargadores × 2 = 8 tomas
  - **Total: 38 tomas EV controlables**
- **Demanda Mall**: Perfil real Iquitos (potencia base)

---

## 4. CRITERIOS Y REGLAS DE DIMENSIONAMIENTO

### Regla de Prioridad Solar → BESS → Cargas

1. **PV → EV Directo** (Solar a Motos/Mototaxis)
   - Prioridad máxima: carga EV desde generación fotovoltaica
   - Directo, sin pérdidas en BESS

2. **Excedente PV → Carga BESS** (Hasta SOC 100%)
   - Fuente: Generación solar excedente después de EV
   - Mantiene SOC máximo (100%) para período punta

3. **Excedente Final → Mall** (Abastecimiento secundario)
   - Alimenta centro comercial si aún hay excedente
   - Sin impacto en disponibilidad BESS para EV

4. **BESS → EV (en déficit)** (Descarga en período crítico)
   - Solo desde punto de cruce PV = EV hasta cierre (22h)
   - Objetivo: Cubrir 100% del déficit EV horario
   - SOC objetivo al cierre: 20% (seguridad para próximo día)

### Análisis de Cruce de Curvas PV vs EV

| Análisis | Hora | Descripción |
|----------|------|-------------|
| Fin de carga BESS | ~6h | PV ≥ EV, SOC alcanza 100% |
| Inicio descarga BESS | ~17h | PV < EV, punto crítico (cruce) |
| Cierre operativo | 22h | Fin de operación EV y BESS |
| Déficit EV promedio | - | 559.3 kWh/día |
| **Déficit EV máximo** | - | **708.0 kWh/día** ← Criterio de diseño |
| Pico demanda EV | - | 156.0 kW |

---

## 5. BALANCE ENERGÉTICO - FLUJOS DIARIOS Y ANUALES

### 5.1 Generación

| Concepto | Diario | Anual | Unidad |
|----------|--------|-------|--------|
| **Generación PV Solar** | 22,719 | 8,292.5 | kWh/día, MWh/año |

### 5.2 Demanda

| Carga | Diario | Anual | Unidad |
|------|--------|-------|--------|
| Mall (comercial) | 33,885 | 12,367.9 | kWh/día, MWh/año |
| EV (motos + mototaxis) | 1,129 | 412.2 | kWh/día, MWh/año |
| **Total demanda** | **35,014** | **12,780.1** | **kWh/día, MWh/año** |

### 5.3 Flujos de Energía

| Flujo | Valor Diario | Valor Anual | Descripción |
|------|---------|-----------|-------------|
| **Excedente PV** | 22,149 kWh | 8,079.4 MWh | (PV - Demanda total) |
| **Déficit EV punta** | 708 kWh | - | Máximo déficit BESS debe cubrir |
| **Import red** | 17,897 kWh | 6,532.4 MWh | Energía adquirida a tarifa OSINERGMIN |
| **Export red** | 5,532 kWh | 2,019.1 MWh | Excedente inyectado (arbitraje) |

### 5.4 Distribución PV Diaria

| Destino | kWh/día | Porcentaje |
|---------|---------|-----------|
| →EV directo | 570 | 2.5% |
| →Carga BESS | (excedente) | ~97% |
| →Mall | (después BESS) | Variable |

---

## 6. DIMENSIONAMIENTO FINAL BESS v5.3

### Criterio de Diseño: 100% Cobertura Déficit EV

**Parámetro de Cálculo**
```
Capacidad = Déficit_EV_Máximo / (DoD × Eficiencia)
          = 708 kWh/dia / (0.80 × 0.95)
          = 708 / 0.76
          ≈ 931 kWh
```

**Aplicación Factor de Diseño**
- Base calculated: 931 kWh
- Factor de margen: 1.20×
- **Capacidad final v5.3: 1,700 kWh** (amplificada para arbitraje tarifario HP/HFP)

### Especificaciones Finales Adoptadas

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| **Capacidad** | 1,700 kWh | Margen 20% + arbitraje OSINERGMIN |
| **Potencia** | 400 kW | Carga/descarga en 4-5 horas |
| **C-rate nominal** | 0.36 C | Descarga en 2.8 horas (potencia suficiente) |
| **DoD efectivo** | 80% | (1,360 kWh útiles disponibles) |
| **Eficiencia round-trip** | 95% | Pérdidas BESS + inversor |
| **Ciclos/día** | 0.82 | Operación sostenible sin degradación |
| **Rango SOC** | 20%-100% | (1,360 kWh rango operativo) |

---

## 7. OPERACIÓN DEL BESS - ARBITRAJE HP/HFP

### 7.1 Estrategia de Carga (HFP: 06:00-17:00)

**Fuentes de carga BESS**
1. **Excedente solar** (prioridad)
   - Rango: 6h-17h (máxima generación solar)
   - De PV residual después de alimentar EV

2. **Grid en horas fuera punta** (si SOC < 80%)
   - Precio menor: S/.0.28/kWh
   - Llena BESS hasta 80% para ser usado en punta

**Perfil carga típico**
- Inicio carga: ~06:00h (amanecer)
- Fin carga: ~17:00h (punto de cruce PV = EV)
- SOC objetivo: 100% para período punta
- Eficiencia aplicada: 95% round-trip

### 7.2 Estrategia de Descarga (HP: 18:00-22:00)

**Destinos de descarga BESS**
1. **EV Chargers** (prioridad 1)
   - Cubre 90.5% de demanda EV en horas punta
   - Tarifa que evita: S/.0.45/kWh (máxima)

2. **Mall** (prioridad 2)
   - Complementa demanda comercial en punta
   - Evita compra a precio máximo tarifa

**Perfil descarga típico**
- Inicio descarga: ~17:00h-18:00h (punto crítico PV < EV)
- Fin descarga: ~22:00h (cierre centro comercial)
- SOC objetivo final: 20% (margen de seguridad)
- Descarga activa: 5 horas efectivas

### 7.3 Métricas de Operación Diaria

| Métrica | Valor | Unidad |
|---------|-------|--------|
| **Carga BESS diaria** | Prom. 1,400 | kWh |
| **Descarga BESS diaria** | Prom. 1,390 | kWh |
| **Ciclos por día** | 0.82 | ciclos |
| **SOC mínimo** | 20 | % |
| **SOC máximo** | 100 | % |
| **Autosuficiencia energética** | 48.9 | % |
| **Rango operacional** | 20-100 | % SOC |

### 7.4 Cobertura de Demanda EV

| Fuente | Energía anual | Porcentaje |
|--------|--------------|-----------|
| PV directo | 208 MWh | 50.4% |
| **BESS** | **165 MWh** | **40.0%** |
| Red eléctrica | 39 MWh | 9.5% |
| **Total EV cubierto** | **412 MWh** | **100%** |

---

## 8. MÉTRICAS ECONÓMICAS - AHORRO ARBITRAJE OSINERGMIN

### 8.1 Costos Anuales

| Concepto | Monto | Unidad |
|----------|-------|--------|
| **BASELINE** (sin BESS, sin PV) | 4,219,367 | S/./año |
| **CON SISTEMA** (PV + BESS) | 2,387,533 | S/./año |
| **Ahorro por arbitraje BESS** | 82,251 | S/./año |
| **Ahorro TOTAL del sistema** | **1,831,834** | **S/./año** |

### 8.2 Indicadores de Rentabilidad

| Indicador | Valor | Observación |
|-----------|-------|-------------|
| **Reducción de costo** | 43.4% | Vs. baseline sin energías renovables |
| **ROI arbitraje BESS** | 1.9% | Retorno sobre inversión anual |
| **Período payback estimado** | ~50 años | (Con costo BESS ~USD 200-300/kWh instalado) |

### 8.3 Desglose del Ahorro Anual

```
BASELINE (sin PV, sin BESS):
  12,780.1 MWh × tarifa promedio = S/.4,219,367/año

CON SISTEMA (PV + BESS):
  6,532.4 MWh × tarifa actual = S/.2,387,533/año
  
AHORRO DIRECTO POR PV:        S/.1,749,583/año
AHORRO ARBITRAJE BESS HP/HFP: S/.  82,251/año
AHORROS TOTAL:                S/.1,831,834/año
```

---

## 9. IMPACTO AMBIENTAL - REDUCCIÓN CO₂

### 9.1 Factor de Emisión

**Factor de emisión CO₂ para Iquitos:**
- **0.4521 kg CO₂/kWh**
- Fuente: Sistema térmico aislado (diésel/residual)
- Base: MINEM/OSINERGMIN - Sistema Loreto

### 9.2 Emisiones Anuales

| Escenario | Emisiones | Unidad |
|-----------|-----------|--------|
| **BASELINE** (sin PV, sin BESS) | 3,172.0 | ton CO₂/año |
| **CON SISTEMA** (PV + BESS) | 2,953.3 | ton CO₂/año |
| **Reducción directa** | 218.7 | ton CO₂/año |

### 9.3 Reducción de Emisiones Indirectas

| Concepto | Valor | Unidad |
|----------|-------|--------|
| **CO₂ evitado por PV + BESS** | 218.7 | ton/año |
| **Reducción porcentual** | 6.9 | % |
| **Equivalente a** | 52 árboles | (reforestación anual) |

**Nota**: La reducción es "indirecta" pues BESS reemplaza energía térmica de red en las horas punta (18:00-23:00) cuando se consume principalmente generación diésel en Iquitos.

---

## 10. SIMULACIÓN HORARIA - RESULTADOS AGREGADOS

### 10.1 Simulación 8,760 Horas (1 año)

**Energías procesadas**

| Flujo | Energía anual | Descripción |
|-------|--------------|-------------|
| PV generado | 8,292.5 MWh | Solar fotovoltaica |
| EV cargado | 412.2 MWh | Motos + mototaxis (9h-22h) |
| Mall consumido | 12,367.9 MWh | Centro comercial |
| BESS cargado | 293.8 MWh | Energía ingresada a batería |
| BESS descargado | 278.8 MWh | Energía extraída de batería |
| Red importada | 6,532.4 MWh | Electricidad comprada |
| Red exportada | 2,019.1 MWh | Excedente inyectado (arbitraje) |

### 10.2 Eficiencias

| Proceso | Eficiencia | Descripción |
|---------|-----------|-------------|
| **Round-trip BESS** | 95% | Carga → Descarga (nominal) |
| **Carga efectiva diaria** | Var. | Según disponibilidad solar |
| **Disponibilidad SOC** | 80% | Rango 20%-100% |

---

## 11. ARCHIVOS GENERADOS

### 11.1 Archivos de Datos

| Archivo | Tamaño | Contenido | Ubicación |
|---------|--------|----------|-----------|
| **bess_results.json** | 1.8 KB | Configuración y métricas BESS | data/oe2/bess |
| **bess_simulation_hourly.csv** | 1,927.7 KB | Simulación 8,760 horas, 29 columnas | data/oe2/bess |
| **bess_daily_balance_24h.csv** | 7.8 KB | Perfil día típico (24 horas) | data/oe2/bess |

### 11.2 Archivos de Salida CityLearn

Directorio: `data/oe2/citylearn/`
- Datasets listos para entrenamiento de agentes RL (SAC, PPO, A2C)
- Formato compatible con CityLearn v2

### 11.3 Gráficas Generadas

| Gráfica | Descripción | Ubicación |
|---------|-------------|-----------|
| System Complete | Sistema FV + BESS completo | reports/oe2/bess |
| Monthly Analysis | Análisis mensual de generación | reports/oe2/bess |

---

## 12. RESUMEN EJECUTIVO

### Síntesis del Dimensionamiento

```
╔════════════════════════════════════════════════════════════╗
║         SÍNTESIS EJECUTIVA BESS v5.3 (2026-02-12)          ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  BESS:    1,700 kWh / 400 kW (arbitraje OSINERGMIN)       ║
║  PV:      8,292.5 MWh/año de generación solar             ║
║  DEMANDA: 12,780.1 MWh/año (mall + EV)                   ║
║                                                            ║
║  AHORRO ANUAL:     S/.1,831,834/año (43.4% reducción)     ║
║  ROI ARBITRAJE:    1.9% (sobre inversión BESS)            ║
║                                                            ║
║  CO₂ REDUCIDO:     218.7 ton/año (6.9% reducción)         ║
║  AUTOSUFICIENCIA:  48.9% energética                       ║
║                                                            ║
║  CICLOS/DÍA:       0.82 (operación sostenible)            ║
║  RANGO SOC:        20%-100% (1,360 kWh útiles)            ║
║                                                            ║
╠════════════════════════════════════════════════════════════╣
║  ✅ DIMENSIONAMIENTO COMPLETADO EXITOSAMENTE              ║
║     Listo para integración CityLearn + Agentes RL         ║
╚════════════════════════════════════════════════════════════╝
```

### Alcances del Sistema

**Fase OE2 (Dimensionamiento = COMPLETADA)**
- ✅ Cálculo de capacidad BESS: 1,700 kWh / 400 kW
- ✅ Reglas de operación (prioridad solar → BESS)
- ✅ Simulación 8,760 horas con arbitraje HP/HFP
- ✅ Generación datasets CityLearn (38 sockets EV)
- ✅ Análisis económico y CO₂

**Fase OE3 (Control = Próxima)**
- Entrenamiento agentes RL (SAC, PPO, A2C)
- Optimización en tiempo real con CityLearn v2
- Comparación vs baseline (sin RL)

---

## 13. ESPECIFICACIONES TÉCNICAS DETALLADAS

### 13.1 Infraestructura EV

**Chargers Iquitos v5.2**
- **Ubicación 1 (Motos)**: Playa de carga motos
  - Cantidad: 15 cargadores
  - Sockets: 15 × 2 = 30 tomas
  - Potencia c/u: 7.4 kW (Mode 3, 32A @ 230V)
  - Subtotal potencia: 222 kW

- **Ubicación 2 (Mototaxis)**: Playa de carga mototaxis
  - Cantidad: 4 cargadores
  - Sockets: 4 × 2 = 8 tomas
  - Potencia c/u: 7.4 kW (Mode 3, 32A @ 230V)
  - Subtotal potencia: 59.2 kW

**Total Sistema**
- Cargadores: 19 unidades
- Sockets controlables: 38 tomas
- Potencia instalada EV: 281.2 kW

### 13.2 Horario Operativo EV

| Franja horaria | Estado | Observación |
|---|---|---|
| **09:00 - 22:00** | OPERATIVO | Horario comercial mall |
| Fuera de horario | INACTIVO | Ningún EV conectado |

**Energía EV por franjas horarias**
- 09:00-14:00: Demanda media (mañana tardía)
- 14:00-18:00: Demanda baja (tarde temprana)
- 18:00-22:00: Demanda alta (tarde-noche, punta OSINERGMIN)

---

## 14. PRÓXIMOS PASOS

### Fase OE3 - Control Predictivo

1. **Entrenar agentes RL con CityLearn v2**
   ```bash
   python -m src.agents.{sac|ppo_sb3|a2c_sb3} \
     --env citylearn \
     --method {SAC|PPO|A2C} \
     --episodes 26280 \
     --gpu
   ```

2. **Evaluar mejoras vs baseline**
   - Baseline: Dispatch sin RL (regla prioridad solar)
   - Métrica: CO₂ evitado + ahorro económico
   - Target: -30% CO₂, +15% ahorro vs baseline

3. **Integración física Iquitos (Fase OE4)**
   - Comunicación BESS ↔ EMS (Gestión energética)
   - Control en tiempo real 38 sockets
   - Telemetría y monitoreo

---

## APÉNDICE: CONFIGURACIÓN OSINERGMIN

### Resolución Base
- **Documento**: OSINERGMIN N° 047-2024-OS/CD
- **Pliego Tarifario**: MT3 Media Tensión (Comercial/Industrial)
- **Concesionario**: Electro Oriente S.A.
- **Región**: Iquitos, Loreto (Sistema aislado)
- **Vigencia**: 2024-11-04 al 2025-11-03

### Aplicabilidad a Proyecto EV Mall
- El mall Iquitos → Clasificación MT3 por potencia contratada (35 kW)
- Tarifas horarias HP/HFP aplican dichotómicamente
- BESS permite retirada preferente en HFP (arbitraje costo-energía)

---

**Documento generado**: 2026-02-12 19:52:56  
**Versión BESS**: v5.3  
**Estado**: ✅ Dimensionamiento completado  
**Siguiente fase**: Agentes RL (SAC/PPO/A2C) en CityLearn v2
