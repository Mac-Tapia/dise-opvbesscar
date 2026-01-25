#!/usr/bin/env python3
"""Script para corregir errores en sac.py automáticamente."""

import re
from pathlib import Path

def fix_sac_file():
    """Corrige errores comunes en sac.py."""
    file_path = Path("d:/diseñopvbesscar/src/iquitos_citylearn/oe3/agents/sac.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Reemplazar logger.info con f-strings por logging con %
    # Patrón: logger.info(f"...{var}...")
    pattern = r'logger\.info\(f"(.+?)"\)'
    replacement = lambda m: f'logger.info("{m.group(1).replace("{", "%s").replace("}", "")}")' if "{" in m.group(1) else m.group(0)

    # Función más simple para arreglar logging
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # Reemplazar f-strings en logger calls por % formatting
        if 'logger.' in line and 'f"' in line:
            # Extraer el patrón logger.XXX(f"...")
            match = re.search(r'logger\.(info|warning|error|debug)\(f"(.+?)"\)', line)
            if match:
                level = match.group(1)
                msg = match.group(2)
                # Contar variables {var} en el mensaje
                vars_in_msg = re.findall(r'\{([^}]+)\}', msg)
                if vars_in_msg:
                    # Reemplazar {var} con %s
                    msg_template = re.sub(r'\{[^}]+\}', '%s', msg)
                    # Obtener valores de las variables
                    vars_str = ', '.join(vars_in_msg)
                    new_line = line.replace(match.group(0), f'logger.{level}("{msg_template}", {vars_str})')
                    fixed_lines.append(new_line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    # 2. Reemplazar Exception general
    content = '\n'.join(fixed_lines)
    content = re.sub(r'except Exception:', 'except (ImportError, ModuleNotFoundError, AttributeError):', content)

    # 3. Agregar encoding a open()
    content = re.sub(r'open\("([^"]+)", "([^"]+)"\)', r'open("\1", "\2", encoding="utf-8")', content)

    # 4. Eliminar statements pass innecesarios
    content = re.sub(r'\n\s+pass\n', '\n', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ sac.py corregido exitosamente")

if __name__ == "__main__":
    fix_sac_file()
