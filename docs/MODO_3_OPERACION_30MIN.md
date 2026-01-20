# Operación Modo 3 IEC 61851 - Chargers 128 Sesiones de 30 Minutos

## Clarificación de Capacidad vs Demanda

### ❌ Interpretación INCORRECTA

- "1030 vehículos simultáneamente cargando durante 13 horas" ← **FALSO**
- "Los chargers solo atienden 1030 vehículos al día" ← **FALSO**
- "Cada charger tiene su propia flota fija" ← **FALSO**

### ✅ Interpretación CORRECTA

- **128 chargers físicos** = 272 kW total
- **Pico de 4 horas**: 900 motos + 130 mototaxis = 1030 veh (para DIMENSIONAR)
- **Operación TOTAL**: Los MISMOS 128 chargers atienden MUCHO MÁS durante 13 horas (9am-10pm)
- **Modo 3 (IEC 61851)**: Carga lenta, segura, cada 30 min → nuevo vehículo
- **Multiplex**: 13 horas = 26 intervalos de 30 min → muchos más vehículos por charger

---

## Timeline Operativo - Playa Motos (Ejemplo)

```text
╔═══════════════════════════════════════════════════════════════════════════╗
║                    PLAYA MOTOS: 112 CHARGERS (224 kW)                    ║
║                        DURANTE 13 HORAS (9am-10pm)                       ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  HORAS 9-13 (PICO - 4H): Máxima demanda = 900 motos                     ║
║  ─────────────────────────────────────────────────────────────────────────║
║                                                                           ║
║  9:00-9:30 am   │ Sesión 1: ~115 motos en los 112 chargers @ 224 kW   ║
║  9:30-10:00 am  │ Sesión 2: ~115 motos DIFERENTES @ 224 kW              ║
║  10:00-10:30 am │ Sesión 3: ~115 motos DIFERENTES @ 224 kW              ║
║  10:30-11:00 am │ Sesión 4: ~115 motos DIFERENTES @ 224 kW              ║
║  11:00-11:30 am │ Sesión 5: ~115 motos DIFERENTES @ 224 kW              ║
║  11:30-12:00 pm │ Sesión 6: ~115 motos DIFERENTES @ 224 kW              ║
║  12:00-12:30 pm │ Sesión 7: ~115 motos DIFERENTES @ 224 kW              ║
║  12:30-1:00 pm  │ Sesión 8: ~115 motos DIFERENTES @ 224 kW              ║
║                 │ SUBTOTAL PICO (4H): 8 sesiones × 115 = ~920 motos    ║
║  ─────────────────────────────────────────────────────────────────────────║
║                                                                           ║
║  HORAS 13-21 (TARDE/NOCHE - 9H): Demanda variable                       ║
║  ─────────────────────────────────────────────────────────────────────────║
║                                                                           ║
║  1:00-1:30 pm   │ Sesión 9: ~50 motos @ 160 kW                          ║
║  1:30-2:00 pm   │ Sesión 10: ~50 motos @ 160 kW                         ║
║  ...            │ ... (Continúa con demanda decreciente)                 ║
║  9:30-10:00 pm  │ Sesión 26: ~20 motos @ 65 kW                          ║
║                 │ SUBTOTAL TARDE (9H): 18 sesiones × ~40 = ~720 motos  ║
║                                                                           ║
║  ─────────────────────────────────────────────────────────────────────────║
║  TOTAL 13 HORAS: ~1640 motos atendidas                                   ║
║  (Mucho más que pico de 900 motos para dimensionamiento)                 ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```text

---

## Arquitectura de Control - Chargers Individuales

### 🎮 Controlabilidad por Charger

Cada **charger es una unidad controlable independiente** en el momento de carga:

**Playa Motos**:

- 112 chargers = 112 tomas controlables
- Cada toma: potencia 0-2 kW (reducción de velocidad, pausa, etc.)
- Control granular: decidir qué chargers cargan a potencia máxima vs reducida
- Observable: `charger_MOTO_CH_001_power_kw`, ..., `charger_MOTO_CH_112_power_kw`

**Playa Mototaxis**:

- 16 chargers = 16 tomas controlables
- Cada toma: potencia 0-3 kW (reducción de velocidad, pausa, etc.)
- Control granular: decidir qué chargers cargan a potencia máxima vs reducida
- Observable: `charger_MOTO_TAXI_CH_113_power_kw`, ..., `charger_MOTO_TAXI_CH_128_power_kw`

### 📊 Niveles de Control en CityLearn

 | Nivel | Observable | Rango | Control |
 | ------- | ----------- | ------- | --------- |
 | **Agregado Total** | `ev_charging_power_total_kw` | 0-272 kW | Potencia global |
 | **Playa** | `ev_charging_power_playa_motos_kw` | 0-224 kW | Suma de 112 chargers |
 | **Playa** | `ev_charging_power_playa_mototaxis_kw` | 0-48 kW | Suma de 16 chargers |
 | **Individual** | `charger_MOTO_CH_001_power_kw` | 0-2 kW | 1 charger específico |
 | **Individual** | `charger_MOTO_TAXI_CH_128_power_kw` | 0-3 kW | 1 charger específico |

### Acción RL: Control Individual vs Agregado

**Opción 1: Control por playa** (agregado):

```python
# Agent decide: reducir potencia playa motos a 160 kW
action = {"playa_motos_power": 0.71}  # 160/224 = 71%
# CityLearn distribuye entre 112 chargers proporcionalmente
```text

**Opción 2: Control individual** (granular):

```python
# Agent decide: reducir solo 20 chargers, dejar 92 a máximo
action = {"MOTO_CH_001": 0.5,  # 1 kW en lugar de 2 kW
          "MOTO_CH_002": 0.5,  # ... y así 20 chargers
          ...
          "MOTO_CH_021": 0.5}
# Resultado: 92 chargers × 2kW + 20 chargers × 1kW = 204 kW (en lugar de 224)
```text

---

 | Hora | Sesión | Motos Activas | Potencia Playa Motos | Potencia Playa Mototaxis | Total |
 | ------ | -------- | --------------- | --------------------- | --------------------- | ------- |
 | 9:00-9:30 | 1 | 35-40 | 224 kW | 0 kW | 224 kW |
 | 9:30-10:00 | 2 | 35-40 | 224 kW | 0 kW | 224 kW |
 | 10:00-10:30 | 3 | 35-40 | 224 kW | 15 kW | 239 kW |
 | ... | ... | ... | ... | ... | ... |
 | 18:00-18:30 | 17 | 35-40 | 224 kW | 32 kW | 256 kW (PICO) |
 | 18:30-19:00 | 18 | 35-40 | 224 kW | 48 kW | 272 kW (MÁXIMO) |
 | 19:00-19:30 | 19 | 35-40 | 224 kW | 48 kW | 272 kW (MÁXIMO) |
 | 19:30-20:00 | 20 | 35-40 | 224 kW | 48 kW | 272 kW (MÁXIMO) |
 | 20:00-20:30 | 21 | 20-30 | 160 kW | 48 kW | 208 kW (descenso) |
 | 20:30-21:00 | 22 | 15-20 | 120 kW | 45 kW | 165 kW |

### Observables Individuales

- `charger_MOTO_CH_001_power_kw`: Sesión 1 = 2 kW, Sesión 2 = 2 kW, ...
- `charger_MOTO_CH_002_power_kw`: Sesión 1 = 2 kW, Sesión 2 = 2 kW, ...
- ... (112 chargers similares en Playa Motos)
- `charger_MOTO_TAXI_CH_113_power_kw`: Empieza a las 14:00, 3 kW/socket
- ... (16 chargers en Playa Mototaxis)

**Control RL - Acciones disponibles**:

**A nivel de charger individual**:

- Reducir potencia: 2 kW (Motos) → 1 kW, 0.5 kW, o pausa
- Reducir potencia: 3 kW (Taxis) → 1.5 kW, 0.75 kW, o pausa
- Seleccionar qué chargers operan a máxima velocidad vs reducida
- Objetivo: Distribuir carga sin exceder 272 kW pico

**A nivel de playa**:

- Limitar potencia agregada: Playa Motos máx 200 kW (en lugar de 224)
- Limitar potencia agregada: Playa Mototaxis máx 40 kW (en lugar de 48)
- CityLearn distribuye internamente entre los chargers

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
 | **Función 1030** | Para dimensionar chargers | Para dimensionar chargers | **Cálculo de capacidad** |
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

### Reward Esperado

- **Baseline** (sin control): Pico 272 kW, CO2 ∝ 3252 kWh
- **Con RL A2C**: Pico 200 kW, CO2 reducido 15%
- **Con RL PPO**: Pico 180 kW, CO2 reducido 20%
- **Con RL SAC**: Pico 160 kW, CO2 reducido 25%, Fairness 0.72

---

## Conclusión

✅ **128 tomas controlables** (112 Motos + 16 Taxis)
✅ **Cada toma es charger individual controlable en tiempo real**
✅ **Pico 1030 veh (4h 9am-1pm)** → dimensiona 272 kW
✅ **Total 2200+ veh (13h 9am-10pm)** → multiplex de 30 min
✅ **Control: agregado por playa O individual por charger**
✅ **Modo 3 IEC 61851: carga lenta, segura, estacionamiento**

**Para CityLearn**:

- 3 observables agregados (total, motos, taxis)
- 128 observables individuales (cada charger/toma)
- Acciones RL: decidir potencia de chargers individuales
- Evitar exceso de potencia sin sacrificar fairness

Este es el **MODELO CORRECTO** para control granular en RL.

Este es el **MODELO CORRECTO** para entrenamiento RL.
