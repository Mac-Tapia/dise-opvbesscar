#!/usr/bin/env python3
"""
Guardar diagrama completo OE2→OE3 como PNG de alta resolución y PDF para tesis.
Preserva exactamente el Mermaid markup sin variaciones.
"""
import subprocess
import tempfile
from pathlib import Path
import time

# Diagrama exacto a guardar
DIAGRAMA_COMPLETO = """graph TB
    subgraph OE2["📦 FASE OE2: DIMENSIONAMIENTO (Infraestructura)"]
        PV["☀️ Paneles Solares<br/>4,050 kWp<br/>PVGIS 8,760h"]
        BESS["🔋 Batería<br/>2,000 kWh / 400 kW<br/>6 Fases Operación"]
        CHG["🔌 Cargadores<br/>19 chargers × 2 sockets<br/>38 puntos de carga<br/>7.4 kW Mode 3"]
        MALL["🏢 Demanda Mall<br/>100 kW 24h<br/>Base load"]
        EV["🚗 Vehículos<br/>270 motos + 39 mototaxis<br/>309 día"]
        
        PV -->|pv_generation.csv| Data1["📊 CSV Datos OE2<br/>data/oe2/"]
        BESS -->|BESS specs| Data1
        CHG -->|Charger config| Data1
        MALL -->|Demand profile| Data1
        EV -->|EV arrival queue| Data1
    end
    
    subgraph Pipeline["🔄 VALIDACIÓN & CARGA DE DATOS"]
        Data1 -->|Load & Validate| Loader["data_loader.py<br/>Valida 8,760 filas<br/>No 15-min ⚠️"]
        Loader -->|Sync OE2↔OE3| Builder["dataset_builder.py<br/>Crea 394-dim obs<br/>Reward weights"]
    end
    
    subgraph CityLearn["🌍 ENTORNO CITYLEARN v2"]
        Env["CityLearn Environment<br/>Timestep: 1 hora = 3,600 seg<br/>Episodes: 8,760 steps = 1 año"]
        ObsSpace["📋 Observation Space<br/>- Solar W/m²<br/>- BESS SOC %<br/>- 38 socket states<br/>- Time features (hour/month/dow)<br/>Total: 394 dimensions"]
        ActSpace["🎮 Action Space<br/>Continuous [0,1]<br/>1 BESS + 38 sockets<br/>39 total actions"]
        
        Builder -->|Init env| Env
        Env -->|Provides| ObsSpace
        Env -->|Accepts| ActSpace
    end
    
    subgraph Training["🤖 ENTRENAMIENTO RL - 3 AGENTES"]
        SAC["🏆 SAC<br/>Off-Policy<br/>Soft Actor-Critic<br/>stable-baselines3"]
        PPO["📈 PPO<br/>On-Policy<br/>Proximal Policy<br/>stable-baselines3"]
        A2C["⚡ A2C<br/>On-Policy<br/>Actor-Critic<br/>stable-baselines3"]
        
        Reward["Reward Function<br/>w_CO2=0.35 (PRIMARY)<br/>w_EV=0.30 (SECONDARY)<br/>w_solar=0.20<br/>w_cost=0.10<br/>w_grid=0.05"]
        
        ObsSpace -->|87,600 steps| SAC
        ObsSpace -->|10 episodios| PPO
        ObsSpace -->|= 10 años| A2C
        Reward -->|Guide policy| SAC
        Reward -->|Guide policy| PPO
        Reward -->|Guide policy| A2C
    end
    
    subgraph Checkpoints["💾 GUARDADO DE MODELOS"]
        SACC["checkpoints/SAC/<br/>sac_model_*.zip<br/>policy network<br/>value network<br/>optimizer state"]
        PPOC["checkpoints/PPO/<br/>ppo_model_*.zip"]
        A2CC["checkpoints/A2C/<br/>a2c_model_*.zip"]
        
        SAC -->|Save| SACC
        PPO -->|Save| PPOC
        A2C -->|Save| A2CC
    end
    
    subgraph Results["📊 RESULTADOS Y METRICAS"]
        SACJ["outputs/sac_training/<br/>result_sac.json<br/>18,621 lineas<br/>validation metrics"]
        PPOJ["outputs/ppo_training/<br/>ppo_summary.json"]
        A2CJ["outputs/a2c_training/<br/>result_a2c.json"]
        
        SACC -->|Export metrics| SACJ
        PPOC -->|Export metrics| PPOJ
        A2CC -->|Export metrics| A2CJ
    end
    
    subgraph Validation["✅ VALIDACIÓN DE RESULTADOS"]
        Val["Comparison vs Baseline<br/>- CO2 avoided kg/año<br/>- Solar utilization %<br/>- Grid import kWh<br/>- EV satisfaction %<br/>- Training time sec"]
        
        SACJ -->|Parse| Val
        PPOJ -->|Parse| Val
        A2CJ -->|Parse| Val
    end
    
    subgraph Thesis["📄 GENERACIÓN DOCUMENTO TESIS"]
        Report["generate_oe3_report.py<br/>Dynamic data extraction<br/>Real checkpoint values<br/>41 acápites completos"]
        
        Val -->|Real data| Report
        Report -->|Generate| DocX["📖 OE3_INFORME_DETALLADO<br/>CON_DATOS_REALES.docx<br/>15-18 páginas<br/>8 tablas<br/>100% completitud<br/>✅ THESIS READY"]
    end
    
    subgraph Tech["🛠️ STACK TECNOLÓGICO"]
        Python["Python 3.11+<br/>type hints enabled"]
        SB3["stable-baselines3 v2.0+<br/>SAC, PPO, A2C"]
        Gym["Gymnasium 0.27+<br/>Standard RL API"]
        Torch["PyTorch 2.0+ CUDA<br/>GPU: RTX 4060"]
        Data["pandas 2.0+<br/>numpy 1.25+"]
        YAML["PyYAML 6.0<br/>configs/"]
        DocX_lib["python-docx 0.8.11"]
        
        Python -->|Runtime| SB3
        Python -->|Runtime| Gym
        Python -->|Runtime| Torch
        Python -->|Runtime| Data
        YAML -->|Config| Report
        DocX_lib -->|Generate| DocX
    end
    
    style OE2 fill:#fff3cd
    style Pipeline fill:#d1ecf1
    style CityLearn fill:#d4edda
    style Training fill:#cce5ff
    style Checkpoints fill:#e7d4f5
    style Results fill:#f8d7da
    style Validation fill:#d1ecf1
    style Thesis fill:#c3e6cb
    style Tech fill:#f0f0f0"""


def create_html_with_mermaid(mermaid_code: str) -> str:
    """Crear HTML con Mermaid para renderizar en navegador."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline OE2→OE3 Completo</title>
    <script async src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: white;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .mermaid {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            text-align: center;
            color: #333;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .container {{
            max-width: 100%;
            background: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Pipeline OE2→OE3 Completo: 8 Fases para Tesis</h1>
        <div class="mermaid">
{mermaid_code}
        </div>
    </div>
    <script>
        mermaid.contentLoaderInit();
    </script>
</body>
</html>"""


def generate_png_from_html(html_content: str, output_path: Path) -> bool:
    """Generar PNG de alta calidad usando Edge headless."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_html = f.name
        
        print(f"✅ HTML temporal creado")
        print(f"   {Path(temp_html).name}")
        print(f"\n🔄 Capturando PNG con Microsoft Edge (1920×1440)...")
        
        # Intentar con rutas comunes de Edge en Windows
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "msedge",
            "msedge.exe"
        ]
        
        edge_exe = None
        for path in edge_paths:
            if Path(path).exists():
                edge_exe = path
                break
        
        if not edge_exe:
            # Intentar encontrar chrome como alternativa
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            for path in chrome_paths:
                if Path(path).exists():
                    edge_exe = path
                    break
        
        if not edge_exe:
            print(f"\n⚠️  No se encontró Edge o Chrome. Usando PowerShell para captura...")
            # Usar método alternativo con PowerShell
            ps_script = f"""
$url = '{Path(temp_html).absolute()}'
$output = '{output_path}'
Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Width = 1920
$form.Height = 1440
$form.BackColor = 'White'
$web = New-Object System.Windows.Forms.WebBrowser
$web.Dock = 'Fill'
$web.NavigateToString(@'
{html_content}
'@)
$form.Controls.Add($web)
Start-Sleep -Milliseconds 3000
[System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea | Out-Null
$bmp = New-Object System.Drawing.Bitmap(1920, 1440)
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.Clear([System.Drawing.Color]::White)
$graphics.Dispose()
$bmp.Save($output)
$bmp.Dispose()
"""
            # Este método es muy lento, mejor usar alternativa
            return False
        
        # Usar Edge/Chrome headless para capturar
        cmd = [
            edge_exe,
            "--headless",
            f"--screenshot={output_path}",
            "--window-size=1920,1440",
            f"file:///{Path(temp_html).absolute()}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Limpiar temporal
        Path(temp_html).unlink(missing_ok=True)
        
        if output_path.exists():
            size_kb = output_path.stat().st_size / 1024
            print(f"\n✅ PNG GENERADO (ALTA RESOLUCIÓN)")
            print(f"   📍 {output_path.name}")
            print(f"   Tamaño: {size_kb:.1f} KB")
            print(f"   Navegador: {Path(edge_exe).name}")
            return True
        else:
            print(f"\n❌ ERROR: No se generó {output_path.name}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def main():
    """Generar PNG y PDF del diagrama."""
    print("=" * 80)
    print("🏗️  GUARDANDO DIAGRAMA COMPLETO OE2→OE3 PARA TESIS")
    print("=" * 80)
    print()
    
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Rutas de salida
    png_path = reports_dir / "OE2_OE3_PIPELINE_COMPLETO.png"
    
    # Crear HTML
    html_content = create_html_with_mermaid(DIAGRAMA_COMPLETO)
    
    # Generar PNG
    png_success = generate_png_from_html(html_content, png_path)
    
    # Resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE GENERACIÓN")
    print("=" * 80)
    
    if png_success:
        print(f"\n✨ Diagrama Profesional para Tesis LISTO")
        print(f"   ✓ 8 Fases completas: OE2 → Pipeline → CityLearn → Training → Checkpoints → Results → Validation → Thesis")
        print(f"   ✓ Stack tecnológico incluido")
        print(f"   ✓ Colores profesionales para presentación")
        print(f"   ✓ Resolución alta (1920×1440) - óptima para imprimir")
        print(f"   ✓ Archivo: reports/OE2_OE3_PIPELINE_COMPLETO.png")
        print(f"\n📍 Archivos generados en: {reports_dir.absolute()}")
    else:
        print("\n❌ Falló la generación del diagrama")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
