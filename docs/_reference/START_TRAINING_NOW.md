# 🚀 GUÍA RÁPIDA - COMENZAR ENTRENAMIENTO AHORA

**Fecha:** 2026-02-02  
**Estado:** ✅ COMPLETADO Y LISTO

---

## ⚡ INICIO RÁPIDO (3 PASOS)

### Paso 1: Abre una terminal en `d:\diseñopvbesscar`

```bash
cd d:\diseñopvbesscar
```

### Paso 2: Ejecuta el entrenamiento

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-baseline
```

### Paso 3: Espera y observa el progreso

Verás actualizaciones cada 30 segundos como esta:

```
════════════════════════════════════════════════════════════════════════════════
[2026-02-02 14:23:45] 📊 ESTADO DEL ENTRENAMIENTO
════════════════════════════════════════════════════════════════════════════════

[14:23:45] 🔄 SAC
   ⏱️  Tiempo: 15.3 min
   📦 Checkpoints: 3
   ⏭️  Último: 125s hace
   ✅ ACTIVO
```

---

## 🎯 ¿QUÉ PASARÁ?

1. **SAC** se entrenará primero (máx 2 horas)
   - Si falla → Reintentará automáticamente
   - Si tiene éxito → PPO comienza

2. **PPO** se entrenará luego (máx 3 horas)
   - Si falla → Reintentará automáticamente
   - Si tiene éxito → A2C comienza

3. **A2C** se entrenará al final (máx 3 horas)
   - Si falla → Reintentará automáticamente
   - Si tiene éxito → Reporte final

4. **Resultado final** (~6-8 horas total)
   - Archivo: `outputs/oe3_simulations/simulation_summary.json`
   - Tabla: `outputs/oe3_simulations/co2_comparison.md`

---

## 👀 CÓMO MONITOREAR (OPCIONAL)

### Opción 1: Ver logs en vivo
```bash
# En otra terminal
tail -f training_live.log
```

### Opción 2: Ver estado JSON
```bash
# En otra terminal - ver estado cada 5 segundos
watch -n 5 "cat outputs/oe3_simulations/training_status.json | python -m json.tool | head -50"
```

### Opción 3: Solo ver main terminal
```bash
# El output ya se muestra cada 30s en la terminal principal
```

---

## ⚠️ SI ALGO FALLA

### Ctrl+C (Interrumpir)
El sistema guardará el estado antes de terminar:
- ✅ Checkpoints guardados
- ✅ Estado persistido en JSON
- ✅ Puedes continuar después

### Reintenta automáticos
Si un agente falla:
1. ✅ Intenta automáticamente (intento 1/2)
2. ✅ Si falla de nuevo, continúa siguiente agente (intento 2/2)
3. ✅ Si ambos fallan, reporta error pero sigue

### Ver qué pasó
```bash
# Ver archivo de estado completo
cat outputs/oe3_simulations/training_status.json | python -m json.tool
```

---

## 📊 RESULTADOS FINALES

Cuando termine, verás algo como:

```
📊 REPORTE FINAL DE ENTRENAMIENTO
════════════════════════════════════════════════════════════════════════════════

✅ AGENTES COMPLETADOS: 3
   • SAC       :     7235 kg CO2/año |   65.2% autoconsumo
   • PPO       :     7100 kg CO2/año |   68.5% autoconsumo
   • A2C       :     7450 kg CO2/año |   62.1% autoconsumo

🏆 MEJOR AGENTE: PPO
   Emisiones anuales: 7100 kg CO2
```

### Archivos generados:
- ✅ `result_SAC.json` - Resultados detallados SAC
- ✅ `result_PPO.json` - Resultados detallados PPO
- ✅ `result_A2C.json` - Resultados detallados A2C
- ✅ `simulation_summary.json` - Resumen completo
- ✅ `co2_comparison.md` - Tabla comparativa
- ✅ `training_status.json` - Estado final

---

## 🎓 NUEVAS CARACTERÍSTICAS

| Feature | Beneficio |
|---------|-----------|
| **Monitoreo cada 30s** | Sabes exactamente qué está pasando |
| **Reintentos automáticos** | Si falla, reinténtalo sin intervención |
| **Detección de timeouts** | Si se atasca, detecta y reintenta |
| **Logs visibles** | Puedes seguir el progreso en tiempo real |
| **Persistencia de estado** | Si interrumpes, puedes continuar |
| **Transición automática** | Pasa automáticamente de SAC → PPO → A2C |
| **Manejo de errores** | Los errores no detienen todo |

---

## 💡 TIPS

1. **Deja que corra:** No interrumpas manualmente a menos que sea necesario
2. **Monitorea:** Abre otro terminal para ver `training_status.json`
3. **Paciencia:** Toma 6-8 horas, pero es automático
4. **Resultados:** Los verás en `outputs/oe3_simulations/`
5. **Cleanup:** Si quieres empezar de cero, borra `checkpoints/`

---

## 🟢 STATUS ACTUAL

**Limpieza:** ✅ Completada (Fase 9)  
**Relanzamiento:** ✅ Completado (Fase 9)  
**Mejoras:** ✅ Implementadas (Ahora)  
**Validación:** ✅ Exitosa

**LISTO PARA ENTRENAR** 🚀

---

## 📞 SOPORTE

Si algo no funciona:

1. **¿Error de importes?**
   - `pip install -r requirements.txt`

2. **¿Out of memory?**
   - SAC ya está optimizado para RTX 4060 (8GB)

3. **¿Timeout muy corto?**
   - Editar en `run_oe3_simulate.py`, línea ~350
   - `timeout_minutes = {"sac": 180, "ppo": 240, "a2c": 240}`

4. **¿Ver logs antiguos?**
   - Ver: `outputs/oe3_simulations/trace_*.csv`

---

## 🎉 ¡YA ESTÁS LISTO!

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-baseline
```

**El sistema ahora es:**
- ✅ Robusto (reintentos + recuperación)
- ✅ Visible (monitoreo cada 30s)
- ✅ Confiable (timeouts + detección de bloqueos)
- ✅ Automático (transición entre agentes)
- ✅ Persistente (estado guardado)

**¡Disfruta del entrenamiento! 🚀**

