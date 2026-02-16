#!/bin/bash
# Script para limpiar caché de Pylance
echo "🧹 Limpiando caché de Pylance..."

# Buscar todas las carpetas de pyrightconfig en la extensión de Pylance
PYLANCE_DIRS=$(find ~/.vscode/extensions -name "*pylance*" -type d 2>/dev/null)

for dir in $PYLANCE_DIRS; do
    echo "Limpiando: $dir"
    rm -rf "$dir/.cache" 2>/dev/null
    rm -rf "$dir/pyrightconfig.json" 2>/dev/null
done

echo "✅ Caché limpiado"
