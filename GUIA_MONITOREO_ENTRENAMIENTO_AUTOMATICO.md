# GUÍA RÁPIDA: Monitoreo del Entrenamiento Automático
**Uso**: Mientras el entrenamiento está ejecutándose en background

---

## 1. ESTADO RÁPIDO (Terminal)

```bash
# Ver último agente ejecutándose
tail -20 <path_a_logs>/oe3_simulate.log | grep -E "\[Uncontrolled\]|\[SAC\]|\[PPO\]|\[A2C\]" | tail -1

# Ver progreso por agente
for agent in Uncontrolled SAC PPO A2C; do
  if [ -f "outputs/oe3/simulations/result_$agent.json" ]; then
    echo "$agent: $(cat outputs/oe3/simulations/result_$agent.json | python -c "import json, sys; d=json.load(sys.stdin); print(f\"{d['steps']}/8760 steps = {d['simulated_years']:.1f} años\")")"
  fi
done
```

---

## 2. MONITOREO EN TIEMPO REAL

### Terminal 1: Ver logs
```bash
tail -f <path_logs> | grep -E "\[paso\]|\[ERROR\]|\[CO2\]|\[RESUME\]"
```

### Terminal 2: Ver checkpoints guardados
```bash
watch -n 10 'echo "=== SAC ===" && ls -lh checkpoints/sac/*.zip 2>/dev/null | wc -l && echo && echo "=== PPO ===" && ls -lh checkpoints/ppo/*.zip 2>/dev/null | wc -l && echo && echo "=== A2C ===" && ls -lh checkpoints/a2c/*.zip 2>/dev/null | wc -l'
```

### Terminal 3: Resultados parciales
```bash
while true; do
  clear
  echo "=== RESULTADOS PARCIALES ==="
  for f in outputs/oe3/simulations/result_*.json; do
    agent=$(basename "$f" | sed 's/result_//;s/.json//')
    if [ -f "$f" ]; then
      python -c "import json; d=json.load(open('$f')); print(f'{agent:15}: {d[\"steps\"]:5}/8760 steps | CO2: {d[\"carbon_kg\"]/1e6:7.2f}M kg')"
    fi
  done
  sleep 5
done
```

---

## 3. SEÑALES DE PROGRESO ESPERADAS

### Uncontrolled (5-10 min)
```
[Uncontrolled] paso 500 / 8760    ← ~3 min
[Uncontrolled] paso 1000 / 8760   ← ~6 min
[Uncontrolled] paso 1500 / 8760   ← ~9 min
... completar ...
[EPISODE] Ejecutó 8760 pasos (episodio completo)
```

### SAC (15-20 min per episodio)
```
[SAC] Episodio 1/5 iniciando...
[SAC] paso 500 / 8760
[SAC] paso 1000 / 8760
[SAC] Entrenamiento acumulado: 1000 steps
[SAC] Mean reward: X.XXX
[SAC] Checkpoint guardado: checkpoints/sac/sac_step_1000.zip
... (repetir para episodios 2-5) ...
[SAC] Episodio 5/5 completado
```

### PPO (20-30 min por entrenamiento)
```
[PPO] Iniciando entrenamiento con 87600 timesteps
[PPO] paso 1000 / 87600
[PPO] paso 2000 / 87600
[PPO] Checkpoint guardado: checkpoints/ppo/ppo_step_1000.zip
... continue ...
```

### A2C (15-25 min)
```
[A2C] Iniciando entrenamiento con 87600 timesteps
[A2C] Episodio 1/10 iniciando
... continue ...
```

---

## 4. SEÑALES DE ERROR A VIGILAR

| Error | Significado | Acción |
|-------|-----------|--------|
| `[ERROR] SAC could not be created` | Fallback a Uncontrolled | Continúa automáticamente |
| `GPU out of memory` | VRAM insuficiente | Usar device=cpu o reducir batch_size |
| `NaN` en rewards | Cálculo inestable | Revisar cálculos CO2 o recompensa |
| `Checkpoint dir not found` | Falta crear directorio | Script lo hace automáticamente |
| `null` en pv_bess_uncontrolled | Serialización JSON | YA CORREGIDO en esta versión |
| `KeyboardInterrupt` | Entrenamiento interrumpido | Resume desde checkpoint siguiente ejecución |

---

## 5. CUANDO TERMINA (VALIDACIÓN FINAL)

```bash
# 1. Ejecutar validación
python scripts/validate_training_integrity.py --output-dir outputs/oe3/simulations

# Esperado:
# ✅ VALIDACIÓN COMPLETA: SISTEMA SÓLIDO Y LISTO

# 2. Ver tabla CO2
cat outputs/oe3/simulations/co2_comparison.md

# Esperado:
# | Escenario                    | CO2_kg    | Reduccion_vs_grid_kg | Reduccion_vs_base_pct |
# |------------------------------|-----------|----------------------|----------------------|
# | Grid-only + tailpipe         | 7.4M      | 0.0                  | 0.0%                 |
# | Baseline PV+BESS sin control | 5.71M     | 1.69M                | 22.8%                |
# | SAC                          | 4.2M      | 3.2M                 | 42.8%                |
# | PPO                          | 4.0M      | 3.4M                 | 45.9%                |
# | A2C                          | 4.3M      | 3.1M                 | 41.9%                |

# 3. Verificar baseline guardado
python -c "import json; s=json.load(open('outputs/oe3/simulations/simulation_summary.json')); b=s['pv_bess_uncontrolled']; print(f'Baseline: {b[\"agent\"]} | {b[\"steps\"]} steps | CO2: {b[\"carbon_kg\"]/1e6:.2f}M kg')"

# Esperado:
# Baseline: Uncontrolled | 8760 steps | CO2: 5.71M kg

# 4. Comprobación final
ls -lh outputs/oe3/simulations/
# Esperado: 12 archivos (3 por agente × 4 agentes)
# - result_*.json (4 archivos)
# - timeseries_*.csv (4 archivos)  
# - trace_*.csv (4 archivos)
```

---

## 6. PARÁMETROS DE INTERÉS

### CO2 Metrics
- `grid_import_kwh`: Energía importada del grid (↓ es mejor)
- `pv_generation_kwh`: Energía solar generada
- `carbon_kg`: CO2 total (↓ es mejor, objetivo principal)

### Control Quality
- `ev_charging_kwh`: Energía a motos/mototaxis (↑ es mejor)
- `reward_co2_mean`: Penalización CO2 media (-1 a +1)
- `reward_solar_mean`: Consumo solar medio (0 a +1, ↑ es mejor)

### Progress
- `steps`: Timesteps ejecutados (objetivo: 8760 = 1 año)
- `simulated_years`: Años simulados (objetivo: 1.0 para baseline, 2+ para SAC/PPO)

---

## 7. SI ALGO FALLA

### Opción A: Reintentar desde Último Checkpoint
```bash
# El script automáticamente:
# 1. Verifica si existe checkpoint en checkpoints/{sac,ppo,a2c}/
# 2. Si existe, resume desde último step
# 3. Si no existe, comienza desde cero

# Solo ejecuta el script nuevamente:
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

### Opción B: Limpiar y Reiniciar Desde Cero
```bash
# Eliminar checkpoints y resultados viejos
rm -rf checkpoints/
rm -rf outputs/oe3/simulations/result_*.json

# Ejecutar nuevamente
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

### Opción C: Ejecutar Solo Un Agente
```bash
# Para testear si un agente específico funciona:
python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac --episodes 1

# O directamente en simulate.py:
python -c "
from src.iquitos_citylearn.oe3.simulate import simulate
from pathlib import Path
result = simulate(
    schema_path=Path('data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json'),
    agent_name='sac',
    out_dir=Path('outputs/oe3/simulations'),
    training_dir=None,
    carbon_intensity_kg_per_kwh=0.4521,
    seconds_per_time_step=3600,
    sac_episodes=1,
    seed=42,
)
print(f'Agent: {result.agent}, CO2: {result.carbon_kg}')
"
```

---

## 8. ESTADO A DIFERENTE HORA

**Comenzó a**: 2026-01-30 13:06:37  
**Uncontrolled completado**: ~13:15-13:20 (10-15 min)  
**SAC completado**: ~13:50-14:10 (30-50 min)  
**PPO completado**: ~14:40-15:10 (30-50 min)  
**A2C completado**: ~15:10-15:40 (30-50 min)  
**Summary generado**: ~15:50 (esperado)

---

## 9. QUICK REFERENCE

| Acción | Comando |
|--------|---------|
| Ver progreso rápido | `ls -lh outputs/oe3/simulations/*.json` |
| Ver último log | `tail -50 <logs>` |
| Ver CO2 baseline | `python -c "import json; print(json.load(open('outputs/oe3/simulations/result_Uncontrolled.json'))['carbon_kg'])"` |
| Validar integridad | `python scripts/validate_training_integrity.py` |
| Ver tabla CO2 | `cat outputs/oe3/simulations/co2_comparison.md` |
| Contar checkpoints | `find checkpoints -name "*.zip" \| wc -l` |
| Limpiar resultados | `rm -rf outputs/oe3/simulations/result_*.json` |
| Limpiar checkpoints | `rm -rf checkpoints/` |

---

## 10. CONTACTO / SOPORTE

Si hay problemas durante el entrenamiento:

1. **Check logs primero**: `tail -100 <logs>` para contexto
2. **Ejecutar validador**: `python scripts/validate_training_integrity.py` para diagnóstico
3. **Opción fallback**: Agentes falidos usan Uncontrolled automáticamente
4. **Resume capability**: Checkpoints guardados cada 1000 steps

✅ **SISTEMA DISEÑADO PARA SER RESILIENTE**
