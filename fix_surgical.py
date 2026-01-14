#!/usr/bin/env python3
"""
Surgical final fixes for specific remaining issues
"""

from pathlib import Path
import re


def fix_tabla_contenidos_surgical(filepath):
    """Fix specific MD055, MD009, MD005 in TABLA_CONTENIDOS.md"""
    content = filepath.read_text(encoding='utf-8')
    
    # Fix line 171: single space indent + trailing space
    content = content.replace(' - Paso | Input | Proceso | Output', '- Paso | Input | Proceso | Output')
    content = content.replace(' VERIFICACION_FINAL_ENTREGA | Verificación | 2,000 | 8 | 8 | - | **TOTALES**: 39,300+ palabras, 85+ secciones, 56+ tablas, 37+ ejemplos código',
                             '| VERIFICACION_FINAL_ENTREGA | Verificación | 2,000 | 8 | 8 | - |\n\n**TOTALES**: 39,300+ palabras, 85+ secciones, 56+ tablas, 37+ ejemplos código')
    
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Surgical fix: {filepath.name}")


def fix_verificacion_entrenamiento_surgical(filepath):
    """Fix specific MD055, MD022, MD032 in VERIFICACION_ENTRENAMIENTO_SAC.md"""
    content = filepath.read_text(encoding='utf-8')
    
    # Fix heading spacing issues (MD022)
    content = re.sub(r'(\d+\.\*\*[^*]+\*\*)-(\*\*[^*]+\*\*)', r'\1\n\n- \2', content)
    
    # Fix list spacing (MD032)
    content = re.sub(r'(\*\*[^\n]*\*\*)\n(- )', r'\1\n\n\2', content)
    
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Surgical fix: {filepath.name}")


def fix_analisis_visual_surgical(filepath):
    """Fix code blocks and heading spacing"""
    content = filepath.read_text(encoding='utf-8')
    
    # Fix bare ```text without proper spacing
    content = re.sub(r'(\*\*)\n(```)', r'\1\n\n\2\n', content)
    content = re.sub(r'(```text)\n', r'\1', content)
    content = re.sub(r'(```)\n(```)', r'\1', content)
    
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Surgical fix: {filepath.name}")


def fix_verificacion_completa_surgical(filepath):
    """Fix heading and list spacing in VERIFICACION_COMPLETA_RESUMEN.md"""
    content = filepath.read_text(encoding='utf-8')
    
    # Fix heading + list without spacing
    content = re.sub(r'(\*\*Respuesta: [^\n]*\*\*)\n(- )', r'\1\n\n\2', content)
    
    # Fix 3-space indentation
    content = re.sub(r'\n   -', r'\n-', content)
    
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Surgical fix: {filepath.name}")


def main():
    base = Path('d:\\diseñopvbesscar')
    
    fixes = {
        'TABLA_CONTENIDOS.md': fix_tabla_contenidos_surgical,
        'VERIFICACION_ENTRENAMIENTO_SAC.md': fix_verificacion_entrenamiento_surgical,
        'ANALISIS_VISUAL_APRENDIZAJE_SAC.md': fix_analisis_visual_surgical,
        'VERIFICACION_COMPLETA_RESUMEN.md': fix_verificacion_completa_surgical,
    }
    
    for filename, fixer in fixes.items():
        filepath = base / filename
        if filepath.exists():
            fixer(filepath)
    
    print("\n✓ Surgical fixes completed!")


if __name__ == '__main__':
    main()
