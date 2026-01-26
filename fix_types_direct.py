#!/usr/bin/env python3
import sys

# Leer todo el archivo
with open('src/iquitos_citylearn/oe2/chargers.py', 'r') as f:
    lines = f.readlines()

# Reemplazos simples línea por línea
new_lines = []
for line in lines:
    # Reemplazos directos
    line = line.replace('List[', 'list[')
    line = line.replace('Dict[', 'dict[')
    line = line.replace('Tuple[', 'tuple[')

    # Optional -> | None (más cuidadoso)
    # Optional[X] -> X | None
    import re
    line = re.sub(r'Optional\[([^]]+)\]', r'\1 | None', line)

    new_lines.append(line)

# Escribir de vuelta
with open('src/iquitos_citylearn/oe2/chargers.py', 'w') as f:
    f.writelines(new_lines)

print("✅ Archivo actualizado correctamente")
