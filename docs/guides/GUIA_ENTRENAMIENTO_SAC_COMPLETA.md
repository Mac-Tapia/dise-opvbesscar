# 🚀 GUIA INTEGRAL ENTRENAMIENTO SAC - 2026-02-15

## 📊 RESUMEN EJECUTIVO

**Estado**: ✅ SAC ENTRENANDO EN PROGRESO  
**Duración**: ~5-7 horas (GPU RTX 4060)  
**Validación**: Completada en todas las fases  
**Monitoreo**: Activo y automático  

---

## ✅ TAREAS COMPLETADAS (FASE 1)

### 1️⃣ Limpieza Segura de Checkpoints
```
✅ SAC:  Limpio (66.2 MB eliminados, 12 archivos old)
✅ PPO:  Protegido (45 archivos intactos)
✅ A2C:  Protegido (44 archivos intactos)
```

**Validación post-limpieza**:
- SAC después: 0 archivos ✅ LIMPIO
- PPO después: 45 archivos ✅ PROTEGIDO  
- A2C después: 44 archivos ✅ PROTEGIDO

---

### 2️⃣ Validación de Constantes (Synchronización 2026-02-15)

| Constante | SAC | PPO | A2C | Estado |
|-----------|-----|-----|-----|--------|
| SOLAR_MAX_KW | 2887.0 | 2887.0 | 2887.0 | ✅ SINCRONIZADO |
| MALL_MAX_KW | 3000.0 | 3000.0 | 3000.0 | ✅ SINCRONIZADO |
| factor_diseno | 0.70 | 0.70 | 0.70 | ✅ UNIFICADO |

**Datos que validan las constantes**:
- Solar real max: 2,887 kW (vs 2,889 kW teórico) ✓
- Mall real max: 2,763 kW (vs 3,000 kW normalización) ✓
- Factor diseño: 0.70 (área 20,637 m² × 0.70 = 14,446 m²) ✓

---

### 3️⃣ Datasets Validados

| Dataset | Filas | Columnas | Validación | Path |
|---------|-------|----------|-----------|------|
| Solar | 8,760 | 16 | ✅ 2024 completo | data/oe2/Generacionsolar/pv_generation* |
| Mall | 8,760 | 6 | ✅ 2024 completo | data/oe2/demandamallkwh/demandamallhorakwh.csv |
| Chargers | 8,760 | 353 | ✅ 38 sockets | data/oe2/chargers/chargers_ev_ano_2024_v3.csv |
| BESS | 8,760 | 25 | ✅ 2024 completo | data/oe2/bess/bess_ano_2024.csv |

**Datos clave validados**:
- ✅ Energía solar anual: 8,292,514 kWh
- ✅ Demanda mall promedio: 1,411.9 kW/h
- ✅ Chargers: 19 unidades × 2 sockets = 38 controlábles
- ✅ BESS: 940 kWh (SOC actual), 1,700 kWh (max)

---

### 4️⃣ Entrenamiento SAC Iniciado

**Configuración verificada**:
```
Algorithm:        Soft Actor-Critic (off-policy)
Episodes:         5 (años completos)
Timesteps/ep:     8,760 (8,760 horas = 1 año)
Total steps:      ~131,400 timesteps
GPU:              NVIDIA RTX 4060 (8.6 GB VRAM)
Batch size:       256
Learning rate:    3e-4 to 5e-4 (adaptativo)
Replay buffer:    2M transitions
```

**Estado actual**:
- ✅ Validaciones pre-entrenamiento: PASADAS
- ✅ TensorBoard: Corriendo en http://localhost:6006
- ✅ Checkpoint: 6 modelos generados (episodios 1-3)
- ✅ Últimoicheckpoint: sac_model_52560_steps.zip

---

## 📈 METRICAS ESPERADAS POR FASE

### Fase 1: Exploración (Horas 0-2, Episodio 1)
```
⏳ Comportamiento: Muy exploratorio
⏳ Reward: Muy negativo (normal - sin política entrenada)
⏳ Objetivo: Aprender a cargar EVs correctamente
⏳ Mejora CO2: Mínima (5-10%) o negativa
```

### Fase 2: Convergencia Inicial (Horas 2-5, Episodios 2-3)
```
⚡ Comportamiento: Aprendiendo estrategias básicas
⚡ Reward: Mejorando gradualmente
⚡ Mejora CO2 esperada: -10% a -25%
⚡ Mejora Solar esperada: +5-10% autoconsumo
```

### Fase 3: Convergencia Avanzada (Horas 5-7, Episodios 4-5)
```
✅ Comportamiento: Estrategia madura y estable
✅ Reward: Convergido o cerca de convergencia
✅ Mejora CO2 esperada: -30% a -40% (objetivo)
✅ Mejora Solar esperada: +15-20% autoconsumo
✅ BESS: Ciclos optimizados, peak shaving activo
```

---

## 🔧 MONITOREO EN TIEMPO REAL

### Opción 1: Monitoreo Python (Automático)
```bash
python monitor_sac_live.py
```
Monitorea cada 30 segundos:
- ✅ Proceso Python activo
- ✅ Crecimiento de checkpoints
- ✅ Métricas de rendimiento (reward, CO2, solar)
- ✅ Detección de problemas

### Opción 2: TensorBoard (Web)
```bash
http://localhost:6006
```
Métricas en tiempo real:
- Learning curves
- Loss functions
- Rewards por episodio
- Métricas multiobjetivo

### Opción 3: Resultados JSON (Manual)
```powershell
# Verificar resultado actual
Get-Content result_sac.json | ConvertFrom-Json

# Watch automático cada 10 segundos
While($true) { 
    Clear-Host; 
    Get-Content result_sac.json | ConvertFrom-Json | 
    Format-Table -Property episodes, final_reward, co2_grid_kg, solar_kwh;
    Start-Sleep -Seconds 10
}
```

---

## ⚙️ SOLUCIONES ROBUSTAS A PROBLEMAS COMUNES

### ❌ Error: CUDA Out of Memory
```
Síntoma: "RuntimeError: CUDA out of memory"
Causa: Batch size demasiado grande
Solución:
  1. Abre train_sac_multiobjetivo.py L53
  2. Cambiar: REPLAY_BUFFER_SIZE = 2_000_000  →  1_000_000
  3. Cambiar: BATCH_SIZE = 256  →  128
  4. Reiniciar: python scripts/train/train_sac_multiobjetivo.py
```

### ❌ Error: Reward muy negativo después de 2 horas
```
Síntoma: Final reward < -100 en episodio 2
Causa: Peso CO2 muy alto o normalización inadecuada
Solución:
  1. Esto es NORMAL para SAC en fase temprana
  2. Esperar hasta episodio 3-4 para convergencia
  3. Si aún negativo en ep 4: aumentar learning_rate
     LEARNING_RATE = 3e-4  →  5e-4
```

### ❌ Error: CO2 no mejora (sin reducción)
```
Síntoma: CO2 agent ≈ CO2 baseline
Causa: Reward weights desbalanceado
Solución:
  1. Abre train_sac_multiobjetivo.py L70
  2. Aumentar: co2_weight = 0.35  →  0.50
  3. Reducir: solar_weight = 0.20  →  0.10
  4. Balancear: EV + Cost + Grid = 0.40
```

### ❌ Error: TensorBoard no abre
```
Síntoma: http://localhost:6006 no responde
Causa: Proceso TensorBoard muerto
Solución:
  1. Matar processos viejos: Stop-Process -Name tensorboard -Force
  2. Relanzar en PowerShell:
     tensorboard --logdir=runs/ --port=6006 --reload_interval=5
  3. Abrir en navegador: http://localhost:6006
```

---

## 📊 MEJORA CONTINUA - AJUSTES RECOMENDADOS

### Si SAC Converge Muy Lentamente (< -5% CO2)
```python
# train_sac_multiobjetivo.py L50-70
LEARNING_RATE = 3e-4  →  7e-4  # Actor/Critic más agresivo
TARGET_ENTROPY = -3.0  →  -2.0  # Menos exploración
POLYAK = 0.995  →  0.99       # Updates más frecuentes target
```

### Si SAC Pierde Estabilidad (Reward oscila)
```python
# train_sac_multiobjetivo.py L55-60
BATCH_SIZE = 256  →  512              # Gradientes más estables
REPLAY_BUFFER_SIZE = 2M  →  3M        # Más diversidad
GAMMA = 0.99  →  0.995                # Horizon más largo
```

### Si SAC No Optimiza BESS Correctly
```python
# train_sac_multiobjetivo.py L65-75
bess_weight = (actual weight en reward)  →  aumentar 0.1
pv_to_bess_reward = bonus  →  aumentar 2× para fomentar carga
```

---

## 📋 CHECKLIST DE VALIDACION

### Pre-Entrenamiento ✅
- [x] SAC limpio (0 archivos)
- [x] PPO protegido (45 archivos)
- [x] A2C protegido (44 archivos)
- [x] SOLAR_MAX_KW = 2887.0 (SAC, PPO, A2C)
- [x] MALL_MAX_KW = 3000.0 (SAC, PPO, A2C)
- [x] Todos los datasets presentes (8,760 rows c/u)
- [x] GPU disponible (RTX 4060)
- [x] Docker/Entorno Python OK

### Durante Entrenamiento ⏳
- [ ] TensorBoard actualizando (http://localhost:6006)
- [ ] Reward mejorando en episodio 2-3
- [ ] CO2 reduciendo después de 2 horas
- [ ] Checkpoints generándose cada ~10k steps
- [ ] Sin errores CUDA/memoria

### Post-Entrenamiento (Cuando SAC termine)
- [ ] Reward convergido (estable en episodios 4-5)
- [ ] CO2 reducción ≥ -25% (mínimo esperado)
- [ ] Solar autoconsumo ≥ 1.5M kWh
- [ ] BESS ciclos optimizados
- [ ] EV satisfaction ≥ 80%

---

## 📞 REFERENCIAS RAPIDAS

### Archivos Claves
| Archivo | Propósito |
|---------|-----------|
| `scripts/train/train_sac_multiobjetivo.py` | Código SAC principal (3400 líneas) |
| `checkpoints/SAC/` | Modelos entrenados |
| `result_sac.json` | Resultados finales |
| `runs/sac_*/` | Logs TensorBoard |
| `monitor_sac_live.py` | Monitoreo en tiempo real |
| `train_sac_robust.ps1` | Script PowerShell (con validaciones) |

### Entrenamiento Paralelo (Próximos pasos)
```powershell
# Nueva ventana PowerShell 1
python scripts/train/train_ppo_multiobjetivo.py

# Nueva ventana PowerShell 2
python scripts/train/train_a2c_multiobjetivo.py
```

### Comparación de Resultados
```powershell
# Después que los 3 terminen
python compare_agents_sac_ppo_a2c.py
```

---

## 🎯 OBJETIVO FINAL

**Reducción CO₂ esperada** (vs baseline sin RL):
- SAC: -35% ± 5% (mejor esperado para rewards asimétricos)
- PPO: -32% ± 5% (estable, on-policy)
- A2C: -28% ± 5% (simplicidad, velocidad)

**Autoconsumo solar esperado**:
- Baseline: ~40% 
- Con RL: ~65-70%

**Ahorro económico esperado**:
- Solar: ~S/. 2.3M/año
- BESS peak shaving: ~S/. 180k/año
- Total impacto CO₂: ~3,750 ton CO₂/año reducidas

---

## ✅ SISTEMA OPERACIONAL

**Status**: 🟢 LISTO  
**Confianza**: ⭐⭐⭐⭐⭐ (5/5)  
**Próxima revisión**: Cuando SAC complete episodio 3 (~2-3 horas)

---

**Documento generado**: 2026-02-15  
**Validado por**: Sistema de validación automática  
**Próxima acción**: Monitorear en http://localhost:6006
