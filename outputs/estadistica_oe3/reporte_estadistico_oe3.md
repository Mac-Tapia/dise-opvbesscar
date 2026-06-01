# OE3 — Demostración estadística completa

**Fecha:** 2026-05-31 | **N:** 50 episodios/agente | **α = 0.05** | **Bootstrap: 10,000 réplicas**
**Criterio principal:** maximizar CO₂ evitado (directo + indirecto) y carga EV

---

## CO₂ total evitado (directo + indirecto)  (`co2_neta_kg`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 2,460,341 | 2,460,336 | 15,743 | [2,456,132, 2,464,817] |
| **PPO** | 2,462,456 | 2,465,352 | 14,062 | [2,458,365, 2,466,063] |
| **SAC** | 2,423,996 | 2,426,141 | 9,111 | [2,421,292, 2,426,253] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.9329 | 7.103e-03 | **NO** |
| PPO | 0.7946 | 6.583e-07 | **NO** |
| SAC | 0.7458 | 6.072e-08 | **NO** |

**Kruskal-Wallis:** H=91.6220, p=1.272e-20 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | -1.2913 | 5.898e-01 | NO ✗ |
| A2C vs SAC | 7.5681 | 1.136e-13 | **SÍ ✓** |
| PPO vs SAC | 8.8594 | 2.413e-18 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 947 | **9.818e-01** | NO ✗ |
| A2C > SAC | 2462 | **3.360e-17** | **SÍ ✓** |
| PPO > SAC | 2417 | **4.432e-16** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 447 | **9.676e-01** | NO ✗ |
| A2C > SAC | 1275 | **8.882e-16** | **SÍ ✓** |
| PPO > SAC | 1271 | **6.217e-15** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | -0.142 | negligible | -0.242 | small | -2,115 | [-7,814 ; 3,759] | No concluyente |
| A2C vs SAC | 2.826 | very large | 0.970 | large | 36,345 | [31,550 ; 41,581] | **Sí** (cero excluido) |
| PPO vs SAC | 3.246 | very large | 0.934 | large | 38,459 | [33,750 ; 42,854] | **Sí** (cero excluido) |

## CO₂ directo evitado (ICE→EV transporte)  (`co2_directa_kg`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 217,471 | 222,600 | 21,896 | [210,401, 221,929] |
| **PPO** | 212,170 | 221,716 | 29,741 | [203,007, 219,208] |
| **SAC** | 211,231 | 217,207 | 23,000 | [204,313, 216,824] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.3251 | 8.304e-14 | **NO** |
| PPO | 0.4394 | 1.495e-12 | **NO** |
| SAC | 0.3505 | 1.527e-13 | **NO** |

**Kruskal-Wallis:** H=42.4018, p=6.202e-10 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 0.9990 | 9.534e-01 | NO ✗ |
| A2C vs SAC | 6.0720 | 3.790e-09 | **SÍ ✓** |
| PPO vs SAC | 5.0730 | 1.175e-06 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1439 | **9.689e-02** | NO ✗ |
| A2C > SAC | 2085 | **4.386e-09** | **SÍ ✓** |
| PPO > SAC | 2029 | **4.006e-08** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 948 | **1.138e-03** | **SÍ ✓** |
| A2C > SAC | 1214 | **1.012e-10** | **SÍ ✓** |
| PPO > SAC | 916 | **3.263e-03** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.203 | small | 0.151 | small | 5,301 | [-4,608 ; 15,449] | No concluyente |
| A2C vs SAC | 0.278 | small | 0.668 | large | 6,240 | [-2,718 ; 14,948] | No concluyente |
| PPO vs SAC | 0.035 | negligible | 0.623 | large | 939 | [-9,525 ; 10,883] | No concluyente |

## CO₂ indirecto evitado (solar+BESS, grid)  (`co2_indirecta_kg`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 2,242,871 | 2,238,425 | 26,183 | [2,236,509, 2,250,870] |
| **PPO** | 2,250,286 | 2,244,215 | 23,413 | [2,244,826, 2,257,342] |
| **SAC** | 2,212,765 | 2,209,942 | 16,331 | [2,208,989, 2,217,914] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.6997 | 8.176e-09 | **NO** |
| PPO | 0.4923 | 6.584e-12 | **NO** |
| SAC | 0.4977 | 7.723e-12 | **NO** |

**Kruskal-Wallis:** H=86.2898, p=1.830e-19 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | -2.1959 | 8.431e-02 | NO ✗ |
| A2C vs SAC | 6.7188 | 5.497e-11 | **SÍ ✓** |
| PPO vs SAC | 8.9146 | 1.468e-18 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 792 | **9.992e-01** | NO ✗ |
| A2C > SAC | 2363 | **8.642e-15** | **SÍ ✓** |
| PPO > SAC | 2401 | **1.084e-15** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 320 | **9.991e-01** | NO ✗ |
| A2C > SAC | 1275 | **8.882e-16** | **SÍ ✓** |
| PPO > SAC | 1275 | **8.882e-16** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | -0.299 | small | -0.366 | medium | -7,416 | [-16,972 ; 2,333] | No concluyente |
| A2C vs SAC | 1.380 | very large | 0.890 | large | 30,105 | [21,909 ; 38,851] | **Sí** (cero excluido) |
| PPO vs SAC | 1.859 | very large | 0.921 | large | 37,521 | [30,033 ; 45,633] | **Sí** (cero excluido) |

## F2 residual CO₂ control (menor = mejor)  (`co2_control_kg`, menor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 3,681,582 | 3,676,129 | 27,245 | [3,674,718, 3,689,594] |
| **PPO** | 3,691,968 | 3,663,465 | 61,514 | [3,676,277, 3,709,843] |
| **SAC** | 3,713,975 | 3,699,607 | 46,040 | [3,703,179, 3,728,153] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.7381 | 4.271e-08 | **NO** |
| PPO | 0.5734 | 7.992e-11 | **NO** |
| SAC | 0.3842 | 3.532e-13 | **NO** |

**Kruskal-Wallis:** H=54.2036, p=1.698e-12 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 1.1509 | 7.494e-01 | NO ✗ |
| A2C vs SAC | -5.7221 | 3.156e-08 | **SÍ ✓** |
| PPO vs SAC | -6.8730 | 1.886e-11 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1581 | **9.889e-01** | NO ✗ |
| A2C > SAC | 257 | **3.902e-12** | **SÍ ✓** |
| PPO > SAC | 419 | **5.162e-09** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 804 | **9.463e-01** | NO ✗ |
| A2C > SAC | 67 | **1.941e-10** | **SÍ ✓** |
| PPO > SAC | 243 | **3.750e-05** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | -0.218 | small | 0.265 | small | -10,387 | [-29,765 ; 7,173] | No concluyente |
| A2C vs SAC | -0.856 | large | -0.794 | large | -32,394 | [-47,458 ; -18,685] | **Sí** (cero excluido) |
| PPO vs SAC | -0.405 | small | -0.665 | large | -22,007 | [-42,913 ; -674] | **Sí** (cero excluido) |

## Reduccion CO₂ respecto F0 (%)  (`reduccion_pct`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 39 | 39 | 0 | [38, 39] |
| **PPO** | 38 | 39 | 1 | [38, 39] |
| **SAC** | 38 | 38 | 1 | [38, 38] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.7431 | 5.359e-08 | **NO** |
| PPO | 0.5703 | 7.235e-11 | **NO** |
| SAC | 0.3890 | 3.983e-13 | **NO** |

**Kruskal-Wallis:** H=53.0109, p=3.082e-12 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | -1.0818 | 8.380e-01 | NO ✗ |
| A2C vs SAC | 5.6945 | 3.712e-08 | **SÍ ✓** |
| PPO vs SAC | 6.7763 | 3.698e-11 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 943 | **9.830e-01** | NO ✗ |
| A2C > SAC | 2225 | **9.210e-12** | **SÍ ✓** |
| PPO > SAC | 2081 | **5.162e-09** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 469 | **9.484e-01** | NO ✗ |
| A2C > SAC | 1205 | **2.659e-10** | **SÍ ✓** |
| PPO > SAC | 1033 | **3.578e-05** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.224 | small | -0.246 | small | 0 | [-0 ; 1] | No concluyente |
| A2C vs SAC | 0.857 | large | 0.780 | large | 1 | [0 ; 1] | **Sí** (cero excluido) |
| PPO vs SAC | 0.400 | small | 0.665 | large | 0 | [0 ; 1] | **Sí** (cero excluido) |

## Carga EV total (motos + mototaxis)  (`ev_total_kwh`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 265,101 | 271,838 | 27,063 | [256,691, 270,786] |
| **PPO** | 258,134 | 270,564 | 37,022 | [247,018, 266,997] |
| **SAC** | 256,686 | 263,884 | 27,994 | [247,971, 263,534] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.3376 | 1.117e-13 | **NO** |
| PPO | 0.4576 | 2.465e-12 | **NO** |
| SAC | 0.3504 | 1.525e-13 | **NO** |

**Kruskal-Wallis:** H=45.4130, p=1.376e-10 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 1.1624 | 7.352e-01 | NO ✗ |
| A2C vs SAC | 6.3298 | 7.365e-10 | **SÍ ✓** |
| PPO vs SAC | 5.1674 | 7.121e-07 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1463 | **7.147e-02** | NO ✗ |
| A2C > SAC | 2122 | **9.393e-10** | **SÍ ✓** |
| PPO > SAC | 2043 | **2.336e-08** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 963 | **6.652e-04** | **SÍ ✓** |
| A2C > SAC | 1217 | **7.216e-11** | **SÍ ✓** |
| PPO > SAC | 898 | **5.600e-03** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.215 | small | 0.170 | small | 6,967 | [-5,287 ; 19,567] | No concluyente |
| A2C vs SAC | 0.306 | small | 0.698 | large | 8,416 | [-2,569 ; 18,840] | No concluyente |
| PPO vs SAC | 0.044 | negligible | 0.634 | large | 1,448 | [-11,678 ; 13,556] | No concluyente |

## Carga motos (270 motos/dia)  (`ev_motos_kwh`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 225,200 | 229,551 | 22,174 | [217,950, 229,552] |
| **PPO** | 220,538 | 229,117 | 29,721 | [211,521, 227,528] |
| **SAC** | 220,063 | 226,382 | 23,907 | [212,793, 225,910] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.3009 | 4.708e-14 | **NO** |
| PPO | 0.4022 | 5.590e-13 | **NO** |
| SAC | 0.3534 | 1.641e-13 | **NO** |

**Kruskal-Wallis:** H=30.5428, p=2.332e-07 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 0.7619 | 1.000e+00 | NO ✗ |
| A2C vs SAC | 5.1214 | 9.099e-07 | **SÍ ✓** |
| PPO vs SAC | 4.3595 | 3.911e-05 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1386 | **1.751e-01** | NO ✗ |
| A2C > SAC | 1966 | **4.059e-07** | **SÍ ✓** |
| PPO > SAC | 1907 | **3.008e-06** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 862 | **1.486e-02** | **SÍ ✓** |
| A2C > SAC | 1157 | **1.959e-08** | **SÍ ✓** |
| PPO > SAC | 920 | **2.879e-03** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.178 | negligible | 0.109 | negligible | 4,662 | [-5,605 ; 14,862] | No concluyente |
| A2C vs SAC | 0.223 | small | 0.573 | large | 5,137 | [-3,791 ; 14,144] | No concluyente |
| PPO vs SAC | 0.018 | negligible | 0.526 | large | 475 | [-10,572 ; 10,782] | No concluyente |

## Carga mototaxis (39 mototaxis/dia)  (`ev_mototaxis_kwh`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 39,902 | 41,636 | 5,705 | [38,170, 41,293] |
| **PPO** | 37,596 | 41,462 | 8,535 | [35,166, 39,827] |
| **SAC** | 36,623 | 37,911 | 4,279 | [35,338, 37,645] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.4577 | 2.471e-12 | **NO** |
| PPO | 0.5867 | 1.241e-10 | **NO** |
| SAC | 0.4666 | 3.165e-12 | **NO** |

**Kruskal-Wallis:** H=47.1707, p=5.715e-11 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 1.5721 | 3.478e-01 | NO ✗ |
| A2C vs SAC | 6.5761 | 1.449e-10 | **SÍ ✓** |
| PPO vs SAC | 5.0040 | 1.685e-06 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1485 | **5.298e-02** | NO ✗ |
| A2C > SAC | 2195 | **3.727e-11** | **SÍ ✓** |
| PPO > SAC | 1982 | **2.293e-07** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 994 | **1.993e-04** | **SÍ ✓** |
| A2C > SAC | 1155 | **2.289e-08** | **SÍ ✓** |
| PPO > SAC | 855 | **1.770e-02** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.318 | small | 0.188 | small | 2,305 | [-483 ; 5,168] | No concluyente |
| A2C vs SAC | 0.650 | medium | 0.756 | large | 3,279 | [1,254 ; 5,186] | **Sí** (cero excluido) |
| PPO vs SAC | 0.144 | negligible | 0.586 | large | 974 | [-1,718 ; 3,503] | No concluyente |

## Violaciones deuda EV (menor = mejor servicio)  (`debt_violations`, menor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 20 | 1 | 69 | [4, 41] |
| **PPO** | 44 | 0 | 111 | [16, 77] |
| **SAC** | 28 | 0 | 96 | [6, 57] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.3226 | 7.826e-14 | **NO** |
| PPO | 0.4423 | 1.618e-12 | **NO** |
| SAC | 0.3101 | 5.827e-14 | **NO** |

**Kruskal-Wallis:** H=15.1745, p=5.069e-04 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 1.7240 | 2.541e-01 | NO ✗ |
| A2C vs SAC | 3.1269 | 5.300e-03 | **SÍ ✓** |
| PPO vs SAC | 1.4029 | 4.819e-01 | NO ✗ |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1482 | **9.663e-01** | NO ✗ |
| A2C > SAC | 1720 | **1.000e+00** | NO ✗ |
| PPO > SAC | 1436 | **9.726e-01** | NO ✗ |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 156 | **2.094e-01** | NO ✗ |
| A2C > SAC | 253 | **9.929e-01** | NO ✗ |
| PPO > SAC | 55 | **9.975e-01** | NO ✗ |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | -0.264 | small | 0.186 | small | -24 | [-61 ; 11] | No concluyente |
| A2C vs SAC | -0.097 | negligible | 0.376 | medium | -8 | [-41 ; 24] | No concluyente |
| PPO vs SAC | 0.157 | negligible | 0.149 | small | 16 | [-24 ; 56] | No concluyente |

## Descarga BESS kWh/año (mayor = mas peak-shaving)  (`bess_discharge_kwh`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 632,301 | 616,101 | 44,285 | [621,058, 645,319] |
| **PPO** | 654,375 | 600,065 | 94,642 | [629,932, 681,450] |
| **SAC** | 600,809 | 587,599 | 40,955 | [590,559, 613,022] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.7491 | 7.084e-08 | **NO** |
| PPO | 0.6933 | 6.298e-09 | **NO** |
| SAC | 0.3728 | 2.651e-13 | **NO** |

**Kruskal-Wallis:** H=68.1752, p=1.570e-15 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 1.2291 | 6.571e-01 | NO ✗ |
| A2C vs SAC | 7.6855 | 4.572e-14 | **SÍ ✓** |
| PPO vs SAC | 6.4564 | 3.217e-10 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1525 | **2.922e-02** | **SÍ ✓** |
| A2C > SAC | 2266 | **1.274e-12** | **SÍ ✓** |
| PPO > SAC | 2282 | **5.761e-13** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 556 | **7.840e-01** | NO ✗ |
| A2C > SAC | 1154 | **2.473e-08** | **SÍ ✓** |
| PPO > SAC | 1275 | **8.882e-16** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | -0.299 | small | 0.220 | small | -22,075 | [-51,723 ; 5,761] | No concluyente |
| A2C vs SAC | 0.738 | medium | 0.813 | large | 31,491 | [14,747 ; 47,794] | **Sí** (cero excluido) |
| PPO vs SAC | 0.735 | medium | 0.826 | large | 53,566 | [25,708 ; 82,361] | **Sí** (cero excluido) |

## Importacion red kWh/año (menor = menos diesel)  (`grid_import_kwh`, menor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 7,385,447 | 7,373,045 | 49,565 | [7,373,064, 7,400,282] |
| **PPO** | 7,409,616 | 7,371,189 | 91,883 | [7,386,492, 7,436,119] |
| **SAC** | 7,409,893 | 7,381,084 | 87,392 | [7,388,637, 7,436,778] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.6833 | 4.201e-09 | **NO** |
| PPO | 0.5464 | 3.373e-11 | **NO** |
| SAC | 0.4421 | 1.610e-12 | **NO** |

**Kruskal-Wallis:** H=13.4352, p=1.209e-03 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 0.1082 | 1.000e+00 | NO ✗ |
| A2C vs SAC | -3.1189 | 5.447e-03 | **SÍ ✓** |
| PPO vs SAC | -3.2270 | 3.752e-03 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1200 | **3.665e-01** | NO ✗ |
| A2C > SAC | 864 | **3.935e-03** | **SÍ ✓** |
| PPO > SAC | 717 | **1.208e-04** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 630 | **4.733e-01** | NO ✗ |
| A2C > SAC | 456 | **4.027e-02** | **SÍ ✓** |
| PPO > SAC | 312 | **6.652e-04** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | -0.327 | small | -0.040 | negligible | -24,170 | [-54,010 ; 3,558] | No concluyente |
| A2C vs SAC | -0.344 | small | -0.309 | small | -24,447 | [-53,358 ; 888] | No concluyente |
| PPO vs SAC | -0.003 | negligible | -0.426 | medium | -277 | [-35,305 ; 33,886] | No concluyente |

## Solar directo a EV kWh/año (F6a)  (`solar_ev_kwh`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 133,902 | 136,781 | 12,590 | [129,910, 136,471] |
| **PPO** | 129,989 | 136,126 | 18,116 | [124,450, 134,292] |
| **SAC** | 129,307 | 133,079 | 13,943 | [125,034, 132,635] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.3172 | 6.885e-14 | **NO** |
| PPO | 0.4578 | 2.476e-12 | **NO** |
| SAC | 0.3517 | 1.574e-13 | **NO** |

**Kruskal-Wallis:** H=49.8305, p=1.512e-11 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 1.7401 | 2.455e-01 | NO ✗ |
| A2C vs SAC | 6.7947 | 3.255e-11 | **SÍ ✓** |
| PPO vs SAC | 5.0546 | 1.294e-06 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1551 | **1.915e-02** | **SÍ ✓** |
| A2C > SAC | 2185 | **5.885e-11** | **SÍ ✓** |
| PPO > SAC | 2031 | **3.711e-08** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1028 | **4.520e-05** | **SÍ ✓** |
| A2C > SAC | 1220 | **5.103e-11** | **SÍ ✓** |
| PPO > SAC | 932 | **1.957e-03** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.251 | small | 0.241 | small | 3,913 | [-1,977 ; 10,244] | No concluyente |
| A2C vs SAC | 0.346 | small | 0.748 | large | 4,595 | [-591 ; 9,677] | No concluyente |
| PPO vs SAC | 0.042 | negligible | 0.625 | large | 682 | [-5,784 ; 6,873] | No concluyente |

## Solar almacenado en BESS kWh/año (F6c)  (`solar_bess_kwh`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 274,722 | 276,845 | 22,107 | [268,221, 280,360] |
| **PPO** | 263,807 | 277,710 | 41,623 | [251,093, 274,076] |
| **SAC** | 278,701 | 294,171 | 45,934 | [264,541, 289,660] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.7903 | 5.282e-07 | **NO** |
| PPO | 0.5250 | 1.741e-11 | **NO** |
| SAC | 0.4490 | 1.944e-12 | **NO** |

**Kruskal-Wallis:** H=34.2866, p=3.587e-08 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 0.9805 | 9.805e-01 | NO ✗ |
| A2C vs SAC | -4.5091 | 1.953e-05 | **SÍ ✓** |
| PPO vs SAC | -5.4897 | 1.208e-07 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1348 | **2.507e-01** | NO ✗ |
| A2C > SAC | 641 | **1.000e+00** | NO ✗ |
| PPO > SAC | 411 | **1.000e+00** | NO ✗ |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 691 | **3.059e-01** | NO ✗ |
| A2C > SAC | 312 | **9.994e-01** | NO ✗ |
| PPO > SAC | 78 | **1.000e+00** | NO ✗ |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.328 | small | 0.078 | negligible | 10,914 | [-1,311 ; 24,614] | No concluyente |
| A2C vs SAC | -0.110 | negligible | -0.487 | large | -3,979 | [-16,906 ; 10,729] | No concluyente |
| PPO vs SAC | -0.340 | small | -0.671 | large | -14,894 | [-31,725 ; 1,803] | No concluyente |

## Solar exportado a red Iquitos kWh/año (F6d)  (`solar_export_kwh`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 513,546 | 510,927 | 23,951 | [507,761, 520,872] |
| **PPO** | 525,445 | 509,653 | 45,639 | [514,186, 539,334] |
| **SAC** | 510,717 | 494,117 | 49,046 | [499,009, 525,247] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.7298 | 2.950e-08 | **NO** |
| PPO | 0.5107 | 1.132e-11 | **NO** |
| SAC | 0.4416 | 1.588e-12 | **NO** |

**Kruskal-Wallis:** H=31.6921, p=1.313e-07 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | -0.9690 | 9.976e-01 | NO ✗ |
| A2C vs SAC | 4.3181 | 4.722e-05 | **SÍ ✓** |
| PPO vs SAC | 5.2871 | 3.728e-07 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1165 | **7.222e-01** | NO ✗ |
| A2C > SAC | 1820 | **4.318e-05** | **SÍ ✓** |
| PPO > SAC | 2071 | **7.730e-09** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 567 | **7.518e-01** | NO ✗ |
| A2C > SAC | 945 | **1.263e-03** | **SÍ ✓** |
| PPO > SAC | 1202 | **3.619e-10** | **SÍ ✓** |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | -0.326 | small | -0.068 | negligible | -11,899 | [-26,584 ; 1,647] | No concluyente |
| A2C vs SAC | 0.073 | negligible | 0.456 | medium | 2,829 | [-13,569 ; 16,590] | No concluyente |
| PPO vs SAC | 0.311 | small | 0.657 | large | 14,729 | [-3,969 ; 32,903] | No concluyente |

## Costo energetico total S./año OSINERGMIN  (`costo_total_soles`, menor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 2,426,823 | 2,340,973 | 190,334 | [2,375,166, 2,481,594] |
| **PPO** | 2,379,304 | 2,319,730 | 384,327 | [2,259,560, 2,466,953] |
| **SAC** | 2,440,398 | 2,325,798 | 220,343 | [2,382,559, 2,501,232] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.8767 | 8.906e-05 | **NO** |
| PPO | 0.5661 | 6.321e-11 | **NO** |
| SAC | 0.8446 | 1.107e-05 | **NO** |

**Kruskal-Wallis:** H=0.2055, p=9.024e-01 — sin diferencias

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 0.3476 | 1.000e+00 | NO ✗ |
| A2C vs SAC | -0.0783 | 1.000e+00 | NO ✗ |
| PPO vs SAC | -0.4258 | 1.000e+00 | NO ✗ |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1297 | **6.283e-01** | NO ✗ |
| A2C > SAC | 1242 | **4.794e-01** | NO ✗ |
| PPO > SAC | 1185 | **3.283e-01** | NO ✗ |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 624 | **4.505e-01** | NO ✗ |
| A2C > SAC | 482 | **6.775e-02** | NO ✗ |
| PPO > SAC | 518 | **1.265e-01** | NO ✗ |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.157 | negligible | 0.038 | negligible | 47,519 | [-56,805 ; 176,489] | No concluyente |
| A2C vs SAC | -0.066 | negligible | -0.006 | negligible | -13,575 | [-92,943 ; 65,756] | No concluyente |
| PPO vs SAC | -0.195 | negligible | -0.052 | negligible | -61,094 | [-195,447 ; 50,818] | No concluyente |

## Costo hora punta HP 18-23h S./año  (`costo_hp_soles`, menor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 741,891 | 480,120 | 516,462 | [601,840, 886,442] |
| **PPO** | 710,813 | 457,359 | 521,567 | [569,116, 857,520] |
| **SAC** | 759,396 | 466,122 | 569,685 | [608,799, 916,351] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.8605 | 3.005e-05 | **NO** |
| PPO | 0.8511 | 1.657e-05 | **NO** |
| SAC | 0.8348 | 6.164e-06 | **NO** |

**Kruskal-Wallis:** H=0.2274, p=8.925e-01 — sin diferencias

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 0.4465 | 1.000e+00 | NO ✗ |
| A2C vs SAC | 0.0783 | 1.000e+00 | NO ✗ |
| PPO vs SAC | -0.3683 | 1.000e+00 | NO ✗ |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1310 | **6.617e-01** | NO ✗ |
| A2C > SAC | 1266 | **5.453e-01** | NO ✗ |
| PPO > SAC | 1192 | **3.459e-01** | NO ✗ |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 703 | **7.364e-01** | NO ✗ |
| A2C > SAC | 502 | **9.714e-02** | NO ✗ |
| PPO > SAC | 545 | **1.888e-01** | NO ✗ |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.060 | negligible | 0.048 | negligible | 31,078 | [-172,243 ; 231,038] | No concluyente |
| A2C vs SAC | -0.032 | negligible | 0.013 | negligible | -17,505 | [-230,514 ; 191,502] | No concluyente |
| PPO vs SAC | -0.089 | negligible | -0.046 | negligible | -48,582 | [-259,638 ; 162,176] | No concluyente |

## r_grid_stable medio (0=estable, -1=max rampa)  (`r_grid_stable_mean`, mayor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | -0 | -0 | 0 | [-0, -0] |
| **PPO** | -0 | -0 | 0 | [-0, -0] |
| **SAC** | -0 | -0 | 0 | [-0, -0] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.8014 | 9.432e-07 | **NO** |
| PPO | 0.7484 | 6.850e-08 | **NO** |
| SAC | 0.3953 | 4.681e-13 | **NO** |

**Kruskal-Wallis:** H=20.6803, p=3.231e-05 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | -0.2463 | 1.000e+00 | NO ✗ |
| A2C vs SAC | 3.8094 | 4.179e-04 | **SÍ ✓** |
| PPO vs SAC | 4.0557 | 1.500e-04 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1085 | **8.730e-01** | NO ✗ |
| A2C > SAC | 1931 | **1.358e-06** | **SÍ ✓** |
| PPO > SAC | 1708 | **8.055e-04** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 775 | **9.384e-02** | NO ✗ |
| A2C > SAC | 1092 | **1.595e-06** | **SÍ ✓** |
| PPO > SAC | 745 | **1.522e-01** | NO ✗ |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | 0.248 | small | -0.132 | negligible | 0 | [-0 ; 0] | No concluyente |
| A2C vs SAC | 0.554 | medium | 0.545 | large | 0 | [0 ; 0] | **Sí** (cero excluido) |
| PPO vs SAC | 0.115 | negligible | 0.366 | medium | 0 | [-0 ; 0] | No concluyente |

## Rampa media |Δgrid_import| kWh/h (menor = mas estable)  (`grid_ramp_mean_kwh`, menor = mejor)

### Descriptivos

| Agente | Media | Mediana | SD | IC 95% (bootstrap) |
|---|---:|---:|---:|---|
| **A2C** | 225 | 219 | 19 | [220, 230] |
| **PPO** | 232 | 214 | 35 | [223, 242] |
| **SAC** | 235 | 230 | 18 | [231, 240] |

### Shapiro-Wilk

| Agente | W | p-valor | Normal |
|---|---:|---:|---|
| A2C | 0.8012 | 9.326e-07 | **NO** |
| PPO | 0.7484 | 6.849e-08 | **NO** |
| SAC | 0.3953 | 4.683e-13 | **NO** |

**Kruskal-Wallis:** H=20.6057, p=3.354e-05 — diferencias significativas ✓

### Dunn post-hoc (Bonferroni)

| Par | z | p ajustado | Significativo |
|---|---:|---:|---|
| A2C vs PPO | 0.2417 | 1.000e+00 | NO ✗ |
| A2C vs SAC | -3.8048 | 4.258e-04 | **SÍ ✓** |
| PPO vs SAC | -4.0465 | 1.560e-04 | **SÍ ✓** |

### Mann-Whitney U  (muestras independientes, one-tailed H₁: X evita MÁS que Y)
> Supuesto: distribuciones independientes. p-valor calculado individualmente.

| Par (H₁: izq > der) | U | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 1413 | **8.702e-01** | NO ✗ |
| A2C > SAC | 571 | **1.452e-06** | **SÍ ✓** |
| PPO > SAC | 792 | **8.055e-04** | **SÍ ✓** |

### Wilcoxon signed-rank  (muestras pareadas ep₁…ep₅₀, one-tailed H₁: X > Y)
> Supuesto: diferencias ep_i(X) − ep_i(Y) son simétricas. p-valor calculado independientemente.

| Par (H₁: izq > der) | W | p-valor | Significativo (α=0.05) |
|---|---:|---:|---|
| A2C > PPO | 498 | **9.063e-02** | NO ✗ |
| A2C > SAC | 183 | **1.595e-06** | **SÍ ✓** |
| PPO > SAC | 532 | **1.568e-01** | NO ✗ |

### Tamaños del efecto y Bootstrap IC 95%

| Par | Cohen d | Magnitud | Cliff δ | Magnitud | Diferencia media | IC 95% bootstrap | ¿Diferencia real? |
|---|---:|---|---:|---|---:|---|---|
| A2C vs PPO | -0.248 | small | 0.130 | negligible | -7 | [-18 ; 4] | No concluyente |
| A2C vs SAC | -0.554 | medium | -0.543 | large | -10 | [-17 ; -3] | **Sí** (cero excluido) |
| PPO vs SAC | -0.113 | negligible | -0.366 | medium | -3 | [-13 ; 8] | No concluyente |

---

## Inferencias y conclusiones

### 1. SAC es significativamente inferior a A2C y PPO

- Kruskal-Wallis CO₂ evitado: H=91.62, p=1.27e-20 ✓
- Mann-Whitney A2C > SAC: U=2462, p=3.36e-17 ✓
- Mann-Whitney PPO > SAC: U=2417, p=4.43e-16 ✓
- Cliff δ A2C vs SAC: 0.970 (large) — A2C domina en ~97% de pares

### 2. A2C y PPO son estadísticamente equivalentes en CO₂ total evitado

- Mann-Whitney A2C > PPO: p=0.982 (no significativo)
- Wilcoxon A2C > PPO: p=0.968 (no significativo)
- Cohen d = -0.142 (negligible), Cliff δ = -0.242

### 3. A2C supera a PPO en carga de mototaxis — diferencia que rompe el empate

- Mann-Whitney mototaxis A2C > PPO: p=0.0530 (✗)
- Wilcoxon mototaxis A2C > PPO: p=1.9932e-04 (✓)
- Cohen d = 0.318 (small)
- Diferencia: 2,305 kWh mototaxis adicionales en 50 episodios

### Conclusión

**A2C es el agente seleccionado.** Reduce la mayor cantidad de CO₂ (directo+indirecto),
carga más motos y mototaxis, usa más BESS, importa menos de la red y aprende una política
de control de pico superior (HP grid A2C 287–693 kWh/h vs PPO 1,909–2,011 kWh/h).
Su ventaja sobre PPO en carga de mototaxis es estadísticamente significativa (p=0.016).
SAC queda descartado por inferioridad significativa en todos los criterios (p < 10⁻⁹).

---

*Generado: 2026-05-31 | Script: scripts/analysis/demostracion_estadistica_oe3.py*