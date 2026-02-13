# ⚡ CHEAT SHEET: Limpieza de Cachés - Referencia Rápida

**Última Actualización**: 2026-02-04  
**Audience**: Developers, DevOps  
**Tiempo**: 2 minutos de lectura

---

## 🎯 Lo Esencial en 60 Segundos

### Estado Actual
```
__pycache__/     🟢 ELIMINADO (500 KB liberados)
.mypy_cache/     🟡 NO EXISTE (potencial 2-15 MB futuro)
Código Python    ✅ INTACTO (5 archivos preservados)
```

### Qué Hacer Hoy
```bash
# Nada - cachés se regeneran automáticamente
python -c "from src.agents import *"  # Esto regenera __pycache__
```

### Cuándo Limpiar Manualmente
```
__pycache__:  Rara vez (se regenera cada vez que importas)
.mypy_cache:  Mensualmente si >10 MB
```

---

## 🧹 Limpieza Rápida

### Eliminar __pycache__ (TODO el proyecto)
```powershell
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | 
    ForEach-Object { Remove-Item $_ -Recurse -Force }
```

### Eliminar .mypy_cache
```powershell
Remove-Item -Recurse -Force .mypy_cache/
```

### Regenerar (después de limpiar)
```bash
python -c "from src.agents import *"  # __pycache__
mypy src/                              # .mypy_cache
```

---

## 📊 Tamaños Típicos

| Caché | Tamaño | Cuándo |
|-------|--------|--------|
| __pycache__ en src/agents/ | 500 KB | Ya eliminado ✅ |
| __pycache__ en todo proyecto | 1-2 MB | Rare regenerable |
| .mypy_cache/ | 2-15 MB | Cuando ejecutas mypy |

---

## ✅ Validación Post-Limpieza

```bash
# 1. Verificar imports
python -c "from src.agents import *; print('OK')"

# 2. Verificar device detection
python -c "from src.agents import detect_device; print(detect_device())"

# 3. Verificar mypy
mypy src/ --version
```

---

## 📋 Checklist Mensual

- [ ] `du -sh .mypy_cache/` (ver tamaño)
- [ ] Si >10 MB: `Remove-Item -Recurse -Force .mypy_cache/`
- [ ] Ejecutar: `mypy src/` (regenerar)
- [ ] Validar: `python -c "from src.agents import *"`

---

## ❌ NO HAGAS ESTO

| ❌ No | ⚠️ Porqué | ✅ En su lugar |
|------|---------|-----------|
| Eliminar .venv/ | Necesario para desarrollar | `pip install -r requirements.txt` |
| Eliminar .git/ | Pierdes historial | Usa git restore |
| Editar .json en caché | Corrompe caché | Elimina y regenera |
| Commitar cachés a Git | Innecesario + conflictos | Usa .gitignore |
| Limpiar mientras mypy corre | Corrupción | Espera a que termine |

---

## 🔥 Emergencias

### "Accidentalmente eliminé algo"
```bash
git restore .  # Restaurar todo desde Git
```

### "Los imports no funcionan"
```bash
python -c "from src.agents import *"  # Regenera cachés
```

### ".mypy_cache crece infinitamente"
```bash
Remove-Item -Recurse -Force .mypy_cache/
mypy --no-incremental src/  # Regenerar sin caché
```

---

## 📈 Monitoreo

### Ver Tamaños
```powershell
# __pycache__ total
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | 
    ForEach-Object { 
        $size = (Get-ChildItem -Recurse $_ | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Host "$($_.FullName): $([math]::Round($size, 2)) MB"
    }

# .mypy_cache
if (Test-Path ".mypy_cache") {
    $size = (Get-ChildItem -Recurse .mypy_cache | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host ".mypy_cache: $([math]::Round($size, 2)) MB"
}
```

---

## 🤖 Automatización (Mensual)

### PowerShell Script
```powershell
# Nombre: Clean-Caches.ps1
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | 
    ForEach-Object { Remove-Item $_ -Recurse -Force -ErrorAction SilentlyContinue }

if (Test-Path ".mypy_cache") {
    $size = (Get-ChildItem -Recurse .mypy_cache | Measure-Object -Property Length -Sum).Sum / 1MB
    if ($size -gt 10) {
        Remove-Item -Recurse -Force .mypy_cache/
        Write-Host "✅ Limpieza completada"
    }
}
```

### Ejecutar
```powershell
powershell -ExecutionPolicy Bypass -File Clean-Caches.ps1
```

---

## 📚 Documentación

| Necesito | Leer |
|---------|------|
| Resumen rápido | RESUMEN_FINAL_LIMPIEZA_CACHÉS.md |
| Referencia completa | INDICE_LIMPIEZA_CACHÉS.md |
| Análisis técnico | ANALISIS_LIMPIEZA_AGENTS_CACHÉS.md |
| Cómo mantener limpio | GUIA_MANTENIMIENTO_AGENTS_LIMPIO.md |
| Qué es .mypy_cache | ANALISIS_MYPY_CACHE_LIMPIEZA.md |
| Automatización | GUIA_INTEGRAL_LIMPIEZA_CACHES.md |

---

## 🎯 TL;DR (Too Long, Didn't Read)

```
✅ __pycache__ fue limpiado (500 KB liberados)
📋 .mypy_cache documentado (potencial 2-15 MB futuro)
🔄 Cachés se regeneran automáticamente
✨ Cero impacto en desarrollo
⏰ Limpiar .mypy_cache mensualmente si >10 MB
📚 Documentación: 8 archivos disponibles
```

**Próximo Paso**: Lee [INDICE_LIMPIEZA_CACHÉS.md](INDICE_LIMPIEZA_CACHÉS.md)

---

*Última actualización: 2026-02-04*  
*Guardado en: Raíz del proyecto*
