## 🔄 Sistema Automático de Actualización v5.8

Balance energético se **actualiza automáticamente** cada vez que cambian los datasets sin necesidad de intervención manual.

---

## ⚡ Uso Rápido

### Opción 1: Regeneración Inteligente (RECOMENDADO)

```bash
# Un comando para TODO - detecta cambios y regenera según sea necesario
python scripts/regenerate_all_auto.py
```

**Qué hace:**
✅ Detecta cambios en BESS, Solar, EV Chargers  
✅ Si BESS cambió: transforma dataset  
✅ Regenera gráficas automáticamente  
✅ Ahorra tiempo: no regenera si no hay cambios  

**Salida:**
- `data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv` (si BESS cambió)
- `reports/balance_energetico/*.png` (15 gráficas)

---

### Opción 2: Forzar Regeneración

```bash
# Regenera todo sin detectar cambios previamente
python scripts/regenerate_balance_auto.py --force
```

---

### Opción 3: Scripts Individuales (Si necesitas control fino)

```bash
# 1. Solo transformar dataset BESS
python scripts/transform_dataset_v57.py

# 2. Solo regenerar gráficas
python scripts/regenerate_graphics_v57.py

# 3. Verificar cambios sin regenerar
python src/utils/dataset_change_detector.py
```

---

## 📊 Datasets Monitoreados Automáticamente

El sistema detecta cambios en:

| Dataset | Ubicación | Tipo |
|---------|-----------|------|
| **BESS** | `data/oe2/bess/bess_ano_2024.csv` | Batería de almacenamiento |
| **SOLAR** | `data/interim/oe2/solar/pv_generation_timeseries.csv` | Generación PV |
| **EV CHARGERS** | `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` | Perfiles de carga EV |
| **TRANSFORMED** | `data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv` | Dataset derivado |

---

## 🔧 Cómo Modifica Balance.py

Cuando ejecutas `regenerate_all_auto.py`:

1. **Detector de cambios** (`DatasetChangeDetector`)
   - Computa hash SHA256 de cada dataset
   - Compara con estado anterior
   - Guarda nuevo estado en `.dataset_state.json`

2. **Balance.py auto-update** (v5.8)
   - Usa `DatasetChangeDetector` al inicializarse
   - Reporta cambios detectados
   - Dispara regeneración automática si `auto_update=True`

3. **Pipeline automático**
   ```
   Detectar cambios → Transform BESS (si cambió) → Regenerar gráficas
   ```

---

##  🗂️ Archivos De Control

**Estado de datasets:**
```
data/processed/citylearn/.dataset_state.json
```

Contiene hashes y timestamps de última ejecución. **NO MODIFICAR MANUALMENTE.**

Para forzar regeneración completa:
```bash
rm data/processed/citylearn/.dataset_state.json
python scripts/regenerate_all_auto.py
```

---

## ✅ Verificación

Después de ejecutar:

```bash
# Ver resumen de generación
ls -lh reports/balance_energetico/

# Verificar SOC del BESS (debe ser 20-100%)
python verify_soc_min.py

# Verificar datasets cargados correctamente
python src/utils/dataset_change_detector.py
```

---

## 💡 Casos de Uso

**Escenario 1:** Cambias parámetros BESS en `bess_ano_2024.csv`
```bash
# Tu editor modifica: data/oe2/bess/bess_ano_2024.csv
# Luego ejecutas:
python scripts/regenerate_all_auto.py
# ✅ Detecta cambio BESS → Transforma → Regenera gráficas
```

**Escenario 2:** Actualizas generación solar
```bash
# Tu sistema actualiza: data/interim/oe2/solar/pv_generation_timeseries.csv
python scripts/regenerate_all_auto.py
# ✅ Detecta cambio SOLAR → Regenera gráficas
```

**Escenario 3:** Quieres regenerar forzadamente
```bash
python scripts/regenerate_balance_auto.py --force
# ✅ Regenera sin detectar cambios (útil para debugging)
```

---

## 🔍 Verbose Mode (Detalles)

```bash
python scripts/regenerate_balance_auto.py --verbose
# Muestra cada dataset monitoreado y su tamaño
```

---

## 📌 Integración con CI/CD

Si tienes un pipeline automatizado:

```yaml
# GitHub Actions / GitLab CI example
regenerate_balance:
  script:
    - python scripts/regenerate_all_auto.py
```

El sistema es idempotent: ejecutarlo múltiples veces es seguro.

---

## 🐛 Diagnóstico

Si algo funciona mal:

```bash
# 1. Ver qué datasets existen
ls -la data/oe2/bess/
ls -la data/interim/oe2/solar/
ls -la data/oe2/chargers/

# 2. Forzar regeneración completa
rm data/processed/citylearn/.dataset_state.json
python scripts/regenerate_all_auto.py --force

# 3. Verificar integridad
python verify_soc_min.py
```

---

v5.8 - February 2026
