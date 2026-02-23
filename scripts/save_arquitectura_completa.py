"""
Guarda el DIAGRAMA ARQUITECTURA PROFESIONAL COMPLETO como PNG
pvbesscar v7.1 - Diagrama Profesional OE2-OE3 Completo
"""

from pathlib import Path
import subprocess
import time

# ARQUITECTURA PROFESIONAL COMPLETA - CORRECTLY FORMATTED
ARQUITECTURA_COMPLETA = """graph TB
    subgraph OE2["📦 FASE OE2: DIMENSIONAMIENTO (Infraestructura)"]
        PV["☀️ Paneles Solares<br/>4,050 kWp<br/>PVGIS 8,760h"]
        BESS["🔋 Batería<br/>2,000 kWh / 400 kW<br/>6 Fases Operación"]
        CHG["🔌 Cargadores<br/>19 chargers × 2 sockets<br/>38 puntos de carga<br/>7.4 kW Mode 3"]
        MALL["🏢 Demanda Mall<br/>PROMEDIO: 1,412 kW<br/>PICO: 2,763 kW<br/>ANUAL: 12,368,653 kWh"]
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
        ObsSpace["📋 Observation Space<br/>- Solar W/m²<br/>- BESS SOC %<br/>- 38 socket states<br/>- Time features<br/>Total: 394 dimensions"]
        ActSpace["🎮 Action Space<br/>Continuous [0,1]<br/>1 BESS + 38 sockets<br/>39 total actions"]
        
        Builder -->|Init env| Env
        Env -->|Provides| ObsSpace
        Env -->|Accepts| ActSpace
    end
    
    subgraph Training["🤖 ENTRENAMIENTO RL - 3 AGENTES"]
        SAC["🏆 SAC<br/>Off-Policy<br/>Soft Actor-Critic<br/>stable-baselines3"]
        PPO["📈 PPO<br/>On-Policy<br/>Proximal Policy<br/>stable-baselines3"]
        A2C["⚡ A2C<br/>On-Policy<br/>Actor-Critic<br/>stable-baselines3"]
        
        Reward["Reward Function<br/>w_CO2=0.35 PRIMARY<br/>w_EV=0.30 SECONDARY<br/>w_solar=0.20<br/>w_cost=0.10<br/>w_grid=0.05"]
        
        ObsSpace -->|87,600 steps| SAC
        ObsSpace -->|10 episodios| PPO
        ObsSpace -->|10 años| A2C
        Reward -->|Guide policy| SAC
        Reward -->|Guide policy| PPO
        Reward -->|Guide policy| A2C
    end
    
    subgraph Checkpoints["💾 GUARDADO DE MODELOS"]
        SACC["checkpoints/SAC/<br/>sac_model_*.zip"]
        PPOC["checkpoints/PPO/<br/>ppo_model_*.zip"]
        A2CC["checkpoints/A2C/<br/>a2c_model_*.zip"]
        
        SAC -->|Save| SACC
        PPO -->|Save| PPOC
        A2C -->|Save| A2CC
    end
    
    subgraph Results["📊 RESULTADOS Y METRICAS"]
        SACJ["outputs/sac/<br/>result_sac.json"]
        PPOJ["outputs/ppo/<br/>ppo_summary.json"]
        A2CJ["outputs/a2c/<br/>result_a2c.json"]
        
        SACC -->|Export| SACJ
        PPOC -->|Export| PPOJ
        A2CC -->|Export| A2CJ
    end
    
    subgraph Validation["✅ VALIDACIÓN"]
        Val["Comparison Metrics<br/>- CO2 avoided kg/año<br/>- Solar utilization %<br/>- Grid import kWh<br/>- EV satisfaction %"]
        
        SACJ -->|Parse| Val
        PPOJ -->|Parse| Val
        A2CJ -->|Parse| Val
    end
    
    subgraph Thesis["📄 DOCUMENTO TESIS"]
        Report["generate_oe3_report.py<br/>Dynamic extraction<br/>41 acápites completos"]
        
        Val -->|Real data| Report
        Report -->|Generate| DocX["📖 OE3_INFORME_DETALLADO<br/>✅ THESIS READY"]
    end
    
    style OE2 fill:#fff3cd
    style Pipeline fill:#d1ecf1
    style CityLearn fill:#d4edda
    style Training fill:#cce5ff
    style Checkpoints fill:#e7d4f5
    style Results fill:#f8d7da
    style Validation fill:#d1ecf1
    style Thesis fill:#c3e6cb"""

def create_html_for_diagram(diagram, titulo):
    """Crea HTML para renderizar el diagrama"""
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
{diagram}
        </div>
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default', maxTextSize: 90000 }});
    </script>
</body>
</html>"""

def main():
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("🏗️  GUARDANDO ARQUITECTURA PROFESIONAL COMPLETA")
    print("=" * 80)
    
    # Crear HTML temporal
    html_content = create_html_for_diagram(ARQUITECTURA_COMPLETA, "Arquitectura Completa pvbesscar")
    html_path = reports_dir / '_ARQUITECTURA_TEMP.html'
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ HTML temporal creado")
    print(f"   {html_path.name}")
    
    # Convertir a PNG usando Edge
    png_path = reports_dir / '01_ARQUITECTURA_PROFESIONAL_COMPLETA.png'
    
    edge_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not Path(edge_exe).exists():
        edge_exe = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    
    if Path(edge_exe).exists():
        print(f"\n🔄 Capturando PNG con Edge...")
        
        cmd = [
            edge_exe,
            f"--headless",
            f"--disable-gpu",
            f"--screenshot={png_path.absolute().as_posix()}",
            f"--window-size=1920,1080",
            f"file:///{html_path.absolute().as_posix()}"
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            time.sleep(2)
            
            if png_path.exists():
                size_kb = png_path.stat().st_size / 1024
                print(f"\n✅ PNG GENERADO")
                print(f"   📍 {png_path.name}")
                print(f"   Tamaño: {size_kb:.1f} KB")
                
                # Limpiar HTML temporal
                html_path.unlink()
                print(f"\n✨ Arquitectura Profesional Completa guardada en reports/")
                print("   ✓ Mall: 1,412 kW promedio / 2,763 kW pico")
                print("   ✓ 7 fases completas: OE2 → Pipeline → CityLearn → Training → Checkpoints → Results → Thesis")
                print("   ✓ 3 agentes RL: SAC, PPO, A2C")
                print("   ✓ Stack tecnológico incluido")
                
                return True
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return False

if __name__ == '__main__':
    main()
