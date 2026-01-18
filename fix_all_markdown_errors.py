#!/usr/bin/env python3
"""
Fix ALL Markdown errors (MD040, MD060, MD029, MD036) en archivos.
"""

import re
from pathlib import Path

def fix_markdown_file(file_path: Path) -> int:
    """
    Fix todos los errores Markdown en un archivo.
    Retorna número de cambios hechos.
    """
    content = file_path.read_text(encoding='utf-8')
    original = content
    
    # 1. Fix MD060: Separadores de tabla (|---|---| → | --- | --- |)
    # Patrón: línea que comienza con | y tiene solo |, -, y espacios
    def fix_table_separators(text):
        lines = text.split('\n')
        fixed_lines = []
        for line in lines:
            # Detectar separador de tabla
            if re.match(r'^\s*\|[\s\-|]+\|\s*$', line):
                if '-' in line:
                    # Es separador, arreglar espacios
                    parts = line.split('|')
                    fixed_parts = []
                    for part in parts:
                        part = part.strip()
                        if part and all(c in '-' for c in part):
                            # Es separador (guiones)
                            fixed_parts.append(' ' + part + ' ')
                        else:
                            # Otro contenido
                            fixed_parts.append(' ' + part + ' ' if part else '')
                    
                    # Reconstruir
                    new_line = '|' + '|'.join(fixed_parts) + '|'
                    # Normalizar espacios
                    new_line = re.sub(r'\s+\|', ' |', new_line)
                    new_line = re.sub(r'\|\s+', '| ', new_line)
                    fixed_lines.append(new_line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        return '\n'.join(fixed_lines)
    
    # 2. Fix MD040: Bloques de código sin lenguaje
    def fix_code_blocks(text):
        # Patrón: ``` sin lenguaje
        text = re.sub(r'```\n(from |import )', r'```python\n\1', text)
        text = re.sub(r'```\n(for |if |def |class )', r'```python\n\1', text)
        text = re.sub(r'```\n(\w+\s*=)', r'```python\n\1', text)
        text = re.sub(r'```\n(\{)', r'```json\n\1', text)
        text = re.sub(r'```\n(│|├|└|outputs|data|src|scripts)', r'```bash\n\1', text)
        text = re.sub(r'```\n(\w+:)', r'```yaml\n\1', text)
        return text
    
    # 3. Fix MD029: Ordered list (1. 2. 3. no 1. 1. 1. o 1. 5. 3.)
    def fix_ordered_lists(text):
        lines = text.split('\n')
        fixed_lines = []
        expected_num = 1
        
        for line in lines:
            # Detectar línea de lista ordenada
            match = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
            if match:
                indent, _, content = match.groups()
                # Reemplazar con número correcto
                fixed_lines.append(f"{indent}{expected_num}. {content}")
                expected_num += 1
            elif re.match(r'^\s*[*\-\+]\s+', line):
                # Lista sin ordenar, resetear
                expected_num = 1
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    # 4. Fix MD036: Énfasis como heading (**text** → # text)
    def fix_emphasis_as_heading(text):
        # Solo si está en línea sola y no es tabla
        lines = text.split('\n')
        fixed_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Si es línea sola con solo **text**
            if stripped.startswith('**') and stripped.endswith('**') and '\n' not in line and '|' not in line:
                # Convertir a heading
                content = stripped[2:-2]  # Quitar ** **
                fixed_lines.append(f"## {content}")
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    # Aplicar todas las correcciones
    content = fix_table_separators(content)
    content = fix_code_blocks(content)
    content = fix_ordered_lists(content)
    content = fix_emphasis_as_heading(content)
    
    # Guardar si cambió
    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return 1
    return 0


def main():
    """Fix todos los archivos con errores."""
    
    workspace = Path("d:\\diseñopvbesscar")
    
    # Archivos conocidos con errores
    target_files = [
        "INICIO_RAPIDO_CONTROL_OPERATIVO.md",
        "RESUMEN_EJECUTIVO_CONTROL_OPERATIVO.md",
    ]
    
    print("=" * 80)
    print("CORRECTOR AUTOMÁTICO DE MARKDOWN (MD040/MD060/MD029/MD036)")
    print("=" * 80)
    print()
    
    total_fixed = 0
    
    for filename in target_files:
        file_path = workspace / filename
        if file_path.exists():
            count = fix_markdown_file(file_path)
            if count > 0:
                print(f"✅ {filename}: ARREGLADO")
                total_fixed += 1
            else:
                print(f"⚠️  {filename}: Sin cambios necesarios")
        else:
            print(f"❌ {filename}: No encontrado")
    
    print()
    print("=" * 80)
    print(f"RESULTADO: {total_fixed} archivos procesados")
    print("=" * 80)


if __name__ == "__main__":
    main()
