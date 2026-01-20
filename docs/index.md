# 🏗️ PVBESSCAR - RL Building Energy Management

Documentación oficial del proyecto PVBESSCAR (PV-BESS-CAR) para gestión inteligente de energía en edificios usando Reinforcement Learning.

## 📚 Tabla de Contenidos

```{toctree}
:maxdepth: 2

inicio
arquitectura
modelos
datos
evaluacion
deployment
```

## 🎯 Descripción General

PVBESSCAR es un sistema de gestión inteligente de energía para edificios que integra:

- **Paneles Solares (PV)**: Generación de energía renovable
- **Baterías (BESS)**: Almacenamiento de energía
- **Cargadores de Vehículos (CAR)**: Demanda flexible
- **Agentes RL**: Políticas de control optimizadas

### Agentes Implementados

- **PPO** (Proximal Policy Optimization): 18,432 timesteps
- **A2C** (Advantage Actor-Critic): 17,536 timesteps
- **SAC** (Soft Actor-Critic): 17,520 timesteps

## 📊 Recursos Principales

### Gráficas

- 25 gráficas regeneradas con datos reales
- Ubicación: `analyses/oe3/training/plots/`
- Índice: [plots/README.md](../analyses/oe3/training/plots/README.md)

### Checkpoints

- PPO: 11 checkpoints en `checkpoints/ppo_gpu/`
- A2C: 10 checkpoints en `checkpoints/a2c_gpu/`
- SAC: 176 checkpoints en `checkpoints/sac/`

### Datasets

- 476 archivos CSV
- 101 escenarios de validación
- Datos reales de demanda de mall

## 🚀 Guía Rápida

### Análisis de Modelos

```bash
python EJECUTAR_OPCION_1_ANALISIS.py
```

### Evaluación en Escenarios

```bash
python VERIFICACION_101_ESCENARIOS_2_PLAYAS.py
```

### Análisis Energético

```bash
python EVALUACION_METRICAS_COMPLETAS.py
```

## 📖 Documentación Disponible

- [RESUMEN_SESION_CONSOLIDACION_20260119.md](../RESUMEN_SESION_CONSOLIDACION_20260119.md): Resumen de limpieza del proyecto
- [PROXIMOSPASOS_OPCIONES_CONTINUACION.md](../PROXIMOSPASOS_OPCIONES_CONTINUACION.md): Opciones de continuación
- [plots/README.md](../analyses/oe3/training/plots/README.md): Índice de gráficas

## 🔗 Enlaces Útiles

- [GitHub Repository](https://github.com/Mac-Tapia/dise-opvbesscar)
- [CityLearn](https://github.com/intelligent-environments-lab/CityLearn)
- [Stable-Baselines3](https://stable-baselines3.readthedocs.io/)

## 📝 Requisitos

```text
python >= 3.10
stable-baselines3 >= 2.0
gymnasium >= 0.28
numpy
pandas
matplotlib
```

## 📧 Contacto

Para consultas sobre el proyecto, contactar al equipo de investigación.

---

**Última actualización**: 2026-01-20
**Estado**: ✅ Proyecto estable y consolidado