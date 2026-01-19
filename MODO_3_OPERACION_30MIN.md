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

```
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
```

---

## Comportamiento de Observables en CityLearn

### Observable: `ev_charging_power_playa_motos_kw`

| Hora | Sesión | Motos Activas | Potencia Playa Motos | Potencia Playa Taxis | Total |
|------|--------|---------------|---------------------|---------------------|-------|
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

**Control RL**:

- Puede reducir potencia de Playa Motos: 224 kW → 150 kW (ej: cargar a menor velocidad)
- Puede reducir potencia de Playa Taxis: 48 kW → 30 kW
- Objetivo: Evitar pico de 272 kW (18:00-20:00)

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
```

### Schema Observables

```python
# Agregados (control de playas)
"ev_charging_power_total_kw"                    # 0-272 kW
"ev_charging_power_playa_motos_kw"              # 0-224 kW  
"ev_charging_power_playa_mototaxis_kw"          # 0-48 kW

# Individuales (monitoreo detallado)
"charger_MOTO_CH_001_power_kw"      # 0-8 kW
"charger_MOTO_CH_002_power_kw"      # 0-8 kW
...
"charger_MOTO_CH_112_power_kw"      # 0-8 kW

"charger_MOTO_TAXI_CH_113_power_kw" # 0-12 kW
"charger_MOTO_TAXI_CH_114_power_kw" # 0-12 kW
...
"charger_MOTO_TAXI_CH_128_power_kw" # 0-12 kW
```

---

## Capacidad Real vs Demanda

### Dimensionamiento OE2 ✅

| Métrica | Playa Motos | Playa Taxis | Total |
|---------|------------|-------------|-------|

## Dimensionamiento OE2 ✅

| Métrica | Playa Motos | Playa Taxis | Total |
|---------|------------|-------------|-------|
| **Chargers Físicos** | 112 | 16 | **128** |
| **Sockets Totales** | 112 (4 por charger) | 16 (4 por charger) | **128** |
| **Potencia/Socket** | 2 kW | 3 kW | - |
| **Potencia Pico** | 224 kW | 48 kW | **272 kW** |
| **PICO (4 horas)** | 900 motos | 130 taxis | **1030 veh** |
| **Función 1030** | Para dimensionar chargers | Para dimensionar chargers | **Cálculo de capacidad** |
| **Sesiones/Día** | 30 min | 30 min | 30 min |
| **Total diario (13h)** | 1600+ motos | 600+ taxis | **2200+ veh** |
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

✅ **128 chargers = capacidad fija (272 kW pico)**  
✅ **900 + 130 = 1030 veh pico (4 horas)** → Dimensionamiento de hardware  
✅ **2200+ veh totales (13 horas)** → Verdadera demanda diaria  
✅ **30 min por sesión = Modo 3 IEC 61851**  
✅ **No simultáneo: secuencial, multiplex, reutilizable**  

**Importancia para CityLearn**:

- El pico de 1030 veh en 4 horas determina qué potencia necesitas (272 kW)
- El total de 2200+ veh en 13 horas es lo que los chargers realmente atienden
- El agente RL ve potencia instantánea (0-272 kW) y optimiza scheduling de carga

Este es el **MODELO CORRECTO** para entrenamiento RL.
