# ╔════════════════════════════════════════════════════════════════════════════╗
# ║     🚀 LANZADOR DE ENTRENAMIENTO A2C CON GPU - ROBUSTO SIN INTERRUPCIONES   ║
# ║                            27 Enero 2026                                     ║
# ╚════════════════════════════════════════════════════════════════════════════╝

Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     🚀 INICIANDO ENTRENAMIENTO A2C CON GPU AL MÁXIMO                     ║" -ForegroundColor Cyan
Write-Host "║        Python 3.11 | PyTorch 2.7.1+cu118 | CUDA 11.8 | RTX 4060         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Verificar Python 3.11
Write-Host "[1/4] 🔍 Verificando Python 3.11..." -ForegroundColor Yellow
$pythonCheck = py -3.11 --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "     ✅ Python $pythonCheck" -ForegroundColor Green
}
else {
    Write-Host "     ❌ Error: Python 3.11 no encontrado" -ForegroundColor Red
    exit 1
}

# Verificar PyTorch con CUDA
Write-Host "[2/4] 🔍 Verificando PyTorch + CUDA..." -ForegroundColor Yellow
$cudaCheck = py -3.11 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')" 2>&1
Write-Host "     ✅ $cudaCheck" -ForegroundColor Green

# Verificar CityLearn
Write-Host "[3/4] 🔍 Verificando CityLearn v2.5.0..." -ForegroundColor Yellow
$citylearnCheck = py -3.11 -c "import citylearn; print(f'CityLearn: {citylearn.__version__}')" 2>&1
Write-Host "     ✅ $citylearnCheck" -ForegroundColor Green

# Crear archivo de log
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logFile = "outputs/training_a2c_gpu_${timestamp}.log"
New-Item -ItemType Directory -Force -Path "outputs" | Out-Null

Write-Host "[4/4] 🚀 Lanzando entrenamiento A2C en GPU..." -ForegroundColor Yellow
Write-Host "     📝 Log file: $logFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  PROCESO INICIADO - El entrenamiento continuará en background            ║" -ForegroundColor Green
Write-Host "║  Para monitorear: tail -f $logFile                                        ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Lanzar en background con redirección a log
$scriptBlock = {
    param($logPath)
    $ErrorActionPreference = "Continue"

    # Capturar TODA la salida
    $output = py -3.11 -m scripts.run_oe3_simulate --config configs/default.yaml 2>&1

    # Guardar en log
    $output | Out-File -FilePath $logPath -Encoding UTF8 -Append

    # Mostrar en consola también
    Write-Host $output
}

# Ejecutar en background
$job = Start-Job -ScriptBlock $scriptBlock -ArgumentList $logFile
$jobId = $job.Id

Write-Host "✅ Entrenamiento lanzado en background (Job ID: $jobId)" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Información del proceso:" -ForegroundColor Cyan
Write-Host "   Job ID: $jobId" -ForegroundColor White
Write-Host "   Log: $logFile" -ForegroundColor White
Write-Host "   Duración estimada: 2-3 horas con GPU" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Comandos útiles:" -ForegroundColor Cyan
Write-Host "   Ver log (últimas 50 líneas):  Get-Content $logFile -Tail 50 -Wait" -ForegroundColor Gray
Write-Host "   Ver GPU en tiempo real:      nvidia-smi -l 1" -ForegroundColor Gray
Write-Host "   Ver estado del job:          Get-Job -Id $jobId" -ForegroundColor Gray
Write-Host "   Detener entrenamiento:       Stop-Job -Id $jobId" -ForegroundColor Gray
Write-Host "   Resultados finales:          outputs/oe3_simulations/simulation_summary.json" -ForegroundColor Gray
Write-Host ""

# Monitorear GPU en paralelo
Write-Host "🔥 MONITOREO DE GPU EN TIEMPO REAL:" -ForegroundColor Yellow
Write-Host ""

$monitor_count = 0
while ($monitor_count -lt 30) {
    $gpuInfo = nvidia-smi --query-gpu=utilization.gpu, memory.used, memory.total --format=csv, noheader, nounits 2>$null

    if ($gpuInfo) {
        $parts = $gpuInfo -split ','
        $gpuUtil = [int]$parts[0]
        $memUsed = [int]$parts[1]
        $memTotal = [int]$parts[2]

        $memPercent = [math]::Round(($memUsed / $memTotal) * 100, 1)

        # Barra visual
        $utilBar = "░" * 32
        $utilFilled = [math]::Round($gpuUtil / 3.125)
        $utilBar = ("█" * $utilFilled) + ("░" * (32 - $utilFilled))

        $memBar = "░" * 32
        $memFilled = [math]::Round($memPercent / 3.125)
        $memBar = ("█" * $memFilled) + ("░" * (32 - $memFilled))

        Write-Host "`r[$(Get-Date -Format 'HH:mm:ss')] GPU: $utilBar $($gpuUtil)%  |  MEM: $memBar $($memPercent)% ($memUsed/$memTotal MB)" -ForegroundColor Cyan -NoNewline
    }

    Start-Sleep -Seconds 5
    $monitor_count++

    # Verificar si el job terminó
    $jobStatus = Get-Job -Id $jobId -ErrorAction SilentlyContinue
    if ($jobStatus.State -eq "Completed" -or $jobStatus.State -eq "Failed") {
        Write-Host ""
        Write-Host ""
        Write-Host "✅ ENTRENAMIENTO COMPLETADO" -ForegroundColor Green
        Receive-Job -Id $jobId
        break
    }
}

Write-Host ""
Write-Host ""
Write-Host "📋 ESTADO FINAL:" -ForegroundColor Yellow
$finalJob = Get-Job -Id $jobId -ErrorAction SilentlyContinue
Write-Host "   Job ID: $jobId" -ForegroundColor White
Write-Host "   Estado: $($finalJob.State)" -ForegroundColor White
Write-Host "   Duración: $((Get-Date) - $finalJob.PSBeginTime)" -ForegroundColor White
Write-Host ""

if (Test-Path "outputs/oe3_simulations/simulation_summary.json") {
    Write-Host "✅ RESULTADOS DISPONIBLES EN:" -ForegroundColor Green
    Write-Host "   outputs/oe3_simulations/simulation_summary.json" -ForegroundColor Cyan
}
