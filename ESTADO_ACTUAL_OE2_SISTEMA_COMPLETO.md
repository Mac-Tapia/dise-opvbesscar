# ✅ Sistema OE2 - Estado Actual (25 Enero 2026)

## Arquitectura Implementada

### 128 Tomas Controlables Independientemente

```
PLAYAS DE ESTACIONAMIENTO
│
├─ Playa Motos (112 tomas)
│  ├─ Toma 0-111: 2.0 kW cada una (Modo 3 AC 16A)
│  └─ Potencia total: 224 kW
│
└─ Playa Mototaxis (16 tomas)
   ├─ Toma 112-127: 3.0 kW cada una (Modo 3 AC 16A)
   └─ Potencia total: 48 kW

TOTAL: 128 TOMAS × 272 kW INSTALADOS
```

### Resolución Temporal

| Aspecto | Especificación |
|---------|----------------|
| **Modo de carga** | Modo 3 AC (Corriente Alterna trifásica 16A) |
| **Intervalo** | 30 minutos |
| **Intervalos/día** | 48 (24h × 60min/30min) |
| **Intervalos/año** | 17,520 (365 × 48) |
| **Horario operación** | 09:00 - 22:00 (13 horas/día) |
| **Horario pico** | 18:00 - 22:00 (4 horas/día) |
| **Período cubierto** | 1 año completo (365 días) |

### Perfiles Generados

#### A. Perfil Consolidado
```
data/interim/oe2/chargers/perfil_tomas_30min.csv
├─ Filas: 2,242,560 (128 × 17,520)
├─ Columnas: 14 (toma_id, type, date, time, factors, power, energy)
├─ Formato: CSV (UTF-8)
└─ Tamaño: ~150 MB
```

#### B. Perfiles Individuales por Toma
```
data/interim/oe2/chargers/toma_profiles/
├─ toma_000_moto_30min.csv ... toma_111_moto_30min.csv
├─ toma_112_mototaxi_30min.csv ... toma_127_mototaxi_30min.csv
├─ Total: 128 archivos
└─ Filas por archivo: 17,520
```

## Variabilidad Independiente

Cada toma tiene patrón ÚNICO:

### Factor Horario (Base - Igual para todas)
```
09:00-18:00: Factor = 0.5 (carga media)
18:00-22:00: Factor = 1.0 (carga máxima/pico)
22:00-09:00: Factor = 0.0 (cerrado)
```

### Ocupancia (Independiente por toma)
```
Probabilidad de EV conectado en intervalo: 0-100% (aleatoria)
├─ Si ocupado: P_toma = factor_horario × P_max × ocupancia
└─ Si vacío: P_toma = 0 kW
```

### Resultado
Cada toma tiene comportamiento REALISTA:
- Algunas tomas llenas en hora pico
- Otras parcialmente ocupadas
- Algunas vacías mientras otras cargan
- Patrones varían día a día y entre tomas

## Demanda Proyectada

### Agregada (128 tomas)

| Métrica | Valor |
|---------|-------|
| Carga promedio | 96.3 kW (considerando ocupancia) |
| Carga pico | ~270 kW (18:00-22:00, ~95% ocupancia) |
| Carga mínima | 0 kW (22:00-09:00) |
| **Total anual** | **717,374 kWh** |

### Por Tipo de Vehículo

| Tipo | Cantidad | Potencia | Energía/año | % |
|------|----------|----------|------------|---|
| Motos | 112 | 224 kW | 590,886 kWh | 82.4% |
| Mototaxis | 16 | 48 kW | 126,488 kWh | 17.6% |
| **TOTAL** | **128** | **272 kW** | **717,374 kWh** | **100%** |

## Integración con Sistema OE2

### Solar PV (GENERACIÓN)
```
Sistema solar: 4,050 kWp
Generación anual estimada: ~15.2 GWh
Proporción para EV: ~717 MWh/año (4.7%)
```

### BESS (ALMACENAMIENTO)
```
Capacidad: 2 MWh / 1.2 MW (fijo, no controlado por RL)
Función: Cubrir déficit nocturno (22:00-09:00)
Carga: Desde PV excedente
Descarga: 18:00-22:00 (cuando solar = 0)
```

### Mall (EDIFICIO)
```
Demanda: ~3,358 MWh/año (no es EV)
Complementario a carga de vehículos
```

## Control OE3 - Acción por Toma

### Espacio de Acción (128 dimensiones)

```python
action = [a₀, a₁, ..., a₁₂₇]

Donde:
  aᵢ ∈ [0, 1]  # Potencia normalizada

Interpretación física:
  P_toma_i = aᵢ × P_max_toma_i
  
  Si i ∈ [0, 112):     # Moto
    P = aᵢ × 2.0 kW
  Si i ∈ [112, 128):   # Mototaxi
    P = aᵢ × 3.0 kW
```

### Ejemplo de Control
```
aᵢ = 1.0 → Toma i carga a máxima potencia
aᵢ = 0.5 → Toma i carga a 50% de potencia
aᵢ = 0.0 → Toma i apagada (no carga)
```

## Observación OE3 - Estado Individual

```python
obs = [
    # Global (11 dims)
    solar_generation_kw,
    total_demand_kw,
    bess_soc_percent,
    grid_import_kw,
    # ... time features
    
    # Por toma (128 × 4 = 512 dims)
    [
        toma_0_is_occupied,
        toma_0_charge_factor,
        toma_0_power_kw,
        toma_0_accumulated_charge,
        
        # ... toma 1-126
        
        toma_127_is_occupied,
        toma_127_charge_factor,
        toma_127_power_kw,
        toma_127_accumulated_charge,
    ]
]
```

## Recompensa Multiobjetivo

```python
# Pesos
r = 0.50×r_co2 + 0.20×r_solar + 0.10×r_cost + 0.10×r_ev + 0.05×r_grid

# Objetivo: Minimizar CO₂
# - Motos 2kW: Usar PV directo > BESS > Grid
# - Mototaxis 3kW: Prioridad según disponibilidad de solar
# - Resultado esperado: 26-29% reducción vs baseline
```

## Archivos Disponibles

### Documentación
- `ARQUITECTURA_TOMAS_INDEPENDIENTES.md` → Concepto
- `CITYLEARN_128TOMAS_TECNICO.md` → Integración técnica
- `RESUMEN_PERFILES_INDEPENDIENTES_128TOMAS.md` → Detalles perfiles
- `RESUMEN_ACTUALIZACION_TOMAS_INDEPENDIENTES.md` → Resumen ejecutivo

### Datos
- `data/interim/oe2/chargers/individual_chargers.json` → Config de 128 tomas
- `data/interim/oe2/chargers/perfil_tomas_30min.csv` → Perfiles consolidados (2.2M rows)
- `data/interim/oe2/chargers/toma_profiles/` → 128 archivos individuales
- `data/interim/oe2/chargers/chargers_schema.json` → Schema CityLearn

### Scripts
- `generate_toma_profiles_30min.py` → Generador de perfiles independientes
- `verify_and_generate_chargers_data.py` → Verificación general

## Próximos Pasos - OE3

### 1. Construir Dataset CityLearn
```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```
**Validará:**
- 128 tomas presentes
- Obs space ~523 dims
- Action space 128 dims
- Perfiles cargados correctamente

### 2. Entrenar Agentes RL
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
```
**Entrenará 3 agentes:**
- SAC (off-policy) - Mejor muestra eficiencia
- PPO (on-policy) - Más estable
- A2C (simpler baseline)

### 3. Evaluar Resultados
```bash
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```
**Comparará:**
- CO₂ baseline vs agentes
- Solar utilization
- Grid import reduction
- EV satisfaction

## Estado de Implementación

| Componente | Status | Notas |
|-----------|--------|-------|
| Dimensionamiento OE2 | ✅ Completo | 112 motos + 16 mototaxis |
| Perfiles horarios | ❌ Deprecado | Reemplazado por 30 min |
| Perfiles 30 minutos | ✅ Completo | 17,520 intervals/toma |
| Perfiles independientes | ✅ Completo | Cada toma tiene patrón único |
| JSON configuración | ✅ Completo | 128 tomas con especificaciones |
| Schema CityLearn | ✅ Completo | Compatible con v2.5 |
| Dataset builder | 🔄 Por adaptar | Necesita integrar perfil_tomas_30min.csv |
| RL training | 🔄 Por comenzar | Esperando dataset |
| Evaluación | ⏳ Próximo | Después del training |

## Validación Rápida

```bash
# Verificar perfiles
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/chargers/perfil_tomas_30min.csv'); print(f'Total: {len(df):,} rows, {len(df.columns)} columns'); print(f'Tomas: {df[\"toma_id\"].max()+1}, Intervals/toma: {len(df)//128}')"

# Resultado esperado:
# Total: 2,242,560 rows, 14 columns
# Tomas: 128, Intervals/toma: 17,520

# Ver ejemplo de una toma
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/chargers/perfil_tomas_30min.csv'); print(df[df['toma_id']==0].iloc[900:905][['date','hour_of_day','minute_of_hour','power_kw','is_occupied']])"
```

---

## Resumen Ejecutivo

✅ **Sistema OE2 completo con 128 tomas independientes a 30 minutos**

- 128 tomas controlables (112 motos 2kW + 16 mototaxis 3kW)
- Perfiles generados: 17,520 intervalos/año por toma
- Variabilidad realista: cada toma con patrón independiente
- Datos: 2.2M filas (consolidado) + 128 CSV (individuales)
- Modo 3 AC 16A: 09:00-22:00 operación, 18:00-22:00 pico
- Demanda total: ~717 MWh/año (82.4% motos, 17.6% mototaxis)
- Ready for OE3 RL training (SAC/PPO/A2C)

🚀 **Próximo:** Adaptar dataset_builder.py e iniciar training
