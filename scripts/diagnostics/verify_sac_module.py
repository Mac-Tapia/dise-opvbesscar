#!/usr/bin/env python3
"""
Verificación final: Importar el módulo real y confirmar que tiene ventana móvil.
"""
import sys
import inspect

sys.path.insert(0, 'd:\\diseñopvbesscar\\src')

from iquitos_citylearn.oe3.agents.sac import SACAgent

print("=" * 60)
print("VERIFICACIÓN: Módulo SAC cargado correctamente")
print("=" * 60)

# Obtener código fuente del método _train_sb3_sac
source = inspect.getsource(SACAgent._train_sb3_sac)

# Buscar la presencia de código de ventana móvil
checks = {
    "recent_rewards": "recent_rewards" in source,
    "reward_window_size": "reward_window_size" in source,
    "ventana móvil presente": "Ventana móvil para reward_avg" in source or "recent_rewards.append" in source,
    "pop de ventana": "recent_rewards.pop(0)" in source,
    "cálculo ventana": "sum(self.recent_rewards)" in source
}

print("\n✓ Módulo importado desde:", inspect.getfile(SACAgent))
print(f"✓ Archivo modificado: {inspect.getfile(SACAgent)}")

print(f"\n📋 VERIFICACIÓN DE CÓDIGO:")
for check, result in checks.items():
    status = "✅" if result else "❌"
    print(f"   {status} {check}: {result}")

# Verificar que el método existe y tiene la implementación correcta
all_passed = all(checks.values())

if all_passed:
    print(f"\n{'='*60}")
    print("✅ ¡VERIFICACIÓN EXITOSA!")
    print("   El código de ventana móvil está correctamente implementado")
    print("   y el módulo Python lo tiene cargado.")
    print(f"{'='*60}")
else:
    print(f"\n{'='*60}")
    print("❌ ERROR: Faltan componentes de ventana móvil")
    print(f"{'='*60}")

# Mostrar fragmento del código relevante
print("\n📄 FRAGMENTO DE CÓDIGO RELEVANTE:")
print("-" * 60)
lines = source.split('\n')
for i, line in enumerate(lines):
    if 'recent_rewards' in line or 'reward_window_size' in line:
        # Mostrar línea con contexto
        start = max(0, i-1)
        end = min(len(lines), i+2)
        for j in range(start, end):
            marker = ">>>" if j == i else "   "
            print(f"{marker} {lines[j]}")
        print()
        if i > 50:  # Solo mostrar primeras ocurrencias
            break
