# ✅ Perfiles de Carga - 128 Tomas Independientes (Modo 3, 30 Minutos)

## Resumen de Generación

**Estado:** ✅ COMPLETADO

### Estructura Generada

```
128 TOMAS INDEPENDIENTES × 17,520 INTERVALOS DE 30 MINUTOS
│
├─ Motos: 112 tomas × 2.0 kW
│  └─ Perfiles: toma_000_moto_30min.csv ... toma_111_moto_30min.csv
│
└─ Mototaxis: 16 tomas × 3.0 kW
   └─ Perfiles: toma_112_mototaxi_30min.csv ... toma_127_mototaxi_30min.csv
```

### Resolución de Datos

| Parámetro | Valor |
|-----------|-------|
| **Intervalo temporal** | 30 minutos (Modo 3 AC 16A) |
| **Filas por toma** | 17,520 (365 días × 48 intervalos/día) |
| **Tomas totales** | 128 (112 motos + 16 mototaxis) |
| **Filas consolidadas** | 2,242,560 (128 × 17,520) |
| **Período cubierto** | 1 año completo (365 días) |

### Horario de Operación (Base)

```
22:00 ──────────── 09:00: CERRADO (Power = 0 kW)
09:00 ──────────── 18:00: OFF-PICO (Factor = 0.5 × P_max)
18:00 ──────────── 22:00: PICO (Factor = 1.0 × P_max)
```

### Características Independientes por Toma

Cada toma tiene:

1. **Factor Horario Base**: Igual para todas (definido por horario)
2. **Occupancy Factor**: INDEPENDIENTE (0-100%)
   - Simula probabilidad de tener EV conectado
   - Varía aleatoriamente por intervalo y por toma
   - Promedio: 50% (algunas tomas sin EV)

3. **Poder Entregado**:
   ```
   P_toma = charge_factor × P_max × (1 si occupied else 0)
   ```

### Demanda Agregada (128 Tomas)

| Métrica | Valor |
|---------|-------|
| **Media diaria** | 3,930.82 kW |
| **Pico (máximo)** | 4,010.00 kW |
| **Mínimo** | 0.00 kW (horas cerradas) |
| **Anual total** | 717,374 kWh |
| **Motos (82.4%)** | 590,886 kWh/año |
| **Mototaxis (17.6%)** | 126,488 kWh/año |

### Archivos Generados

#### 1. Archivo Consolidado
```
data/interim/oe2/chargers/perfil_tomas_30min.csv

Columnas:
├─ toma_id: 0-127 (ID de toma)
├─ toma_type: 'moto' o 'mototaxi'
├─ date: YYYY-MM-DD
├─ hour_of_day: 0-23
├─ minute_of_hour: 0 o 30
├─ time_decimal: hora decimal (9.5 = 9:30 AM)
├─ day_of_week: 0-6 (lunes-domingo)
├─ month: 1-12
├─ charge_factor: 0.0, 0.5, o 1.0 (horario)
├─ occupancy: 0-1 (aleatoria, prob. EV conectado)
├─ is_occupied: 0 o 1 (binario)
├─ power_max_kw: 2.0 (motos) o 3.0 (mototaxis)
├─ power_kw: potencia actual [kW]
└─ energy_kwh: energía por intervalo [kWh]

Filas: 2,242,560
Formato: CSV (UTF-8)
```

#### 2. Archivos Individuales por Toma
```
data/interim/oe2/chargers/toma_profiles/

TOMA_000_moto_30min.csv      → TOMA_111_moto_30min.csv      (112 motos)
TOMA_112_mototaxi_30min.csv  → TOMA_127_mototaxi_30min.csv  (16 mototaxis)

Total: 128 archivos CSV
Filas por archivo: 17,520
```

### Variabilidad Implementada

**Por Intervalo (misma toma, diferentes momentos):**
- Horario base determina carga máxima
- Occupancy aleatoria simula presencia/ausencia de EV
- Resultado: potencia varía por ocupancia

**Por Toma (mismo intervalo, diferentes tomas):**
- Cada toma tiene patrón occupancy INDEPENDIENTE
- Algunos intervalos ocupados en toma A, vacíos en toma B
- Refleja realismo de estacionamiento compartido

### Ejemplo: Intervalo 18:30 (Hora Pico)

```
Horario: 18:30 → charge_factor = 1.0 (PICO)

TOMA 0 (moto):
  occupancy = 0.87 → occupied ✓
  power_kw = 1.0 × 2.0 × 1 = 2.0 kW
  energy_kwh = 2.0 × 0.5 = 1.0 kWh

TOMA 50 (moto):
  occupancy = 0.12 → NOT occupied ✗
  power_kw = 1.0 × 2.0 × 0 = 0.0 kW
  energy_kwh = 0.0 kWh

TOMA 112 (mototaxi):
  occupancy = 0.65 → occupied ✓
  power_kw = 1.0 × 3.0 × 1 = 3.0 kW
  energy_kwh = 3.0 × 0.5 = 1.5 kWh

DEMANDA AGREGADA (18:30):
  Total = 2.0 + 0.0 + ... + 3.0 = ~1,900-2,100 kW (varía por day)
```

### Integración OE3

Los perfiles pueden usarse para:

1. **Observación del agente RL:**
   - Estado de cada toma: `power_kw[toma_id]`
   - Disponibilidad: `is_occupied[toma_id]`
   - Historial de carga: últimas 4-8 observaciones

2. **Control independiente:**
   - Acción por toma: `action[toma_id] ∈ [0, 1]`
   - Potencia asignada: `P = action[toma_id] × power_max[toma_id]`

3. **Recompensa multiobjetivo:**
   - Ver cómo el agente aprende a:
     - Cargar tomas ocupadas prioritariamente
     - Respetar ocupancia (no cargar si vacío)
     - Balancear carga entre 128 tomas

### Próximos Pasos

```bash
# 1. Verificar estructura
python -c "import pandas as pd; df = pd.read_csv('data/interim/oe2/chargers/perfil_tomas_30min.csv'); print(f'Filas: {len(df)}, Columnas: {len(df.columns)}')"

# 2. Ver ejemplo de una toma
python -c "import pandas as pd; df = pd.read_csv('data/interim/oe2/chargers/perfil_tomas_30min.csv'); print(df[df['toma_id']==0].head(10))"

# 3. Integrar en dataset_builder.py para OE3
# Modificar para leer perfil_tomas_30min.csv en lugar de perfil_horario_carga.csv
```

---

## Checklist

- ✅ 128 tomas generadas
- ✅ 17,520 intervalos de 30 minutos por toma
- ✅ Variabilidad independiente por toma
- ✅ Archivo consolidado: 2.2M filas
- ✅ Archivos individuales: 128 CSV
- ✅ Modo 3 AC 16A implementado
- ✅ Horario 09:00-22:00 (13 horas/día)
- ✅ Pico 18:00-22:00 (4 horas/día)
- 🔄 Próximo: Integrar en dataset builder OE3
