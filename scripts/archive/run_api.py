#!/usr/bin/env python3.11
import subprocess
import sys
import time

print("[INFO] Iniciando PVBESSCAR API v3.0")
print("[INFO] Puerto: 8000")

try:
    # Ejecutar uvicorn como subproceso sin bloqueante
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "fastapi_websocket_server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"],
        cwd="d:\\diseñopvbesscar",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    print(f"[INFO] API iniciado con PID {process.pid}")
    print("[INFO] Presiona Ctrl+C para detener")
    
    # Mantener el proceso vivo
    while True:
        time.sleep(1)
        if process.poll() is not None:
            print(f"[ERROR] Proceso terminado con codigo {process.returncode}")
            break
except KeyboardInterrupt:
    print("\n[INFO] Deteniendo...")
    process.terminate()
    process.wait()
    print("[INFO] Proceso detenido")
