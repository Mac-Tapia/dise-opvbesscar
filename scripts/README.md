# Scripts - Pipeline de Entrenamiento OE3

📖 **Guía completa:** [INDEX_SCRIPTS_ESENCIALES.md](INDEX_SCRIPTS_ESENCIALES.md)

---

## ⚡ Quick Start (30 segundos)

```bash
# TODO EN 1 COMANDO:
python -m scripts.run_training_sequence --config configs/default.yaml
```

**Qué hace:**
- ✅ Construye dataset desde OE2 artifacts
- ✅ Entrena SAC, PPO, A2C
- ✅ Genera tabla comparativa CO₂

**Duración:** 50-70 minutos (GPU)

---

## 📋 Scripts Esenciales

| Script | Propósito | Paso |
|--------|-----------|------|
| `_common.py` | Configuración | - |
| `run_oe3_build_dataset.py` | Construir dataset | 1️⃣ |
| `run_oe3_simulate.py` | Entrenar agentes | 2️⃣ |
| `run_training_sequence.py` | **Pipeline completo** | 🚀 |
| `run_uncontrolled_baseline.py` | Baseline | alt |
| `run_oe3_co2_table.py` | Resultados | 3️⃣ |

---

## 🏃 Paso a Paso

```bash
# PASO 1: Dataset (30-60 seg)
python -m scripts.run_oe3_build_dataset

# PASO 2: Entrenar (50 min)
python -m scripts.run_training_sequence

# PASO 3: Resultados (10 seg)
python -m scripts.run_oe3_co2_table
```

---

## 📁 Archivos Archivados

Todos los scripts obsoletos, de debugging y versiones antiguas están en:
- `archive/` ← 104 archivos (para referencia histórica)

---

**Última actualización:** 2026-02-01  
**Estado:** ✅ Listo para entrenar
