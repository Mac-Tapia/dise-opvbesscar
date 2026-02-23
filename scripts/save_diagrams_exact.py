"""
Guarda los dos diagramas Mermaid renderizados exactamente como están
pvbesscar v7.1 - Exportador de Diagramas sin cambios
"""

from pathlib import Path

# Diagrama 1: Arquitectura - TAL COMO SE RENDERIZÓ
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

# Diagrama 2: Flujo de Trabajo - TAL COMO SE RENDERIZÓ
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

def main():
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    
    # Guardar diagramas como archivos .mmd (sin cambios)
    arq_mmd = reports_dir / '01_ARQUITECTURA_PROYECTO.mmd'
    flujo_mmd = reports_dir / '02_FLUJO_TRABAJO_DETALLADO.mmd'
    
    with open(arq_mmd, 'w', encoding='utf-8') as f:
        f.write(DIAGRAMA_ARQUITECTURA)
    
    with open(flujo_mmd, 'w', encoding='utf-8') as f:
        f.write(DIAGRAMA_FLUJO)
    
    print("=" * 80)
    print("✅ DIAGRAMAS MERMAID GUARDADOS - EXACTAMENTE TAL COMO SE RENDERIZARON")
    print("=" * 80)
    print(f"\n📄 Archivo 1: reports/01_ARQUITECTURA_PROYECTO.mmd")
    print(f"   ├─ Arquitectura General (OE2 → OE3)")
    print(f"   ├─ Infraestructura: 4,050 kWp solar | Mall 1,412 kW avg")
    print(f"   ├─ BESS: 2,000 kWh | 19 Chargers (38 sockets)")
    print(f"   └─ Agentes: SAC/PPO/A2C con resultados CO₂ reales")
    
    print(f"\n📄 Archivo 2: reports/02_FLUJO_TRABAJO_DETALLADO.mmd")
    print(f"   ├─ 8 Etapas de ejecución completas")
    print(f"   ├─ ETAPA 1: Inputs (Mall/Solar/EV/Config)")
    print(f"   ├─ ETAPA 2-4: Load, Build, Environment")
    print(f"   ├─ ETAPA 5-6: Reward & Training")
    print(f"   ├─ ETAPA 7-8: Evaluation & Report")
    print(f"   └─ Con archivos y directorios específicos")
    
    print("\n" + "=" * 80)
    print("📌 PARA CONVERTIR A PDF:")
    print("=" * 80)
    print("\n✨ Opción 1 - Mermaid Live (RECOMENDADO):")
    print("  1. Abre: https://mermaid.live")
    print("  2. Proyecto abierto en navegador: Ctrl+Shift+S")
    print("  3. Selecciona el HTML desde localhost:8000 en pestaña abierta")
    print("  4. O copia contenido manual de los .mmd files")
    print("  5. Exporta → Download as PDF")
    
    print("\n⚙️  Opción 2 - Mermaid CLI:")
    print("  npm install -g @mermaid-js/mermaid-cli")
    print("  mmdc -i reports/01_ARQUITECTURA_PROYECTO.mmd -o reports/01_ARQUITECTURA_PROYECTO.pdf")
    print("  mmdc -i reports/02_FLUJO_TRABAJO_DETALLADO.mmd -o reports/02_FLUJO_TRABAJO_DETALLADO.pdf")
    
    print("\n🌐 Opción 3 - Navegador (desde el HTML abierto):")
    print("  1. Pestaña abierta: http://localhost:8000/ARQUITECTURA_DIAGRAMA_INTERACTIVO.html")
    print("  2. Presiona: Ctrl+P")
    print("  3. Guardar como PDF")
    
    print("\n" + "=" * 80)
    print("✨ Archivos guardados sin cambios - Listos para conversión a PDF")
    print("=" * 80)

if __name__ == '__main__':
    main()
