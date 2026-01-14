#!/usr/bin/env python3
"""
Test rápido para verificar que la ventana móvil de rewards funciona correctamente.
"""
import sys
sys.path.insert(0, 'd:\\diseñopvbesscar\\src')

# Simular la clase del callback
class TestRewardWindow:
    def __init__(self):
        self.recent_rewards = []
        self.reward_window_size = 200
        self.reward_sum = 0.0
        self.reward_count = 0
    
    def add_reward(self, r):
        scaled_r = float(r) * 100.0
        self.reward_sum += scaled_r
        self.reward_count += 1
        # Agregar a ventana móvil
        self.recent_rewards.append(scaled_r)
        if len(self.recent_rewards) > self.reward_window_size:
            self.recent_rewards.pop(0)
    
    def get_avg_reward(self):
        if self.recent_rewards:
            return sum(self.recent_rewards) / len(self.recent_rewards)
        return 0.0
    
    def get_global_avg(self):
        return self.reward_sum / max(1, self.reward_count)

# Test
print("=" * 60)
print("TEST: Ventana Móvil vs Promedio Global")
print("=" * 60)

window = TestRewardWindow()

# Simular 500 pasos con rewards variando
import random
random.seed(42)

print("\nAgregando 500 rewards simulados...")
for i in range(500):
    # Simular rewards que mejoran con el tiempo
    base = 0.6
    variation = random.uniform(-0.1, 0.1) + (i / 1000)
    reward = base + variation
    window.add_reward(reward)

print(f"\n✓ Total rewards agregados: {window.reward_count}")
print(f"✓ Tamaño ventana actual: {len(window.recent_rewards)}")
print(f"✓ Tamaño ventana esperado: min({window.reward_count}, {window.reward_window_size})")

# Comparar promedios
global_avg = window.get_global_avg()
window_avg = window.get_avg_reward()

print(f"\n📊 RESULTADOS:")
print(f"   Promedio GLOBAL (todos los pasos): {global_avg:.4f}")
print(f"   Promedio VENTANA (últimos 200):    {window_avg:.4f}")
print(f"   Diferencia:                         {abs(window_avg - global_avg):.4f}")

# Verificar que son diferentes (si hay aprendizaje)
if abs(window_avg - global_avg) > 0.01:
    print(f"\n✅ CORRECTO: La ventana móvil es DIFERENTE del promedio global")
    print(f"   Esto permite ver cambios recientes en las recompensas")
else:
    print(f"\n⚠️  Los promedios son similares (esperado con rewards constantes)")

# Verificar tamaño correcto
if len(window.recent_rewards) == window.reward_window_size:
    print(f"✅ CORRECTO: Ventana limitada a {window.reward_window_size} elementos")
else:
    print(f"⚠️  Ventana tiene {len(window.recent_rewards)} elementos")

print("\n" + "=" * 60)
print("TEST COMPLETADO")
print("=" * 60)
