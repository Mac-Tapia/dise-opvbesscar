#!/usr/bin/env python3
"""
Servidor Web Local - Accede a resultados de Docker en navegador
URL: http://localhost:8000
"""

import os
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser

# Crear índice HTML
INDEX_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐳 Docker Results - Iquitos EV Smart Charging</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }
        .whale-icon {
            font-size: 3em;
            animation: float 3s ease-in-out infinite;
        }
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }
        .url-box {
            background: rgba(255,255,255,0.1);
            border: 2px solid white;
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            font-family: 'Courier New', monospace;
            font-size: 1.2em;
            margin-top: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .card:hover { transform: translateY(-5px); }
        .card h2 {
            color: #2a5298;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card a {
            display: inline-block;
            background: #2a5298;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            margin-top: 10px;
            font-weight: bold;
            transition: background 0.3s;
        }
        .card a:hover { background: #1e3c72; }
        .result-type {
            font-size: 0.9em;
            color: #666;
            margin-top: 10px;
        }
        .badge {
            display: inline-block;
            background: #FFD700;
            color: #333;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            margin-right: 5px;
        }
        .info {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .info h2 { color: #2a5298; margin-bottom: 15px; }
        .info p { color: #555; line-height: 1.8; margin-bottom: 10px; }
        .path-box {
            background: #f0f4f8;
            border-left: 4px solid #2a5298;
            padding: 12px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
            color: #2a5298;
        }
        footer { text-align: center; color: white; margin-top: 40px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><span class="whale-icon">🐳</span> Docker Results Portal</h1>
            <p>Iquitos EV Smart Charging Infrastructure - OE3 RL Training</p>
            <div class="url-box">
                📍 Estás en: <strong>http://localhost:8000</strong>
            </div>
        </header>

        <div class="info">
            <h2>📊 Resultados del Entrenamiento</h2>
            <p><strong>Estado:</strong> ✅ Completado exitosamente</p>
            <p><strong>Agentes entrenados:</strong> SAC (🥇), PPO (🥈), A2C (🥉), Baseline</p>
            <p><strong>GPU:</strong> NVIDIA CUDA 12.7</p>
            <p><strong>Mejor desempeño:</strong> <span class="badge">SAC - 7,547,021 kg CO₂</span></p>
            <p><strong>Ubicación física:</strong></p>
            <div class="path-box">d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\</div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>📍 Mapa de Ejecución</h2>
                <p>Visualiza la arquitectura completa de Docker y dónde corrió todo.</p>
                <a href="DOCKER_EXECUTION_MAP.html" target="_blank">Ver Mapa</a>
                <div class="result-type">🔗 Interfaz visual interactiva</div>
            </div>

            <div class="card">
                <h2>📈 Reporte OE3</h2>
                <p>Análisis detallado de resultados CO₂ con tabla comparativa de agentes.</p>
                <a href="REPORTE_OE3.html" target="_blank">Ver Reporte</a>
                <div class="result-type">📊 Tabla interactiva</div>
            </div>

            <div class="card">
                <h2>🥇 Resultados SAC</h2>
                <p>Mejor agente RL - Soft Actor-Critic con máxima entropía.</p>
                <a href="simulations/sac_results.json" target="_blank">Ver JSON</a>
                <a href="simulations/timeseries_SAC.csv" target="_blank">Ver CSV</a>
                <div class="result-type">7,547,021 kg CO₂ (1.49% reducción)</div>
            </div>

            <div class="card">
                <h2>🥈 Resultados PPO</h2>
                <p>Agente Proximal Policy Optimization.</p>
                <a href="simulations/ppo_results.json" target="_blank">Ver JSON</a>
                <a href="simulations/timeseries_PPO.csv" target="_blank">Ver CSV</a>
                <div class="result-type">7,578,734 kg CO₂</div>
            </div>

            <div class="card">
                <h2>🥉 Resultados A2C</h2>
                <p>Actor-Critic Asincrónico.</p>
                <a href="simulations/a2c_results.json" target="_blank">Ver JSON</a>
                <a href="simulations/timeseries_A2C.csv" target="_blank">Ver CSV</a>
                <div class="result-type">7,615,072 kg CO₂</div>
            </div>

            <div class="card">
                <h2>📊 Resumen Simulación</h2>
                <p>Datos consolidados de todos los agentes y comparativa.</p>
                <a href="simulations/simulation_summary.json" target="_blank">Ver JSON</a>
                <a href="simulations/co2_comparison.md" target="_blank">Ver Markdown</a>
                <div class="result-type">33.5 KB - Datos completos</div>
            </div>

            <div class="card">
                <h2>🔍 Traces Detallados</h2>
                <p>Ejecución paso a paso de cada agente (8760 horas).</p>
                <a href="simulations/trace_SAC.csv" target="_blank">SAC Trace</a>
                <a href="simulations/trace_PPO.csv" target="_blank">PPO Trace</a>
                <a href="simulations/trace_A2C.csv" target="_blank">A2C Trace</a>
                <div class="result-type">~50 MB cada uno</div>
            </div>

            <div class="card">
                <h2>📁 Carpeta Completa</h2>
                <p>Accede a todos los archivos generados.</p>
                <a href="simulations/" target="_blank">Abrir Carpeta</a>
                <div class="result-type">15 archivos | 109.2 MB total</div>
            </div>
        </div>

        <div class="info">
            <h2>🖇️ Acceso Local</h2>
            <p><strong>Ruta en Windows:</strong></p>
            <div class="path-box">d:\\diseñopvbesscar\\outputs\\oe3\\</div>
            <p style="margin-top: 20px;"><strong>Comandos útiles en PowerShell:</strong></p>
            <div class="path-box">
                # Listar archivos<br>
                dir d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\<br>
                <br>
                # Ver JSON en terminal<br>
                Get-Content d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\simulation_summary.json
            </div>
        </div>

        <footer>
            <p>✅ Servidor ejecutándose en http://localhost:8000</p>
            <p>© 2026 Iquitos EV Smart Charging Infrastructure</p>
        </footer>
    </div>
</body>
</html>
"""

def start_server():
    """Inicia servidor HTTP local"""
    os.chdir(Path("d:/diseñopvbesscar/outputs/oe3"))
    
    # Crear índice
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(INDEX_HTML)
    
    port = 8000
    server = HTTPServer(("localhost", port), SimpleHTTPRequestHandler)
    
    print("\n" + "="*80)
    print("🌐 SERVIDOR WEB LOCAL INICIADO".center(80))
    print("="*80)
    print(f"\n📍 Accede en tu navegador:\n   http://localhost:{port}\n")
    print(f"📁 Sirviendo archivos desde:\n   d:\\diseñopvbesscar\\outputs\\oe3\\\n")
    print("✅ Presiona Ctrl+C para detener el servidor\n")
    print("="*80 + "\n")
    
    # Abrir navegador automáticamente
    webbrowser.open(f"http://localhost:{port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("⏹️  Servidor detenido".center(80))
        print("="*80)
        server.server_close()

if __name__ == "__main__":
    start_server()
