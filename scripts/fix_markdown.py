#!/usr/bin/env python3
"""
Script para corregir errores markdown comunes en DOCUMENTACION_COMPLETA.md
Corrige:
- MD036: Énfasis usado en lugar de heading
- MD040: Código sin lenguaje especificado
- MD051: Fragmentos de enlace inválidos
- MD024/MD025: Encabezados duplicados
- MD060: Espacios en tablas
"""

import re
import os

def fix_emphasis_as_heading(content):
    """Convierte énfasis a headings apropiados"""
    # Línea 5: **Tesis para optar...** → ### Tesis para optar...
    content = re.sub(
        r'^\*\*Tesis para optar el Título Profesional de Ingeniero\*\*$',
        '### Tesis para optar el Título Profesional de Ingeniero',
        content,
        flags=re.MULTILINE
    )
    return content


def fix_fenced_code_blocks(content):
    """Agrega lenguaje a bloques de código sin especificar"""
    # Encuentra bloques ``` sin lenguaje y agrega 'text'
    lines = content.split('\n')
    in_code_block = False
    new_lines = []
    
    for i, line in enumerate(lines):
        # Si es apertura de bloque sin lenguaje
        if line.strip() == '```' and (i == 0 or lines[i-1].strip() != ''):
            # Mira adelante para determinar si es código o no
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip() and not next_line.startswith('#'):
                    new_lines.append('```text')
                else:
                    new_lines.append('```')
            else:
                new_lines.append('```')
        else:
            new_lines.append(line)
    
    return '\n'.join(new_lines)


def fix_table_spacing(content):
    """Agrega espacios en tablas markdown (MD060)"""
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # Detecta líneas de tabla (contienen |)
        if '|' in line and not line.strip().startswith('|'):
            # Asegura espacios después de | al inicio y antes de | al final
            line = line.replace('|', ' | ')
            # Limpia espacios múltiples
            line = re.sub(r'\s+\|', ' |', line)
            line = re.sub(r'\|\s+', '| ', line)
            # Limpia bordes
            line = re.sub(r'^\s+\|', '| ', line)
            line = re.sub(r'\|\s+$', ' |', line)
        
        new_lines.append(line)
    
    return '\n'.join(new_lines)


def fix_link_fragments(content):
    """Corrige fragmentos de enlace inválidos (MD051)"""
    # Reemplaza caracteres especiales en fragmentos por guiones
    def escape_fragment(match):
        fragment = match.group(1)
        # Convierte a lowercase, reemplaza espacios por guiones, elimina acentos
        fragment_clean = fragment.lower()
        fragment_clean = fragment_clean.replace(' ', '-')
        fragment_clean = fragment_clean.replace('á', 'a')
        fragment_clean = fragment_clean.replace('é', 'e')
        fragment_clean = fragment_clean.replace('í', 'i')
        fragment_clean = fragment_clean.replace('ó', 'o')
        fragment_clean = fragment_clean.replace('ú', 'u')
        fragment_clean = re.sub(r'[^a-z0-9\-]', '', fragment_clean)
        return f'#{fragment_clean}'
    
    content = re.sub(r'#([^)]+)\)', escape_fragment, content)
    return content


def remove_duplicate_headings(content):
    """Elimina encabezados h1 duplicados, mantiene solo el primero"""
    lines = content.split('\n')
    h1_count = 0
    new_lines = []
    
    for i, line in enumerate(lines):
        if line.startswith('# ') and not line.startswith('## '):
            h1_count += 1
            if h1_count == 1:
                new_lines.append(line)
            elif h1_count == 2:
                # Segunda aparición de h1 → convertir a h2
                new_lines.append(line.replace('# ', '## ', 1))
            else:
                # Otras apariciones → convertir a h3
                new_lines.append(line.replace('# ', '### ', 1))
        else:
            new_lines.append(line)
    
    return '\n'.join(new_lines)


def main():
    filepath = 'd:\\diseñopvbesscar\\docs\\DOCUMENTACION_COMPLETA.md'
    
    print("🔧 Leyendo archivo...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_size = len(content)
    
    print("✓ Corrigiendo énfasis como heading...")
    content = fix_emphasis_as_heading(content)
    
    print("✓ Corrigiendo bloques de código sin lenguaje...")
    content = fix_fenced_code_blocks(content)
    
    print("✓ Corrigiendo espacios en tablas...")
    content = fix_table_spacing(content)
    
    print("✓ Corrigiendo fragmentos de enlace...")
    content = fix_link_fragments(content)
    
    print("✓ Eliminando encabezados duplicados...")
    content = remove_duplicate_headings(content)
    
    print("💾 Guardando archivo...")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    new_size = len(content)
    print(f"\n✅ Completado!")
    print(f"   Tamaño antes: {original_size:,} bytes")
    print(f"   Tamaño después: {new_size:,} bytes")


if __name__ == '__main__':
    main()
