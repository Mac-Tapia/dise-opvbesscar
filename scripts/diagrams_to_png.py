"""
Convierte los diagramas Mermaid exactos a PNG usando Edge
Orden correcto: 1) Arquitectura, 2) Flujo
Con demanda mall corregida: 1,412 kW promedio / 2,763 kW pico
"""

from pathlib import Path
import subprocess
import time

# DIAGRAMA 1: ARQUITECTURA (DEBE IR PRIMERO)
ARQUITECTURA = """graph TB
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

# DIAGRAMA 2: FLUJO DE TRABAJO
FLUJO = """graph LR
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

def create_html_page(diagrama, titulo):
    """Crea página HTML para un diagrama"""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{titulo}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: white;
            font-family: Arial, sans-serif;
        }}
        .diagram-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .mermaid {{
            background: white;
        }}
    </style>
</head>
<body>
    <div class="diagram-container">
        <div class="mermaid">
{diagrama}
        </div>
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default', maxTextSize: 90000 }});
    </script>
</body>
</html>"""

def capture_to_png_via_edge(html_content, png_path):
    """Captura diagrama a PNG usando Edge"""
    
    # Crear archivo HTML temporal
    temp_html = Path('temp_diagram.html')
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    try:
        edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        if not Path(edge_exe).exists():
            edge_exe = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        
        if not Path(edge_exe).exists():
            print(f"   ❌ Edge no encontrado")
            return False
        
        # Crear screenshot con Edge
        cmd = [
            edge_exe,
            f"--headless",
            f"--disable-gpu",
            f"--screenshot={png_path.absolute().as_posix()}",
            f"file:///{temp_html.absolute().as_posix()}"
        ]
        
        print(f"   🔄 Capturando con Edge...")
        subprocess.run(cmd, capture_output=True, timeout=30, check=False)
        time.sleep(2)
        
        temp_html.unlink()  # Eliminar temporal
        
        if png_path.exists():
            print(f"   ✅ PNG generado: {png_path.name}")
            print(f"      Tamaño: {png_path.stat().st_size:,} bytes")
            return True
        else:
            print(f"   ❌ Error capturando")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        if temp_html.exists():
            temp_html.unlink()
        return False

def main():
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("🖼️  CONVERTIR DIAGRAMAS A IMÁGENES PNG")
    print("=" * 80)
    print("\n📊 Orden CORRECTO:")
    print("   1️⃣  ARQUITECTURA (OE2 → OE3)")
    print("   2️⃣  FLUJO DE TRABAJO (8 Etapas)")
    print("\n🏪 Demanda Mall: 1,412 kW promedio / 2,763 kW pico")
    print("\n" + "=" * 80)
    
    diagramas = [
        (ARQUITECTURA, "01_ARQUITECTURA_PROFESIONAL.png", "Arquitectura Profesional pvbesscar"),
        (FLUJO, "02_FLUJO_TRABAJO_DETALLADO.png", "Flujo de Trabajo (8 Etapas)"),
    ]
    
    success = 0
    
    for i, (diagrama, png_name, titulo) in enumerate(diagramas, 1):
        png_path = reports_dir / png_name
        
        print(f"\n{i}. {titulo}")
        print(f"   📁 {png_name}")
        
        html = create_html_page(diagrama, titulo)
        
        if capture_to_png_via_edge(html, png_path):
            success += 1
    
    print("\n" + "=" * 80)
    print(f"✨ Resultado: {success}/2 imágenes PNG generadas")
    print("=" * 80)
    print("\n📍 Ubicación: reports/")
    print("   ✅ 01_ARQUITECTURA_PROFESIONAL.png")
    print("   ✅ 02_FLUJO_TRABAJO_DETALLADO.png")
    print("\n🎯 Ambas con demanda Mall corregida: 1,412 kW / 2,763 kW")

if __name__ == '__main__':
    main()
