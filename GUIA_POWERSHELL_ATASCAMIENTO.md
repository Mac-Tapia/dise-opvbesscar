# 🔧 GUÍA: CÓMO CORREGIR POWERSHELL CUANDO SE ATASCA

## 🚀 SOLUCIONES RÁPIDAS

### Opción 1: Ejecutar Script Automático (RECOMENDADO)
```powershell
& "scripts\optimize_powershell.ps1"
```
Esto:
- ✓ Mata procesos Python residuales
- ✓ Limpia caché de VS Code
- ✓ Configura variables de entorno
- ✓ Reactiva el ambiente virtual

### Opción 2: Comando Manual Rápido
```powershell
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
```

### Opción 3: Resetear Terminal desde VS Code
1. Presiona: `Ctrl + Shift + J` (abrir Terminal)
2. Haz clic en el botón "X" para cerrar el terminal actual
3. Presiona nuevamente `Ctrl + Shift + J` para abrir uno nuevo limpio

---

## 🔍 CAUSAS DEL ATASCAMIENTO

| Causa | Síntoma | Solución |
|-------|---------|----------|
| Procesos Python residuales | Terminal lento/congelado | Ejecutar `optimize_powershell.ps1` |
| Caché de Pylance corrupto | Autocompletado lento | Limpiar `.vscode` |
| Variables de entorno | Output desordenado | Recargar `$PROFILE` |
| Demasiados terminales abiertos | Sistema lento | Cerrar terminales no usados |

---

## ⚙️ VARIABLES DE ENTORNO CLAVE

Se configuran automáticamente en `optimize_powershell.ps1`:

```powershell
$env:PYTHONUNBUFFERED = 1            # Output sin buffer
$env:PYTHONDONTWRITEBYTECODE = 1     # No crear .pyc
$env:PYTHONIOENCODING = "utf-8"      # Encoding correcto
$env:PYTHONWARNINGS = "ignore"       # Suprimir warnings
```

---

## 🔬 DIAGNÓSTICO

### Ver procesos activos:
```powershell
Get-Process python | Select-Object Name, Id, CPU, Memory
```

### Ver RAM disponible:
```powershell
Get-WmiObject -Class win32_operatingsystem | Select-Object FreePhysicalMemory
```

### Ver directorios temporales:
```powershell
ls $env:TEMP | Measure-Object | Select-Object Count
```

---

## 💡 PREVENCIÓN

1. **Ejecutar una vez por sesión:**
   ```powershell
   & "scripts\optimize_powershell.ps1"
   ```

2. **Al iniciar VS Code:**
   - El script se puede añadir al `$PROFILE` de PowerShell si es necesario

3. **Monitorear procesos:**
   ```powershell
   # Cada 10 segundos, mostrar procesos Python
   while($true) { 
       Clear-Host
       Get-Process python -ErrorAction SilentlyContinue
       Start-Sleep -Seconds 10 
   }
   ```

---

## 📝 RESUMEN RÁPIDO

| Acción | Comando |
|--------|---------|
| Limpiar TODO | `& "scripts\optimize_powershell.ps1"` |
| Matar Python | `Get-Process python \| Stop-Process -Force` |
| Cerrar Terminal | `exit` |
| Nuevo Terminal | `Ctrl + Shift + J` |

**Última actualización:** 2026-02-12
