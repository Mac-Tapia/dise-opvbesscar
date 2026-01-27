# ✓ VERIFICACION DE SCHEMA Y DATASETS - RESULTADO

## Status Actual: ✓ SCHEMA Y DATASETS LISTOS

### Datos Verificados:

✓ **Schema CityLearn**: `outputs/schema_building.json`
  - 8,760 timesteps (1 año completo, resolución horaria)
  - 128 chargers + 1 building (sistema centralizado)
  - Completamente conectado

✓ **Solar OE2**: `data/interim/oe2/solar/pv_generation_timeseries.csv`
  - 8,760 filas (resolución horaria exacta)
  - Timeseries AC generación fotovoltaica desde PVGIS

✓ **Chargers OE2**: `data/interim/oe2/chargers/individual_chargers.json`
  - 32 chargers × 4 sockets = 128 sockets total
  - Potencia: 2kW (motos), 3kW (mototaxis)

✓ **BESS OE2**: `data/interim/oe2/bess/bess_config.json`
  - Capacidad: 4,520 kWh
  - Potencia: 2,712 kW

✓ **Perfil Horario**: `data/interim/oe2/chargers/perfil_horario_carga.csv`
  - 24 horas de demanda horaria

✓ **Configuración**: `configs/default.yaml`
  - Dispatch rules habilitadas
  - Reward function configurada

---

## ⚠️ BLOQUEO ACTUAL: PYTHON 3.13 vs 3.11

**PROBLEMA**: 
- Tienes Python 3.13 instalado
- El proyecto REQUIERE Python 3.11 EXACTAMENTE
- Las librerías compiladas (CityLearn, Stable-Baselines3) no son compatibles con 3.13

**SOLUCION**:

### Opción 1: Rápida (Recomendada si NO tienes Python 3.11)

1. Descarga Python 3.11 desde: https://www.python.org/downloads/
2. Ejecuta: `.\INSTALAR_PYTHON_311.ps1`
3. Script automatiza: venv + instalación dependencias

### Opción 2: Manual (Si entiendes venv)

```powershell
# 1. Descarga e instala Python 3.11 manualmente
# 2. Crea venv
python3.11 -m venv .venv

# 3. Activa venv
.\.venv\Scripts\Activate.ps1

# 4. Instala dependencias
pip install -r requirements-training.txt

# 5. Verifica Python 3.11
python --version
# Debe mostrar: Python 3.11.x
```

### Opción 3: Usar version existente (si Python 3.11 ya existe)

Si Python 3.11 ya está instalado en tu sistema:

```powershell
# Crea venv directamente con 3.11
python3.11 -m venv .venv

# Activa
.\.venv\Scripts\Activate.ps1

# Verifica
python --version
# Debe mostrar: Python 3.11.x

# Instala deps
pip install -r requirements-training.txt
```

---

## Próximos Pasos (DESPUÉS de activar Python 3.11)

### Verificar schema + datasets están conectados:

```powershell
python verificar_schema_datasets.py
```

Salida esperada:
```
✓ VERIFICACIONES EXITOSAS: 7/7
✓ SCHEMA Y DATASETS TOTALMENTE CONECTADOS Y LISTOS
```

### Ejecutar A2C:

```powershell
python -m scripts.run_a2c_only --config configs/default.yaml
```

Salida esperada:
```
================================================================================
ENTRENAMIENTO A2C SOLAMENTE
================================================================================

[1/5] Validando Python 3.11...
      ✓ Python 3.11.x detectado

[2/5] Cargando configuración...
      ✓ config loaded

[3/5] Construyendo dataset CityLearn...
      ✓ Schema: outputs/schema_building.json (128 chargers, 8,760 timesteps)

[4/5] Ejecutando baseline...
      ✓ Baseline complete: CO2=XXXX kg/year

[5/5] Entrenando A2C...
      Episode 1 | Reward: -1200 | CO2: 9800 | Steps: 8760
      Episode 2 | Reward: -1050 | CO2: 9500 | Steps: 8760
      ...
```

---

## ✓ Verificación Final - Checklist

Antes de ejecutar A2C, asegúrate de:

- [ ] Python 3.11 instalado (`python3.11 --version` muestra Python 3.11.x)
- [ ] venv creado: `.venv` existe
- [ ] venv activado: Ves `(.venv)` al inicio de PowerShell
- [ ] Dependencias instaladas: `pip list | grep citylearn` muestra CityLearn
- [ ] `python --version` muestra Python 3.11.x (NO 3.13)
- [ ] `python verificar_schema_datasets.py` retorna 0 (éxito)

Una vez completado ✓, A2C está completamente listo para entrenar.

---

## Si algo falla

### Error: "Python 3.11 no encontrado"
```powershell
# Python 3.11 NO está en PATH
# Solución: Descarga e instala Python 3.11 con "Add to PATH" marcado
```

### Error: "ModuleNotFoundError"
```powershell
# Dependencias no instaladas
# Solución: pip install -r requirements-training.txt
```

### Error: Aún muestra Python 3.13
```powershell
# El venv está usando la versión equivocada
# Solución: Elimina venv y recrea con Python 3.11
Remove-Item -Recurse .venv
python3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

---

## Recursos

- Documentación: `INSTALAR_PYTHON_311_PASOS.txt`
- Script automático: `INSTALAR_PYTHON_311.ps1`
- Verificador schema: `verificar_schema_datasets.py`
