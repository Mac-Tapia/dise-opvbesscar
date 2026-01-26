#!/usr/bin/env python3
"""Actualizar tipos en chargers.py"""

filepath = 'src/iquitos_citylearn/oe2/chargers.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazos simples de texto
replacements = {
    'List[': 'list[',
    'Dict[': 'dict[',
    'Tuple[': 'tuple[',
}

for old, new in replacements.items():
    content = content.replace(old, new)

# Manejo especial de Optional
import re
# Optional[X] -> X | None (siendo cauteloso con el regex)
content = re.sub(r'Optional\[([a-zA-Z0-9_\[\], \.]+)\]', r'\1 | None', content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Actualización completada")
import subprocess
subprocess.run(['git', 'status'])
