# 🚨 REVISIÓN EJECUTIVA: ARQUITECTURA SIMPLIFICADA Y VELOCIDAD ACELERADA

## Fecha
31 de Enero 2026 | 09:45 UTC

---

## RESUMEN EJECUTIVO

**El baseline y entrenamiento están corriendo ~30-50x MÁS RÁPIDO de lo normal porque la arquitectura tiene SIMPLIFICACIONES CRÍTICAS que eliminan dinámicas de simulación fundamentales.**

### Velocidad Observada vs Esperada
| Métrica | Esperado | Observado | Factor |
|---------|----------|-----------|--------|
| Timesteps/segundo | 5-20 | ~515 | **25-100x MÁS RÁPIDO** |
| Duración episodio 8760 pasos | 436-1,752 seg | ~17 seg | **25-100x MÁS RÁPIDO** |
| Complejidad computacional | ALTA (física EV) | MÍNIMA | **REDUCIDA** |

---

## PROBLEMA 1: BESS SOC CONSTANTE (CRÍTICO)

### ¿Qué está pasando?
El archivo `electrical_storage_simulation.csv` contiene **UN SOLO VALOR constante para las 8,760 horas del año**:

```
soc_stored_kwh: 2260.0 (todas las 8760 filas)
Desviación estándar: 0.0
Valores únicos: 1
```

### Impacto
- **BESS no se está simulando dinámicamente**
- No hay carga/descarga realista
- No hay despacho inteligente
- Reduce cálculos de simulación a casi NADA
- **Baseline no es representativo del sistema real**

### Código Fuente (dataset_builder.py línea 896)
```python
# Crear DataFrame con estado del BESS (simplificado)
initial_soc = bess_cap * 0.5  # kWh = 2260
bess_df = pd.DataFrame({
    "soc_stored_kwh": np.full(n, initial_soc, dtype=float)  # ⚠️ CONSTANTE
})
```

### Lo que DEBERÍA estar pasando
- SOC debería variar hora a hora (2260 → 0 → 4520 kWh)
- Basado en carga solar, demanda de carga, demanda del mall
- Incluir eficiencia de round-trip (95%)
- Cumplir límites min (10%) y max (95%)

---

## PROBLEMA 2: CHARGERS ELIMINADOS DEL SCHEMA (CRÍTICO)

### ¿Qué está pasando?
El schema de CityLearn **elimina la key de chargers** para evitar un RecursionError en CityLearn v2.5.0:

```python
# Workaround: Remover chargers del schema para evitar RecursionError
if "chargers" in b:
    del b["chargers"]  # ⚠️ ELIMINADO

if "electric_vehicles_def" in schema:
    del schema["electric_vehicles_def"]  # ⚠️ ELIMINADO
```

### Resultado
- **0 Electric Vehicles configurados en CityLearn** (debería haber 128)
- Schema dice: `"electric_vehicles": 0 defined`
- Charger files existen pero NO están conectados al environment
- Agentes NO pueden controlar carga de EVs
- **Control de EVs está deshabilitado**

### Archivos Generados ✓ Pero No Usados
```
✓ charger_simulation_001.csv ... charger_simulation_128.csv (128 files, 8760 rows cada uno)
✓ 128 chargers definidos en OE2
✓ Perfiles horarios cargados correctamente
✗ PERO: No están referenciados en schema.json
```

---

## PROBLEMA 3: PV NO CONFIGURADO (CRÍTICO)

### ¿Qué está pasando?
En el schema final, **NO HAY pv_power_plant configurado en el building**:

```
Building: Mall_Iquitos
   ✓ Electrical Storage (BESS): 4520 kWh, 2712 kW
   ✗ NO PV CONFIGURED!
   ✗ NO chargers KEY IN BUILDING
   ✓ Electric Vehicles (top-level): 0 defined
```

### Impacto
- Sin PV configurado, CityLearn no simula generación solar
- Weather.csv tiene irradiance pero PV plant no lo consume
- Sin PV, no hay carga de BESS en horas pico
- Sin carga de BESS, SOC permanece constante
- **Loop cerrado: Constancia de SOC es consecuencia directa**

---

## PROBLEMA 4: VELOCIDAD IMPOSIBLE DE CÁLCULO

### Análisis
| Factor | Impacto en Velocidad |
|--------|---------------------|
| BESS SOC constante (no cambios) | **-80% cálculo** |
| Chargers no simulados (0 EV en schema) | **-60% cálculo** |
| PV no configurado (skip de física solar) | **-40% cálculo** |
| Building load sí se simula | ✓ +100 pasos/sec |
| **Total** | **~90% REDUCCIÓN** |

### Estimación Realista
```
Expected (full simulation): 5-20 steps/sec
Observed (reduced): ~515 steps/sec = 25-100x faster
Root cause: 3 componentes críticas SIMPLIFICADAS
```

---

## VERIFICACIÓN DE DATOS: ¿ESTÁN COMPLETOS?

### ✓ Datos OE2 SÍ están cargados correctamente:

1. **Solar Generation** 
   - ✓ 8,760 filas (horario, 1 año completo)
   - ✓ Media: 0.220 W/kWp
   - ✓ Max: 0.694 W/kWp
   - ✓ Fuente: PVGIS (confirmado)

2. **Building Load (Mall Demand)**
   - ✓ 8,760 horas
   - ✓ Media: 1,412 kW
   - ✓ Max: 2,101 kW
   - ✓ Total anual: 12.37 M kWh
   - ✓ Patrón diario real (confirmado)

3. **Charger Profiles**
   - ✓ 128 archivos CSV generados
   - ✓ 8,760 filas cada uno (completo)
   - ✓ Media: 1.83 kW
   - ✓ Max: 3.0 kW (motos 2kW, mototaxis 3kW)

4. **BESS Configuration**
   - ✓ 4,520 kWh capacidad (de OE2)
   - ✓ 2,712 kW potencia (de OE2)
   - ✗ PERO: SOC es CONSTANTE (no dinámico)

### Conclusión
**Los archivos OE2 SÍ están completos, PERO los archivos generados para CityLearn están SIMPLIFICADOS:**
- ✓ Datos fuente: Completos
- ✗ Datos procesados: Simplificados
- ✗ Schema: Incompleto/desactivado

---

## IMPACTO EN ENTRENAMIENTO

### Baseline no es representativo
```
Uncontrolled (baseline):
- R_total = -0.1712
- R_CO2 = -0.1680
- R_cost = -1.0000

Problema: Sin BESS dinámico ni chargers, baseline no muestra
la complejidad real del problema de optimización.
```

### Agentes No Pueden Aprender Control de Chargers
```
SAC Training:
- [SAC] paso 100 | reward_avg=24.6936
- [SAC] paso 500 | reward_avg=24.6500

Problema: Sin chargers en schema, agentes no tienen
acción válida para controlar carga de EVs.
Reward elevado artificial (sin dinámicas reales).
```

---

## RAÍZ DE LOS PROBLEMAS

### Error de Arquitectura
CityLearn v2.5.0 tiene un **RecursionError** cuando se usa `electric_vehicle_chargers`:

```python
# ERROR EN CITYLEARN
→ Accede a electric_vehicle_charger_state
→ Que referencia electric_vehicles  
→ Que referencia electric_vehicle_chargers
→ Infinite recursion
```

### Solución Actual (INCORRECTA)
```python
# Workaround fallido:
del b["chargers"]  # ⚠️ Elimina chargers del building
del schema["electric_vehicles_def"]  # ⚠️ Elimina definiciones
# Resultado: 0 EVs en schema = Sin control de carga
```

### Solución Correcta (NO IMPLEMENTADA)
1. Usar `EV_VEHICLES` a nivel global (no building)
2. Crear wrapper que intercede RecursionError
3. Implementar chargers via observables + acciones
4. NO eliminar, sino DESACTIVAR recursión

---

## DIAGNÓSTICO FINAL

| Componente | Estado | Problema |
|------------|--------|----------|
| Solar Data | ✓ Completo | - |
| Load Data | ✓ Completo | - |
| Charger Data | ✓ Completo | ✗ No conectado a schema |
| BESS Config | ✓ Completo | ✗ SOC constante |
| PV Config | ✗ Falta | ✗ No en building |
| EV Control | ✗ Desactivado | ✗ 0 EVs en schema |
| **Velocidad** | ✗ 30-100x rápido | ✗ Causado por arriba |
| **Baseline** | ✗ No representativo | ✗ Causado por arriba |

---

## RECOMENDACIONES URGENTES

### CRÍTICO (Bloquea entrenamiento real)
- [ ] **Fix 1**: Implementar BESS dinámico con despacho real
  - Crear SOC basado en import/export/charging por hora
  - Incluir límites (min 10%, max 95%)
  - Incluir eficiencia 95%

- [ ] **Fix 2**: Restaurar chargers a schema
  - Resolver RecursionError en CityLearn
  - Integrar 128 EVs en observables + acciones
  - Validar agentes pueden controlar carga

- [ ] **Fix 3**: Configurar PV en building
  - Agregar pv_power_plant al schema
  - Conectar a weather.csv (irradiance)
  - Validar despacho PV→BESS→EV

### Validación Post-Fix
- [ ] Rerun baseline: Debería tomar ~180-300 segundos (no 17)
- [ ] Verificar rewards reales cambian por acción (no constantes)
- [ ] Validar SAC aprende a controlar chargers (co2_avoided debe cambiar)
- [ ] Confirmar BESS SOC varía 2260 → 0 → 4520 kWh

---

## ESTIMACIÓN DE IMPACTO

### Antes (Actual)
- ⚠️ Baseline: 17 sec/episode
- ⚠️ SAC: 30 sec/3-episodes
- ⚠️ Rewards: Artificiales (no reflejan complejidad)
- ⚠️ Agentes: No controlan carga (0 EVs)

### Después (Post-Fix)
- ✓ Baseline: ~250-300 sec/episode (realista)
- ✓ SAC: ~900 sec/3-episodes (con aprendizaje real)
- ✓ Rewards: Dinámicos (reflejan complejidad)
- ✓ Agentes: Controlan 128 chargers (misión cumplida)

---

## CONCLUSIÓN

**NO ES UN PROBLEMA DE RAPIDEZ = EFICIENCIA**

Es un problema de **SIMPLIFICACIÓN ARQUITECTÓNICA** que:
1. Desactiva componentes críticas (chargers, PV)
2. Crea dinámicas falsas (SOC constante)
3. Acelera simulación artificialmente
4. Invalida entrenamiento y resultados

**Solución: Restaurar arquitectura completa con todos los componentes activos.**

---

Generado: 2026-01-31 09:50 UTC
Autor: Revisión Automática del Sistema
