#!/usr/bin/env python3
"""
Extrae contenido del documento Word y lo presenta en párrafos listos para pegar
"""
from docx import Document
from pathlib import Path

def extract_paragraphs_for_copy():
    """Extrae todos los párrafos del documento y los organiza para copiar/pegar"""
    
    doc = Document('reports/ARQUITECTURA_PVBESSCAR_TESIS.docx')
    
    # Crear archivo de texto con contenido limpio
    output = []
    current_section = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        
        if not text:
            continue
        
        # Determinar nivel de encabezado
        if para.style.name == 'Heading 1':
            output.append(f"\n{'='*80}")
            output.append(f"{text}")
            output.append(f"{'='*80}\n")
            current_section = text
        elif para.style.name == 'Heading 2':
            output.append(f"\n{'-'*80}")
            output.append(f"{text}")
            output.append(f"{'-'*80}\n")
        elif para.style.name == 'Heading 3':
            output.append(f"\n▪ {text}\n")
        elif para.style.name in ['Heading 4', 'Heading 5']:
            output.append(f"  • {text}\n")
        elif para.style.name in ['List Bullet', 'List Number']:
            output.append(f"  • {text}")
        else:
            # Párrafo normal
            output.append(text)
    
    # Guardar en archivo
    content = "\n".join(output)
    with open('reports/ARQUITECTURA_PVBESSCAR_PARAGRAFOS.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    
    return content

if __name__ == "__main__":
    content = extract_paragraphs_for_copy()
    print("✓ Contenido extraído y guardado en: reports/ARQUITECTURA_PVBESSCAR_PARAGRAFOS.txt")
    print(f"✓ Total de caracteres: {len(content):,}")
    print("\nPreview (primeros 1500 caracteres):\n")
    print(content[:1500])
    print("\n...")
