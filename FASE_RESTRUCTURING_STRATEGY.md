#!/usr/bin/env python3
"""
Restructuración del orden de evaluación de 6 fases BESS (v5.9.2)

PRINCIPIO: Mantener las 6 fases exactamente como están, solo cambiar el ORDEN DE E EVALUACIÓN

PROBLEMA:
- FASE 2 (carga) se ejecuta en horas 9-17h y marca bess_action_assigned=True
- Luego FASE 4/5 (descarga) no pueden ejecutarse porque validación 'not bess_action_assigned[h]' previene

SOLUCIÓN:
- Evaluar FASE 4/5 (descarga) PRIMERO
- Solo evaluar FASE 1/2/3 (carga) si NO hay descarga en esa hora
- Mantener todos los detalles de cada fase intactos

ESTRUCTURA NUEVA DEL LOOP (por hora):
1. ¿Es fuera de horario operativo (22h-6h)? → FASE 6 (REPOSO)
2. ¿Hay descarga posible (FASE 4/5)?
   ├─ FASE 4: ¿PV < MALL y MALL > 1900 kW? → DESCARGAR BESS
   └─ FASE 5: ¿EV deficit (PV insuficiente)? → DESCARGAR BESS
3. Si NO hay descarga en hora:
   ├─ FASE 1: ¿Hora 6-9 (antes EV abre)? → CARGAR BESS
   ├─ FASE 2: ¿Hora 9+ y SOC < 99%? → CARGAR BESS en paralelo con EV
   └─ FASE 3: ¿SOC >= 99%? → HOLDING (mantener sin carga/descarga)

CAMBIOS A bess.py:
- Mover bloque FASE 4/5 ANTES de FASE 1/2/3
- Agregar validación: if not bess_action_assigned[h] para FASE 1/2/3
- Remover validación: 'not bess_action_assigned[h]' de FASE 4/5 (ya se evaluaron primero)
"""

print(__doc__)
print("\nEsta es la estrategia a implementar en bess.py:")
print("- MANTENER 6 fases intactas")
print("- CAMBIAR orden de evaluación")
print("- RESULTADO: Descarga tiene máxima prioridad, carga es fallback")
