# Gráficas de Diagnóstico de RL - A2C v5.3

## STATUS: ✅ COMPLETAMENTE IMPLEMENTADO

El script `scripts/train/train_a2c_multiobjetivo.py` incluye un sistema **completo de diagnóstico** para monitorear el entrenamiento de A2C con las métricas clave de RL.

---

## 1️⃣ Gráficas Individuales Generadas

### a) **Entropy vs Steps** (`a2c_entropy.png`)
- **Métrica**: Diversidad de la policy (exploración)
- **Zona de alerta**: < 0.1 (exploration collapse)
- **Interpretación**:
  - Entropy alta inicialmente = exploración activa
  - Entropy baja al final = policy convergida
  - Colapso prematuro = aumentar `ent_coef` (0.01 → 0.02)

### b) **Policy Loss vs Steps** (`a2c_policy_loss.png`)
- **Métrica**: Pérdida del actor
- **Interpretación**:
  - Debería decrecer y estabilizarse
  - Oscilaciones normales en on-policy (A2C)
  - Si crece = learning rate muy alto

### c) **Value Loss vs Steps** (`a2c_value_loss.png`)
- **Métrica**: Pérdida del crítico (predicción de valores)
- **Umbral de warning**: > 100
- **Interpretación**:
  - Debería decrecer monotónico hasta convergencia
  - Muy alto persistente = arquitectura/normalización problemática
  - Si no decrece = reducir `vf_coef` (0.5 → 0.25)

### d) **Explained Variance vs Steps** (`a2c_explained_variance.png`)
- **Métrica**: Calidad de predicciones del crítico
- **Rango ideal**: > 0.5 (zona verde en gráfico)
- **Interpretación**:
  - 1.0 = predicciones perfectas
  - 0.0 = aleatorio (basura)
  - Debería aumentar duramente entrenamiento
  - Si bajo = crítico no aprende bien

### e) **Gradient Norm vs Steps** (`a2c_grad_norm.png`)
- **Métrica**: Norma de gradientes
- **Umbral de clipping**: 0.5 (línea azul)
- **Alerta**: > 10 (explosión, línea roja)
- **Interpretación**:
  - Mide estabilidad numérica
  - Muy alto = inestabilidad, gradientes que explotan
  - Muy bajo = vanishing gradients

---

## 2️⃣ Dashboard Combinado

### **a2c_dashboard.png** (Vista 2×3)

```
[Entropy]              [Policy Loss]         [Value Loss]
[Explained Variance]   [Grad Norm]          [Learning Rate]
```

**Característica**: Anotación automática de alertas en el título

---

## 3️⃣ Métricas Registradas Durante Entrenamiento

**Frecuencia**: Cada 1,000 pasos

```
✓ Paso actual (num_timesteps)
✓ Entropy (exploración)
✓ Policy loss (mejora de policy)
✓ Value loss (calidad de crítico)
✓ Explained variance (predicciones)
✓ Grad norm (estabilidad)
✓ Learning rate actual (puede cambiar con schedulers)
```

---

## 4️⃣ Sistema de Alertas (Early Warning)

| Alerta | Condición | Significado | Acción |
|--------|-----------|-------------|--------|
| **Entropy Collapse** | `entropy < 0.1` | Exploración muerta | ↑ `ent_coef` (0.01→0.02) |
| **High Value Loss** | `value_loss > 100` | Crítico mal, generalización pobre | Revisar LR, arch, norm |
| **Grad Explosion** | `grad_norm > 10` | Gradientes inestables | ↓ LR, ↑ `max_grad_norm` |
| **Low Explained Var** | `explained_var < umbral` | Crítico no predice bien | ↑ `vf_coef`, arch mayor |

---

## 5️⃣ Configuración A2C Completa

### **Default** (GPU-optimized)
```python
A2CConfig.for_gpu()
├─ learning_rate: 3e-4      (óptimo para Adam)
├─ n_steps: 16              (balance updates/estabilidad)
├─ gamma: 0.99              (discount factor)
├─ gae_lambda: 0.95         (GAE para reducir varianza)
├─ ent_coef: 0.01           (exploración estándar)
├─ vf_coef: 0.5             (balance policy/value)
├─ max_grad_norm: 0.5       (clipping conservador)
└─ normalize_advantage: True (reduce varianza)
```

### **Factory Methods Predefinidos**

**High Exploration** (tareas complejas):
```python
A2CConfig.high_exploration()
├─ learning_rate: 3e-4
├─ n_steps: 32              ← Horizonte más largo
├─ ent_coef: 0.02           ← Mayor exploración
└─ vf_coef: 0.25            ← Menos énfasis en value
```

**Stable Convergence** (convergencia garantizada):
```python
A2CConfig.stable_convergence()
├─ learning_rate: 1e-4      ← Más bajo
├─ n_steps: 16
├─ gae_lambda: 0.97         ← GAE más alto
├─ ent_coef: 0.005          ← Menos exploración
└─ max_grad_norm: 0.3       ← Más restrictivo
```

---

## 6️⃣ KPIs CityLearn Integrados

Además de métricas RL, se registran KPIs de control:

```
✓ Electricity Consumption (net) - Importación/exportación
✓ Electricity Cost - USD/soles
✓ Carbon Emissions - kg CO2
✓ Ramping - Variabilidad de carga
✓ Avg Daily Peak - Picos diarios
✓ Load Factor - Eficiencia de uso
```

**Gráficos**: `city_learn_kpis.png` (dashboard 2×3)

---

## 7️⃣ Interpretación de Gráficas

### ✅ Entrenamiento Saludable

```
Entropy:    Empieza alta (~1.0) → baja a ~0.1-0.3 (convergencia gradual)
Policy Loss: Decrece → estabiliza en valor bajo
Value Loss: Decrece monotónico → converge
Explained Var: Sube de negativo → cruza 0 → alcanza 0.3-0.7
Grad Norm: Oscila alrededor del clipping threshold
```

### ⚠️ Anormalidades Comunes

| Síntoma | Causa | Solución |
|---------|-------|----------|
| **Entropy cae a 0 rápido** | `ent_coef` muy bajo | ↑ `ent_coef` |
| **Value loss no baja** | Arquitectura pequeña, LR/norm problema | Cambiar `vf_coef`, arquitectura |
| **Explained var muy bajo** | Crítico débil | ↑ `vf_coef` o arquitectura mayor |
| **Policy loss crece** | Learning rate muy alto | ↓ `learning_rate` |
| **Grad norm > 10** | Inestabilidad numérica | ↓ `learning_rate`, ↑ clipping |

---

## 8️⃣ Locaciones de Archivos

```
Gráficas individuales A2C:
  outputs/a2c_training/a2c_entropy.png
  outputs/a2c_training/a2c_policy_loss.png
  outputs/a2c_training/a2c_value_loss.png
  outputs/a2c_training/a2c_explained_variance.png
  outputs/a2c_training/a2c_grad_norm.png

Dashboards:
  outputs/a2c_training/a2c_dashboard.png           (6 métricas RL)
  outputs/a2c_training/city_learn_kpis.png        (6 KPIs control)

Checkpoints:
  checkpoints/A2C/a2c_model_*.zip                 (cada 2,000 steps)
  checkpoints/A2C/a2c_final_model.zip             (modelo final)
```

---

## 9️⃣ Clase A2CMetricsCallback

**Referencia**: `scripts/train/train_a2c_multiobjetivo.py` línea ~348

```python
class A2CMetricsCallback(BaseCallback):
    """Registra métricas A2C y genera gráficos de diagnóstico."""
    
    def _on_step(self) -> bool:
        # Registra cada 1,000 steps
        # - Entropy, policy_loss, value_loss
        # - Explained variance, grad_norm
        # - Learning rate
        # Valida alertas
        
    def _generate_a2c_graphs(self) -> None:
        # Genera 6 gráficos A2C
        # suaviza curvas (rolling mean)
        # anotaciones de alertas
        
    def _on_training_end(self) -> None:
        # Llama a _generate_a2c_graphs()
        # Llama a _generate_kpi_graphs()
        # Resumen de alertas acumuladas
```

---

## 🔟 Flujo de Entrenamiento

```
┌─────────────────────────────────┐
│ Iniciar entrenamiento           │
├─────────────────────────────────┤
│ A2CMetricsCallback activo       │
├─────────────────────────────────┤
│ Cada 1,000 steps:               │
│  • Registra 7 métricas          │
│  • Verifica alertas             │
├─────────────────────────────────┤
│ Finaliza (87,600 steps)         │
├─────────────────────────────────┤
│ _on_training_end():             │
│  • Genera 6 gráficos A2C        │
│  • Genera 6 gráficos KPI        │
│  • Resumen de alertas           │
└─────────────────────────────────┘
```

---

## 📊 Comandos para Revisar Resultados

```bash
# Ver gráficas después de entrenamiento
python -c "
import matplotlib.pyplot as plt
from pathlib import Path
img = plt.imread('outputs/a2c_training/a2c_dashboard.png')
plt.imshow(img)
plt.axis('off')
plt.tight_layout()
plt.show()
"

# Listar todos los gráficos generados
ls -la outputs/a2c_training/

# Contar alertas registradas
grep -c "entropy_collapse_alerts\|high_value_loss" outputs/a2c_training/*.log
```

---

## ✨ RESUMEN

✅ **Implementación Completa**: Todas las gráficas de diagnóstico A2C requeridas
✅ **Sistema de Alertas**: Early warning para problemas comunes
✅ **Factory Methods**: Configuraciones predefinidas (GPU, High Exploration, Stable)
✅ **KPI Integration**: Métricas de control CityLearn incluidas
✅ **Production Ready**: Listo para entrenamiento sin cambios adicionales

**Generadas automáticamente al finalizar**: 12 gráficos (6 RL + 6 KPI)

---

*Documento: v5.3 (2026-02-14)*
*Script: `scripts/train/train_a2c_multiobjetivo.py`*
*Status: PRODUCCIÓN*
