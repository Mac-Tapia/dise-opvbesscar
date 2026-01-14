#!/usr/bin/env python3
"""
Script para reintenteur PPO en CPU con diagnostico completo de errores
"""

import sys
import os
import traceback
from pathlib import Path

# Agregar el proyecto al path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("\n" + "="*80)
    print("DIAGNOSTICO: Reintentando PPO en CPU con captura completa de error")
    print("="*80 + "\n")
    
    try:
        from scripts._common import load_all
        from iquitos_citylearn.oe3.simulate import simulate
        
        print("[OK] Importando configuracion...")
        cfg, rp = load_all("configs/default.yaml")
        
        print("[OK] Configuracion cargada:")
        print(f"  - Dataset: {cfg['oe3']['dataset']['name']}")
        print(f"  - PPO timesteps: {cfg['oe3']['evaluation'].get('ppo', {}).get('timesteps', 'No especificado')}")
        print(f"  - PPO device: {cfg['oe3']['evaluation'].get('ppo', {}).get('device', 'auto')}")
        
        # Cambiar device a CPU para PPO
        if 'ppo' not in cfg['oe3']['evaluation']:
            cfg['oe3']['evaluation']['ppo'] = {}
        
        cfg['oe3']['evaluation']['ppo']['device'] = 'cpu'
        
        print("\n[OK] Configuracion modificada:")
        print(f"  - PPO device cambiado a: CPU (para diagnostico)")
        print(f"  - Esto permitira capturar el error completo sin interferencia GPU")
        
        # Construir rutas
        dataset_name = cfg["oe3"]["dataset"]["name"]
        processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name
        
        print(f"\n[OK] Dataset path: {processed_dataset_dir}")
        print(f"  - Existe: {processed_dataset_dir.exists()}")
        
        if not processed_dataset_dir.exists():
            print("\n[WARN] Dataset no encontrado - es necesario ejecutar run_oe3_build_dataset primero")
            return
        
        schema_pv = processed_dataset_dir / "schema_pv_bess.json"
        if not schema_pv.exists():
            print(f"\n[WARN] Schema no encontrado: {schema_pv}")
            return
        
        # Configuración para PPO
        out_dir = rp.outputs_dir / "oe3" / "simulations"
        training_dir = rp.analyses_dir / "oe3" / "training"
        out_dir.mkdir(parents=True, exist_ok=True)
        training_dir.mkdir(parents=True, exist_ok=True)
        
        ppo_cfg = cfg['oe3']['evaluation'].get('ppo', {})
        ppo_timesteps = int(ppo_cfg.get('timesteps', 10000))  # Reducido para diagnóstico
        
        print(f"\n[START] Iniciando simulacion PPO (10k timesteps en CPU)...")
        print(f"  - Esto deberia capturar cualquier error sin interferencia GPU")
        print(f"  - Tiempo estimado: 10-15 minutos")
        print("\n")
        
        result = simulate(
            schema_path=schema_pv,
            agent_name="PPO",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
            seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
            ppo_timesteps=ppo_timesteps,
            ppo_device='cpu',
            ppo_checkpoint_freq_steps=500,
            ppo_n_steps=int(ppo_cfg.get('n_steps', 1024)),
            ppo_batch_size=int(ppo_cfg.get('batch_size', 128)),
            ppo_use_amp=False,  # Desactivar AMP en CPU
            ppo_target_kl=ppo_cfg.get('target_kl'),
            ppo_kl_adaptive=bool(ppo_cfg.get('kl_adaptive', True)),
            ppo_log_interval=int(ppo_cfg.get('log_interval', 1000)),
            deterministic_eval=True,
            seed=int(cfg["project"].get("seed", 42)),
        )
        
        print("\n[OK] Simulacion PPO completada exitosamente")
        print(f"  - Resultado: {result}")
        
    except Exception as e:
        print("\n" + "="*80)
        print("[ERROR] ERROR CAPTURADO - TRACEBACK COMPLETO:")
        print("="*80 + "\n")
        
        # Imprimir traceback completo
        traceback.print_exc()
        
        # Información adicional del error
        print("\n" + "="*80)
        print("[INFO] INFORMACION DEL ERROR:")
        print("="*80)
        print(f"Tipo de excepcion: {type(e).__name__}")
        print(f"Mensaje: {str(e)}")
        print(f"Archivo: {getattr(e, '__traceback__', 'N/A').tb_frame.f_code.co_filename if hasattr(e, '__traceback__') else 'N/A'}")
        print(f"Linea: {getattr(e, '__traceback__', 'N/A').tb_lineno if hasattr(e, '__traceback__') else 'N/A'}")
        
        # Análisis de causa probable
        print("\n" + "="*80)
        print("[ANALYSIS] ANALISIS DE CAUSA PROBABLE:")
        print("="*80)
        
        error_str = str(e).lower()
        if 'memory' in error_str or 'oom' in error_str:
            print("  -> Causa probable: FALTA DE MEMORIA")
            print("     Solucion: Reducir batch_size, n_steps, o timesteps")
            
        elif 'device' in error_str or 'cuda' in error_str or 'gpu' in error_str:
            print("  -> Causa probable: PROBLEMA CON GPU/CUDA")
            print("     Solucion: Usar CPU (ya configurado)")
            
        elif 'citylearn' in error_str or 'environment' in error_str or 'env' in error_str:
            print("  -> Causa probable: PROBLEMA CON ENTORNO CITYLEARN")
            print("     Solucion: Verificar schema_pv_bess.json y archivos de datos")
            
        elif 'timeout' in error_str or 'hang' in error_str:
            print("  -> Causa probable: TIMEOUT O BLOQUEO")
            print("     Solucion: Reducir timesteps o revisar datos de entrada")
            
        else:
            print("  -> Causa desconocida - revisar traceback arriba")
        
        print("\n" + "="*80)
        print("[NEXT] PROXIMOS PASOS RECOMENDADOS:")
        print("="*80)
        print("  1. Analizar el traceback arriba para identificar la linea exacta del error")
        print("  2. Verificar que el dataset CityLearn esta correctamente construido")
        print("  3. Revisar los archivos de datos en data/processed/citylearn/")
        print("  4. Considerar ejecutar con even fewer timesteps (5k) para test rapido")
        print("  5. Si es MemoryError, reducir: batch_size, n_steps, ppo_timesteps")
        
        sys.exit(1)

if __name__ == '__main__':
    main()
