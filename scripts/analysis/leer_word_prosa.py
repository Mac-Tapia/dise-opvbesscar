"""Lee y muestra el texto completo del Word v8 para revisión de prosa."""
from __future__ import annotations
from docx import Document

doc = Document("outputs/docx/INFORME_OE3_SELECCION_AGENTE_RL_v8.docx")

print(f"Total párrafos: {len(doc.paragraphs)}, tablas: {len(doc.tables)}\n")

for i, p in enumerate(doc.paragraphs):
    txt = p.text.strip()
    if not txt:
        continue
    sty = p.style.name
    if sty.startswith("Heading"):
        print(f"\n{'='*60}")
        print(f"[{i}] {sty}: {txt}")
        print(f"{'='*60}")
    else:
        # Solo mostrar los primeros 200 chars de cada párrafo
        print(f"  [{i}] {txt[:200]}")
