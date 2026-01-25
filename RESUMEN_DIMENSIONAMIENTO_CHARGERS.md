# DIMENSIONAMIENTO DE CARGADORES EV - MODO 3 (IEC 61851)

## REGLAS DE DIMENSIONAMIENTO

### 1. Parámetros de Entrada (Hora Pico)

- **900 motos** en hora pico (6pm-10pm, 4 horas)
- **130 mototaxis** en hora pico (6pm-10pm, 4 horas)
- **TOTAL: 1,030 vehículos** en ventana de 4 horas

**IMPORTANTE**: Estos valores son SOLO para dimensionar la cantidad de cargadores y tomas necesarios.

### 2. Resultado del Dimensionamiento

- **32 cargadores totales**
  - 28 cargadores para motos (112 tomas) × 2.0 kW = 224 kW
  - 4 cargadores para mototaxis (16 tomas) × 3.0 kW = 48 kW
- **128 tomas totales** (32 cargadores × 4 tomas/cargador)
- **Potencia instalada: 272 kW**

### 3. Operación Diaria

Los cargadores dimensionados operan **TODO EL DÍA**:

- **Horario**: 9:00 AM - 10:00 PM (13 horas)
- **Modo 3**: Sesiones de 30 minutos
- **Sesiones por toma**: 13h × 2 sesiones/hora = 26 sesiones/día
- **Utilización**: 92%

### 4. Capacidad Total de la Infraestructura

#### Capacidad Diaria

```
128 tomas × 26 sesiones/día × 92% utilización = 3,062 vehículos/día
```

#### Proyecciones

- **Mensual**: 3,062 × 30 días = **91,860 vehículos/mes**
- **Anual**: 3,062 × 365 días = **1,117,630 vehículos/año**
- **20 años**: 1,117,630 × 20 = **22,352,600 vehículos**

## CARACTERÍSTICAS TÉCNICAS

### Modo de Carga: Modo 3 (IEC 61851)

- **Motos**: 2.0 kW por toma
- **Mototaxis**: 3.0 kW por toma
- **Duración de sesión**: 30 minutos fijos
- **Tomas por cargador**: 4 tomas controlables

### Distribución por Playa de Estacionamiento

#### Playa de Motos

- 28 cargadores
- 112 tomas (28 × 4)
- 224 kW instalados
- 2,679 kWh/día (escenario base)

#### Playa de Mototaxis

- 4 cargadores
- 16 tomas (4 × 4)
- 48 kW instalados
- 573 kWh/día (escenario base)

## DATOS GUARDADOS

### Archivo: `chargers_results.json`

```json
{
  "n_motos_pico": 900,
  "n_mototaxis_pico": 130,
  "n_chargers_recommended": 32,
  "potencia_total_instalada_kw": 272.0,
  "capacidad_infraestructura_dia": 3062,
  "capacidad_infraestructura_mes": 91860,
  "capacidad_infraestructura_anio": 1117630,
  "capacidad_infraestructura_20anios": 22352600
}
```

## RESUMEN EJECUTIVO

1. **Dimensionamiento**: 900 motos + 130 mototaxis en hora pico → 32 cargadores (128 tomas)
2. **Operación**: Los 128 tomas operan 13h/día (9am-10pm) con sesiones de 30 min
3. **Capacidad**: 3,062 vehículos/día, 1.1 millones/año, 22.3 millones en 20 años
4. **Potencia**: 272 kW instalados (224 kW motos + 48 kW mototaxis)
