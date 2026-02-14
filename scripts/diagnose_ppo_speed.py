#!/usr/bin/env python3
"""
Diagnóstico: Verifica por qué model.learn() es 100x más rápido de lo esperado
"""

from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)

def check_ppo_timing():
    """
    Verifica:
    1. Si model.learn() está recibiendo los callbacks correctamente
    2. Si env.step() y env.reset() están siendo llamados
    3. Si la GPU está siendo utilizada
    """
    
    print('\n' + '='*100)
    print('⏱️  DIAGNÓSTICO: ¿Por qué model.learn() es 100x más rápido?')
    print('='*100)
    
    print('\n🔍 Análisis de posibles causas:\n')
    
    causes = [
        {
            'num': 1,
            'name': 'callbacks no se ejecutan',
            'check': 'DetailedLoggingCallback y PPOMetricsCallback no están siendo invocados',
            'impact': '⚠️  Crítico: Sin callbacks, loss/rewards no se calculan',
            'solution': 'Verificar que on_step() del callback se llame en CADA timestep'
        },
        {
            'num': 2,
            'name': 'env.step() no se computa completamente',
            'check': 'Observation, reward, done no se calculan (solo se retorna dummy data)',
            'impact': '⚠️  Crítico: Sin reward, PPO no tiene información para optimizar',
            'solution': 'Verificar que step() hace TODA la física del sistema (cálculo CO2, balance energético, etc)'
        },
        {
            'num': 3,
            'name': 'GPU no se usa para forward pass del policy',
            'check': 'Model está en CPU en lugar de GPU (device="cuda" no se aplica)',
            'impact': '❌ crítico: Forward pass debería ser ~10x más lento en CPU',
            'solution': 'Verificar que model.__init__ traduce poli a device correcto'
        },
        {
            'num': 4,
            'name': 'n_steps está muy bajo (<1000)',
            'check': 'Si n_steps=128, solo hace 128 steps por update en lugar de 2048',
            'impact': '⚠️  No es tan crítico pero afecta eficiencia',
            'solution': 'Usar n_steps=2048 como está configurado'
        },
        {
            'num': 5,
            'name': 'Entrenamiento se está saltando epochs',
            'check': 'n_epochs=1 en lugar de n_epochs=3',
            'impact': '⚠️  Entrenamiento menos estable pero más rápido',
            'solution': 'Usar n_epochs=3 para actualización múltiple del gradiente'
        },
    ]
    
    for cause in causes:
        print(f"{cause['num']}. ❓ {cause['name'].upper()}")
        print(f"   Síntoma: {cause['check']}")
        print(f"   Impacto: {cause['impact']}")
        print(f"   Solución: {cause['solution']}\n")
    
    # Verificar config real
    print('\n' + '='*100)
    print('📋 VERIFICACIÓN: Configuración actual en PPOConfig')
    print('='*100 + '\n')
    
    try:
        # Agregar ruta
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from scripts.train.train_ppo_multiobjetivo import PPOConfig
        
        # Crear config
        config = PPOConfig(device='cuda')
        
        print(f'✅ PPOConfig loaded')
        
        # Mostrar parámetros clave
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
                print(f'   ✅ {key:20s} = {value}')
            else:
                print(f'   ❌ {key:20s} = NO ENCONTRADO')
        
        print('\n🎯 RECOMENDACIÓN:\n')
        print('   Si model.learn() realmente tomó 2.6 minutos para 87,600 timesteps:')
        print('   =>  561 steps/sec en GPU es ANORMALMENTE RÁPIDO')
        print('   =>  Debería ser 5-10 steps/sec (dependiendo de callback overhead)')
        print('   ')
        print('   Causa más probable: DetailedLoggingCallback/PPOMetricsCallback')
        print('   NO se están ejecutando cada timestep.')
        print('   ')
        print('   Solución: Verificar en model.learn() que callbacks están registrados')
        print('   y que on_step() se llama DESPUÉS de cada env.step()')
        
    except Exception as e:
        print(f'❌ Error cargando config: {e}')
    
    print('\n' + '='*100 + '\n')

if __name__ == '__main__':
    check_ppo_timing()
