#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera diagramas de arquitectura y flujo de trabajo como archivos SVG/HTML
Los diagramas Mermaid se convierten a imágenes usando mermaid-cli o se exportan como HTML
"""

import json
from pathlib import Path
from datetime import datetime

# Diagramas Mermaid
DIAGRAMA_ARQUITECTURA = """graph TB
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

DIAGRAMA_FLUJO = """graph LR
    subgraph Input["📥 ENTRADA: ARTEFACTOS OE2"]
        PVF["data/oe2/Generacionsolar/<br/>pv_generation.csv"]
        BESSF["data/oe2/BESS/<br/>bess_ano_2024.csv"]
        CHGF["data/oe2/chargers/<br/>chargers_ev_*.csv"]
        EVDF["data/oe2/EV_Demand/<br/>demand_profiles.csv"]
    end
    
    subgraph Load["🔄 ETAPA 1: CARGA Y VALIDACIÓN"]
        OE2Val["src/dimensionamiento/oe2/<br/>Modules:<br/>- solar_pvlib.py<br/>- chargers.py<br/>- bess.py<br/>- data_loader.py"]
        Check["Validaciones Críticas:<br/>✓ Solar: 8,760 filas horarias<br/>✓ NO 15-min data<br/>✓ BESS: 6-phase logic<br/>✓ Chargers: 19×2=38 sockets<br/>✓ EV: queue model"]
        
        PVF -->|Parse CSV| OE2Val
        BESSF -->|Parse CSV| OE2Val
        CHGF -->|Parse JSON| OE2Val
        EVDF -->|Parse| OE2Val
        OE2Val -->|Validate| Check
    end
    
    subgraph Process["⚙️ ETAPA 2: PROCESAMIENTO OE2→OE3"]
        Builder["src/dataset_builder_citylearn/<br/>dataset_builder.py:<br/>- Load OE2 artifacts<br/>- Build 394-dim vector<br/>- Create reward weights<br/>- Normalize observations"]
        
        Interop["Interoperabilidad:<br/>data/interim/oe2/<br/>- Solar prep<br/>- BESS dispatch<br/>- Charger schedule<br/>- EV demand queue"]
        
        Check -->|OE2 artifacts OK| Builder
        Builder -->|Transform| Interop
    end
    
    subgraph Env["🌍 ETAPA 3: ENTORNO RL"]
        CL["CityLearn v2 Environment<br/>- 8,760 timesteps<br/>- 1h per step<br/>- Multi-building support"]
        
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
        Val["Comparison Report:<br/>Metrics extraction<br/>- Parse JSON<br/>- Annualize values<br/>- Calculate %reductions<br/>- vs Baseline"]
        
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

DIAGRAMA_ESTRUCTURA = """graph TB
    ROOT["📦 diseñopvbesscar/<br/>root project directory"]
    
    subgraph SRC["📁 src/"]
        OE2["📂 dimensionamiento/oe2/<br/>INFRAESTRUCTURA<br/>├── data_loader.py<br/>├── chargers.py<br/>├── solar_pvlib.py<br/>├── bess.py<br/>├── balance_energetico/<br/>│   └── balance.py<br/>└── generacionsolar/"]
        
        AGENTS["📂 agents/<br/>RL AGENTS<br/>├── sac.py<br/>├── ppo_sb3.py<br/>├── a2c_sb3.py<br/>├── no_control.py<br/>└── agent_utils.py"]
        
        DATASET["📂 dataset_builder_citylearn/<br/>DATASET & REWARDS<br/>├── dataset_builder.py<br/>├── rewards.py<br/>├── observation_wrapper.py<br/>└── action_bounds.py"]
        
        UTILS["📂 utils/<br/>SHARED CODE<br/>├── logging.py<br/>├── time.py<br/>├── series.py<br/>├── validation.py<br/>└── agent_utils.py"]
        
        ROOT --> SRC
        SRC --> OE2
        SRC --> AGENTS
        SRC --> DATASET
        SRC --> UTILS
    end
    
    subgraph DATA["📁 data/"]
        OE2Data["📂 oe2/<br/>OE2 ARTIFACTS<br/>├── Generacionsolar/<br/>│   └── pv_generation_*.csv<br/>│       (8,760 hourly rows)<br/>├── BESS/<br/>│   └── bess_ano_2024.csv<br/>├── chargers/<br/>│   └── chargers_ev_*.csv<br/>├── EV_Demand/<br/>│   └── demand_profiles.csv<br/>└── MALL/<br/>    └── mall_demand_24h.csv"]
        
        Interim["📂 interim/oe2/<br/>PROCESSED OE2<br/>├── solar/pv_*.csv<br/>│   (validated & normalized)<br/>├── bess/bess_processed.csv<br/>├── chargers/chargers_*.json<br/>└── ev/ev_demand_queue.json"]
        
        ROOT --> DATA
        DATA --> OE2Data
        DATA --> Interim
    end
    
    subgraph CHECKPOINTS["📁 checkpoints/"]
        SACC_["📂 SAC/checkpoint_agent<br/>├── sac_model_*.zip<br/>│   (policy + value nets)<br/>├── sac_model_final_*.zip<br/>│   (best model)<br/>└── metadata.json"]
        
        PPOC_["📂 PPO/checkpoint_agent<br/>├── ppo_model_*.zip<br/>└── metadata.json"]
        
        A2CC_["📂 A2C/checkpoint_agent<br/>├── a2c_model_*.zip<br/>└── metadata.json"]
        
        ROOT --> CHECKPOINTS
        CHECKPOINTS --> SACC_
        CHECKPOINTS --> PPOC_
        CHECKPOINTS --> A2CC_
    end
    
    subgraph OUTPUTS["📁 outputs/"]
        SACO["📂 sac_training/<br/>├── result_sac.json<br/>│   (18,621 lines)<br/>│   ├─ training metrics<br/>│   └─ validation metrics<br/>├── trace_sac.csv<br/>└── logs/"]
        
        PPOO["📂 ppo_training/<br/>├── ppo_training_summary.json<br/>├── trace_ppo.csv<br/>└── logs/"]
        
        A2CO["📂 a2c_training/<br/>├── result_a2c.json<br/>├── trace_a2c.csv<br/>└── logs/"]
        
        BASEL["📂 baselines/<br/>├── with_solar/<br/>│   └── baseline_comparison.csv<br/>└── without_solar/<br/>    └── baseline_comparison.csv"]
        
        ROOT --> OUTPUTS
        OUTPUTS --> SACO
        OUTPUTS --> PPOO
        OUTPUTS --> A2CO
        OUTPUTS --> BASEL
    end
    
    subgraph SCRIPTS["📁 scripts/"]
        GEN["generate_oe3_detailed_report.py<br/>├─ Load checkpoint JSONs<br/>├─ Extract dynamic values<br/>├─ Build 41 acápites<br/>└─ Generate .docx"]
        
        TRAIN["train/<br/>├── train_sac.py<br/>├── train_ppo_multiobjetivo.py<br/>└── train_a2c.py"]
        
        VAL["Validation scripts<br/>├── verify_structure.py<br/>├── validate_checkpoints.py<br/>└── validate_values.py"]
        
        ROOT --> SCRIPTS
        SCRIPTS --> GEN
        SCRIPTS --> TRAIN
        SCRIPTS --> VAL
    end
    
    subgraph CONFIG["📁 configs/"]
        YAML_["default.yaml<br/>├─ learning_rates<br/>├─ network_sizes<br/>├─ reward_weights<br/>├─ env_params<br/>└─ training_steps"]
        
        ROOT --> CONFIG
        CONFIG --> YAML_
    end
    
    subgraph REPORTS["📁 reports/"]
        DOCX["OE3_INFORME_DETALLADO_<br/>CON_DATOS_REALES.docx<br/>✅ 100% Completitud<br/>• 41 acápites<br/>• 8 tablas<br/>• 15-18 páginas<br/>• Datos reales<br/>• THESIS READY"]
        
        ROOT --> REPORTS
        REPORTS --> DOCX
    end
    
    subgraph ENV_INFO["⚙️ CONFIGURACIÓN PROYECTO"]
        REQ["requirements.txt<br/>├─ stable-baselines3≥2.0<br/>├─ gymnasium≥0.27<br/>├─ pandas, numpy<br/>├─ torch (optional)<br/>├─ pyyaml<br/>└─ python-docx"]
        
        GITIGNORE[".gitignore<br/>├─ .venv/<br/>├─ __pycache__/<br/>├─ checkpoints/<br/>(muy large)<br/>└─ outputs/ (temp)"]
        
        GITHUB["🔗 GitHub Actions<br/>Branch: smartcharger<br/>Default: main<br/>Repo: Mac-Tapia/<br/>dise-opvbesscar"]
        
        ROOT --> REQ
        ROOT --> GITIGNORE
        ROOT --> GITHUB
    end
    
    style SRC fill:#d4edda
    style DATA fill:#fff3cd
    style CHECKPOINTS fill:#e7d4f5
    style OUTPUTS fill:#f8d7da
    style SCRIPTS fill:#cce5ff
    style CONFIG fill:#d1ecf1
    style REPORTS fill:#c3e6cb
    style ENV_INFO fill:#f0f0f0"""


def generate_html_page(diagrams: dict) -> str:
    """Genera HTML con todos los diagramas usando mermaid.js"""
    
    html_template = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arquitectura y Flujo de Trabajo - pvbesscar</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .diagram-section {
            padding: 40px;
            border-bottom: 1px solid #eee;
        }
        
        .diagram-section:last-child {
            border-bottom: none;
        }
        
        .diagram-title {
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .diagram-description {
            color: #666;
            margin-bottom: 20px;
            font-size: 0.95em;
            line-height: 1.6;
        }
        
        .mermaid {
            display: flex;
            justify-content: center;
            overflow-x: auto;
            background: #f9f9f9;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #eee;
        }
        
        .footer {
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
        
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
            }}
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .diagram-title {{
                font-size: 1.3em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ Arquitectura y Flujo de Trabajo</h1>
            <p>Proyecto pvbesscar - Optimización de Carga EV con RL</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Generado: {timestamp}</p>
        </div>
        
        <div class="diagram-section">
            <div class="diagram-title">📊 1. ARQUITECTURA GENERAL (OE2 → OE3)</div>
            <div class="diagram-description">
                Muestra el pipeline completo: Infraestructura OE2 (Solar, BESS, Cargadores) → 
                Validación de datos → CityLearn v2 Environment → 3 Agentes RL (SAC, PPO, A2C) → 
                Guardado de checkpoints → Export de métricas → Validación → Generación de documento tesis
            </div>
            <div class="mermaid">{diagrama_arquitectura}</div>
        </div>
        
        <div class="diagram-section">
            <div class="diagram-title">🔄 2. FLUJO DE TRABAJO DETALLADO (8 ETAPAS)</div>
            <div class="diagram-description">
                Pipeline de 8 etapas desde entrada de artefactos OE2 hasta salida de documento tesis:
                Entrada → Carga y Validación → Procesamiento OE2↔OE3 → Entorno RL → 
                Entrenamiento → Guardado → Export Métricas → Comparación → Generación Documento
            </div>
            <div class="mermaid">{diagrama_flujo}</div>
        </div>
        
        <div class="diagram-section">
            <div class="diagram-title">📁 3. ESTRUCTURA DE DIRECTORIOS</div>
            <div class="diagram-description">
                Organización del código fuente, datos, modelos entrenados, métricas y resultados.
                Incluye: src/ (código), data/ (artifacts), checkpoints/ (modelos), 
                outputs/ (métricas), scripts/ (utilidades), configs/ (yaml), reports/ (resultados)
            </div>
            <div class="mermaid">{diagrama_estructura}</div>
        </div>
        
        <div class="footer">
            <p>🔗 Repositorio: <strong>Mac-Tapia/dise-opvbesscar</strong> (rama: smartcharger)</p>
            <p>Para ver en PDF, usa: Ctrl+P (Imprimir) → Guardar como PDF</p>
        </div>
    </div>
    
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
        mermaid.contentLoaders = [];
    </script>
</body>
</html>
"""
    
    timestamp = datetime.now().strftime("%d de %B de %Y a las %H:%M")
    
    html_content = html_template.format(
        timestamp=timestamp,
        diagrama_arquitectura=diagrams['arquitectura'],
        diagrama_flujo=diagrams['flujo'],
        diagrama_estructura=diagrams['estructura']
    )
    
    return html_content


def main():
    """Genera los archivos de diagrama"""
    
    # Crear carpeta reports si no existe
    reports_dir = Path('reports')
    reports_dir.mkdir(exist_ok=True)
    
    diagrams = {
        'arquitectura': DIAGRAMA_ARQUITECTURA,
        'flujo': DIAGRAMA_FLUJO,
        'estructura': DIAGRAMA_ESTRUCTURA
    }
    
    # Generar HTML
    html_content = generate_html_page(diagrams)
    html_path = reports_dir / 'ARQUITECTURA_DIAGRAMA_INTERACTIVO.html'
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Diagrama HTML generado: {html_path}")
    print(f"\n📖 Para convertir a PDF:")
    print(f"   1. Abre en navegador: {html_path}")
    print(f"   2. Presiona Ctrl+P (Imprimir)")
    print(f"   3. Selecciona 'Guardar como PDF'")
    print(f"   4. Guarda en: reports/ARQUITECTURA_DIAGRAMA.pdf")
    
    # Generar también archivo JSON con metadatos
    metadata = {
        'project': 'pvbesscar',
        'description': 'Arquitectura y Flujo de Trabajo',
        'timestamp': datetime.now().isoformat(),
        'diagrams': {
            'arquitectura': 'Pipeline general OE2→OE3',
            'flujo': '8 etapas de ejecución',
            'estructura': 'Organización de directorios'
        },
        'files': {
            'html': str(html_path),
            'instructions': 'Convertir HTML a PDF usando navegador (Ctrl+P → Guardar como PDF)'
        }
    }
    
    metadata_path = reports_dir / 'diagrams_metadata.json'
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Metadatos guardados: {metadata_path}")
    print(f"\n✅ Los archivos están listos en: {reports_dir}/")


if __name__ == '__main__':
    main()
