@echo off
REM A2C Training with Real OE2 Data - Windows Batch Runner
REM This script starts A2C training with full console monitoring in PowerShell

echo.
echo ================================================================================
echo A2C TRAINING WITH REAL OE2 DATA
echo ================================================================================
echo.
echo Data Configuration:
echo   - Solar: 4,162 kW from Iquitos (real timeseries)
echo   - EV Chargers: 128 with real demand profiles
echo   - BESS: 2,000 kWh / 1,200 kW
echo   - Objective: Minimize CO2 (0.4521 kg CO2/kWh)
echo.
echo Starting training in PowerShell...
echo.

REM Open new PowerShell window and run training
powershell -NoExit -Command "python train_a2c_final_real_data.py"
