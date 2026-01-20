#!/usr/bin/env python3.11
"""
PVBESSCAR Docker Web Interface
Interfaz web para gestionar contenedores Docker
"""

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import subprocess
import json
import socket
from pathlib import Path
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Configuration
PROJECT_ROOT = Path(__file__).parent
DOCKER_COMPOSE_FILES = {
    'cpu': 'docker-compose.yml',
    'gpu': 'docker-compose.gpu.yml',
    'dev': 'docker-compose.dev.yml',
}

# HTML Template
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
        
        .card.status {
            border-left: 4px solid #667eea;
        }
        
        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        
        .status-item:last-child {
            border-bottom: none;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .badge.running {
            background: #d4edda;
            color: #155724;
        }
        
        .badge.stopped {
            background: #f8d7da;
            color: #721c24;
        }
        
        .badge.error {
            background: #f8d7da;
            color: #721c24;
        }
        
        .badge.healthy {
            background: #d4edda;
            color: #155724;
        }
        
        .button-group {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        
        button {
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .btn-success {
            background: #28a745;
            color: white;
        }
        
        .btn-success:hover {
            background: #218838;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .btn-danger:hover {
            background: #c82333;
        }
        
        .btn-warning {
            background: #ffc107;
            color: black;
        }
        
        .btn-warning:hover {
            background: #e0a800;
        }
        
        .btn-info {
            background: #17a2b8;
            color: white;
        }
        
        .btn-info:hover {
            background: #138496;
        }
        
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            border-bottom: 2px solid #eee;
        }
        
        .tab-button {
            background: transparent;
            border: none;
            padding: 10px 15px;
            color: #666;
            font-weight: bold;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }
        
        .tab-button.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .log-container {
            background: #1e1e1e;
            color: #0f0;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 10px;
        }
        
        .log-line {
            padding: 2px 0;
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .loading {
            text-align: center;
            padding: 20px;
        }
        
        .alert {
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .port-info {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-size: 14px;
        }
        
        .port-link {
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
        }
        
        .port-link:hover {
            text-decoration: underline;
        }
        
        footer {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🐳 PVBESSCAR Docker Manager</h1>
            <p>Web interface para gestionar contenedores Docker</p>
        </header>
        
        <div class="grid">
            <!-- Status Card -->
            <div class="card status">
                <h2>📊 Status</h2>
                <div id="status-content" class="loading">
                    <div class="spinner"></div>
                </div>
            </div>
            
            <!-- Quick Actions -->
            <div class="card">
                <h2>⚡ Acciones Rápidas</h2>
                <div class="tabs">
                    <button class="tab-button active" onclick="switchTab('cpu', this)">CPU</button>
                    <button class="tab-button" onclick="switchTab('gpu', this)">GPU</button>
                    <button class="tab-button" onclick="switchTab('dev', this)">Dev</button>
                </div>
                
                <div id="cpu" class="tab-content active">
                    <div class="button-group">
                        <button class="btn-primary" onclick="buildImage('cpu')">Build CPU</button>
                        <button class="btn-success" onclick="startServices('cpu')">Start CPU</button>
                        <button class="btn-danger" onclick="stopServices('cpu')">Stop</button>
                    </div>
                </div>
                
                <div id="gpu" class="tab-content">
                    <div class="button-group">
                        <button class="btn-primary" onclick="buildImage('gpu')">Build GPU</button>
                        <button class="btn-success" onclick="startServices('gpu')">Start GPU</button>
                        <button class="btn-danger" onclick="stopServices('gpu')">Stop</button>
                    </div>
                </div>
                
                <div id="dev" class="tab-content">
                    <div class="button-group">
                        <button class="btn-primary" onclick="buildImage('dev')">Build Dev</button>
                        <button class="btn-success" onclick="startServices('dev')">Start Dev</button>
                        <button class="btn-danger" onclick="stopServices('dev')">Stop</button>
                    </div>
                </div>
            </div>
            
            <!-- Services Info -->
            <div class="card">
                <h2>🌐 Acceso Web</h2>
                <div class="port-info">
                    <strong>Jupyter Lab (CPU):</strong><br>
                    <a href="http://localhost:8888" class="port-link" target="_blank">http://localhost:8888</a>
                </div>
                <div class="port-info">
                    <strong>Jupyter Lab (GPU):</strong><br>
                    <a href="http://localhost:8889" class="port-link" target="_blank">http://localhost:8889</a>
                </div>
                <div class="port-info">
                    <strong>Docker Manager:</strong><br>
                    <a href="http://localhost:5000" class="port-link" target="_blank">http://localhost:5000</a>
                </div>
            </div>
        </div>
        
        <!-- Main Logs Area -->
        <div class="card">
            <h2>📋 Logs & Output</h2>
            <div class="button-group">
                <button class="btn-info" onclick="viewLogs('all')">Ver Logs</button>
                <button class="btn-info" onclick="viewLogs('pipeline')">Pipeline</button>
                <button class="btn-info" onclick="viewLogs('jupyter')">Jupyter</button>
                <button class="btn-warning" onclick="clearLogs()">Limpiar</button>
            </div>
            <div id="logs" class="log-container">
                <div class="log-line">Sistema listo...</div>
            </div>
        </div>
        
        <footer>
            <p>PVBESSCAR Docker Manager v1.0.0 | Python 3.11 | Flask + Docker Compose</p>
        </footer>
    </div>
    
    <script>
        let currentMode = 'cpu';
        
        function switchTab(mode, button) {
            document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            button.classList.add('active');
            document.getElementById(mode).classList.add('active');
            currentMode = mode;
        }
        
        function addLog(message, type = 'info') {
            const logsDiv = document.getElementById('logs');
            const timestamp = new Date().toLocaleTimeString();
            const line = document.createElement('div');
            line.className = 'log-line';
            line.textContent = `[${timestamp}] ${message}`;
            logsDiv.appendChild(line);
            logsDiv.scrollTop = logsDiv.scrollHeight;
        }
        
        function clearLogs() {
            document.getElementById('logs').innerHTML = '';
        }
        
        function showAlert(message, type = 'info') {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type}`;
            alertDiv.textContent = message;
            document.querySelector('.container').prepend(alertDiv);
            setTimeout(() => alertDiv.remove(), 5000);
        }
        
        async function buildImage(mode) {
            addLog(`🔨 Building ${mode} image...`);
            showAlert(`Building ${mode} image...`, 'info');
            
            try {
                const response = await fetch(`/api/build`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode})
                });
                
                const data = await response.json();
                if (data.success) {
                    addLog(`✅ Image ${mode} built successfully`);
                    showAlert(`✅ Image ${mode} built successfully`, 'success');
                } else {
                    addLog(`❌ Error building image: ${data.error}`);
                    showAlert(`❌ Error: ${data.error}`, 'error');
                }
            } catch (error) {
                addLog(`❌ Error: ${error.message}`);
                showAlert(`❌ Error: ${error.message}`, 'error');
            }
        }
        
        async function startServices(mode) {
            addLog(`🚀 Starting ${mode} services...`);
            showAlert(`Starting ${mode} services...`, 'info');
            
            try {
                const response = await fetch(`/api/start`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode})
                });
                
                const data = await response.json();
                if (data.success) {
                    addLog(`✅ Services ${mode} started`);
                    showAlert(`✅ Services ${mode} started`, 'success');
                    updateStatus();
                } else {
                    addLog(`❌ Error: ${data.error}`);
                    showAlert(`❌ Error: ${data.error}`, 'error');
                }
            } catch (error) {
                addLog(`❌ Error: ${error.message}`);
                showAlert(`❌ Error: ${error.message}`, 'error');
            }
        }
        
        async function stopServices(mode) {
            addLog(`⏹️  Stopping ${mode} services...`);
            showAlert(`Stopping ${mode} services...`, 'info');
            
            try {
                const response = await fetch(`/api/stop`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode})
                });
                
                const data = await response.json();
                if (data.success) {
                    addLog(`✅ Services ${mode} stopped`);
                    showAlert(`✅ Services ${mode} stopped`, 'success');
                    updateStatus();
                } else {
                    addLog(`❌ Error: ${data.error}`);
                    showAlert(`❌ Error: ${data.error}`, 'error');
                }
            } catch (error) {
                addLog(`❌ Error: ${error.message}`);
                showAlert(`❌ Error: ${error.message}`, 'error');
            }
        }
        
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                let html = '';
                for (const [name, status] of Object.entries(data.containers || {})) {
                    const badge = status.running ? 'running' : 'stopped';
                    html += `
                        <div class="status-item">
                            <span>${name}</span>
                            <span class="badge ${badge}">${status.running ? 'RUNNING' : 'STOPPED'}</span>
                        </div>
                    `;
                }
                
                document.getElementById('status-content').innerHTML = html || 'No containers found';
            } catch (error) {
                console.error('Error updating status:', error);
            }
        }
        
        async function viewLogs(service) {
            addLog(`📜 Loading ${service} logs...`);
            
            try {
                const response = await fetch(`/api/logs?service=${service}`);
                const data = await response.json();
                
                document.getElementById('logs').innerHTML = '';
                const lines = data.logs.split('\\n');
                lines.forEach(line => {
                    if (line.trim()) {
                        addLog(line);
                    }
                });
            } catch (error) {
                addLog(`❌ Error loading logs: ${error.message}`);
            }
        }
        
        // Auto-update status every 5 seconds
        setInterval(updateStatus, 5000);
        
        // Initial status
        updateStatus();
        addLog('🟢 Docker Manager iniciado');
    </script>
</body>
</html>
"""

def run_command(cmd, shell=False):
    """Execute command and capture output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=shell,
            timeout=30
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Command timeout',
            'stdout': '',
            'stderr': 'Command exceeded 30 seconds'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'stdout': '',
            'stderr': str(e)
        }

def check_docker():
    """Check if Docker is running"""
    result = run_command(['docker', 'ps'], shell=True)
    return result['success']

@app.route('/')
def index():
    """Main page"""
    return render_template_string(TEMPLATE)

@app.route('/api/status')
def api_status():
    """Get containers status"""
    result = run_command(['docker', 'ps', '-a', '--format', '{{.Names}}|{{.State}}'], shell=True)
    
    containers = {}
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
        'docker_running': check_docker(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/build', methods=['POST'])
def api_build():
    """Build Docker image"""
    mode = request.json.get('mode', 'cpu')
    
    tag = {
        'cpu': 'pvbesscar:latest',
        'gpu': 'pvbesscar:latest-gpu',
        'dev': 'pvbesscar:dev'
    }.get(mode, 'pvbesscar:latest')
    
    cmd = [
        'docker', 'build',
        '--build-arg', 'BUILDKIT_INLINE_CACHE=1',
        '-t', tag,
        '.'
    ]
    
    result = run_command(cmd, shell=True)
    
    return jsonify({
        'success': result['success'],
        'message': f"Image {tag} built",
        'error': result['stderr'] if not result['success'] else None,
        'output': result['stdout']
    })

@app.route('/api/start', methods=['POST'])
def api_start():
    """Start services"""
    mode = request.json.get('mode', 'cpu')
    
    compose_file = DOCKER_COMPOSE_FILES.get(mode, 'docker-compose.yml')
    
    cmd = ['docker-compose', '-f', compose_file, 'up', '-d']
    
    result = run_command(cmd, shell=True)
    
    return jsonify({
        'success': result['success'],
        'message': f"Services {mode} started",
        'error': result['stderr'] if not result['success'] else None,
        'output': result['stdout']
    })

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Stop services"""
    mode = request.json.get('mode', 'cpu')
    
    compose_file = DOCKER_COMPOSE_FILES.get(mode, 'docker-compose.yml')
    
    cmd = ['docker-compose', '-f', compose_file, 'down']
    
    result = run_command(cmd, shell=True)
    
    return jsonify({
        'success': result['success'],
        'message': f"Services {mode} stopped",
        'error': result['stderr'] if not result['success'] else None,
        'output': result['stdout']
    })

@app.route('/api/logs')
def api_logs():
    """Get container logs"""
    service = request.args.get('service', 'all')
    
    if service == 'all':
        cmd = ['docker-compose', 'logs', '--tail=100']
    else:
        cmd = ['docker', 'logs', f'pvbesscar-{service}', '--tail=100']
    
    result = run_command(cmd, shell=True)
    
    return jsonify({
        'success': result['success'],
        'logs': result['stdout'] if result['success'] else result['stderr'],
        'service': service
    })

@app.route('/api/health')
def api_health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'docker': check_docker(),
        'timestamp': datetime.now().isoformat()
    })

def get_local_ip():
    """Get local IP address"""
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
    ╔═══════════════════════════════════════════╗
    ║  🐳 PVBESSCAR Docker Web Interface       ║
    ║  Python 3.11 + Flask                    ║
    ╚═══════════════════════════════════════════╝
    """)
    
    local_ip = get_local_ip()
    print(f"\n🌐 Web Interface Available:")
    print(f"   Local:    http://localhost:5000")
    print(f"   Network:  http://{local_ip}:5000")
    print(f"\n✨ Jupyter Lab (when running):")
    print(f"   CPU:  http://localhost:8888")
    print(f"   GPU:  http://localhost:8889")
    print(f"\n📝 Press Ctrl+C to stop the server\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
