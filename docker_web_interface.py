#!/usr/bin/env python3.11
"""
PVBESSCAR Docker Web Interface - MEJORADA
Interfaz web para gestionar contenedores Docker con manejo robusto de errores
"""

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import subprocess
import json
import socket
from pathlib import Path
from datetime import datetime
import os
import sys

app = Flask(__name__)
CORS(app)

# Configuration
PROJECT_ROOT = Path(__file__).parent
DOCKER_COMPOSE_FILES = {
    'cpu': 'docker-compose.yml',
    'gpu': 'docker-compose.gpu.yml',
    'dev': 'docker-compose.dev.yml',
}

# HTML Template mejorado
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PVBESSCAR Docker Manager</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        header h1 {
            color: #667eea;
            margin-bottom: 5px;
        }
        
        header p {
            color: #666;
            font-size: 14px;
        }
        
        .alert {
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
            display: none;
        }
        
        .alert.error {
            background-color: #fee;
            border-left: 4px solid #f44;
            color: #c33;
        }
        
        .alert.warning {
            background-color: #ffeaa7;
            border-left: 4px solid #fdcb6e;
            color: #d63031;
        }
        
        .alert.success {
            background-color: #d4edda;
            border-left: 4px solid #28a745;
            color: #155724;
        }
        
        .alert.info {
            background-color: #d1ecf1;
            border-left: 4px solid #0c5460;
            color: #0c5460;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .card.status { border-left: 4px solid #667eea; }
        .card.actions { border-left: 4px solid #f39c12; }
        .card.web { border-left: 4px solid #27ae60; }
        
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        
        .status-item:last-child { border-bottom: none; }
        
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .status-badge.running { background-color: #d4edda; color: #155724; }
        .status-badge.stopped { background-color: #f8d7da; color: #721c24; }
        .status-badge.error { background-color: #fee; color: #c33; }
        
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
            border-bottom: 2px solid #eee;
        }
        
        .tab-btn {
            background: none;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            color: #666;
            font-weight: 500;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }
        
        .tab-btn.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        
        .action-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }
        
        button {
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
            font-size: 14px;
        }
        
        .btn-primary { background-color: #667eea; color: white; }
        .btn-primary:hover { background-color: #5568d3; transform: translateY(-2px); }
        
        .btn-success { background-color: #27ae60; color: white; }
        .btn-success:hover { background-color: #229954; transform: translateY(-2px); }
        
        .btn-danger { background-color: #e74c3c; color: white; }
        .btn-danger:hover { background-color: #c0392b; transform: translateY(-2px); }
        
        .btn-secondary { background-color: #95a5a6; color: white; }
        .btn-secondary:hover { background-color: #7f8c8d; transform: translateY(-2px); }
        
        .loading {
            display: inline-block;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .log-viewer {
            background-color: #1e1e1e;
            color: #0f0;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
            display: none;
        }
        
        .log-viewer.active {
            display: block;
        }
        
        .link-button {
            background: none;
            border: none;
            color: #667eea;
            cursor: pointer;
            text-decoration: underline;
            padding: 0;
            font-size: 14px;
        }
        
        .link-button:hover {
            color: #5568d3;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🐳 PVBESSCAR Docker Manager</h1>
            <p>Web interface para gestionar contenedores Docker</p>
        </header>
        
        <div id="alerts"></div>
        
        <div class="grid">
            <!-- Status Card -->
            <div class="card status">
                <h2>📊 Estado</h2>
                <div id="status-content">
                    <div style="text-align: center; padding: 20px;">
                        <div class="loading">⏳</div>
                        <p>Cargando estado...</p>
                    </div>
                </div>
            </div>
            
            <!-- Actions Card -->
            <div class="card actions">
                <h2>⚡ Acciones Rápidas</h2>
                <div class="tabs">
                    <button class="tab-btn active" onclick="switchTab('cpu-actions')">CPU</button>
                    <button class="tab-btn" onclick="switchTab('gpu-actions')">GPU</button>
                    <button class="tab-btn" onclick="switchTab('dev-actions')">Dev</button>
                </div>
                
                <div id="cpu-actions" class="action-grid">
                    <button class="btn-primary" onclick="buildImage('cpu')">Build CPU</button>
                    <button class="btn-success" onclick="startService('cpu')">Start CPU</button>
                    <button class="btn-danger" onclick="stopService('cpu')">Stop</button>
                </div>
                
                <div id="gpu-actions" class="action-grid" style="display:none;">
                    <button class="btn-primary" onclick="buildImage('gpu')">Build GPU</button>
                    <button class="btn-success" onclick="startService('gpu')">Start GPU</button>
                    <button class="btn-danger" onclick="stopService('gpu')">Stop</button>
                </div>
                
                <div id="dev-actions" class="action-grid" style="display:none;">
                    <button class="btn-primary" onclick="buildImage('dev')">Build Dev</button>
                    <button class="btn-success" onclick="startService('dev')">Start Dev</button>
                    <button class="btn-danger" onclick="stopService('dev')">Stop</button>
                </div>
            </div>
            
            <!-- Web Access Card -->
            <div class="card web">
                <h2>🌐 Acceso Web</h2>
                <div class="status-item">
                    <span>Jupyter Lab (CPU):</span>
                    <a href="http://localhost:8888" target="_blank" class="link-button">http://localhost:8888</a>
                </div>
                <div class="status-item">
                    <span>Jupyter Lab (GPU):</span>
                    <a href="http://localhost:8889" target="_blank" class="link-button">http://localhost:8889</a>
                </div>
                <div class="status-item">
                    <span>Docker Manager:</span>
                    <a href="http://localhost:5000" target="_blank" class="link-button">http://localhost:5000</a>
                </div>
            </div>
        </div>
        
        <!-- Logs Card -->
        <div class="card">
            <h2>📋 Logs y Output</h2>
            <div class="tabs">
                <button class="tab-btn active" onclick="switchLogs('ver-logs')">Ver Logs</button>
                <button class="tab-btn" onclick="switchLogs('pipeline')">Pipeline</button>
                <button class="tab-btn" onclick="switchLogs('jupyter')">Jupyter</button>
                <button class="tab-btn" onclick="switchLogs('limpiar')">Limpiar</button>
            </div>
            <div id="ver-logs" class="log-viewer active"></div>
            <div id="pipeline" class="log-viewer"></div>
            <div id="jupyter" class="log-viewer"></div>
            <div id="limpiar" class="log-viewer"></div>
        </div>
    </div>
    
    <script>
        // Estado global
        let currentTab = 'cpu-actions';
        let currentLogTab = 'ver-logs';
        
        // Mostrar alerta
        function showAlert(message, type = 'info') {
            const alerts = document.getElementById('alerts');
            const alert = document.createElement('div');
            alert.className = `alert ${type}`;
            alert.textContent = message;
            alert.style.display = 'block';
            alerts.appendChild(alert);
            
            setTimeout(() => alert.remove(), 5000);
        }
        
        // Cambiar tab de acciones
        function switchTab(tab) {
            document.getElementById(currentTab).style.display = 'none';
            document.getElementById(tab).style.display = 'grid';
            
            // Actualizar botones activos
            document.querySelectorAll('.tabs .tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            currentTab = tab;
        }
        
        // Cambiar tab de logs
        function switchLogs(tab) {
            document.getElementById(currentLogTab).classList.remove('active');
            document.getElementById(tab).classList.add('active');
            
            // Actualizar botones activos
            document.querySelectorAll('.tabs .tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            currentLogTab = tab;
        }
        
        // Obtener estado
        function getStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    let html = '<div class="status-item"><strong>Docker Daemon:</strong>';
                    html += data.docker_running ? 
                        '<span class="status-badge running">✓ Corriendo</span>' :
                        '<span class="status-badge error">✗ No disponible</span>';
                    html += '</div>';
                    
                    if (Object.keys(data.containers).length === 0) {
                        html += '<p style="margin-top: 10px; color: #666;">No hay contenedores</p>';
                    } else {
                        for (const [name, info] of Object.entries(data.containers)) {
                            const badge = info.running ? 'running' : 'stopped';
                            const text = info.running ? '✓ Corriendo' : '✗ Detenido';
                            html += `<div class="status-item"><strong>${name}</strong><span class="status-badge ${badge}">${text}</span></div>`;
                        }
                    }
                    
                    document.getElementById('status-content').innerHTML = html;
                })
                .catch(err => {
                    document.getElementById('status-content').innerHTML = 
                        '<p style="color: red;">Error: ' + err.message + '</p>';
                });
        }
        
        // Build imagen
        function buildImage(mode) {
            showAlert(`🔨 Construyendo imagen ${mode}...`, 'info');
            fetch('/api/build', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mode: mode})
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showAlert(`✓ Imagen ${mode} construida exitosamente`, 'success');
                    } else {
                        showAlert(`✗ Error: ${data.error || data.message}`, 'error');
                    }
                    getStatus();
                })
                .catch(err => showAlert(`✗ Error: ${err.message}`, 'error'));
        }
        
        // Iniciar servicio
        function startService(mode) {
            showAlert(`▶️ Iniciando servicios ${mode}...`, 'info');
            fetch('/api/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mode: mode})
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showAlert(`✓ Servicios ${mode} iniciados`, 'success');
                    } else {
                        showAlert(`✗ Error: ${data.error || data.message}`, 'error');
                    }
                    getStatus();
                })
                .catch(err => showAlert(`✗ Error: ${err.message}`, 'error'));
        }
        
        // Detener servicio
        function stopService(mode) {
            showAlert(`⏹️  Deteniendo servicios ${mode}...`, 'info');
            fetch('/api/stop', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mode: mode})
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showAlert(`✓ Servicios ${mode} detenidos`, 'success');
                    } else {
                        showAlert(`⚠️  ${data.message || 'Servicios no estaban corriendo'}`, 'warning');
                    }
                    getStatus();
                })
                .catch(err => showAlert(`✗ Error: ${err.message}`, 'error'));
        }
        
        // Ver logs
        function viewLogs(service) {
            fetch(`/api/logs?service=${service}`)
                .then(r => r.json())
                .then(data => {
                    const viewer = document.getElementById(service);
                    viewer.textContent = data.logs || 'No hay logs disponibles';
                })
                .catch(err => {
                    document.getElementById(service).textContent = 'Error: ' + err.message;
                });
        }
        
        // Inicializar
        window.onload = () => {
            getStatus();
            setInterval(getStatus, 10000); // Actualizar cada 10 segundos
        };
    </script>
</body>
</html>
"""

def run_command(cmd, shell=False, timeout=30):
    """Execute command and capture output con mejor manejo de errores"""
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
            'returncode': result.returncode,
            'command': ' '.join(cmd) if isinstance(cmd, list) else cmd
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Timeout',
            'stdout': '',
            'stderr': f'Comando excedió {timeout} segundos',
            'command': ' '.join(cmd) if isinstance(cmd, list) else cmd
        }
    except FileNotFoundError as e:
        return {
            'success': False,
            'error': 'Comando no encontrado',
            'stdout': '',
            'stderr': f'{cmd[0] if isinstance(cmd, list) else cmd} no está instalado',
            'command': ' '.join(cmd) if isinstance(cmd, list) else cmd
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(type(e).__name__),
            'stdout': '',
            'stderr': str(e),
            'command': ' '.join(cmd) if isinstance(cmd, list) else cmd
        }

def check_docker():
    """Verificar si Docker está corriendo"""
    result = run_command('docker ps', shell=True)
    return result['success']

@app.route('/')
def index():
    """Página principal"""
    return render_template_string(TEMPLATE)

@app.route('/api/status')
def api_status():
    """Obtener estado de contenedores"""
    docker_running = check_docker()
    containers = {}
    
    if docker_running:
        result = run_command('docker ps -a --format "{{.Names}}|{{.State}}"', shell=True)
        if result['success']:
            lines = result['stdout'].strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split('|')
                    if len(parts) == 2:
                        containers[parts[0]] = {
                            'running': parts[1] == 'running',
                            'state': parts[1]
                        }
    
    return jsonify({
        'success': True,
        'containers': containers,
        'docker_running': docker_running,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/build', methods=['POST'])
def api_build():
    """Construir imagen Docker"""
    try:
        data = request.get_json() or {}
        mode = data.get('mode', 'cpu')
        
        if not check_docker():
            return jsonify({
                'success': False,
                'message': 'Docker daemon no disponible',
                'error': 'Inicia Docker Desktop o Docker Engine',
                'mode': mode
            }), 503
        
        compose_file = DOCKER_COMPOSE_FILES.get(mode, 'docker-compose.yml')
        cmd = f'docker-compose -f {compose_file} build'
        result = run_command(cmd, shell=True, timeout=300)
        
        return jsonify({
            'success': result['success'],
            'message': f"Imagen {mode} {'construida' if result['success'] else 'error al construir'}",
            'error': result.get('stderr', ''),
            'output': result.get('stdout', ''),
            'mode': mode
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error interno',
            'error': str(e),
            'mode': mode
        }), 500

@app.route('/api/start', methods=['POST'])
def api_start():
    """Iniciar servicios Docker"""
    try:
        data = request.get_json() or {}
        mode = data.get('mode', 'cpu')
        
        if not check_docker():
            return jsonify({
                'success': False,
                'message': 'Docker daemon no disponible',
                'error': 'Inicia Docker Desktop o Docker Engine',
                'mode': mode
            }), 503
        
        compose_file = DOCKER_COMPOSE_FILES.get(mode, 'docker-compose.yml')
        cmd = f'docker-compose -f {compose_file} up -d'
        result = run_command(cmd, shell=True)
        
        return jsonify({
            'success': result['success'],
            'message': f"Servicios {mode} {'iniciados' if result['success'] else 'error'}",
            'error': result.get('stderr', ''),
            'output': result.get('stdout', ''),
            'mode': mode
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error interno',
            'error': str(e),
            'mode': mode
        }), 500

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Detener servicios Docker"""
    try:
        data = request.get_json() or {}
        mode = data.get('mode', 'cpu')
        
        if not check_docker():
            return jsonify({
                'success': False,
                'message': 'Docker daemon no disponible',
                'error': 'Inicia Docker Desktop o Docker Engine',
                'mode': mode
            }), 503
        
        compose_file = DOCKER_COMPOSE_FILES.get(mode, 'docker-compose.yml')
        cmd = f'docker-compose -f {compose_file} down'
        result = run_command(cmd, shell=True)
        
        return jsonify({
            'success': result['success'],
            'message': f"Servicios {mode} detenidos",
            'error': result.get('stderr', '') if not result['success'] else None,
            'output': result.get('stdout', ''),
            'mode': mode
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Error interno',
            'error': str(e),
            'mode': mode
        }), 500

@app.route('/api/logs')
def api_logs():
    """Obtener logs"""
    try:
        service = request.args.get('service', 'all')
        
        if service == 'all':
            cmd = 'docker-compose logs --tail=100 2>&1 || echo "No logs available"'
        else:
            cmd = f'docker logs pvbesscar-{service} --tail=100 2>&1 || echo "Container not found"'
        
        result = run_command(cmd, shell=True)
        
        return jsonify({
            'success': True,
            'logs': result['stdout'] or result['stderr'] or 'No hay logs',
            'service': service
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'logs': f'Error: {str(e)}',
            'service': 'error'
        }), 500

@app.route('/api/health')
def api_health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'docker': check_docker(),
        'timestamp': datetime.now().isoformat()
    })

def get_local_ip():
    """Obtener IP local"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════╗
    ║  🐳 PVBESSCAR Docker Web Interface - MEJORADA  ║
    ║  Python 3.11 + Flask                          ║
    ║  Version 2.0 - Error Handling Mejorado        ║
    ╚════════════════════════════════════════════════╝
    """)
    
    local_ip = get_local_ip()
    print(f"\n🌐 Interfaz Web Disponible:")
    print(f"   Local:    http://localhost:5000")
    print(f"   Network:  http://{local_ip}:5000")
    print(f"\n✨ Jupyter Lab (cuando esté corriendo):")
    print(f"   CPU:  http://localhost:8888")
    print(f"   GPU:  http://localhost:8889")
    print(f"\n⚠️  REQUISITO: Docker Desktop debe estar corriendo")
    print(f"   Descarga: https://www.docker.com/products/docker-desktop")
    print(f"\n📝 Presiona Ctrl+C para detener el servidor\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
