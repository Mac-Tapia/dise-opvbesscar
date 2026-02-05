# GUÍA DE EJECUCIÓN RÁPIDA - AGENTES RL

## ⚡ INICIO INMEDIATO

### Opción A: Test Rápido (1 minuto para verificar sistema)
```bash
python train_sac_test.py
```
✓ Verifica: Dataset, Environment, SAC agent
✓ Entrena: 5,000 timesteps
✓ Esperado: "STATUS: ✓ SAC FUNCIONANDO CORRECTAMENTE"

---

### Opción B: SAC Completo (RECOMENDADO - 2h CPU)
```bash
python train_sac_production.py
```
✓ Entrena: 100,000 timesteps (11 episodios)
✓ Checkpoints: Guardados cada 50k steps
✓ Output: `checkpoints/SAC/sac_final_model.zip`
✓ Métricas: `outputs/sac_training/sac_training_metrics.json`

---

### Opción C: Todos los Agents (6h CPU total)
```bash
python train_all_agents.py
```
✓ Secuencial: SAC → PPO → A2C
✓ Outputs: 3 modelos finales
✓ Ranking: Automático al final

---

### Opción D: Paralelo (Fastest - requiere 3 terminales)

**Terminal 1:**
```bash
python train_sac_production.py
```

**Terminal 2 (mientras avanza Terminal 1):**
```bash
python train_ppo_production.py
```

**Terminal 3 (mientras progresan):**
```bash
python train_a2c_production.py
```

Luego evalúar:
```bash
python evaluate_agents.py
```

---

## 📊 DESPUÉS DEL ENTRENAMIENTO

### Ver Métricas
```bash
# JSON bonito
python -c "import json; print(json.dumps(json.load(open('outputs/sac_training/sac_training_metrics.json')), indent=2))"

# Variables clave
python -c "import json; m=json.load(open('outputs/sac_training/sac_training_metrics.json')); print(f\"Reward: {m['validation_mean_reward']:.2f} ± {m['validation_std_reward']:.2f}\")"
```

### ComparaciónAgents
```bash
# Tabla CSV
cat outputs/evaluation/evaluation_comparison.csv

# JSON completo
python -c "import json; print(json.dumps(json.load(open('outputs/evaluation/evaluation_report.json')), indent=2))"
```

### Monitoring en Tiempo Real
```bash
# Terminal aparte - ejecutar MIENTRAS entrena
tensorboard --logdir outputs/*/tensorboard
# → http://localhost:6006
```

---

## 🔧 CONFIGURACIÓN RÁPIDA

### CPU vs GPU

**Detectar GPU (si disponible):**
```bash
python -c "import torch; print('GPU!' if torch.cuda.is_available() else 'CPU')"
```

**Forzar CPU (si GPU da problemas):**
Editar script antes de ejecutar:
```python
# En train_sac_production.py, cambiar:
'device': 'cpu'  # ← Agregar esta línea en sac_config
```

### Reducir Memoria

Si dice "OOM - Out of Memory":
```python
# En train_sac_production.py:
sac_config = {
    'batch_size': 32,      # ← Reducir de 64
    'buffer_size': 100000, # ← Reducir de 1,000,000
    'policy_kwargs': {
        'net_arch': [128, 128],  # ← Reducir de [256, 256]
    }
}
```

### Entrenar Menos Episodios

Editar TOTAL_TIMESTEPS:
```python
TOTAL_TIMESTEPS = 50000  # ← Cambiar de 100,000 (5 episodios en lugar de 11)
```

---

## 📋 CHECKLIST PRE-EJECUCIÓN

Antes de `python train_sac_production.py`:

- [ ] ✅ `python train_sac_test.py` ejecutado exitosamente
- [ ] ✅ `data/interim/oe2/` contiene 4 archivos críticos
- [ ] ✅ `data/processed/citylearn/iquitos_ev_mall/` existe (161 archivos)
- [ ] ✅ `configs/default.yaml` presente
- [ ] ✅ `checkpoints/` directory creado (auto-crea)
- [ ] [ ] Espacio en disco: mínimo 5GB disponible

**Si falta algo:**
```bash
# Construir dataset
python build_citylearnv2_with_oe2.py
```

---

## 🎯 ESCENARIOS TÍPICOS

### Escenario 1: "Quiero ver si funciona rápido"
```bash
python train_sac_test.py
# ✓ 75 segundos → Resultado: OK/ERROR
```

### Escenario 2: "Quiero entrenar un agent completo"
```bash
python train_sac_production.py
# ✓ 1-2 horas → Modelo guardado
python evaluate_agents.py
# ✓ 5 minutos → Métricas finales
```

### Escenario 3: "Quiero comparar SAC vs PPO vs A2C"
```bash
python train_all_agents.py
# ✓ 6 horas → Ranking automático
```

### Escenario 4: "Quiero entrenar y monitorear"
```bash
# Terminal 1: Entrenar
python train_sac_production.py

# Terminal 2: Monitor (abrir MIENTRAS avanza)
tensorboard --logdir outputs/sac_training/tensorboard

# Abrir navegador → http://localhost:6006
```

### Escenario 5: "Quiero solo checkpoint rápido cada poco"
Editar TOTAL_TIMESTEPS = 10000 (solo 1 episodio, 5 min)

---

## ⚠️ ERRORES COMUNES Y SOLUCIONES

### "❌ ModuleNotFoundError: No module named 'stable_baselines3'"
```bash
pip install stable-baselines3
pip install gymnasium
```

### "❌ FileNotFoundError: data/interim/oe2/..."
```bash
# Verificar
ls -la data/interim/oe2/
# Si faltan: necesita OE2 data para ejecutar

# O ejecutar dataset builder primero
python build_citylearnv2_with_oe2.py
```

### "❌ CUDA out of memory"
```bash
# Reducir batch size en script:
'batch_size': 32

# O reducir timesteps:
TOTAL_TIMESTEPS = 50000
```

### "❌ Training seems stuck (loss not decreasing)"
Completamente normal para primeros 1000 steps.
Esperar hasta step 10,000+ para ver cambios.

### "❌ Modelo no carga después de entrenar"
```bash
# Verificar que existe
ls -la checkpoints/SAC/

# Si existe pero no carga, puede ser incompatibilidad
# Solución: Entrenar de nuevo o usar backup anterior
```

---

## 📊 INTERPRETAR RESULTADOS

### Reward durante entrenamiento

```
Steps: 1,000  | Loss: -25.3   ← Explorando
Steps: 10,000 | Loss: -30.2   ← Mejorando
Steps: 50,000 | Loss: -32.5   ← Convergiendo
Steps: 100,000| Loss: -32.8   ← Plateau (esperado)
```

✓ Normal: Reward oscila ±10% en últimos 20k steps
❌ Problema: Reward aumentando monotónicamente (divergencia)
❌ Problema: Reward siempre constante (no aprende)

### Validación Final

```
Ep 1: reward=-38.52  ← Individual episode
Ep 2: reward=-39.15
Ep 3: reward=-38.97
Mean: -38.88 ± 0.30  ← Resumen

✓ BUENOS: Std < 5.0 (agent estable)
❌ MALO: Std > 10.0 (agent inestable)
```

---

## 🚀 NEXT STEPS DESPUÉS DE ENTRENAR

### 1️⃣ Evaluar Modelo
```bash
python evaluate_agents.py
```

### 2️⃣ Inspeccionar En Detalle
```bash
# Cargar modelo en Python
from stable_baselines3 import SAC
model = SAC.load('checkpoints/SAC/sac_final_model')
model.policy  # Ver arquitectura
print(model.num_timesteps)  # Ver steps entrenados
```

### 3️⃣ Usar Modelo para Inferencia
```python
# Ejemplo de uso
from stable_baselines3 import SAC
model = SAC.load('checkpoints/SAC/sac_final_model')

# Reset environment
obs, _ = env.reset()

# Inference
for step in range(100):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, _ = env.step(action)
    if terminated or truncated:
        break
```

### 4️⃣ Entrenar Más Episodios
```python
# Resume training
model = SAC.load('checkpoints/SAC/sac_final_model')
model.learn(total_timesteps=50000, reset_num_timesteps=False)
```

---

## 💾 BACKUP Y VERSION CONTROL

Después de cada entrenamiento:
```bash
# Backup modelo
cp checkpoints/SAC/sac_final_model.zip checkpoints/SAC/sac_final_model_v1.zip

# Backup métricas
cp outputs/sac_training/sac_training_metrics.json outputs/sac_training/sac_metrics_v1.json
```

---

## 🔄 WORKFLOW COMPLETO (Ejemplo)

```bash
# [1] Test rápido - verificar sistema (1 min)
python train_sac_test.py
# Output: "STATUS: ✓ SAC FUNCIONANDO CORRECTAMENTE"

# [2] SAC entrenar (2h)
python train_sac_production.py
# Output: checkpoints/SAC/sac_final_model.zip

# [3] PPO entrenar (1h) - paralelo o secuencial
python train_ppo_production.py

# [4] A2C entrenar (30min)
python train_a2c_production.py

# [5] Evaluar (5 min)
python evaluate_agents.py
# Output: outputs/evaluation/evaluation_report.json

# [6] Ver resultados
cat outputs/evaluation/evaluation_comparison.csv

# [7] Monitor con TensorBoard (en navegador)
tensorboard --logdir outputs/*/tensorboard
```

---

## 📞 DEBUGGING RÁPIDO

```bash
# Verificar PyTorch/Stable-Baselines3
python -c "import stable_baselines3; print('✓ SB3 OK')"

# Verificar Gymnasium
python -c "import gymnasium; print('✓ Gymnasium OK')"

# Verificar dataset
python -c "import json; json.load(open('data/processed/citylearn/iquitos_ev_mall/schema.json')); print('✓ Dataset OK')"

# Verificar checkpoints directory
python -c "from pathlib import Path; Path('checkpoints').mkdir(exist_ok=True); print('✓ Checkpoints OK')"
```

---

**¡Listo para entrenar! 🚀**

Próximo paso:
```bash
python train_sac_test.py
```

Esperado output:
```
[6] ENTRENAR 5 EPISODIOS (TEST RÁPIDO)
[7] TEST INFERENCIA
[... éxito ...]
STATUS: ✓ SAC FUNCIONANDO CORRECTAMENTE
```

Si ves esto → Ejecutar:
```bash
python train_sac_production.py
```
