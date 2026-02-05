# 🚀 Dimensionamiento de Cargadores - Quick Start

## Descripción

El sistema de **dimensionamiento de cargadores EV** permite calcular la infraestructura requerida (número de cargadores, tomas, capacidad energética) para 4 escenarios predefinidos:

| Escenario | Penetración | Factor Carga | Cargadores | Tomas | Energía/día |
|-----------|------------|--------------|-----------|-------|------------|
| 🟢 **CONSERVADOR** | 10% | 80% | 4 | 16 | 186 kWh |
| 🟡 **MEDIANO** | 55% | 60% | 20 | 80 | 766 kWh |
| 🔵 **RECOMENDADO** | 90% | 90% | 33 | 132 | 3,252 kWh |
| 🔴 **MÁXIMO** | 100% | 100% | 35 | 140 | 4,014 kWh |

---

## 🎯 Opciones de Ejecución

### Opción 1: Modo Directo (Línea de Comando)

```bash
# Ejecutar todos los escenarios
python scripts/main_dimensionamiento.py --todos

# Ejecutar escenario específico
python scripts/main_dimensionamiento.py --escenario RECOMENDADO
python scripts/main_dimensionamiento.py --escenario MEDIANO

# Listar escenarios disponibles
python scripts/main_dimensionamiento.py --lista
```

### Opción 2: Modo Interactivo (Windows)

```powershell
# Ejecutar menú interactivo
.\scripts\run_dimensionamiento.ps1
```

**Menú:**
```
1. CONSERVADOR (PE: 10%, FC: 80%)
2. MEDIANO (PE: 55%, FC: 60%)
3. RECOMENDADO (PE: 90%, FC: 90%)
4. MÁXIMO (PE: 100%, FC: 100%)
5. Ejecutar TODOS los escenarios
6. Listar escenarios
```

### Opción 3: Modo Interactivo (Linux/Mac)

```bash
# Ejecutar menú interactivo
./scripts/run_dimensionamiento.sh
```

---

## 📊 Salida de Datos

### Visualización en Consola

Cada ejecución genera:
- ✅ Resumen de Tabla 13 (rangos de referencia)
- ✅ Validación contra rangos OE2
- ✅ Cálculos de dimensionamiento para cada escenario
- ✅ Impacto ambiental (CO₂ evitado directo e indirecto)

**Ejemplo:**
```
📋 RECOMENDADO
   Penetración: 90% | Factor Carga: 90%
   Vehículos/día: 927 (810 motos + 117 mototaxis)
   Cargadores: 33 | Tomas: 132 | Energía: 3,252 kWh/día
   Sesiones pico (4h): 927
   CO₂ Directo evitado/año: 2,544,569 kg
```

### Archivos Generados

Después de ejecutar `--todos`, se generan:

**📁 `outputs/dimensionamiento/`**

#### JSON: `escenarios_dimensionamiento.json`
Datos estructurados para análisis y integración:
```json
[
  {
    "escenario": "RECOMENDADO",
    "penetracion": 0.9,
    "factor_carga": 0.9,
    "vehicles_day_total": 927,
    "cargadores": 33,
    "tomas_totales": 132,
    "energia_dia_kwh": 3252.0,
    "energia_anio_kwh": 1186980.0,
    "co2_direct_avoided_year_kg": 2544568.592,
    "co2_indirect_avoided_year_kg": 178877.886,
    "co2_net_avoided_year_kg": 2723446.478
  },
  ...
]
```

#### CSV: `escenarios_dimensionamiento.csv`
Datos tabulares para Excel/análisis:
```csv
escenario,penetracion,factor_carga,vehicles_day_total,cargadores,tomas_totales,...
CONSERVADOR,0.1,0.8,103,4,16,...
MEDIANO,0.55,0.6,567,20,80,...
RECOMENDADO,0.9,0.9,927,33,132,...
MÁXIMO,1.0,1.0,1030,35,140,...
```

---

## 🔍 Interpretación de Resultados

### Estructura de Datos de Salida

Cada escenario incluye:

| Campo | Descripción |
|-------|------------|
| `escenario` | Nombre (CONSERVADOR/MEDIANO/RECOMENDADO/MÁXIMO) |
| `penetracion` | % de vehículos que cargan (PE) |
| `factor_carga` | % de energía utilizada del máximo (FC) |
| `vehicles_day_motos` | Motos cargadas por día |
| `vehicles_day_mototaxis` | Mototaxis cargadas por día |
| `cargadores` | **Número de cargadores requeridos** |
| `tomas_totales` | **Número de tomas (sockets)** = cargadores × 4 |
| `energia_dia_kwh` | Energía diaria requerida (kWh) |
| `energia_anio_kwh` | Energía anual requerida (kWh) |
| `co2_direct_avoided_year_kg` | CO₂ evitado vs gasolina (kg/año) |
| `co2_indirect_avoided_year_kg` | CO₂ evitado vs grid térmico (kg/año) |
| `co2_net_avoided_year_kg` | CO₂ total evitado (kg/año) |

### Validación contra Tabla 13

La salida incluye marcas de validación:
- ✅ **VÁLIDO**: El escenario está dentro de los rangos de Tabla 13
- ⚠️ **ADVERTENCIA**: El escenario está fuera de rango (pero sigue siendo calculable)

**Rangos de Tabla 13:**
- Cargadores: 4-35 (promedio: 20.61)
- Tomas: 16-140 (promedio: 82.46)
- Energía: 92.8-3,252 kWh/día (promedio: 903.46)

---

## 💡 Casos de Uso

### 1. Validar Diseño Actual (RECOMENDADO)
```bash
python scripts/main_dimensionamiento.py --escenario RECOMENDADO
```
→ Muestra que se necesitan **33 cargadores × 4 tomas = 132 tomas** para cargar 927 vehículos/día

### 2. Comparar Escenarios
```bash
python scripts/main_dimensionamiento.py --todos
```
→ Genera tabla comparativa de todos los 4 escenarios en JSON y CSV

### 3. Estimar Impacto Ambiental
```bash
python scripts/main_dimensionamiento.py --todos
# Revisar outputs/dimensionamiento/escenarios_dimensionamiento.json
# Campo: co2_net_avoided_year_kg
```
→ RECOMENDADO evita **2.72 millones de kg CO₂/año** (2,723 tCO₂)

### 4. Análisis de Expansión
```bash
python scripts/main_dimensionamiento.py --escenario MÁXIMO
```
→ Muestra caso límite: 35 cargadores, 140 tomas, 4,014 kWh/día

---

## 📋 Referencia Rápida

### Archivos Clave

| Archivo | Descripción |
|---------|------------|
| `scripts/main_dimensionamiento.py` | Script principal (CLI) |
| `scripts/run_dimensionamiento.ps1` | Menú interactivo Windows |
| `scripts/run_dimensionamiento.sh` | Menú interactivo Linux/Mac |
| `outputs/dimensionamiento/` | Directorio de salida |

### Parámetros Fijos (DEFAULT_CONFIG)

```python
{
    'n_motos': 900,                    # Flota total motos
    'n_mototaxis': 130,                # Flota total mototaxis
    'session_minutes': 40,             # Duración sesión carga
    'utilization': 0.85,               # Utilización de chargers
    'sockets_per_charger': 4,          # Tomas por cargador
    'charger_power_moto': 2.0,         # kW por moto
    'charger_power_mototaxi': 3.0,     # kW por mototaxi
    'opening_hour': 9,                 # Apertura (9 AM)
    'closing_hour': 22,                # Cierre (10 PM)
    'peak_hours': [18, 19, 20, 21],   # Horas pico (6-10 PM)
}
```

---

## 🛠️ Troubleshooting

### Error: `ModuleNotFoundError: No module named 'iquitos_citylearn'`
**Solución:** Asegurate que estés en el directorio raíz del proyecto:
```bash
cd d:\diseñopvbesscar  # Windows
python scripts/main_dimensionamiento.py --lista
```

### Error: `UnicodeEncodeError` con emoji
**Solución:** Ya está solucionado en el script (UTF-8 encoding automático para Windows)

### Escenario aparece como "⚠️ ADVERTENCIA"
**Explicación:** El escenario está fuera de los rangos de Tabla 13 pero sigue siendo válido para cálculo. Revisa la columna `delta` en la salida.

---

## 📚 Información Adicional

### Conceptos Clave

- **PE (Penetración)**: % de la flota total que carga en el sistema en un día
- **FC (Factor de Carga)**: % de energía máxima utilizada por vehículo
- **Sesiones Pico (4h)**: Cantidad de vehículos cargándose durante horas pico (6-10 PM)
- **CO₂ Directo**: Emisión equivalente de gasolina que se evita (2.146 kg CO₂/kWh)
- **CO₂ Indirecto**: Emisión del grid térmico Iquitos que se evita (0.4521 kg CO₂/kWh)

### Conversiones

- 1 cargador = 4 tomas (sockets)
- 128 tomas = 32 cargadores (OE2 Full)
- 1,000 kg CO₂ = 1 tCO₂

---

## 🎓 Próximos Pasos

1. **Explorar Datos**: Abrir `outputs/dimensionamiento/escenarios_dimensionamiento.csv` en Excel
2. **Analizar Impacto**: Revisar columna `co2_net_avoided_year_kg` en JSON
3. **Validar Diseño**: Comparar valores calculados vs especificaciones OE2
4. **Integrar en OE3**: Los datos de cargadores se usan para configurar el entorno CityLearn OE3

---

**Última actualización**: 2026-02-04  
**Estado**: ✅ PRODUCCIÓN LISTA
