#!/usr/bin/env python3
"""
Script para actualizar chargers.py con tipos modernos de Python 3.11+
"""
import re

# Leer archivo
with open('src/iquitos_citylearn/oe2/chargers.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazos sistemáticos
replacements = [
    # Cambiar tipos viejos por tipos nuevos
    (r'\bList\[', 'list['),
    (r'\bDict\[', 'dict['),
    (r'\bTuple\[', 'tuple['),
    (r'\bSet\[', 'set['),
]

# Primero hacer los reemplazos simples
for old, new in replacements:
    content = re.sub(old, new, content)

# Manejar Optional[X] -> X | None
# Patrón complejo para capturar tipos anidados
def replace_optional(match):
    tipo = match.group(1)
    # Si ya es un tipo con [], dejar como es
    if '[' in tipo:
        return f"{tipo} | None"
    return f"{tipo} | None"

# Buscar Optional[algo] donde algo puede tener puntos (ej: pd.DataFrame)
content = re.sub(r'Optional\[([a-zA-Z_][a-zA-Z0-9_\.]*(?:\[[^\]]*\])?)\]', replace_optional, content)

# Cambiar Tuple[np.ndarray, np.ndarray] a una forma compatible
content = re.sub(r'tuple\[np\.ndarray, np\.ndarray\]', 'tuple[NDArray[np.floating[Any]], NDArray[np.floating[Any]]]', content)

# Cambiar np.ndarray restantes a NDArray[np.floating[Any]]
content = re.sub(r'\bnp\.ndarray\b', 'NDArray[np.floating[Any]]', content)

# Guardar archivo
with open('src/iquitos_citylearn/oe2/chargers.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Archivo actualizado con tipos modernos de Python 3.11+")
