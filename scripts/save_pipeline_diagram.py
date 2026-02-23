#!/usr/bin/env python3
"""
Generate complete OE2→OE3 pipeline diagram (8 stages) as PNG.
Uses Edge headless browser to capture Mermaid rendering.
"""

import subprocess
import tempfile
from pathlib import Path

# Complete 8-stage pipeline diagram
PIPELINE_MARKUP = """graph LR
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


def create_html_for_diagram(mermaid_code: str) -> str:
    """Create HTML with Mermaid rendering and external styling."""
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline OE2→OE3 Completo (8 Etapas)</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        html, body {{
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }}
        .mermaid {{
            display: flex;
            justify-content: center;
            margin: 20px auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <h1>Pipeline OE2→OE3: 8 Etapas Completas con Métricas en Tiempo Real</h1>
    <div class="mermaid">
{mermaid_code}
    </div>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            flowchart: {{ useMaxWidth: true, htmlLabels: true }}
        }});
        mermaid.contentLoaded();
    </script>
</body>
</html>"""
    return html


def find_edge_executable():
    """Find Microsoft Edge executable on Windows."""
    import shutil
    common_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    
    # Try to find via shutil
    edge_from_path = shutil.which('msedge')
    if edge_from_path:
        return edge_from_path
    
    # Try common paths
    for path in common_paths:
        if Path(path).exists():
            return path
    
    raise FileNotFoundError("Microsoft Edge not found. Please check installation.")


def main():
    print("=" * 80)
    print("🏗️  GUARDANDO PIPELINE OE2→OE3 (8 ETAPAS)")
    print("=" * 80)
    print()

    # Create temp HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        html_content = create_html_for_diagram(PIPELINE_MARKUP)
        f.write(html_content)
        html_path = Path(f.name)

    print(f"✅ HTML temporal creado")
    print(f"   {html_path.name}")
    print()

    # Convert to PNG using Edge
    output_path = Path('reports') / '03_PIPELINE_OE2_OE3_COMPLETO.png'
    output_path.parent.mkdir(exist_ok=True)

    print("🔄 Capturando PNG con Edge...")
    try:
        edge_exe = find_edge_executable()
        # Use check=False to avoid raising on non-zero exit
        result = subprocess.run(
            [
                edge_exe,
                '--headless=new',
                '--disable-gpu',
                f'--screenshot={str(output_path)}',
                f'file:///{html_path.absolute()}'
            ],
            capture_output=True,
            timeout=30
        )
        
        # Wait a bit for file to be written
        import time
        time.sleep(2)
        
        if not output_path.exists():
            print(f"❌ Edge execution output:")
            print(f"   stdout: {result.stdout.decode('utf-8', errors='ignore')}")
            print(f"   stderr: {result.stderr.decode('utf-8', errors='ignore')}")
            raise FileNotFoundError(f"PNG not generated at {output_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Get file size
    if output_path.exists():
        file_size_kb = output_path.stat().st_size / 1024

        print()
        print("✅ PNG GENERADO")
        print(f"   📍 {output_path.name}")
        print(f"   Tamaño: {file_size_kb:.1f} KB")
        print()

        print("✨ Pipeline OE2→OE3 guardado en reports/")
        print("   ✓ 8 etapas completas: Entrada → Carga → Procesamiento → Entorno → Training → Checkpoints → Métricas → Documento")
        print("   ✓ 3 agentes RL: SAC, PPO, A2C")
        print("   ✓ Reward function incluido: 0.35 CO₂ + 0.30 EV + 0.20 Solar + 0.10 Cost + 0.05 Grid")
        print("   ✓ Mall load: 1,412 kW promedio / 2,763 kW pico / 12.37M kWh/año")
        print("   ✓ Datos reales desde checkpoints y artefactos OE2")
        print()
    else:
        print(f"❌ PNG file not found at {output_path}")
        print("   Ensure Edge is properly installed and accessible.")

    # Cleanup
    html_path.unlink()


if __name__ == '__main__':
    main()
