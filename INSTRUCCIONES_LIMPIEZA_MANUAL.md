# ⚠️ LIMPIEZA MANUAL REQUERIDA

**Status**: Terminal de VS Code no responde a comando - instrucciones manuales proporcionadas

**Lo que necesitas hacer**: Ejecutar uno de estos comandos en PowerShell (ejecuta como administrador)

---

## 🔧 Opción 1: Usando PowerShell (RECOMENDADO)

```powershell
# Abre PowerShell como Administrador
# Luego copia y pega esto:

cd d:\diseñopvbesscar

# Eliminar 128 archivos charger_simulation
for ($i=1; $i -le 128; $i++) {
    $num = "{0:D3}" -f $i
    Remove-Item "data\processed\citylearn\iquitos_ev_mall\charger_simulation_$num.csv" -ErrorAction SilentlyContinue
}

# Eliminar 2 variant schemas
Remove-Item "data\processed\citylearn\iquitos_ev_mall\schema_grid_only.json" -ErrorAction SilentlyContinue
Remove-Item "data\processed\citylearn\iquitos_ev_mall\schema_pv_bess.json" -ErrorAction SilentlyContinue

Write-Host "✅ Eliminación completada"
```

---

## 🔧 Opción 2: Ejecutar script Python creado

```bash
# En PowerShell normal (no necesita admin):
cd d:\diseñopvbesscar
python cleanup_unused_files.py
```

---

## 🔧 Opción 3: Ejecutar batch file

```bash
# En cmd.exe:
cd d:\diseñopvbesscar
cleanup.bat
```

---

## 📊 Qué se eliminará

```
✓ charger_simulation_001.csv  → charger_simulation_128.csv    (128 archivos)
✓ schema_grid_only.json
✓ schema_pv_bess.json

Total: 130 archivos
Espacio liberado: ~140 MB
```

---

## ✅ Verificación

Después de ejecutar, verifica que estos archivos CRÍTICOS aún existen:

```
✓ Generacionsolar/pv_generation_hourly_citylearn_v2.csv
✓ chargers/chargers_real_hourly_2024.csv
✓ chargers/chargers_real_statistics.csv
✓ demandamallkwh/demandamallhorakwh.csv
✓ electrical_storage_simulation.csv
✓ schema.json
```

Todos los anteriores DEBEN existir. Si alguno desaparece, algo salió mal.

---

## 📝 Archivos de soporte creados

- `cleanup_unused_files.py` - Script Python completo con logging
- `cleanup_simple.py` - Script Python simple
- `cleanup.bat` - Script Batch de Windows
- `do_cleanup.py` - Script minimalista

Elige cualquiera de los anteriores para ejecutar manualmente.

