"""
Convierte diagramas Mermaid a PDF usando fpdf + renderizado
pvbesscar v7.1 - PDF Generator sin Node.js
"""

from pathlib import Path
import subprocess
import sys

def convert_mermaid_to_pdf_via_api(mmd_file: Path, pdf_file: Path):
    """
    Convierte diagrama Mermaid a PDF usando Kroki API (online)
    Kroki es un API que soporta múltiples formatos incluyendo Mermaid
    """
    
    # Leer el contenido del archivo .mmd
    with open(mmd_file, 'r', encoding='utf-8') as f:
        mermaid_code = f.read()
    
    # Intentar diferentes métodos de conversión
    
    # Método 1: Usar Kroki API (más confiable, sin dependencias)
    try:
        import requests
        import base64
        
        print(f"\n🔄 Usando Kroki API para convertir {mmd_file.name}...")
        
        # Encodificar el diagrama en Base64 para la URL
        encoded = base64.b64encode(mermaid_code.encode()).decode()
        
        # Usar Kroki para convertir a SVG primero
        kroki_url = f"https://kroki.io/mermaid/pdf"
        
        response = requests.post(kroki_url, data=mermaid_code, timeout=30)
        response.raise_for_status()
        
        with open(pdf_file, 'wb') as f:
            f.write(response.content)
        
        print(f"   ✅ PDF generado: {pdf_file}")
        return True
        
    except ImportError:
        print("   ⚠️  requests no instalado, intentando alternativa...")
    except Exception as e:
        print(f"   ⚠️  Error con Kroki: {e}")
    
    # Método 2: Usar urllib (sin dependencias externas)
    try:
        import urllib.request
        import urllib.parse
        
        print(f"\n🔄 Intentando con urllib + URL encoding...")
        
        kroki_url = "https://kroki.io/mermaid/pdf"
        
        # Preparar datos
        data = mermaid_code.encode('utf-8')
        
        # Hacer request
        req = urllib.request.Request(kroki_url, data=data, method='POST')
        req.add_header('Content-Type', 'text/plain')
        
        with urllib.request.urlopen(req, timeout=30) as response:
            pdf_content = response.read()
        
        with open(pdf_file, 'wb') as f:
            f.write(pdf_content)
        
        print(f"   ✅ PDF generado: {pdf_file}")
        return True
        
    except Exception as e:
        print(f"   ⚠️  Error con urllib: {e}")
    
    return False

def main():
    """Convierte los dos diagramas a PDF"""
    
    reports_dir = Path('reports')
    
    files_to_convert = [
        ('01_ARQUITECTURA_PROYECTO.mmd', '01_ARQUITECTURA_PROYECTO.pdf'),
        ('02_FLUJO_TRABAJO_DETALLADO.mmd', '02_FLUJO_TRABAJO_DETALLADO.pdf'),
    ]
    
    print("=" * 80)
    print("🔄 CONVERSIÓN DE DIAGRAMAS MERMAID A PDF")
    print("=" * 80)
    print("\n📌 Usando Kroki API (https://kroki.io) - sin instalaciones")
    
    success_count = 0
    
    for mmd_name, pdf_name in files_to_convert:
        mmd_file = reports_dir / mmd_name
        pdf_file = reports_dir / pdf_name
        
        if not mmd_file.exists():
            print(f"\n❌ No encontrado: {mmd_file}")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"📄 {mmd_name} → {pdf_name}")
        print(f"{'=' * 80}")
        
        if convert_mermaid_to_pdf_via_api(mmd_file, pdf_file):
            success_count += 1
            print(f"   Tamaño: {pdf_file.stat().st_size:,} bytes")
        else:
            print(f"   ❌ No se pudo convertir")
    
    print(f"\n{'=' * 80}")
    print(f"✨ Resultado: {success_count}/{len(files_to_convert)} PDFs generados")
    print("=" * 80)
    
    if success_count > 0:
        print("\n📌 Archivos PDF creados en: reports/")
        for _, pdf_name in files_to_convert:
            pdf_file = reports_dir / pdf_name
            if pdf_file.exists():
                print(f"   ✅ {pdf_name}")

if __name__ == '__main__':
    main()
