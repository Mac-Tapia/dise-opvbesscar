#!/usr/bin/env python3
"""
Generar PNG y PDF del diagrama 8-etapas OE2→OE3 (flujo horizontal).
Igual que el anterior, sin variaciones en el contenido.
"""
import requests
from pathlib import Path
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from PIL import Image
import io

# Diagrama exacto (flujo horizontal 8 etapas)
DIAGRAMA_8ETAPAS = """graph LR
    subgraph Input["📥 ENTRADA: ARTEFACTOS OE2"]
        PVF["data/oe2/Generacionsolar/<br/>pv_generation.csv"]
        BESSF["data/oe2/BESS/<br/>bess_ano_2024.csv"]
        CHGF["data/oe2/chargers/<br/>chargers_ev_*.csv"]
        EVDF["data/oe2/EV_Demand/<br/>demand_profiles.csv"]
        MALLF["data/oe2/demandamallkwh/<br/>demandamallhorakwh.csv<br/>PROMEDIO: 1,412 kW<br/>PICO: 2,763 kW"]
    end
    
    subgraph Load["🔄 ETAPA 1: CARGA Y VALIDACIÓN"]
        OE2Val["src/dimensionamiento/oe2/<br/>Modules:<br/>- solar_pvlib.py<br/>- chargers.py<br/>- bess.py<br/>- data_loader.py"]
        Check["Validaciones Críticas:<br/>✓ Solar: 8,760 filas horarias<br/>✓ NO 15-min data<br/>✓ BESS: 6-phase logic<br/>✓ Chargers: 19×2=38 sockets<br/>✓ Mall: 1,412 kW avg (2,763 peak)<br/>✓ EV: queue model"]
        
        PVF -->|Parse CSV| OE2Val
        BESSF -->|Parse CSV| OE2Val
        CHGF -->|Parse JSON| OE2Val
        EVDF -->|Parse| OE2Val
        MALLF -->|Parse CSV| OE2Val
        OE2Val -->|Validate| Check
    end
    
    subgraph Process["⚙️ ETAPA 2: PROCESAMIENTO OE2→OE3"]
        Builder["src/dataset_builder_citylearn/<br/>dataset_builder.py:<br/>- Load OE2 artifacts<br/>- Build 394-dim vector<br/>- Create reward weights<br/>- Normalize observations"]
        
        Interop["Interoperabilidad:<br/>data/interim/oe2/<br/>- Solar prep<br/>- BESS dispatch<br/>- Charger schedule<br/>- EV demand queue<br/>- Mall load allocation"]
        
        Check -->|OE2 artifacts OK| Builder
        Builder -->|Transform| Interop
    end
    
    subgraph Env["🌍 ETAPA 3: ENTORNO RL"]
        CL["CityLearn v2 Environment<br/>- 8,760 timesteps<br/>- 1h per step<br/>- Multi-building support<br/>- Mall load: 1,412 kW nominal"]
        
        Obs["Observation Vector 394-D:<br/>• Building: 12 (energy, temperature)<br/>• Solar: 24 (hourly gen trace)<br/>• BESS: 5 (SOC, mode, power)<br/>• EV: 38×3=114 (per socket)<br/>• Net: 5 (frequency, voltage)<br/>• Time: 12 (hour, day, season)<br/>• Economic: 3 (tariff, price, carbon)"]
        
        Act["Action Vector 39-D:<br/>• BESS: 1 (power [0,1])<br/>• EV sockets: 38 (power [0,1])<br/>→ Normalized to actual kW<br/>  via action_bounds"]
        
        Interop -->|Init| CL
        CL -->|Provides| Obs
        CL -->|Accepts| Act
    end
    
    subgraph Train["🤖 ETAPA 4: ENTRENAMIENTO"]
        SACTr["SAC Training<br/>- 87,600 steps<br/>- 10 episodes<br/>- off-policy<br/>- ~350 sec GPU"]
        PPOTr["PPO Training<br/>- 87,600 steps<br/>- on-policy<br/>- ~200 sec GPU"]
        A2CTr["A2C Training<br/>- 87,600 steps<br/>- on-policy simple<br/>- ~160 sec GPU"]
        
        Reward["🎯 Reward Function<br/>R_total = 0.35×R_CO2<br/>          + 0.30×R_EV<br/>          + 0.20×R_solar<br/>          + 0.10×R_cost<br/>          + 0.05×R_grid<br/>          - P_bess_low<br/>(source: rewards.py)"]
        
        Obs -->|Feed| SACTr
        Obs -->|Feed| PPOTr
        Obs -->|Feed| A2CTr
        Reward -->|Guide| SACTr
        Reward -->|Guide| PPOTr
        Reward -->|Guide| A2CTr
    end
    
    subgraph Save["💾 ETAPA 5: GUARDADO"]
        SACChk["checkpoints/SAC/<br/>sac_model_final_*.zip<br/>- policy_net<br/>- value_net<br/>- optimizer_state"]
        PPOChk["checkpoints/PPO/<br/>ppo_model_*.zip"]
        A2CChk["checkpoints/A2C/<br/>a2c_model_*.zip"]
        
        SACTr -->|Save| SACChk
        PPOTr -->|Save| PPOChk
        A2CTr -->|Save| A2CChk
    end
    
    subgraph Export["📊 ETAPA 6: EXPORT MÉTRICAS"]
        SACJ["outputs/sac_training/<br/>result_sac.json<br/>├─ training:<br/>│  ├─ duration_seconds<br/>│  ├─ steps_per_sec<br/>│  └─ mean_reward<br/>└─ validation:<br/>   ├─ mean_co2_avoided_kg<br/>   ├─ mean_solar_kwh<br/>   ├─ mean_grid_kwh<br/>   └─ mean_ev_satisfaction"]
        
        PPOJ["outputs/ppo_training/<br/>ppo_training_summary.json"]
        A2CJ["outputs/a2c_training/<br/>result_a2c.json"]
        
        SACChk -->|Log metrics| SACJ
        PPOChk -->|Log metrics| PPOJ
        A2CChk -->|Log metrics| A2CJ
    end
    
    subgraph Compare["✅ ETAPA 7: COMPARACIÓN & VALIDACIÓN"]
        Val["Comparison Report:<br/>Metrics extraction<br/>- Parse JSON<br/>- Annualize values<br/>- Calculate %reductions<br/>- vs Baseline<br/>- Mall load: 12.37M kWh/año"]
        
        SACJ -->|Parse| Val
        PPOJ -->|Parse| Val
        A2CJ -->|Parse| Val
    end
    
    subgraph GenDoc["📄 ETAPA 8: GENERACIÓN DOCUMENTO"]
        GenScript["scripts/<br/>generate_oe3_detailed_report.py<br/>├─ Load checkpoints<br/>├─ Extract dynamic values<br/>├─ Build document structure<br/>│  (8 sections × 41 acápites)<br/>├─ Insert real data<br/>└─ Format tables"]
        
        Val -->|Real data| GenScript
    end
    
    subgraph Output["📖 SALIDA FINAL"]
        DocOut["reports/<br/>OE3_INFORME_DETALLADO_<br/>CON_DATOS_REALES.docx<br/>✅ 100% Completitud<br/>✅ 41 acápites<br/>✅ 8 tablas<br/>✅ Datos reales<br/>✅ THESIS READY"]
        
        GenScript -->|Generate| DocOut
    end
    
    style Input fill:#fff3cd
    style Load fill:#d1ecf1
    style Process fill:#d4edda
    style Env fill:#d1f5ff
    style Train fill:#cce5ff
    style Save fill:#e7d4f5
    style Export fill:#f8d7da
    style Compare fill:#d1ecf1
    style GenDoc fill:#f0e6ff
    style Output fill:#90EE90"""


def generate_png_via_kroki(mermaid_code: str, output_path: Path) -> bool:
    """Generar PNG usando Kroki API (POST)."""
    try:
        print(f"🔄 Generando PNG (Kroki API)...")
        
        url = "https://kroki.io/mermaid/png"
        headers = {"Content-Type": "text/plain"}
        
        response = requests.post(
            url,
            data=mermaid_code.encode('utf-8'),
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            size_kb = output_path.stat().st_size / 1024
            print(f"   ✅ PNG generado: {size_kb:.1f} KB")
            return True
        else:
            print(f"   ❌ Error {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def create_pdf_from_png(png_path: Path, pdf_path: Path) -> bool:
    """Crear PDF a partir de PNG."""
    try:
        print(f"📄 Convirtiendo PNG a PDF...")
        
        # Abrir imagen PNG
        img = Image.open(png_path)
        
        # Convertir a RGB si es necesario
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        
        # Crear PDF con tamaño A3 landscape
        page_width, page_height = A3[1], A3[0]  # Intercambiar para landscape
        
        c = canvas.Canvas(str(pdf_path), pagesize=(page_width, page_height))
        
        # Calcular tamaño de imagen para que quepa en la página
        img_width, img_height = img.size
        aspect_ratio = img_height / img_width
        
        # Usar máximo ancho disponible con margen
        max_width = page_width - 0.5 * inch
        new_width = max_width
        new_height = new_width * aspect_ratio
        
        # Centrar verticalmente
        x = 0.25 * inch
        y = (page_height - new_height) / 2
        
        # Guardar imagen temporalmente
        temp_img = Path('temp_diagram.png')
        img.save(temp_img)
        
        # Dibujar en PDF
        c.drawImage(str(temp_img), x, y, width=new_width, height=new_height)
        c.save()
        
        # Limpiar temporal
        temp_img.unlink(missing_ok=True)
        
        size_kb = pdf_path.stat().st_size / 1024
        print(f"   ✅ PDF generado: {size_kb:.1f} KB")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def create_html_interactive(mermaid_code: str, output_path: Path) -> bool:
    """Crear HTML interactivo."""
    try:
        print(f"🌐 Generando HTML interactivo...")
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline OE2→OE3 - 8 Etapas</title>
    <script async src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 100%;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 20px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .mermaid {{
            display: flex;
            justify-content: center;
            overflow-x: auto;
        }}
        .info {{
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-top: 20px;
            border-radius: 4px;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Pipeline OE2→OE3: 8 Etapas Completas</h1>
        <p class="subtitle">Flujo de datos: OE2 → Validación → CityLearn → Training → Checkpoints → Métricas → Validación → Tesis</p>
        
        <div class="mermaid">
{mermaid_code}
        </div>
        
        <div class="info">
            <strong>ℹ️ Interactivo:</strong> Puedes hacer zoom (rueda del ratón), desplazarte (clic+arrastrar) y guardar como imagen (click derecho).
        </div>
    </div>
    
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
        mermaid.contentLoaderInit();
    </script>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        size_kb = output_path.stat().st_size / 1024
        print(f"   ✅ HTML generado: {size_kb:.1f} KB")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    print("=" * 80)
    print("🏗️  GUARDANDO DIAGRAMA 8-ETAPAS OE2→OE3 (FLUJO HORIZONTAL)")
    print("=" * 80)
    print()
    
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Rutas de salida
    png_path = reports_dir / "PIPELINE_8ETAPAS_OE2_OE3.png"
    pdf_path = reports_dir / "PIPELINE_8ETAPAS_OE2_OE3.pdf"
    html_path = reports_dir / "PIPELINE_8ETAPAS_INTERACTIVO.html"
    
    print("📝 Generando archivos...\n")
    
    # 1. PNG
    png_ok = generate_png_via_kroki(DIAGRAMA_8ETAPAS, png_path)
    
    # 2. PDF (desde PNG)
    pdf_ok = False
    if png_ok:
        pdf_ok = create_pdf_from_png(png_path, pdf_path)
    
    # 3. HTML
    html_ok = create_html_interactive(DIAGRAMA_8ETAPAS, html_path)
    
    # Resumen
    print("\n" + "=" * 80)
    print("✨ DIAGRAMA PROFESIONAL PARA TESIS GENERADO")
    print("=" * 80)
    
    print(f"\n📁 Archivos en reports/:\n")
    
    files_info = [
        ("PIPELINE_8ETAPAS_OE2_OE3.png", "🎯 USAR EN TESIS", png_ok),
        ("PIPELINE_8ETAPAS_OE2_OE3.pdf", "📄 Versión PDF", pdf_ok),
        ("PIPELINE_8ETAPAS_INTERACTIVO.html", "🌐 Ver en navegador", html_ok),
    ]
    
    for fname, purpose, ok in files_info:
        status = "✅" if ok else "❌"
        fpath = reports_dir / fname
        if fpath.exists():
            size = fpath.stat().st_size / 1024
            print(f"   {status} {fname:<40} ({size:.1f} KB) - {purpose}")
        else:
            print(f"   {status} {fname:<40} - {purpose}")
    
    print(f"\n✓ 8 Fases: OE2 → Carga → Procesamiento → Entorno → Training → Checkpoints → Métricas → Documento")
    print(f"✓ Flujo horizontal con todas las dependencias y detalles")
    print(f"✓ Colores profesionales para presentación")
    print(f"✓ Resolución optimizada para impresión\n")
    
    return 0 if (png_ok and pdf_ok and html_ok) else 1


if __name__ == "__main__":
    exit(main())
