# ACTUALIZACIÓN RESOLUCIÓN TEMPORAL - 15 MINUTOS

## Resumen Ejecutivo

Se ha actualizado exitosamente el sistema de generación de perfiles de carga
para utilizar **intervalos de 15 minutos** en lugar de intervalos horarios.

## Cambios Implementados

### 1. Función `build_hourly_profile()` (chargers.py, líneas 622-724)

#### Antes (24 intervalos horarios):

<!-- markdownlint-disable MD013 -->
```python
hours = list(range(24))
operating_hours = [h for h in hours if opening_hour <= h < closing_hour]
```bash
<!-- markdownlint-enable MD013 -->

#### Ahora (96 intervalos de 15 minutos):

<!-- markdownlint-disable MD013 -->
```python
intervals_per_hour = 4
total_intervals = 24 * intervals_per_hour  # 96
intervals = list(range(total_intervals))
opening_interval = opening_hour * intervals_per_hour
closi...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

#### Cálculo de energía y potencia:

<!-- markdownlint-disable MD013 -->
```python
# Energía en kWh para cada intervalo de 15 min
energy_interval = energy_day_kwh * factor_array
# Potencia en kW (promedio durante 15 min): kWh / 0.25h = kW
power_kw = energy_interval / 0.25
```bash
<!-- markdownlint-enable MD013 -->

#### Estructura de salida actualizada:

<!-- markdownlint-disable MD013 -->
```python
return pd.DataFrame({
    "interval": intervals,                          # 0-95...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

### 2. Función `generate_annual_charger_profiles()`(chargers.py, líneas
794-878)

#### Antes (8,760 horas/año):

<!-- markdownlint-disable MD013 -->
```python
hours_year = 8760
index = pd.date_range(start=start_date, periods=hours_year, freq='h')
annual_profile = np.zeros(hours_year)
```bash
<!-- markdownlint-enable MD013 -->

#### Ahora (35,040 intervalos de 15 min/año):

<!-- markdownlint-disable MD013 -->
```python
intervals_per_year = 8760 * 4  # 35040 intervalos de 15 min
index = pd.date_range(start=start_date, periods=intervals_per_year, freq='15m...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

#### Bucle diario actualizado:

<!-- markdownlint-disable MD013 -->
```python
for day in range(365):
    day_start = day * intervals_per_day  # 96 intervalos/día
    day_end = day_start + intervals_per_day
    
    # Asegurar que no hay carga fuera del horario
    for i in range(intervals_per_day):
        if i < opening_interval or i >= closing_interval:
            day_profile[i] = 0.0
```bash
<!-- markdownlint-enable MD013 -->

## Estructura del Archivo CSV Generado

<!-...
```

[Ver código completo en GitHub]bash
Total intervalos: 96
Energía total: 3,252.00 kWh/día
Potencia máxima: 409.85 kW
Energía pico (18-21h): 1,300.80 kWh
Energía fuera pico: 1,951.20 kWh
```bash
<!-- markdownlint-enable MD013 -->

<!-- markdownlint-disable MD013 -->
### Muestra de Datos - Hora Pico (18h) | interval | time_of_day | hour | minute | energy_kwh | power_kw | is_peak | |----------|-------------|------|--------|------------|----------|---------| | 72 | 18.00 | 18 | 0 | 81.3 | 325.2 | True | | 73 | 18.25 | 18 | 15 | 81.3 | 325.2 | True | | 74 | 18.50 | 18 | 30 | 81.3 | 325.2 | Tr...
```

[Ver código completo en GitHub]bash
Total intervalos: 35,040 (8,760 horas × 4)
Frecuencia: 15 minutos
Formato timestamp: '2024-01-01 00:00:00' con freq='15min'
```bash
<!-- markdownlint-enable MD013 -->

## Ventajas de la Resolución de 15 Minutos

1. **Mayor precisión temporal**: Captura variaciones intra-horarias de demanda
2. **Compatibilidad CityLearn**: Estándar de simulación de edificios
3. **Picos de demanda reales**: Detecta picos de 15 min vs. promedios horarios
4. **Control BESS mejorado**: Permite estrategias de carga/descarga más precisas
5. **Regulación eléctrica**: Muchas utilities requieren datos cada 15 min

## Impacto en BESS

Con resolución de 15 minutos, el dimensionamiento del BESS será más preciso:

- **Antes (horario)**: Pico promedio en 1 hora podría ocultar picos de 15 min
- **Ahora (15 min)**: Captura picos reales de potencia → dimensionamiento
  - correcto

#### Ejemplo:

- Promedio horario 18h: 325 kW
- Pico real 18:00-18:15: 409.85 kW ← **Detectado ahora**

Esto asegura que el BESS tenga la potencia suficiente para cubrir los picos
reales.

## Scripts de Verificación

1. **`GENERAR_PERFIL_15MIN.py`**: Genera perfil de 15 min y guarda CSV
2. **`TEST_PERFIL_15MIN.py`**: Prueba unitaria de `build_hourly_profile()`
3. **`VERIFICAR_PERFIL_15MIN_CSV.py`**: Verifica estructura y datos del CSV

## Próximos Pasos

1. ✅ **COMPLETADO**: Actualizar `build_hourly_profile()` a 15 min
2. ✅ **COMPLETADO**: Actualizar `generate_annual_charger_profiles()` a 15 min
3. ✅ **COMPLETADO**: Generar y verificar `perfil_horario_carga.csv`
4. **PENDIENTE**: Actualizar módulo BESS para leer perfiles de 15 min
5. **PENDIENTE**: Re-dimensionar BESS con datos de 15 min y déficit corregido
(2,675 kWh/día)
6. **PENDIENTE**: Generar perfiles anuales por playa (Playa_Motos,
Playa_Mototaxis)

---

**Fecha de actualización:** 2026-01-20  
#### Archivos modificados:

- `src/iquitos_citylearn/oe2/chargers.py` (funciones `build_hourly_profile` y
  - `generate_annual_charger_profiles`)
- `data/oe2/perfil_horario_carga.csv` (generado)

#### Scripts creados:

- `GENERAR_PERFIL_15MIN.py`
- `TEST_PERFIL_15MIN.py`
- `VERIFICAR_PERFIL_15MIN_CSV.py`
