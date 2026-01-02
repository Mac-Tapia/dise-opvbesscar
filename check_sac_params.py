from stable_baselines3 import SAC
import inspect

sig = inspect.signature(SAC.__init__)
params = list(sig.parameters.keys())
print("Parámetros de SAC de Stable-Baselines3:")
for i, param in enumerate(params):
    print(f"  {i+1}. {param}")
print(f"\nTotal de parámetros: {len(params)}")
print(f"\n¿Contiene 'use_amp'? {'use_amp' in params}")
print(f"¿Contiene 'amp'? {'amp' in params}")
print(f"¿Contiene 'device'? {'device' in params}")
