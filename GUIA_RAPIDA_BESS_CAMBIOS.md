# GUIA RAPIDA: Modificaciones del BESS v5.7

## ¿Dónde están los parámetros del BESS?

### Opción 1: Configuración Simple (RECOMENDADO para modificaciones)
```python
# Archivo: src/dimensionamiento/oe2/disenobess/bess_config_simple.py
# Aquí están TODOS los parámetros en un solo lugar

BESS_SPECS = {
    'capacity_kwh': 2000.0,          # Cambiar capacidad aquí
    'power_kw': 400.0,               # Cambiar potencia aquí
    'efficiency_rtc': 0.95,          # Cambiar eficiencia aquí
}

SOC_LIMITS = {
    'min_percent': 20.0,             # CAMBIAR SOC MINIMO AQUI
    'max_percent': 100.0,            # CAMBIAR SOC MAXIMO AQUI
}

DISPATCH_RULES = {
    'ev_priority': True,             # Cambiar prioridad EV aquí
    'peak_shaving': True,            # Habilitar/deshabilitar peak shaving
    'peak_threshold_kw': 1900.0,     # Cambiar umbral de pico aquí
    'closing_hour': 22,              # Cambiar hora de cierre aquí
    'closing_soc_target': 0.20,      # Cambiar SOC objetivo cierre aquí
}
```

### Opción 2: Código Principal (Para cambios avanzados)
```python
# Archivo: src/dimensionamiento/oe2/disenobess/bess.py (líneas 193-197)

BESS_CAPACITY_KWH_V53 = 2000.0     # Línea 193
BESS_POWER_KW_V53 = 400.0          # Línea 194
BESS_DOD_V53 = 0.80                # Línea 195
BESS_EFFICIENCY_V53 = 0.95         # Línea 196
BESS_SOC_MIN_V53 = 0.20            # Línea 197 ← SOC MINIMO AQUI
BESS_SOC_MAX_V53 = 1.00            # Línea 198 ← SOC MAXIMO AQUI
```

## Verificar valores actuales del BESS

```bash
# Ver parámetros configurados
python -c "from src.dimensionamiento.oe2.disenobess.bess_config_simple import BESS_SUMMARY; print(BESS_SUMMARY)"

# Ver valores en dataset
python verify_soc_min.py
```

## Cambio más común: SOC mínimo del BESS

### Cambio de 20% a otro valor (ej: 15%)

1. **Opción rápida (recomendado):**
   - Editar `bess_config_simple.py` línea ~16:
   ```python
   'min_percent': 15.0,    # Cambiar de 20.0 a 15.0
   ```

2. **Opción completa (si affects lógica de despacho):**
   - Editar `bess.py` línea 197:
   ```python
   BESS_SOC_MIN_V53 = 0.15  # Cambiar de 0.20 a 0.15
   ```
   - Ejecutar:
     ```bash
     python scripts/transform_dataset_v57.py  # Regenerar dataset
     python scripts/regenerate_graphics_v57.py # Regenerar gráficos
     ```

## Validación después de cambios

```bash
# 1. Verificar que el SOC respeta límites
python verify_soc_min.py

# 2. Regenerar dataset transformado
python scripts/transform_dataset_v57.py

# 3. Regenerar gráficos
python scripts/regenerate_graphics_v57.py

# 4. Verificar archivos de salida
ls -lh reports/balance_energetico/
ls -lh data/processed/citylearn/iquitos_ev_mall/
```

## Estado actual (2026-02-19)

✅ **BESS VERIFICADO:**
- SOC mínimo: 20% (exacto)
- SOC máximo: 100% (exacto)
- Capacidad: 2,000 kWh
- DoD: 80% (1,600 kWh usables)
- Peak shaving a Mall: 611,757 kWh/año
- Cobertura EV: 141,748 kWh/año

## Archivos relacionados

```
├── src/dimensionamiento/oe2/disenobess/
│   ├── bess_config_simple.py      ← Configuración simplificada (AQUI)
│   └── bess.py                    ← Código principal (4800+ líneas)
├── data/oe2/bess/
│   └── bess_ano_2024.csv          ← Dataset generado (8760 × 34 cols)
└── scripts/
    ├── transform_dataset_v57.py   ← Regenera dataset transformado
    └── regenerate_graphics_v57.py ← Regenera gráficos
```
