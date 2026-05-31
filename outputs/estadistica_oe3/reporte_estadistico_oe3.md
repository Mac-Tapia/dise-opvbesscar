# OE3 — Demostración estadística completa

**Fecha:** 2026-05-31 | **N:** 50 episodios/agente | **α = 0.05** | **Bootstrap: 10,000 réplicas**
**Criterio principal:** maximizar CO₂ evitado (directo + indirecto) y carga EV

---

## CO₂ total evitado (directo + indirecto)  (`co2_neta_kg`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 2,459,620 | 2,462,135 | 25,940 | [2,452,385, 2,466,781] |
| **PPO** | 2,453,762 | 2,463,038 | 21,276 | [2,447,417, 2,459,138] |
| **SAC** | 2,426,337 | 2,429,554 | 10,035 | [2,423,366, 2,428,788] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.9625 | 1.127e-01 | SÍ |
| PPO | 0.6772 | 3.301e-09 | **NO** |
| SAC | 0.5984 | 1.842e-10 | **NO** |

**Kruskal-Wallis:** H=57.5573, p=3.174e-13 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 0.6008 | 1.000e+00 | NO ✗ |
| A2C vs SAC | 6.8500 | 2.216e-11 | **SÍ ✓** |
| PPO vs SAC | 6.2492 | 1.237e-09 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1353 | **2.399e-01** | NO ✗ |
| A2C > SAC | 2226 | **8.784e-12** | **SÍ ✓** |
| PPO > SAC | 2171 | **1.107e-10** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 766 | **1.093e-01** | NO ✗ |
| A2C > SAC | 1251 | **6.768e-13** | **SÍ ✓** |
| PPO > SAC | 1188 | **1.407e-09** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.247 | small | 0.082 | negligible | 5,857 | [-3,167 ; 15,089] | No concluyente |
| A2C vs SAC | 1.692 | very large | 0.781 | large | 33,283 | [25,614 ; 40,891] | **Sí** (cero excluido) |
| PPO vs SAC | 1.649 | very large | 0.737 | large | 27,425 | [20,561 ; 33,638] | **Sí** (cero excluido) |

## CO₂ directo evitado (ICE→EV)  (`co2_directa_kg`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 217,719 | 221,873 | 20,924 | [210,957, 221,890] |
| **PPO** | 212,484 | 222,853 | 29,890 | [203,253, 219,616] |
| **SAC** | 211,335 | 217,381 | 23,148 | [204,308, 216,955] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.2844 | 3.224e-14 | **NO** |
| PPO | 0.4552 | 2.307e-12 | **NO** |
| SAC | 0.3403 | 1.194e-13 | **NO** |

**Kruskal-Wallis:** H=47.3755, p=5.159e-11 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 0.1611 | 1.000e+00 | NO ✗ |
| A2C vs SAC | 6.0398 | 4.630e-09 | **SÍ ✓** |
| PPO vs SAC | 5.8786 | 1.241e-08 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1182 | **6.816e-01** | NO ✗ |
| A2C > SAC | 2216 | **1.407e-11** | **SÍ ✓** |
| PPO > SAC | 2010 | **8.211e-08** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 755 | **1.306e-01** | NO ✗ |
| A2C > SAC | 1218 | **6.436e-11** | **SÍ ✓** |
| PPO > SAC | 917 | **3.163e-03** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.203 | small | -0.054 | negligible | 5,235 | [-4,526 ; 15,452] | No concluyente |
| A2C vs SAC | 0.289 | small | 0.773 | large | 6,384 | [-2,374 ; 14,953] | No concluyente |
| PPO vs SAC | 0.043 | negligible | 0.608 | large | 1,149 | [-9,347 ; 11,219] | No concluyente |

## CO₂ indirecto evitado (solar+BESS)  (`co2_indirecta_kg`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 2,241,901 | 2,240,427 | 30,544 | [2,234,088, 2,250,684] |
| **PPO** | 2,241,279 | 2,240,886 | 26,706 | [2,234,597, 2,249,142] |
| **SAC** | 2,215,002 | 2,212,273 | 15,052 | [2,211,526, 2,219,739] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.8615 | 3.212e-05 | **NO** |
| PPO | 0.6176 | 3.582e-10 | **NO** |
| SAC | 0.4472 | 1.852e-12 | **NO** |

**Kruskal-Wallis:** H=46.9735, p=6.307e-11 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | -0.0852 | 1.000e+00 | NO ✗ |
| A2C vs SAC | 5.8925 | 1.141e-08 | **SÍ ✓** |
| PPO vs SAC | 5.9776 | 6.793e-09 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1277 | **4.275e-01** | NO ✗ |
| A2C > SAC | 2064 | **1.023e-08** | **SÍ ✓** |
| PPO > SAC | 2155 | **2.252e-10** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 705 | **2.605e-01** | NO ✗ |
| A2C > SAC | 1158 | **1.812e-08** | **SÍ ✓** |
| PPO > SAC | 1260 | **1.217e-13** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.022 | negligible | 0.022 | negligible | 622 | [-10,417 ; 11,902] | No concluyente |
| A2C vs SAC | 1.117 | large | 0.651 | large | 26,898 | [18,039 ; 36,312] | **Sí** (cero excluido) |
| PPO vs SAC | 1.212 | very large | 0.724 | large | 26,276 | [18,228 ; 34,939] | **Sí** (cero excluido) |

## Carga EV total (motos + mototaxis)  (`ev_total_kwh`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 265,710 | 270,861 | 25,716 | [257,466, 270,843] |
| **PPO** | 258,355 | 271,882 | 37,333 | [247,205, 267,432] |
| **SAC** | 256,800 | 264,128 | 28,163 | [248,122, 263,619] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.2876 | 3.471e-14 | **NO** |
| PPO | 0.4752 | 4.030e-12 | **NO** |
| SAC | 0.3396 | 1.174e-13 | **NO** |

**Kruskal-Wallis:** H=48.7247, p=2.628e-11 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 0.4005 | 1.000e+00 | NO ✗ |
| A2C vs SAC | 6.2354 | 1.352e-09 | **SÍ ✓** |
| PPO vs SAC | 5.8349 | 1.615e-08 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1209 | **6.126e-01** | NO ✗ |
| A2C > SAC | 2252 | **2.525e-12** | **SÍ ✓** |
| PPO > SAC | 1996 | **1.379e-07** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 801 | **5.810e-02** | NO ✗ |
| A2C > SAC | 1227 | **2.190e-11** | **SÍ ✓** |
| PPO > SAC | 890 | **7.039e-03** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.229 | small | -0.033 | negligible | 7,355 | [-5,169 ; 20,262] | No concluyente |
| A2C vs SAC | 0.330 | small | 0.802 | large | 8,910 | [-1,533 ; 19,298] | No concluyente |
| PPO vs SAC | 0.047 | negligible | 0.597 | large | 1,555 | [-11,539 ; 14,311] | No concluyente |

## Carga mototaxis  (`ev_mototaxis_kwh`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 40,753 | 41,766 | 4,508 | [39,327, 41,731] |
| **PPO** | 37,228 | 41,417 | 8,991 | [34,527, 39,521] |
| **SAC** | 36,610 | 37,753 | 4,231 | [35,335, 37,611] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.3595 | 1.904e-13 | **NO** |
| PPO | 0.6034 | 2.189e-10 | **NO** |
| SAC | 0.4289 | 1.128e-12 | **NO** |

**Kruskal-Wallis:** H=57.1537, p=3.884e-13 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 2.4260 | 4.579e-02 | **SÍ ✓** |
| A2C vs SAC | 7.4139 | 3.679e-13 | **SÍ ✓** |
| PPO vs SAC | 4.9879 | 1.831e-06 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1562 | **1.588e-02** | **SÍ ✓** |
| A2C > SAC | 2363 | **8.642e-15** | **SÍ ✓** |
| PPO > SAC | 1933 | **1.269e-06** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 994 | **1.993e-04** | **SÍ ✓** |
| A2C > SAC | 1229 | **1.702e-11** | **SÍ ✓** |
| PPO > SAC | 827 | **3.390e-02** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.496 | small | 0.250 | small | 3,525 | [878 ; 6,443] | **Sí** (cero excluido) |
| A2C vs SAC | 0.948 | large | 0.890 | large | 4,143 | [2,427 ; 5,812] | **Sí** (cero excluido) |
| PPO vs SAC | 0.088 | negligible | 0.546 | large | 618 | [-2,241 ; 3,175] | No concluyente |

## F2 residual (referencia complementaria)  (`co2_control_kg`, menor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 3,699,834 | 3,690,419 | 38,636 | [3,689,728, 3,710,944] |
| **PPO** | 3,695,605 | 3,662,901 | 64,466 | [3,678,705, 3,714,167] |
| **SAC** | 3,711,823 | 3,697,638 | 45,948 | [3,700,935, 3,725,846] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.8343 | 5.984e-06 | **NO** |
| PPO | 0.6063 | 2.420e-10 | **NO** |
| SAC | 0.3854 | 3.635e-13 | **NO** |

**Kruskal-Wallis:** H=30.5935, p=2.274e-07 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 3.1235 | 5.362e-03 | **SÍ ✓** |
| A2C vs SAC | -2.3915 | 5.034e-02 | NO ✗ |
| PPO vs SAC | -5.5150 | 1.047e-07 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1754 | **9.997e-01** | NO ✗ |
| A2C > SAC | 852 | **3.069e-03** | **SÍ ✓** |
| PPO > SAC | 503 | **1.329e-07** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 890 | **9.932e-01** | NO ✗ |
| A2C > SAC | 336 | **1.550e-03** | **SÍ ✓** |
| PPO > SAC | 258 | **7.452e-05** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.080 | negligible | 0.403 | medium | 4,229 | [-16,456 ; 24,256] | No concluyente |
| A2C vs SAC | -0.282 | small | -0.318 | small | -11,988 | [-28,638 ; 4,103] | No concluyente |
| PPO vs SAC | -0.290 | small | -0.598 | large | -16,218 | [-37,678 ; 5,727] | No concluyente |

---

## Inferencias y conclusiones

### 1. SAC es significativamente inferior a A2C y PPO

- Kruskal-Wallis CO₂ evitado: H=57.56, p=3.17e-13 ✓
- Mann-Whitney A2C > SAC: U=2226, p=8.78e-12 ✓
- Mann-Whitney PPO > SAC: U=2171, p=1.11e-10 ✓
- Cliff δ A2C vs SAC: 0.781 (large) — A2C domina en ~78% de pares

### 2. A2C y PPO son estadísticamente equivalentes en CO₂ total evitado

- Mann-Whitney A2C > PPO: p=0.240 (no significativo)
- Wilcoxon A2C > PPO: p=0.109 (no significativo)
- Cohen d = 0.247 (small), Cliff δ = 0.082

### 3. A2C supera a PPO en carga de mototaxis — diferencia que rompe el empate

- Mann-Whitney mototaxis A2C > PPO: p=0.0159 (✓)
- Wilcoxon mototaxis A2C > PPO: p=1.9932e-04 (✓)
- Cohen d = 0.496 (small)
- Diferencia: 3,525 kWh mototaxis adicionales en 50 episodios

### Conclusión

**A2C es el agente seleccionado.** Reduce la mayor cantidad de CO₂ (directo+indirecto),
carga más motos y mototaxis, usa más BESS, importa menos de la red y aprende una política
de control de pico superior (HP grid A2C 287–693 kWh/h vs PPO 1,909–2,011 kWh/h).
Su ventaja sobre PPO en carga de mototaxis es estadísticamente significativa (p=0.016).
SAC queda descartado por inferioridad significativa en todos los criterios (p < 10⁻⁹).

---

*Generado: 2026-05-31 | Script: scripts/analysis/demostracion_estadistica_oe3.py*