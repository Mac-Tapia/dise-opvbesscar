# 📊 VISUALIZACIÓN DE LAS 6 FASES INTOCABLES DEL BESS

## Principio Fundamental

**Las 6 FASES del BESS son la base de cálculo operativo y NO SE MODIFICAN EN BESS.PY**

Solo se mejora su **visualización en las gráficas** (balance.py) para que sean claramente identificables y comprensibles.

---

## 1️⃣ FASE 1: CARGA GRADUAL (6h-15h)

### Características Operativas (bess.py - Línea 1643-1667)
```
- Inicia cuando genera PV (~6h) desde SOC 20% (cierre día anterior)
- Carga PROGRESIVA/GRADUAL: Sube poco a poco a máximo 390 kW
- Crece continuamente hasta alcanzar SOC 100% (~15h)
- SE DETIENE automáticamente en SOC 100%
- No usa red (SOLO PV disponible)
- Propósito: Almacenar máxima energía para descarga posterior
```

### Visualización en Gráficas (balance.py - Línea 271)
```
ZONA COLOREADA: Verde claro (alpha=0.08)
INTERVALO: 6h a 15h

ELEMENTOS VISIBLES:
├─ Barras verdes ascendentes (bess_charge_kw)
├─ SOC azul sube de 20% → 100%
├─ PV generación (amarillo/naranja) alimenta BESS
└─ Etiqueta: "FASE 1: Carga Gradual (6-15h)"

VALIDACIÓN EN GRÁFICA:
✓ Charge inicia alrededor de la 6h
✓ Charge termina cuando SOC llega a 100%
✓ No hay barras de descarga en esta zona
```

---

## 2️⃣ FASE 2: HOLDING (15h-17h aprox)

### Características Operativas (bess.py - Línea 1669-1710)
```
- Ocurre cuando SOC ≥ 99% y aún hay generación PV
- Mantiene SOC 100% constante (cero carga, cero descarga)
- BESS entra en "modo espera" (idle)
- PV atiende directamente a EV sin cargar BESS más
- Propósito: Conservar energía para punto crítico (PV < demanda)
```

### Visualización en Gráficas (balance.py - Línea 274)
```
ZONA COLOREADA: Azul claro (alpha=0.08)
INTERVALO: 15h a 17h (aprox - dinámico)

ELEMENTOS VISIBLES:
├─ Barras de carga DESAPARECEN (cero carga)
├─ SOC azul PLANA al 100% (línea horizontal constante)
├─ PV (amarillo) fluye directo a EV (sin cargar BESS)
├─ EV demanda verde light (PV directo)
└─ Etiqueta: "FASE 2: Holding (15-17h)"

VALIDACIÓN EN GRÁFICA:
✓ SOC se estabiliza en 100%
✓ Carga cae a cero
✓ Descarga aún es cero (transición)
```

---

## 3️⃣ FASE 3: DESCARGA (17h-22h)

### Características Operativas (bess.py - Línea 1712-1854)
```
ACTIVA CUANDO: PV < demanda (punto crítico, aprox 17h)

DESCARGA HACIA EV (PRIORIDAD 1):
├─ Cubre 100% del deficit EV (máxima prioridad)
├─ Cuando pv_kwh < ev_kwh
└─ Descarga máximo hasta SOC 20% (mínimo absoluto)

DESCARGA HACIA MALL (PRIORIDAD 2 - PEAK SHAVING):
├─ Reduce picos MALL cuando mall_kwh > 1900 kW
├─ Solo aplica si hay carencia solar (PV < demanda MALL)
└─ Descarga adicional junto con cobertura EV
```

### Visualización en Gráficas (balance.py - Línea 277)
```
ZONA COLOREADA: Rojo claro (alpha=0.08)
INTERVALO: 17h a 22h

ELEMENTOS VISIBLES:
├─ Barras ROJAS descendentes (descarga BESS)
├─ SOC azul CAJA de 100% → 20% (línea descendente)
├─ EV demanda (verde light) suplida por BESS (barras rojas inferiores)
├─ MALL demanda (azul oscuro) + peak shaving (rojo superpuesto)
├─ Grid importación (rojo línea) cubre el resto
└─ Etiqueta: "FASE 3-5: Descarga + Peak Shaving (17-22h)"

VALIDACIÓN EN GRÁFICA:
✓ Barras rojas de descarga aparecen
✓ SOC desciende continuamente hacia 20%
✓ EV recibe cobertura desde BESS (100%)
✓ MALL picos se reducen (peak shaving visible)
```

---

## 4️⃣ FASE 4: PEAK SHAVING (17h-21h en picos > 1900 kW)

### Características Operativas (bess.py - Línea 1829-1854)
```
ACTIVE CUANDO:
├─ MALL demand > 1900 kW (threshold) Y
├─ Hay carencia solar (PV < demanda MALL) Y
├─ SOC > 20% (energía disponible)

ACCIÓN:
├─ Descarga BESS hacia MALL para cortar picos
├─ Intenta limitar demanda total ≤ 1900 kW
└─ Opera en PARALELO con cobertura EV (FASE 5)

RESULTADO:
├─ Reducción anual: 610,523 kWh (89.9% de descarga BESS)
├─ Impacto: Evita saturación/apagones en red aislada
└─ CO₂ evitado: Reemplaza generación térmica Iquitos
```

### Visualización en Gráficas
```
IDENTIFICACIÓN EN GRÁFICA:
1. Línea NARANJA PUNTEADA en y=1900 kW
   ├─ Marca threshold de peak shaving
   └─ Visible en rango 0-3000 kW (eje Y)

2. Barras ROJAS SUPERPUESTAS (descarga)
   ├─ Cuando MALL > 1900 kW
   └─ Separación visual sobre demanda base

3. SOC DESCENSO ACELERADO (17h-21h)
   ├─ Caída más rápida que FASE 3 sin picos
   └─ Recupera en FASE 6 (22h-9h)

VALIDACIÓN EN GRÁFICA:
✓ MALL demand toca/supera línea 1900 kW
✓ Barras rojas de descarga coinciden con picos
✓ Grid import (rojo línea) BAJA cuando BESS descarga
✓ SOC desciende proporcionalmente a descarga
```

---

## 5️⃣ FASE 5: DUAL DESCARGA (17h-22h)

### Características Operativas (bess.py - Línea 1912-1970)
```
SIMULTANEO: EV + MALL pikes en paralelo

PRIORIDAD 1: BESS → EV
├─ Cubre 100% deficit EV (cobertura garantizada)
├─ Máxima descarga hasta consumir energía disponible
└─ Hasta las 22h (cierre operativo EV)

PRIORIDAD 2: BESS → MALL (si queda SOC)
├─ Peak shaving: reduce MALL cuando > 1900 kW
├─ Descarga adicional con energía residual
└─ Hasta las 22h
```

### Visualización en Gráficas
```
IDENTIFICACIÓN EN GRÁFICA:
1. BARRAS ROJAS DUAL (superpuestas)
   ├─ Parte inferior: EV demand (rojo sólido)
   ├─ Parte superior: MALL peak shaving (rojo más oscuro)
   └─ Altura total = bess_discharge bruto

2. SOC AZUL DESCENSO CONTINUO
   ├─ 17h: 100% (inicio descarga)
   ├─ 22h: ~20% (mínimo operacional)
   └─ Pendiente proporcional a descarga

3. GRID IMPORT (rojo línea)
   ├─ Baja cuando BESS descarga
   ├─ Cubre lo que BESS no puede
   └─ Crece si BESS insuficiente

VALIDACIÓN EN GRÁFICA:
✓ Dos cortes visibles en barras (EV + MALL)
✓ EV siempre cubierto 100% (no hay defict)
✓ MALL baja cuando desciende a < 1900 kW
✓ Grid import cubre EV + MALL restante
```

---

## 6️⃣ FASE 6: REPOSO (22h-9h)

### Características Operativas (bess.py - Línea 1858-1879)
```
ESTADO: Stand-by / Idle

BESS ACCIÓN: CERO
├─ No carga (PV no genera, EV cerrado)
├─ No descarga (EV cierra a las 22h)
└─ Mantiene SOC 20% (mínimo defensivo)

EV ESTADO: CERRADO
├─ No hay demanda (horas 22-9h)
├─ No hay carga desde grid
└─ Reposar hasta mañana a las 9h

MALL ESTADO: Abierto pero sin apoyo BESS
├─ Se alimenta de grid público
├─ Sin peak shaving (BESS en reposo)
└─ Tarifa HFP (tarifa baja nocturna)
```

### Visualización en Gráficas (balance.py - Línea 280)
```
ZONA COLOREADA: Gris claro (alpha=0.08)
INTERVALO: 22h a 24h + 0h a 6h (dos segmentos)

ELEMENTOS VISIBLES:
├─ Cero barras verdes (sin carga)
├─ Cero barras rojas (sin descarga)
├─ SOC azul PLANA al 20% (línea horizontal en mínimo)
├─ PV amarillo CERO (no genera en noche)
├─ EV verde CERO (cerrado 22h-6h)
├─ MALL azul SOLO grid (roja línea = importación)
└─ Etiqueta: "FASE 6: Reposo (22-6h)"

VALIDACIÓN EN GRÁFICA:
✓ No hay movimiento en barras BESS
✓ SOC se mantiene constante en 20%
✓ Grid cubre 100% demanda MALL
✓ EV demand = 0
```

---

## Mapa Visual Completo (Un Día)

```
24h TIMELINE CON FASES:
├─ 00h-06h │ GRIS  │ FASE 6: REPOSO (BESS idle, SOC 20%)
├─ 06h-15h │ VERDE │ FASE 1: CARGA (BESS 20%→100%)
├─ 15h-17h │ AZUL  │ FASE 2: HOLDING (SOC 100% constante)
├─ 17h-22h │ ROJO  │ FASE 3-5: DESCARGA EV + PEAK SHAVING MALL
│          │       │   ├─ EV 100% cobertura (rojo inferior)
│          │       │   └─ MALL peak shaving (rojo superior + naranja threshold)
└─ 22h-00h │ GRIS  │ FASE 6: CIERRE (BESS → 20%, cierra operaciones)

SOC AZUL (eje derecho):
├─ 00h-06h: constante 20%
├─ 06h-15h: sube 20% → 100%
├─ 15h-17h: plana 100%
├─ 17h-22h: baja 100% → 20%
└─ 22h-00h: constante 20%
```

---

## Validación: Coherencia de Fases

### ✅ Las gráficas respetan:

1. **Duración temporal:** Cada fase ocurre en el intervalo definido
2. **Transiciones:** Hay cambios visuales claros entre fases
3. **Datos reales:** Barras y líneas vienen directo de bess.py (sin cambios)
4. **SOC lógica:** Sube en carga, se estabiliza en holding, baja en descarga
5. **Grid fallback:** Red pública cubre lo que BESS no puede
6. **EV prioridad:** Siempre cubierto al 100% en horario operativo
7. **Peak shaving:** Reducción visible cuando MALL > 1900 kW

### ❌ Nada se modifica en bess.py:

- Lógica de descarga: INTACTA
- Threshold 1900 kW: INTACTA
- 6 fases operativas: INTOCABLES base de cálculo
- Datos crudos: Pasan directamente a gráficas

---

## Implementación (balance.py)

**Archivo:** `src/dimensionamiento/oe2/balance_energetico/balance.py`

**Cambios:**
1. **Línea 217-237:** Docstring expandido describiendo 6 fases
2. **Línea 271-280:** Zonas coloreadas para cada fase
3. **Línea 272:** Verde (6-15h) FASE 1 CARGA
4. **Línea 274:** Azul (15-17h) FASE 2 HOLDING
5. **Línea 277:** Rojo (17-22h) FASE 3-5 DESCARGA
6. **Línea 280-281:** Gris (22-6h) FASE 6 REPOSO

**Gráficas generadas con mejora:**
- ✅ 00_BALANCE_INTEGRADO_COMPLETO.png (6 fases visuals)
- ✅ 00.1_EXPORTACION_Y_PEAK_SHAVING.png
- ✅ 00.3_PEAK_SHAVING_INTEGRADO_MALL.png
- ✅ 05.1_bess_carga_descarga.png

---

## Conclusión

✅ **Respeto total a las 6 fases intocables de BESS**
- Lógica operativa: SIN CAMBIOS en bess.py
- Visualización: MEJORADA en balance.py
- Claridad: Cada fase identificable por color + etiqueta
- Datos: Del CSV real (bess_ano_2024.csv)

---

**Status:** ✅ COMPLETADO
**Fecha:** 2026-02-20
**Versión:** v5.8
