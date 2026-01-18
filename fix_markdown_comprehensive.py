#!/usr/bin/env python3
"""
Script para reparar todos los errores MD040 y MD060 en archivos Markdown.
MD040: Fenced code blocks sin language
MD060: Table column style (espacios faltantes alrededor de pipes)
"""

import re
import sys
from pathlib import Path

def fix_md040_code_blocks(content: str) -> str:
    """
    Reparar MD040: Agregar 'python' como idioma a bloques de código sin idioma.
    Detecta ``` seguido inmediatamente por nombre de variable/código.
    """
    # Patrón 1: ``` seguido por una línea que comienza con "from " o "import "
    content = re.sub(
        r'```\n(from |import )',
        r'```python\n\1',
        content
    )
    
    # Patrón 2: ``` seguido por una línea que comienza con "for ", "if ", "def ", etc.
    content = re.sub(
        r'```\n(for |if |def |class |with |try |except |while )',
        r'```python\n\1',
        content
    )
    
    # Patrón 3: ``` seguido por una línea que comienza con número o path (estructura de directorio)
    content = re.sub(
        r'```\n(│|├|└|outputs|data|src|scripts)',
        r'```bash\n\1',
        content
    )
    
    # Patrón 4: ``` seguido por variable assignment (x = )
    content = re.sub(
        r'```\n(\w+\s*=)',
        r'```python\n\1',
        content
    )
    
    # Patrón 5: ``` seguido por JSON-like structure
    content = re.sub(
        r'```\n(\{)',
        r'```json\n\1',
        content
    )
    
    # Patrón 6: ``` seguido por YAML-like structure
    content = re.sub(
        r'```\n(\w+:)',
        r'```yaml\n\1',
        content
    )
    
    # Patrón 7: Standalone ``` (vacío) - asumir python por defecto en contexto de RL
    content = re.sub(
        r'```\n\n```',
        r'```python\n\n```',
        content
    )
    
    return content


def fix_md060_table_separators(content: str) -> str:
    """
    Reparar MD060: Arreglar separadores de tabla (| --- | --- |)
    Patrón incorrecto: |---|---|---|
    Patrón correcto:   | --- | --- | --- |
    """
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Detectar si es una línea de separador de tabla
        if re.match(r'^\s*\|[\s\-|]*\|', line):
            # Verificar si contiene guiones (separador)
            if '-' in line:
                # Dividir por pipes y reconstruir con espacios
                parts = line.split('|')
                
                # Filtrar partes vacías y arreglar espacios
                fixed_parts = []
                for _, part in enumerate(parts):
                    part = part.strip()
                    
                    # Para separadores (partes que solo contienen guiones)
                    if part and all(c in '- ' for c in part):
                        # Convertir a formato estándar: 3+ guiones
                        dashes = part.count('-')
                        fixed_parts.append(' ' + '-' * max(3, dashes) + ' ')
                    elif part:  # Otros contenidos (headers)
                        fixed_parts.append(' ' + part + ' ')
                    else:
                        fixed_parts.append('')
                
                # Reconstruir línea con pipes y espacios
                new_line = '|' + '|'.join(fixed_parts) + '|'
                # Limpiar múltiples espacios
                new_line = re.sub(r'\s+\|', ' |', new_line)
                new_line = re.sub(r'\|\s+', '| ', new_line)
                fixed_lines.append(new_line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def process_file(file_path: Path) -> tuple[bool, str]:
    """
    Procesar un archivo y retornar (éxito, mensaje).
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Aplicar ambas correcciones
        content = fix_md040_code_blocks(content)
        content = fix_md060_table_separators(content)
        
        # Guardar
        file_path.write_text(content, encoding='utf-8')
        return True, f"✅ {file_path.name}: Reparado"
    except Exception as e:
        return False, f"❌ {file_path.name}: {str(e)}"


def main():
    """Procesar todos los archivos .md con errores."""
    
    workspace = Path("d:\\diseñopvbesscar")
    
    # Archivos conocidos con errores (según get_errors)
    target_files = [
        "PLAN_CONTROL_OPERATIVO.md",
        "GUIA_IMPLEMENTACION_CONTROL_OPERATIVO.md",
        "RESUMEN_MAESTRO_CAMBIOS.md",
    ]
    
    print("=" * 60)
    print("REPARADOR DE MARKDOWN (MD040 + MD060)")
    print("=" * 60)
    
    results = []
    for filename in target_files:
        file_path = workspace / filename
        if file_path.exists():
            success, msg = process_file(file_path)
            results.append((success, msg))
            print(msg)
        else:
            print(f"⚠️  {filename}: No encontrado en {workspace}")
    
    print("\n" + "=" * 60)
    successes = sum(1 for s, _ in results if s)
    print(f"RESULTADO: {successes}/{len(target_files)} archivos reparados")
    print("=" * 60)
    
    return 0 if all(s for s, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
