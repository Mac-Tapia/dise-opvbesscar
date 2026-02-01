#!/usr/bin/env python3.11
"""
PVBESSCAR Dashboard - Con WebSocket Real-Time
Conectado a FastAPI para datos en vivo
"""

from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuración
API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PVBESSCAR Dashboard Pro</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .container {
            max-width: 1800px;
            margin: 0 auto;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }
        
        header h1 {
            font-size: 32px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(255,255,255,0.2);
            padding: 10px 15px;
            border-radius: 20px;
            font-size: 14px;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #00ff88;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            border-left: 5px solid #667eea;
        }
        
        .card.live {
            border-left-color: #f39c12;
            background: linear-gradient(135deg, #fff 0%, #fffacd 100%);
        }
        
        .card.success {
            border-left-color: #27ae60;
        }
        
        .card.danger {
            border-left-color: #e74c3c;
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #eee;
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            font-weight: 500;
            color: #555;
        }
        
        .metric-value {
            font-size: 20px;
            font-weight: bold;
            color: #667eea;
            min-width: 120px;
            text-align: right;
        }
        
        .update-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #f39c12;
            border-radius: 50%;
            margin-left: 10px;
            animation: pulse 1s infinite;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background-color: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }
        
        .objectives-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        
        .objective-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .objective-value {
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .objective-label {
            font-size: 12px;
            opacity: 0.9;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .chart-container {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .chart-container h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 16px;
        }
        
        canvas {
            max-height: 300px;
        }
        
        .agent-panel {
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .agent-action {
            font-size: 24px;
            font-weight: bold;
            display: inline-block;
            background: rgba(0,0,0,0.2);
            padding: 10px 20px;
            border-radius: 6px;
            margin: 10px 0;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102,126,234,0.4);
        }
        
        .btn-action {
            background: #27ae60;
            color: white;
            font-size: 12px;
            padding: 8px 15px;
        }
        
        .btn-action:hover {
            background: #229954;
        }
        
        .btn-action.charge {
            background: #3498db;
        }
        
        .btn-action.discharge {
            background: #e74c3c;
        }
        
        .timestamp {
            font-size: 11px;
            color: #999;
            margin-top: 10px;
            text-align: right;
        }
        
        .connection-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            padding: 8px 12px;
            background: rgba(39, 174, 96, 0.2);
            border-radius: 4px;
            color: #27ae60;
        }
        
        .connection-status.disconnected {
            background: rgba(231, 76, 60, 0.2);
            color: #e74c3c;
        }
        
        .live-indicator {
            font-size: 10px;
            color: #f39c12;
            font-weight: bold;
            animation: blink 1s infinite;
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>⚡ PVBESSCAR Pro Dashboard</h1>
                <p style="font-size: 14px; opacity: 0.9;">Sistema Inteligente de Gestión Energética | Agente RL en Tiempo Real</p>
            </div>
            <div class="status-badge">
                <span class="status-dot"></span>
                <span id="wsStatus">Conectando...</span>
            </div>
        </header>
        
        <!-- Objetivos -->
        <div class="objectives-grid" id="objectivesContainer">
            <div class="objective-card">
                <div class="objective-label">Reducción Costo</div>
                <div class="objective-value" id="costObj">0%</div>
                <div class="objective-label">Objetivo: 75%</div>
            </div>
            <div class="objective-card">
                <div class="objective-label">Reducción CO2</div>
                <div class="objective-value" id="co2Obj">0%</div>
                <div class="objective-label">Objetivo: 50%</div>
            </div>
            <div class="objective-card">
                <div class="objective-label">Disponibilidad</div>
                <div class="objective-value" id="availObj">95%</div>
                <div class="objective-label">Objetivo: 99%</div>
            </div>
            <div class="objective-card">
                <div class="objective-label">Convergencia IA</div>
                <div class="objective-value" id="convObj">0%</div>
                <div class="objective-label">Objetivo: 100%</div>
            </div>
        </div>
        
        <!-- Panel del Agente -->
        <div class="agent-panel">
            <h2 style="margin-bottom: 15px;">🤖 Agente RL - Control en Vivo</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px;">
                <div>
                    <div style="font-size: 12px; opacity: 0.9;">Acción Actual</div>
                    <div class="agent-action" id="agentAction">IDLE</div>
                </div>
                <div>
                    <div style="font-size: 12px; opacity: 0.9;">Episodios</div>
                    <div class="agent-action" id="episodes">0</div>
                </div>
                <div>
                    <div style="font-size: 12px; opacity: 0.9;">Recompensa</div>
                    <div class="agent-action" id="reward">€0</div>
                </div>
                <div>
                    <div style="font-size: 12px; opacity: 0.9;">Convergencia</div>
                    <div class="agent-action" id="convergence">0%</div>
                </div>
            </div>
            <div class="controls">
                <button class="btn-action charge" onclick="controlAgent('CHARGE')">⬆️ Cargar</button>
                <button class="btn-action discharge" onclick="controlAgent('DISCHARGE')">⬇️ Descargar</button>
                <button class="btn-action" onclick="controlAgent('IDLE')">➡️ Reposo</button>
                <button class="btn-primary" onclick="getAgentStatus()" style="margin-left: auto;">🔄 Actualizar</button>
            </div>
        </div>
        
        <!-- Métricas Principal -->
        <div class="grid">
            <div class="card live">
                <h2>⚡ Energía en Vivo</h2>
                <div class="metric">
                    <span class="metric-label">Consumo <span class="update-indicator"></span></span>
                    <span class="metric-value" id="consumo">0.0 kW</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Generación Solar</span>
                    <span class="metric-value" id="solar">0.0 kW</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Batería (SOC)</span>
                    <span class="metric-value" id="bateria">0%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="batteryBar" style="width: 50%"></div>
                </div>
                <div class="metric">
                    <span class="metric-label">Grid Import</span>
                    <span class="metric-value" id="grid">0.0 kW</span>
                </div>
                <div class="timestamp" id="energyTime"></div>
            </div>
            
            <div class="card">
                <h2>💰 Costos</h2>
                <div class="metric">
                    <span class="metric-label">Precio Actual</span>
                    <span class="metric-value" id="priceKwh">€0.00/kWh</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Costo Hoy</span>
                    <span class="metric-value" id="costToday">€0.00</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Costo Total</span>
                    <span class="metric-value" id="costTotal">€0.00</span>
                </div>
                <div class="metric">
                    <span class="metric-label">CO2 Evitado</span>
                    <span class="metric-value" id="co2Avoided">0 kg</span>
                </div>
                <div class="timestamp" id="costTime"></div>
            </div>
            
            <div class="card success">
                <h2>✅ Sistema</h2>
                <div class="metric">
                    <span class="metric-label">Estado</span>
                    <span class="metric-value" id="sysStatus" style="color: #27ae60;">Operativo</span>
                </div>
                <div class="metric">
                    <span class="metric-label">API FastAPI</span>
                    <span class="metric-value" id="apiStatus" style="color: #27ae60;">✓ OK</span>
                </div>
                <div class="metric">
                    <span class="metric-label">WebSocket</span>
                    <span class="metric-value" id="wsStatusValue" style="color: #f39c12;">Conectando...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">MongoDB</span>
                    <span class="metric-value" id="mongoStatus" style="color: #27ae60;">✓ OK</span>
                </div>
                <div class="timestamp" id="sysTime"></div>
            </div>
        </div>
        
        <!-- Gráficos -->
        <div class="charts-grid">
            <div class="chart-container">
                <h3>📊 Energía (Últimas 24h)</h3>
                <canvas id="energyChart"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>📈 Costo Acumulado</h3>
                <canvas id="costChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        // Estado global
        const MAX_POINTS = 24;
        let ws = null;
        let energyChart = null;
        let costChart = null;
        
        let data = {
            timestamps: [],
            consumos: [],
            solares: [],
            baterias: [],
            costos: []
        };
        
        // Conectar WebSocket
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8000/ws');
            
            ws.onopen = () => {
                console.log('✅ WebSocket conectado');
                updateStatus('Conectado', 'connected');
            };
            
            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                
                if (msg.type === 'metrics') {
                    updateMetrics(msg);
                } else if (msg.type === 'agent') {
                    updateAgent(msg);
                } else if (msg.type === 'objectives') {
                    updateObjectives(msg);
                }
            };
            
            ws.onerror = (error) => {
                console.error('❌ Error WebSocket:', error);
                updateStatus('Error de conexión', 'disconnected');
            };
            
            ws.onclose = () => {
                console.log('❌ WebSocket desconectado');
                updateStatus('Desconectado', 'disconnected');
                // Reintentar conexión
                setTimeout(connectWebSocket, 5000);
            };
        }
        
        function updateStatus(text, state) {
            const el = document.getElementById('wsStatus');
            el.textContent = text;
            el.parentElement.className = 'status-badge ' + (state === 'connected' ? '' : 'disconnected');
        }
        
        function updateMetrics(msg) {
            document.getElementById('consumo').textContent = msg.consumo.toFixed(1) + ' kW';
            document.getElementById('solar').textContent = msg.solar.toFixed(1) + ' kW';
            document.getElementById('bateria').textContent = msg.bateria.toFixed(0) + '%';
            document.getElementById('batteryBar').style.width = msg.bateria + '%';
            document.getElementById('grid').textContent = '0.0 kW';
            document.getElementById('priceKwh').textContent = '€' + msg.costo.toFixed(2) + '/kWh';
            document.getElementById('co2Avoided').textContent = msg.co2.toFixed(0) + ' kg';
            document.getElementById('energyTime').textContent = 'Actualizado: ' + new Date().toLocaleTimeString();
            
            // Actualizar gráfico
            data.timestamps.push(new Date().toLocaleTimeString());
            data.consumos.push(msg.consumo);
            data.solares.push(msg.solar);
            data.baterias.push(msg.bateria);
            data.costos.push(msg.costo);
            
            if (data.timestamps.length > MAX_POINTS) {
                data.timestamps.shift();
                data.consumos.shift();
                data.solares.shift();
                data.baterias.shift();
                data.costos.shift();
            }
            
            if (energyChart) {
                energyChart.data.labels = data.timestamps;
                energyChart.data.datasets[0].data = data.consumos;
                energyChart.data.datasets[1].data = data.solares;
                energyChart.data.datasets[2].data = data.baterias;
                energyChart.update();
            }
        }
        
        function updateAgent(msg) {
            document.getElementById('agentAction').textContent = msg.action;
            document.getElementById('episodes').textContent = msg.episodes;
            document.getElementById('reward').textContent = '€' + msg.reward.toFixed(0);
            document.getElementById('convergence').textContent = msg.convergence.toFixed(1) + '%';
        }
        
        function updateObjectives(msg) {
            document.getElementById('costObj').textContent = msg.cost_reduction.toFixed(1) + '%';
            document.getElementById('co2Obj').textContent = msg.co2_reduction.toFixed(1) + '%';
            document.getElementById('availObj').textContent = msg.availability.toFixed(1) + '%';
            document.getElementById('convObj').textContent = msg.convergence.toFixed(1) + '%';
        }
        
        function controlAgent(action) {
            fetch(`http://localhost:8000/api/control/${action}`)
                .then(r => r.json())
                .then(data => console.log('✅ Acción ejecutada:', data));
        }
        
        function getAgentStatus() {
            fetch('http://localhost:8000/api/agent')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('episodes').textContent = data.episodes;
                    document.getElementById('reward').textContent = '€' + data.total_reward.toFixed(0);
                    document.getElementById('convergence').textContent = data.convergence_percent.toFixed(1) + '%';
                });
        }
        
        function initCharts() {
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: true,
                animation: { duration: 0 }
            };
            
            // Gráfico Energía
            energyChart = new Chart(document.getElementById('energyChart'), {
                type: 'line',
                data: {
                    labels: data.timestamps,
                    datasets: [
                        {
                            label: 'Consumo (kW)',
                            data: data.consumos,
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.05)',
                            borderWidth: 2,
                            tension: 0.4
                        },
                        {
                            label: 'Solar (kW)',
                            data: data.solares,
                            borderColor: '#f39c12',
                            backgroundColor: 'rgba(243, 156, 18, 0.05)',
                            borderWidth: 2,
                            tension: 0.4
                        },
                        {
                            label: 'Batería (%)',
                            data: data.baterias,
                            borderColor: '#27ae60',
                            backgroundColor: 'rgba(39, 174, 96, 0.05)',
                            borderWidth: 2,
                            tension: 0.4
                        }
                    ]
                },
                options: chartOptions
            });
            
            // Gráfico Costo
            costChart = new Chart(document.getElementById('costChart'), {
                type: 'line',
                data: {
                    labels: data.timestamps,
                    datasets: [{
                        label: 'Costo (€)',
                        data: data.costos,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.05)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: chartOptions
            });
        }
        
        // Inicializar
        window.addEventListener('load', () => {
            initCharts();
            connectWebSocket();
            getAgentStatus();
            
            // Actualizaciones periodales
            setInterval(getAgentStatus, 10000);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(TEMPLATE)

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════╗
    ║  🎨 Dashboard Pro - Interfaz Principal        ║
    ║  Con WebSocket en Tiempo Real                 ║
    ╚════════════════════════════════════════════════╝
    
    🌐 Acceso: http://localhost:5000
    🔌 WebSocket: ws://localhost:8000/ws
    ⚡ API: http://localhost:8000/api/...
    
    ℹ️  Asegúrate de que FastAPI esté corriendo en puerto 8000
    ℹ️  Presiona Ctrl+C para detener
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
