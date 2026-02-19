# 🔍 GUÍA: Cómo Ver y Verificar las Mejoras

## 1️⃣ Lo Más Rápido: Ver la Gráfica

### Ubicación del archivo:
```
d:\diseñopvbesscar\outputs\00.5_FLUJO_ENERGETICO_INTEGRADO.png
```

### ¿Qué buscar en la gráfica?

#### SUBPLOT 1 (Flujo Anual - Arriba a la izquierda)
**Busca el panel AMARILLO** con información:
- Debe mostrar: `🚲 PERFIL EV DESDE CHARGERS.PY (DESAGREGADO):`
- Debe mostrar: `270 MOTOS: 30 sockets, 4.6 kWh batería, 2.906 kWh/carga`
- Debe mostrar: `39 MOTOTAXIS: 8 sockets, 7.4 kWh batería, 4.674 kWh/carga`
- Debe mostrar: `Operación: 9h-22h (carga redistribuida 21h)`

#### SUBPLOT 2 (Día Operativo - Arriba a la derecha)
**Busca dos barras VERDES DIFERENTES**:
- Verde CLARO (#32CD32): Deben estar las "MOTOS (270/día, 30 sockets, 4.6 kWh)"
- Verde OSCURO (#00DD00): Deben estar las "MOTOTAXIS (39/día, 8 sockets, 7.4 kWh)"

**Busca anotación @ hora 17h** (inicio fase DESCARGA):
```
FASE 2: DESCARGA (17h-22h)
BESS→EV: 270 motos (30 sockets, 2.906 kWh) + 39 taxis (8 sockets, 4.674 kWh)
BESS→Peak Shaving: si total>1900 kW y SOC>50%
```

#### SUBPLOT 3 (SOC BESS - Abajo)
**Busca línea negra** con puntos en las 24 horas
- Debe tener zona roja (<20%) en la parte inferior
- Debe tener zona verde (20%-100%) en el medio
- Debe tener zona azul punteada (>50%) en la parte superior
- Punto crítico @ 22h: El SOC debe llegar a exactamente 20%

---

## 2️⃣ Verificación por Test Automático

### Ejecutar test de validación:

```bash
cd d:\diseñopvbesscar
python test_visualizacion_mejorada_ev_bess.py
```

### ¿Qué esperar?

**Buen resultado** (~120 segundos):
```
[OK] BalanceEnergeticoSystem inicializado
[OK] Datasets cargados y validados (EV profile checks incluidos)
[OK] Balance calculado

[INFO] ESPECIFICACIONES DESDE CHARGERS.PY:
  MOTOS:       270/día, 30 sockets
              Batería: 4.6 kWh, Carga: 2.906 kWh
  MOTOTAXIS:   39/día, 8 sockets
              Batería: 7.4 kWh, Carga: 4.674 kWh

[INFO] BESS OPERACIÓN EN DATASET:
  Columnas BESS: ['pv_to_bess_kw', 'bess_charge_kw', ...]
  SOC Min: 39.8%, SOC Max: 100.0%

[INFO] GENERANDO VISUALIZACIÓN MEJORADA...
[OK] Gráfica guardada en: d:\diseñopvbesscar\outputs

VALIDACION: La grafica muestra los elementos esperados?
[OK] Panel info muestra PERFIL EV DESDE CHARGERS.PY
[OK] Leyenda muestra MOTOS y MOTOTAXIS separadas
[OK] Anotaciones en 17h mencionan especificaciones reales

TEST COMPLETADO ✅
```

---

## 3️⃣ Verificación en IDE (VS Code)

### Abrir archivo modificado:
1. Abre: `src/dimensionamiento/oe2/balance_energetico/balance.py`
2. Ve a línea **1031** (Ctrl+G en VS Code)

### ¿Qué ver en secuencia?

**Líneas 1031-1062**: Panel informativo
```python
f'\n🚲 PERFIL EV DESDE CHARGERS.PY (DESAGREGADO):\n'
f'  270 MOTOS      : 30 sockets, 4.6 kWh batería, 2.906 kWh/carga\n'
f'  39 MOTOTAXIS   : 8 sockets, 7.4 kWh batería, 4.674 kWh/carga\n'
```

**Líneas 1090-1145**: EV desagregado
```python
# Buscar columnas de motos (sockets 0-29) vs taxis (sockets 30-37)
bar2a = ax2_top.bar(hours, ev_dem_motos, ..., 
                   label='Demanda EV - MOTOS (...)', color='#32CD32', ...)
bar2b = ax2_top.bar(hours, ev_dem_taxis, ..., 
                   label='Demanda EV - MOTOTAXIS (...)', color='#00DD00', ...)
```

**Líneas 1147-1182**: BESS desagregado
```python
bar3a = ax2_top.bar(hours, bess_to_ev_actual, ..., 
                   label='BESS→EV (Prioridad 1)', color='#FF8C00', ...)
bar3b = ax2_top.bar(hours, bess_to_peak_actual, ..., 
                   label='BESS→Peak Shaving (Prioridad 2, >1,900kW, SOC>50%)', 
                   color='#FFA500', ...)
```

**Línea 1213**: Título mejorado
```python
f'DÍA REPRESENTATIVO #{day_idx}: LÓGICA OPERATIVA REAL BESS v5.4 + PERFIL EV DESDE CHARGERS\n'
```

**Línea 1231**: Anotaciones @ 17h
```python
'BESS→EV: 270 motos (30 sockets, 2.906 kWh) + 39 taxis (8 sockets, 4.674 kWh)'
```

---

## 4️⃣ Verificación en Python Interactivo

### Script de verificación rápida:

```python
from pathlib import Path
from src.dimensionamiento.oe2.balance_energetico.balance import BalanceEnergeticoSystem
from src.dimensionamiento.oe2.balance_energetico.ev_profile_integration import (
    MOTO_SPEC, MOTOTAXI_SPEC, CHARGING_EFFICIENCY
)

# 1. Cargar datos
balance = BalanceEnergeticoSystem()
balance.load_all_datasets()
df = balance.calculate_balance()

# 2. Verificar especificaciones de chargers
print("MOTOS:", MOTO_SPEC.quantity_per_day, "veh/día", MOTO_SPEC.sockets_assigned, "sockets")
print("Carga motos:", MOTO_SPEC.energy_to_charge_kwh, "kWh")
print()
print("TAXIS:", MOTOTAXI_SPEC.quantity_per_day, "veh/día", MOTOTAXI_SPEC.sockets_assigned, "sockets")
print("Carga taxis:", MOTOTAXI_SPEC.energy_to_charge_kwh, "kWh")
print()
print("Total sockets:", MOTO_SPEC.sockets_assigned + MOTOTAXI_SPEC.sockets_assigned)
print("Eficiencia:", CHARGING_EFFICIENCY * 100, "%")

# 3. Verificar datos en dataset
print("\nDatos en dataset:")
print("EV Demanda total:", df['ev_demand_kw'].sum(), "kWh/año")
print("BESS Carga:", df['bess_charge_kw'].sum(), "kWh/año")
print("BESS Descarga:", df['bess_discharge_kw'].sum(), "kWh/año")
print("SOC:", df['bess_soc_percent'].min(), "-", df['bess_soc_percent'].max(), "%")

# 4. Generar gráficas
out_dir = Path(__file__).parent / "outputs"
balance.plot_energy_balance(out_dir=out_dir)
print(f"\nGráficas guardadas en: {out_dir}")
```

**Output esperado**:
```
MOTOS: 270 veh/día 30 sockets
Carga motos: 2.906 kWh
<...>
TAXIS: 39 veh/día 8 sockets
Carga taxis: 4.674 kWh
<...>
Total sockets: 38
Eficiencia: 62.0 %

Datos en dataset:
EV Demanda total: 408281.5 kWh/año
BESS Carga: 580200 kWh/año
BESS Descarga: 209374 kWh/año
SOC: 39.8 - 100.0 %

Gráficas guardadas en: d:\diseñopvbesscar\outputs
```

---

## 5️⃣ Inspeccionar Especificaciones Detalladas

### Ver especificaciones completas de chargers.py:

```python
from src.dimensionamiento.oe2.balance_energetico.ev_profile_integration import (
    MOTO_SPEC, MOTOTAXI_SPEC, MALL_OPERATIONAL_HOURS, print_ev_profile_summary
)

print("=" * 80)
print("ESPECIFICACIONES MOTOS:")
print("=" * 80)
print(f"Cantidad: {MOTO_SPEC.quantity_per_day} motos/día")
print(f"Sockets: {MOTO_SPEC.sockets_assigned} (asignados a {MOTO_SPEC.chargers_assigned} cargadores)")
print(f"Batería: {MOTO_SPEC.battery_kwh} kWh")
print(f"Carga nominal: {MOTO_SPEC.energy_to_charge_kwh} kWh (SOC 20%-80%)")
print(f"SOC llegada: {MOTO_SPEC.soc_arrival.mean*100:.1f}% ± {MOTO_SPEC.soc_arrival.std*100:.1f}%")
print(f"SOC objetivo: {MOTO_SPEC.soc_target.mean*100:.1f}% ± {MOTO_SPEC.soc_target.std*100:.1f}%")

print()
print("=" * 80)
print("ESPECIFICACIONES MOTOTAXIS:")
print("=" * 80)
print(f"Cantidad: {MOTOTAXI_SPEC.quantity_per_day} taxis/día")
print(f"Sockets: {MOTOTAXI_SPEC.sockets_assigned} (asignados a {MOTOTAXI_SPEC.chargers_assigned} cargadores)")
print(f"Batería: {MOTOTAXI_SPEC.battery_kwh} kWh")
print(f"Carga nominal: {MOTOTAXI_SPEC.energy_to_charge_kwh} kWh (SOC 20%-80%)")
print(f"SOC llegada: {MOTOTAXI_SPEC.soc_arrival.mean*100:.1f}% ± {MOTOTAXI_SPEC.soc_arrival.std*100:.1f}%")
print(f"SOC objetivo: {MOTOTAXI_SPEC.soc_target.mean*100:.1f}% ± {MOTOTAXI_SPEC.soc_target.std*100:.1f}%")

print()
print("=" * 80)
print("HORARIO OPERATIVO MALL (Mall multiplier por hora):")
print("=" * 80)
for hour, factor in MALL_OPERATIONAL_HOURS.items():
    print(f"  {hour:02d}h: {factor*100:3.0f}%", end="  ")
    if (hour + 1) % 6 == 0:
        print()
```

**Output**:
```
================================================================================
ESPECIFICACIONES MOTOS:
================================================================================
Cantidad: 270 motos/día
Sockets: 30 (asignados a 15 cargadores)
Batería: 4.6 kWh
Carga nominal: 2.906 kWh (SOC 20%-80%)
SOC llegada: 24.5% ± 10.0%
SOC objetivo: 78.0% ± 12.0%

================================================================================
ESPECIFICACIONES MOTOTAXIS:
================================================================================
Cantidad: 39 taxis/día
Sockets: 8 (asignados a 4 cargadores)
Batería: 7.4 kWh
Carga nominal: 4.674 kWh (SOC 20%-80%)
SOC llegada: 24.5% ± 10.0%
SOC objetivo: 78.0% ± 12.0%

================================================================================
HORARIO OPERATIVO MALL (Mall multiplier por hora):
================================================================================
  00h:   0%    01h:   0%    02h:   0%    03h:   0%    04h:   0%    05h:   0%  
  06h:   0%    07h:   0%    08h:   0%    09h:  30%    10h:  40%    11h:  55%  
  12h:  70%    13h:  85%    14h: 100%    15h: 100%    16h: 100%    17h: 100%  
  18h: 100%    19h: 100%    20h: 100%    21h:   0%    22h:   0%    23h:   0%  
```

---

## 6️⃣ Verificar Cambios en Git (Si disponible)

```bash
cd d:\diseñopvbesscar
git diff src/dimensionamiento/oe2/balance_energetico/balance.py
```

Busca estas palabras clave en el diff:
- `+PERFIL EV DESDE CHARGERS`
- `+270 MOTOS`
- `+39 MOTOTAXIS`
- `+Prioridad 1`
- `+Prioridad 2`
- `+2.906`
- `+4.674`

---

## 7️⃣ Resumen Rápido de Verificación

| Verificación | Comando/Archivo | Esperado |
|--------------|-----------------|----------|
| **Gráfica principal** | `outputs/00.5_FLUJO_ENERGETICO_INTEGRADO.png` | 3 subplots con EV desagregado y BESS Prioridad 1/2 |
| **Test automático** | `python test_visualizacion_mejorada_ev_bess.py` | Sale "✅ TEST COMPLETADO" |
| **Código en balance.py** | Líneas 1031-1231 | 5 secciones mejoradas documentadas |
| **Especificaciones** | `ev_profile_integration.py` | MOTO/MOTOTAXI specs exportadas |
| **Panel info gráfica** | Ver subplot 1 (color amarillo) | Muestra PERFIL EV + motos/taxis |
| **EV bars** | Ver subplot 2 | Dos barras verdes distintas (claro vs oscuro) |
| **BESS bars** | Ver subplot 2 (17h-22h) | Naranja oscuro (Prioridad 1) + claro (Prioridad 2) |
| **Anotaciones** | Ver subplot 2 @ 17h | Especificaciones exactas de motos/taxis |
| **SOC gráfica** | Ver subplot 3 | Línea negra con 20% @ 22h |

---

## 📝 Si Algo No Ve Bien

### Problema: La gráfica no se ve
**Solución**:
```bash
# Regenerar gráficas
python test_visualizacion_mejorada_ev_bess.py

# O directamente:
python -c "from src.dimensionamiento.oe2.balance_energetico.balance import BalanceEnergeticoSystem; b=BalanceEnergeticoSystem(); b.load_all_datasets(); b.calculate_balance(); b.plot_energy_balance()"
```

### Problema: No ve MOTOS/MOTOTAXIS en la leyenda
**Verificación**:
```bash
# Ver columnas en dataset
python -c "import pandas as pd; import sys; sys.path.insert(0,'.'); from src.dimensionamiento.oe2.balance_energetico.balance import BalanceEnergeticoSystem; b=BalanceEnergeticoSystem(); b.load_all_datasets(); df=b.calculate_balance(); print([c for c in df.columns if 'socket' in c or 'charging' in c])"
```

### Problema: BESS solo muestra una barra naranja
**Esperado**: Por ahora es normal si dataset no tiene `bess_discharge_to_ev_kw` y `bess_discharge_peak_shaving_kw` desagregados. El fallback muestra BESS total.

**Para obtener desagregación completa**:
- Asegúrate que `data/oe2/bess/bess_ano_2024.csv` tiene columnas de destino
- O actualiza balance.py para calcularlas desde lógica de prioridades

---

**¿Dudas?** Revisar:
- `RESUMEN_EJECUTIVO_VISUALIZACION_EV_BESS.md` - Resumen alto nivel
- `MEJORAS_VISUALIZACION_EV_BESS_IMPLEMENTADAS.md` - Detalles técnicos
- `DOCUMENTO_TECNICO_CAMBIOS_BALANCE_PY.md` - Línea por línea qué cambió
