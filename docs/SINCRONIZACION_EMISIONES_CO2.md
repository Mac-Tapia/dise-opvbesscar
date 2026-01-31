# Sincronización de Parámetros de Emisiones CO₂

**Última actualización**: 2026-01-30

## Constantes Centralizadas

Todas las constantes de emisiones están definidas en:
- **Código**: `src/iquitos_citylearn/oe3/emissions_constants.py` (EMISIONES singleton)
- **Config**: `configs/default.yaml` → `oe3.emissions` + `oe3.co2_emissions`

## Valores Sincronizados

### 1. Factor de Emisión de la Red Eléctrica
```yaml
# configs/default.yaml
oe3.co2_emissions.grid_import_factor_kg_kwh: 0.4521  # kg CO₂/kWh
oe3.grid.carbon_intensity_kg_per_kwh: 0.4521          # kg CO₂/kWh
```

```python
# emissions_constants.py
GRID_CO2_FACTOR_KG_PER_KWH = 0.4521  # kg CO₂/kWh
```

**Fuente**: Central térmica aislada de Iquitos (generación diesel)

### 2. Eficiencia Vehículos Eléctricos
```yaml
# configs/default.yaml
oe3.emissions.km_per_kwh: 35.0  # km/kWh
```

```python
# emissions_constants.py
EV_KM_PER_KWH = 35.0  # km/kWh
```

**Referencia**: Motos/mototaxis eléctricas típicas

### 3. Eficiencia Vehículos de Combustión
```yaml
# configs/default.yaml
oe3.emissions.km_per_gallon: 120.0  # km/galón
```

```python
# emissions_constants.py
ICE_KM_PER_GALLON = 120.0  # km/galón
```

**Referencia**: Motos/mototaxis a gasolina promedio

### 4. Emisiones de Combustión
```yaml
# configs/default.yaml
oe3.emissions.kgco2_per_gallon: 8.9  # kg CO₂/galón
```

```python
# emissions_constants.py
ICE_KGCO2_PER_GALLON = 8.9  # kg CO₂/galón
```

**Fuente**: Factor estándar EPA para gasolina (8.887 kg CO₂/galón)

## Archivos a Sincronizar

### Configuración YAML
- ✅ `configs/default.yaml`
- ✅ `configs/default_optimized.yaml`
- ✅ `configs/sac_ppo_only.yaml`

### Código Python
- ✅ `src/iquitos_citylearn/oe3/emissions_constants.py` (FUENTE DE VERDAD)
- ✅ `src/iquitos_citylearn/oe3/rewards.py` → `IquitosContext`
- ✅ `src/iquitos_citylearn/oe3/agents/sac.py` → `SACConfig`
- ✅ `src/iquitos_citylearn/oe3/agents/ppo_sb3.py` → `PPOConfig`
- ✅ `src/iquitos_citylearn/oe3/agents/a2c_sb3.py` → `A2CConfig`
- ✅ `src/iquitos_citylearn/oe3/dispatcher.py`
- ✅ `src/iquitos_citylearn/oe3/baseline_simulator.py`

## Cálculos Derivados

### CO₂ por km (vehículo de combustión)
```
co2_per_km = kgco2_per_gallon / km_per_gallon
           = 8.9 / 120.0
           = 0.0742 kg CO₂/km
```

### CO₂ por km (vehículo eléctrico desde grid)
```
kwh_per_km = 1 / km_per_kwh = 1 / 35.0 = 0.0286 kWh/km
co2_per_km = kwh_per_km × grid_co2_factor
           = 0.0286 × 0.4521
           = 0.0129 kg CO₂/km
```

### Reducción de CO₂ por km (EV vs ICE)
```
reduction = co2_ice - co2_ev
          = 0.0742 - 0.0129
          = 0.0613 kg CO₂/km
          = 61.3 g CO₂/km (83% de reducción)
```

## Componentes de CO₂ en el Reward

El reward multi-objetivo ahora incluye:

### 1. CO₂ Directo (Grid Import)
```python
co2_grid_kg = grid_import_kwh × 0.4521
```

### 2. CO₂ Evitado Indirecto (Solar)
```python
co2_avoided_indirect_kg = solar_consumed_kwh × 0.4521
```
**Interpretación**: Solar que se consume evita importar energía del grid térmico

### 3. CO₂ Evitado Directo (EVs)
```python
total_km = ev_charging_kwh × 35.0
gallons_avoided = total_km / 120.0
co2_avoided_direct_kg = gallons_avoided × 8.9
```
**Interpretación**: EVs cargados evitan el uso de motos/mototaxis a gasolina

### 4. CO₂ Neto
```python
co2_net_kg = co2_grid_kg - (co2_avoided_indirect_kg + co2_avoided_direct_kg)
```

**Objetivo del agente**: Minimizar `co2_net_kg` (puede ser negativo = carbono neto negativo)

## Validación de Sincronización

Ejecutar script de validación:

```bash
python scripts/validate_emissions_config.py
```

Este script verifica que:
1. Todos los YAMLs tengan los mismos valores
2. Las constantes en código coincidan con los YAMLs
3. Los cálculos derivados sean consistentes

## Checklist de Modificación

Si necesitas cambiar algún parámetro de emisiones:

1. ✅ Actualizar `emissions_constants.py` (FUENTE DE VERDAD)
2. ✅ Actualizar `configs/default.yaml` → `oe3.emissions` + `oe3.co2_emissions`
3. ✅ Actualizar `configs/default_optimized.yaml`
4. ✅ Actualizar `configs/sac_ppo_only.yaml`
5. ✅ Actualizar `rewards.py` → `IquitosContext` (si aplica)
6. ✅ Ejecutar `python scripts/validate_emissions_config.py`
7. ✅ Relanzar entrenamiento con `--skip-baseline` para usar nuevos valores

## Ejemplos de Uso

### Calcular CO₂ evitado por 100 kWh de carga EV
```python
from iquitos_citylearn.oe3.emissions_constants import calculate_ev_co2_avoided

co2_avoided = calculate_ev_co2_avoided(100.0)  # kWh
# Resultado: 28.98 kg CO₂ evitado
```

### Calcular CO₂ evitado por 50 kWh de solar
```python
from iquitos_citylearn.oe3.emissions_constants import calculate_solar_co2_avoided

co2_avoided = calculate_solar_co2_avoided(50.0)  # kWh
# Resultado: 22.61 kg CO₂ evitado
```

## Referencias

- **Grid factor**: Ministerio de Energía y Minas - Perú (central térmica Iquitos)
- **EV efficiency**: Datos de fabricantes de motos/mototaxis eléctricas
- **ICE efficiency**: Estadísticas INEI Perú - parque vehicular Loreto
- **ICE emissions**: EPA (US Environmental Protection Agency) - combustión gasolina
