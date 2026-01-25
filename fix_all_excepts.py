#!/usr/bin/env python3
"""Limpiar todos los errores de except sin cuerpo en sac.py."""

from pathlib import Path

def fix_all_except_errors():
    """Arregla todos los except sin cuerpo."""
    file_path = Path("src/iquitos_citylearn/oe3/agents/sac.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        fixed_lines.append(line)

        # Si es except
        if line.rstrip().endswith(':') and 'except' in line:
            # Obtener nivel de indentación
            indent_len = len(line) - len(line.lstrip())
            next_indent = ' ' * (indent_len + 4)

            # Verificar si necesita pass
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Si la siguiente línea está menos indentada o no es contenido
                if next_line.strip() and (len(next_line) - len(next_line.lstrip())) <= indent_len:
                    # Insertar pass
                    fixed_lines.append(f'{next_indent}pass\n')

        i += 1

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print("✅ Todos los except sin cuerpo han sido arreglados")

if __name__ == "__main__":
    fix_all_except_errors()
