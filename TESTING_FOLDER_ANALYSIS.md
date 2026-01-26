# Análisis de Carpeta `/scripts/testing/`

## 📊 Resumen
- **Total de archivos**: 32 archivos Python
- **Estado**: Carpeta de utilidades y debugging (deprecated scripts)
- **Uso**: No se importa desde main codebase

## 📁 Categorización por Tipo

### 1. CLEANUP SCRIPTS (8 archivos) - ⚠️ YA USADOS, PUEDEN ELIMINARSE
- `LIMPIAR_GRAFICAS_REGENERADAS.py` - Limpieza de gráficas regeneradas
- `LIMPIAR_RAIZ.py` - Limpia raíz del proyecto (lista de archivos a borrar)
- `LIMPIAR_WARNINGS_PYTHON.py` - Limpia warnings de Python
- `fix_all_markdown_errors.py` - Correcciones de markdown
- `fix_markdown_final.py` - Correcciones finales de markdown
- `CORREGIR_ERRORES_HEADING.py` - Corrige errores MD025
- `CORREGIR_ERRORES_MD009.py` - Corrige espacios en blanco
- `CORREGIR_ERRORES_MD040.py` - Corrige listas de código
- `CORREGIR_ERRORES_MD060.py` - Corrige tablas

**Recomendación**: Estos fueron herramientas de ONE-TIME. Pueden eliminarse después de completar limpieza.

### 2. VERIFICATION SCRIPTS (15 archivos) - ✅ ÚTILES PARA DEBUGGING
- `VERIFICACION_VINCULACION_BESS.py` - Verifica BESS ↔ chargers ↔ solar
- `VERIFICACION_DIMENSIONAMIENTO_OE2.py` - Valida dimensionamiento OE2
- `VERIFICACION_FINAL_CHARGERS.py` - Verificación final de chargers
- `VERIFICACION_101_ESCENARIOS_2_PLAYAS.py` - Escenarios 2 playas
- `VERIFICAR_APERTURA_VARIACION.py` - Apertura y variación
- `VERIFICAR_DEFICIT_REAL.py` - Déficit real
- `VERIFICAR_PERFIL_15MIN_CSV.py` - Perfil 15 min
- `VERIFICAR_RAMPA_CIERRE.py` - Rampa de cierre
- `VERIFICAR_PERFILES.py` - Validación de perfiles
- `verificar_capacidad_vs_perfil.py` - Capacidad vs perfil
- `verificar_df_15min.py` - DataFrame 15 min
- `verificar_escala_grafica.py` - Escala gráfica
- `verificar_json_capacidad.py` - JSON capacidad
- `verificar_valores_15min.py` - Valores 15 min
- `test_15_ciclos.py` - Test 15 ciclos (API)
- `test_dashboard.py` - Test dashboard
- `TEST_PERFIL_15MIN.py` - Test perfil 15 min

**Recomendación**: Mantener. Son útiles para debugging y reproducir issues específicos.

### 3. ANALYSIS/REPORT SCRIPTS (4 archivos) - ✅ INFORMACIÓN ÚTIL
- `gpu_usage_report.py` - Reporte de uso GPU
- `MAXIMA_GPU_REPORT.py` - Reporte máximo GPU
- `WHY_SO_SLOW.py` - Análisis de lentitud
- `generador_datos_aleatorios.py` - Generador datos aleatorios

**Recomendación**: Mantener. Proporcionan insights sobre performance y diagnostics.

### 4. CONFIRMATION SCRIPTS (2 archivos) - ⚠️ HISTÓRICO
- `CONFIRMACION_DOS_PLAYAS.py` - Confirmación 2 playas
- `CONFIRMACION_FINAL_DOS_PLAYAS.py` - Confirmación final 2 playas

**Recomendación**: Pueden eliminarse (archivos históricos de validación).

## 🔍 Análisis de Duplicados

### Verificación de Duplicados de Contenido
```
Análisis: Se ejecutó búsqueda de contenido similar
- NO hay duplicados exactos de contenido (cada script resuelve un problema específico)
- Algunos tienen nombres similares pero objetivos diferentes:
  * LIMPIAR_* vs fix_* → Distintas categorías de limpieza
  * VERIFICACION_* vs VERIFICAR_* vs verificar_* → Distintos aspectos de OE2
  * test_* vs TEST_* → API test vs data test
```

## 📝 Recomendación Final: PLAN DE LIMPIEZA

### FASE 1: ELIMINAR (archivos one-time ya usados)
```
LIMPIAR_GRAFICAS_REGENERADAS.py
LIMPIAR_RAIZ.py  
LIMPIAR_WARNINGS_PYTHON.py
fix_all_markdown_errors.py
fix_markdown_final.py
CORREGIR_ERRORES_HEADING.py
CORREGIR_ERRORES_MD009.py
CORREGIR_ERRORES_MD040.py
CORREGIR_ERRORES_MD060.py
CONFIRMACION_DOS_PLAYAS.py
CONFIRMACION_FINAL_DOS_PLAYAS.py
```
**Total a eliminar**: 11 archivos (34% de carpeta)

### FASE 2: MANTENER (útiles para debugging)
```
VERIFICATION:
- VERIFICACION_VINCULACION_BESS.py
- VERIFICACION_DIMENSIONAMIENTO_OE2.py
- VERIFICACION_FINAL_CHARGERS.py
- VERIFICACION_101_ESCENARIOS_2_PLAYAS.py
- VERIFICAR_* (10 archivos)
- test_* (3 archivos)

ANALYSIS:
- gpu_usage_report.py
- MAXIMA_GPU_REPORT.py
- WHY_SO_SLOW.py
- generador_datos_aleatorios.py
```
**Total a mantener**: 21 archivos (66% de carpeta)

## ✅ Acciones Recomendadas

1. **Crear carpeta deprecated**: Mover archivos one-time a `scripts/testing/deprecated/`
2. **Documentar**: Crear `scripts/testing/README.md` explicando cada script
3. **Alias**: Crear shortcuts en raíz si se usan frecuentemente
4. **Git**: Documentar cambio en commit

