# Quick Reference - Dataset Metrics v5.4 para Agentes RL

**Última actualización**: 2026-02-13  
**Versión**: v5.4 (Ahorros + CO₂ Indirecto Integrado)

---

## ¿Qué cambió?

El dataset `bess_simulation_hourly.csv` **ahora incluye 4 nuevas columnas** que cuantifican:

| # | Columna | Tipo | Rango | Propósito |
|---|---------|------|-------|-----------|
| 21 | `peak_reduction_savings_soles` | Real (S/) | 0-139 | Ahorro económico por cortar pico |
| 22 | `peak_reduction_savings_normalized` | [0,1] | 0-1 | Observable RL: ahorros normalizados |
| 23 | `co2_avoided_indirect_kg` | Real (kg) | 0-176 | CO₂ evitado por BESS (thermal grid) |
| 24 | `co2_avoided_indirect_normalized` | [0,1] | 0-1 | Observable RL: CO₂ normalizado |

---

## Valores Totales Anuales (2024)

```
Ahorros:         S/. 118,445/año   (por reducir picos > 2000 kW)
CO₂ evitado:     203.5 ton/año    (BESS reemplaza diesel thermal)
```

### ¿Por qué estas métricas importan?

**Ahorros** (`peak_reduction_savings_soles`):
- BESS descarga para limitar demanda máxima (Mall + EV > 2000 kW)
- Pagar tarifa pico es costoso → BESS evita eso
- Cuantificamos ahorro en S/./hora

**CO₂ Indirecto** (`co2_avoided_indirect_kg`):
- Red de Iquitos = generación térmica (diesel B5)
- Factor: 0.4521 kg CO₂/kWh
- BESS discharge = energía que NO viene de la red térmica
- Cuantificamos CO₂ evitado en kg/hora

---

## Para Agentes RL: Observables en CityLearn

Tus agentes (SAC, PPO, A2C) reciben en cada paso:

```python
observation = {
    # Existentes (v5.3):
    'bess_soc_kwh': <float>,              # SOC 0-1700 kWh
    'pv_generation_kwh': <float>,         # Solar kWh
    'grid_import_kwh': <float>,           # Import desde red
    
    # NUEVAS (v5.4):  ← Estos están normalizados [0,1]
    'peak_reduction_savings_normalized': <float>,   # Ahorros [0, 1]
    'co2_avoided_indirect_normalized': <float>,     # CO₂ [0, 1]
}
```

---

## Ejemplo de Reward Function Multi-Objetivo

```python
def compute_multigoal_reward(observation, action, info):
    """Reward que balancea CO₂, ahorros, y estabilidad."""
    
    # Variables normalizadas [0,1] del dataset v5.4
    r_co2 = observation['co2_avoided_indirect_normalized']
    r_savings = observation['peak_reduction_savings_normalized']
    
    # Penalizar imports (existente)
    r_grid = -max(observation['grid_import_kwh'] / 1000, 0)  # Normalizar a [0,1]
    
    # Incentivar SOC responsable
    soc_kwh = observation['bess_soc_kwh']
    r_soc = abs(soc_kwh - 850) / 850  # Target SOC = 50% = 850 kWh
    
    # Pesos configurables
    weights = {
        'co2': 0.50,        # 50% prioridad ambiental
        'savings': 0.30,    # 30% beneficio económico
        'grid': 0.15,       # 15% reducir imports
        'soc': 0.05,        # 5% estabilidad SOC
    }
    
    # Combinar
    total = weights['co2'] * r_co2 + weights['savings'] * r_savings + \
            weights['grid'] * r_grid + weights['soc'] * r_soc
    
    return total / sum(weights.values())
```

---

## Verificación Rápida

Si necesitas validar que todo está correcto:

```bash
# 1. Verifica que el dataset existe y tiene las columnas
python -c "import pandas as pd; df=pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv'); print('OK' if 'peak_reduction_savings_normalized' in df.columns else 'MISSING')"

# 2. Corre la validación completa
python validate_metrics_v54_integration.py

# 3. Mira los valores rápidos
python -c "import pandas as pd; df=pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv'); print(f'Ahorros: S/. {df[\"peak_reduction_savings_soles\"].sum():,.0f}'); print(f'CO2: {df[\"co2_avoided_indirect_kg\"].sum():,.0f} kg')"
```

---

## Calibración de Rewards (Sugerencias)

### Opción 1: Prioridad Ambiental (CO₂ primero)
```python
weights = {
    'co2': 0.70,      # Maximizar CO₂ evitado
    'savings': 0.20,  # Ahorros secundarios
    'grid': 0.10,     # Reducir imports
}
```
**Cuándo usar**: Si la sostenibilidad es la meta principal

### Opción 2: Balance Económico-Ambiental (Recomendado)
```python
weights = {
    'co2': 0.50,      # Equilibrio
    'savings': 0.30,  # Ahorros
    'grid': 0.15,     # Imports
    'soc': 0.05,      # Estabilidad
}
```
**Cuándo usar**: Balance entre sostenibilidad y viabilidad económica

### Opción 3: Máximo ROI (Económico primero)
```python
weights = {
    'savings': 0.60,  # Maximizar ahorros
    'co2': 0.30,      # CO₂ como beneficio
    'grid': 0.10,     # Reducir imports
}
```
**Cuándo usar**: Si necesitas justificación financiera

---

## Cómo Interpretarlos en Resultados

Después de entrenar un agente, verás en rewards/logs:

```
Episode 100:
  - co2_avoided_indirect: 0.450 (45% del máximo teórico)  ← De cols normalizadas
  - peak_reduction_savings: 0.320 (32% del máximo)        ← De cols normalizadas
  - grid_import_reduction: 25.3%                          ← De cols reales
  - Total reward: 0.385
```

**Interpretación**:
- Si `co2_avoided_indirect` ≈ 1.0 → Agente maximiza BESS discharge ✓
- Si `peak_reduction_savings` > 0.5 → Agente descarga durante hora punta ✓
- Si `grid_import_reduction` > 30% → BESS trabajo exitoso ✓

---

## Dataset Location

```
data/oe2/bess/bess_simulation_hourly.csv  ← Archivo principal
└─ 8,760 filas (1 año) × 25 columnas
   ├─ Columnas existentes (21 cols)
   └─ Columnas nuevas (4 cols)  ← v5.4
```

**Para cargar en Python**:
```python
import pandas as pd

df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')

# Acceder a nuevas métricas
ahorros_total = df['peak_reduction_savings_soles'].sum()
co2_total = df['co2_avoided_indirect_kg'].sum()

print(f"Ahorros: S/. {ahorros_total:,.0f}")
print(f"CO₂: {co2_total/1000:.1f} ton")
```

---

## Troubleshooting

**P: ¿Por qué veo ceros en `peak_reduction_savings_soles`?**  
R: Esos son las horas donde BESS no descargó para mall (no hubo pico > 2000 kW). Normal: el BESS principalmente se usa horas punta (18-22h).

**P: ¿Las métricas están en la salida de CityLearn?**  
R: Sí, el `dataset_builder` las extrae automáticamente. Verifica con:
```python
print(artifacts['electrical_storage_simulation'].head())  # Debe mostrar las 3 cols
```

**P: ¿Puedo cambiar los pesos de rewards?**  
R: Sí, cualquier valor en `weights = {...}` es configurable. Experimenta con grid search.

**P: ¿Retro compatible con v5.3?**  
R: Sí. Si faltan las columnas, `dataset_builder` crea ceros automáticamente (aviso en logs).

---

## Documentación Completa

- **Técnica detallada**: [`DATASET_METRICS_v54_INTEGRATION.md`](DATASET_METRICS_v54_INTEGRATION.md)
- **Resumen ejecutivo**: [`INTEGRATION_SUMMARY_v54.md`](INTEGRATION_SUMMARY_v54.md)
- **Script de validación**: [`validate_metrics_v54_integration.py`](validate_metrics_v54_integration.py)

---

**Estado**: ✅ Listo para OE3  
**Versión": 5.4  
**Soporte**: Revisa documentación adjunta si encuentras problemas
