#!/usr/bin/env python3
"""
LIMPIAR CUMPLIMIENTO_ESTRICTO.md
Elimina todas las estructuras problemáticas
"""

import re
from pathlib import Path

def limpiar():
    """Limpia el archivo CUMPLIMIENTO_ESTRICTO.md"""
    ruta = Path('CUMPLIMIENTO_ESTRICTO.md')
    with open(ruta, encoding='utf-8') as f:
        content = f.read()
    
    # 1. Remover TODOS los ``` que no tienen contenido real
    # Patrón: ``` [whitespace] ``` o ```` seguido de ``` luego ````
    
    # Remove 4 backticks followed by 3 backticks
    content = re.sub(r'````\s*\n\s*```\s*\n\s*````', '', content)
    
    # Remove isolated triple backticks with whitespace
    content = re.sub(r'```\s*\n\s*\n```', '', content)
    content = re.sub(r'```\s*\n\s*```', '', content)
    
    # 2. Remover "```markdown" incompletos (que cierra abruptamente)
    content = re.sub(r'```markdown\s*\n\s*\n```', '', content)
    content = re.sub(r'```markdown\s*$', '', content, flags=re.MULTILINE)
    
    # 3. Remover espacios finales (MD009)
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)
    
    # 4. Asegurar espacios alrededor de headings
    content = re.sub(r'([^\n])\n(###)', r'\1\n\n\2', content)
    content = re.sub(r'(###[^\n]+)\n([^\n])', r'\1\n\n\2', content)
    
    # 5. Remover puntuación final en headings (MD026)
    content = re.sub(r'^(#{1,6}\s+[^:\n]+):\s*$', r'\1', content, flags=re.MULTILINE)
    
    # 6. Limiar espacios excesivos
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ CUMPLIMIENTO_ESTRICTO.md limpiado")

if __name__ == "__main__":
    limpiar()
