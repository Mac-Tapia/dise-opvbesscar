#!/usr/bin/env python3.11
"""
PVBESSCAR Dashboard - Dashboard en Tiempo Real
Interfaz web avanzada con gráficos en vivo y seguimiento del agente
"""

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import subprocess
import json
import socket
from pathlib import Path
from datetime import datetime, timedelta
import os
import sys
import threading
import time
import random

app = Flask(__name__)
CORS(app)

# Configuration
PROJECT_ROOT = Path(__file__).parent

# Global state
system_metrics = {
    'timestamp': [],
    'consumo': [],
    'solar': [],
    'bateria': [],
    'costo': [],
    'acciones': []
}

agent_state = {
    'status': 'running',
    'episodes': 0,
    'rewards': 0,
    'progress': 0,
    'last_action': 'IDLE',
    'last_update': datetime.now().isoformat(),
    'goals': {
        'cost_reduction': {'target': 75, 'current': 0},
        'co2_reduction': {'target': 50, 'current': 0},
        'availability': {'target': 99, 'current': 95},
        'learning': {'target': 100, 'current': 45}
    }
}

# HTML Template avanzado
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PVBESSCAR Dashboard - Real Time</title>
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
            max-width: 1600px;
            margin: 0 auto;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            color: white;
        }
        
        header h1 {
            font-size: 32px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        header p {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: #00ff88;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            border-left: 5px solid #667eea;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }
        
        .card.agent { border-left-color: #f39c12; }
        .card.metrics { border-left-color: #27ae60; }
        .card.goals { border-left-color: #e74c3c; }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .metric-box {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #eee;
        }
        
        .metric-box:last-child {
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
        
        .goal-item {
            margin-bottom: 15px;
        }
        
        .goal-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        .goal-label .target {
            color: #999;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
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
        
        #energyChart, #costChart, #agentChart {
            max-height: 300px;
        }
        
        .agent-status {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 15px;
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
            border-radius: 8px;
            color: white;
            margin-bottom: 15px;
        }
        
        .agent-action {
            font-size: 24px;
            font-weight: bold;
            background: rgba(255,255,255,0.2);
            padding: 10px 20px;
            border-radius: 6px;
        }
        
        .action-charge { background-color: #27ae60; }
        .action-discharge { background-color: #e74c3c; }
        .action-idle { background-color: #95a5a6; }
        
        .real-time-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #27ae60;
            font-weight: bold;
        }
        
        .dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            background-color: #27ae60;
            border-radius: 50%;
            animation: blink 1s infinite;
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
        
        .controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
            font-size: 14px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102,126,234,0.4);
        }
        
        .btn-success {
            background-color: #27ae60;
            color: white;
        }
        
        .btn-success:hover {
            background-color: #229954;
        }
        
        .btn-danger {
            background-color: #e74c3c;
            color: white;
        }
        
        .btn-danger:hover {
            background-color: #c0392b;
        }
        
        .timestamp {
            font-size: 12px;
            color: #999;
            margin-top: 10px;
            text-align: right;
        }
        
        .goals-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .goal-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        
        .goal-value {
            font-size: 28px;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .goal-name {
            font-size: 12px;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>
                <span class="status-indicator"></span>
                🚀 PVBESSCAR Dashboard - Control en Tiempo Real
            </h1>
            <p>Sistema de Gestión Inteligente de Energía | Agente RL en Producción</p>
        </header>
        
        <!-- Resumen de Objetivos -->
        <div class="goals-summary">
            <div class="goal-card">
                <div class="goal-name">Reducción Costo</div>
                <div class="goal-value" id="costGoal">0%</div>
                <div class="goal-name">/ 75% objetivo</div>
            </div>
            <div class="goal-card">
                <div class="goal-name">Reducción CO2</div>
                <div class="goal-value" id="co2Goal">0%</div>
                <div class="goal-name">/ 50% objetivo</div>
            </div>
            <div class="goal-card">
                <div class="goal-name">Disponibilidad</div>
                <div class="goal-value" id="availGoal">95%</div>
                <div class="goal-name">/ 99% objetivo</div>
            </div>
            <div class="goal-card">
                <div class="goal-name">Aprendizaje IA</div>
                <div class="goal-value" id="learningGoal">45%</div>
                <div class="goal-name">/ 100% objetivo</div>
            </div>
        </div>
        
        <!-- Grid Principal -->
        <div class="grid">
            <!-- Estado del Agente -->
            <div class="card agent">
                <h2>🤖 Estado del Agente RL</h2>
                <div class="agent-status">
                    <div>
                        <div class="metric-label">Acción Actual</div>
                        <div class="agent-action" id="currentAction">IDLE</div>
                    </div>
                    <div style="text-align: right;">
                        <div class="metric-label">Episodios</div>
                        <div style="font-size: 28px; font-weight: bold;" id="episodes">0</div>
                    </div>
                </div>
                
                <div class="metric-box">
                    <span class="metric-label">Estado</span>
                    <span id="agentStatus" style="color: #27ae60; font-weight: bold;">✅ Corriendo</span>
                </div>
                <div class="metric-box">
                    <span class="metric-label">Recompensa Acumulada</span>
                    <span class="metric-value" id="totalReward">€0</span>
                </div>
                <div class="metric-box">
                    <span class="metric-label">Tasa de Aprendizaje</span>
                    <div style="width: 100%; margin-left: 10px;">
                        <div class="progress-bar">
                            <div class="progress-fill" id="learningProgress" style="width: 45%"></div>
                        </div>
                    </div>
                </div>
                
                <div class="controls" style="margin-top: 15px;">
                    <button class="btn-primary" onclick="getAgentStatus()">🔄 Actualizar</button>
                    <button class="btn-danger" onclick="pauseAgent()">⏸ Pausar</button>
                </div>
                
                <div class="timestamp" id="agentTimestamp"></div>
            </div>
            
            <!-- Métricas en Tiempo Real -->
            <div class="card metrics">
                <h2>📊 Métricas en Vivo</h2>
                <div class="metric-box">
                    <span class="metric-label">Consumo Edificio</span>
                    <span class="metric-value" id="consumo">0 kW</span>
                </div>
                <div class="metric-box">
                    <span class="metric-label">Generación Solar</span>
                    <span class="metric-value" id="solar">0 kW</span>
                </div>
                <div class="metric-box">
                    <span class="metric-label">Batería (SOC)</span>
                    <div style="width: 100%; margin-left: 10px;">
                        <div class="progress-bar">
                            <div class="progress-fill" id="batteryBar" style="width: 50%"></div>
                        </div>
                        <div id="batteryValue">50%</div>
                    </div>
                </div>
                <div class="metric-box">
                    <span class="metric-label">Importación Red</span>
                    <span class="metric-value" id="grid">0 kW</span>
                </div>
                <div class="metric-box">
                    <span class="metric-label">Costo Actual</span>
                    <span class="metric-value" id="cost">€0</span>
                </div>
                
                <div class="timestamp" id="metricsTimestamp"></div>
            </div>
            
            <!-- Objetivos de Proyecto -->
            <div class="card goals">
                <h2>🎯 Objetivos del Proyecto</h2>
                
                <div class="goal-item">
                    <div class="goal-label">
                        <span>Reducción de Costo</span>
                        <span class="target">75% objetivo</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="costBar" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666;" id="costPct">0%</div>
                </div>
                
                <div class="goal-item">
                    <div class="goal-label">
                        <span>Minimización CO2</span>
                        <span class="target">50% objetivo</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="co2Bar" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666;" id="co2Pct">0%</div>
                </div>
                
                <div class="goal-item">
                    <div class="goal-label">
                        <span>Disponibilidad Energía</span>
                        <span class="target">99% objetivo</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="availBar" style="width: 95%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666;" id="availPct">95%</div>
                </div>
                
                <div class="goal-item">
                    <div class="goal-label">
                        <span>Convergencia IA (Aprendizaje)</span>
                        <span class="target">100% objetivo</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="learningBar" style="width: 45%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666;" id="learningPct">45%</div>
                </div>
                
                <div class="timestamp" id="goalsTimestamp"></div>
            </div>
        </div>
        
        <!-- Gráficos en Tiempo Real -->
        <div class="charts-grid">
            <div class="chart-container">
                <h3>📈 Energía (24h)</h3>
                <canvas id="energyChart"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>💰 Costo Acumulado</h3>
                <canvas id="costChart"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>🤖 Aprendizaje del Agente</h3>
                <canvas id="agentChart"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        // Configuración
        const UPDATE_INTERVAL = 5000; // Cada 5 segundos
        const MAX_POINTS = 24; // 24 puntos (2 minutos con UPDATE_INTERVAL)
        
        // Datos para gráficos
        let energyData = {
            labels: [],
            consumo: [],
            solar: [],
            bateria: []
        };
        
        let costData = {
            labels: [],
            costs: []
        };
        
        let agentData = {
            labels: [],
            learning: []
        };
        
        // Gráficos
        let energyChart, costChart, agentChart;
        
        // Inicializar
        function initCharts() {
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: true,
                animation: { duration: 0 }
            };
            
            // Gráfico de Energía
            const energyCtx = document.getElementById('energyChart').getContext('2d');
            energyChart = new Chart(energyCtx, {
                type: 'line',
                data: {
                    labels: energyData.labels,
                    datasets: [
                        {
                            label: 'Consumo (kW)',
                            data: energyData.consumo,
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            borderWidth: 2,
                            tension: 0.4
                        },
                        {
                            label: 'Solar (kW)',
                            data: energyData.solar,
                            borderColor: '#f39c12',
                            backgroundColor: 'rgba(243, 156, 18, 0.1)',
                            borderWidth: 2,
                            tension: 0.4
                        },
                        {
                            label: 'Batería (%)',
                            data: energyData.bateria,
                            borderColor: '#27ae60',
                            backgroundColor: 'rgba(39, 174, 96, 0.1)',
                            borderWidth: 2,
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    ...chartOptions,
                    scales: {
                        y: { beginAtZero: true, max: 100 }
                    }
                }
            });
            
            // Gráfico de Costo
            const costCtx = document.getElementById('costChart').getContext('2d');
            costChart = new Chart(costCtx, {
                type: 'line',
                data: {
                    labels: costData.labels,
                    datasets: [{
                        label: 'Costo Acumulado (€)',
                        data: costData.costs,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: chartOptions
            });
            
            // Gráfico de Agente
            const agentCtx = document.getElementById('agentChart').getContext('2d');
            agentChart = new Chart(agentCtx, {
                type: 'line',
                data: {
                    labels: agentData.labels,
                    datasets: [{
                        label: 'Aprendizaje (%)',
                        data: agentData.learning,
                        borderColor: '#764ba2',
                        backgroundColor: 'rgba(118, 75, 162, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    ...chartOptions,
                    scales: {
                        y: { beginAtZero: true, max: 100 }
                    }
                }
            });
        }
        
        // Actualizar datos
        function updateData() {
            const now = new Date().toLocaleTimeString();
            
            // Simular datos (en producción vendrían de API)
            const newConsumo = 30 + Math.random() * 40;
            const newSolar = Math.sin(Date.now() / 3600000) * 50 + 50;
            const newBateria = 60 + Math.random() * 40;
            const newCost = 150 + Math.random() * 50;
            const newLearning = Math.min(100, 45 + Math.random() * 0.5);
            
            // Actualizar energía
            energyData.labels.push(now);
            energyData.consumo.push(newConsumo);
            energyData.solar.push(Math.max(0, newSolar));
            energyData.bateria.push(newBateria);
            
            // Actualizar costo
            costData.labels.push(now);
            costData.costs.push(newCost);
            
            // Actualizar agente
            agentData.labels.push(now);
            agentData.learning.push(newLearning);
            
            // Mantener máximo de puntos
            if (energyData.labels.length > MAX_POINTS) {
                energyData.labels.shift();
                energyData.consumo.shift();
                energyData.solar.shift();
                energyData.bateria.shift();
                costData.labels.shift();
                costData.costs.shift();
                agentData.labels.shift();
                agentData.learning.shift();
            }
            
            // Actualizar métricas
            document.getElementById('consumo').textContent = newConsumo.toFixed(1) + ' kW';
            document.getElementById('solar').textContent = Math.max(0, newSolar).toFixed(1) + ' kW';
            document.getElementById('batteryBar').style.width = newBateria + '%';
            document.getElementById('batteryValue').textContent = newBateria.toFixed(0) + '%';
            document.getElementById('cost').textContent = '€' + newCost.toFixed(0);
            
            // Actualizar objetivos (simulación)
            const costReduction = Math.min(75, Math.random() * 30);
            const co2Reduction = Math.min(50, Math.random() * 25);
            const availability = 95 + Math.random() * 4;
            
            document.getElementById('costBar').style.width = costReduction + '%';
            document.getElementById('costPct').textContent = costReduction.toFixed(0) + '%';
            document.getElementById('co2Bar').style.width = co2Reduction + '%';
            document.getElementById('co2Pct').textContent = co2Reduction.toFixed(0) + '%';
            document.getElementById('availBar').style.width = availability + '%';
            document.getElementById('availPct').textContent = availability.toFixed(0) + '%';
            document.getElementById('learningBar').style.width = newLearning + '%';
            document.getElementById('learningPct').textContent = newLearning.toFixed(0) + '%';
            
            // Actualizar gráficos
            energyChart.data.labels = energyData.labels;
            energyChart.data.datasets[0].data = energyData.consumo;
            energyChart.data.datasets[1].data = energyData.solar;
            energyChart.data.datasets[2].data = energyData.bateria;
            energyChart.update();
            
            costChart.data.labels = costData.labels;
            costChart.data.datasets[0].data = costData.costs;
            costChart.update();
            
            agentChart.data.labels = agentData.labels;
            agentChart.data.datasets[0].data = agentData.learning;
            agentChart.update();
            
            // Actualizar timestamps
            document.getElementById('metricsTimestamp').textContent = 'Actualizado: ' + now;
            document.getElementById('goalsTimestamp').textContent = 'Actualizado: ' + now;
        }
        
        // Acciones
        function getAgentStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('episodes').textContent = Math.floor(Math.random() * 10000);
                    document.getElementById('agentTimestamp').textContent = 'Actualizado: ' + new Date().toLocaleTimeString();
                });
        }
        
        function pauseAgent() {
            alert('Agente pausado (función simulada)');
        }
        
        // Inicializar
        window.addEventListener('load', () => {
            initCharts();
            updateData();
            setInterval(updateData, UPDATE_INTERVAL);
        });
    </script>
</body>
</html>
"""

def run_command(cmd, shell=False, timeout=30):
    """Execute command"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=shell,
            timeout=timeout,
            cwd=str(PROJECT_ROOT)
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'stdout': '', 'stderr': str(e)}

@app.route('/')
def index():
    return render_template_string(TEMPLATE)

@app.route('/api/status')
def api_status():
    return jsonify({
        'status': 'operational',
        'timestamp': datetime.now().isoformat(),
        'agent': agent_state,
        'metrics': system_metrics
    })

if __name__ == '__main__':
    print("""
    ╔═════════════════════════════════════════════════╗
    ║  🚀 PVBESSCAR Dashboard - Real Time             ║
    ║  Con gráficos en vivo y seguimiento del agente  ║
    ╚═════════════════════════════════════════════════╝
    
    🌐 Acceso: http://localhost:5000
    📊 Gráficos en tiempo real
    🤖 Estado del agente RL
    🎯 Seguimiento de objetivos
    
    ℹ️  Presiona Ctrl+C para detener
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
