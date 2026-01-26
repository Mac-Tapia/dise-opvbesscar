# VERIFICACION Y GENERACION - DATOS CARGADORES OE3

## Fecha: 2026-01-25 22:15:00

## Resumen Ejecutivo

✓ Sistema de cargadores OE2 completamente verificado y generado
✓ 128 cargadores configurados (112 motos + 16 mototaxis)
✓ Perfiles horarios generados (8,760 horas = 365 días × 24 horas)
✓ Schema JSON para integración CityLearn creado

## Configuración de Cargadores

### Motos Eléctricas
- **Cantidad**: 112 cargadores
- **Potencia**: 2.0 kW por cargador
- **Sockets**: 4 por cargador = 448 sockets totales
- **Capacidad instalada**: 224 kW
- **Ubicación**: Playa_Motos (Iquitos)

### Mototaxis Eléctricos
- **Cantidad**: 16 cargadores
- **Potencia**: 3.0 kW por cargador
- **Sockets**: 4 por cargador = 64 sockets totales
- **Capacidad instalada**: 48 kW
- **Ubicación**: Playa_Mototaxis (Iquitos)

### Sistema Completo
- **Total cargadores**: 128
- **Total sockets**: 512
- **Potencia máxima**: 272 kW
- **Eficiencia**: 95% (0.95)
- **Conector**: Type2

## Perfil de Carga Horario

### Horario Operación
- **Apertura**: 09:00
- **Cierre**: 22:00
- **Horas operación**: 13 horas/día
- **Horas pico**: 18:00-22:00 (4 horas)

### Patrón de Demanda
- **Fuera de operación (00:00-09:00, 22:00-24:00)**: 0% carga (0 kW)
- **Fuera de pico (09:00-18:00)**: 50% carga
  - Motos: 112 × 2 × 0.5 = 112 kW
  - Mototaxis: 16 × 3 × 0.5 = 24 kW
  - **Total**: 136 kW
- **Pico (18:00-22:00)**: 100% carga
  - Motos: 112 × 2 × 1.0 = 224 kW
  - Mototaxis: 16 × 3 × 1.0 = 48 kW
  - **Total**: 272 kW (capacidad máxima)

### Energía Anual Estimada

Motos:
- Horas fuera operación: 8,760 × (11/24) = 4,015 h → 0 kWh
- Horas fuera pico: 365 × 9 = 3,285 h × 112 kW = 367,920 kWh
- Horas pico: 365 × 4 = 1,460 h × 224 kW = 327,040 kWh
- **Subtotal motos**: 694,960 kWh/año

Mototaxis:
- Horas fuera operación: 4,015 h → 0 kWh
- Horas fuera pico: 3,285 h × 24 kW = 78,840 kWh
- Horas pico: 1,460 h × 48 kW = 70,080 kWh
- **Subtotal mototaxis**: 148,920 kWh/año

**Total anual**: 843,880 kWh (843.9 MWh/año)

## Integración OE2 ↔ OE3

### Archivos Generados
1. **individual_chargers.json**: Configuración de 128 cargadores
   - ID único para cada cargador
   - Tipo (moto/mototaxi)
   - Potencia nominal (2.0 o 3.0 kW)
   - Ubicación (lat/lon Iquitos)
   - Eficiencia y especificaciones

2. **perfil_horario_carga.csv**: Perfil horario (8,760 horas)
   - Hour: [0-8759]
   - hour_of_day: [0-23]
   - date: YYYY-MM-DD
   - Factores de carga por tipo
   - Demanda total por hora

3. **chargers_schema.json**: Schema CityLearn
   - Configuración de control
   - Pesos multi-objetivo
   - Rutas de datos
   - Parámetros de operación

### Coherencia Sistema Completo

| Componente | Especificación | Status |
|-----------|---|---|
| Solar PV | 4,050 kWp → 8,030 MWh/año | ✓ Verificado |
| BESS | 2,000 kWh / 1,200 kW | ✓ Verificado |
| Cargadores | 272 kW → 844 MWh/año | ✓ Generado |
| Perfil carga | 8,760 horas (1 año) | ✓ Generado |
| Schema JSON | CityLearn compatible | ✓ Generado |

### Ratio Oversizing
- Solar / EV: 8,030 / 844 = **9.5×** (sistema altamente sobredimensionado)
- BESS es 2.4× la energía diaria de EV (déficit nocturno cubierto)

## Listo para OE3

✓ Todos los datos OE2 generados y verificados
✓ Coherencia de dimensionamiento confirmada
✓ JSON schemas listos para CityLearn
✓ Perfiles horarios (8,760 horas) generados
✓ Sistema ready para entrenamiento RL

**Próximos pasos**:
1. Ejecutar `python run_training_optimizado.py`
2. Seleccionar opción 4: Secuencia SAC → PPO → A2C
3. Monitorear GPU durante entrenamiento
4. Analizar resultados CO₂

---
*Generado automáticamente por verify_and_generate_chargers_data.py*
