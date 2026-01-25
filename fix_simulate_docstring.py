#!/usr/bin/env python3
"""
Arregla el docstring roto en simulate_bess_operation
"""
from pathlib import Path

def fix_simulate_bess_docstring():
    """Corrige el docstring que contiene código"""
    file_path = Path("src/iquitos_citylearn/oe2/bess.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # El docstring de simulate_bess_operation empieza en línea 259
    # y debería cerrarse en línea 267 (después de "Resolucion: Horaria...")
    # Pero todo el código está dentro del docstring hasta línea 393

    # Solución: Cerrar el docstring en línea 267 y quitar """ de las líneas de código

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Si llegamos a la línea que dice "Resolucion: Horaria..."
        if i == 266:  # 0-indexed, así que 267 es índice 266
            # Cerrar el docstring aquí
            new_lines.append('    """\n')
            # Ahora las variables deben inicializarse
            n_hours = 'int(len(pv_kwh))'  # Calculado
            new_lines.append(f'    n_hours = len(pv_kwh)\n')
            new_lines.append('    grid_import_mall = np.zeros(n_hours)\n')
            new_lines.append('    grid_export = np.zeros(n_hours)\n')
            new_lines.append('    pv_used_ev = np.zeros(n_hours)\n')
            new_lines.append('    pv_used_mall = np.zeros(n_hours)\n')
            i += 1

            # Saltar líneas que estaban en el docstring (268-271)
            while i < len(lines) and 'grid_import_mall = np.zeros' in lines[i]:
                i += 1
            while i < len(lines) and 'grid_export = np.zeros' in lines[i]:
                i += 1
            while i < len(lines) and 'pv_used_ev = np.zeros' in lines[i]:
                i += 1
            while i < len(lines) and 'pv_used_mall = np.zeros' in lines[i]:
                i += 1
            while i < len(lines) and lines[i].strip() == '':
                i += 1
            continue

        new_lines.append(line)
        i += 1

    # Guardar archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print("✅ Docstring corregido en simulate_bess_operation")

if __name__ == "__main__":
    fix_simulate_bess_docstring()
