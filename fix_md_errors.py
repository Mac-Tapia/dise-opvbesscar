#!/usr/bin/env python3
"""Script para corregir MD040/MD060 errors en archivos markdown"""

from pathlib import Path

files_to_fix = [
    'RESUMEN_DOCKER.md',
    'COMIENZA_AQUI.md',
    'DOCKER_INDEX.md'
]

for filename in files_to_fix:
    filepath = Path(filename)
    if not filepath.exists():
        print(f"⊘ {filename} no encontrado")
        continue
    
    content = filepath.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Fix 1: Agregar lenguaje a fenced code blocks sin lenguaje
    i = 0
    while i < len(lines):
        if lines[i].strip() == '```':
            # Mirar próximas líneas para determinar contenido
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Detectar tipo de contenido
                if next_line.startswith('#') or 'import' in next_line or 'def ' in next_line:
                    lines[i] = '```python'
                elif next_line.startswith('✓') or next_line.startswith('✅') or '├' in next_line or '│' in next_line or '┌' in next_line:
                    lines[i] = '```text'
                elif next_line.startswith('docker') or 'docker' in next_line or next_line.startswith('./'):
                    lines[i] = '```bash'
                elif next_line.startswith('Set-') or next_line.startswith('.\\'):
                    lines[i] = '```powershell'
                elif next_line.startswith('oe2:') or next_line.startswith('oe3:') or ':' in next_line:
                    lines[i] = '```yaml'
                else:
                    lines[i] = '```bash'  # default
        i += 1
    
    # Fix 2: Corregir table formatting - agregar espacios en separadores
    i = 0
    while i < len(lines):
        line = lines[i]
        # Si es una línea que solo contiene |, -, y espacios
        if '|' in line and '-' in line:
            parts = line.split('|')
            # Verificar si es principalmente separadores (todas las partes son vacías o solo dashes)
            is_separator = all(
                p.strip() == '' or all(c in '-= ' for c in p.strip()) 
                for p in parts
            )
            if is_separator:
                # Es una separadora, arreglarlo
                new_parts = []
                for part in parts:
                    stripped = part.strip()
                    if stripped and all(c in '-=' for c in stripped):
                        new_parts.append(f' {stripped} ')
                    elif stripped:
                        new_parts.append(f' {stripped} ')
                    else:
                        new_parts.append('')
                lines[i] = '|' + '|'.join(new_parts) + '|'
        i += 1
    
    # Guardar cambios
    new_content = '\n'.join(lines)
    if new_content != content:
        filepath.write_text(new_content, encoding='utf-8')
        print(f"✅ {filename} corregido")
    else:
        print(f"⊘ {filename} sin cambios")

print("\n✅ Proceso completado")
