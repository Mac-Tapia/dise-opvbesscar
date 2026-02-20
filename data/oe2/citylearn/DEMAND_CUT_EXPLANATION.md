
# DATASET PARA AGENTE RL - DEMANDA CORTADA POR BESS (v5.4)

## Contexto
El BESS ha sido pre-optimizado en OE2 (Dimensionamiento) para:
- Cubrir 100% de la demanda EV (motos y mototaxis)
- Realizar peak shaving del MALL en horas punta
- Maximizar autosuficiencia renovable

## Demanda "Cortada" = Demanda Original - Contribución BESS

### Columnas para el Agente RL

**non_shiftable_load:** load_after_bess_kwh
- Demanda total después de restar la contribución del BESS
- = ev_demand_after_bess_kwh + mall_demand_after_bess_kwh
- Representa lo que el agente debe gestionar con EV chargers + grid

**solar_generation:** pv_kwh
- Generación PV horaria (no modificada)
- El agente puede usar este PV para cubrir demanda cortada

### Estadísticas Típicas (Año 2024)

Total demanda original:         1,645,295 kWh
├─ EV:                            769,295 kWh
└─ MALL:                          876,000 kWh

Total demanda cortada (c/ BESS):   1,181,820 kWh
├─ EV cortada:                     305,820 kWh (60% reducida por BESS)
└─ MALL cortada:                   876,000 kWh (0% peak shaving en syn. data)

Impacto BESS:
- Reduce demanda EV en 60.2% (463,476 kWh cubiertos)
- Reduce demanda MALL a través de peak shaving
- Resultado: Agente ve demanda ~28% menor que original

### Cómo Usar en CityLearn

```python
import pandas as pd
from citylearn import CityLearn

# El dataset ya contiene demanda cortada
# No se requiere transformación adicional

env = CityLearn(
    schema="citylearn/schema.json",
    central_agent=False,
    verbose=False
)

# Entrenar agente
agent.learn(env, timesteps=100000)
```

### Verificación de Consistencia

Cada hora debe cumplir:
- non_shiftable_load = pv_to_ev + pv_to_mall + grid_import
- (Cuando demanda_cortada es considerada sin BESS en el numerador)

### Notas Importantes

1. El BESS y sus acciones NO están en este dataset
   - Es pre-optimizado, no controlable por el agente
   
2. El agente ve una demanda REDUCIDA
   - Esto es correcto: el BESS ya manejó parte de ella
   
3. Objetivo del agente: minimizar grid_import de demanda_cortada
   - Meta: grid_import → 0 (máxima autosuficiencia renovable)

---
Dataset generado: 2026-02-18 (v5.4)
