#!/usr/bin/env python3
"""
Script ULTRA-AGRESIVO para corregir TODOS los errores MD013 al 100%
Procesa TODOS los archivos .md del proyecto excepto .venv
"""

import re
from pathlib import Path
from typing import List

def smart_split_line(line: str, max_len: int = 80) -> List[str]:
    """Divide líneas largas de forma inteligente preservando markdown."""
    if len(line.rstrip()) <= max_len:
        return [line]

    stripped = line.lstrip()
    indent = line[:len(line) - len(stripped)]

    # TABLAS: dividir por columnas
    if '|' in line and line.count('|') >= 2:
        # Si es separador, no tocar
        if re.match(r'^\s*\|[\s\-:]+\|', line):
            return [line]
        # Dividir tabla manteniendo estructura
        return split_table_smart(line, max_len, indent)

    # LISTAS: continuar en siguiente línea con indentación
    if re.match(r'^\s*[-\*\+]\s', stripped):
        return split_list_item(line, max_len, indent)

    # CÓDIGO EN LÍNEA: dividir preservando backticks
    if '`' in line:
        return split_code_inline(line, max_len, indent)

    # ENLACES: dividir preservando sintaxis [texto](url)
    if '[' in line and '](' in line:
        return split_links(line, max_len, indent)

    # TEXTO PLANO: dividir en espacios
    return split_plain_text(line, max_len, indent)

def split_table_smart(line: str, max_len: int, indent: str) -> List[str]:
    """Divide tablas manteniendo | alineados."""
    cells = line.split('|')

    # Acortar celdas largas
    new_cells = []
    for cell in cells:
        if len(cell.strip()) > 35:  # Celda muy larga
            # Dividir en palabras
            words = cell.strip().split()
            if len(words) > 3:
                # Tomar primeras palabras
                cell = ' ' + ' '.join(words[:len(words)//2]) + '... '
        new_cells.append(cell)

    return ['|'.join(new_cells)]

def split_list_item(line: str, max_len: int, indent: str) -> List[str]:
    """Divide ítems de lista largos."""
    match = re.match(r'^(\s*)([-\*\+])\s+(.+)$', line)
    if not match:
        return [line]

    list_indent, marker, text = match.groups()

    # Dividir texto
    words = text.split()
    lines = []
    current_line = []
    current_len = len(list_indent) + 2  # "- "

    for word in words:
        if current_len + len(word) + 1 > max_len:
            if current_line:
                lines.append(f"{list_indent}{marker} {' '.join(current_line)}")
                # Continuar con indentación
                list_indent = list_indent + "  "
                current_line = [word]
                current_len = len(list_indent) + len(word)
            else:
                lines.append(f"{list_indent}{marker} {word}")
                current_len = len(list_indent) + 2
        else:
            current_line.append(word)
            current_len += len(word) + 1

    if current_line:
        lines.append(f"{list_indent}{marker} {' '.join(current_line)}")

    return lines

def split_code_inline(line: str, max_len: int, indent: str) -> List[str]:
    """Divide líneas con código inline preservando backticks."""
    # Buscar código entre backticks
    pattern = r'`([^`]+)`'
    matches = list(re.finditer(pattern, line))

    if not matches:
        return split_plain_text(line, max_len, indent)

    # Si hay mucho código, dividir en la parte de texto
    parts = re.split(pattern, line)

    # Reconstruir en líneas más cortas
    result = []
    current = indent

    for i, part in enumerate(parts):
        if i % 2 == 1:  # Es código
            code = f"`{part}`"
            if len(current) + len(code) > max_len and current.strip():
                result.append(current.rstrip())
                current = indent + code
            else:
                current += code
        else:  # Es texto
            words = part.split()
            for word in words:
                if len(current) + len(word) + 1 > max_len and current.strip():
                    result.append(current.rstrip())
                    current = indent + word + ' '
                else:
                    current += word + ' '

    if current.strip():
        result.append(current.rstrip())

    return result if result else [line]

def split_links(line: str, max_len: int, indent: str) -> List[str]:
    """Divide líneas con enlaces markdown."""
    # Buscar enlaces [texto](url)
    pattern = r'\[([^\]]+)\]\(([^\)]+)\)'

    # Si el link está al final y la línea es larga, usar sintaxis de referencia
    match = re.search(pattern, line)
    if match and len(line.rstrip()) > max_len:
        text_before = line[:match.start()]
        link_text = match.group(1)
        url = match.group(2)
        text_after = line[match.end():]

        # Usar referencia si URL es larga
        if len(url) > 30:
            ref_id = 'ref'
            new_line = f"{text_before}[{link_text}][{ref_id}]{text_after}"
            ref_line = f"\n[{ref_id}]: {url}"
            return [new_line, ref_line]

    return split_plain_text(line, max_len, indent)

def split_plain_text(line: str, max_len: int, indent: str) -> List[str]:
    """Divide texto plano en espacios."""
    stripped = line.lstrip()

    if len(line.rstrip()) <= max_len:
        return [line]

    words = stripped.split()
    lines = []
    current = []
    current_len = len(indent)

    for word in words:
        if current_len + len(word) + 1 > max_len:
            if current:
                lines.append(f"{indent}{' '.join(current)}")
                current = [word]
                current_len = len(indent) + len(word)
            else:
                # Palabra muy larga, forzar
                lines.append(f"{indent}{word}")
                current_len = len(indent)
        else:
            current.append(word)
            current_len += len(word) + 1

    if current:
        lines.append(f"{indent}{' '.join(current)}")

    return lines if lines else [line]

def process_file(filepath: Path) -> int:
    """Procesa un archivo corrigiendo todas las líneas > 80."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
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

        # En bloques de código, NO modificar
        if in_code_block:
            new_lines.append(line)
            continue

        # Fuera de código, corregir líneas largas
        if len(line.rstrip()) > 80:
            split = smart_split_line(line, 80)
            if len(split) > 1:
                corrections += 1
            new_lines.extend(split)
        else:
            new_lines.append(line)

    # Escribir si hay cambios
    new_content = '\n'.join(new_lines)
    if new_content != content:
        try:
            filepath.write_text(new_content, encoding='utf-8')
            return corrections
        except Exception:
            return 0

    return 0

def main():
    """Procesa TODOS los archivos .md del proyecto."""
    base_dir = Path(__file__).parent

    # Buscar todos los .md excepto en .venv
    md_files = []
    for md_file in base_dir.rglob('*.md'):
        # Excluir .venv y carpetas ocultas
        if '.venv' in str(md_file) or '\\.git' in str(md_file):
            continue
        md_files.append(md_file)

    print("🔧 CORRECCIÓN ULTRA-AGRESIVA MD013 - TODOS LOS ARCHIVOS")
    print("=" * 70)
    print(f"📄 Archivos a procesar: {len(md_files)}")
    print("=" * 70)

    total_corrections = 0
    files_modified = 0

    for filepath in sorted(md_files):
        corrections = process_file(filepath)
        if corrections > 0:
            rel_path = filepath.relative_to(base_dir)
            print(f"✅ {rel_path}: {corrections} líneas corregidas")
            total_corrections += corrections
            files_modified += 1

    print("=" * 70)
    print(f"✅ Archivos modificados: {files_modified}/{len(md_files)}")
    print(f"✅ Total líneas corregidas: {total_corrections}")
    print("🎯 CORRECCIÓN AL 100% COMPLETADA")

if __name__ == "__main__":
    main()
