#!/usr/bin/env python3
"""
Genera diagrama arquitectura e arquitectura workflow en HTML para exportar a PDF
pvbesscar v7.1 - Generador de Diagramas Profesionales
"""

from pathlib import Path
from datetime import datetime

# Diagramas Mermaid con MALL demand actualizado (Feb 2026)
DIAGRAMA_ARQUITECTURA = """graph TB
    subgraph OE2["⚙️ FASE OE2: Dimensionamiento de Infraestructura"]
        direction LR
        SOL["☀️ Panel Solar<br/>4,050 kWp<br/>8,760 h/año"]
        MALL["🏢 Demanda Mall<br/>PROMEDIO: 1,412 kW<br/>PICO: 2,763 kW<br/>ANUAL: 12,368,653 kWh"]
        BESS["🔋 BESS Battery<br/>2,000 kWh<br/>400 kW<br/>Efficiency: 95%"]
        CARGADORES["🔌 19 Chargers<br/>38 Sockets<br/>7.4 kW each<br/>Mode 3"]
        EV["🛵 EV Fleet<br/>270 Motos<br/>39 MotoTaxis<br/>38 daily"]
        
        SOL --> BESS
        MALL --> BESS
        BESS --> CARGADORES
        EV --> CARGADORES
    end
    
    subgraph OE3["🤖 FASE OE3: Control con RL Agents"]
        direction LR
        CL["CityLearn v2<br/>Environment<br/>8,760 timesteps"]
        SAC["Soft Actor Critic<br/>Off-Policy<br/>Best for asymmetric"]
        PPO["Proximal Policy<br/>Optimization<br/>On-Policy stable"]
        A2C["Advantage Actor<br/>Critic<br/>Lightweight"]
        
        CL --> SAC
        CL --> PPO
        CL --> A2C
    end
    
    subgraph RESULTADOS["📊 Resultados Entrenados (CO₂ minimización)"]
        SAC_R["SAC Agent<br/>CO₂: 790,308 kg/año<br/>Solar: 98.93%<br/>Grid: 2,249,319 kWh"]
        PPO_R["PPO Agent<br/>CO₂: 417,134 kg/año<br/>Solar: 100%<br/>Grid: 2,696,960 kWh"]
        A2C_R["A2C Agent<br/>CO₂: 407,908 kg/año<br/>Solar: 100%<br/>Grid: 1,276,586 kWh"]
    end
    
    OE2 -.->|Artifact: CSV, JSON| OE3
    SAC --> SAC_R
    PPO --> PPO_R
    A2C --> A2C_R
    
    style OE2 fill:#e1f5ff,stroke:#0277bd,stroke-width:2px
    style OE3 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style RESULTADOS fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px"""

DIAGRAMA_FLUJO = """graph LR
    subgraph ETAPA1["ETAPA 1: Inputs del Proyecto"]
        MALLF["📊 Demanda Mall<br/>demandamallhorakwh.csv<br/>PROMEDIO: 1,412 kW<br/>PICO: 2,763 kW"]
        SOLF["☀️ Generación Solar<br/>pv_generation_timeseries.csv<br/>4,050 kWp<br/>8,760 hourly"]
        EV_F["🛵 EV Demand Profiles<br/>demand_ev_anual.csv<br/>270 motos + 39 taxis<br/>38 sockets"]
        CFG["⚙️ Configuration<br/>architecture.yaml<br/>500 timesteps"]
    end
    
    subgraph ETAPA2["ETAPA 2: Load & Validation"]
        DL["📥 Data Loader<br/>data_loader.py<br/>✓ Solar: 8,760 rows<br/>✓ Mall: 1,412 kW avg (2,763 peak)<br/>✓ EV: 38 sockets"]
        VAL["✅ Validation<br/>OE2ValidationError<br/>if solar ≠ 8,760h<br/>if chargers ≠ 38"]
    end
    
    subgraph ETAPA3["ETAPA 3: Build OE2 Artifacts"]
        CHARGERS["🔌 Charger Specs<br/>chargers.py<br/>19 units × 2 sockets<br/>7.4 kW @ 230V"]
        BESS_CFG["🔋 BESS Config<br/>bess.py<br/>2,000 kWh<br/>400 kW / SOC 20-100%"]
    end
    
    subgraph ETAPA4["ETAPA 4: Create CityLearn Environment"]
        CL["🏗️ CityLearn v2<br/>Environment<br/>- Obs: 394-dim solar/BESS/38sockets<br/>- Action: 39-dim (1 BESS + 38 chargers)<br/>- HorizonLen: 8,760 timesteps"]
    end
    
    subgraph ETAPA5["ETAPA 5: Reward & Agent Initialization"]
        RW["🎯 Multi-Objective Reward<br/>w_CO₂=0.35 | w_EV=0.30<br/>w_solar=0.20 | w_cost=0.10<br/>w_grid=0.05"]
        AGENTS["🤖 Initialize Agents<br/>SAC/PPO/A2C from sb3<br/>policy='MlpPolicy'<br/>validate_env_spaces()"]
    end
    
    subgraph ETAPA6["ETAPA 6: Training Loop (26,280 steps)"]
        TRN["🔄 Learn with CB<br/>agent.learn(total_timesteps=26280)<br/>checkpoint every N steps<br/>save_config_every_callback"]
    end
    
    subgraph ETAPA7["ETAPA 7: Evaluation & Results"]
        EVAL["📊 Evaluate<br/>CO₂ (kg/año)<br/>Solar self-consumption %<br/>Grid import (kWh)<br/>EV satisfaction %"]
        CSV["💾 Save Results<br/>result_{sac,ppo,a2c}.json<br/>ppo_training_summary.json"]
    end
    
    subgraph ETAPA8["ETAPA 8: Document + Report"]
        DOC["📄 Generate Thesis<br/>generate_oe3_detailed_report.py<br/>Dynamic values from checkpoints<br/>41 acápites (100% completud)"]
        PDF["📕 Save PDF Report<br/>OE3_INFORME_DETALLADO.pdf<br/>Reward weights validated<br/>MALL: 1,412 kW reflected"]
    end
    
    MALLF --> DL
    SOLF --> DL
    EV_F --> DL
    CFG --> DL
    
    DL --> VAL
    VAL --> CHARGERS
    VAL --> BESS_CFG
    CHARGERS --> CL
    BESS_CFG --> CL
    CL --> RW
    RW --> AGENTS
    AGENTS --> TRN
    TRN --> EVAL
    EVAL --> CSV
    CSV --> DOC
    DOC --> PDF
    
    style ETAPA1 fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style ETAPA2 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style ETAPA3 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style ETAPA4 fill:#f1f8e9,stroke:#558b2f,stroke-width:2px
    style ETAPA5 fill:#ffe0b2,stroke:#ff6f00,stroke-width:2px
    style ETAPA6 fill:#e0f2f1,stroke:#00695c,stroke-width:2px
    style ETAPA7 fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    style ETAPA8 fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px"""

def generate_html(architecture_mermaid: str, workflow_mermaid: str) -> str:
    """Genera HTML con diagramas Mermaid - SIN conflictos de formato"""
    
    timestamp = datetime.now().strftime("%d de %B de %Y a las %H:%M")
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arquitectura y Flujo de Trabajo pvbesscar</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .timestamp {{
            text-align: center;
            color: #999;
            font-size: 0.9em;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
        }}
        
        .diagram-section {{
            margin-bottom: 60px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 8px;
            border-left: 5px solid #667eea;
        }}
        
        .diagram-title {{
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 25px;
            font-weight: 600;
        }}
        
        .mermaid {{
            display: flex;
            justify-content: center;
            background: white;
            padding: 20px;
            border-radius: 8px;
        }}
        
        .footer {{
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #ddd;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                max-width: 100%;
                margin: 0;
            }}
            .diagram-section {{
                page-break-inside: avoid;
                margin-bottom: 30px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ Arquitectura y Flujo de Trabajo</h1>
            <p>Proyecto pvbesscar - Optimización de Carga EV con RL</p>
        </div>
        
        <div class="content">
            <div class="timestamp">Generado: {timestamp}</div>
            
            <div class="diagram-section">
                <div class="diagram-title">1️⃣ Arquitectura General del Proyecto</div>
                <div class="mermaid">
{architecture_mermaid}
                </div>
            </div>
            
            <div class="diagram-section">
                <div class="diagram-title">2️⃣ Flujo de Trabajo Detallado: 8 Etapas</div>
                <div class="mermaid">
{workflow_mermaid}
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>pvbesscar v7.1</strong> | Repositorio: Mac-Tapia/dise-opvbesscar (rama: smartcharger)</p>
            <p>📌 Para convertir a PDF: Abre en navegador → Ctrl+P (Imprimir) → Guardar como PDF</p>
        </div>
    </div>
    
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default', maxTextSize: 90000 }});
    </script>
</body>
</html>
"""
    return html

def main():
    """Genera archivos HTML y PDF"""
    
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    
    print("=" * 70)
    print("🏗️  GENERADOR DE DIAGRAMAS ARQUITECTURA - pvbesscar v7.1")
    print("=" * 70)
    
    # Generar HTML
    html_content = generate_html(DIAGRAMA_ARQUITECTURA, DIAGRAMA_FLUJO)
    html_path = reports_dir / 'ARQUITECTURA_DIAGRAMA_INTERACTIVO.html'
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ HTML generado: {html_path}")
    print(f"   Tamaño: {len(html_content):,} bytes")
    
    # Intentar generar PDF con WeasyPrint si está disponible
    try:
        import weasyprint
        print("\n🔄 Generando PDF con WeasyPrint...")
        pdf_path = reports_dir / 'ARQUITECTURA_DIAGRAMA.pdf'
        weasyprint.HTML(string=html_content).write_pdf(pdf_path)
        print(f"✅ PDF generado: {pdf_path}")
    except ImportError:
        print("\n⚠️  WeasyPrint no instalado. Alternativa:")
        print("   1. Abre en navegador: " + str(html_path))
        print("   2. Presiona Ctrl+P (Imprimir)")
        print("   3. Selecciona 'Guardar como PDF'")
        print("   4. Guarda como: reports/ARQUITECTURA_DIAGRAMA.pdf")
    except Exception as e:
        print(f"\n⚠️  Error generando PDF: {e}")
        print("   Abre el HTML en navegador y usa Ctrl+P para guardar en PDF")
    
    print("\n" + "=" * 70)
    print("✨ Proceso completado")
    print("=" * 70)

if __name__ == '__main__':
    main()
