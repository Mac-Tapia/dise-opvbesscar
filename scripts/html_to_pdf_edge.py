"""
Convierte HTML a PDF usando Microsoft Edge (disponible en Windows 10/11)
pvbesscar v7.1 - PDF Generator usando Edge
"""

from pathlib import Path
import subprocess
import time
import json

def convert_html_to_pdf_edge(html_path: Path, pdf_path: Path):
    """
    Convierte HTML a PDF usando Microsoft Edge via headless mode
    """
    
    try:
        # Rutas posibles de Edge en Windows
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        
        edge_exe = None
        for path in edge_paths:
            if Path(path).exists():
                edge_exe = path
                break
        
        if not edge_exe:
            print("   ⚠️  Microsoft Edge no encontrado")
            return False
        
        print(f"   📄 Usando: {edge_exe}")
        
        # Convertir a ruta absoluta
        html_abs = html_path.absolute().as_posix()
        pdf_abs = pdf_path.absolute().as_posix()
        
        # Comando para Edge en modo headless con print-to-pdf
        cmd = [
            edge_exe,
            f"--headless",
            f"--disable-gpu",
            f"--print-to-pdf={pdf_abs}",
            f"file:///{html_abs}"
        ]
        
        print(f"   🔄 Ejecutando: {' '.join(cmd[:3])}...")
        
        # Ejecutar Edge
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        time.sleep(2)  # Esperar a que se escriba el archivo
        
        if pdf_path.exists():
            print(f"   ✅ PDF generado: {pdf_path.name}")
            print(f"      Tamaño: {pdf_path.stat().st_size:,} bytes")
            return True
        else:
            print(f"   ❌ Error: No se creó el PDF")
            if result.stderr:
                print(f"      {result.stderr.decode()[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("   ❌ Tiempo agotado")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    reports_dir = Path('reports')
    
    print("=" * 80)
    print("🔄 CONVERSIÓN DE HTML A PDF USANDO MICROSOFT EDGE")
    print("=" * 80)
    
    html_file = reports_dir / 'ARQUITECTURA_DIAGRAMA_INTERACTIVO.html'
    pdf_file = reports_dir / 'ARQUITECTURA_DIAGRAMA.pdf'
    
    if not html_file.exists():
        print(f"\n❌ No encontrado: {html_file}")
        return
    
    print(f"\n📄 Convirtiendo: {html_file.name}")
    print(f"   → Destino: {pdf_file.name}")
    print()
    
    success = convert_html_to_pdf_edge(html_file, pdf_file)
    
    if success:
        print("\n" + "=" * 80)
        print("✨ PDF generado exitosamente")
        print("=" * 80)
        print(f"\n📍 Ubicación: {pdf_file}")
        print(f"\n📋 Contenido:")
        print(f"   • Diagrama 1: Arquitectura General (OE2 → OE3)")
        print(f"   • Diagrama 2: Flujo de Trabajo (8 Etapas)")
    else:
        print("\n" + "=" * 80)
        print("❌ No se pudo generar el PDF con Edge")
        print("=" * 80)
        print("\n💡 Alternativa: Usar el navegador")
        print("   1. Abre: http://localhost:8000/ARQUITECTURA_DIAGRAMA_INTERACTIVO.html")
        print("   2. Presiona: Ctrl+P")
        print("   3. Guardar como PDF")

if __name__ == '__main__':
    main()
