#!/usr/bin/env python3
"""
Script inteligente para corregir 447 errores markdown sin dañar contenido
Estrategia: Solo correcciones mínimas y seguras
"""

import re

def fix_markdown_issues(filepath):
    """Corrige errores markdown específicos"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 1. MD036: Énfasis usado en lugar de heading (línea 5 específicamente)
    # **Tesis para optar...** → ### Tesis para optar...
    content = re.sub(
        r'^\*\*Tesis para optar el Título Profesional de Ingeniero\*\*$',
        '### Tesis para optar el Título Profesional de Ingeniero',
        content,
        flags=re.MULTILINE
    )
    
    # 2. MD040: Agregar lenguaje a bloques de código vacíos o sin especificar
    # Encuentra ```\n``` seguido de contenido no markdown
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == '```' and i + 1 < len(lines):
            # Mirar siguiente línea para determinar lenguaje
            next_line = lines[i + 1]
            
            # Si la siguiente línea es texto/código (no markdown)
            if next_line.strip() and not next_line.startswith('#') and not next_line.startswith('|'):
                # Es probablemente python, bash, json, etc.
                # Por defecto usa 'text' para ser seguro
                if any(keyword in next_line for keyword in ['import ', 'def ', 'class ', 'print', '{']):
                    fixed_lines.append('```python')
                elif any(keyword in next_line for keyword in ['$', '#!/', 'bash']):
                    fixed_lines.append('```bash')
                elif '{' in next_line and '}' in next_line:
                    fixed_lines.append('```json')
                else:
                    fixed_lines.append('```text')
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
        i += 1
    
    content = '\n'.join(fixed_lines)
    
    # 3. MD060: Tabla column spacing - agregar espacios alrededor de |
    # Pero ser cuidadoso para no romper tablas existentes
    lines = content.split('\n')
    fixed_lines = []
    for line in lines:
        # Detecta filas de tabla (contienen múltiples |)
        if line.count('|') >= 2:
            # Verifica si ya tiene espacios correctamente
            if not re.search(r' \| ', line):
                # Agrega espacios alrededor de | si faltan
                # Pero conserva estructura
                line = re.sub(r'\|(?! )', '| ', line)  # Falta espacio después
                line = re.sub(r'(?<! )\|', ' |', line)  # Falta espacio antes
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # 4. MD051: Fragmentos de enlace inválidos - simplemente remover los problemas
    # Enlaces como [text](#52-comparación-con-literatura)
    # Convertir a minúsculas y caracteres válidos
    def fix_fragment(match):
        link_text = match.group(1)
        fragment = match.group(2)
        
        # Normalizar fragment: lowercase, no acentos, espacios a guiones
        fragment_norm = fragment.lower()
        acentos = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n'}
        for acentuado, normal in acentos.items():
            fragment_norm = fragment_norm.replace(acentuado, normal)
        
        fragment_norm = re.sub(r'[^a-z0-9\s\-]', '', fragment_norm)
        fragment_norm = fragment_norm.replace(' ', '-')
        fragment_norm = re.sub(r'-+', '-', fragment_norm)
        fragment_norm = fragment_norm.strip('-')
        
        return f'[{link_text}](#{fragment_norm})'
    
    content = re.sub(r'\[([^\]]+)\]\(#([^\)]+)\)', fix_fragment, content)
    
    # 5. Guardar
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


if __name__ == '__main__':
    filepath = 'd:\\diseñopvbesscar\\docs\\DOCUMENTACION_COMPLETA.md'
    print("🔍 Analizando y corrigiendo markdown...")
    
    if fix_markdown_issues(filepath):
        print("✅ Correcciones aplicadas exitosamente")
    else:
        print("ℹ️ No se realizaron cambios")
