# 📚 Guía Rápida: Gestión de Datos y Entrenamientos Incrementales

## 📁 Archivos Generados

- **`training_results_archive.json`** - Archivo consolidado con datos de todos los agentes
- **`scripts/query_training_archive.py`** - Utilidad de consultas y gestión
- **`TABLA_COMPARATIVA_FINAL_CORREGIDA.md`** - Tabla markdown con comparativa completa

---

## 🔍 Comandos de Consulta

Todos los comandos se ejecutan así:
```bash
python scripts/query_training_archive.py <comando>
```

### Ver Resumen Completo
```bash
python scripts/query_training_archive.py summary
```
Output: Reporte con todos los agentes, métricas finales, ranking, duraciones

### Ver Métricas de Energía
```bash
python scripts/query_training_archive.py energy
```
Output: Grid import anual, CO₂ anual, Solar utilizado (por agente)

### Ver Métricas de Aprendizaje
```bash
python scripts/query_training_archive.py performance
```
Output: Reward Final, Actor Loss, Critic Loss (por agente)

### Ver Duración de Entrenamientos
```bash
python scripts/query_training_archive.py duration
```
Output: Minutos entrenados, duración HMS, velocidad promedio (por agente)

### Ver Reducciones vs Baseline
```bash
python scripts/query_training_archive.py reductions
```
Output: Porcentaje de reducción en grid y CO₂ (por agente)

### Ver Ranking de Agentes
```bash
python scripts/query_training_archive.py ranking
```
Output:
```
🏆 RANKING DE AGENTES:
  1. A2C: Best energy efficiency (3,494 kWh/año)
  2. PPO: Fastest training speed (3,984 kWh/año)
  3. SAC: Excellent off-policy robustness (4,000 kWh/año)
```

### Buscar Mejor Agente por Criterio
```bash
python scripts/query_training_archive.py best <criterion>
```

Criterios disponibles: `energy`, `speed`, `reward`, `stability`, `overall`

Ejemplos:
```bash
python scripts/query_training_archive.py best energy      # A2C (menor consumo grid)
python scripts/query_training_archive.py best speed       # PPO (más rápido)
python scripts/query_training_archive.py best reward      # SAC (rewards más altos)
python scripts/query_training_archive.py best overall     # PPO (balance general)
```

### Ver Estado de Agentes
```bash
python scripts/query_training_archive.py status
```
Output: SAC: COMPLETED, PPO: COMPLETED, A2C: COMPLETED

---

## 🚀 Entrenamientos Incrementales

### Preparar Agente para Entrenamientos Adicionales

```bash
python scripts/query_training_archive.py prepare <AGENT> <NEW_TOTAL_TIMESTEPS>
```

**Ejemplo:** Duplicar entrenamiento de PPO (26,280 → 52,560 pasos)
```bash
python scripts/query_training_archive.py prepare PPO 52560
```

Output:
```
📋 PREPARACIÓN PARA ENTRENAMIENTO INCREMENTAL: PPO
  Pasos actuales: 26,280
  Pasos deseados: 52,560
  Pasos a entrenar: 26,280
  Checkpoint: ppo_final.zip
  Directorio: D:\diseñopvbesscar\analyses\oe3\training\checkpoints\ppo
```

Y proporciona el **código template** listo para usar:

```python
from stable_baselines3 import PPO
import os

# Load agent from checkpoint
agent = PPO.load(
    os.path.join('D:\diseñopvbesscar\analyses\oe3\training\checkpoints\ppo', 'ppo_final.zip'),
    env=env
)

# Resume training (accumulates timesteps)
agent.learn(
    total_timesteps=26280,           # Pasos adicionales a entrenar
    reset_num_timesteps=False        # CRITICAL: No resetear contador
)

# Save new checkpoint
agent.save('checkpoint_step_52560')
```

### ⚠️ IMPORTANTE: `reset_num_timesteps=False`

**SIEMPRE** usa `reset_num_timesteps=False` para entrenamientos incrementales:
- Si `True`: Reset el contador a 0 (pierde progreso)
- Si `False`: Acumula pasos al total existente ✅

---

## 📊 Datos Almacenados en JSON

El archivo `training_results_archive.json` contiene:

### Por cada agente:
```json
{
  "algorithm_name": "Soft Actor-Critic",
  "status": "COMPLETED",
  "training_dates": {
    "start_utc": "2026-01-28T19:01:00Z",
    "end_utc": "2026-01-28T21:47:00Z",
    "duration_minutes": 166
  },
  "final_metrics": {
    "reward_final": 521.89,
    "actor_loss_final": -5.62,
    "critic_loss_final": 0.0,
    "grid_import_kwh_annual": 4000,
    "co2_kg_annual": 1808
  },
  "checkpoint_management": {
    "checkpoints_saved": 53,
    "checkpoint_directory": "D:\\...\\checkpoints\\sac",
    "final_checkpoint": "sac_final.zip",
    "can_resume_training": true
  }
}
```

---

## 🔄 Flujo de Trabajo: Nuevos Entrenamientos

### 1️⃣ Consultá estado actual
```bash
python scripts/query_training_archive.py summary
```

### 2️⃣ Decide qué agente entrenar más
```bash
python scripts/query_training_archive.py best energy   # Si buscas eficiencia
python scripts/query_training_archive.py best speed    # Si buscas rapidez
```

### 3️⃣ Prepará template para nuevos pasos
```bash
python scripts/query_training_archive.py prepare <AGENT> <PASOS_TOTALES>
```

### 4️⃣ Ejecutá entrenamiento incremental
Copia el código template y ajusta `env` según tu setup

### 5️⃣ Actualiza datos después de entrenar
```python
from scripts.query_training_archive import TrainingArchiveManager

manager = TrainingArchiveManager()
new_metrics = {
    "reward_final": 530.5,
    "grid_import_kwh_annual": 3800,
    # ... más métricas ...
}
manager.update_after_incremental_training("PPO", new_metrics)
```

---

## 📈 Resumen Rápido de Agentes

| Agente | Mejor Para | Grid Anual | Duración |
|--------|-----------|-----------|----------|
| **A2C** 🥇 | Eficiencia máxima | 3,494 kWh | 2h 36m |
| **PPO** 🥈 | Balance general | 3,984 kWh | 2h 26m |
| **SAC** 🥉 | Exploración robusta | 4,000 kWh | 2h 46m |

---

## 🛠️ Troubleshooting

### Erro: "Archive not found"
- Verifica que `training_results_archive.json` exista en raíz del proyecto

### Comando no reconocido
- Uso: `python scripts/query_training_archive.py <comando>`
- No: `python query_training_archive.py ...`

### Entrenamientos incrementales fallan
- Verifica `reset_num_timesteps=False` en el código
- Asegúrate de que `env` sea la misma que la original
- Backup checkpoints antes de resumir

---

## 📎 Referencias

- 📊 [Tabla Comparativa Final](./TABLA_COMPARATIVA_FINAL_CORREGIDA.md)
- 📄 [SAC Report](./REPORTE_ENTRENAMIENTO_SAC_FINAL.md)
- 📄 [PPO Report](./REPORTE_ENTRENAMIENTO_PPO_FINAL.md)
- 📄 [A2C Report](./REPORTE_ENTRENAMIENTO_A2C_DETALLADO.md)
- 🗄️ [Training Archive (JSON)](./training_results_archive.json)

