# Operación Modo 3 IEC 61851 - Chargers 128 Sesiones de 30 Minutos

## Actualización: 2026-01-24

### Configuración de Infraestructura

  | Parámetro | Valor |  
|-----------|-------|
  | Cargadores físicos | 32 (28 motos + 4 mototaxis) |  
  | Tomas por cargador | 4 |  
  | **Total tomas** | **128** (112 motos + 16 mototaxis) |  
  | Potencia motos | 2.0 kW/toma |  
  | Potencia mototaxis | 3.0 kW/toma |  
  | **Potencia total** | **272 kW** (224 + 48) |  
  | Horario operación | 9 AM - 10 PM (13 horas) |  
  | Duración sesión | 30 minutos (Modo 3) |  

---

## Tabla 13 OE2 - Escenarios de Dimensionamiento

  | Escenario | PE | FC | Cargadores | Tomas | Energía/Día | Vehíc/Día | Vehíc/20años |  
|-----------|---:|---:|----------:|------:|------------:|----------:|-------------:|
  | CONSERVADOR | 0.10 | 0.40 | 4 | 16 | 231 kWh | 257 | 1,876,100 |  
  | MEDIANO | 0.50 | 0.60 | 20 | 80 | 1,739 kWh | 1,287 | 9,395,100 |  
  ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
  | MÁXIMO | 1.00 | 1.00 | 35 | 140 | 5,800 kWh | 2,575 | 18,797,500 |  

> **Nota**: PE = Probabilidad de Evento de carga, FC = Factor de Carga (% de
batería a recargar)

---

## Vehículos Cargados - Escenario RECOMENDADO

### Datos de Horas Pico (6pm-10pm)

- **~900 motos** en 4 horas pico (PE=1.0)
- **~130 mototaxis** en 4 horas pico (PE=1.0)
- Factor pico: 40% de demanda diaria
- Escenario RECOMENDADO usa PE=0.65

### Vehículos Cargados por Período (RECOMENDADO PE=0.65)

  | Período | Motos | Mototaxis | Total |  
|---------|------:|----------:|------:|
  | **Día** | 1,462 | 210 | **1,672** |  
  | **Mes** | 43,860 | 6,300 | **50,160** |  
  | **Año** | 533,630 | 76,650 | **610,280** |  
  | **20 años** | 10,672,600 | 1,533,000 | **12,205,600** |  

### Energía Cargada por Período (RECOMENDADO)

  | Período | Motos | Mototaxis | Total |  
|---------|------:|----------:|------:|
  | **Día** | 2,193 kWh | 630 kWh | **2,823 kWh** |  
  | **Mes** | 65,790 kWh | 18,900 kWh | **84,690 kWh** |  
  | **Año** | 800,445 kWh | 229,950 kWh | **1,030,395 kWh** |  
  | **20 años** | 16,009 MWh | 4,599 MWh | **20,608 MWh** |  

---

## Clarificación de Capacidad vs Demanda

### ❌ Interpretación INCORRECTA

- "1030 vehículos simultáneamente cargando durante 13 horas" ← **FALSO**
- "Los chargers solo atienden 1030 vehículos al día" ← **FALSO**
- "Cada charger tiene su propia flota fija" ← **FALSO**

### ✅ Interpretación CORRECTA

- **128 tomas físicas** = 272 kW total
- **Pico de 4 horas**: ~900 motos + ~130 mototaxis (para DIMENSIONAR, PE=1.0)
- **Operación RECOMENDADO (PE=0.65)**: 128 tomas atienden **~1,672
  - vehículos/día**
- **Operación MÁXIMO (PE=1.0)**: 128 tomas atienden **~2,575 vehículos/día**
- **Modo 3 (IEC 61851)**: Carga lenta, segura, cada 30 min → nuevo vehículo
- **Multiplex**: 13 horas = 26 intervalos de 30 min → muchos más vehículos por
  - toma

---

## Timeline Operativo - Playa Motos (Ejemplo)

```text
╔═══════════════════════════════════════════════════════════════════════════╗
║             PLAYA MOTOS: 28 CARGADORES × 4 TOMAS = 112 TOMAS             ║
║                        DURANTE 13 HORAS (9am-10pm)                       ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  HORAS PICO (6pm-10pm - 4H): ~900 motos (40% de demanda diaria)         ║
║  ─────────────────────────────────────────────────────────────────────────║
║                                                                           ║
║  6:00-6:30 pm   │ Sesión 1: ~115 motos en las 112 tomas @ 224 kW       ║
║  6:30-7:00 pm   │ Sesión 2: ~115 motos DIFERENTES @ 224 kW              ║
║  7:00-7:30 pm   │ Sesión 3: ~115 motos DIFERENTES @ 224 kW              ║
║  7:30-8:00 pm   │ Sesión 4: ~115 motos DIFERENTES @ 224 kW              ║
║  8:00-8:30 pm   │ Sesión 5: ~115 motos DIFERENTES @ 224 kW              ║
║  8:30-9:00 pm   │ Sesión 6: ~115 motos DIFERENTES @ 224 kW              ║
║  9:00-9:30 pm   │ Sesión 7: ~115 motos DIFERENTES @ 224 kW              ║
║  9:30-10:00 pm  │ Sesión 8: ~115 motos DIFERENTES @ 224 kW              ║
║                 │ SUBTOTAL PICO (4H): 8 sesiones × 115 = ~900 motos     ║
║  ─────────────────────────────────────────────────────────────────────────║
║                                                                           ║
║  HORAS FUERA PICO (9am-6pm - 9H): ~1,350 motos (60% de demanda diaria) ║
║  ─────────────────────────────────────────────────────────────────────────║
║                                                                           ║
║  9:00-9:30 am   │ Sesión: ~80 motos @ 160 kW                            ║
║  ...            │ ... (Continúa con demanda variable)                    ║
║  5:30-6:00 pm   │ Sesión: ~75 motos @ 150 kW                            ║
║                 │ SUBTOTAL FUERA PICO (9H): ~1,350 motos                ║
║                                                                           ║
║  ─────────────────────────────────────────────────────────────────────────║
║  TOTAL 13 HORAS: ~2,250 motos atendidas (RECOMENDADO)                    ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```bash

---

## Arquitectura de Control - Tomas Individuales

### 🎮 Controlabilidad por Toma

Cada **toma es una unidad controlable independiente** en el momento de carga:

**Playa Motos (28 cargadores × 4 tomas = 112 tomas)**:

- 112 tomas = 112 unidades controlables
- Cada toma: potencia 0-2 kW (reducción de velocidad, pausa, etc.)
- Control granular: decidir qué tomas cargan a potencia máxima vs reducida
- Observable: `MOTO_CH_001_ev_charging_power`, ...,
  - `MOTO_CH_112_ev_charging_power`

**Playa Mototaxis (4 cargadores × 4 tomas = 16 tomas)**:

- 16 tomas = 16 unidades controlables
- Cada toma: potencia 0-3 kW (reducción de velocidad, pausa, etc.)
- Control granular: decidir qué tomas cargan a potencia máxima vs reducida
- Observable: `MOTO_TAXI_CH_113_ev_charging_power`, ...,
  - `MOTO_TAXI_CH_128_ev_charging_power`

### 📊 Niveles de Control en CityLearn

  | Nivel | Observable | Rango | Control |  
| ------- | ----------- | ------- | --------- |
  | **Agregado Total** | `ev_charging_power_total_kw` | 0-272 kW | Potencia global |  
  | **Playa** | `ev_charging_power_playa_motos_kw` | 0-224 kW | Suma de 112 tomas |  
  | **Playa** | `ev_charging_power_playa_mototaxis_kw` | 0-48 kW | Suma de 16 tomas |  
  | **Individual** | `MOTO_CH_001_ev_charging_power` | 0-2 kW | 1 toma específica |  
  | **Individual** | `MOTO_TAXI_CH_128_ev_charging_power` | 0-3 kW | 1 toma específica |  

### Acción RL: Control Individual por Toma (OE3)

**Arquitectura OE3: 128 acciones individuales**:

```python
# Agent decide: controlar cada toma independientemente
action = {"action_charger_1": 0.5,   # MOTO_CH_001: 1 kW
          "action_charger_2": 1.0,   # MOTO_CH_002: 2 kW (máx)
          ...
          "action_charger_128": 0.7} # MOTO_TAXI_CH_128: 2.1 kW
# Total 128 acciones + 1 BESS = 129 acciones
```bash

          "MOTO_CH_002": 0.5,  # ... y así 20 chargers
          ...
          "MOTO_CH_021": 0.5}

# Resultado: 92 chargers × 2kW + 20 chargers × 1kW = 204 kW (en lugar de 224)

```text

---

  | Hora | Sesión | Motos Activas | Potencia Playa Motos | Potencia Playa Mototaxis | Total |  
| ------ | -------- | --------------- | --------------------- | --------------------- | ------- |
  | 9:00-9:30 | 1 | 35-40 | 70 kW | 0 kW | 70 kW |  
  | 9:30-10:00 | 2 | 40-50 | 90 kW | 0 kW | 90 kW |  
  | 10:00-10:30 | 3 | 50-60 | 110 kW | 15 kW | 125 kW |  
  | ... | ... | ... | ... | ... | ... |  
  | 18:00-18:30 | 17 | 100-112 | 224 kW | 32 kW | 256 kW (PICO) |  
  | 18:30-19:00 | 18 | 112 | 224 kW | 48 kW | 272 kW (MÁXIMO) |  
  | 19:00-19:30 | 19 | 112 | 224 kW | 48 kW | 272 kW (MÁXIMO) |  
  | 19:30-20:00 | 20 | 112 | 224 kW | 48 kW | 272 kW (MÁXIMO) |  
  | 20:00-20:30 | 21 | 80-100 | 180 kW | 48 kW | 228 kW (descenso) |  
  | 21:30-22:00 | 26 | 20-30 | 50 kW | 20 kW | 70 kW |  

### Observables Individuales (OE3: 264 observables)

- `MOTO_CH_001_ev_charging_power`: Sesión = 0-2 kW
- `MOTO_CH_002_ev_charging_power`: Sesión = 0-2 kW
- ... (112 tomas en Playa Motos)
- `MOTO_TAXI_CH_113_ev_charging_power`: 0-3 kW
- ... (16 tomas en Playa Mototaxis)

**Control RL - Acciones disponibles (OE3: 129 acciones)**:

**A nivel de toma individual (128 acciones)**:

- `action_charger_1` ... `action_charger_128`
- Cada acción: 0.0 (apagar) hasta 1.0 (potencia máxima)
- Motos: 0-2 kW por toma
- Mototaxis: 0-3 kW por toma
- Objetivo: Distribuir carga sin exceder 272 kW pico

**BESS (1 acción)**:

- `action_battery`: Control de carga/descarga batería
- Objetivo: Almacenar solar, reducir picos

**Control RL esperado**:

- Monitorear power por charger individual
- Tomar decisiones de control por charger individual durante sesión
- Evitar exceso total sin sacrificar servicio (fairness entre vehículos)

---

## Parámetros de CityLearn

### Chargers en schema_with_128_chargers.json

```json
{
  "charger_id": "MOTO_CH_001",
  "playa": "Playa_Motos",
  "location": "Motos Zone 1",
  "sockets": 4,
  "power_per_socket_kw": 2.0,
  "total_power_kw": 8.0,
  "charging_mode": "Mode 3 (IEC 61851)",
  "session_duration_minutes": 30,
  "daily_sessions": "~26 sesiones",
  "annual_profile": "chargers_hourly_profiles.csv"
}
```text

### Schema Observables

```python
# Agregados (control de playas)
"ev_charging_power_total_kw"                    # 0-272 kW
"ev_charging_power_playa_motos_kw"              # 0-224 kW
"ev_charging_power_playa_mototaxis_kw"          # 0-48 kW

# Individuales (control GRANULAR - cada charger)
"charger_MOTO_CH_001_power_kw"      # 0-2 kW (1 toma)
"charger_MOTO_CH_002_power_kw"      # 0-2 kW (1 toma)
...
"charger_MOTO_CH_112_power_kw"      # 0-2 kW (1 toma)

"charger_MOTO_TAXI_CH_113_power_kw" # 0-3 kW (1 toma)
"charger_MOTO_TAXI_CH_114_power_kw" # 0-3 kW (1 toma)
...
"charger_MOTO_TAXI_CH_128_power_kw" # 0-3 kW (1 toma)

# TOTAL: 3 agregados + 128 individuales = 131 observables EV
```text

---

## Capacidad Real vs Demanda

### Dimensionamiento OE2 ✅

  | Métrica | Playa Motos | Playa Mototaxis | Total |  
| --------- | ------------ | ----------------- | ------- |
  | **Chargers Físicos** | 112 | 16 | **128** |  
  | **Sockets Totales** | 112 (4 por charger) | 16 (4 por charger) | **128** |  
  | **Potencia/Socket** | 2 kW | 3 kW | - |  
  | **Potencia Pico** | 224 kW | 48 kW | **272 kW** |  
  | **PICO (4 horas)** | 900 motos | 130 mototaxis | **1030 veh** |  
  ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
  | **Sesiones/Día** | 30 min | 30 min | 30 min |  
  | **Total diario (13h)** | 1600+ motos | 600+ mototaxis | **2200+ veh** |  
  | **Horas Operación** | 9am-10pm (13h) | 9am-10pm (13h) | 9am-10pm |  

---

## Importancia para Entrenamiento RL

### Observaciones para el Agente

1. **Agregados (nivel de playa)**:
   - `ev_charging_power_playa_motos_kw` → Puede controlar que NO alcance 224 kW
   - `ev_charging_power_playa_mototaxis_kw` → Puede controlar que NO alcance 48 kW

2. **Individuales (nivel de charger)**:
   - `charger_MOTO_CH_001_power_kw`, etc. → Monitorea utilización específica
   - Permite tomar decisiones por charger (si fuera necesario)

### Acciones de Control RL

- **Reducir velocidad de carga**: 2 kW → 1 kW en Playa Motos (riego de exceder pico)
- **Pausar sesión**: Esperar 10 min antes de iniciar sesión siguiente
- **Transferir sesiones**: Si ambas playas están al máximo, meter mototaxis en prime time

### Reward Esperado (Escenario RECOMENDADO: 905 kWh/día)

- **Baseline** (sin control): Pico 272 kW, Energía ~905 kWh/día
- **Con RL A2C**: Pico 200 kW, CO2 reducido 15%
- **Con RL PPO**: Pico 180 kW, CO2 reducido 20%
- **Con RL SAC**: Pico 160 kW, CO2 reducido 25%, Fairness 0.72

---

## Conclusión

✅ **128 tomas controlables** (112 Motos + 16 Taxis)
✅ **32 cargadores físicos** (28 Motos + 4 Taxis, 4 tomas c/u)
✅ **Pico 4h (6pm-10pm)**: ~900 motos + ~130 mototaxis
✅ **Total/día**: ~2,575 vehículos (RECOMENDADO)
✅ **Control: individual por toma (128 acciones)**
✅ **Modo 3 IEC 61851: carga lenta, segura, 30 min/sesión**

**Para CityLearn**:

- 3 observables agregados (total, motos, taxis)
- 128 observables individuales (cada charger/toma)
- Acciones RL: decidir potencia de chargers individuales
- Evitar exceso de potencia sin sacrificar fairness

Este es el **MODELO CORRECTO** para control granular en RL.

Este es el **MODELO CORRECTO** para entrenamiento RL.
