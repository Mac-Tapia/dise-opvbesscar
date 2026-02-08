#!/usr/bin/env python3
"""Callback mejorado para mostrar motos/mototaxis por iteración en entrenamiento."""

template = '''
# ============================================================================
# CALLBACK MEJORADO: LOGGING DE MOTOS/MOTOTAXIS POR ITERACIÓN
# ============================================================================

class ImprovedVehicleLoggingCallback(BaseCallback):
    """Callback que muestra motos/mototaxis cargando en cada iteración."""
    
    def __init__(self, verbose=0, log_interval=1000):
        super().__init__(verbose)
        self.log_interval = log_interval
        self.episode_motos = 0
        self.episode_mototaxis = 0
        self.total_steps = 0
    
    def _on_step(self) -> bool:
        """Llamado después de cada step."""
        self.total_steps += 1
        
        # Extraer acciones del agente
        if hasattr(self.model, 'env') and hasattr(self.model.env, 'env'):
            env = self.model.env.env
            
            # Acciones actuales (último paso)
            # Mototaxis: sockets 0-27 (28 sockets)
            # Motos: sockets 28-127 (100 sockets)
            
            # Contar cargadores activos (action > 0.5 = activo)
            last_action = getattr(env, 'last_action', None)
            if last_action is not None:
                motos_active = np.sum(last_action[29:129] > 0.5)  # indices 29-129 = sockets 28-127
                mototaxis_active = np.sum(last_action[1:29] > 0.5)  # indices 1-29 = sockets 0-27
                
                self.episode_motos += motos_active
                self.episode_mototaxis += mototaxis_active
                
                # Log cada log_interval pasos
                if self.total_steps % self.log_interval == 0:
                    episode = self.model.num_timesteps // 8760
                    progreso = (self.total_steps % 8760) / 8760 * 100
                    print(f"  Step {self.total_steps:>7d} | Ep {episode:>2d} | "
                          f"Progreso {progreso:>5.1f}% | "
                          f"Motos: {motos_active:>3d}/112 | "
                          f"Mototaxis: {mototaxis_active:>3d}/16")
        
        return True
    
    def _on_episode_end(self) -> None:
        """Llamado al final de cada episodio."""
        episode = self.model.num_timesteps // 8760
        
        # Calcular promedios
        motos_por_hora = self.episode_motos / 8760
        mototaxis_por_hora = self.episode_mototaxis / 8760
        motos_por_dia = motos_por_hora * 24
        mototaxis_por_dia = mototaxis_por_hora * 24
        
        print(f"\\n  {'='*70}")
        print(f"  EPISODIO {episode} COMPLETADO - VEHÍCULOS CARGADOS")
        print(f"  {'='*70}")
        print(f"    Motos:")
        print(f"      • Total episodio: {self.episode_motos:>10,.0f}")
        print(f"      • Promedio/hora:  {motos_por_hora:>10.1f}")
        print(f"      • Promedio/día:   {motos_por_dia:>10.1f}")
        print(f"    Mototaxis:")
        print(f"      • Total episodio: {self.episode_mototaxis:>10,.0f}")
        print(f"      • Promedio/hora:  {mototaxis_por_hora:>10.1f}")
        print(f"      • Promedio/día:   {mototaxis_por_dia:>10.1f}")
        print(f"  {'='*70}\\n")
        
        # Reset para próximo episodio
        self.episode_motos = 0
        self.episode_mototaxis = 0
'''

print("\n" + "="*80)
print("📝 CALLBACK MEJORADO: LOGGING DE VEHÍCULOS")
print("="*80 + "\n")

print(template)

print("\n" + "="*80)
print("✅ CÓMO USAR ESTE CALLBACK:")
print("="*80 + "\n")

print("""
En train_ppo_multiobjetivo.py / train_a2c_multiobjetivo.py / train_sac_multiobjetivo.py:

# Crear callback
vehicle_callback = ImprovedVehicleLoggingCallback(log_interval=1000)

# Combinar con otros callbacks
callbacks = CallbackList([checkpoint_callback, vehicle_callback, logging_callback])

# Usar en learn()
model.learn(
    total_timesteps=TOTAL_TIMESTEPS,
    callback=callbacks,
    progress_bar=True
)

OUTPUT ESPERADO:
  Step    1000 | Ep  0 | Progreso  11.4% | Motos:  42/112 | Mototaxis:   8/16
  Step    2000 | Ep  0 | Progreso  22.8% | Motos:  45/112 | Mototaxis:   7/16
  ...
  
  ======================================================================
  EPISODIO 1 COMPLETADO - VEHÍCULOS CARGADOS
  ======================================================================
    Motos:
      • Total episodio:      359,845
      • Promedio/hora:             41.1
      • Promedio/día:            987.1
    Mototaxis:
      • Total episodio:       51,406
      • Promedio/hora:              5.9
      • Promedio/día:            141.0
  ======================================================================
""")

print("\n" + "="*80)
print("INTEGRACIÓN RECOMENDADA:")
print("="*80 + "\n")

print("""
✅ Paso 1: Copiar ImprovedVehicleLoggingCallback a train_ppo_multiobjetivo.py
✅ Paso 2: Copiar ImprovedVehicleLoggingCallback a train_a2c_multiobjetivo.py
✅ Paso 3: Copiar ImprovedVehicleLoggingCallback a train_sac_multiobjetivo.py
✅ Paso 4: Agregar en callbacks = CallbackList([...., vehicle_callback])
✅ Paso 5: Ejecutar entrenamiento

Resultado: Verás motos/mototaxis por iteración y episodio
""")
