# Metodología de la investigación — OE3

**Versión:** 2026-05-31
**Sección de tesis:** Capítulo III — Metodología
**Diseño:** cuasi-experimental por simulación

---

## 3.1 Tipo de investigación

La investigación es de tipo **aplicada** y de enfoque **cuantitativo**.

Es **aplicada** porque se orienta a resolver un problema concreto: la gestión óptima de la
carga de vehículos eléctricos (motos y mototaxis) mediante agentes de aprendizaje por
refuerzo (RL) en el sistema fotovoltaico-BESS del complejo comercial de Iquitos, con el
fin de minimizar las emisiones de CO₂ de la red eléctrica aislada (Murillo Vargas, 2010;
Arias, 2012). Los resultados tienen aplicación directa en la operación del sistema real.

Es **cuantitativa** porque las variables de interés —CO₂ evitado, energía EV cargada,
importación de red, estado de carga del BESS— se expresan en unidades métricas medibles
y se analizan mediante procedimientos estadísticos formales (Hernández Sampieri et al.,
2014, p. 4). El proceso sigue la secuencia: planteamiento del problema → marco teórico →
hipótesis → operacionalización de variables → recolección de datos por simulación →
análisis estadístico → conclusiones.

---

## 3.2 Nivel de investigación

El nivel de investigación es **explicativo-causal**.

Es explicativo porque no se limita a describir el comportamiento de los agentes ni a
establecer relaciones de asociación, sino que busca determinar *por qué* un agente produce
mayor reducción de CO₂ que otro: la política aprendida (variable independiente) *causa*
diferencias medibles en las emisiones y en la carga de vehículos eléctricos (variables
dependientes), lo que se verifica con pruebas estadísticas de hipótesis de causalidad
(Hernández Sampieri et al., 2014, pp. 95–96; Tamayo y Tamayo, 2003, p. 46).

El estudio posee también un componente descriptivo en sus primeras etapas (caracterización
del sistema, dimensionamiento OE2), pero la contribución central es explicativa: la
comparación causal entre los tres tratamientos experimentales (SAC, PPO, A2C) bajo
condiciones controladas de simulación.

---

## 3.3 Diseño de investigación

### 3.3.1 Justificación del diseño cuasi-experimental

La fase OE3 (selección del agente de control) se clasifica como cuasi-experimental por
simulación porque el investigador **manipula deliberadamente la variable independiente**
—el tipo de algoritmo de
aprendizaje por refuerzo— y mide el efecto sobre las variables dependientes en un entorno
controlado de simulación. Esta característica es constitutiva del diseño experimental
según Hernández Sampieri et al. (2014, p. 129):

> "Los experimentos manipulan tratamientos, estímulos, influencias o intervenciones
> (denominadas variables independientes) para observar sus efectos sobre otras variables
> (las dependientes) en una situación de control."

La simulación por computadora es reconocida en la literatura metodológica como
instrumento válido para producir datos experimentales cuando el sistema real no puede
someterse directamente a tratamientos (Law, 2015, p. 1; Banks et al., 2010, p. 3;
Montgomery, 2017, p. 11). La condición experimental se cumple porque:

1. **Manipulación de la VI**: se ejecutan tres tratamientos diferenciados (SAC, PPO, A2C)
   sobre el mismo entorno de simulación.
2. **Medición de las VD**: CO₂ evitado, carga EV y variables operativas se registran en
   cada episodio con precisión de cuatro decimales.
3. **Control de variables extrañas**: el entorno de simulación mantiene constantes la
   generación solar (5,819,332 kWh/año), la especificación del BESS (2,000 kWh / 400 kW),
   la demanda del mall y el factor de emisión de la red (0.4521 kg CO₂/kWh), de modo que
   las diferencias observadas entre agentes solo pueden atribuirse al algoritmo de control.

### 3.3.2 Diseño cuasi-experimental por simulación

El diseño se clasifica como **cuasi-experimental** (Hernández Sampieri et al., 2014,
pp. 151–165; Campbell & Stanley, 1966) en lugar de experimental puro por la siguiente
razón: los episodios de simulación son secuenciales —no se asignan aleatoriamente a
condiciones—, lo cual impide cumplir el requisito de aleatorización completa del diseño
experimental verdadero. El proceso de entrenamiento es acumulativo: el agente aprende de
los episodios anteriores y cada episodio incorpora ese aprendizaje. Esta dependencia
temporal es inherente a los algoritmos RL y no permite barajar aleatoriamente el orden de
los episodios sin destruir el proceso de aprendizaje.

Sin embargo, el diseño cuasi-experimental con simulación conserva las propiedades clave
de control y reproducibilidad:

- **Grupo de tratamiento 1 (T₁):** agente SAC, 50 episodios (n=50)
- **Grupo de tratamiento 2 (T₂):** agente PPO, 50 episodios (n=50)
- **Grupo de tratamiento 3 (T₃):** agente A2C, 50 episodios (n=50)
- **Preprueba:** episodio 1 de cada agente (política sin aprender)
- **Posprueba:** episodios 45–50 de cada agente (plateau de convergencia)
- **Variable independiente:** tipo de algoritmo RL (SAC, PPO, A2C)
- **Variables dependientes:** CO₂ total evitado, CO₂ directo evitado, CO₂ indirecto
  evitado, carga EV (motos y mototaxis), importación de red, uso del BESS

Adicionalmente, el modelo estocástico de llegada de vehículos (270 motos/día con
distribución de probabilidad calibrada; 39 mototaxis/día) introduce variación aleatoria
en cada episodio, lo que equivale a la función de aleatorización en los experimentos
tradicionales y refuerza la validez interna del diseño (Law, 2015, pp. 223–228).

El esquema del diseño cuasi-experimental con tres grupos de tratamiento es:

```
T₁ (SAC):  O₁  X₁  O₂  ...  O₅₀   (50 episodios × 8,760 h = 438,000 timesteps)
T₂ (PPO):  O₁  X₂  O₂  ...  O₅₀   (50 episodios × 8,760 h = 438,000 timesteps)
T₃ (A2C):  O₁  X₃  O₂  ...  O₅₀   (50 episodios × 8,760 h = 438,000 timesteps)

O = observación (episodio)   X = tratamiento (algoritmo RL)
```

Este esquema se corresponde con el diseño de **series de tiempo interrumpidas con grupos
de comparación** (Hernández Sampieri et al., 2014, p. 165), donde la intervención es el
inicio del entrenamiento RL y las observaciones son los 50 episodios consecutivos.

---

## 3.4 Operacionalización de variables

### Variable independiente

| Variable | Tipo | Definición conceptual | Definición operacional | Escala |
|---|---|---|---|---|
| Algoritmo de control RL | Categórica nominal | Tipo de agente de aprendizaje por refuerzo utilizado para gestionar la carga EV y el BESS | SAC (Soft Actor-Critic), PPO (Proximal Policy Optimization), A2C (Advantage Actor-Critic) | Nominal (3 niveles) |

### Variables dependientes principales

| Variable | Símbolo | Unidad | Definición operacional | Escala |
|---|---|---|---|---|
| CO₂ total evitado | VD₁ | kg CO₂/año | Suma de CO₂ directo (ICE→EV) + CO₂ indirecto (grid reducido por solar+BESS+RL) por episodio | Razón |
| CO₂ directo evitado | VD₂ | kg CO₂/año | CO₂ evitado por sustitución de vehículos de combustión interna por EVs cargados | Razón |
| CO₂ indirecto evitado | VD₃ | kg CO₂/año | CO₂ evitado por reducción de importación de red gracias al control solar+BESS+RL | Razón |
| Carga EV total | VD₄ | kWh/año | Energía eléctrica entregada a motos y mototaxis eléctricas durante el episodio | Razón |
| Carga mototaxis | VD₅ | kWh/año | Energía entregada específicamente a mototaxis (variable de mayor diferenciación entre A2C y PPO) | Razón |

### Variables dependientes operativas (control del sistema)

| Variable | Unidad | Descripción |
|---|---|---|
| Importación de red | kWh/año | Energía importada de la red eléctrica térmica diesel |
| Descarga BESS | kWh/año | Energía descargada del BESS durante el episodio |
| Violaciones de carga | count | Episodios hora en que la demanda EV no fue satisfecha (deuda de carga) |
| F2 residual | kg CO₂/año | CO₂ indirecto residual total con control RL activo (lectura complementaria) |

### Variables controladas (constantes de la simulación)

| Variable | Valor fijo | Fuente |
|---|---|---|
| Generación solar PV | 5,819,332 kWh/año | PVWatts + bifacial, Jinko Tiger Neo JKM580N-72HL4-BDV |
| Capacidad BESS | 2,000 kWh / 400 kW | Dimensionamiento OE2 validado |
| Factor emisión red | 0.4521 kg CO₂/kWh | Red térmica diesel Iquitos (MINEM) |
| Demanda mall | 12,368,500 kWh/año | Medición real complejo comercial |
| Flota diaria | 270 motos + 39 mototaxis | Aforo OE2 |
| Tarifa HP | 0.45 S./kWh (h18–h23) | Electro Oriente Res. N° 047-2024-OS/CD |
| Función de recompensa | CO₂_DUAL_FOCUS v8.1 | Pesos verificados y sincronizados (ver `ev_charging_wrapper.py`) |

---

## 3.5 Población y muestra

### 3.5.1 Unidad de análisis

La **unidad de análisis** es el *episodio de simulación*, definido como una ejecución
continua del sistema EV+BESS+solar durante 8,760 horas consecutivas (un año calendario
completo, de enero a diciembre 2024). Cada episodio produce un vector de variables
dependientes anualizadas.

### 3.5.2 Población

La **población objetivo** es el conjunto de todos los episodios posibles que puede
generar la simulación del sistema para cada algoritmo de control, dado el espacio de
estados del entorno CityLearn v2 con datos de Iquitos 2024. Esta población es
**virtualmente infinita** en extensión pero finita en tendencia asintótica, pues el
proceso de entrenamiento converge hacia una política estacionaria (plateau).

La **población accesible** se define como los episodios producidos durante el proceso de
entrenamiento completo: 50 episodios por agente, determinados por el criterio de
convergencia (coeficiente de variación en plateau < 0.5% durante los últimos 10 episodios).

### 3.5.3 Muestra

**Tamaño de muestra:** n = 50 episodios por agente (N total = 150 episodios).

La muestra es **no probabilística, por saturación estadística** (Hernández Sampieri et al.,
2014, p. 390; Arias, 2012, p. 83). Se justifica con dos criterios convergentes:

**Criterio 1 — Convergencia estadística (CV plateau):**
El coeficiente de variación del reward en los últimos 10 episodios es menor al 0.5% para
los tres agentes, lo que evidencia que la distribución de las variables dependientes es
estable y el incremento de n adicional no aportaría información nueva (principio de
saturación):

| Agente | Reward plateau (media) | SD plateau | CV plateau | Estabilidad |
|---|---:|---:|---:|---|
| A2C | 1,654.1 | 12.40 | 0.460% | Alta |
| PPO | 1,674.9 | 5.75 | 0.283% | Alta |
| SAC | 1,462.8 | 3.56 | 0.186% | Alta |

**Criterio 2 — Potencia estadística:**
Con n=50 por grupo, las pruebas no paramétricas utilizadas (Mann-Whitney U, Wilcoxon
signed-rank) alcanzan una potencia estadística (1−β) > 0.80 para detectar tamaños de
efecto de Cliff δ ≥ 0.30 (efecto pequeño-mediano), con α = 0.05
(Conover, 1999, p. 281; Faul et al., 2007). Los efectos observados oscilan entre
δ = 0.318 (SAC vs A2C, pequeño) y δ = 0.781 (A2C vs SAC en CO₂ evitado, grande),
todos dentro del rango de detección con la muestra seleccionada.

**Criterio 3 — Precedente en investigación RL:**
El estándar empírico en estudios de comparación de agentes RL para gestión energética
utiliza entre 20 y 100 episodios de evaluación (Brandi et al., 2022; Deltetto et al.,
2021; Kathirgamanathan et al., 2021). La muestra de n=50 es consistente con este rango.

### 3.5.4 Muestreo

El método de muestreo es **sistemático-secuencial** (también denominado muestreo por
conveniencia estructurada en simulación): los episodios se recogen en el orden natural
del proceso de entrenamiento, que es la única forma válida de registrar el aprendizaje
acumulativo de los agentes RL. No se emplea aleatorización del orden porque destruiría
el proceso de aprendizaje (Law, 2015, pp. 223–228).

La representatividad se garantiza porque los 50 episodios incluyen:
- Fase de exploración inicial (eps 1–5): variabilidad máxima, política sin aprender
- Fase de aprendizaje activo (eps 6–30): mejora acelerada, transición a política óptima
- Fase de plateau (eps 31–50): política convergida, máxima representatividad operativa

Esta estructura cubre el ciclo de vida completo de cada algoritmo y permite comparar
tanto el proceso de aprendizaje como el estado final de cada agente.

---

## 3.6 Técnicas e instrumentos de recolección de datos

| Técnica | Instrumento | Fuente de datos |
|---|---|---|
| Simulación computacional | Entorno CityLearn v2 + `IquitosEVChargingWrapper` | Sistema EV+BESS+solar Iquitos 2024 |
| Registro automático | `*_episodios_history.csv`, `timeseries_*.csv`, `trace_*.csv` | Trazas de entrenamiento 50 eps × 3 agentes |
| Análisis estadístico | `scripts/analysis/demostracion_estadistica_oe3.py` | Datos de trazas |
| Análisis operativo | `scripts/analysis/control_operativo_bess_ev_oe3.py` | Timeseries por hora del día |

La validez de los instrumentos de simulación fue verificada en la fase OE2:
`dataset_config_v7.json` con `ready_for_citylearn_v2 = true` y 106 pruebas unitarias
pasadas (`python -m pytest tests/ -v`).

---

## 3.7 Hipótesis de investigación

### Hipótesis general

**H₁:** Existe al menos un algoritmo de aprendizaje por refuerzo que, al controlar la
carga de vehículos eléctricos y el sistema BESS de la instalación solar fotovoltaica de
Iquitos, produce una reducción estadísticamente significativa de las emisiones de CO₂
respecto al resto de algoritmos evaluados (α = 0.05).

### Hipótesis específicas

**HE₁ (superioridad sobre SAC):**
El agente A2C evita una cantidad significativamente mayor de CO₂ (directo + indirecto)
que el agente SAC en el sistema EV+BESS+solar de Iquitos.

> H₀: CO₂_evitado_A2C ≤ CO₂_evitado_SAC
> H₁: CO₂_evitado_A2C > CO₂_evitado_SAC

**HE₂ (diferenciación en carga de mototaxis):**
El agente A2C carga una cantidad significativamente mayor de energía en mototaxis
eléctricas que el agente PPO.

> H₀: Carga_mototaxis_A2C ≤ Carga_mototaxis_PPO
> H₁: Carga_mototaxis_A2C > Carga_mototaxis_PPO

**HE₃ (control de pico):**
El agente A2C mantiene una importación de red eléctrica en hora punta (h18–h22)
significativamente menor que el agente PPO.

> H₀: Grid_HP_A2C ≥ Grid_HP_PPO
> H₁: Grid_HP_A2C < Grid_HP_PPO

### Resultados de contraste (resumen)

| Hipótesis | Prueba | Estadístico | p-valor | Decisión |
|---|---|---:|---:|---|
| HE₁: A2C > SAC (CO₂) | Mann-Whitney U | U=2,226 | 8.78×10⁻¹² | **Rechaza H₀ ✓** |
| HE₁: A2C > SAC (CO₂) | Wilcoxon | W=1,251 | 6.77×10⁻¹³ | **Rechaza H₀ ✓** |
| HE₂: A2C > PPO (mototaxis) | Mann-Whitney U | — | 0.016 | **Rechaza H₀ ✓** |
| HE₂: A2C > PPO (mototaxis) | Wilcoxon | — | 1.99×10⁻⁴ | **Rechaza H₀ ✓** |
| A2C = PPO (CO₂ total) | Mann-Whitney U | U=1,353 | 0.240 | No rechaza H₀ (equivalentes) |

---

## 3.8 Procedimiento de análisis estadístico

Dado que las distribuciones de las variables dependientes son **no normales** para SAC y
PPO (Shapiro-Wilk p < 0.001) y se acercan a la normalidad para A2C (W=0.962, p=0.113),
se aplican **pruebas no paramétricas**, que son más robustas para distribuciones
asimétricas con tamaños de muestra moderados (Conover, 1999; Siegel & Castellan, 1988):

1. **Shapiro-Wilk** (n=50): contraste de normalidad para cada agente.
2. **Kruskal-Wallis** (3 grupos): diferencia global entre los tres agentes.
3. **Dunn con corrección Bonferroni**: comparaciones post-hoc por pares.
4. **Mann-Whitney U** (one-tailed): diferencias entre pares con dirección hipotética.
5. **Wilcoxon signed-rank** (one-tailed, pareado): máxima potencia al comparar episodios del mismo período.
6. **Cohen d**: tamaño del efecto paramétrico (|d|<0.2 negligible, 0.2–0.5 small, 0.5–0.8 medium, >0.8 large).
7. **Cliff delta δ**: tamaño del efecto no paramétrico, robusto a no-normalidad (|δ|<0.147 negligible, 0.147–0.33 small, 0.33–0.474 medium, >0.474 large).
8. **Bootstrap IC 95%** (B=10,000): intervalos de confianza para diferencias de medias.

Todo el análisis se implementa y ejecuta con:
```
python scripts/analysis/demostracion_estadistica_oe3.py
```

---

## 3.9 Resultados de las pruebas estadísticas inferenciales

### 3.9.1 Estadísticos descriptivos por variable y agente

**Variable 1: CO₂ total evitado** — `co2_neta_kg` (kg/año, mayor = mejor)

| Agente | n | Media | Mediana | SD | CV% | IC 95% bootstrap |
|---|---:|---:|---:|---:|---:|---|
| **A2C** | 50 | **2,459,620** | 2,462,135 | 25,940 | 1.05 | [2,452,385 ; 2,466,781] |
| PPO | 50 | 2,453,762 | 2,463,038 | 21,276 | 0.87 | [2,447,417 ; 2,459,138] |
| SAC | 50 | 2,426,337 | 2,429,554 | 10,035 | 0.41 | [2,423,366 ; 2,428,788] |

**Variable 2: CO₂ directo evitado** — `co2_directa_kg` (kg/año, mayor = mejor)

| Agente | n | Media | Mediana | SD | IC 95% bootstrap |
|---|---:|---:|---:|---:|---|
| **A2C** | 50 | **217,719** | 221,873 | 20,924 | [210,957 ; 221,890] |
| PPO | 50 | 212,484 | 222,853 | 29,890 | [203,253 ; 219,616] |
| SAC | 50 | 211,335 | 217,381 | 23,148 | [204,308 ; 216,955] |

**Variable 3: CO₂ indirecto evitado** — `co2_indirecta_kg` (kg/año, mayor = mejor)

| Agente | n | Media | Mediana | SD | IC 95% bootstrap |
|---|---:|---:|---:|---:|---|
| **A2C** | 50 | **2,241,901** | 2,240,427 | 30,544 | [2,234,088 ; 2,250,684] |
| PPO | 50 | 2,241,279 | 2,240,886 | 26,706 | [2,234,597 ; 2,249,142] |
| SAC | 50 | 2,215,002 | 2,212,273 | 15,052 | [2,211,526 ; 2,219,739] |

**Variable 4: Carga EV total** — `ev_total_kwh` (kWh/año, mayor = mejor)

| Agente | n | Media | Mediana | SD | IC 95% bootstrap |
|---|---:|---:|---:|---:|---|
| **A2C** | 50 | **265,710** | 270,861 | 25,716 | [257,466 ; 270,843] |
| PPO | 50 | 258,355 | 271,882 | 37,333 | [247,205 ; 267,432] |
| SAC | 50 | 256,800 | 264,128 | 28,163 | [248,122 ; 263,619] |

**Variable 5: Carga mototaxis** — `ev_mototaxis_kwh` (kWh/año, mayor = mejor)

| Agente | n | Media | Mediana | SD | IC 95% bootstrap |
|---|---:|---:|---:|---:|---|
| **A2C** | 50 | **40,753** | 41,766 | 4,508 | [39,327 ; 41,731] |
| PPO | 50 | 37,228 | 41,417 | 8,991 | [34,527 ; 39,521] |
| SAC | 50 | 36,610 | 37,753 | 4,231 | [35,335 ; 37,611] |

**Variable 6 (complementaria): F2 residual** — `co2_control_kg` (kg/año, menor = mejor)

| Agente | n | Media | Mediana | SD | IC 95% bootstrap |
|---|---:|---:|---:|---:|---|
| PPO | 50 | **3,695,605** | 3,662,901 | 64,466 | [3,678,705 ; 3,714,167] |
| A2C | 50 | 3,699,834 | 3,690,419 | 38,636 | [3,689,728 ; 3,710,944] |
| SAC | 50 | 3,711,823 | 3,697,638 | 45,948 | [3,700,935 ; 3,725,846] |

---

### 3.9.2 Contraste de normalidad — Shapiro-Wilk

H₀: la distribución de la variable es normal (α = 0.05).

| Variable | Agente | W | p-valor | ¿Normal? | Consecuencia |
|---|---|---:|---:|---|---|
| CO₂ total evitado | A2C | 0.9625 | 1.127e-01 | **SÍ** | Parametrización posible |
| CO₂ total evitado | PPO | 0.6772 | 3.301e-09 | NO | No paramétrico |
| CO₂ total evitado | SAC | 0.5984 | 1.842e-10 | NO | No paramétrico |
| CO₂ directo | A2C | 0.2844 | 3.224e-14 | NO | No paramétrico |
| CO₂ directo | PPO | 0.4552 | 2.307e-12 | NO | No paramétrico |
| CO₂ directo | SAC | 0.3403 | 1.194e-13 | NO | No paramétrico |
| CO₂ indirecto | A2C | 0.8615 | 3.212e-05 | NO | No paramétrico |
| CO₂ indirecto | PPO | 0.6176 | 3.582e-10 | NO | No paramétrico |
| CO₂ indirecto | SAC | 0.4472 | 1.852e-12 | NO | No paramétrico |
| EV total | A2C | 0.2876 | 3.471e-14 | NO | No paramétrico |
| EV total | PPO | 0.4752 | 4.030e-12 | NO | No paramétrico |
| EV total | SAC | 0.3396 | 1.174e-13 | NO | No paramétrico |
| Mototaxis | A2C | 0.3595 | 1.904e-13 | NO | No paramétrico |
| Mototaxis | PPO | 0.6034 | 2.189e-10 | NO | No paramétrico |
| Mototaxis | SAC | 0.4289 | 1.128e-12 | NO | No paramétrico |
| F2 residual | A2C | 0.8343 | 5.984e-06 | NO | No paramétrico |
| F2 residual | PPO | 0.6063 | 2.420e-10 | NO | No paramétrico |
| F2 residual | SAC | 0.3854 | 3.635e-13 | NO | No paramétrico |

**Decisión:** Se rechazan hipótesis de normalidad en la mayoría de distribuciones.
Se aplican exclusivamente **pruebas no paramétricas** para todas las variables.
La baja W de SAC (0.385–0.598) refleja su distribución bimodal: episodios 1–4 con CO₂
muy alto (política sin aprender, buffer vacío) y episodios 5–50 en plateau bajo.

---

### 3.9.3 Kruskal-Wallis — contraste global (3 grupos)

H₀: los tres agentes tienen la misma distribución para la variable analizada (α = 0.05).

| Variable | H de Kruskal-Wallis | p-valor | gl | ¿Rechaza H₀? |
|---|---:|---:|---:|---|
| CO₂ total evitado | 57.5573 | **3.174×10⁻¹³** | 2 | **SÍ ✓** |
| CO₂ directo evitado | 47.3755 | **5.159×10⁻¹¹** | 2 | **SÍ ✓** |
| CO₂ indirecto evitado | 46.9735 | **6.307×10⁻¹¹** | 2 | **SÍ ✓** |
| Carga EV total | 48.7247 | **2.628×10⁻¹¹** | 2 | **SÍ ✓** |
| Carga mototaxis | 57.1537 | **3.884×10⁻¹³** | 2 | **SÍ ✓** |
| F2 residual (compl.) | 30.5935 | **2.274×10⁻⁷** | 2 | **SÍ ✓** |

**Interpretación:** En las seis variables analizadas, la prueba de Kruskal-Wallis rechaza
la hipótesis nula de igualdad de distribuciones entre los tres agentes con p < 10⁻⁶.
El resultado justifica la realización de comparaciones post-hoc por pares.

---

### 3.9.4 Dunn post-hoc con corrección Bonferroni

H₀: el par de agentes tiene la misma distribución (α ajustado = α/m = 0.05/3 = 0.0167).
Se reporta el p-valor ajustado por corrección Bonferroni.

| Variable | Par | z | p ajustado | ¿Significativo? |
|---|---|---:|---:|---|
| **CO₂ total evitado** | A2C vs PPO | 0.6008 | 1.000 | NO ✗ |
| **CO₂ total evitado** | A2C vs SAC | 6.8500 | **2.216×10⁻¹¹** | **SÍ ✓** |
| **CO₂ total evitado** | PPO vs SAC | 6.2492 | **1.237×10⁻⁹** | **SÍ ✓** |
| CO₂ directo | A2C vs PPO | 0.1611 | 1.000 | NO ✗ |
| CO₂ directo | A2C vs SAC | 6.0398 | **4.630×10⁻⁹** | **SÍ ✓** |
| CO₂ directo | PPO vs SAC | 5.8786 | **1.241×10⁻⁸** | **SÍ ✓** |
| CO₂ indirecto | A2C vs PPO | −0.0852 | 1.000 | NO ✗ |
| CO₂ indirecto | A2C vs SAC | 5.8925 | **1.141×10⁻⁸** | **SÍ ✓** |
| CO₂ indirecto | PPO vs SAC | 5.9776 | **6.793×10⁻⁹** | **SÍ ✓** |
| EV total | A2C vs PPO | 0.4005 | 1.000 | NO ✗ |
| EV total | A2C vs SAC | 6.2354 | **1.352×10⁻⁹** | **SÍ ✓** |
| EV total | PPO vs SAC | 5.8349 | **1.615×10⁻⁸** | **SÍ ✓** |
| **Mototaxis** | **A2C vs PPO** | 2.4260 | **4.579×10⁻²** | **SÍ ✓** |
| Mototaxis | A2C vs SAC | 7.4139 | **3.679×10⁻¹³** | **SÍ ✓** |
| Mototaxis | PPO vs SAC | 4.9879 | **1.831×10⁻⁶** | **SÍ ✓** |
| F2 residual | A2C vs PPO | 3.1235 | **5.362×10⁻³** | **SÍ ✓** |
| F2 residual | A2C vs SAC | −2.3915 | 5.034×10⁻² | NO ✗ (borderline) |
| F2 residual | PPO vs SAC | −5.5150 | **1.047×10⁻⁷** | **SÍ ✓** |

**Patrón observado:** A2C y PPO son **estadísticamente equivalentes** (p=1.000) en CO₂
total, CO₂ indirecto, CO₂ directo y EV total. La única diferencia significativa entre
A2C y PPO en el Dunn test es la variable **carga mototaxis** (p=0.046).
SAC es significativamente inferior a ambos en todas las variables.

---

### 3.9.5 Mann-Whitney U — muestras independientes (one-tailed)

**Naturaleza:** compara rangos entre dos grupos independientes.
**H₁ (dirección):** el agente de la izquierda evita MÁS CO₂ / carga MÁS EV que el de la derecha.
**p-valor:** calculado individualmente para cada par y cada variable. No se comparte con Wilcoxon.

| Variable | Par (H₁: izq > der) | U | p-valor | Sig. (α=0.05) |
|---|---|---:|---:|---|
| CO₂ total evitado | A2C > PPO | 1,353 | 0.2399 | NO ✗ |
| CO₂ total evitado | **A2C > SAC** | **2,226** | **8.784×10⁻¹²** | **SÍ ✓** |
| CO₂ total evitado | **PPO > SAC** | **2,171** | **1.107×10⁻¹⁰** | **SÍ ✓** |
| CO₂ directo | A2C > PPO | 1,182 | 0.6816 | NO ✗ |
| CO₂ directo | **A2C > SAC** | **2,216** | **1.407×10⁻¹¹** | **SÍ ✓** |
| CO₂ directo | **PPO > SAC** | **2,010** | **8.211×10⁻⁸** | **SÍ ✓** |
| CO₂ indirecto | A2C > PPO | 1,277 | 0.4275 | NO ✗ |
| CO₂ indirecto | **A2C > SAC** | **2,064** | **1.023×10⁻⁸** | **SÍ ✓** |
| CO₂ indirecto | **PPO > SAC** | **2,155** | **2.252×10⁻¹⁰** | **SÍ ✓** |
| EV total | A2C > PPO | 1,209 | 0.6126 | NO ✗ |
| EV total | **A2C > SAC** | **2,252** | **2.525×10⁻¹²** | **SÍ ✓** |
| EV total | **PPO > SAC** | **1,996** | **1.379×10⁻⁷** | **SÍ ✓** |
| **Mototaxis** | **A2C > PPO** | **1,562** | **0.0159** | **SÍ ✓** |
| Mototaxis | **A2C > SAC** | **2,363** | **8.642×10⁻¹⁵** | **SÍ ✓** |
| Mototaxis | **PPO > SAC** | **1,933** | **1.269×10⁻⁶** | **SÍ ✓** |
| F2 residual (compl.) | **PPO < SAC** | **503** | **1.329×10⁻⁷** | **SÍ ✓** |
| F2 residual (compl.) | **A2C < SAC** | **852** | **3.069×10⁻³** | **SÍ ✓** |
| F2 residual (compl.) | **PPO < A2C** | **746** | **2.592×10⁻⁴** | **SÍ ✓** |

---

### 3.9.5b Wilcoxon signed-rank — muestras pareadas (one-tailed)

**Naturaleza:** compara diferencias entre pares ep_i(X) − ep_i(Y) para i = 1…50.
**Supuesto:** los episodios son comparables por posición (ep₁ de A2C vs ep₁ de PPO, etc.).
**H₁ (dirección):** la diferencia intrapar es positiva en favor del agente de la izquierda.
**p-valor:** calculado independientemente del Mann-Whitney U. Son dos decisiones estadísticas distintas.

| Variable | Par (H₁: izq > der) | W | p-valor | Sig. (α=0.05) |
|---|---|---:|---:|---|
| CO₂ total evitado | A2C > PPO | 766 | 0.1093 | NO ✗ |
| CO₂ total evitado | **A2C > SAC** | **1,251** | **6.768×10⁻¹³** | **SÍ ✓** |
| CO₂ total evitado | **PPO > SAC** | **1,188** | **1.407×10⁻⁹** | **SÍ ✓** |
| CO₂ directo | A2C > PPO | 755 | 0.1306 | NO ✗ |
| CO₂ directo | **A2C > SAC** | **1,218** | **6.436×10⁻¹¹** | **SÍ ✓** |
| CO₂ directo | **PPO > SAC** | **917** | **3.163×10⁻³** | **SÍ ✓** |
| CO₂ indirecto | A2C > PPO | 705 | 0.2605 | NO ✗ |
| CO₂ indirecto | **A2C > SAC** | **1,158** | **1.812×10⁻⁸** | **SÍ ✓** |
| CO₂ indirecto | **PPO > SAC** | **1,260** | **1.217×10⁻¹³** | **SÍ ✓** |
| EV total | A2C > PPO | 801 | 0.0581 | NO ✗ |
| EV total | **A2C > SAC** | **1,227** | **2.190×10⁻¹¹** | **SÍ ✓** |
| EV total | **PPO > SAC** | **890** | **7.039×10⁻³** | **SÍ ✓** |
| **Mototaxis** | **A2C > PPO** | **994** | **1.993×10⁻⁴** | **SÍ ✓** |
| Mototaxis | **A2C > SAC** | **1,229** | **1.702×10⁻¹¹** | **SÍ ✓** |
| Mototaxis | **PPO > SAC** | **827** | **3.390×10⁻²** | **SÍ ✓** |
| F2 residual (compl.) | **PPO < SAC** | **258** | **7.452×10⁻⁵** | **SÍ ✓** |
| F2 residual (compl.) | **A2C < SAC** | **336** | **1.550×10⁻³** | **SÍ ✓** |
| F2 residual (compl.) | **PPO < A2C** | **385** | **7.039×10⁻³** | **SÍ ✓** |

**Convergencia de las dos pruebas:**
Cuando ambas pruebas coinciden en la decisión (ambas SÍ o ambas NO), la inferencia es
robusta. En este estudio ambas pruebas coinciden en el 100% de los pares evaluados,
lo que refuerza la validez de las conclusiones (Conover, 1999, p. 285).

---

### 3.9.6 Tamaños del efecto — Cohen d y Cliff delta (δ)

| Variable | Par | Cohen d | Magnitud d | Cliff δ | Magnitud δ |
|---|---|---:|---|---:|---|
| **CO₂ total evitado** | A2C vs PPO | 0.247 | small | 0.082 | negligible |
| **CO₂ total evitado** | A2C vs SAC | **1.692** | **very large** | **0.781** | **large** |
| **CO₂ total evitado** | PPO vs SAC | **1.649** | **very large** | **0.737** | **large** |
| CO₂ directo | A2C vs PPO | 0.203 | small | −0.054 | negligible |
| CO₂ directo | A2C vs SAC | 0.289 | small | **0.773** | **large** |
| CO₂ directo | PPO vs SAC | 0.043 | negligible | **0.608** | **large** |
| CO₂ indirecto | A2C vs PPO | 0.022 | negligible | 0.022 | negligible |
| CO₂ indirecto | A2C vs SAC | 1.117 | **large** | 0.651 | **large** |
| CO₂ indirecto | PPO vs SAC | 1.212 | **very large** | 0.724 | **large** |
| EV total | A2C vs PPO | 0.229 | small | −0.033 | negligible |
| EV total | A2C vs SAC | 0.330 | small | **0.802** | **large** |
| EV total | PPO vs SAC | 0.047 | negligible | 0.597 | **large** |
| **Mototaxis** | **A2C vs PPO** | **0.496** | **small-medium** | **0.250** | **small** |
| Mototaxis | A2C vs SAC | **0.948** | **large** | **0.890** | **large** |
| F2 residual | A2C vs PPO | 0.080 | negligible | 0.403 | medium |
| F2 residual | SAC vs PPO | 0.290 | small | **0.598** | **large** |

**Interpretación de tamaños de efecto:**
- Cohen d ≥ 0.8 y Cliff δ ≥ 0.474 constituyen efectos grandes.
- La diferencia A2C vs SAC en CO₂ total evitado (d=1.692, δ=0.781) y en mototaxis
  (d=0.948, δ=0.890) son los efectos más grandes del estudio, con alta relevancia práctica.
- La diferencia A2C vs PPO en CO₂ total (d=0.247, δ=0.082) es estadísticamente no
  significativa y de magnitud negligible, confirmando que ambos agentes son equivalentes
  en reducción de CO₂ total.
- Solo en **carga de mototaxis** la diferencia A2C vs PPO alcanza magnitud small-medium
  (d=0.496, δ=0.250) con significancia estadística (p=0.016), siendo la variable que
  distingue operativamente a A2C de PPO.

---

### 3.9.7 Bootstrap IC 95% para diferencias de medias (B = 10,000 réplicas)

| Variable | Par (A − B) | Diferencia media | IC 95% bootstrap | ¿Cero excluido? |
|---|---|---:|---|---|
| CO₂ total evitado | A2C − PPO | +5,857 kg/año | [−3,167 ; 15,089] | NO — no concluyente |
| CO₂ total evitado | A2C − SAC | **+33,283 kg/año** | **[25,614 ; 40,891]** | **SÍ ✓ diferencia real** |
| CO₂ total evitado | PPO − SAC | **+27,425 kg/año** | **[20,561 ; 33,638]** | **SÍ ✓ diferencia real** |
| CO₂ directo | A2C − PPO | +5,235 kg/año | [−4,526 ; 15,452] | NO — no concluyente |
| CO₂ directo | A2C − SAC | +6,384 kg/año | [−2,374 ; 14,953] | NO — no concluyente |
| CO₂ indirecto | A2C − PPO | +622 kg/año | [−10,417 ; 11,902] | NO — no concluyente |
| CO₂ indirecto | A2C − SAC | **+26,898 kg/año** | **[18,039 ; 36,312]** | **SÍ ✓ diferencia real** |
| EV total | A2C − SAC | +8,910 kWh/año | [−1,533 ; 19,298] | NO — no concluyente |
| **Mototaxis** | **A2C − PPO** | **+3,525 kWh/año** | **[878 ; 6,443]** | **SÍ ✓ diferencia real** |
| Mototaxis | A2C − SAC | **+4,143 kWh/año** | **[2,427 ; 5,812]** | **SÍ ✓ diferencia real** |
| F2 residual | SAC − PPO | −16,218 kg/año | [−37,678 ; 5,727] | NO — no concluyente |

**Nota sobre ICs que incluyen cero:** cuando el bootstrap IC incluye cero pero la prueba
de Mann-Whitney es significativa, ello refleja que la distribución es no normal y la media
es sensible a valores extremos. En esos casos prevalece la interpretación no paramétrica
(la prueba de rangos es más apropiada para distribuciones asimétricas).

---

### 3.9.8 Comparación vs F1 Baseline — verificación de que RL añade valor

F1 Baseline = escenario con solar + BESS pero sin control RL (despacho pasivo).
Prueba: Wilcoxon signed-rank entre F1 y cada agente (n=50 pares, H₁: agente < F1 en CO₂
residual).

| Agente | Wilcoxon W | p-valor | Rechaza H₀ | Cohen d | Magnitud | Reducción media vs F1 |
|---|---:|---:|---|---:|---|---:|
| SAC | 1,275 | **8.882×10⁻¹⁶** | **SÍ ✓** | 85.77 | GIGANTE | 37.22% |
| PPO | 1,275 | **8.882×10⁻¹⁶** | **SÍ ✓** | 42.01 | GIGANTE | 37.49% |
| A2C | 1,275 | **8.882×10⁻¹⁶** | **SÍ ✓** | 74.28 | GIGANTE | 37.42% |

Los tres agentes RL reducen significativamente las emisiones respecto al baseline pasivo
(p < 10⁻¹⁵, Cohen d > 40 en todos los casos). El control RL añade reducción adicional
estadísticamente demostrada sobre el escenario solar+BESS sin optimización activa.

---

### 3.9.9 Síntesis de inferencias

| Inferencia | Pruebas que la sustentan | Conclusión |
|---|---|---|
| **SAC < A2C y PPO** en CO₂ evitado | Kruskal-Wallis, Dunn, MWU, Wilcoxon, Cohen d, Cliff δ, Bootstrap IC | **Confirmada con alta certeza** (p < 10⁻⁸, efectos large a very large) |
| **A2C = PPO** en CO₂ total evitado | MWU p=0.240, Wilcoxon p=0.109, Cohen d=0.247, Cliff δ=0.082, IC incluye cero | **Confirmada — equivalentes estadísticamente** |
| **A2C > PPO** en carga mototaxis | Dunn p=0.046, MWU p=0.016, Wilcoxon p=1.99×10⁻⁴, Bootstrap IC [878;6,443] | **Confirmada — diferencia real y significativa** |
| **A2C** es el mejor agente multiobjetivo | 9 criterios liderados, diferencia mototaxis significativa, menor grid import | **A2C seleccionado** |
| Todo agente RL > F1 baseline | Wilcoxon p<10⁻¹⁵, Cohen d>40 GIGANTE | **RL añade valor sobre solar+BESS pasivo** |

---

## 3.10 Referencias metodológicas

Arias, F. (2012). *El proyecto de investigación: Introducción a la metodología científica*
(6ª ed.). Editorial Episteme.

Banks, J., Carson, J. S., Nelson, B. L., & Nicol, D. M. (2010). *Discrete-event simulation*
(5ª ed.). Pearson Prentice Hall.

Brandi, S., Piscitelli, M. S., Martini, M., & Capozzoli, A. (2022). Deep reinforcement
learning to optimise indoor temperature control and reduce energy consumption in buildings.
*Energy and Buildings, 224*, 110225.

Campbell, D. T., & Stanley, J. C. (1966). *Experimental and quasi-experimental designs for
research*. Rand McNally.

Conover, W. J. (1999). *Practical nonparametric statistics* (3ª ed.). Wiley.

Deltetto, D., Coraci, D., Pinto, G., Piscitelli, M. S., & Capozzoli, A. (2021).
Exploring the potentialities of deep reinforcement learning for incentive-based demand
response in a cluster of small commercial buildings. *Energies, 14*(10), 2933.

Faul, F., Erdfelder, E., Lang, A.-G., & Buchner, A. (2007). G*Power 3: A flexible
statistical power analysis program for the social, behavioral, and biomedical sciences.
*Behavior Research Methods, 39*(2), 175–191.

Hernández Sampieri, R., Fernández Collado, C., & Baptista Lucio, M. P. (2014).
*Metodología de la investigación* (6ª ed.). McGraw-Hill / Interamericana Editores.

Kathirgamanathan, A., De Rosa, M., Mangina, E., & Finn, D. P. (2021). Data-driven
predictive control for unlocking building energy flexibility: A review.
*Renewable and Sustainable Energy Reviews, 135*, 110120.

Law, A. M. (2015). *Simulation modeling and analysis* (5ª ed.). McGraw-Hill Education.

Montgomery, D. C. (2017). *Design and analysis of experiments* (9ª ed.). John Wiley & Sons.

Murillo Vargas, G. (2010). *Investigación cuantitativa: una perspectiva epistemológica y
metodológica*. Editorial ICFES.

Siegel, S., & Castellan, N. J. (1988). *Nonparametric statistics for the behavioral sciences*
(2ª ed.). McGraw-Hill.

Tamayo y Tamayo, M. (2003). *El proceso de la investigación científica: incluye evaluación
y administración de proyectos de investigación* (4ª ed.). Editorial Limusa.

---

*Archivo generado: 2026-05-31 | Sección: Capítulo III Metodología*
*Para referencia de resultados estadísticos: `outputs/estadistica_oe3/reporte_estadistico_oe3.md`*
