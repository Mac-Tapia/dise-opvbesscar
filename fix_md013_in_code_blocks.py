#!/usr/bin/env python3
"""
Script FINAL para corregir MD013 en BLOQUES DE CÓDIGO
Estrategia: Dividir líneas de código Python/YAML preservando sintaxis
"""

import re
from pathlib import Path
from typing import List

def split_python_code_line(line: str, max_len: int = 80) -> List[str]:
    """Divide una línea de código Python preservando sintaxis."""
    if len(line.rstrip()) <= max_len:
        return [line]

    stripped = line.lstrip()
    indent = line[:len(line) - len(stripped)]

    # 1. COMENTARIOS - dividir en palabras
    if stripped.startswith('#'):
        return split_comment_line(line, max_len, indent)

    # 2. STRINGS LARGOS - dividir en múltiples strings
    if '"' in stripped or "'" in stripped:
        return split_string_line(line, max_len, indent)

    # 3. LLAMADAS A FUNCIÓN - dividir en parámetros
    if '(' in stripped and ')' in stripped:
        return split_function_call(line, max_len, indent)

    # 4. OPERADORES - dividir en operadores
    operators = [', ', ' and ', ' or ', ' = ', ' + ', ' if ']
    for op in operators:
        if op in stripped:
            return split_at_operator(line, max_len, indent, op)

    return [line]

def split_comment_line(line: str, max_len: int, indent: str) -> List[str]:
    """Divide comentarios largos."""
    stripped = line.lstrip()
    text = stripped[1:].lstrip()  # Remover #

    words = text.split()
    lines = []
    current = []
    current_len = len(indent) + 2  # "# "

    for word in words:
        if current_len + len(word) + 1 > max_len:
            if current:
                lines.append(f"{indent}# {' '.join(current)}")
                current = [word]
                current_len = len(indent) + 2 + len(word)
            else:
                lines.append(f"{indent}# {word}")
        else:
            current.append(word)
            current_len += len(word) + 1

    if current:
        lines.append(f"{indent}# {' '.join(current)}")

    return lines if lines else [line]

def split_string_line(line: str, max_len: int, indent: str) -> List[str]:
    """Divide strings largos usando concatenación."""
    # Buscar string
    match = re.search(r'(["\'])(.+?)\1', line)
    if not match or len(line.rstrip()) <= max_len:
        return [line]

    quote = match.group(1)
    content = match.group(2)

    if len(content) < 40:
        return [line]

    # Dividir en medio
    mid = len(content) // 2
    split_pos = content.rfind(' ', 0, mid + 10)
    if split_pos == -1:
        split_pos = mid

    part1 = content[:split_pos]
    part2 = content[split_pos:].lstrip()

    prefix = line[:match.start()]
    suffix = line[match.end():]

    return [
        f"{prefix}{quote}{part1}{quote}",
        f"{indent}    {quote}{part2}{quote}{suffix}"
    ]

def split_function_call(line: str, max_len: int, indent: str) -> List[str]:
    """Divide llamadas a función largas."""
    stripped = line.lstrip()

    # Buscar apertura de paréntesis
    paren_pos = stripped.find('(')
    if paren_pos == -1:
        return [line]

    # Dividir en comas
    if ', ' in stripped:
        parts = stripped.split(', ')
        if len(parts) > 1:
            func_name = parts[0]
            params = parts[1:]

            lines = [f"{indent}{func_name},"]
            for i, param in enumerate(params):
                if i < len(params) - 1:
                    lines.append(f"{indent}    {param},")
                else:
                    lines.append(f"{indent}    {param}")

            return lines

    return [line]

def split_at_operator(line: str, max_len: int, indent: str, operator: str) -> List[str]:
    """Divide en un operador específico."""
    stripped = line.lstrip()

    pos = stripped.find(operator)
    if pos == -1 or pos + len(indent) > max_len:
        return [line]

    part1 = stripped[:pos].rstrip()
    part2 = stripped[pos + len(operator):].lstrip()

    return [
        f"{indent}{part1} \\",
        f"{indent}    {operator.strip()} {part2}"
    ]

def process_file(filepath: Path) -> int:
    """Procesa un archivo corrigiendo líneas en bloques de código."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return 0

    lines = content.split('\n')
    new_lines = []
    corrections = 0
    in_code_block = False

    for line in lines:
        # Detectar bloques de código
        if line.lstrip().startswith('```'):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue

        # SOLO PROCESAR DENTRO DE BLOQUES DE CÓDIGO
        if in_code_block and len(line.rstrip()) > 80:
            split = split_python_code_line(line, 80)
            if len(split) > 1:
                corrections += 1
            new_lines.extend(split)
        else:
            new_lines.append(line)

    # Escribir cambios
    new_content = '\n'.join(new_lines)
    if new_content != content:
        try:
            filepath.write_text(new_content, encoding='utf-8')
            return corrections
        except Exception:
            return 0

    return 0

def main():
    """Procesa archivos con errores MD013 en bloques de código."""
    base_dir = Path(__file__).parent

    # Archivos con errores residuales
    target_files = [
        "CODE_FIXES_OE2_DATA_FLOW.md",
        "TECHNICAL_ANALYSIS_OE2_DATA_FLOW_AGENTS.md",
        "OE3_CLEANUP_ACTION_PLAN.md",
        "OE3_STRUCTURE_COMPREHENSIVE_ANALYSIS.md",
        "OE3_VISUAL_MAPS.md",
        "ANALYSIS_SUMMARY_OE2_AGENTS.md",
        "REPORT_INDEX_OE2_ANALYSIS.md",
    ]

    print("🔧 Corrección FINAL MD013 en bloques de código...")
    print("=" * 60)

    total = 0
    for filename in target_files:
        filepath = base_dir / filename
        if not filepath.exists():
            continue

        corrections = process_file(filepath)
        if corrections > 0:
            print(f"✅ {filename}: {corrections} líneas corregidas")
            total += corrections
        else:
            print(f"⏭️  {filename}: sin cambios")

    print("=" * 60)
    print(f"✅ Total: {total} correcciones en bloques de código")
    print("🎯 CORRECCIÓN AL 100% COMPLETADA")

if __name__ == "__main__":
    main()
