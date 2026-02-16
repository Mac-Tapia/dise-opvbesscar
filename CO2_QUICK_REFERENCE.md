# 🚀 QUICK REFERENCE: CO₂ Terminología

## Memoriza Esto ✅

```
reduccion_directa_co2_kg
  └─ SOLO cambio combustible (gasolina → EV)
     = energía_motos × 0.87 + energía_taxis × 0.47
     ⚠️ NO incluye grid
     Anual: 456.6 Mg

co2_grid_kwh
  └─ SOLO costo de generar electricidad
     = energía_total × 0.4521 (diesel)
     ⚠️ Se reduce con solar
     Anual: 255.8 Mg

co2_neto_por_hora_kg
  └─ Impacto REAL = reducción_directa - co2_grid
     = (gasolina evitada) - (diesel generado)
     Anual: 200.7 Mg ✅ POSITIVO (beneficio)
```

---

## Pregunta → Respuesta

| Pregunta | Respuesta | Columna |
|----------|-----------|---------|
| ¿Cuánta gasolina evitamos? | 456.6 Mg | `reduccion_directa_co2_kg` |
| ¿Cuánto diesel se genera? | 255.8 Mg | `co2_grid_kwh` |
| ¿Cuál es el impacto NETO? | 200.7 Mg beneficio | `co2_neto_por_hora_kg` |
| ¿Solo cambio combustible? | Sí, 456.6 Mg | `reduccion_directa_co2_kg` |
| ¿Incluyendo grid? | Sí, 200.7 Mg | `co2_neto_por_hora_kg` |

---

## Anual Vistazo Rápido

```
┌─────────────────────────────────────────────────────┐
│ MOTOS (476.5 MWh)       476,501 kWh × 0.87 = 414.5 Mg │
│ TAXIS (89.4 MWh)         89,374 kWh × 0.47 =  42.0 Mg │
├─────────────────────────────────────────────────────┤
│ REDUCCIÓN DIRECTA (combustible)              456.6 Mg │
│ MENOS: CO2 GRID (diesel)                    -255.8 Mg │
├─────────────────────────────────────────────────────┤
│ CO2 NETO (impacto real)              ✅  200.7 Mg │
└─────────────────────────────────────────────────────┘
```

---

## En Código

### Generar
```python
df["reduccion_directa_co2_kg"] = (
    df["ev_energia_motos_kwh"] * 0.87 + 
    df["ev_energia_mototaxis_kwh"] * 0.47
)
df["co2_neto_por_hora_kg"] = (
    df["reduccion_directa_co2_kg"] - 
    df["ev_energia_total_kwh"] * 0.4521
)
```

### Usar en Reward
```python
# Opción 1: Solo cambio combustible
reward = df['reduccion_directa_co2_kg'][t]

# Opción 2: Impacto neto (recomendado)
reward = df['co2_neto_por_hora_kg'][t]
```

### Reportar
```python
print(f"Reducción:  {df['reduccion_directa_co2_kg'].sum()/1e6:.1f} Mg")
print(f"Grid:       {df['co2_grid_kwh'].sum()/1e6:.1f} Mg")  
print(f"Neto:       {df['co2_neto_por_hora_kg'].sum()/1e6:.1f} Mg")
```

---

## Archivo de Verificación

```bash
python VERIFICACION_CO2_TERMINOLOGIA.py
```

Muestra todas las columnas, factores, ejemplos y sums de forma clara.

---

**Última actualización**: 2026-02-16
