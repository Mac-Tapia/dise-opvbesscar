#!/usr/bin/env python3
"""
Generar PNG del diagrama Mermaid usando Kroki API (sin dependencias).
"""
import requests
import base64
from pathlib import Path
import time

# Diagrama exacto
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


def generate_png_via_kroki(mermaid_code: str, output_path: Path) -> bool:
    """Generar PNG usando Kroki API (free service) con POST."""
    try:
        print("🔄 Usando Kroki API para generar PNG...")
        
        # URL de Kroki (usando POST para evitar límite de URL)
        url = "https://kroki.io/mermaid/png"
        
        # Headers
        headers = {
            "Content-Type": "text/plain",
        }
        
        print(f"   Enviando diagrama a kroki.io (POST)...")
        response = requests.post(url, data=mermaid_code.encode('utf-8'), 
                                headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Guardar PNG
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            size_kb = output_path.stat().st_size / 1024
            print(f"\n✅ PNG GENERADO VIA KROKI")
            print(f"   📍 {output_path.name}")
            print(f"   Tamaño: {size_kb:.1f} KB")
            print(f"   Resolución: Optimizada para presentación")
            return True
        else:
            print(f"\n❌ ERROR: Kroki respondió con código {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERROR: No hay conexión a internet")
        print(f"   Se requiere conexión para usar Kroki API")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def create_html_interactive(mermaid_code: str, output_path: Path):
    """Crear archivo HTML interactivo para visualizar localmente."""
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline OE2→OE3 Completo - Tesis pvbesscar</title>
    <script async src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
            overflow-x: auto;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }}
        .mermaid {{
            background: white;
            display: flex;
            justify-content: center;
            padding: 20px;
        }}
        .info {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px 20px;
            margin-top: 20px;
            border-radius: 4px;
            font-size: 13px;
            color: #555;
            line-height: 1.6;
        }}
        .controls {{
            text-align: center;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
        button {{
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            margin: 0 5px;
            transition: background 0.3s;
        }}
        button:hover {{
            background: #764ba2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏗️ Pipeline OE2→OE3 Completo</h1>
        <p class="subtitle">8 Fases: Dimensionamiento → Validación → Entorno RL → Entrenamiento → Guardar → Resultados → Validación → Tesis</p>
        
        <div class="mermaid">
{mermaid_code}
        </div>
        
        <div class="info">
            <strong>ℹ️ Diagrama Interactivo:</strong> Este archivo HTML contiene un diagrama Mermaid completamente renderizado.
            Puedes hacer zoom con la rueda del ratón, desplazarte con clic y arrastrar.
            Para guardar como imagen: click derecho en el diagrama → Guardar imagen como.
        </div>
        
        <div class="controls">
            <button onclick="window.print()">🖨️ Imprimir / Guardar PDF</button>
            <button onclick="document.location.href='data:text/plain;charset=utf-8,' + encodeURIComponent(document.querySelector('.mermaid').textContent)">📥 Descargar Mermaid</button>
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
    
    return output_path.stat().st_size / 1024


def save_mermaid_source(mermaid_code: str, output_path: Path):
    """Guardar código Mermaid puro para edición."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(mermaid_code)
    
    return output_path.stat().st_size / 1024


def main():
    """Generar PNG y archivos de apoyo."""
    print("=" * 80)
    print("🏗️  GUARDANDO DIAGRAMA COMPLETO OE2→OE3 PARA TESIS")
    print("=" * 80)
    print()
    
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Generar PNG via Kroki
    png_path = reports_dir / "OE2_OE3_PIPELINE_COMPLETO.png"
    html_path = reports_dir / "OE2_OE3_PIPELINE_INTERACTIVO.html"
    mmd_path = reports_dir / "OE2_OE3_PIPELINE_COMPLETO.mmd"
    
    print("📝 Guardando artefactos...")
    print()
    
    # 1. Generar PNG
    png_success = generate_png_via_kroki(DIAGRAMA_COMPLETO, png_path)
    
    # 2. HTML interactivo (siempre éxito)
    try:
        html_size = create_html_interactive(DIAGRAMA_COMPLETO, html_path)
        print(f"✅ HTML INTERACTIVO GENERADO")
        print(f"   📍 {html_path.name}")
        print(f"   Tamaño: {html_size:.1f} KB")
        html_success = True
    except Exception as e:
        print(f"❌ Error en HTML: {e}")
        html_success = False
    
    print()
    
    # 3. Mermaid source
    try:
        mmd_size = save_mermaid_source(DIAGRAMA_COMPLETO, mmd_path)
        print(f"✅ FUENTE MERMAID GUARDADA")
        print(f"   📍 {mmd_path.name}")
        print(f"   Tamaño: {mmd_size:.1f} KB")
        mmd_success = True
    except Exception as e:
        print(f"❌ Error en Mermaid: {e}")
        mmd_success = False
    
    # Resumen
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE GENERACIÓN")
    print("=" * 80)
    
    if png_success and html_success and mmd_success:
        print(f"\n✨ Diagrama Profesional para Tesis LISTO")
        print(f"   ✓ 8 Fases completas del pipeline OE2→OE3")
        print(f"   ✓ Stack tecnológico incluido (Python, PyTorch, stable-baselines3)")
        print(f"   ✓ Colores profesionales para presentación académica")
        print(f"   ✓ Resolución optimizada para impresión")
        print(f"\n📁 Archivos generados:")
        print(f"   1️⃣  OE2_OE3_PIPELINE_COMPLETO.png     ← USAR EN TESIS")
        print(f"   2️⃣  OE2_OE3_PIPELINE_INTERACTIVO.html ← Ver en navegador")
        print(f"   3️⃣  OE2_OE3_PIPELINE_COMPLETO.mmd     ← Editar en herramientas Mermaid")
        print(f"\n💾 Ubicación: {reports_dir.absolute()}")
    else:
        print(f"\n⚠️  Generación parcial:")
        print(f"   PNG: {'✅' if png_success else '❌'}")
        print(f"   HTML: {'✅' if html_success else '❌'}")
        print(f"   Mermaid: {'✅' if mmd_success else '❌'}")
    
    return 0 if (png_success and html_success and mmd_success) else 1


if __name__ == "__main__":
    exit(main())
