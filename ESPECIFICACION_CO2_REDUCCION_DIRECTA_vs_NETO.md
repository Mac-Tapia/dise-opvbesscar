# ⚠️ ESPECIFICACIÓN CRÍTICA: Reducción Directa de CO₂ vs CO₂ Neto

**Fecha**: 2026-02-16  
**Importancia**: 🔴 CRÍTICA - Entender esta distinción es fundamental para interpretar resultados

---

## 🎯 Resumen Ejecutivo

```
REDUCCIÓN DIRECTA DE CO₂ = SOLO cambio de combustible (gasolina → eléctrico)
                          = Energía cargada × factores (0.87 o 0.47 kg CO₂/kWh)
                          ⚠️ NO INCLUYE emisiones del grid diesel
                          
CO₂ NETO = Reducción directa - Emisiones del grid
         = (Gasolina evitada) - (Diesel importado)
         = Impacto CO₂ REAL considerando TODO
```

---

## 📐 Cálculo Matemático

### 1. Reducción Directa de CO₂ (SOLO Combustible)

```
POR MOTO:
  Energía moto cargada × 0.87 kg CO₂/kWh (gasolina → EV)
  
  Ejemplo:
    10 kWh cargado × 0.87 = 8.7 kg CO₂ evitado de gasolina
    
POR MOTOTAXI:
  Energía taxi cargada × 0.47 kg CO₂/kWh (gasolina → EV)
  
  Ejemplo:
    10 kWh cargado × 0.47 = 4.7 kg CO₂ evitado de gasolina
    
TOTAL POR HORA:
  reduccion_directa_co2_kg = (energía motos × 0.87) + (energía taxis × 0.47)
                           = Gasolina evitada en kg CO₂
                           ⚠️ PUNTO IMPORTANTE: No restamos grid aquí
```

### 2. Emisiones del Grid (SOLO Diesel Importado)

```
TODA la electricidad en Iquitos viene de:
  • Diesel (99%)
  • Algo de hidroeléctrica residual (1%)
  Factor: 0.4521 kg CO₂/kWh (red aislada 100% térmica)

POR HORA:
  co2_grid_kwh = Energía total cargada × 0.4521
               = Energía en EVs × factor diesel
               = Diesel que se quema para generar esa electricidad
               
  Ejemplo:
    100 kWh total cargado × 0.4521 = 45.21 kg CO₂ de diesel generado
```

### 3. CO₂ Neto (Impacto Real)

```
IMPACTO NETO = Reducción directa - Emisiones del grid

co2_neto_por_hora_kg = reduccion_directa_co2_kg - co2_grid_kwh
                     = (Gasolina evitada) - (Diesel generado para EV)
                     
ESCENARIOS:

Escenario A: Neto POSITIVO (Beneficio)
  reduccion_directa: 200 kg (gasolina evitada)
  co2_grid:          80 kg (diesel generado)
  co2_neto:         120 kg ✅ GANANCIA neta de 120 kg
  Interpretación: Mejor cargar EV que usar gasolina
  
Escenario B: Neto NEGATIVO (Pérdida)
  reduccion_directa:  50 kg (gasolina evitada)
  co2_grid:         100 kg (diesel generado)
  co2_neto:         -50 kg ❌ PÉRDIDA neta de 50 kg
  Interpretación: Mejor No cargar que usar diesel (pero EVs pueden cargar con solar)
```

---

## 🏗️ Estructura en Dataset

### Columnas Generadas por `generate_socket_level_dataset_v3()`

```python
# REDUCCIÓN DIRECTA (SOLO COMBUSTIBLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
co2_reduccion_motos_kg
  → Energía motos/hora × 0.87 kg CO₂/kWh
  → Gasolina NO quemada en motos
  → Variable: depende de motos cargando
  → ⚠️ Métrica: Cambio combustible puro (moto gasolina → moto EV)

co2_reduccion_mototaxis_kg
  → Energía taxis/hora × 0.47 kg CO₂/kWh
  → Gasolina NO quemada en taxis
  → Variable: depende de taxis cargando
  → ⚠️ Métrica: Cambio combustible puro (taxi gasolina → taxi EV)

reduccion_directa_co2_kg
  → co2_reduccion_motos_kg + co2_reduccion_mototaxis_kg
  → TOTAL gasolina evitada en kg CO₂/hora
  → ⚠️ CRITTICO: ESTO ES SOLO COMBUSTIBLE, NO INCLUYE GRID
  → Máximo teórico: 270 motos × 7.4 kW × 0.87 + 39 taxis × 7.4 kW × 0.47
  
# EMISIONES DEL GRID (SOLO DIESEL GENERADO)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
co2_grid_kwh
  → Energía total cargada × 0.4521 kg CO₂/kWh
  → Diesel quemado para generar esa electricidad
  → Variable: depende de energía total cargada
  → ⚠️ Métrica: Costo ambiental de generar electricidad (red diesel)

# CO₂ NETO (IMPACTO REAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
co2_neto_por_hora_kg
  → reduccion_directa_co2_kg - co2_grid_kwh
  → Impacto CO₂ REAL considerando todo
  → Positivo: Neto beneficio ambiental
  → Negativo: Neto costo ambiental (pero solar puede cambiar esto)
  → ⚠️ Métrica: Lo que los agentes RL deben optimizar
```

---

## 🔍 Ejemplo Paso a Paso (1 Hora)

### Setup Hora 14:00 (Peak Solar)

```
Estado del sistema:
  • 15 motos cargando (sockets 0-14)
  • 3 taxis cargando (sockets 30-32)
  • Potencia: 15×7.4 kW + 3×7.4 kW = 133 kW total
  • Duración: 1 hora (medición horaria)
```

### Cálculos Paso a Paso

```
PASO 1: Energía cargada
  Motos:   15 × 7.4 kW × 1 h = 111 kWh
  Taxis:    3 × 7.4 kW × 1 h = 22.2 kWh
  Total:                      = 133.2 kWh

PASO 2: Reducción Directa (SOLO cambio combustible)
  Motos:   111 kWh × 0.87 = 96.57 kg CO₂ ahorrado (gasolina no quemada)
  Taxis:    22.2 kWh × 0.47 = 10.43 kg CO₂ ahorrado (gasolina no quemada)
  
  reduccion_directa_co2_kg = 96.57 + 10.43 = 107 kg CO₂
  ⚠️ Esto es SOLO el beneficio del cambio de combustible
  ⚠️ NO hemos considerado aún el costo del grid diesel

PASO 3: Emisiones del Grid (diesel para generar esa electricidad)
  Total cargado: 133.2 kWh
  Factor grid:   0.4521 kg CO₂/kWh (diesel, red aislada)
  
  co2_grid_kwh = 133.2 × 0.4521 = 60.2 kg CO₂
  = Diesel que se quemó en Iquitos para generar esa electricidad

PASO 4: CO₂ Neto (Impacto REAL)
  REDUCCIÓN:  107.0 kg (gasolina NO quemada en motos/taxis)
  GRID:       -60.2 kg (diesel quemado en planta térmica)
  NETO:       107.0 - 60.2 = 46.8 kg CO₂ GANANCIA NETA
  
  ✅ Resultado: Esta hora fue BENEFICIOSA
     Se evitó 46.8 kg CO₂ neto (incluyendo impacto del grid diesel)
```

### Interpretación

| Métrica | Valor | Significa |
|---------|-------|----------|
| `reduccion_directa` | 107 kg | Gasolina evitada por cambio combustible |
| `co2_grid` | 60.2 kg | Diesel importado para generar electricidad |
| `co2_neto` | +46.8 kg | Beneficio ambiental REAL (reducción - grid) |

---

## 📊 Resumen Anual (2024)

```
REDUCCIÓN DIRECTA (Cambio de combustible):
  Motos:   476,501 kWh × 0.87 = 414,555 kg
  Taxis:    89,374 kWh × 0.47 =  42,006 kg
  TOTAL:                         456,561 kg evitado por cambio combustible
  
CO₂ GRID (Diesel importado):
  Total:   565,875 kWh × 0.4521 = 255,832 kg
  
CO₂ NETO (Beneficio Real):
  456,561 - 255,832 = 200,729 kg GANANCIA NETA
  
INTERPRETACIÓN:
  ✅ Aunque la red es 100% diesel, los EVs generan 200.7 Mg beneficio neto
  ✅ Razón: Motos/taxis gasolina son MÁS contaminantes que diesel importado
  ⚠️ CON SOLAR: Beneficio aún mayor (solar no genera CO₂)
     = reduccion_directa_co2_kg (sin cambios) = 456.6 Mg
```

---

## ⚠️ Uso Correcto en Análisis

### ❌ MAL

```python
# ❌ Incorrecto: confundir reducción directa con neto
total_benefit = df['reduccion_directa_co2_kg'].sum()
print(f"CO2 total: {total_benefit}")  # Esto NO es el impacto neto
# Fallacy: estamos ignorando que el grid cuesta CO2
```

### ✅ BIEN

```python
# ✅ Correcto: usar CO₂ neto cuando se quiere impacto real
total_benefit_neto = df['co2_neto_por_hora_kg'].sum()
print(f"CO2 neto: {total_benefit_neto}")  # Impacto real considerando grid

# ✅ Si quieres desglosar:
reduccion_directa = df['reduccion_directa_co2_kg'].sum()
grid_cost = df['co2_grid_kwh'].sum()
neto = reduccion_directa - grid_cost
print(f"Reducción: {reduccion_directa}, Grid: {grid_cost}, Neto: {neto}")
```

---

## 🔗 Conexión con Agentes RL

### Para Reward Function

```python
# Opción 1: Optimizar NETO (recomendado)
reward_co2 = df['co2_neto_por_hora_kg'][t] / 1000  # kg → Mg
# El agente verá naturalmente:
# - Si carga con solar: rewarded (neto + 456.6 Mg/año de reducción directa)
# - Si carga con diesel: penalizado (neto + 200.7 Mg/año = balance negativo
#   comparado con no cargar)

# Opción 2: Optimizar reducción directa (para comparativa gasolina vs EV)
reward_co2 = df['reduccion_directa_co2_kg'][t] / 1000  # kg → Mg
# Útil para: "Cuánta gasolina evitamos vs diesel importado"

# Opción 3: Desglosar (para análisis fino)
reward_co2 = (df['reduccion_directa_co2_kg'][t] - df['co2_grid_kwh'][t]) / 1000
# = CO2 neto, pero componente explícito
```

### Para Research

```python
# Pregunta 1: ¿Cuánta gasolina evitamos?
respuesta = 456,561 kg/año = reduccion_directa_co2_kg.sum()

# Pregunta 2: ¿A costa de cuánto diesel?
respuesta = 255,832 kg/año = co2_grid_kwh.sum()

# Pregunta 3: ¿Cuál es el impacto neto?
respuesta = 200,729 kg/año = co2_neto_por_hora_kg.sum()

# Pregunta 4: ¿Por qué el neto es positivo si la red es 100% diesel?
respuesta = Porque los EVs son 44% más eficientes en CO2:
          Moto gasolina: 2.31 kg CO2/L × 2.86 L/100km = 6.61 kg CO2/100km
          Moto EV:       0.4521 kg CO2/kWh × 5 kWh/100km = 2.26 kg CO2/100km
          Ganancia:      6.61 - 2.26 = 4.35 kg CO2/100km = 44% más eficiente
```

---

## 📋 Checklist de Claridad

- ✅ `reduccion_directa_co2_kg` = SOLO cambio de combustible (gasolina → EV)
- ✅ `co2_grid_kwh` = SOLO costo de generar electricidad (diesel)
- ✅ `co2_neto_por_hora_kg` = Impacto REAL (reducción - grid)
- ✅ En documentación de código: comentarios muy claros
- ✅ En reports: siempre especificar *cuál* columna se está usando
- ✅ En rewards: preferir CO₂ neto para representar impacto real

---

## 🚀 Implementación en Código

Ver actualización en:  
**Archivo**: [chargers.py](src/dimensionamiento/oe2/disenocargadoresev/chargers.py)

**Líneas de comentarios actualizadas**:
- Líneas 265-330: Documentación de cálculo CO₂ con ejemplo
- Líneas 889-920: Código generación columnas con comentarios claros

**Comandos para verificar**:

```bash
# 1. Ver dataset generado
python -c "import pandas as pd; df=pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv',index_col=0); print('Reducción directa:', df['reduccion_directa_co2_kg'].sum()); print('CO2 grid:', df['co2_grid_kwh'].sum()); print('CO2 neto:', df['co2_neto_por_hora_kg'].sum())"

# 2. Validar dataset
python VALIDACION_DATASET_COMPLETO_v2026-02-16.py
```

---

**Generado**: 2026-02-16  
**Status**: ✅ LISTO PARA AGENTES RL
