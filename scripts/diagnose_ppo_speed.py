#!/usr/bin/env python3
"""
Diagnostico: Verifica por que model.learn() es 100x mas rapido de lo esperado
"""

from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)

def check_ppo_timing():
    """
    Verifica:
    1. Si model.learn() esta recibiendo los callbacks correctamente
    2. Si env.step() y env.reset() estan siendo llamados
    3. Si la GPU esta siendo utilizada
    """
    
    print('\n' + '='*100)
    print('[TIME]️  DIAGNOSTICO: ¿Por que model.learn() es 100x mas rapido?')
    print('='*100)
    
    print('\n🔍 Analisis de posibles causas:\n')
    
    causes = [
        {
            'num': 1,
            'name': 'callbacks no se ejecutan',
            'check': 'DetailedLoggingCallback y PPOMetricsCallback no estan siendo invocados',
            'impact': '[!]  Critico: Sin callbacks, loss/rewards no se calculan',
            'solution': 'Verificar que on_step() del callback se llame en CADA timestep'
        },
        {
            'num': 2,
            'name': 'env.step() no se computa completamente',
            'check': 'Observation, reward, done no se calculan (solo se retorna dummy data)',
            'impact': '[!]  Critico: Sin reward, PPO no tiene informacion para optimizar',
            'solution': 'Verificar que step() hace TODA la fisica del sistema (calculo CO2, balance energetico, etc)'
        },
        {
            'num': 3,
            'name': 'GPU no se usa para forward pass del policy',
            'check': 'Model esta en CPU en lugar de GPU (device="cuda" no se aplica)',
            'impact': '[X] critico: Forward pass deberia ser ~10x mas lento en CPU',
            'solution': 'Verificar que model.__init__ traduce poli a device correcto'
        },
        {
            'num': 4,
            'name': 'n_steps esta muy bajo (<1000)',
            'check': 'Si n_steps=128, solo hace 128 steps por update en lugar de 2048',
            'impact': '[!]  No es tan critico pero afecta eficiencia',
            'solution': 'Usar n_steps=2048 como esta configurado'
        },
        {
            'num': 5,
            'name': 'Entrenamiento se esta saltando epochs',
            'check': 'n_epochs=1 en lugar de n_epochs=3',
            'impact': '[!]  Entrenamiento menos estable pero mas rapido',
            'solution': 'Usar n_epochs=3 para actualizacion multiple del gradiente'
        },
    ]
    
    for cause in causes:
        print(f"{cause['num']}. ❓ {cause['name'].upper()}")
        print(f"   Sintoma: {cause['check']}")
        print(f"   Impacto: {cause['impact']}")
        print(f"   Solucion: {cause['solution']}\n")
    
    # Verificar config real
    print('\n' + '='*100)
    print('📋 VERIFICACION: Configuracion actual en PPOConfig')
    print('='*100 + '\n')
    
    try:
        # Agregar ruta
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from scripts.train.train_ppo_multiobjetivo import PPOConfig
        
        # Crear config
        config = PPOConfig(device='cuda')
        
        print(f'[OK] PPOConfig loaded')
        
        # Mostrar parametros clave
        import inspect
        init_source = inspect.getsource(config.__init__)
        
        # Regex search para n_steps, n_epochs, learning_rate, device
        import re
        
        checks = [
            ('device', r'self\.device\s*=\s*[\'"]?(\w+)[\'"]?'),
            ('n_steps', r'self\.n_steps\s*=\s*(\d+)'),
            ('batch_size', r'self\.batch_size\s*=\s*(\d+)'),
            ('n_epochs', r'self\.n_epochs\s*=\s*(\d+)'),
            ('learning_rate', r'self\.learning_rate\s*=\s*([\d.e-]+)'),
        ]
        
        for key, pattern in checks:
            match = re.search(pattern, init_source)
            if match:
                value = match.group(1)
                print(f'   [OK] {key:20s} = {value}')
            else:
                print(f'   [X] {key:20s} = NO ENCONTRADO')
        
        print('\n🎯 RECOMENDACION:\n')
        print('   Si model.learn() realmente tomo 2.6 minutos para 87,600 timesteps:')
        print('   =>  561 steps/sec en GPU es ANORMALMENTE RAPIDO')
        print('   =>  Deberia ser 5-10 steps/sec (dependiendo de callback overhead)')
        print('   ')
        print('   Causa mas probable: DetailedLoggingCallback/PPOMetricsCallback')
        print('   NO se estan ejecutando cada timestep.')
        print('   ')
        print('   Solucion: Verificar en model.learn() que callbacks estan registrados')
        print('   y que on_step() se llama DESPUES de cada env.step()')
        
    except Exception as e:
        print(f'[X] Error cargando config: {e}')
    
    print('\n' + '='*100 + '\n')

if __name__ == '__main__':
    check_ppo_timing()
