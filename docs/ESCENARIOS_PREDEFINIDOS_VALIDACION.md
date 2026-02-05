# Validación de Escenarios Predefinidos contra Tabla 13 OE2
## 2026-02-04 - ANÁLISIS COMPLETO

---

## 📊 RESUMEN EJECUTIVO

Se han validado **4 escenarios predefinidos** contra los rangos de **Tabla 13 OE2**:

| Escenario | PE | FC | Cargadores | Tomas | Energía | Estado |
|-----------|----|----|-----------|-------|---------|---------|
| **CONSERVADOR** | 0.10 | 0.80 | 4 | 16 | 185.6 | ✅ VÁLIDO |
| **MEDIANO** | 0.55 | 0.60 | 20 | 80 | 765.6 | ✅ VÁLIDO |
| **RECOMENDADO** | 0.90 | 0.90 | 32 | 128 | 3,252.0 | ✅ VÁLIDO |
| **MÁXIMO** | 1.00 | 1.00 | 36 | 144 | 4,013.6 | ❌ FUERA RANGO |

**Conclusión**: 3 de 4 escenarios están dentro de tolerancia. El escenario MÁXIMO es un **límite teórico** que excede los rangos históricos de Tabla 13.

---

## 🎯 TABLA 13 OE2 - RANGOS DE REFERENCIA

### Cargadores (cantidad)
- **Mínimo**: 4.00
- **Máximo**: 35.00 ⚠️
- **Media**: 20.61
- **Mediana**: 20.00
- **Std Dev**: 9.19

### Tomas Totales (sockets, 4 por cargador)
- **Mínimo**: 16.00
- **Máximo**: 140.00 ⚠️
- **Media**: 82.46
- **Mediana**: 80.00
- **Std Dev**: 36.76

### Energía Día [kWh]
- **Mínimo**: 92.80
- **Máximo**: 3,252.00 ⚠️
- **Media**: 903.46
- **Mediana**: 835.20
- **Std Dev**: 572.07

---

## 🔍 ANÁLISIS DETALLADO DE ESCENARIOS

### 1️⃣ CONSERVADOR (PE=0.10, FC=0.80)

**Parámetros**:
- Penetración: 10% (muy baja)
- Factor carga: 80% (batería casi completa)
- Cargadores: 4 (mínimo operativo)
- Tomas: 16 (mínimo operativo)
- Energía: 185.6 kWh

**Validación contra Tabla 13**:
```
✅ Cargadores: 4 ∈ [4.00, 35.00] → DENTRO
   Delta: -80.59% vs media (muy por debajo de media)

✅ Tomas: 16 ∈ [16.00, 140.00] → DENTRO
   Delta: -80.60% vs media (justo en el mínimo)

✅ Energía: 185.6 ∈ [92.80, 3,252.00] → DENTRO
   Delta: -79.46% vs media (muy baja, mínimo viable)
```

**Interpretación**:
- Representa el **caso base mínimo viable**
- Sistema operando al 10% de penetración de mercado
- Apenas cumple requisitos operacionales
- Caso de arranque o mercado muy restringido
- **Recomendación**: Válido como referencia de mínimo, pero operación real requiere penetración > 50%

---

### 2️⃣ MEDIANO (PE=0.55, FC=0.60)

**Parámetros**:
- Penetración: 55% (operación típica)
- Factor carga: 60% (carga moderada)
- Cargadores: 20 (expansión media)
- Tomas: 80 (expansión media)
- Energía: 765.6 kWh

**Validación contra Tabla 13**:
```
✅ Cargadores: 20 ∈ [4.00, 35.00] → DENTRO
   Delta: -2.96% vs media (casi en la media)

✅ Tomas: 80 ∈ [16.00, 140.00] → DENTRO
   Delta: -2.98% vs media (casi en la media)

✅ Energía: 765.6 ∈ [92.80, 3,252.00] → DENTRO
   Delta: -15.26% vs media (por debajo de media)
```

**Interpretación**:
- Representa el **escenario de operación típica del sistema**
- Penetración de mercado realista (55%)
- Muy cercano a la media de Tabla 13 en cargadores y tomas
- Energía un 15% por debajo de la media (factor carga moderado: 60%)
- **Recomendación**: Ideal para referencia de "operación normal"
- Este es un buen punto de validación intermedia

---

### 3️⃣ RECOMENDADO (PE=0.90, FC=0.90) ⭐ ÓPTIMO

**Parámetros**:
- Penetración: 90% (muy alta penetración)
- Factor carga: 90% (carga máxima)
- Cargadores: 32 (expansión máxima)
- Tomas: 128 (expansión máxima) ← **DISEÑO ACTUAL OE3**
- Energía: 3,252 kWh

**Validación contra Tabla 13**:
```
✅ Cargadores: 32 ∈ [4.00, 35.00] → DENTRO
   Delta: +55.26% vs media (significativamente por encima)

✅ Tomas: 128 ∈ [16.00, 140.00] → DENTRO
   Delta: +55.23% vs media (justo dentro del máximo)

✅ Energía: 3,252.0 ∈ [92.80, 3,252.00] → DENTRO
   Delta: +259.95% vs media (JUSTO en el máximo Tabla 13)
```

**Interpretación**:
- Representa la **configuración RECOMENDADA del proyecto**
- 32 cargadores × 4 tomas = 128 sockets controlables
- Es el **MÁXIMO dentro de los límites Tabla 13**
- Penetración muy alta (90%) con carga al máximo (90%)
- Energía máxima permitida por Tabla 13: 3,252 kWh
- **Estado**: ✅ VÁLIDO - Este es el punto de DISEÑO OE3
- **Conclusión**: Sistema dimensionado correctamente al punto máximo de Tabla 13

---

### 4️⃣ MÁXIMO (PE=1.00, FC=1.00) ⚠️ LÍMITE TEÓRICO

**Parámetros**:
- Penetración: 100% (penetración teórica)
- Factor carga: 100% (carga teórica máxima)
- Cargadores: 36 (expansión teórica)
- Tomas: 144 (expansión teórica)
- Energía: 4,013.6 kWh

**Validación contra Tabla 13**:
```
❌ Cargadores: 36 ∉ [4.00, 35.00] → FUERA DE RANGO
   Delta: +74.67% vs media (supera el máximo histórico de 35)

❌ Tomas: 144 ∉ [16.00, 140.00] → FUERA DE RANGO
   Delta: +74.63% vs media (supera el máximo histórico de 140)

❌ Energía: 4,013.6 ∉ [92.80, 3,252.00] → FUERA DE RANGO
   Delta: +344.25% vs media (supera máximo histórico de 3,252 kWh)
```

**Interpretación**:
- Representa un **límite teórico, no validado en Tabla 13**
- Todos los parámetros están fuera de los rangos históricos
- **36 cargadores** vs máximo histórico de 35
- **144 tomas** vs máximo histórico de 140
- **4,013.6 kWh** vs máximo histórico de 3,252 kWh
- **Estado**: ❌ INVÁLIDO para Tabla 13
- **Propósito**: Punto de referencia para **expansión futura** más allá de Tabla 13
- **Recomendación**: No usar MÁXIMO como baseline de validación, es especulativo

---

## 📈 TABLA COMPARATIVA CON DELTAS

| Métrica | Min (T13) | Conservador | Mediano | Recomendado | Máximo | Max (T13) |
|---------|-----------|-------------|---------|-------------|---------|-----------|
| **Cargadores** | 4.00 | 4 (-80.59%) | 20 (-2.96%) | 32 (+55.26%) | 36 (+74.67%) ❌ | 35.00 |
| **Tomas** | 16.00 | 16 (-80.60%) | 80 (-2.98%) | 128 (+55.23%) | 144 (+74.63%) ❌ | 140.00 |
| **Energía [kWh]** | 92.80 | 185.6 (-79.46%) | 765.6 (-15.26%) | 3,252.0 (+259.95%) | 4,013.6 (+344.25%) ❌ | 3,252.00 |

**Observaciones**:
- CONSERVADOR: Todos en el rango inferior (mínimos)
- MEDIANO: Todos muy cercanos a la media (excelente representación)
- RECOMENDADO: Todos en el rango superior (máximos)
- MÁXIMO: Todos FUERA del rango (teórico)

---

## 🎓 CONCLUSIONES Y RECOMENDACIONES

### Para Validación de Datos ✅

1. **CONSERVADOR** - Usar como **límite inferior de validación**
   - Representa el mínimo operativo
   - Penetración 10% es muy baja para operación normal
   - Válido para pruebas de casos extremos bajos

2. **MEDIANO** - Usar como **baseline de validación primaria**
   - Casi exactamente en la media de Tabla 13
   - Penetración 55% es realista
   - Mejor punto para comparar escenarios

3. **RECOMENDADO** - Usar como **límite superior de validación** ⭐
   - Diseño actual del sistema OE3
   - Justo en los máximos de Tabla 13
   - Confirma que OE3 está correctamente dimensionado
   - Punto de operación óptimo

4. **MÁXIMO** - No usar para validación Tabla 13
   - Es un límite teórico especulativo
   - Fuera de los rangos históricos
   - Puede usarse para planificación de expansión futura
   - Requeriría validación en nuevos datos si se implementa

### Para Desarrollo OE3

- El sistema OE3 actual (32 cargadores, 128 tomas) corresponde al escenario **RECOMENDADO**
- Este es el punto de diseño óptimo dentro de Tabla 13
- Los 3 escenarios válidos (CONSERVADOR, MEDIANO, RECOMENDADO) pueden usarse para análisis de sensibilidad
- El escenario MÁXIMO es para referencia solo (expansión futura)

### Integración en Código

Se ha creado una estructura `EscenarioPredefinido` con validación automática:

```python
from iquitos_citylearn.oe2.chargers import ESCENARIOS_PREDEFINIDOS, validar_escenarios_predefinidos

# Acceder a un escenario
recomendado = ESCENARIOS_PREDEFINIDOS['RECOMENDADO']
# Resultado: 32 cargadores, 128 tomas, 3,252 kWh

# Validar todos los escenarios
resultados = validar_escenarios_predefinidos()
# Devuelve estado de validación para cada uno
```

---

## 🔗 REFERENCIAS Y ARCHIVOS

| Archivo | Propósito |
|---------|-----------|
| `src/iquitos_citylearn/oe2/chargers.py` | Definición de `EscenarioPredefinido` y `ESCENARIOS_PREDEFINIDOS` |
| `scripts/validar_escenarios_predefinidos.py` | Script ejecutable de validación |
| `docs/ESCENARIOS_PREDEFINIDOS_VALIDACION.md` | Este documento (análisis completo) |

---

## ✅ PRÓXIMOS PASOS

1. ✅ **VALIDACIÓN COMPLETADA**: 3 de 4 escenarios dentro de rango
2. ⏳ **INTEGRACIÓN CÓDIGO**: Usar `ESCENARIOS_PREDEFINIDOS` en tests y CI/CD
3. ⏳ **DOCUMENTACIÓN**: Incluir en guías de desarrollo y operación
4. ⏳ **MONITOREO**: Usar MEDIANO como punto de referencia en reportes

---

**Generado**: 2026-02-04  
**Status**: ✅ VALIDACIÓN COMPLETADA  
**Próximo**: Integrar en pipeline de pruebas automatizadas
