#!/usr/bin/env python3
"""
Reconstruir CUMPLIMIENTO_ESTRICTO.md con el formato actualizado.
"""

contenido = """# Cumplimiento estricto - Tabla 9

Este proyecto valida el cumplimiento operacional con:
- Script: `scripts/VALIDAR_CUMPLIMIENTO_ESTRICTO.py`
- Reporte: `REPORTE_CUMPLIMIENTO.json`

Ejecuta el script despues de generar los outputs (ver `VALIDACION.md`).
"""

with open("CUMPLIMIENTO_ESTRICTO.md", "w", encoding="utf-8") as f:
    f.write(contenido)

print("OK CUMPLIMIENTO_ESTRICTO.md reconstruido")
