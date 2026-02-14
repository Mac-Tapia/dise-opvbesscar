# 🚀 GUÍA RÁPIDA - Reconstrucción OE2 v5.2

**⏱️ Tiempo total: 2 minutos**

---

## Opción A: Reconstrucción Solo

```bash
python scripts/validate_and_rebuild_oe2.py
```

**Salida esperada:**
```
✅ ESTADO FINAL: EXITOSO
✓ Solar: 4050.0 kWp
✓ BESS: 1700.0 kWh
✓ Chargers: 19 units, 38 sockets
✓ Mall Demand: 1411.9 kW avg
🎯 LISTO PARA ENTRENAR: SAC | PPO | A2C
```

---

## Opción B: Reconstrucción + Limpieza (RECOMENDADO)

```bash
python scripts/validate_and_rebuild_oe2.py --cleanup
```

**Lo que pasa:**
- ✓ Valida 4 datasets principales
- ✓ Elimina 5 duplicados en `data/interim/oe2/`
- ✓ Libera ~500 MB de espacio
- ✓ Reporte de estado

---

## Opción C: En Python

```python
from src.dimensionamiento.oe2.disenocargadoresev.data_loader import rebuild_oe2_datasets_complete

result = rebuild_oe2_datasets_complete(cleanup_interim=True)

if result["is_valid"]:
    print("✓ Listo para entrenar")
    # Proceder
```

---

## ¿Qué fue actualizado?

| Archivo | Cambio | Líneas |
|---------|--------|--------|
| `data_loader.py` | 3 funciones nuevas + integración | +250 |
| `scripts/validate_and_rebuild_oe2.py` | Script CLI nuevo | +150 |
| `docs/*.md` | 2 guías completas nuevas | +800 |

---

## Datasets Validados

```
✓ Solar:        4,050 kWp | 946.6 kW avg
✓ BESS:         1,700 kWh | 342 kW power
✓ Chargers:     38 sockets | 281.2 kW installed
✓ Mall Demand:  1,411.9 kW avg
✓ Timesteps:    8,760 horas (1 año) cada uno
```

---

## Duplicados Eliminados

```
🗑️  5 archivos eliminados de data/interim/oe2/
🗑️  ~500 MB liberados
```

---

## Si algo falla

```bash
# 1. Ejecutar con limpieza
python scripts/validate_and_rebuild_oe2.py --cleanup

# 2. Si error persiste:
# - Ver: OE2_RECONSTRUCTION_NO_DUPLICITY.md (Troubleshooting)
# - O: INTEGRATION_CLEAN_TRAINING.md (Integración)
```

---

## Entrenar Agente

Después de reconstrucción:

```bash
# SAC
python scripts/train/train_sac_multiobjetivo.py

# O PPO
python scripts/train/train_ppo_multiobjetivo.py

# O A2C
python scripts/train/train_a2c_multiobjetivo.py
```

---

## ¿Más info?

- 📖 Reconstrucción detallada: [OE2_RECONSTRUCTION_NO_DUPLICITY.md](docs/OE2_RECONSTRUCTION_NO_DUPLICITY.md)
- 🔌 Integración RL: [INTEGRATION_CLEAN_TRAINING.md](docs/INTEGRATION_CLEAN_TRAINING.md)
- 📊 Resumen completo: [RESUMEN_COMPLETO_RECONSTRUCCION_OE2.md](RESUMEN_COMPLETO_RECONSTRUCCION_OE2.md)

---

**Estado:** ✅ Listo  
**Última actualización:** 2026-02-13
