# Arquitectura de Tomas Controlables Independientes - OE3

## Cambio Fundamental en Estructura

**ANTES (Incorrecto):**
- 32 cargadores × 4 sockets/cargador = 128 sockets
- Control: **Por cargador** (1 acción = potencia para todos sus 4 sockets)
- Problema: No permite control granular ni visibilidad del estado individual de EVs

**AHORA (Correcto):**
- **128 TOMAS CONTROLABLES INDEPENDIENTEMENTE**
  - 112 tomas para motos (2.0 kW cada una)
  - 16 tomas para mototaxis (3.0 kW cada una)
- Control: **Por toma** (1 acción = potencia para 1 toma específica)
- Ventaja: Control fino, visibilidad de estado de cada EV conectado

---

## Implicaciones para OE3

### 1. Espacio de Observación (Obs Space)

Cada toma tiene observable independiente:

```
Observables por toma (128 total):
├─ Toma 0-111 (Motos):
│  ├─ ev_connected: 0/1 (hay EV conectado?)
│  ├─ ev_state_of_charge: 0-100% (estado batería del EV)
│  ├─ power_setpoint: 0-2.0 kW (potencia actual)
│  └─ session_duration: minutos (cuánto lleva cargando)
│
└─ Toma 112-127 (Mototaxis):
   ├─ ev_connected: 0/1 (hay EV conectado?)
   ├─ ev_state_of_charge: 0-100% (estado batería del EV)
   ├─ power_setpoint: 0-3.0 kW (potencia actual)
   └─ session_duration: minutos (cuánto lleva cargando)

Observables globales:
├─ Solar generation: kW
├─ BESS SOC: %
├─ Grid import/export: kW
├─ Time features (hora, mes, día)
└─ Grid carbon intensity: kg CO₂/kWh
```

**Total Obs Space**: ~534 dimensiones (actualizado dinámicamente)

### 2. Espacio de Acción (Action Space)

Cada acción controla 1 toma independiente:

```
Acción i ∈ [0, 128):
  action_i ∈ [0, 1]  # Normalizado [0-1]
  
Interpretación:
  - action_i = 1.0 → Toma carga a máxima potencia
  - action_i = 0.5 → Toma carga a 50% potencia
  - action_i = 0.0 → Toma apagada

Potencia asignada:
  P_toma_i = action_i × P_max_toma_i
  
  P_max = 2.0 kW  si i ∈ [0, 112)    (motos)
  P_max = 3.0 kW  si i ∈ [112, 128)  (mototaxis)
```

**Total Action Space**: 128 dimensiones (una por toma)

### 3. Física del Sistema (CityLearn)

En cada timestep (1 hora):

```python
# Entrada: acción del agente
action = [a_0, a_1, ..., a_127]  # 128 valores [0-1]

# Cálculo de potencia por toma
for i in range(128):
    if ev_connected[i]:  # Si hay EV conectado
        P_max = 2.0 if i < 112 else 3.0
        power[i] = action[i] * P_max
        # Limitar por estado del EV
        if ev_soc[i] >= 100%:
            power[i] = 0  # EV lleno, no cargar
    else:
        power[i] = 0  # Sin EV, no hay carga

# Demanda total de carga
total_power = sum(power[i] for i in range(128))

# Energía cargada en ese timestep (1 hora)
energy_per_toma[i] = power[i] * 1 hour / efficiency
total_energy = sum(energy_per_toma[i] for i in range(128))

# Actualizar SOC de EVs conectados
for i in range(128):
    if ev_connected[i]:
        ev_soc[i] += energy_per_toma[i] / ev_battery_capacity[i]
        
# Validar demanda contra disponibilidad
if total_energy <= solar_generation + bess_discharge:
    # Surtida por solar + BESS
    grid_import = 0
else:
    # Déficit cubierto por grid
    deficit = total_energy - solar_generation - bess_discharge
    grid_import = deficit
```

---

## Recompensa Multiobjetivo

La recompensa vuelve a entrenar al agente para **controlar 128 tomas de forma independiente** minimizando CO₂:

```python
# Multiobjetivo (OE3)
r_co2 = (weighted_co2_emissions) / CO2_BASELINE          # 0.50
r_solar = (pv_direct_usage) / TOTAL_PV                  # 0.20
r_cost = -(electricity_cost) / MAX_COST                 # 0.10
r_ev = (ev_satisfaction) / MAX_EV_SATISFACTION          # 0.10
r_grid = -(grid_instability) / MAX_INSTABILITY          # 0.10

r_total = 0.50*r_co2 + 0.20*r_solar + 0.10*r_cost + 0.10*r_ev + 0.10*r_grid
```

Cada agente (SAC/PPO/A2C) aprende a:
1. **Priorizar PV → Tomas** (bajo CO₂)
2. **Balancear carga en horas pico** (respetando potencia disponible)
3. **Cargar desde BESS en horas nocturnas** (cuando solar = 0)
4. **Minimizar importación de grid** (alta intensidad CO₂)

---

## Restricciones de Control por Toma

Cada toma debe respetar:

| Restricción | Motos (112 tomas) | Mototaxis (16 tomas) |
|---|---|---|
| Potencia máxima | 2.0 kW | 3.0 kW |
| Voltaje | 400V 16A (Modo 3) | 400V 16A (Modo 3) |
| Batería típica | 2.0 kWh | 4.0 kWh |
| Tiempo carga típico | 1-2 hrs @ 2 kW | 1.5-2 hrs @ 3 kW |
| SOC máx permitido | 100% | 100% |
| SOC mín (inicio carga) | Cualquiera | Cualquiera |

---

## Despacho Priorizado (Dispatch Rules)

En caso de déficit de energía, aplicar:

```
1. PV directa → Tomas (si hay EVs + PV disponible)
2. BESS → Tomas (si hay EVs + BESS descargable)
3. Grid → Tomas (si hay EVs + déficit persistente)
```

Por cada toma:
```python
def assign_power_to_toma(toma_id, action, solar_available, bess_available):
    """
    Asigna potencia a una toma según disponibilidad (dispatch rule).
    """
    # Potencia solicitada por el agente
    P_requested = action * P_max[toma_id]
    
    # Intentar surtir de PV primero
    P_from_pv = min(P_requested, solar_available)
    
    # Restante de BESS
    P_from_bess = min(P_requested - P_from_pv, bess_available)
    
    # Restante de grid (costo CO₂)
    P_from_grid = max(P_requested - P_from_pv - P_from_bess, 0)
    
    # Potencia total asignada (respeta disponibilidad)
    P_total = P_from_pv + P_from_bess + P_from_grid
    
    return {
        'toma_id': toma_id,
        'power_pv': P_from_pv,
        'power_bess': P_from_bess,
        'power_grid': P_from_grid,
        'total': P_total,
        'source_priority': 'PV > BESS > Grid'
    }
```

---

## Integración CityLearn v2.5

Cuando dataset_builder genera schema para OE3:

```json
{
  "buildings": [
    {
      "name": "EV_Charging_Playas",
      "equipment": {
        "solar_pv": { "capacity_kw": 4050 },
        "bess": { "capacity_kwh": 2000, "power_kw": 1200 },
        "ev_chargers": [
          {
            "charger_id": "TOMA_0",     // Toma 0 (moto)
            "type": "moto",
            "power_kw": 2.0,
            "controllable": true
          },
          {
            "charger_id": "TOMA_1",     // Toma 1 (moto)
            "type": "moto",
            "power_kw": 2.0,
            "controllable": true
          },
          // ... tomas 2-111 (motos)
          {
            "charger_id": "TOMA_112",   // Toma 112 (mototaxi)
            "type": "mototaxi",
            "power_kw": 3.0,
            "controllable": true
          },
          // ... tomas 113-127 (mototaxis)
        ]
      }
    }
  ]
}
```

---

## Checklist para Implementación en OE3

- [ ] **Obs Space**: Actualizar a 128 observables (1 por toma) + globales
- [ ] **Action Space**: Confirmar 128 acciones (1 por toma)
- [ ] **Rewards**: Validar que recompensa vea estado de cada toma
- [ ] **Dispatch**: Implementar asignación potencia por toma
- [ ] **Dataset Builder**: Generar schema con 128 tomas como `controllable=true`
- [ ] **Training**: Entrenar SAC/PPO/A2C con 128 acciones
- [ ] **Validation**: Verificar que agentes aprenden a balancear 128 tomas

---

## Resumen

| Aspecto | Valor |
|---|---|
| **Tomas Motos** | 112 (2.0 kW c/u) |
| **Tomas Mototaxis** | 16 (3.0 kW c/u) |
| **Total Tomas Controlables** | **128** |
| **Potencia Total** | 272 kW |
| **Obs per Toma** | 4-5 (connected, SOC, power, duration) |
| **Obs Globales** | ~12-15 (solar, BESS, grid, time) |
| **Total Obs Space** | ~534 dims |
| **Action Space** | 128 dims (una acción por toma) |
| **Despacho** | PV → BESS → Grid (por toma) |

Esta arquitectura permite que el agente RL **tome decisiones granulares y globales simultáneamente**, optimizando cada toma viendo estado individual de EV.
