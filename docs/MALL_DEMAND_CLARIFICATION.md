# CORRECCIÓN: Demanda del Mall - Análisis Completo

## Resumen Ejecutivo

El valor **3,092,204 kWh** es la demanda REAL Y TOTAL del mall/edificio según Building_1.csv

### ✅ Lo que SÍ incluye (3,092,204 kWh):
- `non_shiftable_load`: 3,092,204 kWh (demanda no-desplazable del edificio)
- `dhw_demand`: 0 kWh (agua caliente)
- `cooling_demand`: 0 kWh (refrigeración)
- `heating_demand`: 0 kWh (calefacción)
- **TOTAL EDIFICIO: 3,092,204 kWh/año**

### ❌ Lo que NO incluye:
- **Demanda de chargers (EVs):** Se extrae por separado de `charger_simulation_*.csv`
- En simulate.py: `_extract_ev_charging_kwh()` busca:
  - `chargers_electricity_consumption` en building
  - `electric_vehicle_storage.electricity_consumption`
  - Individual charger data en `chargers[i].electricity_consumption`

## Desglose en CityLearn OE3

### Building_1.csv (Demanda del Edificio/Mall):
```
non_shiftable_load:    3,092,204 kWh/año ← DEMANDA DEL MALL
dhw_demand:            0 kWh/año
cooling_demand:        0 kWh/año
heating_demand:        0 kWh/año
─────────────────────────────────
TOTAL EDIFICIO:        3,092,204 kWh/año
```

### charger_simulation_*.csv (Demanda EV - Por Socket):
```
charger_simulation_001.csv → 8,760 horas (socket 1)
charger_simulation_002.csv → 8,760 horas (socket 2)
...
charger_simulation_128.csv → 8,760 horas (socket 128)

Cada archivo contiene:
- electric_vehicle_charger_state (0=avail, 1=charging, 3=commuting)
- electric_vehicle_id
- electric_vehicle_departure_time

TOTAL CHARGERS:        Se suma durante _extract_ev_charging_kwh()
```

## Comparación: Mall vs EV Chargers

| Componente | Archivo | Demanda | Incluido en |
|------------|---------|---------|-----------|
| **Mall Demand** | Building_1.csv | 3,092,204 kWh/año | `non_shiftable_load` |
| **EV Charging** | charger_simulation_*.csv | ? kWh/año | Extractado en simulate |
| **Total Sistema** | Building_1.csv + chargers/*.csv | > 3,092,204 kWh/año | Demanda total OE3 |

## Validación en simulate.py

En OE3 simulate.py línea ~1120:
```python
# Building load (mall + other)
building = _extract_building_load_kwh(env)  # non_shiftable_load
print(f"Building load: {building.sum():.0f} kWh")  # 3,092,204 kWh

# EV charging (extracted separately)
ev = _extract_ev_charging_kwh(env)  # charger_simulation_*.csv
print(f"EV charging: {ev.sum():.0f} kWh")  # ? (depends on charger profiles)

# TOTAL DEMAND = building + ev
total_demand = building.sum() + ev.sum()
```

## Conclusión

**3,092,204 kWh es CORRECTO como demanda del mall/edificio**
- Es la suma de TODAS las columnas de demanda en Building_1.csv
- Solo incluye edificio, no chargers
- Los chargers se procesan por separado en simulate.py
- Demanda TOTAL del sistema = mall (3,092,204) + chargers (variable por hora)

---

**Documento generado:** 2026-02-04  
**Verificación:** analyze_demand.py → Building_1.csv  
**Estado:** ✅ CORREGIDO Y ACLARADO
