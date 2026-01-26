#!/usr/bin/env python3
"""
Analiza y corrige bess.py identificando líneas de código dentro de docstrings
"""
from pathlib import Path

def analyze_bess():
    """Analiza estructura de docstrings en bess.py"""
    file_path = Path("src/iquitos_citylearn/oe2/bess.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Rastrear docstrings
    in_docstring = False
    docstring_start = 0
    docstring_quotes = None

    issues = []

    for i, line in enumerate(lines, start=1):
        line_stripped = line.strip()

        # Detectar inicio/fin de docstring
        if '"""' in line or "'''" in line:
            quotes = '"""' if '"""' in line else "'''"
            if not in_docstring:
                in_docstring = True
                docstring_start = i
                docstring_quotes = quotes
                # Contar si es docstring de una línea
                if line_stripped.count(quotes) == 2:
                    in_docstring = False
            elif quotes == docstring_quotes:
                in_docstring = False

        # Si estamos dentro de un docstring, verificar líneas sospechosas
        if in_docstring:
            # Líneas que no deberían estar en docstrings
            if any(x in line_stripped for x in ['= np.zeros', '= np.ones', 'for h in range', 'current_soc', 'actual_charge']):
                if not line.startswith(' ' * 8):  # Más de 2 niveles de indentación
                    issues.append((i, docstring_start, f"Posible código en docstring: {line_stripped[:60]}"))

    return issues

if __name__ == "__main__":
    issues = analyze_bess()

    if issues:
        print("PROBLEMAS ENCONTRADOS:")
        for line_num, docstring_start, msg in issues:
            print(f"  Línea {line_num} (docstring comienza en {docstring_start}): {msg}")
    else:
        print("✅ No se encontraron problemas estructurales")

    # Mostrar líneas 265-280
    print("\n" + "="*60)
    print("LINEAS 265-280 (zona de problema):")
    print("="*60)

    with open("src/iquitos_citylearn/oe2/bess.py", 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i in range(264, min(280, len(lines))):
        print(f"{i+1:4d}: {lines[i]}", end='')
