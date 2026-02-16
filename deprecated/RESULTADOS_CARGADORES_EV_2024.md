# 🔌 RESULTADOS SIMULACIÓN CARGADORES EV - IQUITOS 2024

**Fecha**: 14 de Febrero de 2026  
**Componente**: OE2 - Dimensionamiento de Cargadores (Modo 3 @ 7.4 kW)  
**Versión**: v5.2 (Tiempos reales de carga)  
**Status**: ✅ COMPLETADO

---

## 📍 INFRAESTRUCTURA DE CARGA

### Especificaciones Técnicas

| Parámetro | Valor |
|-----------|-------|
| **Ubicación** | Iquitos, Perú (Mall) |
| **Tipo de Cargador** | Modo 3 (Monofásico IEC 61851-1) |
| **Voltaje** | 230V monofásico |
| **Corriente** | 32A |
| **Potencia por toma** | 7.4 kW |
| **Horario Operativo** | 09:00 - 22:00 (13 horas) |
| **Modo de Operación** | Estocástico con colas independientes |

### Cargadores y Sockets

| Componente | Cantidad | Detalles |
|-----------|----------|---------|
| **Cargadores Totales** | 19 unidades | 2 tomas cada uno |
| **Tomas Totales (Sockets)** | 38 | 30 motos + 8 mototaxis |
| **Playa Motos** | 15 cargadores | 30 tomas (2 tomas/cargador) |
| **Playa Mototaxis** | 4 cargadores | 8 tomas (2 tomas/cargador) |
| **Potencia Instalada** | 281.2 kW | 38 tomas × 7.4 kW |

---

## 📊 DIMENSIONAMIENTO POR ESCENARIO

### Tabla de 4 Escenarios

| Escenario | Penetración EV (pe) | Factor Carga (fc) | Cargadores | Tomas | Energía/día |
|-----------|-------------------|-------------------|-----------|-------|------------|
| **CONSERVADOR** | 0.20 (20%) | 0.45 (45%) | 11 | 22 | 834.5 kWh |
| **MEDIANO** | 0.25 (25%) | 0.50 (50%) | 15 | 30 | 1,159.0 kWh |
| **RECOMENDADO** ⭐ | 0.30 (30%) | 0.55 (55%) | 19 | 38 | 1,529.9 kWh |
| **MÁXIMO** | 0.40 (40%) | 0.65 (65%) | 30 | 60 | 2,410.7 kWh |

**Escenario Actual**: RECOMENDADO (pe=0.30, fc=0.55)  
**Base Metodológica**: IEA GEO 2024, BNEF EVO 2025, NREL 2021

---

## 🚲 FLOTA DE VEHÍCULOS (pe=0.30, fc=0.55)

### Base Estacionada
```
Mall Iquitos (diario):
  - Motos: 1,636 vehículos
  - Mototaxis: 236 vehículos
  - Total: 1,872 vehículos/día
```

### Vehículos que Cargan = Base × pe × fc

| Período | Motos | Mototaxis | Total |
|---------|-------|-----------|-------|
| **Diario** | 270 | 39 | 309 |
| **Mensual** | 8,100 | 1,170 | 9,270 |
| **Anual** | 98,550 | 14,235 | 112,785 |

### Distribución Punta (18:00-23:00) vs Fuera de Punta (09:00-18:00)

```
MOTOS:
  Punta (55%): 149 motos en 5 horas → 30 motos/hora
  Fuera punta (45%): 121 motos en 7 horas → 17 motos/hora

MOTOTAXIS:
  Punta (55%): 21 mototaxis en 5 horas → 4.2 mototaxis/hora
  Fuera punta (45%): 18 mototaxis en 7 horas → 2.6 mototaxis/hora
```

---

## ⏰ TIEMPOS DE CARGA REALES (v5.2)

### Eficiencia de Carga

**CHARGING_EFFICIENCY = 0.62 (62%)**

Factores considerados:
- Pérdidas cargador: ~3-5%
- Pérdidas cable/conexión: ~2-3%
- Pérdidas conversión batería: ~5-8%
- Reducción por taper (CV phase): ~10-15% tiempo adicional
- **Total: 62% de potencia nominal**

### Tiempos por Vehículo

#### Moto Eléctrica
```
Batería: 4.6 kWh
Potencia nominal: 7.4 kW
Tiempo ideal: 4.6 kWh ÷ 7.4 kW = 41 minutos
Tiempo REAL: ~60 minutos (50-70 min con perdidas)
Capacidad: 1.0 cargas/hora/toma
```

#### Mototaxi
```
Batería: 7.4 kWh
Potencia nominal: 7.4 kW
Tiempo ideal: 7.4 kWh ÷ 7.4 kW = 67 minutos
Tiempo REAL: ~90 minutos (75-105 min con perdidas)
Capacidad: 0.67 cargas/hora/toma
```

---

## ⚡ ENERGÍA Y POTENCIA

### Energía Cargada

| Métrica | Valor |
|---------|-------|
| **Energía Diaria** | 1,529.9 kWh |
| **Energía Mensual** | 45,897 kWh |
| **Energía Anual** | 453,349 kWh |
| **Energía Motos/año** | 359,149 kWh (79.2%) |
| **Energía Mototaxis/año** | 94,201 kWh (20.8%) |

### Potencia

| Período | Potencia | Estado |
|---------|----------|--------|
| 09:00-17:59 | Ramp 84-257 kW | Operación Normal |
| 18:00-21:59 | 281.2 kW | PICO (100% capacidad) |
| 22:00 | 140.6 kW | Cierre |
| Máxima | 281.2 kW | Instalada |
| Promedio | 51.8 kW | Anual |

### Perfil Horario (Factor de Operación)

```
Hora    Factor    Potencia (kW)    Estado
────────────────────────────────────────
09:00     30%        84.4          Apertura
10:00     30%        84.4
11:00     39%       109.0
12:00     48%       133.6
13:00     56%       158.2
14:00     65%       182.8
15:00     74%       207.4
16:00     82%       232.0
17:00     91%       256.6
18:00    100%       281.2          PICO
19:00    100%       281.2          PICO
20:00    100%       281.2          PICO
21:00    100%       281.2          PICO
22:00     50%       140.6          Cierre
────────────────────────────────────────
Max Instalada: 281.2 kW
Max Energía/día: 2,713.6 kWh
```

---

## 💰 COSTOS OSINERGMIN (Electro Oriente S.A.)

### Tarifas 2024-2025

| Período | Tarifa |
|---------|--------|
| **Hora Punta (HP)** 18:00-22:59 | S/. 0.45/kWh |
| **Fuera Punta (HFP)** 00:00-17:59 | S/. 0.28/kWh |

**Referencia**: OSINERGMIN Resolución N° 047-2024-OS/CD

### Costo de Carga EV Anual

| Concepto | Energía | Tarifa | Costo |
|----------|---------|--------|-------|
| **Hora Punta (HP)** | 200,982 kWh | S/. 0.45/kWh | S/. 90,441.87 |
| **Fuera Punta (HFP)** | 252,368 kWh | S/. 0.28/kWh | S/. 70,662.91 |
| **TOTAL ANUAL** | 453,349 kWh | Promedio | **S/. 161,104.78** |

### Costo Previo (sin EVs, gasolina)

- Consumo gasolina: 154,430 L/año (estimado)
- Precio gasolina: S/. 6.0/L (actual Iquitos)
- Costo anual: **S/. 926,580**

### Ahorro Económico por Electrificación
```
Gasolina:    S/. 926,580/año
Electricidad: S/.  161,105/año
───────────────────────────────
AHORRO:      S/. 765,475/año = 82.6% MENOS COSTO
```

---

## 🌍 REDUCCIÓN DE CO₂

### Reducción DIRECTA (Cambio de Combustible: Gasolina → EV)

#### Metodología

La reducción directa es el CO₂ que se evita porque los vehículos **NO usan gasolina**.

```
Factor Gasolina: 2.31 kg CO₂/L (IPCC)

Para MOTOS:
  Consumo moto 2T: 2.86 L/100 km (35 km/L)
  Moto EV: 5 kWh/100 km (20 km/kWh autonomía)
  
  Por cada kWh cargado:
    Distancia: 20 km
    Gasolina evitada: 20/35 = 0.57 L
    CO₂ bruto: 0.57 × 2.31 = 1.32 kg CO₂
    CO₂ red: 1 kWh × 0.4521 = 0.45 kg CO₂ (diésel Iquitos)
    CO₂ NETO: 1.32 - 0.45 = 0.87 kg CO₂/kWh

Para MOTOTAXIS:
  Consumo 3-wheeler: 4 L/100 km (25 km/L)
  Moto EV: 10 km/kWh autonomía
  
  Por cada kWh cargado:
    Distancia: 10 km
    Gasolina evitada: 10/25 = 0.40 L
    CO₂ bruto: 0.40 × 2.31 = 0.92 kg CO₂
    CO₂ red: 0.45 kg CO₂ (idem)
    CO₂ NETO: 0.92 - 0.45 = 0.47 kg CO₂/kWh

Promedio ponderado (70% motos, 30% taxis):
  0.70 × 0.87 + 0.30 × 0.47 = 0.75 kg CO₂/kWh
```

#### Resultados

| Concepto | Valor |
|----------|-------|
| **Motos** (Factor 0.87) | 312.46 ton CO₂/año |
| **Mototaxis** (Factor 0.47) | 44.27 ton CO₂/año |
| **TOTAL REDUCCIÓN DIRECTA** | **356.73 ton CO₂/año** |
| **Gasolina Evitada** | 154,430 L/año |

### Equivalencias Ambientales
```
356.73 ton CO₂/año equivale a:
  - 77 automóviles sin emitir (~4,630 km/año cada uno)
  - 5,950 árboles plantados y crecidos (20 años)
  - Energía renovable evitada: Gasolina no quemada
```

### Nota Importante
Esta es la **reducción DIRECTA** (evitar combustible fósil).
La **reducción INDIRECTA** (desplazamiento de diésel en la red por solar) se calcula en `solar_pvlib.py` y se suma en OE3.

---

## 📈 ESTADÍSTICAS ESTOCÁSTICAS

### Parámetros de Simulación

| Parámetro | Valor |
|-----------|-------|
| **Modelo de Llegadas** | Poisson |
| **λ Motos** | 0.69 vehículos/toma/hora |
| **λ Mototaxis** | 0.375 vehículos/toma/hora |
| **SOC Inicial** | N(20%, 10%) - batería baja al llegar |
| **SOC Objetivo** | 100% - carga completa |
| **Colas** | FIFO independientes por toma |
| **Reproducibilidad** | random_seed=42 |
| **Horizonte** | 8,760 horas (1 año completo) |

### Tabla Parametrizada (101 escenarios aleatorios)

| Métrica | Mínimo | Promedio | Mediana | Máximo | Desv. Std |
|---------|--------|----------|---------|--------|-----------|
| **Cargadores** | 11 | 18.7 | 19.0 | 28 | 4.09 |
| **Tomas** | 22 | 37.4 | 38.0 | 56 | 8.19 |
| **Sesiones Pico (5h)** | 99.2 | 166.1 | 163.4 | 258.0 | 38.60 |
| **Cargas/día** | 180 | 301.9 | 297 | 469 | 70.19 |
| **Energía/día (kWh)** | 893 | 1,495.5 | 1,471 | 2,323 | 347.64 |
| **Potencia Pico (kW)** | 163 | 276.5 | 281.2 | 414 | 60.59 |

---

## 📁 DATASETS GENERADOS

### Archivo Principal: `chargers_ev_ano_2024_v3.csv`

```
Dimensiones: 8,760 filas × 352 columnas
Período: 01/01/2024 - 31/12/2024 (horario)
Índice: datetime (con zona horaria America/Lima)
Peso: ~45 MB
```

#### Estructura de Columnas por Toma

Para cada una de las 38 tomas (socket_000 a socket_037):

```
socket_XXX_charger_power_kw       Potencia nominal cargador (7.4 kW)
socket_XXX_battery_kwh             Capacidad batería (4.6 moto / 7.4 taxi)
socket_XXX_vehicle_type            Tipo vehículo (MOTO / MOTOTAXI)
socket_XXX_soc_current             SOC actual [0-1]
socket_XXX_soc_arrival             SOC al llegar
socket_XXX_soc_target              SOC objetivo (1.0 = carga completa)
socket_XXX_active                  Toma ocupada (0/1)
socket_XXX_charging_power_kw       Potencia de carga real (0 si inactivo)
socket_XXX_vehicle_count           Vehículos atendidos acumulados
```

#### Columnas Agregadas OSINERGMIN

```
is_hora_punta                      1 si 18:00-22:59, 0 resto
tarifa_aplicada_soles              S/.0.45 (HP) o S/.0.28 (HFP)
ev_energia_total_kwh               Energía total cargada/hora
costo_carga_ev_soles               Costo de carga hora (energía × tarifa)
ev_energia_motos_kwh               Energía cargada motos/hora
ev_energia_mototaxis_kwh           Energía cargada mototaxis/hora
co2_reduccion_motos_kg              CO₂ evitado motos/hora
co2_reduccion_mototaxis_kg         CO₂ evitado mototaxis/hora
reduccion_directa_co2_kg            CO₂ total evitado/hora
ev_demand_kwh                       Alias: demand de EVs para CityLearn
```

### Archivo Diario: `chargers_ev_dia_2024_v3.csv`

```
Dimensiones: 24 filas × 352 columnas
Ejemplo: Día 1 (01/01/2024)
Índice: datetime (24 horas del día)
```

### Gráficas Generadas

1. **`vehiculos_por_periodo_v52.png`**
   - Comparación diario/mensual/anual
   - Desglose motos vs mototaxis

2. **`perfil_horario_carga_v52.png`**
   - Potencia vs hora del día
   - Identificación de picos

---

## ✅ VALIDACIONES COMPLETADAS

### Verificación de Especificación v5.2

```
[OK] Cantidad de cargadores: 19 (15 motos + 4 mototaxis)
[OK] Cantidad de tomas: 38 (30 motos + 8 mototaxis)
[OK] Tomas por cargador: 2 (Modo 3)
[OK] Potencia por toma: 7.4 kW
[OK] IDs únicos: 0-18 (secuenciales)
```

### Verificación CityLearn v2

```
[OK] Filas: 8,760 (1 año horario)
[OK] Índice: datetime con zona horaria
[OK] Columna ev_demand_kwh: PRESENTE
[OK] Columna is_hora_punta: PRESENTE
[OK] Columna reduccion_directa_co2_kg: PRESENTE
[OK] Status: LISTO PARA INTEGRACIÓN OE3
```

---

## 🔗 INTEGRACIÓN OE3

El dataset de cargadores se integra con:

1. **Solar (OE2)**: `pv_generation_hourly_citylearn_v2.csv` (8.29 GWh/año)
2. **Cargadores (OE2)**: `chargers_ev_ano_2024_v3.csv` (453.3 MWh/año)
3. **BESS**: 1,700 kWh max SOC para almacenamiento
4. **RL Agents**: SAC/PPO/A2C para optimizar despacho

### Flujo de Control OE3

```
CityLearn Environment
├─ Observaciones (solar generation, EV demand, BESS SOC)
├─ Acciones (38 sockets + 1 BESS = 39 actuadores)
├─ Recompensa (CO₂ minimization + auto-consumo + carga completa)
└─ Resultado: Política óptima de despacho

Agentes RL:
  ├─ SAC (off-policy) - aprende asimétrica, rápido
  ├─ PPO (on-policy) - robusto, estable
  └─ A2C (on-policy) - rápido, menos memory
```

---

## 📚 REFERENCIAS TÉCNICAS

- **IEA Global EV Outlook 2024**: Penetración EV 30% en mercados emergentes 2030
- **BNEF Electric Vehicle Outlook 2025**: 2/3 ruedas Asia emergente
- **ICCT Electric two/three-wheelers India 2022**: Consumo y especificaciones
- **NREL EV Charging Behavior Study 2021**: Factor de carga fc=0.55
- **IPCC**: Factor CO₂ gasolina = 2.31 kg/L
- **OSINERGMIN**: Tarifas Electro Oriente 2024-2025
- **IEC 61851-1**: Estándar Modo 3 cargadores

---

**Generado**: 2026-02-14 10:35 AM  
**Archivo**: `RESULTADOS_CARGADORES_EV_2024.md`  
**Versión**: v5.2.1  
**Estado**: ✅ LISTO PARA OE3
