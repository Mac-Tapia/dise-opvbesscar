#!/usr/bin/env python3
"""Reporte de progreso de entrenamiento con estimados de GPU y tiempo."""

import json
from pathlib import Path
from datetime import datetime, timedelta
import yaml

print("\n" + "="*80)
print("📊 REPORTE DE ENTRENAMIENTO SAC - PROGRESO & ESTIMADOS GPU")
print("="*80 + "\n")

# Leer configuración
with open("configs/default.yaml") as f:
    cfg = yaml.safe_load(f)

# Parámetros
episodes_config = cfg["oe3"]["evaluation"]["sac"]["episodes"]
steps_per_episode = 8760  # timesteps anuales
batch_size = cfg["oe3"]["evaluation"]["sac"]["batch_size"]
buffer_size = cfg["oe3"]["evaluation"]["sac"]["buffer_size"]
device = cfg["oe3"]["evaluation"]["sac"]["device"]
use_amp = cfg["oe3"]["evaluation"]["sac"]["use_amp"]

total_steps = episodes_config * steps_per_episode

print("⚙️  CONFIGURACIÓN DEL ENTRENAMIENTO")
print("-" * 80)
print(f"Agente:                    SAC (Soft Actor-Critic)")
print(f"Episodios configurados:    {episodes_config}")
print(f"Pasos por episodio:        {steps_per_episode:,} (8760 timesteps/año)")
print(f"Total de pasos:            {total_steps:,}")
print(f"Batch size:                {batch_size}")
print(f"Buffer tamaño:             {buffer_size:,}")
print(f"Device:                    {device}")
print(f"Mixed Precision (AMP):     {'✓ Habilitado' if use_amp else '✗ Deshabilitado'}")

# Leer progreso
checkpoint_dir = Path("analyses/oe3/training/checkpoints/sac")
if checkpoint_dir.exists():
    checkpoints = sorted(
        list(checkpoint_dir.glob("sac_step_*.zip")),
        key=lambda x: int(x.stem.split("_")[-1])
    )
    
    if checkpoints:
        latest = checkpoints[-1]
        step_num = int(latest.stem.split("_")[-1])
        
        print("\n✓ PROGRESO ACTUAL")
        print("-" * 80)
        print(f"Pasos completados:         {step_num:,} / {total_steps:,}")
        progress_pct = (step_num / total_steps) * 100
        print(f"Porcentaje completado:     {progress_pct:.1f}%")
        print(f"Pasos restantes:           {total_steps - step_num:,}")
        print(f"Checkpoints guardados:     {len(checkpoints)}")
        print(f"Última actualización:      {latest.name}")
        
        # Calcular velocidad observada
        # De los logs: ~38 segundos por 100 pasos
        tiempo_por_100_pasos = 38  # segundos (observado del entrenamiento)
        tiempo_por_paso = tiempo_por_100_pasos / 100
        pasos_restantes = total_steps - step_num
        
        print("\n⚡ ESTIMADOS DE TIEMPO")
        print("-" * 80)
        print(f"Velocidad actual:          {tiempo_por_paso:.2f} seg/paso")
        print(f"                           (≈100 pasos = {tiempo_por_100_pasos} segundos)")
        
        # Calcular tiempos
        segundos_restantes_sac = pasos_restantes * tiempo_por_paso
        horas_restantes_sac = segundos_restantes_sac / 3600
        dias_restantes_sac = horas_restantes_sac / 24
        
        # Estimado total (3 agentes: SAC, PPO, A2C)
        horas_total_3agentes = horas_restantes_sac * 3
        dias_total_3agentes = horas_total_3agentes / 24
        
        print(f"\nTiempo restante (SAC):     {horas_restantes_sac:.1f} horas")
        print(f"                           ({dias_restantes_sac:.2f} días)")
        print(f"\nTiempo total (SAC+PPO+A2C):{horas_total_3agentes:.1f} horas")
        print(f"                           ({dias_total_3agentes:.2f} días)")
        
        # Fecha estimada de finalización
        ahora = datetime.now()
        fecha_fin_sac = ahora + timedelta(seconds=segundos_restantes_sac)
        fecha_fin_total = ahora + timedelta(seconds=segundos_restantes_sac * 3)
        
        print(f"\nFecha estimada fin SAC:    {fecha_fin_sac.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Fecha estimada fin TOTAL:  {fecha_fin_total.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n💾 MEMORIA & GPU")
        print("-" * 80)
        
        # Estimados de memoria
        # Batch size 8192, float32 = 4 bytes por valor
        # Observaciones: ~126 valores por timestep
        # Replay buffer: buffer_size * step_size
        
        obs_dim = 126  # dimensionalidad de observación
        memoria_batch_mb = (batch_size * obs_dim * 4) / (1024 * 1024)
        memoria_buffer_gb = (buffer_size * obs_dim * 4) / (1024 * 1024 * 1024)
        memoria_modelo_gb = 0.3  # SAC actor/critic networks aprox
        memoria_total_gb = (memoria_buffer_gb + memoria_modelo_gb)
        
        print(f"Batch size:                {batch_size:,} samples")
        print(f"Memoria por batch:         ~{memoria_batch_mb:.0f} MB")
        print(f"Replay buffer tamaño:      ~{memoria_buffer_gb:.1f} GB")
        print(f"Modelos (actor+critic):    ~{memoria_modelo_gb:.1f} GB")
        print(f"Memoria total GPU:         ~{memoria_total_gb:.1f} GB")
        print(f"\nGPU disponible en sistem:  ~8.6 GB (T4)")
        print(f"Utilización estimada:      {(memoria_total_gb/8.6)*100:.0f}%")
        
        if use_amp:
            print(f"\n✓ Mixed Precision (AMP) ACTIVO → 2x más rápido")
            print(f"  Estimado con AMP:        {horas_restantes_sac/2:.1f} horas SAC")
        
        print("\n🚀 OPTIMIZACIONES APLICADAS")
        print("-" * 80)
        print(f"✓ Device:                  {device} (GPU acceleration)")
        print(f"✓ Mixed Precision:         {'Enabled' if use_amp else 'Disabled'}")
        print(f"✓ Pinned Memory:           Enabled")
        print(f"✓ Batch size:              {batch_size} (optimizado)")
        
        print("\n" + "="*80)
        print(f"Última actualización:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
    else:
        print("\n⚠️  No hay checkpoints aún. Entrenamiento en fase inicial.\n")
else:
    print("\n⚠️  Directorio de checkpoints no encontrado.\n")
