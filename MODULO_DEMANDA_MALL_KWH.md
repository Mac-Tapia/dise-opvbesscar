# Módulo Demanda Mall KWH - Análisis Comportamiento con Control Insertado

**Ubicación:** `src/iquitos_citylearn/oe3/demanda_mall_kwh.py`  
**Script de ejemplo:** `scripts/analizar_demanda_mall_con_control.py`  
**Status:** ✅ Implementado y listo para usar

---

## 📌 Propósito

Este módulo integra **la demanda real del mall** (desde `demandamallkwh.csv`) con **el control operativo** (despacho P1-P5) para visualizar el comportamiento energético completo:

```
Demanda Mall (real)
    ↓
    ├─ P1: Solar → EV directo (minimiza grid)
    ├─ P2: Solar → BESS (prepara pico)
    ├─ P3: BESS → EV (durante pico)
    ├─ P4: Grid → BESS (reserva)
    └─ P5: Grid → EV (último recurso)
    ↓
Balance Energético
    ↓
CO₂ Emitido = Grid Import × 0.4521 kg/kWh
```

---

## 🏗️ Estructura de Clases

### 1. `MallDemandaHoraria` (frozen dataclass)

Representa la demanda del mall **en una hora específica**.

```python
@dataclass(frozen=True)
class MallDemandaHoraria:
    timestamp: datetime          # Fecha/hora
    hora_dia: int               # 0-23
    demanda_mall_kwh: float     # Demanda real (non-shiftable)
    generacion_pv_kwh: float    # PV disponible
    tarifa_usd_kwh: float       # Tarifa eléctrica
    season: str                 # "dry" o "wet"
```

**Ejemplo:**

```python
demanda = MallDemandaHoraria.from_row(
    timestamp=datetime(2024, 8, 15, 14, 0),
    demanda_mall_kwh=1017,      # Pico mediodía
    generacion_pv_kwh=644,      # Solar fuerte
    tarifa_usd_kwh=0.20
)
```

---

### 2. `DispatchControlInsertado` (frozen dataclass)

Representa **la acción de control** en esa hora (decisiones de despacho).

```python
@dataclass(frozen=True)
class DispatchControlInsertado:
    # Prioridades (kWh en la hora)
    p1_pv_a_ev_directo_kwh: float    # Solar → EV directo
    p2_pv_a_bess_kwh: float          # Solar → BESS
    p3_bess_a_ev_kwh: float          # BESS → EV
    p4_grid_a_bess_kwh: float        # Grid → BESS (reserva)
    p5_grid_a_ev_kwh: float          # Grid → EV (último recurso)
    
    # Estado BESS
    bess_soc_antes: float            # % antes
    bess_soc_despues: float          # % después
    bess_ciclos_incrementales: float # Degradación
    
    # EVs
    ev_cargados_numero: int          # Cuántos vehículos
    ev_potencia_promedio_kw: float   # Potencia promedio
```

**Propiedades útiles:**

```python
dispatch.energia_total_despacho_kwh  # P1+P2+P3+P4+P5
dispatch.pv_aprovechado_pct          # Eficiencia solar
```

---

### 3. `BalanceHorario` (frozen dataclass)

Resultado del balance energético para la hora.

```python
@dataclass(frozen=True)
class BalanceHorario:
    # Entradas
    demanda_mall_kwh: float
    ev_demanda_kwh: float
    pv_disponible_kwh: float
    bess_disponible_descarga_kwh: float
    grid_disponible_kwh: float
    
    # Flujos
    pv_a_ev_directo: float
    pv_a_bess: float
    bess_a_ev: float
    grid_a_bess: float
    grid_a_ev: float
    grid_a_mall: float
    
    # Resultados
    import_grid_total_kwh: float     # Total comprado a grid
    export_grid_kwh: float            # Total vendido a grid (exceso)
    co2_total_kg: float              # CO₂ de esta hora
    costo_usd: float                 # Costo en dólares
```

**Propiedades útiles:**

```python
balance.balance_energy              # Verificación (debe ~0)
balance.eficiencia_pv_pct           # % de PV sin conversión
```

---

### 4. `HoraConControlInsertado` (frozen dataclass)

**Snapshot completo** de una hora: demanda + control + resultado.

```python
@dataclass(frozen=True)
class HoraConControlInsertado:
    demanda: MallDemandaHoraria      # Demanda del mall
    dispatch: DispatchControlInsertado  # Control aplicado
    balance: BalanceHorario          # Resultado energético
    
    episodio: int                    # Número de episodio RL
    timestep: int                    # Timestep en episodio (0-8759)
```

---

### 5. `AnalizadorDemandaMallKwh` (clase principal)

Encapsula la lógica de análisis.

#### Métodos principales

**`cargar_demanda_mall_real(interim_dir: Path) → pd.DataFrame`**

Carga demanda real desde `data/interim/oe2/demandamallkwh/demandamallkwh.csv`.

```python
analyzer = AnalizadorDemandaMallKwh(cfg)
df_mall = analyzer.cargar_demanda_mall_real(Path("data/interim/oe2"))

# Resultado
print(df_mall.head())
#                          demanda_mall_kwh
# 2024-01-01 00:00:00               487.0
# 2024-01-01 01:00:00               520.0
# ...
```

---

**`crear_hora_con_control(...) → HoraConControlInsertado`**

Crea snapshot de una hora con demanda + control + resultado.

```python
dispatch_actions = {
    'p1': 80,      # 80 kWh solar → EV directo
    'p2': 150,     # 150 kWh solar → BESS
    'p3': 0,       # No descargar BESS (no es pico)
    'p4': 0,
    'p5': 200,     # 200 kWh grid → EV
    'bess_soc_antes': 50,
    'bess_soc_despues': 60,
    'ciclos': 0.1,
    'ev_count': 50,
    'ev_power': 5.4,
}

hora = analyzer.crear_hora_con_control(
    timestamp=datetime(2024, 8, 15, 14, 0),
    demanda_mall_kwh=1017,
    pv_disponible_kwh=644,
    dispatch_acciones=dispatch_actions,
)

# Acceder a resultados
print(f"CO₂: {hora.balance.co2_total_kg:.0f} kg")
print(f"Grid import: {hora.balance.import_grid_total_kwh:.0f} kWh")
print(f"Costo: ${hora.balance.costo_usd:.2f}")
```

---

**`generar_reporte_24h(horas_con_control: List) → str`**

Genera reporte formateado de 24 horas.

```python
reporte = analyzer.generar_reporte_24h(horas_simuladas)
print(reporte)

# Salida:
# Hora | Demanda | PV Disp | P1→EV  | P2→BESS| ... | CO₂(kg)| BESS%
# ─────┼─────────┼─────────┼────────┼────────┼─────┼─────────┼──────
#  00  |     450 |       0 |      0 |      0 | ... |    1200 |  50.0
#  01  |     420 |       0 |      0 |      0 | ... |    1100 |  50.0
#  ...
#  14  |    1080 |     644 |     80 |    150 | ... |    1020 |  60.0
#  ...
```

---

**`generar_reporte_diario(horas_con_control: List) → Dict`**

Genera resumen diario en JSON.

```python
resumen = analyzer.generar_reporte_diario(horas_simuladas)
print(json.dumps(resumen, indent=2))

# Salida:
{
  "fecha": "2024-08-15T00:00:00",
  "demanda_mall": {
    "min_kwh": 390.0,
    "max_kwh": 1100.0,
    "promedio_kwh": 750.5,
    "total_kwh": 18012.0
  },
  "co2_emitido": {
    "total_kg": 18500.0,
    "factor_grid_kg_kwh": 0.4521
  },
  "control_insertado": {
    "pv_aprovechado_pct": 68.5
  }
}
```

---

## 🔧 Uso en Scripts

### Ejemplo Básico

```python
from scripts._common import load_all
from src.iquitos_citylearn.oe3.demanda_mall_kwh import create_demanda_mall_analyzer

# Cargar config
cfg, rp = load_all("configs/default.yaml")

# Crear analizador
analyzer = create_demanda_mall_analyzer(cfg)

# Cargar demanda real del mall
df_mall = analyzer.cargar_demanda_mall_real(Path("data/interim/oe2"))

# Simular 24 horas con control
horas_simuladas = []
for timestamp in df_mall.index[:24]:
    demanda = df_mall.loc[timestamp, 'demanda_mall_kwh']
    pv = 500.0 if 6 <= timestamp.hour <= 18 else 0.0  # PV dummy
    
    # Crear acciones de control (simulado)
    dispatch = {'p1': 50, 'p2': 100, 'p3': 30, ...}
    
    hora = analyzer.crear_hora_con_control(
        timestamp=timestamp,
        demanda_mall_kwh=demanda,
        pv_disponible_kwh=pv,
        dispatch_acciones=dispatch,
    )
    horas_simuladas.append(hora)

# Generar reportes
reporte = analyzer.generar_reporte_24h(horas_simuladas)
resumen = analyzer.generar_reporte_diario(horas_simuladas)
```

---

## 📊 Métricas Disponibles

Cada `HoraConControlInsertado` proporciona:

| Métrica | Fuente | Descripción |
| --- | --- | --- |
| `demanda.demanda_mall_kwh` | CSV real | Demanda base del mall (no controlable) |
| `demanda.generacion_pv_kwh` | CSV OE2 | PV disponible (control decide uso) |
| `dispatch.p1_pv_a_ev_directo_kwh` | Control | Solar directo a EV |
| `dispatch.p2_pv_a_bess_kwh` | Control | Solar a BESS (almacenamiento) |
| `dispatch.p3_bess_a_ev_kwh` | Control | BESS a EV (especialmente pico) |
| `balance.import_grid_total_kwh` | Cálculo | Total grid import (costo + CO₂) |
| `balance.co2_total_kg` | Cálculo | CO₂ emitido (grid import × 0.4521) |
| `balance.costo_usd` | Cálculo | Costo operativo ($) |
| `balance.eficiencia_pv_pct` | Cálculo | % PV aprovechado sin conversión |

---

## 🎯 Casos de Uso

### 1. Validar despacho P1-P5

```python
# ¿P1 está siendo efectivo?
pv_directo = sum(h.dispatch.p1_pv_a_ev_directo_kwh for h in horas)
print(f"P1 efectividad: {pv_directo/total_pv*100:.1f}% de PV directo a EV")
```

### 2. Monitorear CO₂

```python
# CO₂ por hora
for h in horas_simuladas:
    co2 = h.balance.co2_total_kg
    grid = h.balance.import_grid_total_kwh
    print(f"Hora {h.demanda.hora_dia:2d}: {co2:7.0f} kg CO₂ ({grid:6.0f} kWh grid)")
```

### 3. Analizar eficiencia BESS

```python
# Ciclos de BESS
total_ciclos = sum(h.dispatch.bess_ciclos_incrementales for h in horas)
print(f"BESS ciclos en 24h: {total_ciclos:.2f} ciclos")

# SOC evolution
soc_evolution = [h.dispatch.bess_soc_despues for h in horas]
print(f"SOC min: {min(soc_evolution):.1f}%, max: {max(soc_evolution):.1f}%")
```

### 4. Comparar escenarios

```python
# Escenario 1: Con despacho P1-P5
co2_con_control = sum(h.balance.co2_total_kg for h in horas_con_control)

# Escenario 2: Sin control (100% grid)
co2_sin_control = sum(h.demanda.demanda_mall_kwh for h in horas) * 0.4521

reduccion = (1 - co2_con_control/co2_sin_control) * 100
print(f"Reducción CO₂: {reduccion:.1f}%")
```

---

## 📁 Datos Esperados

### Input: `data/interim/oe2/demandamallkwh/demandamallkwh.csv`

```
FECHAHORA;kWh
1/01/2024 0:15;158
1/01/2024 0:30;161
1/01/2024 0:45;168
...
```

### Output: `outputs/oe3/demanda_mall/`

```
├── reporte_24h_demanda_control.txt    # Tabla 24h
├── resumen_diario_demanda_control.json # Métricas JSON
└── (otros reportes por escenario)
```

---

## 🔄 Integración con OE3 Pipeline

**Paso 1**: Cargar demanda en `run_oe3_build_dataset.py`

```python
df_mall = load_mall_demand_real(...)
```

**Paso 2**: Rastrear con analizador en `simulate.py`

```python
analyzer = create_demanda_mall_analyzer(cfg)
horas_simuladas.append(analyzer.crear_hora_con_control(...))
```

**Paso 3**: Generar reportes post-training

```python
reporte = analyzer.generar_reporte_diario(horas_simuladas)
```

---

## ✅ Validaciones Incluidas

- ✅ Balance energético verifica entrada = salida
- ✅ CO₂ usando factor Iquitos (0.4521 kg/kWh)
- ✅ Eficiencia PV solo cuenta P1+P2 (sin conversión)
- ✅ BESS SOC respeta límites (10-95%)
- ✅ Frozen dataclasses previenen mutaciones

---

## 📝 Notas Técnicas

1. **Demanda es REAL**: `demandamallkwh.csv` contiene datos reales del smart meter del mall
2. **Control es SIMULADO**: Las acciones P1-P5 vienen de política RL o heurística
3. **Balance es DETERMINÍSTICO**: Dada demanda + control, resultado es cálculo directo
4. **CO₂ es DIRECTO**: Solo grid import cuenta (no incluye BESS Scope 1)
5. **Frozen design**: Previene bugs por mutación accidental

---

## 🚀 Ejecución

```bash
# Script de ejemplo completo
python scripts/analizar_demanda_mall_con_control.py

# Output:
# ✅ Demanda mall cargada: 8760 horas
# ✅ 24 horas simuladas con despacho
# ✅ Reporte guardado en outputs/oe3/demanda_mall/
```

---

**Última actualización:** 2025-01-18  
**Módulo:** `demanda_mall_kwh.py` (750+ líneas)  
**Script:** `analizar_demanda_mall_con_control.py` (300+ líneas)
