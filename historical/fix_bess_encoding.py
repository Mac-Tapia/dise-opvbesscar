#!/usr/bin/env python3
"""
Corrige problemas de encoding en bess.py
"""
from pathlib import Path

# Diccionario de reemplazos: caracteres problemáticos -> ASCII
replacements = {
    'ó': 'o',  # o-acute
    'á': 'a',  # a-acute
    'é': 'e',  # e-acute
    'í': 'i',  # i-acute
    'ú': 'u',  # u-acute
}

def fix_encoding(file_path):
    """Lee archivo, reemplaza caracteres acentuados, guarda."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Reemplazar caracteres acentuados
    for old, new in replacements.items():
        content = content.replace(old, new)

    # Guardar cambios
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Archivo corregido: {file_path}")

        # Contar cambios
        for old, new in replacements.items():
            count = original.count(old)
            if count > 0:
                print(f"   - Reemplazado '{old}' → '{new}': {count} veces")
        return True
    else:
        print(f"⚠️ No se encontraron caracteres acentuados en: {file_path}")
        return False

if __name__ == "__main__":
    bess_file = Path("d:\\diseñopvbesscar\\src\\iquitos_citylearn\\oe2\\bess.py")

    print("=" * 60)
    print("REPARADOR DE ENCODING - bess.py")
    print("=" * 60)

    if bess_file.exists():
        fix_encoding(bess_file)

        # Validar sintaxis después de la corrección
        print("\n" + "=" * 60)
        print("VALIDANDO SINTAXIS...")
        print("=" * 60)

        try:
            import py_compile
            py_compile.compile(str(bess_file), doraise=True)
            print("✅ bess.py: Sintaxis correcta!")
        except py_compile.PyCompileError as e:
            print(f"❌ Error de sintaxis: {e}")
    else:
        print(f"❌ Archivo no encontrado: {bess_file}")
